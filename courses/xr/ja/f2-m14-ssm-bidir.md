# M14 — もう 2 つのツリー: SSM と双方向 PIM

前のページでは PIM スパース モードを組みました。受信者は RP へ向けて参加し、ファーストホップ ルータは送信元ごとに RP へ
Register し、ラストホップ ルータが最短パス ツリーへ切り替えます。このページでは、PIM が作る残りの 2 種類のツリーを扱います。
SSM(送信元特定マルチキャスト)では受信者が送信元を指定し、ツリーは RP を通らずに受信者から
送信元へまっすぐ伸びます。双方向 PIM には共有ツリーしかなく、すべての送信者のパケットがその上を両方向に流れます。

ブループリントの 4.4.a の PIM-SSM と PIM-BIDIR、4.4.b の IGMPv3 にあたります。盤面は前のページと同じ XRT-16 です。

## 1. 何が嬉しいのか

### 1.1 困りごと: 送信元の分かっているチャネルと、全員が送る会議

プロバイダーは、盤面に 2 つのサービスを足します。1 つ目は、ヘッドエンドの SRC1 から送るテレビのチャネルです。セットトップ
ボックスは、それぞれのチャネルがどこから来るかを知っています。チャネルの一覧に、グループと送信元 192.168.1.1 の両方が
載っているからです。1 つのチャネルの送信元は 1 つで、最初のパケットが送られる前から分かっています。

2 つ目は会議です。SRC1、RCV2、RCV3 が 1 つのグループに参加し、どれもそのグループから受け取るだけでなく、そのグループへ
送ります。どの拠点もいつでも話せるので、送信元は拠点の数だけあり、どれも前もっては分かりません。

### 1.2 それ以前の手: すべて RP を通す

前のページの PIM スパース モードでも、どちらも運べます。ただし代償があります。

- **送信元が分かっている場合。** 受信者の IGMPv2 レポートはグループしか伝えないので、ラストホップ ルータの PE2 はまず
  RP の P1 へ向けて参加し、ファーストホップ ルータの PE1 は SRC1 を RP へ Register します。最初のパケットが共有ツリーで
  届いて初めて、PE2 は送信元を知り、PE1 との直結のリンクを通る最短パス ツリーへ切り替えます。受信者が初めから知っていた
  送信元を見つけるために、RP が要ります。
- **会議の場合。** 送る拠点はそれぞれ別々に RP へ Register され、最短パス ツリーへ切り替えたルータは、(*,G) のほかに
  送信者ごとに 1 つの (S,G) エントリを持ちます。送信者が 3 つなら、1 つのグループについてルータ 1 台に (S,G) が最大 3 つ。
  拠点が 100 なら 100 です。

どちらにしても、すべてのルータが RP を知っている必要があり、トラフィックが最後に RP を通るかどうかに関係なく、新しい
送信元のたびに RP が関わります。

### 1.3 2 つの答え: RP を使わない、または RP をすべての送信元の根にする

- **SSM: RP を使わない。** 受信者は IGMPv3 レポートで、グループと送信元の両方を指定します。ラストホップ ルータは送信元へ
  向けてまっすぐ参加し、途中のルータはそれぞれ 1 つの (S,G) エントリを持ちます。Register も共有ツリーも切り替えもありません。
  グループは、ふつう SSM 用に取ってある 232.0.0.0/8 から選びます。
- **双方向 PIM: RP をすべての送信元の根にする。** ツリーはグループごとに 1 本で、RP アドレスを根にした (*,G) です。
  送信者のパケットは、ツリーを RP へ向けて上り、受信者へ向けて下ります。Register も (S,G) もないので、ルータの状態は
  送信者の数が増えても増えません。

SSM は送信元の分かっている 1 対多(テレビのチャネルなど)に、双方向 PIM は多対多(会議など)に向きます。残りはスパース
モードのままです。3 つは同じルータの上で同時に動き、それぞれ自分のグループの範囲を受け持ちます(2.3 節と 3.4 節)。

## 2. 仕組み

XRT-16 では、SRC1 は PE1 の先に、RCV2 は PE2 の先にいます。RCV3 は PE3 と PE4 が共有する LAN の ACCESS-3 にいて、
ゲートウェイは PE4 です。P1 は前のページの RP です(Loopback0 10.255.0.11、全グループ)。PE2 から SRC1 への最短経路は
PE1 との直結のリンクで、RP へは P1 とのリンクです。

ACCESS-3 では PE4 が DR(アドレスの大きい方)、PE3 が IGMP クエリア(アドレスの小さい方)です。リンクのラベルは、
サブネットと両端のインターフェイスです。

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host}
  PE1: [1.8, 0]
  PE2: [4.6, 0]
  RCV2: {at: [6.4, 0], kind: host}
  P1: {at: [3.2, 1.4], label: "P1 (RP)"}
  PE4: {at: [4.6, 2.0], label: "PE4 (IOS XE)"}
  PE3: [3.2, 3.1]
  SW1: [4.6, 3.1]
  RCV3: {at: [6.4, 3.1], kind: host}
links:
  - [SRC1, PE1, "192.168.1.0/24\nGi0/0/0/2"]
  - [PE1, PE2, "10.0.12.0/24\nGi0/0/0/0 — Gi0/0/0/0"]
  - [PE2, RCV2, "192.168.2.0/24\nGi0/0/0/3"]
  - [PE1, P1, "10.0.1.0/24\nGi0/0/0/1 — Gi0/0/0/0"]
  - [P1, PE2, "10.0.2.0/24\nGi0/0/0/1 — Gi0/0/0/1"]
  - [P1, PE3, "10.0.3.0/24\nGi0/0/0/2 — Gi0/0/0/0"]
  - {a: PE2, b: PE4, label: "10.0.4.0/24\nGi0/0/0/2 — Et0/0", t: 0.62}
  - [PE3, SW1, "Gi0/0/0/1"]
  - {a: PE4, b: SW1, label: "Et0/1", t: 0.3}
  - [SW1, RCV3]
