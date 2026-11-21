# M6 追補 — 予備の道を配る: 追加パスと PIC

前のページで、BGP の運用機能の部品を見渡しました。このページはそのうち、主の出口が落ちた時の途切れを短くする 2 つを
扱います。追加パス(ADD-PATH)で予備の経路を前もって配り、PIC(Prefix Independent Convergence)でその予備を
フォワーディング テーブルに入れておきます。

ブループリントの 2.4.g(追加パス)と 2.4.h(PIC)にあたり、ラボ XRT-17 の課題 M6-5 と M6-6 で使います。ルート ポリシーと
next-hop-self は M6 の本編で扱いました。GTSM と TCP-AO は「セッションを守る」のページ、経路数の上限・ダンプニング・集約は
「受け取りすぎない」のページで扱います。

## 1. 何が嬉しいのか

### 1.1 困りごと: 出口は 2 つあるのに、PE1 は 1 つしか知らない

XRT-17 のプロバイダー(AS 65000)は 5 台です。PE1 は顧客の CE1(AS 65001)をつなぐ入口の PE、PE2 と PE3 は AS 65100 への
2 つの出口、P1 は BGP を動かさないコア、RR1 は道の外にいる専用のルート リフレクタです。コアの線では IS-IS(インスタンス
CORE、レベル 2)と LDP が動いています。

PE1〜PE3 は RR1 のクライアントで、Loopback0 の間で iBGP を張り、どの PE も next-hop-self です。AS 65100 の X1 と X2 は、
どちらも T の 203.0.113.0/24 を広告します。PE2 は X1 から学んだ経路のローカル プリファレンスを 200 にするので、PE2 が
主の出口、PE3 が予備の出口です。

:::topo
nodes:
  CE1: {at: [0, 1], kind: host, label: "CE1 (AS 65001)"}
  PE1: {at: [2.2, 1], label: "PE1 (入口・XRv 9000)"}
  P1: {at: [4.2, 1], label: "P1 (BGP なし)"}
  RR1: {at: [4.2, 2.5], label: "RR1 (ルート リフレクタ)"}
  PE2: {at: [6.2, 0], label: "PE2 (主の出口)"}
  PE3: {at: [6.2, 2], label: "PE3 (予備の出口)"}
  X1: {at: [8.2, 0], label: "X1"}
  X2: {at: [8.2, 2], label: "X2"}
  T: {at: [9.9, 1], kind: host, label: "T 203.0.113.1"}
links:
  - {a: CE1, b: PE1, label: "172.16.1.0/24"}
  - {a: PE1, b: P1, label: "10.0.1.0/24"}
  - {a: P1, b: PE2, label: "10.0.2.0/24"}
  - {a: P1, b: PE3, label: "10.0.3.0/24"}
  - {a: P1, b: RR1, label: "10.0.21.0/24"}
  - {a: PE2, b: X1, label: "172.16.2.0/24"}
  - {a: PE3, b: X2, label: "172.16.3.0/24"}
  - {a: X1, b: T}
  - {a: X2, b: T}
  - {a: X1, b: X2}
frames:
  - {label: "AS 65000", nodes: [PE1, P1, RR1, PE2, PE3]}
  - {label: "AS 65100", nodes: [X1, X2, T]}
:::

T のデフォルト ルートは X2 を優先するので、T から CE1 への帰りは X2 → PE3 を通ります。このページで追うのは、CE1 から T への
行きの向きだけです。

困るのは PE3 です。PE3 は 203.0.113.0/24 の経路を 2 本知っています。RR1 から来た PE2 経由の iBGP の経路(ローカル
プリファレンス 200)と、X2 から直接学んだ eBGP の経路(100)で、最良は PE2 経由のほうです。BGP が広告するのは最良の経路
だけで、iBGP で学んだ最良は iBGP の相手へ出しません。そのため PE3 は、この宛先について RR1 へ何も送りません。

```console
RP/0/RP0/CPU0:PE3#show bgp 203.0.113.0/24
BGP routing table entry for 203.0.113.0/24
...
Paths: (2 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
  65100
    10.255.0.2 (metric 20) from 10.255.0.21 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
...
  Path #2: Received by speaker 0
  Not advertised to any peer
  65100
    172.16.3.1 from 172.16.3.1 (10.100.255.2)
      Origin IGP, metric 11, localpref 100, valid, external
...
RP/0/RP0/CPU0:RR1#show bgp 203.0.113.0/24
...
Paths: (1 available, best #1)
...
  65100, (Received from a RR-client)
    10.255.0.2 (metric 20) from 10.255.0.2 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
RP/0/RP0/CPU0:PE1#show bgp 203.0.113.0/24
...
Paths: (1 available, best #1)
...
  65100
    10.255.0.2 (metric 20) from 10.255.0.21 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
```

PE3 の 2 本は、どちらも `Not advertised to any peer` です。RR1 と PE1 は、PE2 経由の 1 本しか知りません。予備の出口は、
予備を持っていることを誰にも伝えていません。

### 1.2 それ以前の手: BGP が選び直すのを待つ

何も足さずに PE2 がコアから消えると(P1 の PE2 向けのインターフェイスが止まると)、IS-IS が PE2 のループバック
10.255.0.2/32 を消します。BGP のスピーカーはどれも、経路の next-hop に RIB の中で届くかを見張っています(next-hop の
追跡)。10.255.0.2 に届かなくなると、PE3 は PE2 経由の経路を捨て、X2 からの経路が最良になって RR1 へ広告します。

RR1 がその経路を PE1 へ反射し、PE1 が RIB と CEF に入れるまで、PE1 には CE1 のパケットを送る先がありません。しかも BGP は、
next-hop の変化をすぐには反映せず、間隔(trigger delay)を置いてまとめて処理します。IOS XR の間隔は 2 種類で、next-hop に
届く・届かないのような変化(critical)と、IGP のメトリックの変化(non-critical)に分かれます。

