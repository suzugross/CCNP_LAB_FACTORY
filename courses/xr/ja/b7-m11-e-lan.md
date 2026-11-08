# M11 追補 — E-LAN

ここまでのページで作ったのは E-Line でした。1 つの拠点から、もう 1 つの拠点へです。この追補では、このトラックの XR の
プラットフォームでは動かせないサービスを扱います。**E-LAN**(多くの拠点を 1 つの LAN に)、**EVPN のマルチホーム**
(1 つの拠点を 2 台の PE に)、**イーサネット OAM**(CFM でサービスを見張る)です。CCNP Service Provider のブループリントの
4.2.a、4.2.c、4.1.a にあたります。

| ページ | 内容 | 課題 |
|---|---|---|
| このページ | 多くの拠点を 1 つの LAN に: VPLS と、EVPN の E-LAN | M11-6、M11-7 |
| EVPN のマルチホーム | 1 つの拠点を 2 台の PE に収容し、両方のリンクを使う | M11-8 |
| イーサネット OAM | CFM で E-Line を見張り、Y.1731 で遅延を測る | M11-9 |

ラボは **XRT-12** です。IOS XRv 9000 はブリッジ ドメインを拒否し、CFM もない(付録)ので、ここでは PE を
**Catalyst 8000V**(IOS XE 17.15.1a)にしています。EVPN と CFM の仕組みは OS によりません。経路の種類、イーサネット
セグメント、メンテナンス レベルは IOS XR でも同じです。各節では、IOS XE の形の後に、IOS XR の形を Cisco の
コンフィギュレーション ガイドの形で示します。

:::topo
nodes:
  CE1: {at: [0, 0.3], label: "CE1(拠点 1)"}
  SW1: {at: [0, 1.6], label: "SW1(拠点 4)"}
  CE2: {at: [0, 2.9], label: "CE2(拠点 2)"}
  XE1: {at: [1.9, 0.3], label: "XE1(PE)"}
  XE2: {at: [1.9, 2.9], label: "XE2(PE)"}
  P1: {at: [3.8, 1.6], label: "P1(P、RR)"}
  XE3: {at: [5.7, 1.6], label: "XE3(PE)"}
  CE3: {at: [7.6, 1.6], label: "CE3(拠点 3)"}
links:
  - [CE1, XE1, "Gi2"]
  - [SW1, XE1, "Gi3"]
  - [SW1, XE2, "Gi3"]
  - [CE2, XE2, "Gi2"]
  - [XE1, P1, "CORE-1"]
  - [XE2, P1, "CORE-2"]
  - [P1, XE3, "CORE-3"]
  - [XE3, CE3, "Gi2"]
frames:
  - {label: "AS 65000(IS-IS CORE、LDP)", nodes: [XE1, XE2, P1, XE3]}
:::

4 つの拠点はすべて顧客 C のものです。コアのルータは P1 だけで、P1 は EVPN のルート リフレクタも兼ねます。
SW1(拠点 4)は次のページで加わります。このページで使うのは拠点 1、2、3 です。

## 1. 何が嬉しいのか

### 1.1 3 つの拠点を 1 つの LAN に

顧客 C は、3 つの拠点を 1 つの VLAN にまとめたいと考えています。全部が 1 台のスイッチにつながっているように、
サブネットは 1 つ(172.31.200.0/24)で、ルーティングは自分たちで行い、ARP のようなブロードキャストは全部の拠点に届く形です。

### 1.2 それまでの手: E-Line を網の目に張る

M11 の E-Line では、3 拠点なら 3 本(1–2、1–3、2–3)、n 拠点なら n(n−1)/2 本が要ります。しかも E-Line は線であって
LAN ではありません。CE は E-Line ごとにサブインタフェースとサブネットを 1 つずつ持ち、その間は顧客がルーティングする
ことになります。4 つめの拠点を足すには、既存の全拠点への E-Line を新しく張ります。

### 1.3 この技術の答え: プロバイダーの網を 1 台のスイッチに

