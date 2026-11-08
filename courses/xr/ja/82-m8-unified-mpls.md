# M8 — Unified MPLS

M8 の最初のページのコアは、1 つの IGP ドメインと 1 つの LDP ドメインでした。何千台ものアクセス ルータを持つプロバイダは、
それらをすべて 1 つの IS-IS と 1 つの LDP に収めることはできません。**Unified MPLS** はネットワークを複数の IGP ドメインに
分け、それらを BGP でつなぎます。BGP がプロバイダー エッジのループバックをラベルと一緒に運びます。このページは CCNP Service
Provider のブループリントの 3.1.d にあたります。ラボ XRT-07 の続きで、コアは同じまま、XR01 の先に新しいアクセス網がつながります。

<p class="tolab"><a href="84-m8-appendix.html">図でやさしく始めるなら: M8 — 付録: 図で見る Unified MPLS</a></p>

## 1. 1 つのネットワーク、複数の IGP ドメイン

### 1.1 IGP を分ける理由

IGP では、すべてのルータが自分のドメインのすべてのループバックとリンクを保持し、そのどれかが変わるたびに SPF をやり直します。
LDP は、IGP が運んできたすべてのプレフィックスにラベルを割り当てます。数十台のコアならそれで構いませんが、モバイルや
ブロードバンドのアクセス リングの規模には耐えられません。Seamless MPLS のアーキテクチャのドラフト(draft-ietf-mpls-seamless-mpls)は
「10k to 100k MPLS nodes」を想定して書かれています。Cisco の IOS XR 向けの Unified MPLS の TAC 文書は、これを 2 つの文で
言い表しています。「The purpose of Unified MPLS is all about scaling」と「In order to scale, you cannot distribute the IGP
prefixes from one IGP into the other.」です。

それでもサービスには、ドメインをまたいで、あるプロバイダー エッジ(PE)から別の PE へのラベル スイッチド パスが必要です。
ループバックを IGP の間で再配送すると規模の問題が戻ってくるので、IGP は分けたままにし、BGP がループバックをラベルと一緒に
運びます。これが **BGP ラベル付きユニキャスト**(RFC 8277)です。2 つのドメインの間にあるルータが**境界**です(ドラフトでは
エリア境界ルータ、ABR と呼びます)。境界は両方の IGP を動かし、一方のドメインのラベル付きのルートを、自分をネクスト ホップにして
もう一方のドメインへリフレクトします。

:::topo
nodes:
  RT05: {at: [0, 0.8], label: "RT05 (PE)"}
  RT04: {at: [1.3, 0.8], label: "RT04 (P)"}
  XR01: {at: [2.6, 0.8], label: "XR01 (境界)"}
  RT01: {at: [3.9, 0], label: "RT01 (P)"}
  RT03: {at: [3.9, 1.6], label: "RT03 (P)"}
  RT02: {at: [5.2, 0.8], label: "RT02 (PE)"}
links:
  - [RT05, RT04, "ACCESS-2"]
  - [RT04, XR01, "ACCESS-1"]
  - [XR01, RT01, "PRIMARY"]
  - [XR01, RT03, "BACKUP"]
  - [RT01, RT02, "CORE-A"]
  - [RT03, RT02, "CORE-B"]
frames:
  - {label: "IS-IS ACCESS (49.0002)", nodes: [RT05, RT04]}
  - {label: "IS-IS CORE (49.0001)", nodes: [RT01, RT03, RT02]}
:::

ラボでは、RT05 がアクセス網の PE で、顧客 A の新しいサイト(10.50.0.0/16)を収容しています。RT04 は BGP を持たないアクセスの
ルータで、XR01 が境界です。RT02 はコアの PE で、顧客 A のもう一方のサイト(10.20.0.0/16)を収容しています。RT01 と RT03 は
アクセス網について何も知らず、RT04 はコアについて何も知りません。

### 1.2 2 段に分かれたパス