既定は、IPv4 ユニキャストでは critical が 3000 ms、non-critical が 10000 ms です。VPNv4 と VPNv6 の critical は、7.10.1 から
50 ms です。PE2 を切り離した時、CE1 から T への通信は、入口の PE が IOS XRd なら 2.46 秒、IOS XRv 9000 なら 3.26 秒
止まりました。この間隔とほぼ同じ長さです。その間も、CE1 は 10 ms ごとに送り続けています。

出口の PE2 と X1 の間の線が切れた時は事情が違います。PE2 の eBGP はすぐに落ち(fast-external-fallover。IOS XR では既定で
有効)、取り下げが RR1 を通って流れるので、何も足さなくても途切れは 0.14 秒でした。困るのは、PE2 そのものがコアから消えて、
ほかのルータが next-hop の追跡で気づくしかない時です。

### 1.3 答え: 予備の道を先に配り、先に入れておく

- **追加パス(ADD-PATH)で配る**: PE3 は、最良ではない X2 からの経路も、追加の経路として RR1 へ送ります。RR1 は最良と予備の
  2 本を反射し、PE1 は故障の前から 2 本を知っています。
- **PIC で入れておく**: PE1 は、予備の経路を最良の隣に RIB と CEF へ入れておきます。IS-IS が 10.255.0.2/32 を消した時点で、
  CEF は BGP を待たずに予備へ切り替わります。BGP は、その後で自分の間隔どおりに選び直します。
- **予備の出口にも入れる**: この網は VPN ではないので、PE3 も自分の X2 の経路を予備として入れておく必要があります(2.5 節)。

3 つをそろえると、途切れは 0.15〜0.21 秒になりました。BGP は今までどおり 3 秒待ちますが、
転送はもうそれを待ちません。

## 2. 仕組み

このページでは、203.0.113.0/24 の 1 本の経路を追います。2.1〜2.3 節は故障の前で、経路が PE3 から RR1 を通って PE1 へ届く
までです。2.4 節と 2.5 節は故障の瞬間で、CE1 のパケットが PE1 から PE3 へ届くまでです。

### 2.1 RR は最良の 1 本しか反射しない

PE1 が予備を知らない理由は 2 つあり、それぞれ別の所にあります。

- **PE3 が出さない**: 1.1 節のとおり、PE3 の最良は iBGP で学んだ PE2 経由の経路で、PE3 はそれを RR1 へ出しません。
  X2 からの経路は最良ではないので、これも出しません。
- **RR1 が 1 本しか反射しない**: RR1 が仮に 2 本を持っても、クライアントへ反射するのは自分の最良の 1 本です。RR1 の最良は
  PE2 経由(ローカル プリファレンス 200)なので、PE1 に届くのはやはり 1 本です。

1 本しか送れないのは、BGP の UPDATE のきまりです。同じ相手から同じプレフィックスがもう一度届くと、新しいほうが前のものに
置き換わります(暗黙の取り下げ)。1 つのセッションの上では、1 つのプレフィックスに経路は 1 本しか乗りません。2 本目を
乗せるには、経路を見分ける印が要ります(2.2 節)。

1 つめの理由だけなら、best-external が答えます。最良が iBGP の経路の時に、自分の最良の eBGP の経路を iBGP の相手と RR へ
広告する機能です。PE3 に入れると RR1 は 2 本を持ちますが、反射するのは最良の 1 本のままで、PE1 は 1 本のままです。
入口が IOS XRd の時の途切れは 3.02 秒で、何も足さない時より短くはなりませんでした。

それに Cisco の文書は、best-external を VPNv4・VPNv6・VRF・L2VPN・ラベル付きユニキャストのアドレス ファミリにしか載せて
おらず、ラベルなしの best-external は「ルーティング ループを作りうるので非対応」としています(理由は 2.5 節)。この版
(26.1.1)では素の IPv4 ユニキャストでもコミットが通って動きますが、文書と食い違うので、このラボでは使いません
([付録](69-m6-appendix.html))。

### 2.2 追加パス: パス ID と能力の交渉

追加パス(ADD-PATH、RFC 7911)は、UPDATE の中の各プレフィックスの前に、4 オクテットのパス ID を付けます。経路は
「プレフィックスとパス ID」の組で見分けられるので、同じプレフィックスの経路を何本でも並べて送れます。新しい経路が前の
経路を置き換えるのは、パス ID も同じ時だけです。パス ID は送る側が決め、そのセッションの上だけで意味を持ちます。

出力では、`Received Path ID` が相手の付けてきた ID、`Local Path ID` がこのルータが送る時に付ける ID です。X2 経由の経路を
追うと、PE3 は自分の経路に 3 を付けて送り、RR1 は 3 で受けて 2 を付け直し、PE1 は 2 で受けています。追加パスを使わない
相手から来た経路の `Received Path ID` は 0 です。次は、3.1 節の設定を入れて張り直した後です。

```console
RP/0/RP0/CPU0:PE3#show bgp 203.0.113.0/24
...
  Path #2: Received by speaker 0
  Advertised IPv4 Unicast paths to peers (in unique update groups):
    10.255.0.21     
  65100
    172.16.3.1 from 172.16.3.1 (10.100.255.2)
      Origin IGP, metric 11, localpref 100, valid, external, backup, add-path
      Received Path ID 0, Local Path ID 3, version 20
RP/0/RP0/CPU0:RR1#show bgp 203.0.113.0/24
...
Paths: (2 available, best #1)
...
  65100, (Received from a RR-client)
    10.255.0.2 (metric 20) from 10.255.0.2 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
      Received Path ID 0, Local Path ID 1, version 5
  Path #2: Received by speaker 0
  Advertised IPv4 Unicast paths to peers (in unique update groups):
    10.255.0.1      
  65100, (Received from a RR-client)
    10.255.0.3 (metric 20) from 10.255.0.3 (10.255.0.3)
      Origin IGP, metric 11, localpref 100, valid, internal, backup, add-path
      Received Path ID 3, Local Path ID 2, version 14
RP/0/RP0/CPU0:PE1#show bgp 203.0.113.0/24
...
Paths: (2 available, best #1)
...
    10.255.0.2 (metric 20) from 10.255.0.21 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
      Received Path ID 1, Local Path ID 1, version 9
...
  Path #2: Received by speaker 0
  Not advertised to any peer
  65100
    10.255.0.3 (metric 20) from 10.255.0.21 (10.255.0.3)
      Origin IGP, metric 11, localpref 100, valid, internal
      Received Path ID 2, Local Path ID 0, version 0
```

