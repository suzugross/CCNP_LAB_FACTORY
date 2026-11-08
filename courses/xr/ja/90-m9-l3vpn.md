# M9 — L3VPN の仕組み

この単元では、プロバイダーのコアの上に、顧客ごとのプライベートなネットワークを作ります。MPLS のレイヤ 3 VPN(L3VPN)です。
CCNP Service Provider のブループリントの 4.3 にあたります。1 つのプロバイダーの中の L3VPN(4.3.a)と、共有サービス、つまり
エクストラネットとインターネット接続(4.3.b)です。プロバイダーの間の VPN(4.1.b)と CSC(4.1.c)は付録で説明します。
単元は 3 つのページと付録に分かれています。

| ページ | 中身 | 課題 |
|---|---|---|
| このページ | L3VPN で何が嬉しいか、1 つのパケットを 1 ホップずつ追う仕組み、IOS XR での組み方 | M9-1 |
| ルート リフレクタと同じ AS のサイト | PE どうしを 1 か所で結ぶ、同じ AS 番号のサイトをつなぐ | M9-2 |
| 共有サービスとインターネット | 顧客を分けたまま共有のサーバを見せる、VPN からインターネットへ出す | M9-3、M9-4 |
| 付録 | ラベルの割り当て方、プロバイダーの間の VPN、コマンドの対応 | — |

章 C0「サービスを並べて見る」では、L3VPN をほかのサービスと並べて、外側のラベル(道)と内側のラベル(入れ物)を見ました。
この単元は L3VPN だけを、もう一段深く見ます。

ラボは XRT-09 です。コアはラボ XRT-07 と同じで、XR01 と RT02 がプロバイダー エッジ(PE)、RT01 と RT03 がコアのルータ(P)で、
IS-IS と LDP が動いています。新しいのは XR02 で、VPN のルートのためのルート リフレクタです。

:::topo
nodes:
  CEA1: {at: [0, 0], label: "CEA1 (A のサイト 1)"}
  CEB1: {at: [0, 0.9], label: "CEB1 (B のサイト 1)"}
  SVC: {at: [0, 1.8], label: "SVC (共有)"}
  INET: {at: [1.6, -0.8], label: "INET (インターネット)"}
  XR01: {at: [1.6, 0.9], label: "XR01 (PE)"}
  RT01: {at: [3.2, 0.2], label: "RT01 (P)"}
  RT03: {at: [3.2, 1.6], label: "RT03 (P)"}
  XR02: {at: [3.2, 2.7], label: "XR02 (RR)"}
  RT02: {at: [4.8, 0.9], label: "RT02 (PE)"}
  CEA2: {at: [6.4, 0.4], label: "CEA2 (A のサイト 2)"}
  CEB2: {at: [6.4, 1.4], label: "CEB2 (B のサイト 2)"}
links:
  - [CEA1, XR01, "CUST-A"]
  - [CEB1, XR01, "CUST-B"]
  - [SVC, XR01, "SVC"]
  - [INET, XR01, "global"]
  - [XR01, RT01, "PRIMARY"]
  - [XR01, RT03, "BACKUP"]
  - [RT01, RT02, "CORE-A"]
  - [RT03, RT02, "CORE-B"]
  - [RT03, XR02, "RR-LINK"]
  - [RT02, CEA2, "CUST-A"]
  - [RT02, CEB2, "CUST-B"]
frames:
  - {label: "AS 65000 (IS-IS CORE、LDP)", nodes: [XR01, RT01, RT03, RT02, XR02]}
:::

顧客 A は 2 つのサイトを持ち、それぞれの PE の背後にあって、どちらも AS 65101 です。顧客 B も 2 つのサイトを持ち、AS は 65201 と
65202 です。SVC にはプロバイダーの共有サーバがあり、INET はインターネットの役です(どちらもページ「共有サービスと
インターネット」)。ルート リフレクタ XR02 は RT03 の先にぶら下がり、どの顧客のパケットの経路にも入りません。

## 1. 何が嬉しいのか

### 1.1 困りごと: 顧客ごとのネットワークを、1 つのコアで

顧客 A は 2 つのサイトを持ち、その間をつなぎたいと考えています。顧客 B も同じです。どちらの顧客も、社内のアドレスを
自分で決めています。10.0.0.0/8 のようなプライベート アドレスは誰でも使えるので、別の顧客と同じアドレスを使っていることも
珍しくありません。

プロバイダーには、次の 3 つが求められます。

- **分ける**: 顧客 A のパケットが顧客 B のサイトに届いてはならず、A の経路が B に見えてもいけません。
- **重なってよい**: 2 つの顧客が同じアドレスを使っていても、それぞれのパケットを自分のサイトへ届けます。
- **増やせる**: 顧客とサイトが増えても、触る機器が少なく、コアのルータの仕事が増えないようにします。

### 1.2 それ以前の手

L3VPN の前には、主に 2 つの手がありました。

