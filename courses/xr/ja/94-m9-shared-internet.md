# M9 — 共有サービスとインターネット

このページは、VPN の顧客を分けたまま、一部のルートだけを VPN の間やグローバル テーブルとやり取りする方法を扱います。
ブループリントの 4.3.b(エクストラネットとインターネット接続)にあたり、課題 M9-3 と M9-4 で使います。前のページ
「L3VPN の仕組み」の 2.3 節(ルート ターゲット)を先に読んでください。

## 1. 何が嬉しいのか

### 1.1 共有のサーバを、顧客を分けたまま見せる

プロバイダーは、DNS や監視、クラウドへの入口のようなサービスを、多くの顧客に提供します。サービスのサーバは 1 か所に置きたい
ものの、顧客の VPN は互いに分けておかなければなりません。顧客ごとにサーバを並べたり、顧客ごとの回線で引き込んだりすると、
顧客の数だけ手間が増えます。

### 1.2 VPN の顧客にインターネットも

VPN の顧客は、インターネットにも出たいものです。サイトごとにインターネット用の別の回線を引けば済みますが、回線と CE の
設定が倍になります。同じ PE から出せれば、顧客は 1 本の回線で両方を使えます。

### 1.3 答え

どちらも、ルートをどこに取り込むかを決めるルート ターゲットの組み合わせと、VRF とグローバル テーブルの間でルートを
コピーする仕組みで解きます。

| 困りごと | 答え | 節 |
|---|---|---|
| 共有のサーバを、どの顧客にも見せたい | サーバの VRF が配る荷札を、顧客の VRF が取り込む | 2.1 |
| 顧客どうしは、見えないままにしたい | 顧客の VRF は互いの荷札を取り込まない。取り込みはつながっていかない | 2.2 |
| 一部のルートだけを共有したい | 輸出のポリシーで、そのルートにだけ荷札を足す | 2.3 |
| インターネットのルートを VRF に入れたい | グローバル テーブルから VRF へ取り込む(import from default-vrf) | 2.5 |
| 顧客のルートをインターネットへ出したい | VRF からグローバル テーブルへ書き出す(export to default-vrf) | 2.5 |

## 2. 仕組み

### 2.1 RT の組み合わせで、つながり方を決める

ここまでの VRF は、輸出と輸入に同じ RT を 1 つ使っていました。顧客 A の 2 つのサイトは 65000:101 で互いを取り込み、
顧客 B は 65000:102 です。RFC 4364 は、1 つの RT を輸出と輸入の両方に使うと閉じた VPN になり、輸出と輸入に別の RT を
使えば、ハブ アンド スポークのような別の形が作れる、と書いています(4.3.5 節)。

共有サービスは、この組み合わせで作ります。ラボの約束は次のとおりです。

| VRF | 輸出する RT | 輸入する RT |
|---|---|---|
| CUST-A(XR01 と RT02) | 65000:101 | 65000:101、65000:900 |
| CUST-B(XR01 と RT02) | 65000:102 | 65000:102、65000:900 |
| SVC(XR01) | 65000:999(10.99.1.0/24 には 65000:900 も) | 65000:101、65000:102 |

- 顧客の VRF は 65000:900 を取り込むので、SVC が 900 を付けたルート(10.99.1.0/24)が見えます。
- SVC は 65000:101 と 65000:102 を取り込むので、両方の顧客のルートが見え、サーバからの戻りのパケットにも経路があります。
- 顧客 A の VRF は 65000:102 を取り込まないので、顧客 B のルートは見えません。逆も同じです。

4 つの課題を終えたラボで、SVC の表には両方の顧客のサイトが並び、顧客 B の表には共有のサーバ(10.99.1.0/24)だけが
加わっています。

