# サービスを並べて見る — 外側は道、内側は入れ物

M9 から M11 までに、L3VPN、VPWS(E-Line)、VPLS、EVPN の 4 つのサービスを 1 つずつ組みました。どれも「お客さまの
通信にラベルを付けてコアを渡す」ので、並べると似て見えます。どれがどう違うのか、どの設定がどのサービスのものなのかが、
単元ごとに読んでいると見えにくくなります。

ここでは 4 つを**同じ盤面、同じ CE の組**の上に並べ、違いを少しの問いに絞ります。新しい技術は出てきません。

| ページ | 中身 |
|---|---|
| このページ | 4 つのサービスの違い: お客さまから見た網、PE が覚えるもの、相手の見つけ方、内側のラベルの意味。RR を道の外に置く理由 |
| 組み立て順 | 4 つを同じ 5 つの段で組む。段ごとの設定例と確かめ方 |
| 実践 | ラボ XRT-13 で、コアだけの状態から 5 つのサービスを組む(課題 S-1〜S-5) |
| EVPN-VPWS は何が嬉しいか | 同じ E-Line を LDP の疑似回線と EVPN-VPWS で。拠点を 2 台の PE につなぐとき、道を SR にするとき |

出力は、このページのために組んだ次の盤面で取りました。PE は Catalyst 8000V(IOS XE 17.15.1a)3 台と、
IOS XRv 9000(26.1.1)1 台です。P1、RR1、CE は IOL の IOS XE 17.15 です。ラベルの値は構築のたびに変わります。

:::topo
nodes:
  CE1: {at: [0, 0.3], label: "CE1(拠点 1)"}
  CE2: {at: [0, 2.9], label: "CE2(拠点 2)"}
  XE1: {at: [1.9, 0.3], label: "XE1(PE)"}
  XE2: {at: [1.9, 2.9], label: "XE2(PE)"}
  P1: {at: [3.8, 1.6], label: "P1(P)"}
  RR1: {at: [3.8, 0.3], label: "RR1(RR)"}
  XE3: {at: [5.7, 0.3], label: "XE3(PE)"}
  XR01: {at: [5.7, 2.9], label: "XR01(PE、IOS XR)"}
  CE3: {at: [7.6, 0.3], label: "CE3(拠点 3)"}
  CE4: {at: [7.6, 2.9], label: "CE4(拠点 4)"}
links:
  - [CE1, XE1, "VLAN 100 130 200 210"]
  - [CE2, XE2, "VLAN 100 140 200 210"]
  - [XE1, P1, ""]
  - [XE2, P1, ""]
  - [P1, XE3, ""]
  - [P1, XR01, ""]
  - [P1, RR1, "IS-IS だけ"]
  - [XE3, CE3, "VLAN 140 200 210"]
  - [XR01, CE4, "VLAN 100 130"]
frames:
  - {label: "AS 65000(IS-IS CORE、LDP)", nodes: [XE1, XE2, P1, RR1, XE3, XR01]}
:::

CE は、1 本のリンクの上に VLAN でサービスを分けて載せています。どの CE も、サービスごとにサブインタフェースを持ちます。

| VLAN | サービス | つなぐ拠点 | CE のアドレス |
|---|---|---|---|
| 100 | L3VPN(VRF A) | 1、2、4 | PE との間に拠点ごとのサブネット 172.16.<拠点>.0/24。拠点の LAN は 10.100.<拠点>.0/24 |
| 130 | VPWS(LDP の疑似回線) | 1 ⇔ 4 | 192.168.130.<拠点> |
| 140 | VPWS(EVPN-VPWS) | 2 ⇔ 3 | 192.168.140.<拠点> |
| 200 | EVPN の E-LAN | 1、2、3 | 192.168.200.<拠点> |
| 210 | VPLS | 1、2、3 | 192.168.210.<拠点> |

## 1. 何が嬉しいのか

### 1.1 困りごと: 4 つが同じに見える

4 つのサービスは、どれも次の流れです。CE から受けた通信に PE がラベルを付け、P がラベルを見て運び、相手の PE が
ラベルを外して CE へ渡します。設定にも `l2vpn`、`evpn`、`bgp`、`route-target` のように、同じ語が何度も出てきます。

このため、1 つずつ覚えようとすると混ざります。「VPLS には BGP が要るのか」「EVPN の RT はどこに書いたか」
「L3VPN のラベルと疑似回線のラベルは何が違うのか」が、単元をまたぐと分からなくなります。