- **サイトの間に回線を引く**: プロバイダーは専用線や、フレーム リレー・ATM の仮想回線を売り、ルーティングは顧客が自分の
  ルータで行います。プロバイダーは顧客のアドレスを見ないので、分けることも重なりも問題になりません。ところが、サイトを
  すべて直接つなぐには、サイトの数を N として N(N−1)/2 本の回線が要り(RFC 4110 の 1.3.3 節)、サイトを 1 つ足すたびに、
  既存のサイトへの回線を足すことになります。
- **プロバイダーのルータが顧客の経路を持つ**: プロバイダーのルータが顧客の経路を学習してルーティングすれば、サイトを足すのは
  1 か所で済みます。ところが、ルーティング テーブルが 1 つなら、同じアドレスを 2 つは持てません。分けるには、顧客ごとに
  フィルタを書き続けるか、顧客ごとに専用のルータを置くことになります。コアのすべてのルータが、すべての顧客の経路を持つことにも
  なります。

### 1.3 L3VPN の答え

L3VPN は、2 つ目の手(プロバイダーが顧客の経路を持つ)から困りごとを取り除いたものです。RFC 4364 はこれを
「ピア モデル」と呼び、CE どうしはルーティングで向き合わない、と書いています(1 節)。

| 困りごと | L3VPN の答え | 節 |
|---|---|---|
| 顧客を分けたい | PE が顧客ごとに別のルーティング テーブル(VRF)を持つ | 2.1 |
| 同じアドレスを BGP の中で区別したい | 経路の前に番号(RD)を付ける | 2.2 |
| どの経路をどの VRF に入れるかを決めたい | 経路に荷札(RT)を付け、荷札で取り込む | 2.3 |
| サイトを足すたびに多くの機器を触りたくない | PE どうしが BGP で経路を配る(VPNv4)。触るのはサイトをつなぐ PE だけ | 2.4 |
| コアに顧客の経路を持たせたくない | コアはラベルだけで運ぶ(ラベル 2 枚) | 2.5 |

## 2. 仕組み: 1 つのパケットを 1 ホップずつ

### 2.1 PE の中の別のテーブル: VRF

PE は、グローバルのルーティング テーブルとは別に、顧客ごとのルーティング テーブルを持ちます。これが **VRF**(VPN routing and
forwarding instance)です(RFC 4364 の 3 節)。顧客のインターフェイスを VRF に入れると、そのインターフェイスから入った
パケットは、その VRF のテーブルで宛先を引かれます。

XR01 では、CEA1 につながるインターフェイスが VRF CUST-A に、CEB1 につながるインターフェイスが VRF CUST-B に入っています。
CUST-A のテーブルにあるのは、顧客 A の経路だけです(4 つの課題を終えた後のもので、顧客 A のサイトの行だけを抜き出しています)。

```console
RP/0/RP0/CPU0:XR01#show route vrf CUST-A
...
B    10.101.1.0/24 [20/0] via 172.16.11.2, 00:02:33
B    10.101.2.0/24 [200/0] via 10.255.0.12 (nexthop in vrf default), 00:02:33
C    172.16.11.0/24 is directly connected, 00:02:51, GigabitEthernet0/0/0/2
L    172.16.11.1/32 is directly connected, 00:02:51, GigabitEthernet0/0/0/2
```

10.101.1.0/24 は CEA1 から eBGP で学んだサイト 1 の経路、10.101.2.0/24 はサイト 2 の経路で、ネクスト ホップは RT02 の
ループバック 10.255.0.12 です。`nexthop in vrf default` は、そのネクスト ホップをグローバル テーブルで引くことを表します。
顧客の経路は VRF に、そこへ行く道(RT02 のループバック)はグローバル テーブルにある、という 2 段の構えが、2.5 節の
ラベル 2 枚になります。

顧客 B の経路は CUST-A にありません。XR01 のグローバル テーブルにも、顧客の経路はありません。

```console
RP/0/RP0/CPU0:XR01#show route 10.101.2.0/24
% Network not in table
```

### 2.2 経路に番号を付ける: RD

PE どうしは、すべての顧客の経路を 1 つの BGP で配ります。2 つの顧客が同じ 10.101.2.0/24 を使っていると、BGP の中では
1 つのプレフィックスの 2 本の経路になり、どちらか 1 本しか選ばれません。

そこで PE は、VRF の経路を BGP に出すとき、
その前に 8 バイトの**ルート識別子**(RD)を付けます。RD と IPv4 のアドレスを合わせた 12 バイトが VPN-IPv4 のアドレスで、
RFC 4364 の 4.1 節が定義しています。BGP の中では、RD が違えば別のプレフィックスです。