RT02 は RT05 のループバック 10.255.0.15/32 を、XR01 から BGP で学習します。ネクスト ホップは XR01(10.255.0.1)で、ラベルは
XR01 が選んだものです。そこへパケットを送るとき、RT02 はラベルを 2 つ積みます。下に XR01 の 10.255.0.15/32 用の BGP のラベル、
その上に XR01 まで運ぶ LDP のラベルです。コアのルータは、M8 の最初のページとまったく同じく、いちばん上のラベルだけで
スイッチングします。XR01 は BGP のラベルを受け取り、アクセス網を通って RT05 へ向かう LDP のラベルに付け替えます。
各ドメインの LDP のパスと境界の BGP のラベルからなるこのパスを、**階層型 LSP** と呼びます。

RT02 の配下の顧客 A のサイトから通常の traceroute を打つと、2 つのラベルが見えます。

```console
RT02#traceroute 10.50.0.1 source Loopback100 timeout 1 probe 1
  1 10.0.12.11 [MPLS: Labels 20/24003 Exp 0] 3 msec
  2 10.0.1.1 [MPLS: Labels 0/24003 Exp 0] 15 msec
  3  *
  4 10.0.45.15 2 msec
```

RT01(ホップ 1)は、XR01 の BGP のラベル 24003 の上に、XR01 のループバック用の自分の LDP のラベル 20 を受け取ります。
課題 M8-5 以降 XR01 が explicit null を求めているので、RT01 は 20 を 0 に付け替え、XR01(ホップ 2)は `0/24003` を受け取ります。
XR01 は、RT04 の 10.255.0.15/32 用の LDP のラベルを付けてパケットを RT04 へ送ります。RT05 自身の BGP のラベルは implicit null
なので、その下には何も残りません。RT04(ホップ 3)は、次のルータが RT05 なのでラベルを取り除き、その応答は戻ってきません。
課題 M8-5 の前の RT01 の応答が戻らなかったのと同じです。

## 2. 2 つの IGP ドメインにまたがる境界

### 2.1 2 つの IS-IS インスタンス

IOS XR は複数の IS-IS インスタンスを並べて動かせます。`router isis <タグ>` ごとに、独自の NET、独自のインターフェイス、独自の
リンクステート データベース、独自の SPF を持ちます。再配送しない限り、あるインスタンスから別のインスタンスへは何も渡らないので、
境界で 2 つの IGP ドメインを分けておくには 2 つのインスタンスがすっきりした方法です。ラボのアクセス網はエリア 49.0002 を
使っています。2 つのインスタンスはそもそも LSP を交換しないので、エリアを分けているのはここでは慣習で、必須ではありません。

`show isis adjacency` は、すべてのインスタンスの隣接関係を表示します。

```console
RP/0/RP0/CPU0:XR01#show isis adjacency

IS-IS CORE Level-2 adjacencies:
System Id      Interface                SNPA           State Hold Changed  NSF IPv4 IPv6
RT01           Gi0/0/0/0                *PtoP*         Up    29   00:04:30 Yes None None
RT03           Gi0/0/0/1                *PtoP*         Up    26   00:04:30 Yes None None

IS-IS ACCESS Level-2 adjacencies:
System Id      Interface                SNPA           State Hold Changed  NSF IPv4 IPv6
RT04           Gi0/0/0/2                *PtoP*         Up    27   00:00:37 Yes None None
```

XR01 のルーティング テーブルは両方のインスタンスのルートを持ち、`show route` はインスタンスの名前を表示します
(`Known via "isis ACCESS"`)。RT04 のテーブルにはアクセス網だけが、RT01 のテーブルにはコアだけがあります。

:::note
1 つのインターフェイスが 2 つの IS-IS インスタンスに属せるかどうかは、ガイドによって書き方が違います。Cisco 8000 の IS-IS の
コンフィギュレーション ガイド(リリース 24.x と 2026 年の累積版)は、インターフェイスは 1 つのインスタンスにしか関連付けられない
としています。ASR 9000 のリリース 7.8 以降、NCS 5500、NCS 540 のガイドは、インスタンス ID が異なれば複数のインスタンスで
インターフェイスを共有できるとしています。IOS XRd 26.1.1 は Loopback0(passive)を両方のインスタンスの下に
インスタンス ID なしで受け付け、両方がそれをアドバタイズします。このページでは代わりに、Cisco の Unified MPLS の文書の形を
使います(2.2 節)。
:::