**E-LAN** は、プロバイダーの網全体を 1 台のイーサネット スイッチのようにふるまわせます。各 PE は **ブリッジ ドメイン**
を持ちます。PE の中の小さなスイッチです。どの MAC アドレスがどのポートの先にあるかを覚え、分かっている MAC 宛ての
フレームはそのポートへだけ送り、ブロードキャストと宛先の分からないフレームは全部のポートへコピーします。「ポート」は、
顧客のアタッチメント回線と、ほかの PE への道です。PE どうしの道の作り方は 2 通りあります。**VPLS** は疑似回線で
ブリッジ ドメインどうしをつなぎ(2 章)、**EVPN** は MAC アドレスを BGP で交換します(3 章)。

## 2. VPLS

### 2.1 ブリッジ ドメインを疑似回線のフルメッシュでつなぐ

VPLS では、E-LAN の各 PE が、2 種類のメンバーを持つブリッジ ドメインを持ちます。

- 顧客の **アタッチメント回線**(IOS XE では EFP= ポートの上の `service instance`。M11 の l2transport の
  サブインタフェースと同じものです)。
- **VFI**(仮想フォワーディング インスタンス): 同じ VPLS のほかの PE への疑似回線の集まり。どの疑似回線も M11 と同じ
  LDP の疑似回線で、VC ID には **VPN ID**(ここでは 210)を使います。

どの PE も、ほかのすべての PE と疑似回線を持ちます。**フルメッシュ**です。PE が 3 台なら 3 本です。なぜ全部が要るのかは、
次の 2 つの節で見ます。

### 2.2 1 つのフレームを追う: CE1 の ARP

CE1 が CE3(172.31.210.3)に ping を打つと、まず VLAN 210 で ARP の要求をブロードキャストします。フルメッシュなら次のように
進みます。

:::topo
nodes:
  CE1: [0, 1]
  XE1: [1.6, 1]
  XE2: [3.4, 0.2]
  XE3: [3.4, 1.8]
  CE2: [5, 0.2]
  CE3: [5, 1.8]
links:
  - [CE1, XE1, "タグ 210 | ARP"]
  - [XE1, XE2, "疑似回線 210(コピー)"]
  - [XE1, XE3, "疑似回線 210(コピー)"]
  - [XE2, CE2, "タグ 210"]
  - [XE3, CE3, "タグ 210"]
:::

1. XE1 の EFP がフレームを受け取り、タグを外します。ブリッジ ドメインは「CE1 の MAC は Gi2 の service instance 210 の先」
   と覚えます。
2. 宛先はブロードキャストなので、XE1 は VFI の各疑似回線に 1 つずつコピーを送ります。XE2 へと XE3 へです。どのコピーにも、
   相手の PE が LDP で渡した疑似回線のラベルを付け、その外側にその PE へのトランスポートのラベルを付けます。
3. XE2 と XE3 は、それぞれ「CE1 の MAC は XE1 からの疑似回線の先」と覚え、自分の EFP からフレームを出します(タグ 210 を
   付け直します)。XE2 は、XE3 への疑似回線へは送り**ません**。
4. CE3 は CE1 の MAC 宛てのユニキャストで答えます。XE3 はその MAC が XE1 からの疑似回線の先にあると知っているので、
   答えはそこへだけ送ります。

PE は、スイッチと同じように、フレームそのものから MAC アドレスを覚えます(データ プレーンでの学習)。XE1 の
ブリッジ ドメインには、自分の拠点の MAC は EFP に、遠い拠点の MAC は疑似回線に、という形で出ます。

```console
XE1#show bridge-domain 210
Bridge-domain 210 (3 ports in all)
State: UP                    Mac learning: Enabled
    GigabitEthernet2 service instance 210
    vfi VPLS210 neighbor 10.255.0.42 210
    vfi VPLS210 neighbor 10.255.0.43 210
   AED MAC address    Policy  Tag       Age  Pseudoport
   0   AABB.CC00.6A00 forward dynamic   297  VPLS210.404011, VPLS
                                             VC_LABEL: 17, Intf: GigabitEthernet1
   0   AABB.CC00.6900 forward dynamic   287  GigabitEthernet2.EFP210
```