RD の書き方にはいくつかの形があり(4.2 節)、「AS 番号:番号」か「IP アドレス:番号」がよく使われます。ラボは
「PE のループバック:番号」で、XR01 の CUST-A は 10.255.0.1:101、RT02 の CUST-A は 10.255.0.12:101 です。RFC は、RD は
同じプレフィックスに別の経路を作るためだけのもので、経路の出どころも、どの VPN に配るかも表さない、と書いています
(4.1 節)。どの VRF が経路を取り込むかは、RD では決まりません(2.3 節)。

顧客 B のサイト 2(CEB2)にも、顧客 A のサイト 2 と同じ 10.101.2.0/24 を置いてみます(ループバックを足して BGP で
アドバタイズします。足し方と消し方は下の「やってみる」にあります)。ルート リフレクタ XR02 は、2 本を RD で分けて持ちます。

```console
RP/0/RP0/CPU0:XR02#show bgp vpnv4 unicast | include "Route Distinguisher|10.101.2.0"
...
Route Distinguisher: 10.255.0.12:101
*>i10.101.2.0/24      10.255.0.12              0    100      0 65101 i
Route Distinguisher: 10.255.0.12:102
*>i10.101.2.0/24      10.255.0.12              0    100      0 65202 i
```

XR01 は、顧客 A の方を CUST-A に、顧客 B の方を CUST-B に取り込みます。RT02 は 2 本に別の VPN のラベル(22 と 26)を
付けているので、同じ宛先へのパケットが、顧客ごとに別のサイトに着きます。

```console
RP/0/RP0/CPU0:XR01#show cef vrf CUST-A 10.101.2.0/24
...
     next hop 10.0.1.11/32 GigabitEthernet0/0/0/0 labels imposed {16 22}
RP/0/RP0/CPU0:XR01#show cef vrf CUST-B 10.101.2.0/24
...
     next hop 10.0.1.11/32 GigabitEthernet0/0/0/0 labels imposed {16 26}

CEA1#traceroute 10.101.2.1 source Loopback10 numeric timeout 1 probe 1
  1 172.16.11.1 [AS 64500] 7 msec
  2 10.0.1.11 [AS 64500] [MPLS: Labels 16/22 Exp 0] 10 msec
  3 172.16.12.1 [AS 64500] [MPLS: Label 22 Exp 0] 10 msec
  4 172.16.12.2 [AS 64500] 9 msec
CEB1#traceroute 10.101.2.1 source Loopback10 numeric timeout 1 probe 1
  1 172.16.21.1 6 msec
  2 10.0.1.11 [MPLS: Labels 16/26 Exp 0] 8 msec
  3 172.16.22.1 [MPLS: Label 26 Exp 0] 9 msec
  4 172.16.22.2 10 msec
```

最後のホップは、顧客 A では CEA2(172.16.12.2)、顧客 B では CEB2(172.16.22.2)です。コアの RT01 から見ると、どちらも
「RT02 へ、16」のパケットで、違うのは内側のラベルだけです。

:::try
同じアドレスを 2 つの顧客に置いてみます。課題 M9-2 の後に行い、最後に必ず元に戻します(CEB2 は据え付けのルータです)。

1. CEB2 で、`interface Loopback11` に `ip address 10.101.2.1 255.255.255.0` を設定し、`router bgp 65202` →
   `address-family ipv4` の下に `network 10.101.2.0 mask 255.255.255.0` を足します。
2. 1 分待ってから、XR02 で `show bgp vpnv4 unicast` を、XR01 で `show cef vrf CUST-A 10.101.2.0/24` と
   `show cef vrf CUST-B 10.101.2.0/24` を実行します。CEA1 と CEB1 で、それぞれ
   `traceroute 10.101.2.1 source Loopback10 numeric` を実行します。
3. CEB2 の `network` の行と Loopback11 を消します。

結果の例: 1 分以内に、XR02 は 10.101.2.0/24 を RD 10.255.0.12:101 と 10.255.0.12:102 の 2 本で持ちました。XR01 は
CUST-A では 22、CUST-B では 26 を積み、CEA1 の traceroute は CEA2 に、CEB1 の traceroute は CEB2 に着きました。消してから
30 秒以内に、CUST-B の 10.101.2.0/24 は無くなりました。
:::

### 2.3 経路に荷札を付ける: RT

経路をどの VRF に入れるかは、**ルート ターゲット**(RT)が決めます。RT は BGP の拡張コミュニティで、PE は VRF の経路を
BGP に出すとき、その VRF の**輸出**の RT を付けます。受け取った PE は、経路の RT のどれかが VRF の**輸入**の RT の
どれかと一致すれば、その VRF に経路を取り込みます(RFC 4364 の 4.3.1 節)。

```console
RP/0/RP0/CPU0:XR01#show vrf CUST-A detail
VRF CUST-A; RD 10.255.0.1:101; VPN ID not set
VRF mode: Regular
Description not set
Interfaces:
  GigabitEthernet0/0/0/2
Address family IPV4 Unicast
  Import VPN route-target communities:
    RT:65000:101
    RT:65000:900
  Export VPN route-target communities:
    RT:65000:101
  No import route policy
  No export route policy
...
```