### 2.2 境界自身のループバック

アクセスのルータは XR01 のアドレスを 1 つ必要とします。Loopback0 です。LDP はネイバーのトランスポート アドレスに向けて TCP
セッションを開き、それは XR01 の Loopback0 です(M8 の最初のページの 2.3 節)。また RT05 は、XR01 の Loopback0 と BGP で
ピアリングします。新しいインスタンスに ACCESS-1 だけを入れると、RT04 との隣接関係は上がり、LDP の hello もやり取りされますが、
RT04 は 10.255.0.1 へのルートを持たず、セッションはできません。

Cisco の Unified MPLS の文書は、そのループバックだけを通すルート ポリシーで接続ルートを再配送して、境界のループバックを
もう一方の IGP に載せています。IS-IS では次のようになります。

```text
route-policy ABR-LOOPBACK
  if destination in (10.255.0.1/32) then
    pass
  endif
end-policy
router isis ACCESS
 address-family ipv4 unicast
  redistribute connected route-policy ABR-LOOPBACK
```

すると、アクセスのインスタンスの XR01 の LSP は、外部のフラグを立ててループバックを運び、RT04 はそれを通常のレベル 2 の
ルートとしてインストールします。

```console
RP/0/RP0/CPU0:XR01#show isis instance ACCESS database verbose XR01.00-00
  Metric: 10         IS-Extended RT04.00
  Metric: 10         IP-Extended 10.0.14.0/24
    Prefix Attribute Flags: X:0 R:0 N:0 E:0 A:0
  Metric: 0          IP-Extended 10.255.0.1/32
    Prefix Attribute Flags: X:1 R:0 N:0 E:0 A:0

RT04#show ip route | include ^i
i L2     10.255.0.1/32 [115/10] via 10.0.14.1, 00:00:36, Ethernet0/0
i L2     10.255.0.15/32 [115/20] via 10.0.45.15, 00:05:18, Ethernet0/1
```

ACCESS-1 で LDP が上がると、XR01 は RT04 と RT05 のループバックにもラベルを割り当て、RT01 と RT03 にもアドバタイズします。
RT01 と RT03 はその割り当てを保持しますが(リベラル リテンション)、使うためのルートを持っていません。

:::try
XR01 のループバックが無いとアクセス網がどうなるかを見ます。課題 M8-6 の後に行います。

1. XR01 の `router isis ACCESS` → `address-family ipv4 unicast` の下から `redistribute connected` を外してコミットします。
2. すぐに、そして 5 分後にもう一度、XR01 で `show mpls ldp neighbor brief`、RT04 で `show mpls ldp discovery detail` と
   `show ip route 10.255.0.1` を実行します。
3. 行を戻してコミットし、RT04 とのセッションが戻ることを確かめます。

結果の例: RT04 からは 10.255.0.1 へのルートがすぐに消え、ディスカバリは
`LDP Id: 10.255.0.1:0; no route to transport addr` と表示しました。すでにあった LDP セッションはすぐには終わらず、2 分半後も
両側で `Oper` のままで、4 分半後には消えていました。XR01 と RT05 の BGP セッションは約 2 分半で閉じました。顧客 A のトラフィックは
すぐに止まりました。RT05 が、RT02 のループバックのネクスト ホップ 10.255.0.1 に到達できなくなったからです。行を戻すと、RT04 と
RT05 との LDP と BGP のセッションは数秒で上がり、RT02 と RT05 の間の iBGP セッションも一緒に戻りました。
:::

## 3. BGP ラベル付きユニキャスト

### 3.1 アドレス ファミリー