### 1.2 このページの見方: 4 つの問い

4 つのサービスの違いは、次の 4 つの問いに答えると見えてきます。

1. お客さまから見ると、網は何に見えるか
2. PE は何を覚えるか
3. PE は、同じサービスの相手の PE をどう見つけるか
4. 内側のラベルは何を指すか

先に答えを言うと、**外側のラベルはどのサービスでも同じ「道」で、違いは全部、内側のラベルとその先にある「入れ物」に
あります**。以下、問いを 1 つずつ盤面で確かめます。

## 2. 4 つを並べる

### 2.1 お客さまから見ると: ルータか、ケーブルか、スイッチか

CE1 の ARP の表を見ると、違いがすぐに分かります。

```console
CE1#show ip arp
Protocol  Address          Age (min)  Hardware Addr   Type   Interface
Internet  172.16.1.254           11   5254.00b5.ceb7  ARPA   Ethernet0/0.100
Internet  192.168.130.4           8   aabb.cc00.8e00  ARPA   Ethernet0/0.130
Internet  192.168.200.2           5   aabb.cc00.8c00  ARPA   Ethernet0/0.200
Internet  192.168.200.3           5   aabb.cc00.8d00  ARPA   Ethernet0/0.200
Internet  192.168.210.2           6   aabb.cc00.8c00  ARPA   Ethernet0/0.210
Internet  192.168.210.3           6   aabb.cc00.8d00  ARPA   Ethernet0/0.210
```

(CE1 自身の行は省いています。)

- **L3VPN(VLAN 100)**: CE1 の隣にいるのは PE(XE1 の MAC `5254.00b5.ceb7`)です。CE1 は XE1 と eBGP を話し、
  ほかの拠点の LAN を XE1 から経路として受け取ります。お客さまから見ると、網は **1 台の大きなルータ**です。
- **VPWS(VLAN 130)**: 隣にいるのは、遠くの拠点 4 の CE4(`aabb.cc00.8e00`)です。PE は見えません。
  網は **1 本のケーブル**です。
- **VPLS(VLAN 210)と EVPN(VLAN 200)**: 隣に、CE2 と CE3 の両方がいます。3 つの拠点が 1 つのサブネットに並んでいます。
  網は **1 台のスイッチ**です。

L3VPN では拠点ごとにサブネットが違い(172.16.1.0/24、172.16.2.0/24…)、L2 のサービスでは全拠点が 1 つのサブネットを
分け合います(192.168.210.0/24)。L3VPN は PE がルーティングに加わり、L2 のサービスは PE がフレームを運ぶだけ、という
違いがここに表れます。

```console
CE1#show ip bgp | begin Network
     Network          Next Hop            Metric LocPrf Weight Path
 *>   10.100.1.0/24    0.0.0.0                  0         32768 i
 *>   10.100.2.0/24    172.16.1.254                           0 65000 65002 i
 *>   10.100.4.0/24    172.16.1.254                           0 65000 65004 i
```

L3VPN の CE1 は、拠点 2 と拠点 4 の LAN を、どちらも XE1(172.16.1.254)から AS 65000 経由で受け取っています。
拠点 4 は IOS XR の PE の先ですが、CE1 からは区別がつきません。

### 2.2 PE が覚えるもの

お客さまからの見え方が違うので、PE が覚えるものも違います。

| サービス | PE が覚えるもの | 見る show(IOS XE) |
|---|---|---|
| L3VPN | お客さまの経路(VRF ごとの経路表) | `show ip route vrf A` |
| VPWS | 何も覚えない。この AC とあの疑似回線が対、という対応だけ | `show l2vpn atom vc` |
| VPLS | MAC アドレス。届いたフレームの送信元から学ぶ | `show bridge-domain 210` |
| EVPN | MAC アドレス。BGP で教え合う | `show l2vpn evpn evi 200 detail`、`show bgp l2vpn evpn route-type 2` |

L3VPN の XE1 は、VRF A の経路表に 3 つの拠点の LAN を持っています。自分の拠点 1 は CE1 から eBGP で、拠点 2 と 4 は
ほかの PE から iBGP で受けたものです。