CUST-A は、自分の経路に 65000:101 を付けて出し、65000:101 の付いた経路を取り込みます。RT02 の CUST-A も同じ値なので、
2 つのサイトの経路が互いの VRF に入ります。65000:900 は共有サービスのための荷札です(ページ「共有サービスと
インターネット」)。

RD と RT は、どちらも「:」で区切った同じ見た目の値ですが、役目は別です。

| | RD | RT |
|---|---|---|
| 何のため | 同じアドレスの経路を、BGP の中で区別する | 経路をどの VRF に入れるかを決める |
| どこにあるか | 経路のアドレスの一部(VPN-IPv4 のアドレスの頭) | 経路の属性(拡張コミュニティ) |
| 1 つの経路に | 1 つ | いくつでも |
| ラボの決め方 | PE と VRF ごと(10.255.0.1:101、10.255.0.12:101) | 顧客ごと(A は 65000:101、B は 65000:102) |

PE は、自分のどの VRF にも取り込まない経路を、受け取ったときに捨てます(RFC 4364 の 4.3.2 節)。顧客がつながっていない PE
は、その顧客の経路を持ちません(3.4 節)。

### 2.4 PE どうしで配る: VPNv4 と VPN のラベル

PE どうしは、ループバックの間の iBGP で、VPN-IPv4 のアドレス ファミリー(VPNv4)を使って経路を配ります。VPNv4 の経路は、
RD つきのプレフィックス、RT、ネクスト ホップ、そして **VPN のラベル**を運びます。XR01 が受け取ったサイト 2 の経路です。

```console
RP/0/RP0/CPU0:XR01#show bgp vpnv4 unicast rd 10.255.0.12:101 10.101.2.0/24
BGP routing table entry for 10.101.2.0/24, Route Distinguisher: 10.255.0.12:101
...
Paths: (1 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
  65101
    10.255.0.12 (metric 30) from 10.255.0.21 (10.255.0.12)
      Received Label 22
      Origin IGP, metric 0, localpref 100, valid, internal, best, group-best, import-candidate, not-in-vrf
      Received Path ID 0, Local Path ID 1, version 8
      Extended community: RT:65000:101
      Originator: 10.255.0.12, Cluster list: 10.255.0.21
```

- RD 10.255.0.12:101 は RT02 の CUST-A の RD、ネクスト ホップ 10.255.0.12 は RT02 のループバックです。
- `Received Label 22` が VPN のラベルで、RT02 が選んで経路と一緒に送ってきたものです。
- `RT:65000:101` が顧客 A の荷札です。
- `from 10.255.0.21` と `Cluster list` は、ルート リフレクタ XR02 から届いたことを表します(次のページ)。
- `not-in-vrf` は、受け取ったままのコピーであることを表します。XR01 はこれを自分の RD 10.255.0.1:101 の下にコピーして
  CUST-A に入れ、`show bgp vrf CUST-A` が並べるのはそちらです。

VPN のラベルは、経路を出した PE、つまりパケットの出口になる PE が選びます(RFC 4364 の 4.3.2 節)。RT02 のラベルの表を見ると、
22 が何を指しているかが分かります(VPN のラベルの行だけを抜き出しています)。

```console
RT02#show mpls forwarding-table
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
...
22         No Label   10.101.2.0/24[V] 5230          Et0/2      172.16.12.2
23         No Label   198.51.100.128/25[V]   \
                                       2280          Et0/2      172.16.12.2
24         No Label   10.102.2.0/24[V] 4788          Et1/0      172.16.22.2
```

22 は CUST-A の 10.101.2.0/24 です(`[V]` は VRF のプレフィックスの印)。RT02 は 22 で受けたパケットのラベルを外し、
宛先を引き直さずに CEA2 へ送ります。経路ごとにラベルを割り当てる方式で、IOS XR と IOS XE の既定です(付録 1 節)。
24 は顧客 B のサイト 2 の経路です。

### 2.5 パケットを追う: ラベル 2 枚

顧客 A のパケットを、CEA1(10.101.1.1)から CEA2(10.101.2.1)まで追います。

1. CEA1 は、パケットを XR01 へ送ります。ふつうの IP パケットです。
2. XR01 は、パケットが入ってきたインターフェイスから VRF CUST-A を選び、10.101.2.0/24 を見つけます。ネクスト ホップは
   RT02、VPN のラベルは 22 です。次に、グローバル テーブルで RT02 のループバックへの道を引きます。最短パスの次のホップは
   RT01 で、RT01 は LDP で「RT02 へはこのラベルで」と 16 を伝えています。XR01 は 22 の上に 16 を積み、RT01 へ送ります。
3. RT01 は、いちばん上の 16 だけを見ます。RT02 の 1 つ手前なので、16 を外して(PHP。M8)RT02 へ送ります。
4. RT02 は、残った 22 を見て、ラベルを外し、CEA2 へ送ります。