RFC 8277 は、BGP でプレフィックスにラベルを結び付けます。アドレス ファミリーは AFI 1(IPv4)と SAFI 4 で、ラベルは NLRI の中で
プレフィックスと一緒に運ばれます。RFC 3107 を置き換えたものです。境界で効いてくる規則が 2 つあります。ネクスト ホップを変えずに
ルートを渡すスピーカーはラベルも変えてはならず、自分をネクスト ホップにするスピーカーは自分で結び付けたラベルをアドバタイズ
しなければなりません。

IOS XR では、ラベル付きユニキャストはネイバーのアドレス ファミリー `address-family ipv4 labeled-unicast` で、ルータの
アドレス ファミリー `ipv4 unicast` を前提とします。テーブルは 1 つだけです。`show bgp ipv4 unicast` はラベル付きのルートも表示し、
`show bgp ipv4 labeled-unicast labels` は受け取ったラベルとローカル ラベルを加えて表示します。リリース 6.2.1 以降は、同じ
ネイバーに両方のファミリーを持たせられます。XR01 と RT02 のセッションがそうです。XR01 自身の顧客サイト 10.30.0.0/16 は
ラベルを持たず、通常のユニキャストで送られるからです。

```console
RP/0/RP0/CPU0:XR01#show bgp neighbor 10.255.0.12 | include family
    Address family IPv4 Unicast: advertised and received
    Address family IPv4 Labeled-unicast: advertised and received
```

IOS では、`address-family ipv4` の下の `neighbor <アドレス> send-label` で、そのセッションが送るすべてのルートがラベル付き
ユニキャストになります。ラボでは、RT02 と RT05 がこの形で自分の Loopback0 と顧客 A のネットワークを送ります。どれも自分のルート
なので、ラベルは implicit null です(`show ip bgp labels` の in label に `imp-null` と表示されます)。RT02 は `send-label` を
加えられたとき XR01 とのセッションをリセットし、それ以降はラベル付きのルートだけを送りました。

### 3.2 ルート リフレクタでのネクスト ホップ セルフ

XR01 は RT02 と RT05 のルート リフレクタです。ルート リフレクタは、ネクスト ホップを変えずにルートを渡します(RFC 4456)。
Unified MPLS ではそれが問題になります。RT02 は RT05 のループバックを、RT05 のループバックをネクスト ホップとして受け取りますが、
コアにはそこへ到達できるものがありません。境界は自分をネクスト ホップにする必要があります。

IOS XR では、ネイバーのアドレス ファミリーの下の `next-hop-self` は、ルータがリフレクトするルートには適用されません。Cisco の
TAC 文書は、動作しない解決策の中に「next-hop-self does not work」を挙げ、動作する手順の先頭に `ibgp policy out
enforce-modifications` を置いています。これは `router bgp` の下のグローバルな行で、送信側の変更を、リフレクトする iBGP の
ルートにも適用させます。既定では無効です。`route-reflector-client` と `next-hop-self` はあってもこの行が無いと、RT02 は
ルートを変更されないまま受け取ります。

```console
RT02#show ip bgp 10.255.0.15
BGP routing table entry for 10.255.0.15/32, version 0
Paths: (1 available, no best path)
  Local
    10.255.0.15 (inaccessible) from 10.255.0.1 (10.255.0.1)
      Origin IGP, metric 0, localpref 100, valid, internal
      Originator: 10.255.0.15, Cluster list: 10.255.0.1
      mpls labels in/out nolabel/imp-null
```

ラベルは RT05 自身の implicit null で、ネクスト ホップが変わらないときに RFC 8277 が求めるとおり、変更されずに渡されています。
IOS で同じことをするのは `neighbor <アドレス> next-hop-self all` で、`all` がリフレクトするルートを含めます。

:::try
すべてが動いた状態から、強制の行を外してみます。課題 M8-7 の後に行います。

1. XR01 の `router bgp 65000` の下から `ibgp policy out enforce-modifications` を外してコミットします。
2. RT02 で `show ip bgp 10.255.0.15`、`show ip bgp summary`、`ping 10.50.0.1 source Loopback100` を実行します。
3. 行を戻してコミットし、同じ 3 つのコマンドをもう一度確かめます。