```console
XE1#show ip route vrf A | begin Gateway
Gateway of last resort is not set
      10.0.0.0/24 is subnetted, 3 subnets
B        10.100.1.0 [20/0] via 172.16.1.1, 00:02:26
B        10.100.2.0 [200/0] via 10.255.0.42, 00:02:14
B        10.100.4.0 [200/0] via 10.255.0.1, 00:01:32
```

VPLS の XE1 は、スイッチと同じように MAC の表を持ちます。違うのは、遠くの拠点の MAC が「ポート」ではなく
**疑似回線**の先にいることです。拠点 2 の CE2(`8c00`)は XE2 への疑似回線の先、拠点 3 の CE3(`8d00`)は XE3 への
疑似回線の先、と覚えています。

```console
XE1#show bridge-domain 210
Bridge-domain 210 (3 ports in all)
State: UP                    Mac learning: Enabled
    GigabitEthernet2 service instance 210
    vfi VPLS210 neighbor 10.255.0.42 210
    vfi VPLS210 neighbor 10.255.0.43 210
   AED MAC address    Policy  Tag       Age  Pseudoport
   0   AABB.CC00.8C00 forward dynamic   295  VPLS210.404012, VPLS
                                             VC_LABEL: 27, Intf: GigabitEthernet1
   0   AABB.CC00.8D00 forward dynamic   297  VPLS210.404013, VPLS
                                             VC_LABEL: 26, Intf: GigabitEthernet1
   0   AABB.CC00.8B00 forward dynamic   298  GigabitEthernet2.EFP210
```

EVPN の XE1 も同じブリッジ ドメインの形で MAC を持ちますが、遠くの MAC は、フレームが来る前に **BGP で**届いています。
相手の PE ごとに、受け取った経路を種類ごとに数えた行が出ます(MAC と MAC/IP が種類 2、IMET が種類 3)。

```console
XE1#show l2vpn evpn evi 200 detail
EVPN instance:       200 (VLAN Based)
  RD:                10.255.0.41:200 (auto)
  Import-RTs:        65000:200
  Export-RTs:        65000:200
  Bridge Domain:     200
    BUM Label:       29
    Per-BD Label:    30
    Pseudoports:
      GigabitEthernet2 service instance 200
        Routes: 1 MAC, 1 MAC/IP
    Peers:
      10.255.0.42
        Routes: 1 MAC, 1 MAC/IP, 1 IMET, 0 EAD
      10.255.0.43
        Routes: 1 MAC, 1 MAC/IP, 1 IMET, 0 EAD
```

VPLS と EVPN は、お客さまから見るとどちらもスイッチで、PE の中もどちらもブリッジ ドメインです。違うのは**遠くの MAC の
覚え方**だけです。VPLS はスイッチと同じく届いたフレームから学び、EVPN は BGP で教え合います。EVPN のマルチホームや、
フレームが来る前から宛先が分かることの利点は、この違いから生まれます(M11 追補)。

### 2.3 相手の PE の見つけ方: 名指しするか、BGP で見つけ合うか

同じサービスに加わっている相手の PE を、どう知るか。ここが、設定の形をいちばん大きく分けます。

| 見つけ方 | サービス | 書くもの | ラベルを伝える手段 |
|---|---|---|---|
| **名指し** | VPWS(LDP)、VPLS | 入れ物の中に、相手の PE のアドレスを書く | PE 同士の targeted LDP。書けば自動で張られる |
| **BGP で見つけ合う** | L3VPN、EVPN(E-LAN、EVPN-VPWS) | RR への iBGP にアドレス ファミリを足し、入れ物に RT を付ける | BGP の経路に載せる |

名指しのほうは、相手を書いた数だけセッションができます。XE1 は、疑似回線の相手(XR01)と VPLS の相手(XE2、XE3)の
3 台と、P1 とのリンクの LDP に加えて targeted の LDP を張っています。

```console
XE1#show mpls ldp neighbor | include Peer|Targeted|Src
    Peer LDP Ident: 10.255.0.51:0; Local LDP Ident 10.255.0.41:0
	  GigabitEthernet1, Src IP addr: 10.0.41.51
    Peer LDP Ident: 10.255.0.1:0; Local LDP Ident 10.255.0.41:0
	  Targeted Hello 10.255.0.41 -> 10.255.0.1, active, passive
    Peer LDP Ident: 10.255.0.42:0; Local LDP Ident 10.255.0.41:0
	  Targeted Hello 10.255.0.41 -> 10.255.0.42, active, passive
    Peer LDP Ident: 10.255.0.43:0; Local LDP Ident 10.255.0.41:0
	  Targeted Hello 10.255.0.41 -> 10.255.0.43, active, passive
```