PE3 の X2 の経路は、今は RR1(10.255.0.21)へ広告されています。RR1 は PE3 からの経路を、PE1(10.255.0.1)だけへ出して
います。追加パスを受けると告げているクライアントは、PE1 だけです。

パス ID を付けた経路を送るには、その前に両側が OPEN で取り決めておく必要があります(能力、capability)。取り決めは
アドレス ファミリごと・向きごとで、各側が「受けられる(1)」「送れる(2)」「両方(3)」のどれかを告げます。A から B へ
追加パスが流れるのは、A が送れると告げ、B が受けられると告げた時だけです。この盤面では次のとおりです。

| 機器 | 送る(send) | 受ける(receive) | なぜ |
|---|---|---|---|
| PE3 | 告げる | — | 自分の X2 の経路を、最良でなくても RR1 へ送る |
| RR1 | 告げる | 告げる | PE3 から受け、PE1 へ反射する |
| PE1 | — | 告げる | RR1 から 2 本を受ける |
| PE2 | — | — | PE2 の経路はどこでも最良なので、追加パスは要らない |

能力は OPEN で交渉するので、動いているセッションに設定を足しても、張り直すまで何も変わりません。IOS XR での張り直しは
`clear bgp <近隣>` です。`clear bgp ipv4 unicast <近隣>` は、アドレスの後ろに `soft` か `long-lived-stale` しか取らず、それ
以外は `% Incomplete command.` になります。ソフト リセットで能力を交渉し直す方法はありません。OPEN は、セッションの始まり
にしか送られないからです。

```console
RP/0/RP0/CPU0:PE1#clear bgp ipv4 unicast 10.255.0.21
% Incomplete command.
```

IOS XR では、アドレス ファミリの `additional-paths send` と `additional-paths receive` が、そのアドレス ファミリの
iBGP の近隣すべてに能力を告げさせます。eBGP の近隣とは交渉しません(PE1 と CE1 の eBGP は `Additional-paths operation:
None` のまま。3.3 節)。近隣ごとに変えるなら、近隣の下の `capability additional-paths send`・`receive` です(`disable` で
外す)。

### 2.3 何を送り、何を入れるか: selection の advertise と install

能力は、複数の経路を送ってよいという取り決めにすぎません。どの経路を送るかは、`additional-paths selection route-policy
<名前>` で付けるルート ポリシーが、`set path-selection` で決めます。selection が無ければ、送る能力があっても、送るのは最良
だけです。

このページで使うのは `backup 1` です。予備の経路(バックアップ パス)は次のように決まります。全部の経路から、最良と、最良と
同じ next-hop の経路をすべて除き、残りの中でもう一度最良を選びます。最良と同じ出口を予備にしても、その出口が落ちれば
一緒に落ちるからです。予備は 1 本だけで、`backup` の後ろに書ける数も 1 だけです。

`backup 1` の後ろのキーワードが、予備をどう使うかを決めます。

| `set path-selection …` | 予備を RIB と CEF に入れるか | 広告するもの |
|---|---|---|
| `backup 1 advertise` | 入れない | 最良と予備 |
| `backup 1 install` | 入れる(PIC) | 最良だけ |
| `backup 1 advertise install` | 入れる(PIC) | 最良と予備 |

ほかに `all`(全部の経路)、`group-best`(AS ごとの最良)、`multipath`(マルチパス)、`best-path`(最良だけ)があります
(`set path-selection ?`)。

予備を計算したルータでは、予備の経路の行に `backup, add-path` が付きます(2.2 節の PE3 と RR1)。PE1 は `receive` だけ
なので、2 本目を受けても予備を計算しません。2.2 節の PE1 の 2 本目の行には何も付かず、`Local Path ID` も 0 です。受け
取っただけの予備は、まだどこにも使われていません。

この盤面では、PE3 と RR1 に `backup 1 advertise` を、PE1 に `backup 1 install` を入れます(2.4 節)。PE3 には、後で
`install` も足します(2.5 節)。

### 2.4 PIC: 予備をフォワーディング テーブルに入れておく

`install` は、予備の経路を最良の隣に RIB と CEF へ入れます。RIB の `show route … detail` には `Number of pic paths 1` と、
予備の行の `BGP backup path` が出て、CEF の `show cef … detail` には `recursive, backup` の経路が出ます(3.3 節)。予備は
入っているだけで、ふだんのパケットは最良のほうを通ります。

速さの元は、CEF の階層にあります。203.0.113.0/24 はインターフェイスを直接指さず、next-hop の 10.255.0.2/32 を指し
(`recursive`)、その 10.255.0.2/32 が IS-IS の経路で P1 へのインターフェイスを指します。同じ next-hop を持つ BGP の経路は、
この next-hop の部分を共有します。

IS-IS が 10.255.0.2/32 を消すと、共有の部分が解決できなくなり(`unresolved`)、予備を持つ経路はどれも、その時点で予備へ
移ります。経路の数によらず 1 か所の変化で済むので、Prefix Independent Convergence です。この盤面で予備を持つ経路は
203.0.113.0/24 の 1 本だけなので、名前の「プレフィックスの数によらない」の部分は、ここでは確かめようがありません。

故障の時は、次の順に進みます。

- P1 の PE2 向けのインターフェイスが止まり、IS-IS が 10.255.0.2/32 を消す。
- PE1 の CEF は、10.255.0.2 経由が解決できなくなった時点で、予備の 10.255.0.3 経由で送り始める。BGP はまだ何もしていない。
- critical の間隔(3 秒)の後、PE1 の BGP が選び直し、PE3 経由の経路が最良になる。RR1 も同じように選び直す。