### 2.3 スプリット ホライズン: なぜフルメッシュでなければならないか

手順 3 が、VPLS をループから守る決まりです。**PE は、疑似回線から入ってきたフレームを、同じ VFI の別の疑似回線へは
決して送りません**(スプリット ホライズン)。これが無いと、イーサネットのフレームには TTL が無いので、ブロードキャストが
XE1 → XE2 → XE3 → XE1 と回り続けます。どの PE もほかの全部の PE へ直接の疑似回線を持っているので、2 本目の疑似回線を
渡る必要があるフレームはありません。

決まりの裏返しで、疑似回線が 1 本欠けると、その隙間を回り込んで中継するものはありません。XE1 と XE3 が、どちらも XE2 への
疑似回線しか持っていない(ハブ アンド スポーク)とします。

:::topo
nodes:
  CE1: [0, 1]
  XE1: [1.6, 1]
  XE2: [3.2, 1]
  XE3: [5.2, 1]
  CE3: [6.8, 1]
links:
  - [CE1, XE1, "ARP"]
  - [XE1, XE2, "疑似回線 210"]
  - [XE2, XE3, "疑似回線 210\n送らない(スプリット ホライズン)"]
  - [XE3, CE3, ""]
:::

このとき、XE2 は CE1 と CE3 の MAC をそれぞれの疑似回線で覚えているのに、CE1 から CE3 への ping は通りません。XE2 は
CE3 がどこにいるかを知っていながら、そこへフレームを送らないのです。`show l2vpn vfi` は、スプリット ホライズンを
`S` の列の `Y` で示します。

```console
XE2#show l2vpn vfi name VPLS210
Legend: RT=Route-target, S=Split-horizon, Y=Yes, N=No
VFI name: VPLS210, state: up, type: multipoint, signaling: LDP
  VPN ID: 210
  Bridge-Domain 210 attachment circuits:
  Pseudo-port interface: pseudowire100001
  Interface          Peer Address     VC ID        S
  pseudowire100003   10.255.0.43      210          Y
  pseudowire100002   10.255.0.41      210          Y
```

ハブ アンド スポークを意図して作ることもあります(H-VPLS。ハブのスポーク向きの疑似回線でスプリット ホライズンを外す)が、
そのときはハブがループを防ぐ責任を持ちます。素の VPLS では、フルメッシュそのものがループの防止です。(Catalyst 8000V の
VFI の `member` の行には、スプリット ホライズンを外す選択肢がありません。)

### 2.4 IOS XE での VPLS の設定

:::config Catalyst 8000V(IOS XE 17.15)— VPLS 210 の XE1 の分(3 台とも同じ形)
l2vpn vfi context VPLS210                          ## VFI= この VPLS のための、この PE の疑似回線の集まり
 vpn id 210                                        ## どの疑似回線の VC ID にもなる。全 PE で同じ値
 member 10.255.0.42 encapsulation mpls             ## ほかの PE ごとに 1 行(フルメッシュ)
 member 10.255.0.43 encapsulation mpls
!
interface GigabitEthernet2
 service instance 210 ethernet                     ## アタッチメント回線(EFP)
  encapsulation dot1q 210                          ## 顧客の VLAN 210 のフレームを拾う
  rewrite ingress tag pop 1 symmetric              ## ブリッジ ドメインの中ではタグなし。出ていくときに付け直す
  exit                                             ## service instance とインタフェースを抜ける(3.6 節)
 exit
bridge-domain 210                                  ## PE の中のスイッチ
 member GigabitEthernet2 service-instance 210      ## 顧客向きのポート
 member vfi VPLS210                                ## ほかの PE 向きのポート
!
:::

IOS XR では、同じものを `l2vpn` → `bridge group <名前>` → `bridge-domain <名前>` の下に書きます。アタッチメント回線は
`interface <サブインタフェース>`、ほかの PE ごとに `vfi <名前>` → `neighbor <PE> pw-id <VPN ID>` です。このトラックの
IOS XRv 9000 は、ブリッジ ドメインをコミットで拒否します(`VPLS Bridge domains not supported on this platform`)。