結果の例: RT02 には、ネクスト ホップ 10.255.0.15、ラベル `imp-null` の 10.255.0.15/32 への
パスが 1 本残りました。今回は IOS はそれを `best` と表示しました(課題 M8-7 の初期状態では、同じパスは `(inaccessible)` でした)が、
ping はすべて失われました。ネクスト ホップが自分自身の宛先であるルートは、どこにもつながりません。RT02 と RT05 の間のセッションは、
保持時間が切れていなかったので、アップのままに見えました。行を戻すと、数秒で RT02 のネクスト ホップは 10.255.0.1、ラベルは 24003 に
戻り、ping は通りました。
:::

### 3.3 ラベルの割り当て

XR01 が自分をネクスト ホップにするときは、自分のラベルをアドバタイズする必要があります。IOS XR は既定では BGP のラベルを
割り当てません。`router bgp` → `address-family ipv4 unicast` の下の `allocate-label all` はテーブルのすべてのルートにローカル
ラベルを割り当て、`allocate-label route-policy <名前>` はポリシーが通したルートだけに割り当てます。ローカル ラベルを持たない
ラベル付きのルートは、XR01 をネクスト ホップとして受け取るラベル付きユニキャストのネイバーにはアドバタイズされません。
そのため、`enforce-modifications` はあっても `allocate-label` が無いと、ループバックは RT02 と RT05 から消えました。

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 labeled-unicast 10.255.0.15/32
Paths: (1 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
  Local, (Received from a RR-client)
    10.255.0.15 (metric 30) from 10.255.0.15 (10.255.0.15)
      Received Label 3
      Origin IGP, metric 0, localpref 100, valid, internal, best, group-best, labeled-unicast
```

`enforce-modifications` が無ければ、`allocate-label` だけを入れてもネイバーから見えるものは何も変わりません。ネクスト ホップは
変わらないままで、ラベルも変わりません。2 つの行がそろって初めて動作します。両方があると、XR01 はすべてのルートにローカル
ラベルを持ちます。

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 labeled-unicast labels
   Network            Next Hop        Rcvd Label      Local Label
*>i10.20.0.0/16       10.255.0.12     3               24005
*> 10.30.0.0/16       0.0.0.0         nolabel         3
*>i10.50.0.0/16       10.255.0.15     3               24006
*>i10.255.0.12/32     10.255.0.12     3               24001
*>i10.255.0.15/32     10.255.0.15     3               24003
```

:::try
すべてが動いた状態から、ラベルの割り当てを外してみます。課題 M8-7 の後に行います。

1. XR01 の `router bgp 65000` → `address-family ipv4 unicast` の下から `allocate-label` を外してコミットします。
2. XR01 で `show bgp ipv4 labeled-unicast 10.255.0.15/32` を、RT02 で `show ip bgp labels` と
   `ping 10.50.0.1 source Loopback100` を実行します。
3. 行を戻してコミットします。

結果の例: XR01 は 10.255.0.15/32 について `Not advertised to any peer` と表示し、RT02 の
`show ip bgp labels` からループバックが消えました。10.50.0.0/16 には RT05 からのパスだけが残り、RT02 はそのネクスト ホップに
到達できず、ping はすべて失われました。行を戻すと、どちらも XR01 のラベル(24003 と 24006)付きで戻り、ping は通りました。
:::

### 3.4 ラベルをたどる

XR01 の各ループバック用の BGP のラベルは、そのプレフィックス用の LDP のラベルと同じ番号でした(10.255.0.15/32 は 24003、
10.255.0.12/32 は 24001)。転送テーブルにも 1 行だけです。ルート自体は XR01 のルーティング テーブルで IS-IS のルートのままです。
IS-IS(115)のほうが iBGP(200)よりアドミニストレーティブ ディスタンスが小さいからです。その行は、PE へ向かう LDP のラベルに
付け替えます。

```console
RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24001  16          10.255.0.12/32     Gi0/0/0/0    10.0.1.11       3627
24003  16          10.255.0.15/32     Gi0/0/0/2    10.0.14.14      1673
24005  Pop         10.20.0.0/16                    10.255.0.12     0
24006  Pop         10.50.0.0/16                    10.255.0.15     0
```

`allocate-label all` では、2 つの顧客ネットワークにもラベルが付きます。XR01 は自分のラベルを取り除き、そのパスのラベルを付けて
PE のループバックへ向けてパケットを送ります。RT02 では、RT05 のループバックへのルートが再帰的に解決されます。下に XR01 の
ラベル 24003、その上に RT01 の XR01 用のラベル 20 です。

```console
RT02#show ip cef 10.255.0.15 detail
10.255.0.15/32, epoch 0, flags [rib defined all labels]
  recursive via 10.255.0.1 label 24003
    nexthop 10.0.12.11 Ethernet0/0 label 20-(local:20)
```

## 4. その上に載るサービス

### 4.1 プロバイダー エッジの間の顧客ルート

ラベル付きユニキャストが運ぶのはトランスポート、つまり PE のループバックです。サービスは PE 同士で交換します。ラボでは、
RT02 と RT05 がループバック間で直接 iBGP を実行し、ネクスト ホップを変えずに顧客 A のネットワークを交換します。RT02 は
10.50.0.0/16 をネクスト ホップ 10.255.0.15 で学習し、そのネクスト ホップを XR01 からのラベル付きのルートで解決します。

```console
RT02#show ip cef 10.50.0.0 detail
10.50.0.0/16, epoch 0, flags [rib only nolabel, rib defined all labels]
  recursive via 10.255.0.15
    recursive via 10.255.0.1 label 24003
      nexthop 10.0.12.11 Ethernet0/0 label 20-(local:20)
```

RT02 と RT05 の間の TCP セッション自体も、ラベルを付けて XR01 を通ります。課題 M8-7 の前は、どちらの PE も相手のループバックへの
使えるルートを持たないので、このセッションはできません。

PE はこのセッションで自分のループバックを送ってはなりません。RT05 がここで自分のループバックを送ると、RT02 は
10.255.0.15/32 へのもう 1 本のパスを RT05 から持ち、そのネクスト ホップは 10.255.0.15 自身になります。RT02 のルーティングは
ループバックを自分自身に向け、顧客 A のトラフィックは止まります(`show ip cef` に `recursive via 10.255.0.15, unresolved` と
`recursive-looped`)。ラボの据え付けのルータは、このセッションで顧客のルートだけを送ります。

では、XR01 に顧客のルートもネクスト ホップを変えずにリフレクトさせればよいのではないでしょうか。そうしないのは、IOS は
`send-label` を設定するとすべてのルートにラベルを付けて送り、XR01 がリフレクトするラベル付きのルートは、ループバックと同じく
XR01 をネクスト ホップにするからです。3.3 節の `allocate-label all` がまさにそうで、XR01 は顧客 A のネットワークを、自分を
ネクスト ホップにしてリフレクトしました。サービスの通常の答えは別のアドレス ファミリーで、レイヤ 3 VPN なら VPNv4 です(単元 M9)。

### 4.2 ループバックだけのラベル

`allocate-label route-policy` を使うと、XR01 は境界が運ぶべきものにだけラベルを割り当てます。10.255.0.0/24 の /32 のルートを
通すポリシーでは、顧客ネットワークはローカル ラベルを持たず、XR01 はそれらをリフレクトしなくなります。

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 labeled-unicast labels
   Network            Next Hop        Rcvd Label      Local Label
*>i10.20.0.0/16       10.255.0.12     3               nolabel
*>i10.50.0.0/16       10.255.0.15     3               nolabel
*>i10.255.0.12/32     10.255.0.12     3               24001
*>i10.255.0.15/32     10.255.0.15     3               24003

RP/0/RP0/CPU0:XR01#show bgp ipv4 labeled-unicast neighbors 10.255.0.12 advertised-routes
Network            Next Hop        From            AS Path
10.255.0.12/32     10.255.0.1      10.255.0.12     i
10.255.0.15/32     10.255.0.1      10.255.0.15     i
```

XR01 自身の 10.30.0.0/16 もラベルを失います。それでも同じセッションの通常のユニキャストのファミリーで RT02 に届きます。
IOS XR で 1 つのネイバーに 2 つのファミリーを持たせると、こう動きます。Seamless MPLS のドラフトも境界の役目を同じ言葉で
述べています。境界は「MUST set then BGP NEXT-HOP to its own loopback」であり、「MUST allocate a new local MPLS label for
each labeled iBGP FEC that it reflects」です。

## 5. パスの確認

### 5.1 BGP の FEC への LSP ping

MPLS の LSP ping は、テストする FEC を指定します(M8 の最初のページの 6.1 節)。IOS の既定は LDP の FEC で、RT02 は
10.255.0.15/32 の LDP のラベルを持たないので、要求は送られません(`Q`)。`fec-type bgp` は BGP のラベル付きの FEC をテストします。

```console
RT02#ping mpls ipv4 10.255.0.15/32 fec-type bgp repeat 3
Sending 3, 72-byte MPLS Echos to BGP + Label IP FEC 10.255.0.15/32,
...
Success rate is 0 percent (0/3)

RT02#ping mpls ipv4 10.255.0.15/32 fec-type bgp source 10.255.0.12 repeat 3
Sending 3, 72-byte MPLS Echos to BGP + Label IP FEC 10.255.0.15/32,
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/2/3 ms
```

最初のテストには応答がありませんでした。エグレスは、要求の送信元アドレスに向けて、通常の UDP パケットで応答を送ります。
既定の送信元は RT02 の出力インターフェイスのアドレス 10.0.12.12 で、RT05 はコアのリンクへのルートを持っていません。RT02 の
Loopback0 を送信元にすると、応答はラベル付きのルートをたどって戻ってきました。LSP traceroute は各ルータから見たラベルを表示し、
RT02 へ戻るルートをまったく持たないアクセスのルータ RT04 では `.` になります。

```console
RT02#traceroute mpls ipv4 10.255.0.15/32 fec-type bgp source 10.255.0.12 timeout 1 ttl 6
  0 10.0.12.12 MRU 1500 [Labels: 20/24003 Exp: 0/0]
L 1 10.0.12.11 MRU 1500 [Labels: explicit-null/24003 Exp: 0/0] 1 ms
L 2 10.0.1.1 MRU 1500 [Labels: 16 Exp: 0] 2 ms
. 3 *
! 4 10.0.45.15 3 ms
```

XR01 自身では、10.255.0.15/32 へのルートは LDP のラベルを持つ IS-IS のルートで、`fec-type bgp` は送られませんでした(`Q`)。
既定の LDP の FEC と `fec-type generic` は動作しました。XR01 がホップ 2 で応答するのは、課題 M8-5 以降 `mpls oam` が
設定されているからです。

:::try
RT05 から RT02 へのパスを MPLS OAM でテストします。課題 M8-7 の後に行います。

1. RT05 で `ping mpls ipv4 10.255.0.12/32 repeat 3` を実行し、続けて `fec-type bgp` を付けたもの、
   `fec-type bgp source 10.255.0.15` を付けたものを実行します。
2. `traceroute mpls ipv4 10.255.0.12/32 fec-type bgp source 10.255.0.15 timeout 1 ttl 6` を実行します。

結果の例: FEC の種類を指定しない ping は送られませんでした(`QQQ`)。RT05 は 10.255.0.12/32 の
LDP のラベルを持っていないからです。`fec-type bgp` では要求は送られましたが応答は戻らず、送信元を 10.255.0.15 にすると 3 つとも
成功しました。traceroute は、RT05 を出るときに `21/24001`、RT04 で `explicit-null/24001`、XR01 でラベル 16、RT05 へ戻るルートを
持たない RT01 で `.`、RT02 で `!` を表示しました。
:::

### 5.2 2 つのラベルと MTU

ラベル 2 つで 8 バイト増えます。ラボの 1500 バイトのリンクでは、DF ビット付きで RT02 から RT05 へ通った最大の IP パケットは
1492 バイトで、1496 バイトは失敗しました。ラベルは XR01 の両側で 2 つです。コアでは LDP のラベルと BGP のラベル、アクセス網でも
RT05 は 2 つを積みます。XR01 用の自分の LDP のラベルと、RT02 のループバック用の XR01 の BGP のラベルです。

```console
RT02#ping 10.50.0.1 source Loopback100 size 1496 df-bit repeat 2
..
Success rate is 0 percent (0/2)

RT02#ping 10.50.0.1 source Loopback100 size 1492 df-bit repeat 2
!!
Success rate is 100 percent (2/2), round-trip min/avg/max = 2/2/3 ms
```

## 6. コマンドの対応

| IOS | IOS XR |
|---|---|
| `router isis <タグ>` | `router isis <タグ>`(複数のインスタンス。それぞれが独自のインターフェイスを持つ) |
| `redistribute connected route-map <名前>` | `redistribute connected route-policy <名前>` |
| `address-family ipv4` の下の `neighbor <アドレス> send-label` | ネイバーの下の `address-family ipv4 labeled-unicast` |
| `neighbor <アドレス> next-hop-self all` | ネイバーのアドレス ファミリーの下の `next-hop-self` と `ibgp policy out enforce-modifications` |
| — | `address-family ipv4 unicast` の下の `allocate-label {all \| route-policy <名前>}` |
| `show ip bgp labels` | `show bgp ipv4 labeled-unicast labels` |
| `ping mpls ipv4 <プレフィックス> fec-type bgp [source <アドレス>]` | `ping mpls ipv4 <プレフィックス> fec-type bgp` |

## 実践

ラボ **XRT-08** で、このページの M8 の課題に取り組みます。ラボは IOS XRd を使い、構築に約 4 分かかります。ラボ XRT-07 の
終わったところから始まります。

<p class="tolab"><a href="/_learn?id=XRT-08">ワークスペースでラボ XRT-08 を開く</a> — <a href="83-m8-practice-2.html">課題</a></p>

:::note
このページの出力は、IOS XRd 26.1.1 と、IOL 上の IOS XE 17.15 ルータ 5 台で取得しました(ラボ XRT-08)。秒数はそのラボで
測った値で、保証された値ではありません。

出典: Cisco の TAC 文書「Configure Unified MPLS in Cisco IOS XR」(2015 年、2017 年改訂。Unified MPLS の目的、next-hop-self と
`ibgp policy out enforce-modifications`、`allocate-label`、RPL による境界のループバックの再配送)、「Labeled and Unlabeled
Together on one BGP Neighbor on IOS-XR」(2020 年。1 つのテーブル、1 つのネイバーでの両ファミリー、どのファミリーがどのルートを
運ぶか)、「Cisco IOS-XR BGP with MPLS Designs」(2021 年)。Cisco 8000 の BGP のコマンド リファレンス(2026 年。ネイバーの
アドレス ファミリーとしてのラベル付きユニキャスト、`allocate-label`、`ibgp policy out enforce-modifications`)。Cisco 8000
(24.x と累積版)、ASR 9000(7.8.x、24.x)、NCS 5500(24.x)、NCS 540(26.x)の IS-IS のコンフィギュレーション ガイドの、複数の
インスタンスにまたがるインターフェイスの記述。Catalyst 9500 17.14 のガイド「Configuring Seamless MPLS」(`next-hop-self all`)と
Catalyst 9400 17.12 の BGP のラベル配布のガイド(`send-label`)。RFC 8277(BGP ラベル付きユニキャスト)と
draft-ietf-mpls-seamless-mpls-07(2014 年、失効)。いずれも 2026 年 10 月に確認。次の項目は、ラボ XRT-08 とその PoC での実測に
よるものです。境界の 2 つのインスタンスと両方に載せたループバック、再配送したループバックの外部のフラグ、
`enforce-modifications` が無いときのリフレクトされたルート、`allocate-label` が無いときの取り消し、BGP と LDP で同じラベルの番号、
`send-label` の後のセッションのリセット、PE 自身のループバックを経由する再帰、LSP ping とその送信元アドレス、ラベル 2 つでの MTU。
:::