次は、P1 の PE2 向けのインターフェイスを止めた直後の PE1 です。CEF は PE2 経由を `unresolved` とし、送る先(`Load
distribution` の `[0]`)はもう予備の 10.255.0.3 です。RIB ではまだ PE2 経由が主です。BGP が PE3 経由を最良にしたのは、CEF の
表の更新(`LDI Update time`)の約 2.6 秒後でした(抜粋)。

```console
RP/0/RP0/CPU0:PE1#show cef 203.0.113.0/24 detail
...
 LDI Update time Nov 21 11:19:03.906
...
  Level 1 - Load distribution: 0
  [0] via 10.255.0.3/32, recursive
...
   via 10.255.0.2/32, 0 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0xeb5bb20 0x0]
    unresolved
...
   via 10.255.0.3/32, 3 dependencies, recursive, backup [flags 0x6100]
    path-idx 1 NHID 0x0 [0xf79e140 0x0]
    next hop 10.255.0.3/32 via 10.255.0.3/32
...
RP/0/RP0/CPU0:PE1#show route 203.0.113.0/24 detail
...
  Routing Descriptor Blocks
    10.255.0.2, from 10.255.0.21
...
    10.255.0.3, from 10.255.0.21, BGP backup path
...
RP/0/RP0/CPU0:PE1#show bgp 203.0.113.0/24
...
Last Modified: Nov 21 11:19:06.541 for 00:00:00
Paths: (1 available, best #1)
...
    10.255.0.3 (metric 20) from 10.255.0.21 (10.255.0.3)
      Origin IGP, metric 11, localpref 100, valid, internal, best, group-best
```

ところが、入口の PE1 だけに PIC を入れても、途切れは 2.98 秒でした。PE1 の BGP の critical の間隔を 10 秒に延ばしても、
約 3 秒のままです。PE1 はもう切り替えていて、パケットはその先で落ちています。

### 2.5 ラベルなしの網の落とし穴: 予備の出口が送り返す

パケットを、もう 1 ホップ追います。PE1 は予備の経路で、10.255.0.3 行きの LDP のラベルを積んで P1 へ送ります。P1 は PE3 の
1 つ手前なのでラベルを外し、PE3 には素の IP パケットが届きます。PE2 が消えている間の traceroute でも、ラベルが見えるのは
P1 だけです。

```console
CE1#traceroute 203.0.113.1 source 192.168.1.1 probe 1 timeout 2
Type escape sequence to abort.
Tracing the route to 203.0.113.1
VRF info: (vrf in name/id, vrf out name/id)
  1 172.16.1.254 2 msec
  2 10.0.1.11 [MPLS: Label 24001 Exp 0] 2 msec
  3 10.0.3.3 2 msec
  4 172.16.3.1 3 msec
  5 10.100.23.3 3 msec
```

PE3 は、届いたパケットの宛先 203.0.113.1 を自分の表で引き直します。PE3 の最良は、まだ PE2 経由の iBGP の経路です。PE3 の
BGP が自分の critical の間隔(3 秒)の後に選び直すまで、PE3 はパケットを PE2 の方へ送り返そうとし、PE2 への道はもう無いので、
パケットは捨てられます。PE1 は予備の出口へ切り替えましたが、予備の出口の表は、まだ主の出口を指しています。

:::topo
nodes:
  CE1: {at: [0, 1], kind: host, label: "CE1"}
  PE1: {at: [2.2, 1], label: "PE1 (切り替え済み)"}
  P1: {at: [4.2, 1], label: "P1"}
  RR1: {at: [4.2, 2.5], label: "RR1"}
  PE2: {at: [6.2, 0], label: "PE2 (コアから消えた)"}
  PE3: {at: [6.2, 2], label: "PE3 (最良は PE2 経由)"}
  X1: {at: [8.2, 0], label: "X1"}
  X2: {at: [8.2, 2], label: "X2"}
  T: {at: [9.9, 1], kind: host, label: "T"}
links:
  - {a: CE1, b: PE1, label: "CE1 → T", t: 0.45}
  - {a: PE1, b: P1, label: "LDP のラベル付き\n10.255.0.3 行き"}
  - {a: P1, b: PE2, style: dashed, label: "止まっている"}
  - {a: P1, b: PE3, label: "素の IP で届く\nPE3 は PE2 の方へ送り返す"}
  - {a: P1, b: RR1, style: dashed}
  - {a: PE2, b: X1, style: dashed}
  - {a: PE3, b: X2, style: dashed, label: "CEF に予備が\n無いと使われない"}
  - {a: X1, b: T, style: dashed}
  - {a: X2, b: T, style: dashed}
  - {a: X1, b: X2, style: dashed}
:::

直し方は、PE3 にも PIC を入れることです。予備は X2 から学んだ自分の eBGP の経路で、selection のポリシーを
`backup 1 advertise install` にすると、PE3 も IS-IS が 10.255.0.2/32 を消した時点で CEF を X2 経由へ切り替えます。途切れは
0.15〜0.21 秒になりました。入口の BGP の間隔を 10 秒にしても 0.2 秒を下回ったままで、切り替えはフォワーディング テーブル
だけで済んでいます。

入口が IOS XRd の時は、PE3 にも PIC を入れても、途切れは約 3.0 秒のままでした(同じ形の IOS XRv 9000 の入口は 0.15〜
0.18 秒)。この仮想機では、IGP から遠くの PE(ここでは
PE2)が消えた時、IOS XRd の入口は入れてある予備を使わず、BGP が選び直すのと同じ約 3 秒たってから戻りました。表示は予備を
正しく載せています。そのため、このラボの PE1 は IOS XRv 9000 です(3.4 節・[付録](69-m6-appendix.html))。

VPN では、この送り返しは起きません。L3VPN(M9)の入口の PE は、トランスポート ラベルの下に、出口の PE が割り当てた VPN
ラベルを積みます。ラベルの割り当てがプレフィックスごとか CE ごとなら、出口の PE は VPN ラベルを見て、IP を引き直さずに
CE へ送ります。