BGP のほうは、PE は RR(RR1)と 1 本のセッションを張るだけです。仲間かどうかは RT で決まります。VRF A の RT 65000:100 を
輸入する PE が L3VPN の仲間で、EVI 200 の RT 65000:200 を輸入する PE が E-LAN の仲間です。拠点を足しても、ほかの PE の
設定は変わりません。

```console
XE1#show bgp vpnv4 unicast all summary | begin Neighbor
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.255.0.52     4        65000      34      23        6    0    0 00:13:17        2
172.16.1.1      4        65001      18      17        6    0    0 00:11:49        1
XE1#show bgp l2vpn evpn summary | begin Neighbor
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.255.0.52     4        65000      34      23       20    0    0 00:13:17        6
```

E-Line には 2 つの作り方がありました。LDP の疑似回線は名指し、EVPN-VPWS は BGP です。お客さまから見ると同じケーブルで、
違うのは相手の見つけ方だけです。VPLS と EVPN の E-LAN の関係も同じです。EVPN-VPWS の嬉しさは、拠点を 2 台の PE に
つなぐときと、コアから LDP をなくすときに出ます(「EVPN-VPWS は何が嬉しいか」のページ)。

## 3. 仕組み: 1 ホップずつ

### 3.1 同じ道を 3 つのサービスで

CE1 から CE2 へ、L3VPN、VPLS、EVPN の 3 つで同じように ping を打ち、XE1 → P1 の線と P1 → XE2 の線で
パケットを捕まえました(CML のリンクのキャプチャ)。3 つとも、通る道は CE1 → XE1 → P1 → XE2 → CE2 です。

:::topo
nodes:
  CE1: [0, 1]
  XE1: [1.6, 1]
  P1: [3.2, 1]
  XE2: [4.8, 1]
  CE2: [6.4, 1]
links:
  - [CE1, XE1, "タグ付き"]
  - [XE1, P1, "18 | 内側 | 中身"]
  - [P1, XE2, "内側 | 中身"]
  - [XE2, CE2, "タグ付き"]
:::

| 線 | L3VPN(VLAN 100) | VPLS(VLAN 210) | EVPN(VLAN 200) |
|---|---|---|---|
| CE1 → XE1 | タグ 100、IP | タグ 210、フレーム | タグ 200、フレーム |
| XE1 → P1 | **18** \| 25 \| IP | **18** \| 27 \| CW \| フレーム | **18** \| 30 \| フレーム |
| P1 → XE2 | 25 \| IP | 27 \| CW \| フレーム | 30 \| フレーム |
| XE2 → CE2 | タグ 100、IP | タグ 210、フレーム | タグ 200、フレーム |

(CW はコントロール ワード。3.4 節)

捕まえたパケットは次のとおりです(行を短くしています)。

```console
# XE1 → P1 の線
MPLS (label 18, ttl 254) (label 25, [S], ttl 254) 10.100.1.1 > 10.100.2.1: ICMP echo request
MPLS (label 18, ttl 255) (label 27, [S], ttl 255)
MPLS (label 18, ttl 255) (label 30, [S], ttl 255)
# P1 → XE2 の線
MPLS (label 25, [S], ttl 253) 10.100.1.1 > 10.100.2.1: ICMP echo request
MPLS (label 27, [S], ttl 254)
MPLS (label 30, [S], ttl 254)
```

外側のラベルは、3 つとも **18** です。18 は、P1 が「XE2(10.255.0.42)へはこのラベルで送ってくれ」と LDP で XE1 に
伝えた値で、サービスとは関係がありません。

```console
XE1#show mpls forwarding-table 10.255.0.42 32
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
22         18         10.255.0.42/32   0             Gi1        10.0.41.51
```

P1 は外側の 18 だけを見て XE2 へ送ります。P1 は XE2 の 1 つ手前なので、18 を外してから送ります(PHP)。P1 は内側の
ラベルを見ず、どのサービスのパケットかも知りません。P1 の設定にはサービスが 1 つも出てこず、BGP もありません(3.5 節)。
P1 のラベルの表にあるのは、PE と RR1 のループバックへの道だけです。