:::topo
nodes:
  CEA1: {at: [0, 1], kind: host}
  XR01: [1.3, 1]
  RT01: [2.6, 0.15]
  RT03: [2.6, 1.85]
  RT02: [3.9, 1]
  CEA2: {at: [5.2, 1], kind: host}
links:
  - [CEA1, XR01, "IP"]
  - [XR01, RT01, "16 | 22"]
  - [RT01, RT02, "22"]
  - [RT02, CEA2, "IP"]
  - {a: XR01, b: RT03, style: dashed}
  - {a: RT03, b: RT02, style: dashed}
:::

線の上の数字は、そのリンクを通るときに付いているラベルで、左がいちばん上です。XR01 の転送テーブルと、CML のリンクで
捕まえたパケット(行を短くしています)、CEA1 からの traceroute が、同じものを示します。

```console
RP/0/RP0/CPU0:XR01#show cef vrf CUST-A 10.101.2.0/24
10.101.2.0/24, version 7, internal 0x5000001 0x30 (ptr 0xf79a398) [1], 0x600 (0xf92f398), 0xa08 (0xf318218)
...
   via 10.255.0.12/32, 5 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0xeda0c10 0x0]
    recursion-via-/32
    next hop VRF - 'default', table - 0xe0000000
    next hop 10.255.0.12/32 via 24002/0/21
     next hop 10.0.1.11/32 GigabitEthernet0/0/0/0 labels imposed {16 22}

# XR01 → RT01 の線
MPLS (label 16, ttl 254) (label 22, [S], ttl 254) 10.101.1.1 > 10.101.2.1: ICMP echo request
# RT01 → RT02 の線
MPLS (label 22, [S], ttl 253) 10.101.1.1 > 10.101.2.1: ICMP echo request

CEA1#traceroute 10.101.2.1 source Loopback10 numeric timeout 1 probe 1
  1 172.16.11.1 [AS 64500] 4 msec
  2 10.0.1.11 [AS 64500] [MPLS: Labels 16/22 Exp 0] 1 msec
  3 172.16.12.1 [AS 64500] [MPLS: Label 22 Exp 0] 3 msec
  4 172.16.12.2 [AS 64500] 1 msec
```

`next hop VRF - 'default'` が、2.1 節の 2 段の構えです。VRF の経路のネクスト ホップ(RT02)を、グローバル テーブルで引いて
います。`[AS 64500]` は IOS の traceroute が CEA1 の BGP の表から添える AS 番号(インターネットの AS)で、ラベルとは関係
ありません。

戻りのパケット(CEA2 から CEA1)も、同じ形です。RT02 は、XR01 が CEA1 の経路に割り当てた VPN のラベル 24004 の上に、
XR01 のループバックへの RT01 のラベル 22 を積みます。RT01 は 22 を外さず、0 に替えて XR01 へ送ります。0 は explicit null
で、XR01 が M8 の課題で「外さずに 0 を付けて渡して」と頼んでいるからです(M8 の MPLS OAM と explicit null)。

:::topo
nodes:
  CEA2: {at: [0, 1], kind: host}
  RT02: [1.3, 1]
  RT01: [2.6, 0.15]
  RT03: [2.6, 1.85]
  XR01: [3.9, 1]
  CEA1: {at: [5.2, 1], kind: host}
links:
  - [CEA2, RT02, "IP"]
  - [RT02, RT01, "22 | 24004"]
  - [RT01, XR01, "0 | 24004"]
  - [XR01, CEA1, "IP"]
  - {a: RT02, b: RT03, style: dashed}
  - {a: RT03, b: XR01, style: dashed}
:::

```console
# RT02 → RT01 の線
MPLS (label 22, ttl 254) (label 24004, [S], ttl 254) 10.101.2.1 > 10.101.1.1: ICMP echo reply
# RT01 → XR01 の線
MPLS (label 0, ttl 253) (label 24004, [S], ttl 254) 10.101.2.1 > 10.101.1.1: ICMP echo reply
```

行きの 22 と帰りの 22 は、別のものです。行きの 22 は RT02 が CUST-A の経路に選んだ VPN のラベル、帰りの 22 は RT01 が
XR01 のループバックに選んだ LDP のラベルです。ラベルの番号は、それを選んだルータの中でだけ意味を持ちます。

### 2.6 押さえどころ

- **コアは顧客を知りません**。RT01 は顧客の経路も BGP も持たず、ラベルの表にあるのはループバックとリンクだけです。
  RFC 4364 も、P ルータは VPN ごとの経路の情報を一切持たなくてよい、と書いています(1.5 節)。

  ```console
  RT01#show ip route 10.101.2.1
  % Subnet not in table
  RT01#show ip bgp summary
  % BGP not active
  ```

- **外側のラベルは道、内側のラベルは出口の PE の入れ物**です。外側(16)は LDP が配り、RT02 まで運びます。内側(22)は
  RT02 が BGP で配り、RT02 の中で行き先を決めます。道を LDP から SR に替えても(M10)、内側は変わりません。