frames:
  - {label: "ACCESS-3 192.168.3.0/24(PE3 .252、PE4 .253、RCV3 .1)", nodes: [PE3, SW1, RCV3]}
:::

### 2.1 SSM: 受信者が送信元を指定する

IGMPv3(RFC 3376)では、ホストのレポートに送信元の一覧とフィルタ モードを載せられます。INCLUDE モードのホストは、
そのグループを一覧の送信元からだけ求めます。SSM がホストに求めるのはこれだけで、「232.1.1.1、INCLUDE 192.168.1.1」は
192.168.1.1 からのツリーをちょうど 1 本指します。IOS XR はこのレポートを `Router mode: INCLUDE` と表示し、送信元を
`Group source list` に出します(3.2 節)。

IGMPv1 と IGMPv2 レポートは、グループしか伝えません。SSM 範囲では、ルータにはそうした参加を送る先の RP も送信元も
ないので、レポートを捨てます。グループは IGMP テーブルにも載らず、受信者には何も届きません。そのため SSM には、ホストと、
ホストに面するルータのインターフェイスの両方で IGMPv3 が要ります。Cisco の SSM マッピングを使うと、バージョン 1 と 2 の
レポートに送信元を補えますが、ここでは使いません。

### 2.2 盤面の上の SSM: RP も Register もない

RCV2 が、SRC1(192.168.1.1)からの 232.1.1.1 に参加するところを追います。このグループは 232.0.0.0/8 の中にあり、
IOS XR は既定でこの範囲を SSM として扱います。

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host}
  PE1: [1.8, 0]
  PE2: [4.6, 0]
  RCV2: {at: [6.4, 0], kind: host}
  P1: {at: [3.2, 1.4], label: "P1 (RP): エントリなし"}
links:
  - [SRC1, PE1, "データ →"]
  - [PE1, PE2, "← (S,G) Join\nデータ →"]
  - [PE2, RCV2, "← IGMPv3: 232.1.1.1\n送信元 192.168.1.1\nデータ →"]
  - {a: PE1, b: P1, style: dashed}
  - {a: P1, b: PE2, style: dashed}
:::

1. RCV2 が IGMPv3 レポートを送ります: 232.1.1.1、INCLUDE 192.168.1.1。その LAN のルータは PE2 だけです。
2. PE2 は、232.1.1.1 が自分の SSM 範囲にあるので、RP を探しません。(192.168.1.1, 232.1.1.1) を作り、192.168.1.1 へ
   向かう RPF インターフェイス、つまり PE1 との直結のリンクの Gi0/0/0/0 から (S,G) Join を送ります。
3. PE1 は Gi0/0/0/0 で Join を受け、そのインターフェイスを (S,G) エントリに加えます。SRC1 は PE1 に直接つながっている
   ので、Join はそこで止まります。
4. SRC1 が送ります。PE1 は各パケットを Gi0/0/0/0 だけから送り出し、PE2 は Gi0/0/0/3 から RCV2 へ送ります。

RP の P1 は、232.1.1.1 のエントリを 1 つも持ちません。PE1 も Register を送りません。PE1 にとっても 232.1.1.1 は SSM の
範囲だからです。切り替えもありません。ほかのツリーが無いので、最初のパケットから最短パス ツリーを通ります。P1 は、誰からも
何も頼まれていません。

### 2.3 SSM 範囲

どのグループを SSM とするかはルータごとの設定で、SSM 範囲と呼びます。IOS XR の既定は 232.0.0.0/8 です。範囲を設定すると
既定は置き換わるので、232.0.0.0/8 も SSM のままにしたいなら、一覧に書く必要があります。IOS XE には、`ip pim ssm` を設定
するまで SSM 範囲がありません。232/8 なら `ip pim ssm default`、アクセス リストで指定するなら `ip pim ssm range` です。

すべてのルータで範囲がそろっている必要があります。どのルータも、自分が働く場所で、自分の範囲で判断するからです。
ファーストホップ ルータは、そのグループの送信元を RP へ Register するかを決めます。ラストホップ ルータは、レポートから
送信元への (S,G) Join を送るか、RP への (*,G) Join を送るかを決めます。途中のルータは、そのグループの (*,G) Join を
先へ送るかを決めます。範囲の違うルータは、自分のいる場所でツリーを切ります。

ACCESS-3 で、PE4 が DR の場合の例です。

- **PE4 の Ethernet0/1 が IOS XE の既定の IGMPv2。** SRC1 を指定した RCV3 の IGMPv3 レポートは PE4 のテーブルに
  載らず、PE4 は Join を送らないので、RCV3 には何も届きません。
- **PE4 が IGMPv3 だが `ip pim ssm` がない。** PE4 はレポートを記録しますが、232.1.1.1 をスパース モードのグループと
  みなし、RP へ向けて (*,232.1.1.1) Join を送ります。232.1.1.1 を SSM とみなす PE2 はそれを先へ送らず、P1 は何も
  持ちません。RCV3 には何も届きません。

どちらの場合も、XR の 4 台は正常に見えます。SSM 範囲として正しい表示をし、RCV2 には届き続けます。故障は PE4 にしか
現れません(3.2 節)。XR が間違っているわけではありません。故障の場所ではない、というだけです。

### 2.4 双方向 PIM: 1 本のツリーを、パケットが両方向に流れる

双方向 PIM(RFC 5015)は、スパース モードの共有ツリーだけを残し、その上をパケットが両方向に流れるようにします。双方向の
範囲のグループについて、すべてのルータは RP アドレスへ向かう (*,G) エントリを持ち、受信者は前のページの共有ツリーと
同じく、(*,G) Join でそれに参加します。

変わるのは送信者の側です。送信者からグループ宛てのパケットを受けたルータは、それを Register しません。パケットをツリーの
上へ送り、途中の各ルータは、グループの一覧にあるインターフェイスのうち、届いたインターフェイスを除くすべてからコピーを
送ります。RP へ向かうインターフェイスもその一覧に入っているので、パケットは上へ進み続け、コピーは受信者のいる枝を
下ります。どのルータも (S,G) エントリを作らず、最短パス ツリーへの切り替えもしません。