Cisco の文書がラベルなしの best-external を「ループを作りうる」として認めないのは、この送り返しのためです。VRF ごとに
1 つのラベル(per-VRF)のモードでは、出口の PE が VRF の表で IP を引くので、文書はこのモードの best-external も、同じ理由で
認めていません。

## 3. IOS XR での設定

### 3.1 追加パスの設定例

設定は 3 台の 6 つの塊に分かれ、203.0.113.0/24 の経路と CE1 のパケットに、次の順で効きます。①② PE3 が予備の経路を選んで
送る。③ RR1 が受けて、予備も反射する。④ PE1 が受ける。ここまでがこの節です。⑤ PE1 が予備を RIB と CEF に入れる。⑥ PE3 も
自分の予備を入れる。この 2 つは 3.2 節です。

図の上半分は、経路が PE3 → RR1 → PE1 と配られる所、下半分は、PE2 がコアから消えた直後の CE1 のパケットです。図の番号は、
この節と次の節の設定例の注記の番号と同じです。図の番号にカーソルを置くと(スマホでは押すと)、その部分の設定が出ます。

:::walk
legend: "上半分: 故障の前に、予備の経路が PE3 → RR1 → PE1 と配られる。下半分: P1 と PE2 の間が止まった直後の、CE1 から T へのパケット。青い番号: 設定の塊。"
rows:
  - panel: PE3
    sub: 予備の出口(故障の前)
    items:
      - ref: 1
        head: "**送る経路を選ぶ** `set path-selection backup 1 advertise`"
        say: ["最良(PE2 経由)と同じ next-hop の経路を除いた残りの最良 → X2 からの eBGP の経路が予備"]
      - ref: 2
        head: "**送る能力** `additional-paths send`"
        say: ["RR1 との OPEN で send を告げる(張り直した後に効く)"]
  - {wire: "[[203.0.113.0/24  パス ID 3  NH 10.255.0.3]] _PE3 → RR1"}
  - panel: RR1
    sub: ルート リフレクタ(道の外)
    items:
      - ref: 3
        head: "**受けて、選んで、送る** `additional-paths receive`・`send`・`selection`"
        say: ["PE2 からの最良と PE3 からの予備の 2 本を持ち、予備も反射する"]
  - wire:
      - "[[203.0.113.0/24  パス ID 1  NH 10.255.0.2]] _最良"
      - "[[203.0.113.0/24  パス ID 2  NH 10.255.0.3]] _予備。RR1 → PE1"
  - panel: PE1
    sub: 入口の PE(IOS XRv 9000)
    items:
      - ref: 4
        head: "**受ける能力** `additional-paths receive`"
        say: ["2 本を別の経路として持つ(パス ID 1 と 2)"]
      - ref: 5
        head: "**予備を入れる** `set path-selection backup 1 install`"
        say: ["PE3 経由を予備として RIB と CEF へ。ここまでが故障の前の準備"]
      - say: ["~P1 の PE2 向けの線が止まり、IS-IS が 10.255.0.2/32 を消す", "[[IP 192.168.1.1 → 203.0.113.1]] _CE1 から 10 ms ごとに届く"]
      - ref: 5
        head: "**CEF で 203.0.113.0/24 を引く**"
        match:
          - ["via 10.255.0.2/32, … recursive", false, "unresolved(PE2 のループバックが消えた)"]
          - ["via 10.255.0.3/32, … recursive, backup", true, "当たる → BGP を待たずにこちら"]
  - {wire: "[[=LDP  10.255.0.3 行き]] [[IP → 203.0.113.1]] _P1 へ"}
  - {node: P1, say: ["~BGP なし。ラベルで送る", "~PE3 の 1 つ手前なのでラベルを外す"]}
  - {wire: "[[IP → 203.0.113.1]] ^ラベルなし: PE3 は宛先を引き直す"}
  - panel: PE3
    sub: 予備の出口(パケットが届いた時)
    items:
      - ref: 6
        head: "**自分の予備も入れる** `set path-selection backup 1 advertise install`"
        say: ["PE3 の IS-IS も 10.255.0.2/32 を消している"]
        match:
          - ["via 10.255.0.2/32, … recursive", false, "unresolved(主の出口 PE2)"]
          - ["via 172.16.3.1/32, … bgp-ext, backup", true, "当たる → X2 へ"]
  - {wire: "[[IP → 203.0.113.1]] _Gi0/0/0/1 から X2 へ"}
  - {node: X2, say: ["~AS 65100。OSPF で T へ"]}
  - {wire: "[[IP → 203.0.113.1]]"}
  - {node: T, kind: host, say: ["~届く。途切れは 0.15〜0.21 秒"]}
  - aside: "⑥ が無いと(PE3 の予備は広告するだけ)"
    say: ["~PE3 の最良は PE2 経由の iBGP のまま → PE2 の方へ送り返す → PE2 への道は無く、捨てられる", "~PE3 の BGP が critical の間隔(3 秒)の後に選び直すまで。途切れは約 3 秒"]
  - aside: "③ に selection の行が無いと"
    say: ["~RR1 は最良の 1 本しか反射しない → PE1 は予備を知らず、⑤ は入れる経路を持たない"]
:::

PE3 には、送る経路を選ぶポリシーと、送る能力を入れます。selection のポリシーは、このアドレス ファミリの全部の
プレフィックスに効きます。

:::config fold PE3 — X2 からの経路を、最良でなくても予備として RR1 へ送る
route-policy ADDPATH-OUT                      ## ① 送る経路を選ぶポリシー
  set path-selection backup 1 advertise       ## ① 予備を 1 本計算して広告する。RIB と CEF には入れない
end-policy
!
router bgp 65000
 address-family ipv4 unicast
  additional-paths send                       ## ② iBGP の近隣(RR1)へ send の能力を告げる
  additional-paths selection route-policy ADDPATH-OUT   ## ① このアドレス ファミリの送る経路を、ポリシーで選ぶ
 !
!
:::

RR1 は、受ける能力と送る能力の両方と、反射する経路を選ぶポリシーです。