```console
RP/0/RP0/CPU0:XR01#show route vrf SVC
...
S    10.99.1.0/24 [1/0] via 172.16.91.2, 00:13:36
S    10.99.2.0/24 [1/0] via 172.16.91.2, 00:13:36
B    10.101.1.0/24 [20/0] via 172.16.11.2 (nexthop in vrf CUST-A), 00:02:53
B    10.101.2.0/24 [200/0] via 10.255.0.12 (nexthop in vrf default), 00:06:25
B    10.102.1.0/24 [20/0] via 172.16.21.2 (nexthop in vrf CUST-B), 00:13:30
B    10.102.2.0/24 [200/0] via 10.255.0.12 (nexthop in vrf default), 00:00:24
...
RP/0/RP0/CPU0:XR01#show route vrf CUST-B
...
B    10.99.1.0/24 [200/0] via 172.16.91.2 (nexthop in vrf SVC), 00:13:17
B    10.102.1.0/24 [20/0] via 172.16.21.2, 00:13:48
B    10.102.2.0/24 [200/0] via 10.255.0.12 (nexthop in vrf default), 00:00:24
C    172.16.21.0/24 is directly connected, 00:14:06, GigabitEthernet0/0/0/3
L    172.16.21.1/32 is directly connected, 00:14:06, GigabitEthernet0/0/0/3
```

### 2.2 取り込みは、つながっていかない

SVC は顧客 B のルートを取り込みますが、それを顧客 A へ渡すことはありません。VRF が輸出するのは、その VRF 自身のルート
(CE や静的経路から学んだもの)で、別の VRF から取り込んだルートは、元の RT(顧客 B なら 65000:102)を持ったままです。
SVC の輸出の RT 65000:999 が付くことはないので、顧客 A は SVC を通しても顧客 B を学びません。CEA1 からは、共有のサーバには
届き、顧客 B と SVC の内部のセグメントには届きません。

```console
CEA1#ping 10.99.1.1 source Loopback10 repeat 3
...
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/2/3 ms
CEA1#ping 10.102.1.1 source Loopback10 repeat 3
...
Success rate is 0 percent (0/3)
CEA1#ping 10.99.2.1 source Loopback10 repeat 3
...
Success rate is 0 percent (0/3)
```

共有サービスには、もう 1 つ約束事があります。SVC は両方の顧客のルートを 1 つの表に取り込むので、顧客どうしのアドレスが
重なると、SVC の中では区別できません。前のページの 2.2 節で顧客 B にも 10.101.2.0/24 を置いたとき、CUST-A と CUST-B は
それぞれ自分の 10.101.2.0/24 を持ちましたが、SVC の表で選ばれたのは 1 本(顧客 A の方)だけでした。共有サービスを使う顧客の
アドレスは重ならないように決めるか、NAT で重なりを解く必要があります。

### 2.3 1 つのルートにだけ荷札を足す

RT だけを使うと、VRF はすべてのルートを同じ RT で輸出します。1 つのルートにだけ別の RT を足すには、IOS XR は VRF の
アドレス ファミリーにルート ポリシーを付けます。`export route-policy` は VRF から出ていくルートに、`import route-policy` は
VRF に入ってくるルートに働きます。

ラボでは、共有サービスのすべてのルートに VRF のエクスポートするルート ターゲット 65000:999 が付き、10.99.1.0/24 にはさらに、顧客の VRF が
インポートする 65000:900 が付きます。ポリシーは、そのプレフィックスにだけ追加のターゲットを付けます。

```text
route-policy SVC-EXPORT
  if destination in (10.99.1.0/24) then
    set extcommunity rt (65000:900) additive
  endif
  pass
end-policy
```

`additive` が肝心です。これが無いと、`set extcommunity rt` はルートが既に持っているルート ターゲットを置き換え、10.99.1.0/24 は
65000:900 だけを持って出ていきます。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf SVC 10.99.1.0/24 | include Extended
      Extended community: RT:65000:900

RP/0/RP0/CPU0:XR01#show bgp vrf SVC 10.99.1.0/24 | include Extended
      Extended community: RT:65000:900 RT:65000:999
```

1 つ目の出力は `additive` の無いポリシー、2 つ目はあるポリシーです。ポリシーの条件に合わない 10.99.2.0/24 は、VRF の RT
だけを持って出ていきます。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf SVC 10.99.2.0/24
BGP routing table entry for 10.99.2.0/24, Route Distinguisher: 10.255.0.1:900
...
      Extended community: RT:65000:999
```