RP アドレスは、すべてのツリーが向かう根でしかありません。そこで Register を受けることも、カプセル化を解くこともありません。
Cisco の IOS XE の概要の文書は、RP アドレスがルータのものである必要さえないと書いています。設定例では、RP アドレスは
P1 の専用のループバック(Loopback1)の 10.255.1.11 で、Loopback0 のスパース モードの RP とは分けています。

ツリーの上のルータが持つのは、グループごとに 1 つの (*,G) です。送信者が 1 つでも 100 でも変わりません。SRC1 が送る
だけで参加していないとき、PE1 はそのグループのエントリを何も持ちませんが、パケットは受信者に届きます。PE1 は、双方向の
範囲のパケットを何でも RP へ向けて送り上げるからです。

代償は経路です。パケットはすべてツリーをたどります。盤面では、SRC1 から RCV2 へのパケットは P1 を通り、PE1 と PE2 の
直結のリンクは通りません。どちらのルータも、RP アドレスへの経路にそのリンクを使わないからです。盤面でいちばんの近道は、
会議のパケットを 1 つも運びません。

### 2.5 DF(Designated Forwarder)

上へ向かうパケットは、どのリンクでも、ちょうど 1 台が拾い上げる必要があります。そうでないと 2 回上がります。
そこで双方向 PIM は、すべてのリンクで、RP アドレスごとに 1 台を選びます。これが DF(Designated Forwarder)です。DF は、
そのリンクで RP アドレスへのユニキャスト経路がいちばん良いルータです。DF は、グループのパケットをその
リンクへ送り出してリンク上の受信者に届けます。リンク上の送信者からのパケットを拾い上げて RP へ送るのも、DF だけです。

図は、RP アドレス 10.255.1.11 の各リンクの DF です。P1 自身のリンクでは P1 が勝ちます(自分のループバックへの
経路は [0/0])。PE2 と PE4 のリンクでは、P1 までのリンクが PE2 は 1 本、PE4 は 2 本なので、PE2 が DF です。PE1 と PE2 の
リンクでは、どちらも P1 まで 1 本で、メトリックも同じ [115/10] です。DF はアドレスの大きい PE2 になります。ルータが
1 台だけの LAN では、そのルータが DF です。

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host}
  PE1: [1.8, 0]
  PE2: [4.6, 0]
  RCV2: {at: [6.4, 0], kind: host}
  P1: {at: [3.2, 1.4], label: "P1 (RP 10.255.1.11)"}
  PE4: {at: [4.6, 2.0], label: "PE4 (DR)"}
  PE3: [3.2, 3.1]
  SW1: [4.6, 3.1]
  RCV3: {at: [6.4, 3.1], kind: host}
links:
  - [SRC1, PE1, "DF: PE1"]
  - [PE1, PE2, "DF: PE2"]
  - [PE2, RCV2, "DF: PE2"]
  - [PE1, P1, "DF: P1"]
  - [P1, PE2, "DF: P1"]
  - [P1, PE3, "DF: P1"]
  - {a: PE2, b: PE4, label: "DF: PE2", t: 0.62}
  - [PE3, SW1]
  - [PE4, SW1]
  - [SW1, RCV3]
frames:
  - {label: "ACCESS-3: DF は PE3、DR は PE4", nodes: [PE3, SW1, RCV3]}
:::

ACCESS-3 が要点を示します。ここの DR は PE4(192.168.3.253、アドレスの大きい方)ですが、P1 までのリンクが PE3 は
1 本、PE4 は 2 本なので、DF は PE3 です。双方向 PIM でリンク上の受信者に届けるのは、DR ではなく DF です(IOS XE の設定ガイドと
RFC 5015)。

RCV3 のレポートは両方のルータに届きます。PE3 は RP へ向けて Join を送り、グループを ACCESS-3 へ送り出します。PE4 が
持つのは RP へ向かう上向きのエントリだけで、その下には何もありません。ACCESS-3 では、肩書きは PE4 が持ち、仕事は PE3 が
します。

### 2.6 押さえどころ

- SSM: 受信者が IGMPv3 の INCLUDE モードのレポートで送信元を指定し、ラストホップ ルータが送信元へまっすぐ (S,G) で参加する。
  RP も Register も切り替えもない。SSM 範囲の IGMPv1・IGMPv2 レポートは捨てられる。
- SSM 範囲: IOS XR の既定は 232/8。IOS XE は `ip pim ssm` を設定するまでなし。設定した範囲は既定を置き換える。
  すべてのルータでそろえる。
- 双方向 PIM: グループごとに、RP アドレスを根にした (*,G) が 1 つ。パケットは同じツリーを上り下りする。Register も
  (S,G) も最短パス ツリーもない。
- DF: リンクと RP アドレスごとに 1 台で、RP アドレスへの経路がいちばん良いルータ。リンク上の受信者に届け、リンク上の送信者の
  パケットを拾うのは、DR ではなく DF。
- RP アドレスは IGP に載せる。DF の選出もツリーも、そこへのユニキャスト経路に従う。

## 3. IOS XR で組む

### 3.1 SSM: 既定の範囲と、広げた範囲

232.0.0.0/8 なら、IOS XR には前のページの設定のほかに何も要りません。この範囲は既定で SSM で、IOS XR の IGMP は既定で
バージョン 3 なので、PE1・PE2・PE3 のホストに面するインターフェイスは、すでに INCLUDE モードのレポートを受け付けます。

もっと多くのグループを SSM にするには、PIM にアクセス リストを渡します。一覧は既定を置き換えるので、232.0.0.0/8 も
書きます。各行では、ふつう送信元を書く位置(最初のアドレス)にグループの範囲を、2 つ目の位置に `any` を書きます。
例では、XR の 4 台すべてに 239.100.0.0/16 を足します。

:::config PE1・PE2・P1・PE3 — 232.0.0.0/8 と 239.100.0.0/16 を SSM に
ipv4 access-list SSM-RANGE
 10 permit ipv4 232.0.0.0 0.255.255.255 any      ## 既定の範囲も残す。設定した一覧は既定を置き換える
 20 permit ipv4 239.100.0.0 0.0.255.255 any      ## 足す範囲