:::config fold RR1 — PE3 からの予備を受け、最良と予備の 2 本を反射する
route-policy RR-ADDPATH                       ## ③ 反射する経路を選ぶポリシー
  set path-selection backup 1 advertise       ## ③ 最良に加えて、予備を 1 本広告する
end-policy
!
router bgp 65000
 address-family ipv4 unicast
  additional-paths send                       ## ③ クライアントへ送る能力
  additional-paths receive                    ## ③ PE3 から受ける能力
  additional-paths selection route-policy RR-ADDPATH   ## ③ 予備を計算させる。この行が無いと、反射するのは最良だけ
 !
!
:::

PE1 は、受ける能力だけです。

:::config fold PE1 — RR1 から 2 本目の経路を受ける
router bgp 65000
 address-family ipv4 unicast
  additional-paths receive                    ## ④ RR1 へ receive の能力を告げる。受けるだけで、予備にはしない
 !
!
:::

3 台にコミットしたら、能力を交渉させるために、PE3 と PE1 で RR1 とのセッションを張り直します。RR1 の側は、相手が張り
直すので何もしません。張り直しが終わると、RR1 と PE1 は `Paths: (2 available, best #1)` になります(2.2 節の出力)。最良は
PE2 経由のままです。

```console
RP/0/RP0/CPU0:PE3#clear bgp 10.255.0.21
RP/0/RP0/CPU0:PE1#clear bgp 10.255.0.21
```

### 3.2 PIC の設定例

PE1 には、予備を入れるポリシーを selection で付けます。selection は能力を変えないので、張り直しは要りません。コミットすると、
すぐに RIB と CEF に予備が入ります。

:::config fold PE1 — PE3 経由の予備を、RIB と CEF に入れておく
route-policy PIC                              ## ⑤ 予備を選ぶポリシー
  set path-selection backup 1 install         ## ⑤ 予備を 1 本計算して RIB と CEF へ。広告はしない
end-policy
!
router bgp 65000
 address-family ipv4 unicast
  additional-paths selection route-policy PIC ## ⑤ 張り直しは要らない
 !
!
:::

PE3 では、3.1 節のポリシーを書き直します。IOS XR のルート ポリシーは、行の足し引きではなく丸ごとの置き換えなので、既に
あるポリシーの名前で入ると、警告が出ます。

```console
RP/0/RP0/CPU0:PE3(config)#route-policy ADDPATH-OUT
% WARNING: Policy object route-policy ADDPATH-OUT exists! Reconfiguring it via CLI will replace current definition. Use abort to cancel.
RP/0/RP0/CPU0:PE3(config-rpl)#  set path-selection backup 1 advertise install
RP/0/RP0/CPU0:PE3(config-rpl)#end-policy
RP/0/RP0/CPU0:PE3(config)#commit
```

:::config fold PE3 — X2 からの自分の経路も、予備として RIB と CEF に入れておく
route-policy ADDPATH-OUT                      ## ⑥ 同じ名前で書き直す。前の中身と置き換わる
  set path-selection backup 1 advertise install   ## ⑥ 予備を広告し(① のまま)、自分の RIB と CEF にも入れる
end-policy
:::

IOS XE では、送る経路を数とキーワードで選び、選んだ中から何を出すかを近隣ごとに書きます。予備を RIB と CEF に入れるのは
1 行です。IOS XE の文書は、PIC core(既定で有効)と PIC edge を分けて呼び、`bgp additional-paths install` を PIC edge の
設定としています。

| 何をするか | IOS XR | IOS XE |
|---|---|---|
| 能力を告げる(アドレス ファミリ全体) | `additional-paths send`・`additional-paths receive` | `bgp additional-paths send receive`(片方だけも書ける) |
| 能力を告げる(近隣ごと) | 近隣の下の `capability additional-paths send`・`receive` | `neighbor <近隣> additional-paths send receive` |
| 送る経路を選ぶ | ルート ポリシーの `set path-selection …` を `additional-paths selection route-policy` で付ける | `bgp additional-paths select best 2`(ほかに `group-best`・`all`) |
| 近隣へ出す | selection のポリシーで決まる | `neighbor <近隣> advertise additional-paths best 2` |
| 予備を RIB と CEF に入れる | `set path-selection backup 1 install` | `bgp additional-paths install` |

### 3.3 出力の読み方

**`show bgp <プレフィックス>`**: 3.2 節の後の PE1 では、2 本目に `backup, add-path` が付き、`Local Path ID` が 0 から 2 に
なります(2.2 節の出力と比べてください)。

```console
RP/0/RP0/CPU0:PE1#show bgp 203.0.113.0/24
...
Paths: (2 available, best #1)
...
  Path #2: Received by speaker 0
  Not advertised to any peer
  65100
    10.255.0.3 (metric 20) from 10.255.0.21 (10.255.0.3)
      Origin IGP, metric 11, localpref 100, valid, internal, backup, add-path
      Received Path ID 2, Local Path ID 2, version 12
      Originator: 10.255.0.3, Cluster list: 10.255.0.21
```

- `Paths: (2 available, best #1)`: 経路は 2 本で、最良は 1 本目。
- `backup, add-path`: selection のポリシーが予備に選んだ経路。
- `Received Path ID 2`: RR1 がこの経路に付けてきたパス ID。

**`show route <プレフィックス> detail`**: RIB に予備が入っていれば、`Number of pic paths 1` と、予備の行の
`BGP backup path` が出ます。予備が無い時は、`Tag 65100` と `Number of pic paths …` の 2 行が `Tag 65100, type internal` の
1 行です。

```console
RP/0/RP0/CPU0:PE1#show route 203.0.113.0/24 detail

Routing entry for 203.0.113.0/24
  Known via "bgp 65000", distance 200, metric 11
  Tag 65100
  Number of pic paths 1 , type internal
  Installed Nov 21 09:53:57.531 for 00:00:22
  Routing Descriptor Blocks
    10.255.0.2, from 10.255.0.21
      Route metric is 11, Wt is 1
...
    10.255.0.3, from 10.255.0.21, BGP backup path
      Route metric is 11, Wt is 1
...
```