### 2.5 出力の読み方と、うまくいかないとき

- `show l2vpn vfi name <VFI>`: VFI の疑似回線、その VC ID とスプリット ホライズン。
- `show l2vpn atom vc`: 疑似回線ごとの状態(`UP`/`DOWN`)。
- `show bridge-domain <BD>`: メンバーと、覚えた MAC アドレスと、それを覚えたポート。

1 か所だけ間違えたときの見え方です。

| 間違い | 疑似回線 | 何が何に届くか |
|---|---|---|
| メッシュの疑似回線が 1 本欠けている | 設定したものは全部 UP | 間に疑似回線のない 2 台の PE の拠点どうしが通じない |
| 1 台だけ `vpn id` が違う | その PE の疑似回線が DOWN(`LruRnd`= 相手からラベルが来ない) | その PE の拠点が誰とも通じない |
| 1 つの EFP に `rewrite` が無い(タグが残る) | 全部 UP | その拠点が誰とも通じない。その PE は CE の MAC を覚えない |

最後の行はよく見ておく価値があります。XE1 と XE2 はタグを外すので、ブリッジ ドメインの間をフレームはタグなしで渡ります。
タグを外さない EFP は、それを CE へタグなしで送ります。CE の VLAN 210 のサブインタフェースはそれを受け取らず、CE は一度も
答えず、その MAC は PE のブリッジ ドメインに現れません。その間、疑似回線はずっと UP です。見るべきは疑似回線の状態ではなく、
ブリッジ ドメインの MAC の表です。

:::try
スプリット ホライズンが効くところを見ます。課題 M11-6 の後に行ってください。

1. XE1 の `l2vpn vfi context VPLS210` の下で `member 10.255.0.43 encapsulation mpls` を消します。XE3 では
   `member 10.255.0.41 encapsulation mpls` を消します。
2. CE1 で `clear arp-cache` と `ping 172.31.210.3` を実行します。XE2 で `show bridge-domain 210` を実行します。
3. 2 つの member を戻して、もう一度 ping します。

結果の例: ping は通らず(0 percent)、そのとき XE2 のブリッジ ドメインには CE1 と CE3 の MAC が、それぞれの疑似回線の
先として入っていました。member を戻すと ping は通りました。
:::

## 3. EVPN の E-LAN

### 3.1 MAC アドレスを BGP で: 経路の種類 2

VPLS には弱いところが 2 つあります。どの PE もほかの全部の PE への疑似回線が要るので、LDP のセッションは PE の数の 2 乗で
増えます。また、PE は遠い MAC をフレームからしか覚えないので、知らない MAC 宛てのフレームは全部の PE へあふれます。

EVPN はブリッジ ドメインはそのままに、疑似回線の代わりに、アドレス ファミリー `l2vpn evpn` の BGP の経路を使います。
E-Line で EVPN-VPWS がしたのと同じです。PE は自分の顧客の MAC を、これまでどおりアタッチメント回線のフレームから
覚えますが、覚えた MAC を 1 つずつ **種類 2** の経路(MAC/IP の広告)として広告し、その MAC 宛てのフレームに使うラベルも
載せます。ほかの PE はその MAC を BGP から入れます。その MAC からのフレームがコアを渡る前から、どこにあるかを知っています。

```console
XE1#show bgp l2vpn evpn
     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.0.42:200
 *>i  [2][10.255.0.42:200][0][48][AABBCC006A00][0][*]/20
                      10.255.0.42              0    100      0 ?
 *>i  [2][10.255.0.42:200][0][48][AABBCC006A00][32][172.31.200.2]/24
                      10.255.0.42              0    100      0 ?
```

`[2]` が種類です。続いて RD、イーサネット タグ(0)、MAC(48 ビット)、2 本目の経路ではその MAC に対応する IP アドレス
(32 ビット)です。PE は IP を CE の ARP から知りました。次ホップは、その MAC が背後にいる PE です。

### 3.2 ブロードキャスト: 経路の種類 3 と入口での複製