!
router pim
 address-family ipv4
  ssm range SSM-RANGE                            ## この一覧が permit するグループを、このルータで SSM にする
 !
!
:::

例では `ssm range` を `router pim` の `address-family ipv4` の下に置きました。コマンド リファレンスは `multicast-routing`
の `address-family ipv4` の下に置いています。どちらに置いても、`show pim group-map` の表示は同じでした。

IOS XE の PE4 には 2 つ要ります。SSM 範囲と、ホストに面するインターフェイス(ACCESS-3 の Ethernet0/1)の IGMPv3 です。
IOS XE の IGMP は、既定でバージョン 2 です。

:::config PE4(IOS XE)— 232.0.0.0/8 の SSM と、ACCESS-3 側の IGMPv3
ip pim ssm default                               ## 232.0.0.0/8 を SSM にする。ip pim ssm の行が無いと、どのグループも SSM でない
interface Ethernet0/1
 ip igmp version 3                               ## 既定のバージョン 2 では、RCV3 のバージョン 3 のレポートを記録しない
!
:::

:::config PE4(IOS XE)— XR のルータと同じ、広げた範囲
access-list 30 permit 232.0.0.0 0.255.255.255    ## グループの範囲を並べた標準アクセス リスト
access-list 30 permit 239.100.0.0 0.0.255.255
ip pim ssm range 30                              ## ip pim ssm default の代わりに
:::

:::drill xr-m14-4

### 3.2 SSM の確かめ方

まず範囲を見ます。`show pim group-map` は範囲ごとのモードを出します。SSM 範囲には RP がありません(`0.0.0.0`)。

```console
RP/0/RP0/CPU0:PE2#show pim group-map 232.1.1.1

IP PIM Group Mapping Table 
(* indicates group mappings being used) 
(+ indicates BSR group mappings active in MRIB) 

Group Range         Proto Client   Groups RP address      Info

232.0.0.0/8*        SSM   config   0      0.0.0.0         
```

試すには、RCV2 を IGMPv3 のホストにし、SRC1 を送信元に指定してグループに参加させます。そのあと PE2 の IGMP テーブルを
見ます。

```console
RCV2(config)#interface Ethernet0/0
RCV2(config-if)#ip igmp version 3
RCV2(config-if)#ip igmp join-group 232.1.1.1 source 192.168.1.1
RCV2(config-if)#end
RP/0/RP0/CPU0:PE2#show igmp groups 232.1.1.1 detail

Interface:	GigabitEthernet0/0/0/3
Group:		232.1.1.1
Uptime:		00:00:12
Router mode:	INCLUDE
Host mode:	INCLUDE
Last reporter:	192.168.2.1
Suppress:	0
EVPN Remote group: False (Stale: False)
Group source list:
  Source Address   Uptime    Expires   Fwd    EVPNRemoteRoute   Flags
  192.168.1.1      00:00:12  00:01:58  Yes    No                Remote 4
```

`Router mode: INCLUDE` で、一覧に送信元があります。レポートが送信元を指定した、ということです。次に SRC1 から送り、
経路に沿って PIM トポロジを読みます(抜粋。フラグの凡例は省きます)。

```console
SRC1#ping 232.1.1.1 repeat 10 timeout 1
Sending 10, 100-byte ICMP Echos to 232.1.1.1, timeout is 1 seconds:
Reply to request 0 from 192.168.2.1, 12 ms
Reply to request 1 from 192.168.2.1, 2 ms
...
Reply to request 9 from 192.168.2.1, 2 ms
RP/0/RP0/CPU0:PE2#show pim topology 232.1.1.1
...
(192.168.1.1,232.1.1.1)SPT SSM Up: 00:00:25 
JP: Join(00:00:23) RPF: GigabitEthernet0/0/0/0,10.0.12.1 Flags: 
  GigabitEthernet0/0/0/3      00:00:25  fwd LI LH 
RP/0/RP0/CPU0:P1#show pim topology 232.1.1.1
No PIM topology table entries found.
RP/0/RP0/CPU0:PE1#show pim topology 232.1.1.1
...
(192.168.1.1,232.1.1.1)SPT SSM Up: 00:00:29 
JP: Join(never) RPF: GigabitEthernet0/0/0/2,192.168.1.1* Flags: 
  GigabitEthernet0/0/0/0      00:00:29  fwd Join(00:03:00) 
```

- **`SPT SSM`**: SSM 範囲の (S,G) エントリ。このグループの (*,G) はありません。
- **PE2 の RPF** は、直結のリンク(Gi0/0/0/0、10.0.12.1)の先の PE1 を指し、受信者のインターフェイスには `LI`(IGMP から
  来たローカルの関心)と `LH`(ラストホップ)が付きます。
- **PE1 の RPF** は、Gi0/0/0/2 の SRC1 そのものを指します。Gi0/0/0/0 が一覧にあるのは、PE2 の Join がそこに届いた
  からです。エントリに `SR`(Register を送っている)のフラグはありません。
- **P1** は何も持ちません。RP は経路の上になく、このグループのことを知らされていません。

3.1 節で範囲を広げたあとは、`show pim group-map` に両方の SSM 範囲が並びます。

```console
RP/0/RP0/CPU0:PE2#show pim group-map
...
Group Range         Proto Client   Groups RP address      Info

224.0.1.39/32*      DM    perm     0      0.0.0.0         
224.0.1.40/32*      DM    perm     1      0.0.0.0         
224.0.0.0/24*       NO    perm     0      0.0.0.0         
239.100.0.0/16*     SSM   config   0      0.0.0.0         
232.0.0.0/8*        SSM   config   1      0.0.0.0         
224.0.0.0/4*        SM    config   2      10.255.0.11     RPF: Gi0/0/0/1,10.0.2.11
224.0.0.0/4         SM    static   0      0.0.0.0         RPF: Null,0.0.0.0
```