- **RD は区別、RT は行き先**です。RD は BGP の中で経路を一意にし、RT はどの VRF に入れるかを決めます。

## 3. IOS XR で組む

### 3.1 部品の置き場

部品はどの OS でも同じですが、IOS XR は置き場を分けます。IOS では RD と RT を `vrf definition` の下にまとめて書きます。

- **RT は VRF に属します**。`vrf <名前>` → `address-family ipv4 unicast` → `import route-target` と `export route-target` で、
  どちらも 1 行に 1 つのルート ターゲットを書くサブモードです。
- **インターフェイス**は `vrf <名前>` で VRF に入ります。
- **RD は BGP に属します**。`router bgp <AS>` → `vrf <名前>` → `rd` で、その VRF の CE のネイバーも同じ `vrf` の下に
  置きます。
- **PE どうし**は、BGP の最上位の `address-family vpnv4 unicast` と、ネイバーの下の同じアドレス ファミリーです。

顧客 A のサイト 1 を XR01 に収容する設定です。顧客 B も、値を変えて同じ形です。

:::config fold XR01 — 顧客 A のサイト 1 を VRF に収容する
vrf CUST-A                                    ## 入れ物。RT は VRF の下に書く
 address-family ipv4 unicast
  import route-target                         ## この荷札の付いた経路を取り込む
   65000:101
   65000:900                                  ## 共有サービスの荷札(ページ「共有サービスとインターネット」)
  !
  export route-target                         ## この VRF の経路に付ける荷札
   65000:101
  !
 !
!
interface GigabitEthernet0/0/0/2              ## CEA1 へのインターフェイス
 vrf CUST-A                                   ## 先に VRF に入れてから、アドレスを付ける
 ipv4 address 172.16.11.1 255.255.255.0
!
route-policy PASS                             ## eBGP はポリシーが無いと何も交換しない(M5)
  pass
end-policy
!
router bgp 65000
 bgp router-id 10.255.0.1
 address-family vpnv4 unicast                 ## 最上位の VPNv4。これが無いと下の 2 つが入らない(3.2 節)
 !
 neighbor 10.255.0.21                         ## ルート リフレクタ XR02 とだけ VPNv4 を交換する
  remote-as 65000
  update-source Loopback0
  address-family vpnv4 unicast
  !
 !
 vrf CUST-A
  rd 10.255.0.1:101                           ## RD は BGP の VRF の下(IOS は vrf definition の下)
  address-family ipv4 unicast                 ## RD が先に要る(3.2 節)
  !
  neighbor 172.16.11.2                        ## CEA1 との eBGP
   remote-as 65101
   address-family ipv4 unicast
    route-policy PASS in
    route-policy PASS out
   !
  !
 !
!
:::

同じことを、RT02 は IOS XE で次のように書いています(ラボの据え付けの設定から抜粋)。RD と RT が `vrf definition` に
まとまり、CE のネイバーは BGP の `address-family ipv4 vrf` の下です。

:::config RT02(IOS XE)— 顧客 A のサイト 2(据え付けの設定から抜粋)
vrf definition CUST-A
 rd 10.255.0.12:101                           ## IOS XE の RD は VRF の下
 address-family ipv4
  route-target export 65000:101
  route-target import 65000:101
  route-target import 65000:900
 exit-address-family
!
interface Ethernet0/2
 description CUST-A site 2 (CEA2)
 vrf forwarding CUST-A                        ## IOS XE は、VRF を変えるとアドレスが消える
 ip address 172.16.12.1 255.255.255.0
!
router bgp 65000
 neighbor 10.255.0.21 remote-as 65000
 neighbor 10.255.0.21 update-source Loopback0
 address-family ipv4
  no neighbor 10.255.0.21 activate            ## IPv4 のユニキャストは交換しない
 exit-address-family
 address-family vpnv4
  neighbor 10.255.0.21 activate
  neighbor 10.255.0.21 send-community extended   ## RT は拡張コミュニティ
 exit-address-family
 address-family ipv4 vrf CUST-A
  neighbor 172.16.12.2 remote-as 65101
  neighbor 172.16.12.2 activate
  neighbor 172.16.12.2 as-override             ## 次のページ
 exit-address-family
!
:::

:::note
NCS 5500 と ASR 9000 の L3VPN のコンフィギュレーション ガイド(リリース 7.11)は、インターフェイスの VRF を割り当てる・外す・変える前に、
その IPv4 と IPv6 のアドレスを外す必要があり、外さないと変更は拒否されると書いています。IOS XR 26.1.1(XRv 9000 と XRd の
どちらも)は、アドレスを付けたままの変更を受け付け、アドレスも残します。インターフェイスをグローバル テーブルから VRF へ、その逆へ、
または既にある別の VRF へ移すのは、数秒後には動きます。同じコミットで作った VRF へ移すと、隣と通信できないままになることが
あります。ガイドに従ってください。ラボ XRT-09 では顧客側のインターフェイスにアドレスが無いので、`vrf` と `ipv4 address` を
一緒に入れます。
:::