```console
P1#show mpls forwarding-table
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
16         No Label   10.255.0.52/32   18630         Et1/1      10.0.52.52
17         Pop Label  10.255.0.41/32   14277         Et0/0      10.0.41.41
18         Pop Label  10.255.0.42/32   7446          Et0/1      10.0.42.42
19         Pop Label  10.255.0.43/32   6858          Et0/2      10.0.43.43
20         Pop Label  10.255.0.1/32    5610          Et1/0      10.0.1.1
```

16 は RR1 のループバックへの道です。RR1 は LDP を動かしていないので、出ていくラベルは `No Label`(ラベルを外し、
普通の IP パケットとして送る)です。RR1 の役目は 3.5 節で見ます。

外側のラベルは「どの PE まで運ぶか」という**道**です。M8 の LDP、M8 追補の BGP ラベル付きユニキャスト、M10 の SR は、
どれもこの道の作り方の違いでした。どの作り方でも、上に載るサービスは変わりません。

### 3.2 内側のラベルは、受け取る PE の入れ物の番号

XE2 に着いたとき、残っているのは内側のラベル 1 枚です。XE2 はそれを見て、パケットをどこへ渡すかを決めます。
XE2 のラベルの表を見ると、25、27、30 がそれぞれ何を指しているかが分かります。

```console
XE2#show mpls forwarding-table
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
25         No Label   10.100.2.0/24[V] 826           Gi2.100    172.16.2.1
26         No Label   l2ckt(1)         646           Gi2        point2point
27         No Label   l2ckt(2)         708           none       point2point
28         No Label   l2ckt(3)         0             none       point2point
29         No Label   evpn(mc:bd 200)  120           none       point2point
30         No Label   evpn(uc:bd 200)  456           none       point2point
```

(コアの行は省いています。)

- **25** は VRF A の経路 10.100.2.0/24 です(`[V]` は VRF の印)。XE2 はラベルを外し、VRF A の経路として CE2 へ送ります。
- **27** は疑似回線の 1 本です。VPLS の、XE1 から来る疑似回線で、出口は `none`、つまりブリッジ ドメイン 210 です。
  XE2 はフレームをブリッジ ドメインに入れ、MAC の表で出口のポートを決めます。
- **30** は EVPN のブリッジ ドメイン 200 の、ユニキャスト用のラベルです(`uc`)。29 はブロードキャストなど BUM 用です(`mc`)。

どのラベルも、XE2 が自分で選び、XE1 に「この入れ物宛てならこの番号を付けて」と伝えた番号です。伝え方は、2.3 節の
見つけ方と同じ手段です。

| サービス | 内側のラベルが指すもの | XE1 への伝え方 | XE1 で見る show |
|---|---|---|---|
| L3VPN | XE2 の VRF の経路(または VRF そのもの) | BGP の VPNv4 経路に載せる | `show bgp vpnv4 unicast all labels`(`nolabel/25`) |
| VPWS | 疑似回線の先の AC 1 つ | targeted LDP | `show l2vpn atom vc vcid <ID> detail` |
| VPLS | VPLS の疑似回線(→ブリッジ ドメイン) | targeted LDP | `show bridge-domain <BD>`(`VC_LABEL`) |
| EVPN | EVI のブリッジ ドメイン | BGP の EVPN 経路(種類 2 と 3)に載せる | `show bgp l2vpn evpn route-type 2`(`Label1`) |

番号は PE ごとに意味が違います。この盤面では XE1 も自分の VRF A の経路に 25 を使っていましたが、XE1 の 25 と XE2 の 25 は
別のものです。ラベルの番号は、それを選んだ PE の中でだけ意味を持ちます。

### 3.3 VPWS: 線を 1 本

CE1 から CE4 への VPWS は、XE1 → P1 → XR01 を通ります。

| 線 | VPWS(VLAN 130) |
|---|---|
| CE1 → XE1 | タグ 130、フレーム |
| XE1 → P1 | **20** \| 24010 \| フレーム |
| P1 → XR01 | 24010 \| フレーム |
| XR01 → CE4 | タグ 130、フレーム |

外側の 20 は XR01 への道です。内側の 24010 は XR01 が選んだ番号で、XR01 のラベルの表では、疑似回線から直接
CE4 側のサブインタフェースを指しています。MAC の表も経路の表も引かずに、そのまま出すだけです。