IOS XE では、`show ip mroute` が SSM のエントリに `s` のフラグを付けます。次の 1 つ目は、RCV3 が IGMPv3 で
(192.168.1.1, 232.1.1.1) に参加し、PE4 に `ip pim ssm` と Ethernet0/1 の IGMPv3 があるときです。2 つ目は、PE4 から
`ip pim ssm` を外したあとに、同じ参加を新しいグループ 232.1.1.3 で行ったときです。

```console
PE4#show ip mroute 232.1.1.1
IP Multicast Routing Table
Flags: D - Dense, S - Sparse, B - Bidir Group, s - SSM Group, C - Connected,
       L - Local, P - Pruned, R - RP-bit set, F - Register flag,
       T - SPT-bit set, J - Join SPT, M - MSDP created entry, E - Extranet,
       X - Proxy Join Timer Running, A - Candidate for MSDP Advertisement,
       U - URD, I - Received Source Specific Host Report, 
...
(192.168.1.1, 232.1.1.1), 00:00:32/00:02:27, flags: sTI
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:32/00:02:27, flags: 

PE4#show ip mroute 232.1.1.3
...
(*, 232.1.1.3), 00:00:31/00:02:34, RP 10.255.0.11, flags: SJC
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:31/00:02:34, flags: 
```

範囲があると、エントリは (S,G) で、`s`(SSM のグループ)、`T`(最短パス ツリーの上)、`I`(送信元を指定したレポートから
作った)が付きます。範囲がないと、同じレポートから RP 付きの (*,G) ができ、`S`(スパース)が付きます。XR が SSM として運ぶ
グループへの、スパース モードの参加です。

232.1.1.3 を SSM として扱う PE2 は、この Join を先へ送りませんでした。PE2 の
`show pim topology 232.1.1.3` にはエントリが無く、232.1.1.3 への ping には応答がありませんでした。

:::try
送信元を指定しない参加を、SSM のルータがどう扱うかを見ます。課題 M14-3 の後に行い、最後にホストを元に戻します。

1. RCV2 の `interface Ethernet0/0` に、`ip igmp version 2` と `ip igmp join-group 232.2.2.2` を設定します。
2. 15 秒ほど待ってから、PE2 で `show igmp groups 232.2.2.2 detail` と `show pim topology 232.2.2.2` を、RCV2 で
   `show ip igmp groups` を見ます。
3. RCV2 で、2 行とも外します(`no ip igmp join-group 232.2.2.2`、`no ip igmp version`)。

結果の例: PE2 は `No matching entries in IGMP` と `No PIM topology table entries found.` を返し、RCV2 は 232.2.2.2 を
自分のグループの一覧に出しました。ホストの側では参加済み、ルータの側には記録がありません。
:::

### 3.3 双方向 PIM

双方向 PIM に要るのは 2 つです。すべてのルータから届く RP アドレスと、すべてのルータでの、その RP で双方向にするグループの
一覧です。例では 239.2.0.0/16 を双方向にし、RP アドレス 10.255.1.11 を P1 の新しいループバックに置きます。前のページの
スパース モードの RP(10.255.0.11、全グループ)は残します。

図は、RCV3 が 239.2.2.2 へ送った 1 つのパケットを、RP アドレスまで上り、RCV2 と SRC1 まで下りるまで追います。3 台の
ホストはどれもグループに参加しています。図の番号にカーソルを置くと(スマホでは押すと)、その部分の設定が出ます。

:::walk
legend: "RCV3 からの 1 つのパケット。どのルータも持つのは (*,239.2.2.2) だけ。青い番号はルータに与えるもの。"
rows:
  - {node: RCV3, kind: host, say: ["239.2.2.2 へ送る(ping)", "_ACCESS-3 へ。PE3 と PE4 の両方に見える"]}
  - {wire: "[[IP 192.168.3.1 → 239.2.2.2]]"}
  - panel: PE3
    sub: "IOS XRd · ACCESS-3 の DF"
    items:
      - ref: 2
        head: "**双方向のグループ** `rp-address 10.255.1.11 BIDIR-GROUPS bidir`"
        say: ["239.2.2.2 は一覧にある → (*,G) BD、根は 10.255.1.11", "ACCESS-3 からパケットを拾うのは誰か。そのリンクの DF:"]
        match:
          - ["PE3 192.168.3.252  P1 までリンク 1 本  [115/10]", true, "DF"]
          - ["PE4 192.168.3.253  PE2 経由でリンク 2 本", false, "DF ではない"]
        then: ["→ RPF インターフェイス Gi0/0/0/0 から、10.255.1.11 へ向けて上へ"]
  - {wire: "[[IP 192.168.3.1 → 239.2.2.2]] _CORE-3 を上る"}
  - panel: P1
    sub: "10.255.1.11 は P1 の Loopback1"
    items:
      - ref: 1
        head: "**RP アドレス** `interface Loopback1`、IS-IS で passive"
        say: ["239.2.0.0/16 のツリーは、どのルータのものもこのアドレスへ向かう"]
      - say: ["(*,239.2.2.2): Join を送ってきたすべてのインターフェイスから。届いたインターフェイスは除く", "~→ PE2 への Gi0/0/0/1 と PE1 への Gi0/0/0/0。Gi0/0/0/2 へは戻さない"]
  - {wire: "[[IP 192.168.3.1 → 239.2.2.2]] _CORE-2 を下る"}
  - panel: PE2
    sub: "IOS XRd · ACCESS-2 の DF"
    items:
      - ref: 2
        head: "`rp-address 10.255.1.11 BIDIR-GROUPS bidir`"
        say: ["(*,239.2.2.2) BD は RCV2 のレポートから。(S,G) はない"]
        then: ["→ PE2 が DF の Gi0/0/0/3 へ"]
  - {node: RCV2, kind: host, say: ["受け取って答える"]}
  - aside: "P1 のもう 1 つのコピー"
    say: ["~Gi0/0/0/0 → ヘッドエンドの LAN の DF の PE1 → SRC1。SRC1 も答える"]
  - aside: "ACCESS-3 の PE4: DR だが DF ではない"
    say: ["~③ で PE4 でも 239.2.2.2 は双方向。Ethernet0/1 の DF は PE3", "~→ PE4 は上へも ACCESS-3 へも送らない。エントリは (*,G) で、フラグは `BP`"]