### 3.2 コミットの順序の検査

IOS XR は、コミットのときにこれらの部品の順序を検査します。BGP は、VPNv4 のネイバーや VRF のアドレス ファミリーを置く前に、最上位に
`address-family vpnv4 unicast` を必要とします。また、BGP の中の VRF のアドレス ファミリーには、先に RD が必要です。エラーは
次のとおりです。

```console
!!% 'BGP' detected the 'warning' condition 'The address family has not been initialized'
!!% 'BGP' detected the 'warning' condition 'The parent address family has not been initialized'
!!% 'BGP' detected the 'warning' condition 'The RD for the VRF must be present before an address family is activated'
```

1 つ目は VPNv4 のネイバーから、2 つ目は VRF のアドレス ファミリーから出たもので、どちらも最上位に VPNv4 のファミリーが無い状態です。
失敗したコミットは丸ごと取り消されるので、RD の無い VRF が何もアドバタイズしないまま残ることはありません。新しいガイドは `rd` を
`vrf <名前>` の直下にも書いており、IOS XR 26.1.1 はそこでも受け付けます。このページは、コマンド リファレンスの形どおり RD を BGP に
置きます。

### 3.3 CE とのセッション

PE はふつう、VRF の中で eBGP を使って CE から顧客のルートを学習します。単元 M5 のことはすべてそのまま当てはまります。IOS XR の
eBGP のネイバーは、両方向にルート ポリシーを持つまでルートを交換せず、VRF も例外ではありません。セッションは上がり、ルートは
捨てられます。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-B summary
...
Some configured eBGP neighbors (under default or non-default vrfs)
do not have both inbound and outbound policies configured for IPv4 Unicast
address family. These neighbors will default to sending and/or
receiving no routes and are marked with '!' in the output below.
Use the 'show bgp neighbor <nbr_address>' command for details.

Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
172.16.21.2       0 65201      27      33          113    0    0 00:19:49          0!

RP/0/RP0/CPU0:XR01#show bgp vrf CUST-B neighbors 172.16.21.2 | include "policy|accepted|denied"
  eBGP neighbor with no inbound or outbound policy; defaults to 'drop'
  0 accepted prefixes, 0 are bestpaths
  Exact no. of prefixes denied: 0
  Cumulative no. of prefixes denied: 1
    No policy: 1, Failed RT match: 0
```

入と出にポリシーがあれば、ルートは VRF の BGP テーブルとルーティング テーブルに入ります。`show route vrf CUST-A` はそれらを BGP の
ルートとして並べ、`show bgp vrf CUST-A` はテーブルの前に RD を表示します。

:::try
ポリシーが無いと CE とのセッションがどうなるかを見ます。課題 M9-1 の後に行います。

1. XR01 の `router bgp 65000` → `vrf CUST-B` → `neighbor 172.16.21.2` → `address-family ipv4 unicast` の下から、
   `route-policy` の 2 行を外してコミットします。
2. XR01 で `show bgp vrf CUST-B summary` と `show bgp vrf CUST-B neighbors 172.16.21.2` を、CEB1 で
   `show ip bgp summary` と `show ip route bgp` を実行します。
3. 2 行を戻してコミットし、同じコマンドをもう一度実行します。

結果の例: セッションは上がったままで、リセットもされませんでした(稼働時間は数え続けました)。XR01 は `0!` を表示して
CEB1 のルートを `No policy: 1` に数え、CEB1 の BGP のルートは消えました。CEB1 も何も受け取っていません(`State/PfxRcd 0`)。
行を戻してから 30 秒以内に、XR01 は再びルートを受け入れ、CEB1 にもルートが戻りました。
:::

### 3.4 ルート ターゲットによるふるい

PE は、自分が使える VPN のルートだけを保持します。ルート ターゲットがローカルの VRF のインポートするルート ターゲットのどれにも
一致しないルートは、ポリシーが無くても受信したときに捨てられ、ネイバーの詳細がそれを数えます。

```console
RP/0/RP0/CPU0:XR01#show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT|denied"
  Route refresh request: received 0, sent 2
  Exact no. of prefixes denied: 0
  Cumulative no. of prefixes denied: 2
    No policy: 0, Failed RT match: 2
```

ルートを捨てた PE が、後でそれを必要とすることがあります。新しい VRF を設定したとき、または PE がルートを持っていないインポートの
ルート ターゲットを足したとき、IOS XR はネイバーにルートを送り直すよう頼みます(BGP の**ルート リフレッシュ**)。VRF を
コミットしてから 5 秒以内に顧客 B のルートが届き、`show bgp vpnv4 unicast neighbors` がリフレッシュを数えます。

```console
RP/0/RP0/CPU0:XR01#show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT"
  Route refresh request: received 0, sent 3
    No policy: 0, Failed RT match: 2