```console
RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24009  Unlabelled  10.100.4.0/24[V]   Gi0/0/0/1.100 172.16.4.1      0
24010  Pop         PW(10.255.0.41:130)   \
                                      Gi0/0/0/1.130 point2point     516
```

(コアの行は省いています。)

24009 は L3VPN の VRF A の経路です。IOS XR でも IOS XE でも、ラベルの表は同じ読み方ができます。

### 3.4 ラベルの中身: IP か、フレームか

内側のラベルの下に何が入っているかも、サービスで違います。

- **L3VPN** は IP パケットです。XE1 は CE1 から受けたフレームの Ethernet ヘッダーを外し、IP だけを運びます。
  XE2 は経路表を引いてから、CE2 への新しい Ethernet ヘッダーを付けます。
- **L2 のサービス**は、お客さまの Ethernet フレームそのものです。宛先と送信元の MAC は、CE1 と遠くの CE のものです。
  VPWS の線で捕まえたフレームの頭は、`aabb.cc00.8e00`(CE4)宛て、`aabb.cc00.8b00`(CE1)から、の Ethernet ヘッダーでした。

L2 の 4 つとも、フレームは VLAN のタグを外した形で載っていました。PE が AC で `rewrite ingress tag pop 1 symmetric` を
しているからです。タグはそれぞれの拠点のリンクの中だけの目印で、コアの中には出てきません(M11)。

:::note
VPLS と EVPN-VPWS(どちらも Catalyst 8000V 同士)では、フレームの前に 4 バイトのコントロール ワードが付いていました。
EVPN の E-LAN と、Catalyst 8000V と IOS XR の間の LDP の疑似回線には付いていませんでした。付けるかどうかは PE 同士で
決めます(M11 の 2.4 節)。また、Catalyst 8000V の EVPN-VPWS は、フレームに VLAN 0 のタグを付けて運んでいました。
:::

L3VPN の CE からは、traceroute でもホップごとのラベルが見えます。2 ホップ目の P1 で 2 枚、3 ホップ目の XR01 で 1 枚です。
3.1 節の表と同じ形です。

```console
CE1#traceroute 10.100.4.1 source Loopback100 probe 1 timeout 2
  1 172.16.1.254 16 msec
  2 10.0.41.51 [MPLS: Labels 20/24009 Exp 0] 2 msec
  3 10.0.1.1 [MPLS: Label 24009 Exp 0] 7 msec
  4 172.16.4.1 2 msec
```

### 3.5 RR は道の外に置く: BGP を持たないコア

3.1 節で見たとおり、P1 は外側のラベルだけで運び、どのサービスのパケットかを知りません。P1 には BGP もありません。

```console
P1#show running-config | include ^router
router isis CORE
P1#show ip bgp summary
% BGP not active
```

**何が嬉しいのか**。お客さまの経路(VRF の経路や MAC)を持つのは、そのお客さまをつなぐ PE だけになります。P ルータの表は
「PE のループバックの数」だけで、お客さまや拠点がいくら増えても大きくならず、P ルータの設定も変わりません。この形を
**BGP を持たないコア**(BGP-free core)と呼びます。コアのルータは VPN の経路を知らなくてよい、というのが MPLS の VPN の
出発点です(RFC 4364)。

ただし、PE 同士が BGP で経路を交換するには、RR(またはすべての PE 同士のセッション)が要ります。RR を P ルータに兼ねさせる
こともできます。その場合も P ルータはその経路を転送には使いませんが、全お客さまの VPN の経路を BGP の表に抱え、そのための
メモリと処理を使います。上の嬉しさが崩れるので、この盤面では RR を専用の RR1 に分け、P1 の脇に 1 本でつないでいます。

**仕組み**。RR1 は PE から受けた経路を、ほかの PE へ配ります。RR1 の BGP の表には全拠点の経路が並びますが、RR1 には VRF が
無いので、どの経路も転送の表には入りません。

```console
RR1#show bgp vpnv4 unicast all
BGP table version is 4, local router ID is 10.255.0.52
     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.0.1:100
 *>i  10.100.4.0/24    10.255.0.1               0    100      0 65004 i
Route Distinguisher: 10.255.0.41:100
 *>i  10.100.1.0/24    10.255.0.41              0    100      0 65001 i
Route Distinguisher: 10.255.0.42:100
 *>i  10.100.2.0/24    10.255.0.42              0    100      0 65002 i
```