:::

:::config P1 — 双方向のグループ専用の RP アドレスを、IS-IS で広告する
interface Loopback1                              ## ① 双方向のグループのツリーが、すべて向かうアドレス
 ipv4 address 10.255.1.11 255.255.255.255
!
router isis CORE
 interface Loopback1                             ## ① すべてのルータが、ここへの経路を要る。DF の選出と RPF が使う
  passive                                        ## アドレスを広告する。ループバックに隣接は作らない
  address-family ipv4 unicast
  !
 !
!
:::

:::config PE1・PE2・P1・PE3 — 239.2.0.0/16 を、10.255.1.11 を根にした双方向のグループに
ipv4 access-list BIDIR-GROUPS
 10 permit ipv4 239.2.0.0 0.0.255.255 any        ## ② 双方向のグループ
!
router pim
 address-family ipv4
  rp-address 10.255.0.11                         ## 前のページから: スパース モード、全グループ(3.4 節)
  rp-address 10.255.1.11 BIDIR-GROUPS bidir      ## ② 一覧のグループを、10.255.1.11 を根にした双方向にする
 !
!
:::

:::config PE4(IOS XE)— 同じグループと RP アドレス
ip pim bidir-enable                              ## ③ PE4 では、これを入れるまで bidir のキーワードが拒まれる
access-list 20 permit 239.2.0.0 0.0.255.255      ## ③ 双方向のグループ
ip pim rp-address 10.255.0.11                    ## 前のページから: スパース モード、全グループ(3.4 節)
ip pim rp-address 10.255.1.11 20 bidir           ## ③ XR のルータと同じ RP アドレスとグループ
:::

IOS XR は、双方向 PIM のために何かを有効にする必要がありません。`show pim neighbor` のネイバーには、はじめから `B`
(bidir capable)のフラグが付いています。対応は機種によります。この仮想機では動きますが、Cisco 8000 の設定ガイドは、
Cisco 8000 では非対応と書いています。

PE4 では、`ip pim bidir-enable` を設定するまで、`ip pim rp-address` の `bidir` のキーワードが拒まれます(`% Invalid input`)。
`no ip pim bidir-enable` を入れると、双方向の `ip pim rp-address` の行も一緒に消えます。キーワードは、機能を入れて初めて
存在します。

:::drill xr-m14-5

### 3.4 2 つのスタティック RP が同じグループに当たるとき

例では、どのルータでも 239.2.2.2 が 2 つのスタティック RP に当たります。全グループの 10.255.0.11(スパース モード)と、
239.2.0.0/16 の 10.255.1.11(双方向)です。IOS XR と IOS XE は、違う規則でどちらかを選びます。

- **IOS XR は長い範囲を使う。** 239.2.0.0/16 は 224.0.0.0/4 より長いので、XR は 10.255.1.11 を双方向で使います。
  グループを 1 つ指定した `show pim group-map` は、使われている範囲を出します。これは RFC 7761 が書く最長一致と同じです。
  XR の文書には、この規則の記述がありません。
- **IOS XE はアドレスの最も大きい RP を使う。** `ip pim rp-address` のコマンド リファレンス(Catalyst 9600、IOS XE 17.13)
  には次のとおりあります: "If a multicast group is matched by the access list of more than one configured ip pim
  rp-address command, then the RP for the group is determined by the RP with the highest RP address configured."

```console
RP/0/RP0/CPU0:PE2#show pim group-map 239.2.2.2
...
Group Range         Proto Client   Groups RP address      Info

239.2.0.0/16*       BD    config   1      10.255.1.11     RPF: Gi0/0/0/1,10.0.2.11
PE4#show ip pim rp mapping
PIM Group-to-RP Mappings

Group(s): 224.0.0.0/4, Static
    RP: 10.255.0.11 (?)
Acl: 20, Static, Bidir Mode
    RP: 10.255.1.11 (?)
```

ここでは 2 つの規則の答えが一致します。10.255.1.11 は 10.255.0.11 より大きいので、PE4 も双方向の RP を選び、239.2.2.2 の
エントリは RP 10.255.1.11 と `B` のフラグを持ちます(3.5 節)。どちらの規則もはっきりしています。同じ規則ではない、
というだけです。

アドレスを入れ替えると、答えは分かれます。全グループのスパース モードの RP が 10.255.1.11、239.2.0.0/16 の双方向の RP が
10.255.0.11 なら、XR のルータは引き続き 239.2.2.2 を双方向で運びます(長い範囲)。ところが PE4 は、アドレスの大きい
10.255.1.11 に当て、スパース モードのグループとして扱います。

すると PE4 は、ACCESS-3 の DR として、RCV3 が送ったものを Register し、その (S,G) の状態を作ります。RCV3 は DF の PE3 を
通って受け取り続けるので、届くかどうかだけでは故障が見えません。見えるのは PE4 のエントリです((S,G) があり、`B` がない)。

IOS XE では、どのグループにも `ip pim rp-address` が 1 つだけ当たるようにします。スパース モードの RP には、双方向の範囲を
除いたアクセス リストを付けます。IOS XR では、どちらにしても長い範囲が勝ちます。

### 3.5 双方向 PIM の確かめ方

`show pim df winner` は、RP アドレスとインターフェイスごとに、そのリンクの DF と、DF の RP アドレスへの経路の値([AD/メトリック])
を出します。

```console
RP/0/RP0/CPU0:PE2#show pim df winner

RP               Interface                    DF Winner        Metrics
10.255.1.11      GigabitEthernet0/0/0/2       10.0.4.2         [115/10]
10.255.1.11      GigabitEthernet0/0/0/3       192.168.2.254    [115/10]
10.255.1.11      GigabitEthernet0/0/0/1       10.0.2.11        [0/0]
10.255.1.11      GigabitEthernet0/0/0/0       10.0.12.2        [115/10]
10.255.1.11      Loopback0                    10.255.0.2       [115/10]
RP/0/RP0/CPU0:PE3#show pim df winner

RP               Interface                    DF Winner        Metrics
10.255.1.11      GigabitEthernet0/0/0/1       192.168.3.252    [115/10]
10.255.1.11      GigabitEthernet0/0/0/0       10.0.3.11        [0/0]
10.255.1.11      Loopback0                    10.255.0.3       [115/10]
```