**`show cef <プレフィックス> detail`**: CEF に主と予備の 2 本が並びます。予備には `backup` が付きます。PE3 の予備は X2
からの eBGP の経路で、`bgp-ext` も付きます(抜粋)。

```console
RP/0/RP0/CPU0:PE1#show cef 203.0.113.0/24 detail
...
   via 10.255.0.2/32, 3 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0xf79e080 0x0], Internal 0x110e10a0
    next hop 10.255.0.2/32 via 10.255.0.2/32
...
   via 10.255.0.3/32, 2 dependencies, recursive, backup [flags 0x6100]
    path-idx 1 NHID 0x0 [0xf79e140 0x0]
    next hop 10.255.0.3/32 via 10.255.0.3/32
RP/0/RP0/CPU0:PE3#show cef 203.0.113.0/24 detail
...
   via 10.255.0.2/32, 2 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0x88531068 0x0], Internal 0x8aad50a0
    next hop 10.255.0.2/32 via 10.255.0.2/32
   via 172.16.3.1/32, 2 dependencies, recursive, bgp-ext, backup [flags 0x6120]
    path-idx 1 NHID 0x0 [0x88539800 0x0]
    next hop 172.16.3.1/32 via 172.16.3.1/32
```

- `recursive`: インターフェイスでなく next-hop を指す経路。next-hop は IS-IS の経路で引く。
- `backup`: 予備。ふだんは使わない。
- 故障の直後は、主の 10.255.0.2 経由の行が `unresolved` になり、予備のほうは解決したまま残ります(2.4 節の出力)。

**`show bgp nexthops`**: next-hop の追跡の間隔と、next-hop ごとに届くかどうかです。`Status` の `[R]` は届く、`[UR]` は
届かないの意味です(抜粋)。

```console
RP/0/RP0/CPU0:PE1#show bgp nexthops
...
Gateway Address Family: IPv4 Unicast
Table ID: 0xe0000000
...
Critical Trigger Delay: 3000msec
Non-critical Trigger Delay: 10000msec
...
Status codes: R/UR Reachable/Unreachable
              C/NC Connected/Not-connected
              L/NL Local/Non-local
              PR   Pending Registration
              I    Invalid (Policy drop)
Next Hop        Status          Metric     Tbl-ID   Notf   LastRIBEvent      RefCount
10.255.0.2      [R][NC][NL]         20   e0000000   0/0    00:08:24 (Reg)        1/3
...
10.255.0.21     [R][NC][NL]         20   e0000000   1/0    00:10:30 (Cri)        0/3
172.16.1.1      [R][C][NL]           0   e0000000   1/0    00:10:46 (Cri)        1/4
```

**`show bgp neighbor <近隣>`**: 張り直した後の iBGP の近隣では、アドレス ファミリの部分の `AF-dependent capabilities:` に
`Additional-paths Send:` と `Additional-paths Receive:` の行が出ます。向きごとに `advertised`(自分が告げた)と `received`
(相手が告げた)が並び、両方そろった向き(`advertised and received`)が使われます。

PE3 は送る向きだけ、PE1 は受ける向きだけがそろい、`Additional-paths operation:` もそれぞれ `Send` と `Receive` です。
eBGP の近隣には、どちらの行も出ず、`None` のままです。次は PE3 と PE1 の RR1 との iBGP、PE1 の CE1 との eBGP です(抜粋)。

```console
RP/0/RP0/CPU0:PE3#show bgp neighbor 10.255.0.21
...
 For Address Family: IPv4 Unicast
...
  AF-dependent capabilities:
    Additional-paths Send: advertised and received
    Additional-paths Receive: received
    Extended Nexthop Encoding: advertised and received
...
  Additional-paths operation: Send
...
RP/0/RP0/CPU0:PE1#show bgp neighbor 10.255.0.21
...
 For Address Family: IPv4 Unicast
...
  AF-dependent capabilities:
    Additional-paths Send: received
    Additional-paths Receive: advertised and received
    Extended Nexthop Encoding: advertised and received
...
  Additional-paths operation: Receive
...
RP/0/RP0/CPU0:PE1#show bgp neighbor 172.16.1.1
...
 Remote AS 65001, local AS 65000, external link
...
 For Address Family: IPv4 Unicast
...
  AF-dependent capabilities:
    Extended Nexthop Encoding: advertised
...
  Additional-paths operation: None
```

| コマンド | 何を見るか |
|---|---|
| `show bgp <プレフィックス>` | 経路の本数(`Paths:`)、`backup`・`add-path` の印、`Received Path ID`・`Local Path ID`、どの近隣へ広告したか |
| `show bgp neighbor <近隣>` | アドレス ファミリの `AF-dependent capabilities:` の能力の行(`Additional-paths Send:`・`Receive:`)と `Additional-paths operation:` |
| `show route <プレフィックス> detail` | `Number of pic paths`、予備の行の `BGP backup path` |
| `show cef <プレフィックス> detail` | 主と予備の 2 本(`recursive, backup`)、故障中の `unresolved` |
| `show bgp nexthops` | next-hop の追跡の間隔(`Critical Trigger Delay`・`Non-critical Trigger Delay`)と、next-hop ごとに届くか |

### 3.4 落とし穴

- **能力を足しただけ**: 能力は OPEN で交渉するので、張り直すまで `Additional-paths operation: None` のまま。張り直しは
  `clear bgp <近隣>`。`clear bgp ipv4 unicast <近隣>` は、後ろに `soft` か `long-lived-stale` しか取らない。
- **RR に selection が無い**: send と receive だけでは、RR1 は最良の 1 本しか反射しない。
- **eBGP の近隣**: アドレス ファミリの send と receive が能力を告げるのは、iBGP の近隣だけ。CE1 との eBGP とは交渉しない。
- **受けただけ**: PE1 の `receive` だけでは、2 本目は予備にならない(`Local Path ID 0`、印なし)。予備を入れるのは、PE1 自身の
  selection の `install`。