エクスポートのポリシーはルートを止められません。コマンド リファレンスがそう書いており、ポリシーが通さなかったルートも、
VRF のルート ターゲットを付けて VRF から出ていきます。10.99.2.0/24 を顧客から隠しているのは、ポリシーではなく、どの顧客も
インポートしないそのルート ターゲットです。インポートのポリシーは 2 段のフィルタの 2 段目で、VRF のインポートするルート ターゲットに
既に一致したルートだけを見ます。

:::try
`additive` を外してみます。課題 M9-3 の後に行います。

1. XR01 で、ルート ポリシー SVC-EXPORT を `additive` の無い `set extcommunity rt (65000:900)` で入れ直し、
   コミットします。
2. XR01 で `show bgp vrf SVC 10.99.1.0/24` を、RT02 で `show ip bgp vpnv4 all 10.99.1.0` を、CEA2 で
   `ping 10.99.1.1 source Loopback10` を実行します。
3. `additive` を戻してコミットします。

結果の例: 10.99.1.0/24 は `RT:65000:900` だけを持って出ていき、RT02 のコピーも同じでした。ping は通り続けました。顧客は
65000:900 をインポートするので、顧客から見えるものは何も変わりません。壊れたのはプロバイダーの規約で、65000:999 に頼るものがあれば
そこで気づきます。`additive` を戻すと、ルートは再び 2 つのルート ターゲットを持ちました。
:::

### 2.4 1 つの PE の複数の VRF

共有サービスと顧客 A・B は、どれも XR01 に VRF を持っています。それらの間でも、ルート ターゲットは 2 つの PE の間と同じように
働きます(RFC 4364 の 4.3.6 節)。XR01 は、リモートの PE を介さずに、自分で 10.99.1.0/24 を SVC から CUST-A と CUST-B に
インポートします。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A 10.99.1.0/24
BGP routing table entry for 10.99.1.0/24, Route Distinguisher: 10.255.0.1:101
...
  Local
    172.16.91.2 from 0.0.0.0 (10.255.0.1)
      Origin incomplete, metric 0, localpref 100, weight 32768, valid, extranet, best, group-best, import-candidate, imported
      Received Path ID 0, Local Path ID 1, version 41
      Extended community: RT:65000:900 RT:65000:999
      Origin-AS validity: not-found
      Source AFI: VPNv4 Unicast, Source VRF: SVC, Source Route Distinguisher: 10.255.0.1:900
```

`extranet` と `Source VRF: SVC` が、同じルータの VRF SVC から取り込んだことを表します。ネクスト ホップは SVC のアドレスで、
重みはローカルのルートのものです。ルーティング テーブルは、ネクスト ホップがどこにあるかを示します(2.1 節の
`show route vrf CUST-B`)。共有サーバでは VRF SVC に、RT02 からのルートではグローバル テーブル(`vrf default`)にあり、
そのネクスト ホップは RT02 のループバックです。

### 2.5 VRF とグローバル テーブルの間

顧客 A の公開セグメントはインターネットに到達する必要があり、XR01 はインターネットを INET からグローバル テーブルで学習します。
IOS XR は、VRF のアドレス ファミリーの下の 2 つのコマンドで、VRF とグローバル テーブル(デフォルト VRF)の間で BGP のルートを
リークします。どちらもルート ポリシーが必須です。

- `import from default-vrf route-policy <名前>` は、グローバルのルートを VRF に取り込みます。ルートは VRF の CE に渡り、
  `advertise-as-vpn` があれば、VRF のルート ターゲットを付けた VPNv4 のルートとして他の PE にも渡ります。これが無いと、CEA1 は
  デフォルト ルートを持ち、RT02 の背後の CEA2 は持ちませんでした。
- `export to default-vrf route-policy <名前>` は、VRF のルートをグローバル テーブルにコピーし、そこから INET へ送れるように
  します。既定でエクスポートされるのは、XR01 が自分の CE から学習したルートだけです。サイト 2 の 198.51.100.128/25 のように
  別の PE から学習したルートには、`allow-imported-vpn` が必要です。

```console
RP/0/RP0/CPU0:XR01#show route vrf CUST-A 0.0.0.0/0
Routing entry for 0.0.0.0/0
  Known via "bgp 65000", distance 20, metric 0, candidate default path
  Tag 64500, type external
  ...
  Routing Descriptor Blocks
    192.0.2.2, from 192.0.2.2, BGP external
      Nexthop in Vrf: "default", Table: "default", IPv4 Unicast, Table Id: 0xe0000000

RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 198.51.100.128/25
BGP routing table entry for 198.51.100.128/25
...
  Advertised IPv4 Unicast paths to peers (in unique update groups):
    192.0.2.2
  65101
    10.255.0.12 (metric 30) from 10.255.0.21 (10.255.0.12)
      Received Label 23
      Origin IGP, metric 0, localpref 100, valid, internal, best, group-best, import-candidate, imported
      Extended community: RT:65000:101
      Originator: 10.255.0.12, Cluster list: 10.255.0.21
      Source AFI: VPNv4 Unicast, Source VRF: CUST-A, Source Route Distinguisher: 10.255.0.1:101
      Original Source AFI: VPNv4 Unicast, Original Source Route Distinguisher: 10.255.0.12:101
```

CUST-A のデフォルト ルートは、グローバル テーブルの INET を指しています。サイト 2 の公開セグメントは CUST-A からエクスポートされて
グローバルの BGP テーブルにあり、XR01 はそれを INET へ送ります。XR01 のグローバルの BGP テーブルにあるのは、インターネットの
ルートと顧客 A の 2 つの公開セグメントだけで、顧客の LAN(10.101.0.0/16)も顧客 B も入っていません。

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast
...
   Network            Next Hop            Metric LocPrf Weight Path
*> 0.0.0.0/0          192.0.2.2                              0 64500 i
*> 198.51.100.0/25    172.16.11.2              0             0 65101 i
*>i198.51.100.128/25  10.255.0.12              0    100      0 65101 i
*> 203.0.113.0/24     192.0.2.2                0             0 64500 i
```

スタティック ルートでも、1 つのプレフィックスについて同じことができます。`router static` → `vrf CUST-A` の中で、
`0.0.0.0/0 vrf default 192.0.2.2` のようなルートは、ネクスト ホップをグローバル テーブルに持ちます。BGP のリークと違い、VRF の BGP に
再配送しない限り、XR01 の CE にしか届きません。

### 2.6 パケットを追う

グローバル テーブルの中でも、サイト 2 のセグメントは VPN のネクスト ホップとラベルを持ったままです。INET から 198.51.100.129 へのパケットは、
XR01 で RT02 へのトランスポートのラベルと RT02 の VPN ラベルを付けられ、RT02 が CUST-A の中で届けます。

:::topo
nodes:
  INET: {at: [0, 1], kind: host}
  XR01: [1.3, 1]
  RT01: [2.6, 0.15]
  RT03: [2.6, 1.85]
  RT02: [3.9, 1]
  CEA2: {at: [5.2, 1], kind: host}
links:
  - [INET, XR01, "IP(グローバル)"]
  - [XR01, RT01, "16 | 23"]
  - [RT01, RT02, "23"]
  - [RT02, CEA2, "IP(CUST-A)"]
  - {a: XR01, b: RT03, style: dashed}
  - {a: RT03, b: RT02, style: dashed}
:::