PE2 では、P1 へ向かう Gi0/0/0/1 の DF は P1 自身(10.0.2.11、[0/0])で、ほかのインターフェイスではどれも PE2 が DF です
(10.0.4.2・192.168.2.254・10.0.12.2 は PE2 自身のアドレス)。PE3 では、ACCESS-3(Gi0/0/0/1)の DF は PE3 自身の
192.168.3.252 です。

トポロジには、どのホストも送ったあとでも、`BD` の付いた (*,G) しかありません(抜粋):

```console
RP/0/RP0/CPU0:PE2#show pim topology 239.2.2.2
...
(*,239.2.2.2) BD Up: 00:00:58 RP: 10.255.1.11 
JP: Join(now) RPF: GigabitEthernet0/0/0/1,10.0.2.11 Flags: LH DSS 
  GigabitEthernet0/0/0/3      00:00:58  fwd LI LH 
RP/0/RP0/CPU0:PE2#show mrib route 239.2.2.2
...
(*,239.2.2.2) RPF nbr: 10.0.2.11 Flags: IA RPF Inherit: 239.2.0.0/16
  Up: 00:00:58
  Outgoing Interface List
    GigabitEthernet0/0/0/1 Flags: F, Up: 00:00:58
    GigabitEthernet0/0/0/3 Flags: F LI, Up: 00:00:58
RP/0/RP0/CPU0:P1#show pim topology 239.2.2.2
...
(*,239.2.2.2) BD Up: 00:00:58 RP: 10.255.1.11* 
JP: Join(never) RPF: Loopback1,10.255.1.11* Flags: 
  GigabitEthernet0/0/0/0      00:00:58  fwd Join(00:02:31) 
  GigabitEthernet0/0/0/1      00:00:56  fwd Join(00:02:33) 
  GigabitEthernet0/0/0/2      00:00:41  fwd Join(00:02:48) 
```