ブロードキャストは、やはり全部の拠点に届ける必要があります。各 PE は、EVPN インスタンスごとに **種類 3** の経路
(包含的マルチキャストのイーサネット タグ、IMET)を 1 つ広告します。「私はこの E-LAN にいます。ブロードキャスト、宛先の
分からないユニキャスト、マルチキャスト(BUM)は、このラベルでコピーを送ってください」という意味です。**入口での複製**
(ingress replication)では、顧客からブロードキャストを受け取った PE が、種類 3 の経路を送ってきた PE ごとに 1 つずつ
コピーを作り、それぞれをユニキャストでコアへ送ります。コアにマルチキャストは要りません。

```console
XE1#show bgp l2vpn evpn
Route Distinguisher: 10.255.0.41:200
 *>   [3][10.255.0.41:200][0][32][10.255.0.41]/17
 *>i  [3][10.255.0.41:200][0][32][10.255.0.42]/17
                      10.255.0.42              0    100      0 ?
 *>i  [3][10.255.0.41:200][0][32][10.255.0.43]/17
                      10.255.0.43              0    100      0 ?
```

最後の欄は、コピーを受け取りたい PE のアドレスです。XE1 は自分のものと、XE2 と XE3 のものを、自分の EVI の RD の下に
取り込んで持っています。

### 3.3 1 つのフレームを追う: CE1 から CE3 へ

:::topo
nodes:
  CE1: [0, 1]
  XE1: [1.7, 1]
  P1: [4.1, 1]
  XE3: [5.8, 1]
  CE3: [7.5, 1]
links:
  - [CE1, XE1, "タグ 200 | IP"]
  - [XE1, P1, "LDP のラベル | EVPN のラベル | フレーム"]
  - [P1, XE3, "EVPN のラベル | フレーム"]
  - [XE3, CE3, "タグなし | IP"]
:::

1. CE1 の ARP の要求(ブロードキャスト)が XE1 に入ります。XE1 は CE1 の MAC を Gi2 で覚え、種類 2 の経路で広告します。
   ブロードキャストは、種類 3 の経路を持つ PE(XE2、XE3)ごとにコピーを作り、それぞれにその PE の BUM のラベルを付けて送ります。
2. CE3 が答えます。XE3 は CE3 の MAC を EFP で覚え、種類 2 の経路で広告します。CE1 の MAC は XE1 の種類 2 の経路ですでに
   知っているので、答えは XE1 へだけ送ります。
3. 次に CE1 が CE3 の MAC 宛てに ping を送ります。XE1 はその MAC を XE3 の種類 2 の経路で知っています。その経路に載っていた
   ラベルを付け、外側に XE3 への LDP のラベルを付けます。
4. P1 はトランスポートのラベルを外します(XE3 の 1 つ手前だから)。XE3 は EVPN のラベルからブリッジ ドメインを見つけ、
   フレームをタグなしで CE3 へ送ります。

拠点 3 はポートをタグなしで使っています(3.6 節)が、フレームは同じ E-LAN を渡ります。どのブリッジ ドメインの中でもフレームは
タグなしで、各 EFP が、自分の拠点が使う形に付けたり外したりします。

### 3.4 IOS XE での EVPN の E-LAN の設定

設定は 4 つの部分からなります。ルート リフレクタへの BGP、EVPN の全体の設定、EVPN インスタンス、アタッチメント回線を
インスタンスにつなぐブリッジ ドメインです。

:::config fold Catalyst 8000V(IOS XE 17.15)— EVPN の E-LAN(EVI 200)の XE1 の分
router bgp 65000
 bgp router-id 10.255.0.41                         ## Loopback0
 no bgp default ipv4-unicast                       ## この PE が BGP で運ぶのは EVPN だけ
 neighbor 10.255.0.51 remote-as 65000              ## ルート リフレクタ P1。ほかとは張らない
 neighbor 10.255.0.51 update-source Loopback0
 address-family l2vpn evpn
  neighbor 10.255.0.51 activate
  neighbor 10.255.0.51 send-community both         ## ルート ターゲットは拡張コミュニティで運ばれる