```console
RP/0/RP0/CPU0:XR01#show cef 198.51.100.128/25
198.51.100.128/25, version 61, internal 0x5000001 0x40 (ptr 0xf7974e8) [1], 0x600 (0xf92fd58), 0xa08 (0xf3357b8)
...
   via 10.255.0.12/32, 5 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0xedbdd90 0x0]
    recursion-via-/32
    next hop 10.255.0.12/32 via 24002/0/21
     next hop 10.0.1.11/32 GigabitEthernet0/0/0/0 labels imposed {16 23}

INET#traceroute 198.51.100.129 source Loopback10 numeric timeout 1 probe 1
  1 192.0.2.1 4 msec
  2 10.0.1.11 [MPLS: Labels 16/23 Exp 0] 2 msec
  3 172.16.12.1 [MPLS: Label 23 Exp 0] 1 msec
  4 172.16.12.2 2 msec
```

16 は RT02 のループバックに対する RT01 の LDP のラベルで、23 は 198.51.100.128/25 に対する RT02 の VPN ラベルです。RT02 が次のルータ
なので RT01 は上のラベルを外し、RT02(ホップ 3)は VPN ラベルだけを受け取ります。グローバル テーブルのパケットが、XR01 で
VPN のラベルを付けられて CUST-A に入っていく、というのがこの経路の要です。

逆の方向、CEA2 から INET へは、RT02 がいちばん下に XR01 の集約のラベル 24009 を付けてパケットを XR01 へ送ります。XR01 は
CUST-A で宛先を引き、ネクスト ホップがグローバル テーブルにあるデフォルト ルートを見つけて、パケットを INET へ送ります。

```console
CEA2#traceroute 203.0.113.10 source Loopback11 numeric timeout 1 probe 1
  1 172.16.12.1 [AS 64500] 0 msec
  2 10.0.12.11 [AS 64500] [MPLS: Labels 22/24009 Exp 0] 2 msec
  3 10.0.1.1 [AS 64500] 3 msec
  4 192.0.2.2 [AS 64500] 2 msec
```

24009 は CE から学んだルートのラベルではないので、XR01 は VRF のテーブルで宛先を引き直します(付録 1 節)。

:::try
`advertise-as-vpn` を外してみます。課題 M9-4 の後に行います。

1. XR01 の `vrf CUST-A` → `address-family ipv4 unicast` の下で、`import from default-vrf` の行を `advertise-as-vpn` 無しで
   入れ直してコミットします。
2. XR01 で `show bgp vrf CUST-A 0.0.0.0/0` を、RT02 で `show ip route vrf CUST-A 0.0.0.0` を、CEA1 と CEA2 で
   `show ip route 0.0.0.0` を、CEA2 で `ping 203.0.113.10 source Loopback11` を実行します。
3. `advertise-as-vpn` を戻してコミットします。

結果の例: XR01 は、デフォルト ルートを自分の CE にだけアドバタイズしていると表示しました(`Advertised to CE peers` があり、
`PE peers` が無い)。RT02 と CEA2 からはそれが消え(`% Network not in table`)、CEA1 には残り、CEA2 からの ping は失敗しました。
キーワードを戻してから 1 分以内に、CEA2 は再びデフォルト ルートを持ち、ping は通りました。
:::

## 3. IOS XR で組む

### 3.1 共有サービス

SVC を XR01 に収容し、10.99.1.0/24 にだけ顧客向けの荷札を足す設定です。

:::config fold XR01 — 共有サービスの VRF と、1 つのルートにだけ足す荷札
interface GigabitEthernet0/0/0/4              ## SVC へのインターフェイス
 vrf SVC
 ipv4 address 172.16.91.1 255.255.255.0
!
route-policy SVC-EXPORT                       ## 輸出のポリシー
  if destination in (10.99.1.0/24) then
    set extcommunity rt (65000:900) additive  ## additive で、VRF の RT(999)に 900 を足す
  endif
  pass
end-policy
!
vrf SVC
 address-family ipv4 unicast
  import route-target                         ## 両方の顧客を取り込む(戻りの経路)
   65000:101
   65000:102
  !
  export route-policy SVC-EXPORT
  export route-target                         ## すべてのルートに付ける RT
   65000:999
  !
 !
!
router static
 vrf SVC
  address-family ipv4 unicast                 ## SVC はルーティング プロトコルを動かさない
   10.99.1.0/24 172.16.91.2
   10.99.2.0/24 172.16.91.2
  !
 !