- **入口だけの PIC**: ラベルなしの網では、予備の出口が自分の表で宛先を引き直し、主の出口の方へ送り返す。予備の出口にも
  `install` を入れる。
- **予備は 1 本**: `backup` の後ろは 1 だけ。最良と同じ next-hop の経路は、予備にならない。
- **この仮想機の IOS XRd の入口**: IGP から遠くの PE が消えた時、入れてある予備を使わず、約 3 秒たってから戻った(表示は
  予備を正しく載せている)。自分の線が切れた時は速く、PE2(IOS XRd)は X1 との線を失うと、PE3 経由の予備へ 0.05 秒で
  切り替わった。PIC を通信で確かめる入口は IOS XRv 9000 にする([付録](69-m6-appendix.html))。

ラボ **XRT-17** で課題 M6-5 と M6-6 に取り組みます。ラボの初めの状態では、追加パスも PIC も、どこにも設定されていません。

<p class="tolab"><a href="/_learn?id=XRT-17">ワークスペースでラボ XRT-17 を開く</a> — <a href="64-m6-practice-2.html">課題 M6-5、M6-6</a></p>

:::note
2.2 節・2.4 節・2.5 節の出力、3.1 節と 3.2 節の操作、3.3 節の `show bgp`・`show route`・`show cef`・`show bgp neighbor` の出力、
本文と図の途切れの 0.15〜0.21 秒と 2.98 秒は、XRT-17 の上で課題と同じ値で取得しました(PE1 は IOS XRv 9000 26.1.1、PE2・PE3・
P1・RR1 は IOS XRd 26.1.1、CE1・X1・X2・T は IOS XE 17.15 の IOL)。1.1 節の出力、3.3 節の `show bgp nexthops`、そのほかの途切れの
数値は、PE1〜PE3・P1・RR1・CE1・X1・X2・T が XRT-17 と同じ名前とアドレスを持つ別の盤面のものです。そこでは PE1 が
IOS XRd 26.1.1 で、入口の PE がもう 1 台(IOS XRv 9000 26.1.1)ありました。
途切れの測り方: どちらの盤面でも、CE1(192.168.1.1)から T へ IP SLA の udp-jitter を 10 ms ごとに送り、行きの欠けの続いた長さ
(Loss Period Length)を数えました。故障は P1 の PE2 向けのインターフェイスの shutdown です(CML のリンクの停止では、この仮想機の
IOS XR のインターフェイスは落ちません。M10 の 3 節)。XRT-17 の数値: PE1 と PE3 に PIC 0.21 秒・0.15 秒(2 回)、PE1 だけに PIC
2.98 秒。別の盤面の数値: 何も足さない時 2.46 秒(入口 IOS XRd)・3.26 秒(入口 IOS XRv 9000)、PE2 と X1 の
間の線が切れた時 0.14 秒(入口 IOS XRd)・PE2 にも PIC(予備= PE3 経由)を入れて 0.05 秒、best-external だけ 3.02 秒(IOS XRd)、入口だけの PIC 3.54 秒(IOS XRd)・3.01 秒
(IOS XRv 9000)、同じく入口の critical の間隔を 10 秒にして 2.99 秒・2.93 秒、PE3 にも PIC 0.18 秒・0.15 秒(IOS XRv 9000。
入口の間隔は 10 秒のまま)・2.96 秒・3.02 秒・3.01 秒(IOS XRd)。入口だけの PIC と、PE3 にも PIC の 0.15 秒の測定では、PE3 は
best-external で X2 の経路を出していました。このページの形(PE3 は追加パスで出す・best-external なし)では 0.18 秒
(IOS XRv 9000)・3.01 秒(IOS XRd)でした。
出典: Routing Command Reference for Cisco ASR 9000 Series Routers(`additional-paths send`・`receive`・`selection`、能力は iBGP の
近隣に自動で付くこと、張り直しが要ること、`set path-selection` の構文と backup の数が 1 であること、`advertise best-external` の
アドレス ファミリと「Unlabelled best-external is not supported as it may create routing loop」、`nexthop trigger-delay` の既定と
7.10.1 の変更)。Routing Configuration Guide for Cisco ASR 9000 Series Routers, IOS XR 24.x と 26.x の「Implementing BGP」
(next-hop の追跡の critical と non-critical、Installing Primary Backup Path for PIC、BGP PIC for RIB and FIB、per-VRF の
ラベルのモードと best-external)。BGP Configuration Guide for Cisco NCS 5500, IOS XR 25.x(BGP Additional Paths、best-external の
手順)。TAC のテクニカル ノート「Configure and Verify BGP Path Selection in IOS-XR」(Doc ID 217097。`set path-selection` の
キーワードごとの動き、RIB と CEF の予備は 1 本まで、出力の印)。Cisco IOS XR Routing Configuration Guide for the XR 12000,
Release 4.1(予備の選び方)。Release Notes for ASR 9000, IOS XR 5.1.1(プレフィックスによらない FIB の更新)。IP Routing
Configuration Guide, Cisco IOS XE 17.x の「BGP Additional Paths」と「BGP PIC Edge for IP and MPLS-VPN」(IOS XE の
コマンド。この盤面では動かしていません)。RFC 7911(パス ID、能力の Send/Receive の値)。いずれも 2026 年 11 月に確認。
次は実測によるものです: パス ID と経路の印、能力の行と `Additional-paths operation:` の値、selection の追加に張り直しが
要らないこと、`clear bgp ipv4 unicast <近隣>` の `% Incomplete command.`、故障の直後の CEF と RIB と BGP の時刻、予備の出口の
送り返し、IOS XRd の入口の約 3 秒。
文書と機器が食い違う所・文書に記述が無い所: 素の IPv4 ユニキャストの `advertise best-external` は、文書では非対応ですが、
26.1.1 の IOS XRd と IOS XRv 9000 ではコミットが通り、効きました。IOS XRd の PIC の動きを書いた Cisco の文書は
ありません。
:::