!
l2vpn evpn
 replication-type ingress                          ## BUM は PE ごとにユニキャストでコピー(コアにマルチキャストなし)
 router-id Loopback0
!
l2vpn evpn instance 200 vlan-based                 ## EVI 200。RD と RT は自動(10.255.0.41:200、65000:200)
!
interface GigabitEthernet2
 service instance 200 ethernet
  encapsulation dot1q 200
  rewrite ingress tag pop 1 symmetric
  exit                                             ## service instance とインタフェースを抜ける(3.6 節)
 exit
bridge-domain 200
 member GigabitEthernet2 service-instance 200
 member evpn-instance 200                          ## ブリッジ ドメインを EVI につなぐ(VFI の代わり)
!
:::

`vlan-based` は、EVI ごとにブリッジ ドメインが 1 つという意味で、ふつうの形です。ルート リフレクタには EVI ごとの設定は
要りません。クライアントの `l2vpn evpn` の経路を全部反映します(このラボの P1 は IOS XE のルータで、クライアントは設定済み
です)。

IOS XR では、ブリッジ ドメインに VFI の代わりに `evi <EVI>` を書き(`l2vpn` → `bridge group` → `bridge-domain` →
`evi 200`)、EVI そのものは `evpn` → `evi 200` の下に(`advertise-mac` とともに)書きます。BGP は EVPN-VPWS と同じく、
全体と近隣の下の `address-family l2vpn evpn` です。

### 3.5 出力の読み方

全体を見るのは `show l2vpn evpn evi <EVI> detail` です。自動の RD とルート ターゲット、状態、複製の方式、ほかの PE ごとの
受け取った経路が出ます。

```console
XE1#show l2vpn evpn evi 200 detail
EVPN instance:       200 (VLAN Based)
  RD:                10.255.0.41:200 (auto)
  Import-RTs:        65000:200
  Export-RTs:        65000:200
  State:             Established
  Replication Type:  Ingress (global)
  Encapsulation:     mpls
  Bridge Domain:     200
    BUM Label:       23
    Per-BD Label:    24
    State:           Established
    Pseudoports:
      GigabitEthernet2 service instance 200
        Routes: 1 MAC, 1 MAC/IP
    Peers:
      10.255.0.42
        Routes: 1 MAC, 1 MAC/IP, 1 IMET, 0 EAD
      10.255.0.43
        Routes: 1 MAC, 1 MAC/IP, 1 IMET, 0 EAD
```

`show l2vpn evpn mac` は、EVI の MAC とその居場所の一覧です。自分の拠点のものは EFP(`Gi2:200`)、遠いものは広告した PE の
先です。

```console
XE1#show l2vpn evpn mac
MAC Address    EVI   BD    ESI                      Ether Tag  Next Hop(s)
-------------- ----- ----- ------------------------ ---------- ---------------
aabb.cc00.6900 200   200   0000.0000.0000.0000.0000 0          Gi2:200
aabb.cc00.6a00 200   200   0000.0000.0000.0000.0000 0          10.255.0.42
aabb.cc00.6b00 200   200   0000.0000.0000.0000.0000 0          10.255.0.43
```

ESI の列が 0 なのは、どの拠点も 1 台の PE にしか収容されていないからです。次のページで、ここが埋まります。

### 3.6 うまくいかないとき

- **複製の方式が無い。** `l2vpn evpn` の下に `replication-type ingress` が無いと、EVI は `State: Incomplete` のまま
  (`Replication Type: Not set (global)`、`EVI Down, BD Up`)です。BGP が上がっている PE どうしの間でも、何も
  通りません。BUM の送り方が決まるまで、PE は E-LAN に加わりません。IOS XE のガイドの例は必ずこれを設定していて、
  EVPN の章には、MPLS 上の EVPN で使えるのは入口での複製だけと書かれています。
- **タグなしの拠点。** 拠点 3 では、顧客はこの E-LAN をタグなしで送ります。そこの EFP は `encapsulation untagged` で、
  外すものはありません。XE3 を `encapsulation dot1q 200` の EFP にすると何にも一致せず、拠点 3 は誰とも通じませんでした
  (0 percent)。同じポートのほかのサービス(VLAN 210 と 130)は、それぞれタグ付きの EFP のままです。