(凡例の行は省いています。)

RR1 は配るときに、次の行き先(ネクスト ホップ)を書き換えません。XE1 が RR1 から受け取った拠点 2 の経路は、
送り主(`Originator`)が XE2 で、次の行き先も XE2(10.255.0.42)のままです。

```console
XE1#show bgp vpnv4 unicast all 10.100.2.0/24
BGP routing table entry for 10.255.0.41:100:10.100.2.0/24, version 4
Paths: (1 available, best #1, table A)
  Flag: 0x100
  Advertised to update-groups:
     3
  Refresh Epoch 2
  65002, imported path from 10.255.0.42:100:10.100.2.0/24 (global)
    10.255.0.42 (metric 30) (via default) from 10.255.0.52 (10.255.0.52)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      Extended Community: RT:65000:100
      Originator: 10.255.0.42, Cluster list: 10.255.0.52
      mpls labels in/out nolabel/25
      rx pathid: 0, tx pathid: 0x0
      Updated on Nov 4 2026 21:45:12 UTC
```

(RD 10.255.0.42:100 の項目は省いています。)

そのため XE1 は、この経路へのパケットを XE2 への道(外側 18、内側 25)に載せて P1 へ送ります。RR1 は通りません。
3.1 節で捕まえたパケットのとおりです。

```console
XE1#show ip cef vrf A 10.100.2.0 255.255.255.0 detail
10.100.2.0/24, epoch 0, flags [rib defined all labels]
  recursive via 10.255.0.42 label 25
    nexthop 10.0.41.51 GigabitEthernet1 label 18-(local:22)
```

RR1 を通るのは、PE と RR1 の BGP のセッションだけです。このセッションも、P1 までは RR1 のループバックへの道(ラベル 16)に
載り、P1 がラベルを外して RR1 へ渡します(3.1 節の P1 の表の 16 の行)。XE1 → P1 の線では次のように見えます。

```console
# XE1 → P1 の線
MPLS (label 16, [S], ttl 255) 10.255.0.41.20034 > 10.255.0.52.179: Flags [.], ack 3955820421, win 15900, length 0
```

RR1 自身は MPLS を動かしていません。経路を配るだけで、お客さまのパケットを運ばないからです。

```console
RR1#show mpls interfaces
Interface              IP            Tunnel   BGP Static Operational
```

:::note
RR を P ルータと分け、お客さまの通信の通り道から外す設計は、実際の網でも使われます。Cisco は IOS XRv 9000 を、転送の道に
入らない仮想の RR(vRR)としても用意しています。RR1 は P1 に 1 本でつながるだけなので、そもそも通り道になりようがありません。
:::

## 4. まとめ

| | L3VPN | VPWS | VPLS | EVPN(E-LAN) |
|---|---|---|---|---|
| お客さまから見た網 | 1 台のルータ | 1 本のケーブル | 1 台のスイッチ | 1 台のスイッチ |
| CE の隣にいるもの | PE | 遠くの CE 1 台 | 遠くの CE 全部 | 遠くの CE 全部 |
| PE が覚えるもの | お客さまの経路(VRF) | 覚えない(AC と疑似回線の対) | MAC(届いたフレームから) | MAC(BGP で) |
| 相手の PE の見つけ方 | BGP(RT) | 名指し(LDP)。EVPN-VPWS は BGP | 名指し(LDP) | BGP(RT) |
| 内側のラベルが指すもの | VRF の経路 | AC 1 つ | 疑似回線(→ブリッジ ドメイン) | ブリッジ ドメイン |
| ラベルの下の中身 | IP パケット | Ethernet フレーム | Ethernet フレーム | Ethernet フレーム |
| 外側のラベル | 4 つとも同じ: 出口の PE への道(LDP、SR …) | | | |

一言でいうと、**外側のラベルは道、内側のラベルは着いた PE の入れ物の番号**です。4 つのサービスの違いは、入れ物が何か
(VRF、AC、ブリッジ ドメイン)と、その番号をどう伝えるか(BGP か LDP か)の 2 つに尽きます。

P ルータは外側のラベルしか見ないので、サービスの設定も BGP も要りません。RR は経路を配るだけなので、道の外に置けます。

次のページでは、この違いが設定のどこに出てくるかを、組み立ての順に見ます。