!
router bgp 65000
 vrf SVC
  rd 10.255.0.1:900
  address-family ipv4 unicast
   redistribute static                        ## 静的経路を VRF の BGP に入れて、VPNv4 に出す
  !
 !
!
:::

### 3.2 インターネット接続

INET とグローバル テーブルで eBGP を張り、CUST-A とグローバル テーブルの間でルートをリークする設定です。

:::config fold XR01 — インターネットのルートを VRF へ、公開セグメントをインターネットへ
interface GigabitEthernet0/0/0/5              ## INET へのインターフェイス(グローバル テーブル)
 ipv4 address 192.0.2.1 255.255.255.0
!
route-policy TO-INTERNET                      ## INET へ送るのは公開セグメントだけ
  if destination in (198.51.100.0/25, 198.51.100.128/25) then
    pass
  endif
end-policy
!
route-policy DEFAULT-ONLY                     ## VRF へ取り込むのはデフォルト ルートだけ
  if destination in (0.0.0.0/0) then
    pass
  endif
end-policy
!
route-policy CUST-A-PUBLIC                    ## グローバルへ書き出すのは公開セグメントだけ
  if destination in (198.51.100.0/25, 198.51.100.128/25) then
    pass
  endif
end-policy
!
vrf CUST-A
 address-family ipv4 unicast
  import from default-vrf route-policy DEFAULT-ONLY advertise-as-vpn     ## 他の PE(RT02)にも配る
  export to default-vrf route-policy CUST-A-PUBLIC allow-imported-vpn    ## RT02 から学んだルートも書き出す
 !
!
router bgp 65000
 address-family ipv4 unicast                  ## グローバルの IPv4 ユニキャスト
 !
 neighbor 192.0.2.2                           ## INET との eBGP
  remote-as 64500
  address-family ipv4 unicast
   route-policy PASS in
   route-policy TO-INTERNET out
  !
 !
!
:::

### 3.3 スタティックでの受け渡し

1 つのプレフィックスだけなら、VRF のスタティック ルートのネクスト ホップをグローバル テーブルに置く方法もあります。

:::config XR01 — VRF のデフォルト ルートを、グローバル テーブルの INET へ
router static
 vrf CUST-A
  address-family ipv4 unicast
   0.0.0.0/0 vrf default 192.0.2.2            ## ネクスト ホップはグローバル テーブル(vrf default)で引く
  !
 !
!
:::

この形では、デフォルト ルートは XR01 の CUST-A のルーティング テーブルに入るだけで、VRF の BGP に再配送しない限り、RT02 の
背後のサイトには届きません。戻りの経路(公開セグメントをグローバル テーブルへ)も、別に用意する必要があります。

## 実践

ラボ **XRT-09** で課題 M9-3 と M9-4 に取り組みます。課題 M9-2 を終えた状態から始めます。

<p class="tolab"><a href="/_learn?id=XRT-09">ワークスペースでラボ XRT-09 を開く</a> — <a href="95-m9-practice-3.html">課題 M9-3、M9-4</a></p>

:::note
出典は単元の各ページと同じです(ページ「L3VPN の仕組み」の末尾)。このページの論点は、RFC 4364 の 4.3.5 節・4.3.6 節、
Cisco 8000 と NCS 5500 の BGP のコマンド リファレンス(`export route-policy`)、ASR 9000 の Routing Configuration Guide
(IOS XR 24.x。`advertise-as-vpn` と `allow-imported-vpn` による VRF の動的なルートのリーク、VRF のインポートとエクスポートの
ルーティング ポリシー、別の VRF へのスタティック ルート)、TAC 文書「Configure Route Leak between GRT and VRF with IOS XR」によります。
次の項目は、ラボ XRT-09 とその PoC での実測によるものです。`additive` の無いときに置き換わるルート ターゲット、ポリシーが通さない
ルートのエクスポート、同じ PE の VRF どうしの取り込み、重なるアドレスを共有サービスが区別できないこと、リーク、スタティックでの
受け渡し、ラベル。
:::