- **`BD`**: 双方向の範囲のエントリ。SRC1 も RCV3 も送ったのに、(S,G) の行がありません。
- **`DSS`**(Don't Signal Sources)が PE2 の (*,G) に付きます。`spt-threshold infinity` のときにも付くフラグで、どちらの
  場合もルータは (*,G) に留まります。
- **MRIB の発信インターフェイス リストに RPF インターフェイスがある**(Gi0/0/0/1、`F`)。これがツリーを双方向にしています。
  RCV2 が送ったものは P1 へ上ります。スパース モードのエントリは、RPF インターフェイスを別の着信インターフェイス リストに
  `A`(accept)で持ちます。このエントリには着信のリストが無く、受け付けるものを範囲から引き継ぎます(`IA`、`Inherit:
  239.2.0.0/16`)。
- **P1** が根です。`RP: 10.255.1.11*`(自分自身)、RPF は Loopback1 で、PE1・PE2・PE3 のそれぞれから Join を受けています。

IOS XE では、`show ip pim interface df` がインターフェイスごとの DF を出し(PE4 自身が DF の所に `*`)、`show ip mroute`
がエントリに `B` を付けます。

```console
PE4#show ip pim interface df
* implies this system is the DF
Interface                RP               DF Winner        Metric     Uptime
Ethernet0/1              10.255.1.11       192.168.3.252    10         00:00:08
Ethernet0/0              10.255.1.11       10.0.4.2         10         00:00:16
PE4#show ip mroute 239.2.2.2
...
(*, 239.2.2.2), 00:00:57/00:02:20, RP 10.255.1.11, flags: BP
  Bidir-Upstream: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/0, Bidir-Upstream/Sparse, 00:00:57/stopped, flags: 
```

PE4 はどこでも DF ではありません(`*` が無い)。エントリには `B`(bidir のグループ)と `P`(prune)が付き、中のインター
フェイスは上り口の Ethernet0/0 だけです。RCV3 が参加しているのに、Ethernet0/1 がありません。ACCESS-3 には PE3 が
届けるからです。

いちばん簡単な試験は、ホストからの ping です(抜粋)。参加したホストはどれも、要求ごとに 1 回ずつ答えます:

```console
RCV3#ping 239.2.2.2 repeat 10 timeout 1
Sending 10, 100-byte ICMP Echos to 239.2.2.2, timeout is 1 seconds:
Reply to request 0 from 192.168.3.1, 1 ms
Reply to request 0 from 192.168.1.1, 4 ms
Reply to request 0 from 192.168.2.1, 4 ms
...
Reply to request 9 from 192.168.3.1, 1 ms
Reply to request 9 from 192.168.1.1, 3 ms
Reply to request 9 from 192.168.2.1, 2 ms
```

192.168.3.1 は、自分の ping に答える RCV3 です。SRC1(192.168.1.1)と RCV2(192.168.2.1)が、ほかの 2 つのメンバーです。

### 3.6 落とし穴

- **`ip pim ssm` のない IOS XE**: そこでは、どのグループも SSM ではありません。PE4 は 232/8 の (*,G) Join を RP へ送り、
  PE2 はそれを先へ送らず、XR が正常に見えたまま RCV3 には何も届きません。
- **DR のホスト側のインターフェイスが IGMPv2**: IOS XE の既定です。RCV3 のバージョン 3 のレポートは記録されず、何も
  参加しません。
- **232/8 を書かずに設定した SSM 範囲**: 一覧は既定を置き換えるので、そのルータでは 232/8 が SSM でなくなります。
- **送信元を指定しない参加**: SSM 範囲では、IGMPv1・IGMPv2 レポートは捨てられます。ルータの IGMP テーブルには
  何もありませんが、ホストは参加済みと表示します。
- **バージョン 2 のまま残ったホスト**: ルータのインターフェイスがしばらく IGMPv2 だったなら、ホストはバージョン 2 で答え
  ます。インターフェイスをバージョン 3 に戻しても、すぐには戻りません。ホストは最後のバージョン 2 のクエリのあと、しばらく
  バージョン 2 を続け(クエリの間隔が 60 秒なら、RFC 3376 では 2 × 60 + 10 = 130 秒)、それまで SSM は届きません。
- **変えた直後に同じグループで試す**: 変える前に送られた Join が、そのホールド タイムの 210 秒まで、グループを流し続ける
  ことがあります。まだ誰も参加していないグループで試します。
- **PE4 の `ip pim bidir-enable`**: 無いと `bidir` のキーワードが拒まれます。`no ip pim bidir-enable` は、双方向の
  `ip pim rp-address` の行も一緒に消します。
- **IOS XE の `BIDIR` という名前のアクセス リスト**: `ip pim rp-address … BIDIR bidir` は、名前がキーワードとぶつかって
  `% Ambiguous command` になります。番号のアクセス リストなら通ります。
- **1 つのグループに 2 つのスタティック RP**: IOS XR は長い範囲を、IOS XE はアドレスの大きい RP を使います。IOS XE では一覧が
  重ならないようにします。
- **IS-IS に載っていない RP アドレス**: DF の選出もツリーも、RP アドレスへのユニキャスト経路に従います。RP アドレスを
  持つループバックを広告します。
- **届くかどうかだけで双方向 PIM を判断する**: モードを取り違えたルータがあっても、DF を通ってすべてのホストに届くことが
  あります。すべてのルータで、(S,G) エントリと `B` のフラグを見ます。
- **DR が受信者に届けると思い込む**: 双方向 PIM では DF が届けます。ACCESS-3 では PE4 のエントリに LAN のインターフェイスが
  無く、それで正しい状態です。

## 実践

ラボ **XRT-16** で課題 M14-3 と M14-4 に取り組みます。課題では、このページの例とは別の範囲と別の RP を使います。

<p class="tolab"><a href="/_learn?id=XRT-16">ワークスペースでラボ XRT-16 を開く</a> — <a href="f3-m14-practice-2.html">課題 M14-3、M14-4</a></p>

:::note
このページの出力は XRT-16 で取得しました。IOS XRd 26.1.1(PE1・PE2・P1・PE3)と、IOL の IOS XE 17.15(PE4 とホスト)
です。一部の結果は、PE1・PE2・P1 が同じ名前とアドレスを持ち(PE1 と PE2 は IOS XRv 9000 26.1.1)、共有 LAN の IOS XE 17.15
のルータを R5 と呼んでいた試験の盤面のものです。232.2.2.2 への IGMPv2 の参加、2.3 節の 2 つの故障、
SRC1 が送るだけのときに PE1 がエントリを持たないこと、ホストが IGMPv3 に戻るまでの時間(ルータのインターフェイスを
バージョン 3 に戻してから 103 秒と 136 秒の間)、変更のあとも前の Join がグループを流し続けたこと。アクセス リストの名前 `BIDIR`
の件は、それより前の IOL 17.15 での試験によるものです。
出典: Cisco 8000 と ASR 9000 の Multicast Command Reference(2026-09-11)(既定で 232/8 が SSM であること、設定した範囲が
既定を置き換えること、`ssm range` の置き場が `multicast-routing` の下であること、`ssm map` と、SSM 範囲の IGMPv1・IGMPv2
のレポートを捨てること)。Cisco 8000 の Multicast Configuration Guide、IOS XR 26.1.x〜26.3.x(Cisco 8000 では PIM Bidir を
非対応と記載)。IOS XE: IP Multicast PIM Configuration Guide(IOS XE 16.9)の「IP Multicast Technology Overview」(SSM には
IGMPv3 が要ること、双方向 PIM は (*,G) だけで転送し Register を使わず、RP アドレスはルータのものでなくてよいこと)、
Catalyst 9300 IP Multicast Routing Configuration Guide(IOS XE 17.15)の「Configuring PIM」(DF は RP へのユニキャスト
経路が最も好ましいルータ、双方向のグループの RP ごとに DF、双方向のグループには (*,G) だけ。要旨)、DR ではなく DF がリンク上の
受信者へ転送するという IOS XE のガイドの記述、Cisco IOS IP Multicast Command Reference(`ip pim ssm` は既定で無効、
`show ip mroute` のフラグ `s`・`I`・`B`)、Catalyst 9600 Command Reference(IOS XE 17.13)の `ip pim rp-address`(3.4 節に
引用)と `ip pim bidir-enable`。RFC 3376(IGMPv3、INCLUDE モード、ホストが古い版を続ける時間)、RFC 4604(3.5 節、SSM の
範囲のバージョン 1・2 のレポート)、RFC 4607(232/8)、RFC 5015(双方向 PIM と DF)、RFC 7761(4.7.1 節、グループの範囲の
最長一致。Join のホールド タイム 210 秒)。いずれも 2026 年 11 月に確認。
文書と機器が食い違う所・文書に記述が無い所: Cisco 8000 のガイドは双方向 PIM を非対応と書き、IOS XRd のマルチキャストに
触れた文書はありません。ここではどちらも IOS XRd と IOS XRv 9000 で動きました。1 つのグループに 2 つのスタティック RP が当たるときに
XR がどちらを選ぶかは XR の文書に書かれておらず、長い範囲が使われました。Catalyst 9600 のリファレンスは `ip pim bidir-enable`
を既定で有効と書いていますが、PE4(IOL 17.15)では設定するまで `bidir` のキーワードが拒まれました。コマンド リファレンスは
`ssm range` を `multicast-routing` の下に置き、26.1.1 の CLI のヘルプはそこを `cisco-support` と出します。同じ範囲は、そこでも
`router pim` の下でも効きました。`show pim df winner` は現行のコマンド リファレンスに無く、古い CRS のものにだけあります。
PE1 と PE2 のリンクでは、2 台のメトリックが同じで、アドレスの大きい方が DF になりました。同点の決め方は、上の文書では
確かめていません。
:::