```

これは、65000:102 を CUST-B のインポートするルート ターゲットに戻した直後です。VRF CUST-B を一から設定したときも同じで、
ルート リフレッシュが 1 回、顧客 B のルートは 5 秒以内に届きます。

:::try
XR01 がルートを捨て、もう一度求めるところを見ます。課題 M9-2 の後、課題 M9-3 の前に行います。課題 M9-3 からは VRF SVC も
65000:102 をインポートするので、XR01 はそのために顧客 B のルートを保持します。

1. XR01 で `show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT"` を実行します。
2. CUST-B のインポートするルート ターゲットから 65000:102 を外してコミットします。
   `show bgp vpnv4 unicast rd 10.255.0.12:102` を実行します。
3. `clear bgp vpnv4 unicast 10.255.0.21 soft in` を実行して XR02 にルートを送り直させ、それから手順 1 のコマンドを
   実行します。
4. 65000:102 を戻してコミットします。手順 1 のコマンドと `show bgp vrf CUST-B` を実行します。

結果の例: XR01 は 10.102.2.0/24 をすぐに捨て、RD 10.255.0.12:102 のテーブルは空になりました。ソフト リフレッシュの後、
ネイバーの詳細は `Failed RT match: 2` を表示し、送ったリフレッシュの要求は 0 から 2 になっていました。65000:102 を戻すと
カウンタは 3 になり、5 秒以内に 10.102.2.0/24 が再び CUST-B に入りました。CEB1 は CEB2 に到達できました。
:::

### 3.5 確かめる順番

止まったときは、下の段から順に確かめます(章 C0 の「組み立て順」の段 4 と同じ考え方です)。上の段の症状は、たいてい下の段の
誤りから来ます。

| 段 | 確かめること | XR01 で |
|---|---|---|
| 道 | 出口の PE のループバックへのラベルがある | `show mpls forwarding`(10.255.0.12/32 の行) |
| PE どうし | VPNv4 のセッションが上がり、ルートを受けている | `show bgp vpnv4 unicast summary` |
| 入れ物 | VRF の RT が正しい | `show vrf CUST-A detail` |
| 収容 | CE とのセッションが上がり、`!` が無い | `show bgp vrf CUST-A summary` |
| 経路 | 相手のサイトの経路が届き、VRF に入っている | `show bgp vpnv4 unicast rd <相手の RD>`、`show bgp vrf CUST-A` |
| 転送 | 2 枚のラベルを積んでいる | `show cef vrf CUST-A <宛先>`(`labels imposed`) |
| 端から端 | 顧客のサイトどうしで届く | CE から `ping`・`traceroute`(送信元は LAN のアドレス) |

## 実践

ラボ **XRT-09** で課題 M9-1 に取り組みます。XR01 は IOS XRv 9000 なので、ラボの構築に約 10 分かかります。

<p class="tolab"><a href="/_learn?id=XRT-09">ワークスペースでラボ XRT-09 を開く</a> — <a href="91-m9-practice.html">課題 M9-1</a></p>

:::note
このページの出力は、IOS XRv 9000 26.1.1(XR01)、IOS XRd 26.1.1(XR02)、IOL 上の IOS XE 17.15(他のルータ)で取得しました。
出典: RFC 4364(1 節・1.5 節・3 節・4.1〜4.3 節)と RFC 4110(1.3.3 節)。Cisco 8000(累積版、2026 年)と NCS 5500 の BGP のコマンド
リファレンス(ルート識別子と `rd auto`、`retain route-target`、`as-override`、`allowas-in`、`site-of-origin`、`label mode`、
`export route-policy`)。ASR 9000 の Routing Configuration Guide、IOS XR 24.x(2026 年。アドレス ファミリー、ルート リフレクタと
`retain route-target`、新しい VRF のためのルート リフレッシュ、`advertise-as-vpn` と `allow-imported-vpn` による VRF の動的なルートの
リーク、VRF のインポートとエクスポートのルーティング ポリシー、別の VRF へのスタティック ルート)。NCS 5500 と Cisco 8000 の L3VPN の
コンフィギュレーション ガイドと ASR 9000 の MPLS L3VPN のガイド、リリース 7.11(インターフェイスの VRF、Inter-AS のオプション B、CSC)。
Cisco 8000 のガイド「BGP Route Distinguisher」。Cisco の TAC 文書「Cisco IOS-XR BGP with MPLS Designs」(2021 年)と「Configure Route
Leak between GRT and VRF with IOS XR」。IOS XRd のデータ シート。いずれも 2026 年 10〜11 月に確認。次の項目は、ラボ XRT-09 とその PoC での
実測によるものです。コミットのエラー、VRF の変更で残るインターフェイスのアドレス、捨てられたルートとそのカウンタ、ルート リフレッシュ、
ラベルと線の上のパケット(CML のリンクのキャプチャ)、重なるアドレスの扱い。
:::