- **設定の貼り付け。** IOS XE には `service instance` の中にも `bridge-domain` のコマンドがあります(EFP をブリッジ ドメインに
  入れる古いやり方)。service instance の直後に `!` だけを挟んで貼ると、`bridge-domain 200` は EFP の方に入り、続く `member`
  の行は拒否され(`Invalid input`)、ブリッジ ドメインは EVI につながりませんでした。このページの例のように、先に `exit` で
  service instance とインタフェースを抜けてください。
- **BGP はルート リフレクタとだけ。** PE どうしのセッションでも経路は運べますが、そうすると新しい PE ごとにほかの全部への
  セッションが要ります。EVPN がなくそうとしたものです。

:::try
複製の方式がどれだけ効くかを見ます。課題 M11-7 の後に行ってください。

1. XE3 の `l2vpn evpn` の下の `replication-type ingress` を消します。
2. XE3 で `show l2vpn evpn evi 200 detail` を実行します。CE1 で `clear arp-cache` と `ping 172.31.200.3` を実行します。
3. 行を戻して 30 秒ほど待ち、同じコマンドをもう一度実行します。

結果の例: XE3 の EVI は `Incomplete Pending`(`Replication Type: Not set (global)`、`EVI Down, BD Up`)になり、
CE1 から拠点 3 への ping は通らず(0 percent)、拠点 2 は答えていました。行を戻すと EVI は `Established` に戻り、ping は
通りました。
:::

## 4. コマンド名の対照

| IOS XE では | IOS XR では |
|---|---|
| `l2vpn vfi context <名前>` → `vpn id <n>`、`member <PE> encapsulation mpls` | `l2vpn` → `bridge group` → `bridge-domain` → `vfi <名前>` → `neighbor <PE> pw-id <n>` |
| `bridge-domain <n>` → `member <IF> service-instance <n>` | `bridge-domain <名前>` → `interface <サブインタフェース>` |
| `service instance <n> ethernet`(EFP) | `interface <サブインタフェース> l2transport` |
| `l2vpn evpn instance <EVI> vlan-based` と `member evpn-instance <EVI>` | `evpn` → `evi <EVI>` と `bridge-domain` → `evi <EVI>` |
| `l2vpn evpn` → `replication-type ingress` | —(ガイドの EVPN の例にこの行は無い) |
| `show l2vpn vfi`、`show bridge-domain <n>` | `show l2vpn bridge-domain [detail]` |
| `show l2vpn evpn evi <EVI> detail`、`show l2vpn evpn mac` | `show evpn evi vpn-id <EVI> detail`、`show evpn evi vpn-id <EVI> mac` |

## 実践

ラボ **XRT-12** で、課題 M11-6 と M11-7 に取り組んでください。その後、次のページ「EVPN のマルチホーム」へ進みます。

<p class="tolab"><a href="/_learn?id=XRT-12">ワークスペースでラボ XRT-12 を開く</a> — <a href="b8-m11-practice-4.html">課題</a></p>

:::note
このページの出力は、Catalyst 8000V 17.15.1a(XE1〜XE3)と IOL 上の IOS XE 17.15(P1、CE、SW1)で取得しました。
出典: MPLS Configuration Guide, Cisco IOS XE 17.x(Configuring Virtual Private LAN Services、EVPN Single-Homing、EVPN over
MPLS with IRB)。EVPN の章が名指ししているのは ASR 1000 で、このラボはそれを Catalyst 8000V で動かしました。L2VPN and
Ethernet Services Configuration Guide for the ASR 9000, IOS XR 25.x(Implementing Multipoint Layer 2 Services)と 7.10.x
(EVPN Features)。RFC 4762(LDP の VPLS、フルメッシュとスプリット
ホライズン)、RFC 7432(EVPN)。いずれも 2026 年 11 月に確認しました。出力、複製の方式が無いときのふるまい、タグなしの拠点、
2.5 節の各間違いは、ラボ XRT-12(Catalyst 8000V 17.15.1a)での測定によります。
:::
