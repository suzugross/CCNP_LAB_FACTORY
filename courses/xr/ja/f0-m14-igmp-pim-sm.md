# M14 — 1 本の流れを大勢へ: IGMP と PIM スパース モード

前のページで、単元の全体を見渡しました。このページは、いちばん素直な場合から始めます。1 台のヘッドエンドが送り、
たくさんのセットトップ ボックスが見る、1 つのテレビのチャネルです。ボックスは IGMP で、自分のルータに何が欲しいかを
伝えます。ルータは PIM スパース モードで、ランデブー ポイント(RP)という待ち合わせ場所を通る、チャネルのツリーを作ります。

ブループリントの 4.4.a のうち PIM スパース モードと、4.4.b の IGMP バージョン 1・2・3 にあたります。盤面は XRT-16 で、
2 節の初めに描きます。SSM(Source-Specific Multicast)と双方向 PIM は「もう 2 つのツリー: SSM と双方向 PIM」のページで、RP を手で
設定せずに見つける方法、IPv6、切り分けは「RP の見つけ方、IPv6、切り分け」のページで扱います。

## 1. 何が嬉しいのか

### 1.1 困りごと: 1 つのチャネル、たくさんのセットトップ ボックス

XRT-16 では、SRC1 がプロバイダーのヘッドエンド(テレビのチャネルを送る側)の役を、RCV2 と RCV3 が顧客の家の
セットトップ ボックスの役をします。チャネルは、何時間も続くパケットの流れです。ボックスは、合わせているチャネルを、
合わせている間だけ欲しがります。そして見る人がチャネルを変えるたびに、ボックスもチャネルを変えます。

ボックスは別々のルータの先にいます。RCV2 は PE2 の先に、RCV3 は PE3 と PE4 が共有するアクセス LAN、ACCESS-3 にいます。
ヘッドエンドは、どのボックスが見ているかを知りません。実際のプロバイダーには、ボックスが 2 台、チャネルが 1 つ、
どころではない数があり、同じチャネルが多くのルータの先で同時に見られています。

### 1.2 それ以前の手: 受信者ごとに 1 部ずつか、全部へ流すか

- **受信者ごとのユニキャスト**: SRC1 が、ボックスごとに、そのボックス宛ての 1 部を送ります。ボックスが 2 台なら、
  どのパケットも HEADEND の線を 2 回通り、2 つの道が重なる線でもまた 2 回通ります。1,000 台なら 1,000 回です。
  ヘッドエンドは、誰が見ているかの一覧を持ち続けなければなりません。
- **ブロードキャスト**: ブロードキャストは 1 つの LAN の全ホストに届き、ルータで止まります。ほかのルータの先の
  ボックスには届かず、自分の LAN では、そのチャネルを見ていないホストにも届きます。
- **フラッド アンド プルーン**: 古い設計(PIM デンス モード)は、まず全グループを全部の線へ流し、受信者のいない
  ルータが、隣に止めるよう頼みます。誰も見ていない線にも、どのチャネルも最初の分は流れます。

1 つめは見る人の数だけチャネルを繰り返し、残りの 2 つは頼まれていない所へ送ります。どちらにしても、線が払います。

### 1.3 マルチキャストの答え: 1 本の線に 1 部

- **グループ宛てに 1 回だけ送る**: SRC1 は、各パケットを 1 回だけ、239.1.1.1 のようなグループ アドレス宛てに送ります。
  グループは「このチャネルが欲しい誰か」を表します。送信元アドレスは、SRC1 自身のユニキャスト アドレスのままです。
- **受信者は自分のルータに頼む**: ボックスは、自分の LAN のルータに、どのグループが欲しいかを IGMP で伝えます(2.2 節)。
  ヘッドエンドには、ボックスから何も届きません。
- **ルータがツリーを作る**: ルータどうしが PIM で、送信元から受信者のいる全ルータまでの配信ツリーを作ります。ルータは
  ツリーが枝分かれする所でだけパケットを複製するので、1 本の線を通るのは、その先で何台が見ていても多くて 1 部です。
- **ツリーは見る人に合わせて変わる**: ルータは、最初の受信者が参加した時にツリーに加わり、最後の受信者が去った時に
  抜けます。

盤面では、SRC1 から PE1 を通って PE2 へ 1 部が届き、PE2 が RCV2 の LAN 向けと PE4 向けに 1 部ずつ作ります。SRC1 が送る量は、
見ているボックスが 2 台でも 2,000 台でも同じです。どちらなのかを知る手段もありません。

## 2. 仕組み: 1 つのチャネルを SRC1 から RCV2 と RCV3 へ

XRT-16 のルータは 5 台です。PE1・PE2・P1・PE3 は IOS XRd 26.1.1、PE4 は IOS XE 17.15 で動き、SRC1・RCV2・RCV3 はホストの役を
する IOS XE のルータです。5 台とも IS-IS(インスタンス CORE、レベル 2)を動かします。

アクセスの線は passive なので、ACCESS-3 が PE3 と PE4 の間の通り道になることはありません。このページでは P1 が RP です。この仮想機では XRd も
マルチキャストを転送します。Cisco の文書には、XRd のマルチキャストの記述がありません(末尾の注記)。

:::topo
nodes:
  SRC1: {at: [-0.35, 0], kind: host, label: "SRC1 (ヘッドエンド)"}
  PE1: {at: [1.9, 0], label: "PE1"}
  PE2: {at: [5.1, 0], label: "PE2"}
  RCV2: {at: [7.5, 0], kind: host, label: "RCV2 (セットトップ ボックス)"}
  P1: {at: [3.5, 1.45], label: "P1 (RP 10.255.0.11)"}
  PE3: {at: [3.5, 2.9], label: "PE3"}
  PE4: {at: [5.1, 1.65], label: "PE4 (IOS XE)"}
  SW1: {at: [5.1, 2.9], label: "SW1"}
  RCV3: {at: [7.5, 2.9], kind: host, label: "RCV3 (セットトップ ボックス)"}
links:
  - {a: SRC1, b: PE1, label: "HEADEND", lb: "Gi0/0/0/2", t: 0.3, tb: 0.7}
  - {a: PE1, b: PE2, label: "10.0.12.0/24", la: "Gi0/0/0/0", lb: "Gi0/0/0/0", ta: 0.16, tb: 0.84}
  - {a: PE1, b: P1, label: "10.0.1.0/24", la: "Gi0/0/0/1", lb: "Gi0/0/0/0", ta: 0.18, tb: 0.82}
  - {a: P1, b: PE2, label: "10.0.2.0/24", la: "Gi0/0/0/1", lb: "Gi0/0/0/1", ta: 0.18, tb: 0.82}
  - {a: P1, b: PE3, label: "10.0.3.0/24", la: "Gi0/0/0/2", lb: "Gi0/0/0/0", ta: 0.22, tb: 0.78}
  - {a: PE2, b: PE4, label: "10.0.4.0/24", la: "Gi0/0/0/2", lb: "Et0/0", ta: 0.3, tb: 0.8}
  - {a: PE2, b: RCV2, label: "ACCESS-2", la: "Gi0/0/0/3", t: 0.75, ta: 0.3}
  - {a: PE3, b: SW1, la: "Gi0/0/0/1 .252", ta: 0.42}
  - {a: PE4, b: SW1, la: "Et0/1 .253", ta: 0.4}
  - {a: SW1, b: RCV3, lb: ".1", tb: 0.72}
frames:
  - {label: "ACCESS-3 192.168.3.0/24", nodes: [SW1, RCV3]}
:::

この盤面では、2 つのことがツリーの形を決めます。PE2 から SRC1 への最短の道は PE1 との直結の線ですが、RP へ向かう道は
P1 を通ります。そのため、RP を通るツリーと最短のツリーが PE2 で分かれます。また、ACCESS-3 には PE3(.252)と PE4(.253)の
2 台のルータがいて、RCV3 のデフォルト ゲートウェイは PE4 です。

グループに参加したホストは、そのグループ宛ての ping に答えます。そのため、SRC1 からグループ宛てに ping を打てば、
誰が受け取ったかが分かります。このページの例では、239.1.1.1 をテレビのチャネルにします。

### 2.1 グループ アドレス

マルチキャストのパケットの宛先は、ホストではなくグループです。IPv4 は、グループ用に 224.0.0.0/4(224.0.0.0〜
239.255.255.255)を取ってあります。送信元アドレスは、いつも送り手自身のユニキャスト アドレスです。グループなのは宛先だけです。

| 範囲 | 何に使うか | XRT-16 では |
|---|---|---|
| 224.0.0.0/24 | リンクローカル: 1 本のリンクの上のプロトコル用。ルータは転送せず、ふつう TTL 1 で送られる。224.0.0.1 は全ホスト、224.0.0.2 は全ルータ、224.0.0.13 は全 PIM ルータ、224.0.0.22 は IGMPv3 のレポート | XR のグループ マップでは、モード `NO` |
| 224.0.1.0〜238.255.255.255 | グローバル スコープのグループ。その中の 232.0.0.0/8 は SSM 用に取ってある(次の行) | — |
| 232.0.0.0/8 | SSM: 受信者が送信元も指定する(「もう 2 つのツリー」) | XR は既定で SSM として扱う |
| 239.0.0.0/8 | 管理スコープ: 1 つの組織の中で使う。ユニキャストのプライベート アドレスのようなもの | このページのテレビのチャネル |

ルータが範囲ごとにどう扱うかは、`show pim group-map` で分かります。次は、マルチキャストと RP を設定した後(3 節)の PE2 です。
`*` は使われている行の印です。224.0.1.39 と 224.0.1.40 は Auto-RP(RP の見つけ方の 1 つ。「RP の見つけ方」のページ)のものです。

```console
RP/0/RP0/CPU0:PE2#show pim group-map
IP PIM Group Mapping Table 
(* indicates group mappings being used) 
(+ indicates BSR group mappings active in MRIB) 

Group Range         Proto Client   Groups RP address      Info

224.0.1.39/32*      DM    perm     0      0.0.0.0         
224.0.1.40/32*      DM    perm     1      0.0.0.0         
224.0.0.0/24*       NO    perm     0      0.0.0.0         
232.0.0.0/8*        SSM   config   0      0.0.0.0         
224.0.0.0/4*        SM    config   0      10.255.0.11     RPF: Gi0/0/0/1,10.0.2.11
224.0.0.0/4         SM    static   0      0.0.0.0         RPF: Null,0.0.0.0
```

イーサネットの LAN では、グループ アドレスが MAC アドレスになります。01:00:5e の後ろに、グループ アドレスの下位 23 ビットを
付けたものです。グループ アドレスで変わりうるのは 28 ビット(224.0.0.0/4 が先頭の 4 ビットを決める)なので、5 ビットが
失われ、32 個のグループが 1 つの MAC アドレスを分け合います。

239.1.1.1 は 01:00:5e:01:01:01 になり、224.1.1.1 と 239.129.1.1 も
同じです。01:00:5e:01:01:01 を待つ NIC は 32 個のグループを全部取り込み、頼んでいないものはホストが IP アドレスを見て捨てます。
NIC から見れば、239.1.1.1 のチャネルと 239.129.1.1 のチャネルは同じチャネルです。

### 2.2 IGMP: 受信者が自分のルータに伝える

IGMP(Internet Group Management Protocol)は、ホストと、同じ LAN のルータの間だけで動きます。ルータが尋ね、ホストが答えます。
ルータどうしの間は PIM が引き継ぎます(2.4 節)。

- **クエリ**: LAN の 1 台のルータ(クエリア)が、どのグループが欲しいかを尋ねます。一般クエリは 224.0.0.1(全ホスト)宛てで、
  既定の間隔は IOS XR も IOS XE も 60 秒です。ホストには、答えるまで最大 10 秒(最大応答時間)が与えられます。
- **レポート**: ホストが、グループが欲しいと伝えます。参加した時と、クエリに答える時です。
- **Leave**(バージョン 2 から): ホストが、グループから抜けると 224.0.0.2(全ルータ)宛てに伝えます。クエリアはそのグループ
  だけについて尋ね(グループ固有クエリ)、last member query interval の間に誰も答えなければ、グループを消します。この間隔は
  IOS XR も IOS XE も 1 秒です。

| | IGMPv1 | IGMPv2 | IGMPv3 |
|---|---|---|---|
| レポートの中身 | グループ G が欲しい | グループ G が欲しい | グループ G が欲しい。この送信元からだけ(INCLUDE)か、これ以外の全送信元から(EXCLUDE) |
| グループから抜ける | メッセージなし: グループが時間切れで消える | Leave の後、グループ固有クエリ | 別のレポート: そのホストの G の送信元の一覧が「なし」に変わる |
| クエリの最大応答時間 | なし | あり | あり |
| 既定のバージョンである機器 | — | IOS XE(PE4 とホスト役) | IOS XR(PE1・PE2・P1・PE3) |

バージョン 3 のレポートは、すべて 224.0.0.22 宛てです。SSM にはバージョン 3 が要ります(「もう 2 つのツリー」)。ルータが古いバージョンで
尋ねると、ホストはそのバージョンに下げます。PE2 の RCV2 側のインターフェイスをバージョン 1 にすると、IOS XE のホストの
RCV2 は `Current IGMP host version is 1` と表示します(3.3 節)。

バージョン 2 と 3 では、LAN でいちばん小さい IP アドレスのルータがクエリアになります。PIM の DR(Designated Router。
2.4 節)は逆向きで、プライオリティの次にいちばん大きいアドレスで選ばれます。そのため、ルータが 2 台の LAN では、2 つの役目が
別々のルータに行くことがあります。ACCESS-3 がそうで、PE3(.252)がクエリア、PE4(.253)が DR です。

```console
RP/0/RP0/CPU0:PE3#show igmp interface GigabitEthernet0/0/0/1
GigabitEthernet0/0/0/1 is up, line protocol is up
  Internet address is 192.168.3.252/24
  IGMP_AFD is enabled on interface
  Multihoming is disabled on interface [Stale : False]
  Location is 0xe
  Current IGMP version is 3
  IGMP query interval is 60 seconds
  IGMP querier timeout is 125 seconds
  IGMP max query response time is 10 seconds
  Last member query response interval is 1 seconds
  IGMP activity: 43 joins, 40 leaves
  IGMP querying router is 192.168.3.252 (this system)
  Time elapsed since last query sent 00:00:52
  Time elapsed since IGMP router enabled 00:01:00
  Time elapsed since last report received 00:00:45
PE4#show ip igmp interface Ethernet0/1
Ethernet0/1 is up, line protocol is up
  Internet address is 192.168.3.253/24
  IGMP is enabled on interface
  Current IGMP host version is 2
  Current IGMP router version is 2
  IGMP query interval is 60 seconds
...
  IGMP max query response time is 10 seconds
...
  Multicast designated router (DR) is 192.168.3.253 (this system)
  IGMP querying router is 192.168.3.252  
```

PE3 はバージョン 3、PE4 はバージョン 2 で動いています。どちらも自分の既定です。RFC 3376 も IOS XR の文書も、1 つの LAN の
全ルータを 1 つのバージョンにそろえるよう求めています(RFC は、使われている中でいちばん古いバージョンにそろえるとしています)。
作った直後の ACCESS-3 は、この決まりから外れています。「もう 2 つのツリー」のページで、もう一度取り上げます。誰が尋ねるかについては
2 台の意見が一致しています。PE4 は PE3 をクエリアと表示します。

RCV2 は、IOS XE の既定のバージョン 2 でレポートします。PE2 は、どの参加もバージョン 3 の言い方で持ちます。送信元の一覧が空の
`EXCLUDE` は「全送信元」の意味です。`Expires` はカウントダウンし、レポートが来るたびに初めに戻ります。0 になると、
グループはそのインターフェイスから消えます。

```console
RP/0/RP0/CPU0:PE2#show igmp groups 239.1.1.1 detail
Interface:	GigabitEthernet0/0/0/3
Group:		239.1.1.1
Uptime:		00:00:19
Router mode:	EXCLUDE (Expires: 00:01:50)
Host mode:	INCLUDE
Last reporter:	192.168.2.1
Suppress:	0
EVPN Remote group: False (Stale: False)
Source list is empty
```

IPv6 では、同じプロトコルが別の名前で動きます。MLD(Multicast Listener Discovery)で、ICMPv6 で運ばれます。MLDv1 が IGMPv2
に、MLDv2 が IGMPv3 にあたり、IOS XR は既定で MLDv2 を動かします。IPv6 と一緒に、「RP の見つけ方」のページで扱います。

### 2.3 RPF: パケットは送信元へ戻る道の上から届かなければならない

ユニキャストの転送は、宛先だけを見ます。マルチキャストはそうはいきません。宛先はグループで、グループはメンバーのいる所
すべてです。そこでマルチキャストのルータは、代わりに送信元を見ます。パケットが、ルータ自身がそのパケットの送信元へ送る
時に使うインターフェイスから入ってきた時だけ、パケットを転送します。これが RPF(Reverse Path Forwarding)チェックで、
通らないパケットは捨てられます。共有ツリー(2.4 節)では、送信元の代わりに RP のアドレスでチェックします。

このチェックが無ければ、複製がぐるぐる回りかねません。PE1・P1・PE2 は三角形を作っていて、どのルータも、持っている枝の全部へ
複製するからです。チェックがあれば、どのルータもチャネルを 1 つのインターフェイスでしか受け取らず、それをほかの枝へ複製します。

そのインターフェイスは、ユニキャストのルーティング テーブルから決まります。PIM は自分のルーティング プロトコルを持ちません。
名前の「Protocol Independent」はその意味です。XRT-16 では、経路は IS-IS から来ます。PIM が何を見つけたかは `show pim rpf` で分かります。

```console
RP/0/RP0/CPU0:PE2#show pim rpf
Table: IPv4-Unicast-default
* 192.168.1.1/32 [115/10] 
    via GigabitEthernet0/0/0/0 with rpf neighbor 10.0.12.1
* 10.255.0.11/32 [115/10] 
    via GigabitEthernet0/0/0/1 with rpf neighbor 10.0.2.11
```

PE2 から見て、SRC1(192.168.1.1)は Gi0/0/0/0 の先、PE1(10.0.12.1)の向こうにあり、RP は Gi0/0/0/1 の先、P1 の向こうです。
PIM が Join をどこへ送るかも、同じ引き方で決まります。ルータは、送信元か RP へ向けて RPF ネイバーに Join を送ってツリーに加わり、
パケットは同じ道を逆にたどって降りてきます。ツリーは受信者の側から、逆向きに作られます。データは送信元から流れ、
頼みごとは送信元へ向かって流れます。

### 2.4 PIM スパース モード: RP を通る共有ツリー

PIM(Protocol Independent Multicast)は、ルータどうしの間で動きます。PIM のルータは、各インターフェイスに 30 秒ごとに Hello を
送り、PIM ネイバーを見つけます。LAN ごとに、ネイバーどうしで DR を選びます。DR プライオリティ(既定 1)のいちばん大きい
ルータが勝ち、同じならいちばん大きい IP アドレスのルータです。DR は、自分の LAN のホストのための仕事をします。受信者の
ためにツリーに加わり、送り手を Register します(2.5 節)。

スパース モードは、頼まれた所にだけグループを送ります。頼みごとには、送信元がどこにいるかを誰も知らないうちから行き先が
要ります。そこで、グループごとにランデブー ポイント(RP)を決めます。全ルータが、そのグループの待ち合わせ場所として知っている
1 台のルータです。受信者のルータは RP へ向けて Join し、送信元のことは RP に知らされます。RP から受信者までのツリーが
**共有ツリー**で、(*,G) と書きます。「どの送信元でも、グループ G」の意味です。

このページでは、P1 の Loopback0(10.255.0.11)が全グループの RP で、全ルータに手で設定してあります(3.2 節)。RCV2 と RCV3 が
参加するにつれて、239.1.1.1 の共有ツリーが 1 ホップずつ伸びていきます。番号は下の図と同じです。

- ① RCV2 が 239.1.1.1 をレポートします。PE2 は ACCESS-2 の唯一のルータなのでその DR で、エントリ (*,239.1.1.1) を作り、出力
  インターフェイス リストに Gi0/0/0/3 を入れます。
- ② PE2 はグループの RP(10.255.0.11)と、そこへの RPF インターフェイス(Gi0/0/0/1)を引き、P1 へ (*,G) の Join を送ります。
  P1 は RP なので、(*,239.1.1.1) を作り、出力インターフェイス リストに PE2 向けの Gi0/0/0/1 を入れます。ツリーには根ができ、
  それより上へは伸びません。
- ③ RCV3 が ACCESS-3 で 239.1.1.1 をレポートします。そこの DR の PE4 が (*,239.1.1.1) を作ります。
- ④ PE4 から RP への RPF ネイバーは PE2(10.0.4.2)なので、Join は PE2 へ行きます。PE2 は (*,239.1.1.1) をもう持っているので、
  出力インターフェイス リストに PE4 向けの Gi0/0/0/2 を足すだけで、P1 へは何も新しく送りません。上流への 1 つの Join が、
  その下の枝を全部まかないます。
- ⑤ PE3 も RCV3 のレポートを聞きますが、ACCESS-3 の DR ではないので、Join を送りません。PE3 は RP から 1 ホップの所にいます。
  それでも枝は PE4 を通ります。253 は 252 より大きいからです。

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host, label: "SRC1"}
  PE1: {at: [1.9, 0], label: "PE1"}
  PE2: {at: [5.1, 0], label: "PE2 (ACCESS-2 の DR)"}
  RCV2: {at: [7, 0], kind: host, label: "RCV2"}
  P1: {at: [3.5, 1.45], label: "P1 (RP)"}
  PE3: {at: [3.5, 2.9], label: "PE3 (クエリア・DR でない)"}
  PE4: {at: [5.1, 1.65], label: "PE4 (ACCESS-3 の DR)"}
  SW1: {at: [5.1, 2.9], label: "SW1"}
  RCV3: {at: [7, 2.9], kind: host, label: "RCV3"}
links:
  - {a: SRC1, b: PE1, style: dashed}
  - {a: PE1, b: PE2, style: dashed}
  - {a: PE1, b: P1, style: dashed}
  - {a: P1, b: PE2, label: "② (*,G) Join\nPE2 → P1"}
  - {a: P1, b: PE3, style: dashed}
  - {a: PE2, b: PE4, label: "④ (*,G) Join\nPE4 → PE2"}
  - {a: PE2, b: RCV2, label: "① IGMP レポート", t: 0.6}
  - {a: PE3, b: SW1, style: dashed, label: "⑤ Join なし", t: 0.45}
  - {a: PE4, b: SW1, label: "③ IGMP レポート", t: 0.5}
  - {a: SW1, b: RCV3}
:::

ツリーは、頼まれている間だけ保たれます。各ルータは 60 秒ごとに Join を送り直し、210 秒の間 Join が来なかった枝は消されます。
ルータの先の最後の受信者が去ると、ルータは上流へ Join の代わりに Prune を送ります。

PIM のエントリは `show pim topology` で見ます。次は、2 台のボックスが参加した後、SRC1 がまだ何も送っていない時の PE2・P1・
PE4・PE1 です。

```console
RP/0/RP0/CPU0:PE2#show pim topology 239.1.1.1
...
(*,239.1.1.1) SM Up: 00:00:20 RP: 10.255.0.11 
JP: Join(00:00:29) RPF: GigabitEthernet0/0/0/1,10.0.2.11 Flags: LH 
  GigabitEthernet0/0/0/2      00:00:17  fwd Join(00:03:12) 
  GigabitEthernet0/0/0/3      00:00:20  fwd LI LH 
RP/0/RP0/CPU0:P1#show pim topology 239.1.1.1
...
(*,239.1.1.1) SM Up: 00:00:22 RP: 10.255.0.11* 
JP: Join(never) RPF: Decapstunnel1,10.255.0.11 Flags: 
  GigabitEthernet0/0/0/1      00:00:22  fwd Join(00:03:07) 
PE4#show ip mroute 239.1.1.1
...
(*, 239.1.1.1), 00:00:21/00:02:41, RP 10.255.0.11, flags: SJC
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:21/00:02:41, flags: 
RP/0/RP0/CPU0:PE1#show pim topology 239.1.1.1
No PIM topology table entries found.
```

- `(*,239.1.1.1) SM … RP: 10.255.0.11`: スパース モードの共有ツリーのエントリと、その RP。
- `JP: Join(00:00:29)`: PE2 は上流に Join 済みで、29 秒後にまた Join を送る。
- `RPF: GigabitEthernet0/0/0/1,10.0.2.11`: RP への道。P1 を通る。
- `Flags: LH`: PE2 はラスト ホップ ルータ。自分の LAN に受信者がいる。
- `GigabitEthernet0/0/0/2 … fwd Join(00:03:12)`: PE4 の Join でできた枝。次の Join が来なければ、3 分 12 秒後に消える。
- `GigabitEthernet0/0/0/3 … fwd LI LH`: IGMP から来たローカルの受信者(local interest)。
- P1 の `JP: Join(never)` と `RPF: Decapstunnel1`: 根には、Join を送る上流がない(Decapstunnel は 2.5 節)。

PE4(IOS XE)では、同じツリーが `show ip mroute` に出ます。フラグ `SJC` は、スパース モード、J、つながったインターフェイスに
メンバーがいる、の意味です。J は、既定の設定ではパケットが届いた時に送信元ツリーへ加わることを表します(2.6 節)。SRC1 から
1 ホップの PE1 には、エントリが 1 つもありません。まだ誰も何も送っていないので、当然です。

### 2.5 Register: RP が送信元を知る方法

送り手に IGMP は要りません。SRC1 は、ただ 239.1.1.1 宛てに送り始めます。PE1 は SRC1 の LAN の DR、つまりファースト ホップ
ルータで、ツリーを持っていないグループ宛てのパケットを受け取ります。PE1 はグループの RP を引き、パケットを Register
メッセージに入れてそこへ送ります。マルチキャストのパケットを丸ごと、10.255.0.11 宛てのユニキャストの PIM パケットに入れた
ものです。P1 まではユニキャストのルーティングが運ぶので、ツリーは要りません。

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host, label: "SRC1"}
  PE1: {at: [1.9, 0], label: "PE1 (ファースト ホップ)"}
  PE2: {at: [5.1, 0], label: "PE2"}
  RCV2: {at: [7, 0], kind: host, label: "RCV2"}
  P1: {at: [3.5, 1.45], label: "P1 (RP)"}
  PE3: {at: [3.5, 2.9], label: "PE3"}
  PE4: {at: [5.1, 1.65], label: "PE4"}
  SW1: {at: [5.1, 2.9], label: "SW1"}
  RCV3: {at: [7, 2.9], kind: host, label: "RCV3"}
links:
  - {a: SRC1, b: PE1, label: "239.1.1.1 宛て", t: 0.4}
  - {a: PE1, b: PE2, style: dashed}
  - {a: PE1, b: P1, label: "① Register(ユニキャスト)PE1 → P1\n③ (S,G) Join P1 → PE1\n④ Register-Stop P1 → PE1"}
  - {a: P1, b: PE2, label: "② 共有ツリー\nP1 → PE2"}
  - {a: P1, b: PE3, style: dashed}
  - {a: PE2, b: PE4, label: "② 共有ツリー"}
  - {a: PE2, b: RCV2}
  - {a: PE3, b: SW1, style: dashed}
  - {a: PE4, b: SW1}
  - {a: SW1, b: RCV3}
:::

② P1 は Register からマルチキャストのパケットを取り出し、共有ツリーへ流します。最初のパケットは、この道で RCV2 と RCV3 に
届きます。

IOS XR は、取り出しをインターフェイスとして見せます。RP の上の送信元のエントリは、パケットが入ってくる
インターフェイスとして Decapstunnel を挙げます(ここでは Decapstunnel1。番号は決まっていません)。P1 の MFIB(3.5 節)は、
Register から取り出したパケットを 3 つ、共有ツリーへ送ったパケットを 2 つ(1 つ 100 バイト)と数えました。

```console
RP/0/RP0/CPU0:P1#show mfib route 239.1.1.1 detail
...
Forwarding/Replication Counts: Packets in/Packets out/Bytes out
Failure Counts: RPF / TTL / Empty Olist / Encap RL / Other
...
(192.168.1.1,239.1.1.1),  Flags:  , FMA: 0x0 ,
  Object-ID: 0xfffffffffffffffe 18446744073709551614
  Up: 00:00:17
  Last Used: 00:00:15
  SW Forwarding Counts: 3/2/200
  SW Replication Counts: 3/2/200
  SW Failure Counts: 0/0/0/0/0
...
  Decapstunnel1 Flags:  A, Up:00:00:15 [Object-ID: 0xfffffffffffffffe 18446744073709551614] 
```

③ Register は、始めのうちだけのものです。P1 は送信元ツリーにも加わります。PE1 を通って SRC1 へ向けて、(S,G) の Join を送ります。
(S,G) は「この送信元の、このグループ」の意味です。④ そのツリーを通って、パケットがそのままの形(ネイティブ)で P1 に届くと、
P1 は PE1 に Register-Stop を送り、PE1 は包むのをやめます。Register が届いた時にそのグループの受信者がいなければ、RP は
すぐに Register-Stop を返します。

RP の上の、送信元へ向かう (S,G) エントリは次のとおりです。この出力は 3.4 節のもので、そこではラスト ホップ ルータが共有ツリーに
留まるので、P1 はこの Join を持ち続けます。`RR` は Register を受け取った印です。既定のままだとこれがどうなるかは、次の節で見ます。

```console
RP/0/RP0/CPU0:P1#show pim topology 239.1.1.2
...
(*,239.1.1.2) SM Up: 00:00:40 RP: 10.255.0.11* 
JP: Join(never) RPF: Decapstunnel1,10.255.0.11 Flags: 
  GigabitEthernet0/0/0/1      00:00:40  fwd Join(00:02:49) 

(192.168.1.1,239.1.1.2)SPT SM Up: 00:00:21 
JP: Join(00:00:28) RPF: GigabitEthernet0/0/0/0,10.0.1.1 Flags: KAT(00:03:10) RA RR (00:04:15) 
  No interfaces in immediate olist
```

### 2.6 最短パス ツリーへの切り替え

共有ツリーはチャネルを PE1 → P1 → PE2 と運びますが、PE2 から SRC1 への最短の道は、PE1 との直結の線です。ラスト ホップ
ルータは、送信元が分かれば(共有ツリーを降りてきた最初のパケットに、そのアドレスが書いてある)、送信元に直接 Join できます。
IOS XR も IOS XE も、既定では最初のパケットが届いた時点でそうします。

- ① PE2 は、(192.168.1.1, 239.1.1.1) の (S,G) の Join を、SRC1 への RPF ネイバーである PE1 へ、Gi0/0/0/0 で送ります。PE1 は
  (S,G) の出力インターフェイス リストに Gi0/0/0/0 を足し、パケットは直結の線で PE2 に届くようになります。
- ② PE2 には、この送信元を共有ツリーで受け取る理由がもうありません。P1 へ (S,G,rpt) の Prune を送ります。1 つの送信元について、
  共有ツリーの上でだけ効く Prune です。P1 は、この送信元について Gi0/0/0/1 を `off` にします。
- ③ P1 には、自分から SRC1 のパケットを欲しがる相手がいなくなります。P1 自身の (S,G) エントリは Join をやめ(`JP: Null`)、
  PE1 の (S,G) エントリは PE2 向けにだけ送ります。
- ④ RCV3 のラスト ホップ ルータの PE4 も切り替えます。PE4 から SRC1 への RPF ネイバーは PE2 なので、(S,G) の Join は PE2 へ行き、
  PE2 は (S,G) エントリに Gi0/0/0/2 を足します。

:::topo
nodes:
  SRC1: {at: [0, 0], kind: host, label: "SRC1"}
  PE1: {at: [1.9, 0], label: "PE1"}
  PE2: {at: [5.1, 0], label: "PE2"}
  RCV2: {at: [7, 0], kind: host, label: "RCV2"}
  P1: {at: [3.5, 1.45], label: "P1 (RP)"}
  PE3: {at: [3.5, 2.9], label: "PE3"}
  PE4: {at: [5.1, 1.65], label: "PE4"}
  SW1: {at: [5.1, 2.9], label: "SW1"}
  RCV3: {at: [7, 2.9], kind: host, label: "RCV3"}
links:
  - {a: SRC1, b: PE1}
  - {a: PE1, b: PE2, label: "① (S,G) Join PE2 → PE1\n送信元ツリー: PE1 → PE2"}
  - {a: PE1, b: P1, style: dashed, label: "③ もう Join していない"}
  - {a: P1, b: PE2, style: dashed, label: "② (S,G,rpt) Prune\nPE2 → P1"}
  - {a: P1, b: PE3, style: dashed}
  - {a: PE2, b: PE4, label: "④ (S,G) Join\nPE4 → PE2"}
  - {a: PE2, b: RCV2}
  - {a: PE3, b: SW1, style: dashed}
  - {a: PE4, b: SW1}
  - {a: SW1, b: RCV3}
:::

SRC1 の 10 発の ping は、この間に送られました。最初の 2 発には返事がなく、3 発目にはどちらのボックスからも 2 回ずつ返事が
ありました。4 発目からは、どのボックスもどの要求にも 1 回ずつ答えました。

```console
# Sending と Reply の行だけを残した
SRC1#ping 239.1.1.1 repeat 10 timeout 1
Sending 10, 100-byte ICMP Echos to 239.1.1.1, timeout is 1 seconds:
Reply to request 2 from 192.168.2.1, 16 ms
Reply to request 2 from 192.168.3.1, 23 ms
Reply to request 3 from 192.168.2.1, 4 ms
Reply to request 3 from 192.168.3.1, 6 ms
Reply to request 3 from 192.168.2.1, 5 ms
Reply to request 3 from 192.168.3.1, 4 ms
Reply to request 4 from 192.168.2.1, 3 ms
Reply to request 4 from 192.168.3.1, 3 ms
Reply to request 5 from 192.168.2.1, 3 ms
Reply to request 5 from 192.168.3.1, 3 ms
...
```

その後の PE2・PE1・P1・PE4 の状態です。

```console
RP/0/RP0/CPU0:PE2#show pim topology 239.1.1.1
...
(*,239.1.1.1) SM Up: 00:00:43 RP: 10.255.0.11 
JP: Join(00:00:06) RPF: GigabitEthernet0/0/0/1,10.0.2.11 Flags: LH 
  GigabitEthernet0/0/0/2      00:00:41  fwd Join(00:02:48) 
  GigabitEthernet0/0/0/3      00:00:43  fwd LI LH 

(192.168.1.1,239.1.1.1)SPT SM Up: 00:00:14 
JP: Join(00:00:35) RPF: GigabitEthernet0/0/0/0,10.0.12.1 Flags: KAT(00:03:19) RA 
  GigabitEthernet0/0/0/2      00:00:14  fwd Join(00:03:15) 
RP/0/RP0/CPU0:PE1#show pim topology 239.1.1.1
...
(192.168.1.1,239.1.1.1)SPT SM Up: 00:00:12 
JP: Join(never) RPF: GigabitEthernet0/0/0/2,192.168.1.1* Flags: KAT(00:03:19) RA 
  GigabitEthernet0/0/0/0      00:00:10  fwd Join(00:03:19) 
RP/0/RP0/CPU0:P1#show pim topology 239.1.1.1
...
(*,239.1.1.1) SM Up: 00:00:41 RP: 10.255.0.11* 
JP: Join(never) RPF: Decapstunnel1,10.255.0.11 Flags: 
  GigabitEthernet0/0/0/1      00:00:41  fwd Join(00:02:48) 

(192.168.1.1,239.1.1.1)RPT SM Up: 00:00:11 RP: 10.255.0.11* 
JP: Prune(never) RPF: Decapstunnel1,10.255.0.11 Flags: KAT(00:03:21) RA DCC RR (00:04:23) 
  GigabitEthernet0/0/0/1      00:00:11  off Prune(00:03:18) 

(192.168.1.1,239.1.1.1) SM Up: 00:00:13 
JP: Null(never) RPF: GigabitEthernet0/0/0/0,10.0.1.1 Flags: KAT(00:03:21) RA DCC RR (00:04:23) 
  No interfaces in immediate olist
PE4#show ip mroute 239.1.1.1
...
(*, 239.1.1.1), 00:00:44/stopped, RP 10.255.0.11, flags: SJC
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:44/00:02:18, flags: 

(192.168.1.1, 239.1.1.1), 00:00:17/00:02:42, flags: JT
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:17/00:02:42, flags: 
```

- PE2 のエントリは 2 つです。(*,G) は残り、`(192.168.1.1,239.1.1.1)SPT` は `RPF: GigabitEthernet0/0/0/0,10.0.12.1`。直結の線を
  通る送信元ツリーで、PE4 への枝が Gi0/0/0/2 にあります。
- PE1 の (S,G) は、PE2 へ向かう Gi0/0/0/0 にだけ送ります。
- P1 のエントリは 3 つです。(*,G)、Gi0/0/0/1 が `off Prune(…)` の `(192.168.1.1,239.1.1.1)RPT`(PE2 の (S,G,rpt) の Prune)、
  そして `JP: Null` と `No interfaces in immediate olist` の (S,G) そのものです。
- PE4 の (S,G) のフラグは `JT` です。送信元ツリーに加わった(T: パケットがその上で届いている)の意味です。

共有ツリーはそのまま残ります。(*,G) のエントリは PE2・P1・PE4 に残り、移ったのは SRC1 のパケットだけです。代わりに状態が
増えます。送信元ツリーの上のルータは、グループの (*,G) とは別に、送信元ごとに (S,G) エントリを持ちます。グループを共有ツリーに
留めておくこともできます(3.4 節)。P1 は今も 239.1.1.1 の RP で、そのパケットを 1 つも運んでいません。

### 2.7 押さえどころ

- グループ アドレスは 224.0.0.0/4。224.0.0.0/24 はリンクローカル、232.0.0.0/8 は SSM、239.0.0.0/8 は 1 つの組織の中で使う。
  イーサネットでは 01:00:5e と下位 23 ビット。1 つの MAC アドレスに 32 個のグループ。
- IGMP はホストと自分のルータの間で動く。クエリ、レポート、(バージョン 2 から)Leave。バージョン 3 は送信元を足す。クエリアは
  いちばん小さいアドレス、DR はプライオリティ、次にいちばん大きいアドレス。既定は IOS XR がバージョン 3、IOS XE がバージョン 2。
- RPF: パケットを受け取るのは、ユニキャストのテーブルが示す送信元(共有ツリーでは RP)へのインターフェイスでだけ。Join も
  同じ道を上る。
- スパース モード: (*,G) の Join が、受信者の DR から RP まで 1 ホップずつ進み、60 秒ごとに送り直される。
- Register: ファースト ホップ ルータが、最初のパケットをユニキャストの Register に入れて RP へ送る。RP は送信元へ向けて (S,G) で
  Join し、それから Register-Stop を送る。
- 既定では、ラスト ホップ ルータが最初のパケットで最短パス ツリーへ切り替える。送信元へ向けて (S,G) の Join、RP へ向けて
  (S,G,rpt) の Prune。

## 3. IOS XR で組む

### 3.1 マルチキャストを有効にする: multicast-routing・router pim・router igmp

IOS XR は、マルチキャストを 3 つの設定の塊に分けて持ちます。`multicast-routing` は、どのインターフェイスが加わるかを
アドレス ファミリごとに決めます。`router pim` は PIM の設定を持ちます。RP、送信元ツリーへの切り替え、DR プライオリティのような
インターフェイスごとの設定です。`router igmp` は IGMP の設定を持ちます。バージョンと、ルータ自身が参加するグループです。

既定では、どのインターフェイスも有効になっておらず、それを変えるのは `multicast-routing` だけです。ここでインターフェイスを
有効にすると、PIM(スパース モード)と IGMP の両方がそこで動き始めます。`multicast-routing` で有効にしていない
インターフェイスには、`router pim` や `router igmp` の下の `enable` と `disable` は効きません。

作った直後の XRT-16 では、`multicast-routing` には IPv6 のファミリ(前任者の試行)しかなく、IPv4 の PIM のインターフェイスは
1 つもありません。`router pim` だけを設定しても、何も変わりません。

```console
RP/0/RP0/CPU0:PE2#show pim interface
No interfaces found for VRF default.
RP/0/RP0/CPU0:PE2#show running-config multicast-routing
multicast-routing
 address-family ipv6
  interface all enable
 !
!
RP/0/RP0/CPU0:P1(config)#router pim
RP/0/RP0/CPU0:P1(config-pim)#address-family ipv4
RP/0/RP0/CPU0:P1(config-pim-default-ipv4)#rp-address 10.255.0.11
RP/0/RP0/CPU0:P1(config-pim-default-ipv4)#commit
RP/0/RP0/CPU0:P1(config-pim-default-ipv4)#end
RP/0/RP0/CPU0:P1#show pim interface
No interfaces found for VRF default.
```

これで RP にアドレスは付きました。RP として働くインターフェイスは、1 つもありません。

次の図は、RCV2 の 239.1.1.1 の頼みごとを RP までたどり、PE2 と P1 の設定の塊を、効く順に通ります。番号は、この節と次の節の
設定例の注記の番号と同じです。図の番号にカーソルを置くと(スマホでは押すと)、その部分の設定が出ます。

:::walk
legend: "RCV2 の 239.1.1.1 の頼みごとが、受信者から RP へ上っていく。青い番号: PE2 と P1 の設定。"
rows:
  - {node: RCV2, kind: host, say: ["Ethernet0/0 で `ip igmp join-group 239.1.1.1`", "~セットトップ ボックスがチャネルを頼む(IGMP バージョン 2)"]}
  - {wire: "[[IGMP レポート 239.1.1.1]] _ACCESS-2 の上"}
  - panel: PE2
    sub: ラスト ホップ ルータ(ACCESS-2 の DR とクエリア)
    items:
      - ref: 1
        head: "**マルチキャストを有効に** `multicast-routing`  `interface all enable`"
        say: ["Gi0/0/0/3 とコアの線で IGMP と PIM が動く"]
      - say: ["~IGMP が Gi0/0/0/3 に 239.1.1.1 を記録する(`router igmp`: 何も設定しない= 既定のまま)"]
      - ref: 2
        head: "**どの RP か** `rp-address 10.255.0.11`"
        say: ["239.1.1.1 は 224.0.0.0/4 に入る → RP は 10.255.0.11"]
        then: ["→ RP への RPF: Gi0/0/0/1、ネイバー 10.0.2.11", "→ (*,239.1.1.1)。出力インターフェイス リストに Gi0/0/0/3"]
  - {wire: "[[PIM Join (*,239.1.1.1)]] _Gi0/0/0/1 から P1 へ"}
  - panel: P1
    sub: RP
    items:
      - ref: 1
        head: "**マルチキャストを有効に** `interface all enable`"
        say: ["Gi0/0/0/1 の PIM が PE2 の Join を受け取る"]
      - ref: 2
        head: "**どの RP か** `rp-address 10.255.0.11`"
        say: ["RP は P1 自身の Loopback0"]
        then: ["→ (*,239.1.1.1)。RPF は `Decapstunnel1`(us): ツリーはここで止まる", "→ 出力インターフェイス リストに PE2 向けの Gi0/0/0/1"]
  - aside: "① なしで `router pim` だけ"
    say: ["~`show pim interface` → `No interfaces found for VRF default.` IGMP も PIM もツリーもない"]
  - aside: "① はあるが、Gi0/0/0/1 の PIM を止めた(`router pim` → `interface` → `disable`)"
    say: ["~PE2 の (*,G) は `RPF: Null,0.0.0.0` になり、PE2 は Join を送らない"]
:::

:::config IOS XR の全ルータ(PE1・PE2・P1・PE3)— 全インターフェイスで IPv4 のマルチキャストを有効に
multicast-routing                             ## ① どのインターフェイスがマルチキャストに加わるか(アドレス ファミリごと)
 address-family ipv4                          ## ① IPv4。IPv6 は別の address-family ipv6
  interface all enable                        ## ① Loopback0 も含む全インターフェイス: PIM(スパース モード)と IGMP(バージョン 3)
 !
!
:::

インターフェイスを 1 つずつ有効にすることもできます。同じアドレス ファミリの下で `interface <名前>` に入り、`enable` です。
同じやり方で `disable` を書けば、1 つのインターフェイスを `all` から外せます。コミットの後は、Loopback0 も含め、全部の
インターフェイスで PIM が動きます(`show pim interface`、3.5 節)。

### 3.2 スタティック RP

スタティック RP では、RP のアドレスを全ルータに手で教えます。どのルータにも同じアドレスを教えなければなりません。受信者の Join と
送信元の Register が、同じ 1 台のルータで落ち合う必要があるからです。ここでのアドレスは P1 の Loopback0 で、IS-IS が全ルータに
運びます。各ルータは、ユニキャストのテーブルでそこへの道を見つけます(`show pim rpf`、2.3 節)。

IOS XR では、`rp-address` を `router pim` のアドレス ファミリの下に書きます。ここでのようにアドレスの後ろにアクセス リストを
書かなければ、RP は 224.0.0.0/4 のうち、ほかの用途に取ってある範囲を除いた全部を受け持ちます。232.0.0.0/8 は SSM のまま
です(2.1 節のグループ マップ)。アドレスの後ろにグループのアクセス リストを書くと、RP はそのグループだけを受け持ちます。
「もう 2 つのツリー」のページで使います。

:::config IOS XR の全ルータ(PE1・PE2・P1・PE3)— P1 の Loopback0 を全グループの RP に
router pim                                    ## ② PIM 自身の設定
 address-family ipv4
  rp-address 10.255.0.11                      ## ② P1 の Loopback0。アクセス リストなし= 224.0.0.0/4 の全部
 !
!
:::

IOS XE では、マルチキャスト ルーティングをルータ全体で 1 回有効にし、PIM はインターフェイスごとに有効にします。IGMP は、
インターフェイスで PIM と一緒に動き始めます。`ip pim sparse-mode` だけを書いた後の PE4 の `show ip igmp interface` は、
`IGMP is enabled on interface` と表示します。

:::config PE4(IOS XE)— 両方の線でマルチキャストを有効にし、同じ RP を使う
ip multicast-routing                          ## IPv4 のマルチキャスト ルーティングをルータ全体で有効に
!
interface Ethernet0/0                         ## PE2 へ
 ip pim sparse-mode                           ## このインターフェイスで PIM(スパース モード)。IGMP も一緒に動く
!
interface Ethernet0/1                         ## ACCESS-3
 ip pim sparse-mode
!
ip pim rp-address 10.255.0.11                 ## IOS XR のルータと同じ RP
:::

P1 には自分自身のアドレスを設定してあり、P1 は自分が RP だと分かっています。グループ マップは、RP への RPF を自分の
Decapstunnel に向け、`(us)` を添えます。PE2 では、同じ行が P1 を指します(2.1 節)。

```console
RP/0/RP0/CPU0:P1#show pim group-map 239.1.1.1
IP PIM Group Mapping Table 
(* indicates group mappings being used) 
(+ indicates BSR group mappings active in MRIB) 

Group Range         Proto Client   Groups RP address      Info

224.0.0.0/4*        SM    config   0      10.255.0.11     RPF: De1,10.255.0.11 (us)
```

:::drill xr-m14-1

### 3.3 IGMP の設定: version・join-group・static-group

IGMP は、何も設定しなくても動き始めます。`multicast-routing` が、2.2 節の既定のまま、バージョン 3 で動かします。それを変えるのが
`router igmp` です。`version` は 1・2・3 を取り、全インターフェイス(`router igmp` の直下)にも、1 つのインターフェイスにも
書けます。ほかの 2 つのコマンドは、ルータ自身を、グループがインターフェイスへ来る理由にします。

- `join-group`: ルータが、そのインターフェイスで、ホストと同じようにグループに参加します。グループのパケットを自分の
  プロセッサへ取り込み、グループ宛ての ping に、そのインターフェイスの自分のアドレスから答えます。PIM はそのインターフェイスに
  `LI II` を付けます(II: internal interest)。
- `static-group`: ルータが、ホストが参加したかのように、そのインターフェイスへグループを転送します。ホストはいらず、ルータ
  自身はパケットを取り込みません。参加の期限は切れません。2 つのコマンドが同じグループを指すと、`join-group` が勝ちます。

:::config PE2 — ACCESS-2 を IGMP バージョン 2 にし、PE2 自身を 239.9.9.9 の受信者にする
router igmp                                   ## IGMP 自身の設定。この塊が無ければ既定のまま
 interface GigabitEthernet0/0/0/3             ## ACCESS-2。PE2 はここの DR
  version 2                                   ## 1・2・3(既定は 3): IOS XE のホストが始めるバージョン
  join-group 239.9.9.9                        ## PE2 が参加する: 239.9.9.9 宛ての ping に答える
 !
!
:::

:::config PE2 — 誰も頼んでいない ACCESS-2 へ 239.8.8.8 を流す
router igmp
 interface GigabitEthernet0/0/0/3             ## ACCESS-2(RCV2 側)
  static-group 239.8.8.8                      ## ホストが参加したかのように。参加の期限は切れない
 !
!
:::

:::config PE4(IOS XE)— 同じ 3 つの設定
interface Ethernet0/1                         ## ACCESS-3
 ip igmp version 2                            ## 1・2・3。2 は IOS XE の既定で、ここでは書き出しただけ
 ip igmp join-group 239.9.9.9                 ## PE4 自身が参加し、ping に答える
 ip igmp static-group 239.8.8.8               ## 誰も頼んでいなくても転送する
:::

PE2 の RCV2 側のインターフェイスをバージョン 1 にすると、PE2 の出力からクエリア、最大応答時間、last member query の行が消え、
RCV2 はバージョン 1 に下げました。

```console
RP/0/RP0/CPU0:PE2#show igmp interface GigabitEthernet0/0/0/3
GigabitEthernet0/0/0/3 is up, line protocol is up
  Internet address is 192.168.2.254/24
  IGMP_AFD is enabled on interface
  Multihoming is disabled on interface [Stale : False]
  Location is 0xe
  Current IGMP version is 1
  IGMP query interval is 60 seconds
  IGMP activity: 4 joins, 1 leaves
  Time elapsed since last query sent 00:00:01
  Time elapsed since IGMP router enabled 00:18:32
  Time elapsed since last report received 00:00:01
RCV2#show ip igmp interface Ethernet0/0
Ethernet0/0 is up, line protocol is up
  Internet address is 192.168.2.1/24
  IGMP is enabled on interface
  Current IGMP host version is 1
  Current IGMP router version is 2
...
```

PE2 に `static-group 239.8.8.8` を入れると、IGMP は `Expires: never` で、最後のレポーターを PE2 自身としてグループを載せ、
PIM はふつうの受信者と同じように共有ツリーに加わります。SRC1 の 239.8.8.8 宛ての ping には、誰も答えません。グループは
ACCESS-2 へ流れますが、そこで参加したホストはいないからです。

```console
RP/0/RP0/CPU0:PE2#show igmp groups 239.8.8.8 detail
Interface:	GigabitEthernet0/0/0/3
Group:		239.8.8.8
Uptime:		00:00:11
Router mode:	EXCLUDE (Expires: never)
Host mode:	EXCLUDE
Last reporter:	192.168.2.254
Suppress:	0
EVPN Remote group: False (Stale: False)
Source list is empty
RP/0/RP0/CPU0:PE2#show pim topology 239.8.8.8
...
(*,239.8.8.8) SM Up: 00:00:12 RP: 10.255.0.11 
JP: Join(00:00:37) RPF: GigabitEthernet0/0/0/1,10.0.2.11 Flags: LH 
  GigabitEthernet0/0/0/3      00:00:12  fwd LI LH 
SRC1#ping 239.8.8.8 repeat 5 timeout 1
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 239.8.8.8, timeout is 1 seconds:
.....
```

:::drill xr-m14-2

### 3.4 共有ツリーに留まる

既定では、ラスト ホップ ルータは最初のパケットで送信元ツリーへ切り替えます(2.6 節)。`router pim` の下の
`spt-threshold infinity` は、ルータを共有ツリーに留めます。後ろに `group-list` とアクセス リストを付けると、そのグループだけに
効きます。IOS XE にも同じコマンド `ip pim spt-threshold infinity` があります(`group-list` も付けられます)。

留まる理由はあります。チャネルを、そのために用意した線に載せておく(この盤面なら、PE1 と PE2 の直結の線を通さない)ため、
あるいは送信元ごとの (S,G) エントリをルータに持たせないためです。代わりに、トラフィックは RP を通ります。

この設定が効くのは、設定したルータの上の、そのルータが自分で始める切り替えにだけです。XRT-16 のラスト ホップ ルータは PE2
(RCV2 の分)と PE4(RCV3 の分)で、PE4 は Join を PE2 を通して送ります。PE4 が切り替えたままだと、その (S,G) の Join が PE2 に
届き、PE2 はそれを受けて、直結の線で送信元へ向かう (S,G) エントリを作ります。そのため、設定は両方に入れます。

:::config PE2 — どのグループも送信元ツリーへ切り替えない
router pim
 address-family ipv4
  spt-threshold infinity                      ## 共有ツリーに留まる。group-list <ACL> で一部のグループに絞れる
 !
!
:::

:::config PE4(IOS XE)— 同じ設定
ip pim spt-threshold infinity                 ## 全グループ。group-list <ACL> で絞れる
:::

両方に入れると、新しいグループ 239.1.1.2 宛ての SRC1 の ping には、どちらのボックスも 10 回答え、チャネルは PE1 → P1 → PE2 と
流れました。

PE2 にあるのは (*,G) だけで、`DSS`(Don't Signal Sources: PE2 は切り替えを始めない)が付いています。P1 は PE1 への
(S,G) の Join を持ち続け、パケットを共有ツリーへ流します。この仮想機では、P1 の MFIB が、Gi0/0/0/0 から入って Gi0/0/0/1 から
出たパケットを数えました。PE4 の (*,G) は `SC` で、J がありません。

```console
RP/0/RP0/CPU0:PE2#show pim topology 239.1.1.2
...
(*,239.1.1.2) SM Up: 00:00:38 RP: 10.255.0.11 
JP: Join(00:00:11) RPF: GigabitEthernet0/0/0/1,10.0.2.11 Flags: LH DSS 
  GigabitEthernet0/0/0/2      00:00:36  fwd Join(00:02:53) 
  GigabitEthernet0/0/0/3      00:00:38  fwd LI LH 
RP/0/RP0/CPU0:P1#show pim topology 239.1.1.2
...
(*,239.1.1.2) SM Up: 00:00:40 RP: 10.255.0.11* 
JP: Join(never) RPF: Decapstunnel1,10.255.0.11 Flags: 
  GigabitEthernet0/0/0/1      00:00:40  fwd Join(00:02:49) 

(192.168.1.1,239.1.1.2)SPT SM Up: 00:00:21 
JP: Join(00:00:28) RPF: GigabitEthernet0/0/0/0,10.0.1.1 Flags: KAT(00:03:10) RA RR (00:04:15) 
  No interfaces in immediate olist
RP/0/RP0/CPU0:P1#show mfib route 239.1.1.2 detail
...
(192.168.1.1,239.1.1.2),  Flags:  , FMA: 0x10000 ,
  Object-ID: 0xfffffffffffffffe 18446744073709551614
  Up: 00:00:21
  Last Used: 00:00:05
  SW Forwarding Counts: 13/12/1200
  SW Replication Counts: 13/12/1200
  SW Failure Counts: 0/0/0/0/0
...
  GigabitEthernet0/0/0/0 Flags:  A, Up:00:00:21 [Object-ID: 0xfffffffffffffffe 18446744073709551614] 
  GigabitEthernet0/0/0/1 Flags:  NS EG, Up:00:00:21 [Object-ID: 0xfffffffffffffffe 18446744073709551614] 
PE4#show ip mroute 239.1.1.2
...
(*, 239.1.1.2), 00:00:39/00:02:30, RP 10.255.0.11, flags: SC
  Incoming interface: Ethernet0/0, RPF nbr 10.0.4.2
  Outgoing interface list:
    Ethernet0/1, Forward/Sparse, 00:00:39/00:02:30, flags: 
```

:::try
下流のルータの既定が、PE2 の設定にどう効くかを確かめます。課題 M14-1 を終えた後、課題 M14-2 の前に行い、最後に必ず全部を
元に戻します。グループ 239.1.1.3 と 239.1.1.4 は、課題が使う範囲の外で、課題 M14-1 の RP の範囲の中です。

1. PE2 で、`router pim` → `address-family ipv4` の下に `spt-threshold infinity` を入れてコミットします。PE4 はそのままにします。
2. RCV2 と RCV3 で 239.1.1.3 に参加します(`interface Ethernet0/0` の下に `ip igmp join-group 239.1.1.3`)。15 秒ほど待って、
   SRC1 から ping します: `ping 239.1.1.3 repeat 10 timeout 1`。
3. PE2 と P1 で `show pim topology 239.1.1.3` を、PE4 で `show ip mroute 239.1.1.3` を見ます。PE2 にはどのエントリがあり、
   その (S,G) エントリはどちらを向いているでしょうか。
4. PE4 にも `ip pim spt-threshold infinity` を入れます。RCV2 と RCV3 を 239.1.1.4 に参加させ、SRC1 から ping し、239.1.1.4 に
   ついて同じ 3 つのコマンドを見ます。
5. 全部を元に戻します。PE2 で `no spt-threshold infinity`(とコミット)、PE4 で `no ip pim spt-threshold infinity`、RCV2 と RCV3
   で両方のグループの `no ip igmp join-group` です。

結果の例: PE2 だけに入れた時、どちらのボックスも ping を受け取りました。PE2 のエントリは 2 つで、フラグ `LH DSS` の (*,G) と、
`SPT` の印が付き、`RPF: GigabitEthernet0/0/0/0,10.0.12.1` で、Join を受けたインターフェイスが PE4 向けの Gi0/0/0/2 の (S,G)
でした。P1 には、送信元の `RPT` エントリがあり、Gi0/0/0/1 が `off Prune` でした。PE4 の既定が PE2 へ (S,G) の Join を送って
いて、PE2 は RCV2 の分も含めて、チャネルを直結の線で受け取りました。

PE4 にも入れた時は、PE2 には (*,G)(`LH DSS`)だけが
あり、PE4 の (*,G) のフラグは `SC`、P1 には PE1 へ向かう (S,G) エントリ(`RPF: GigabitEthernet0/0/0/0,10.0.1.1`)があり、
チャネルは PE1 → P1 → PE2 と流れました。
:::

:::drill xr-m14-3

### 3.5 状態の読み方

PE2 と PE4 の、PIM のインターフェイスとネイバーです。

```console
RP/0/RP0/CPU0:PE2#show pim interface
PIM interfaces in VRF default
Address               Interface                     PIM  Nbr   Hello  DR    DR
                                                         Count Intvl  Prior

10.255.0.2            Loopback0                     on   1     30     1     this system
10.0.12.2             GigabitEthernet0/0/0/0        on   2     30     1     this system
10.0.2.2              GigabitEthernet0/0/0/1        on   2     30     1     10.0.2.11
10.0.4.2              GigabitEthernet0/0/0/2        on   2     30     1     10.0.4.4
192.168.2.254         GigabitEthernet0/0/0/3        on   1     30     1     this system
RP/0/RP0/CPU0:PE2#show pim neighbor
PIM neighbors in VRF default
Flag: B - Bidir capable, P - Proxy capable, DR - Designated Router,
      E - ECMP Redirect capable, S - Sticky DR Neighbor
      * indicates the neighbor created for this router

Neighbor Address             Interface              Uptime    Expires  DR pri      Flags

10.0.12.1                    GigabitEthernet0/0/0/0 00:01:02  00:01:44 1           B
10.0.12.2*                   GigabitEthernet0/0/0/0 00:01:09  00:01:43 1           (DR) B E
10.0.2.2*                    GigabitEthernet0/0/0/1 00:01:09  00:01:15 1           B E
10.0.2.11                    GigabitEthernet0/0/0/1 00:00:56  00:01:43 1           (DR) B
10.255.0.2*                  Loopback0              00:01:09  00:01:43 1           (DR) B E
10.0.4.2*                    GigabitEthernet0/0/0/2 00:01:09  00:01:40 1           B
10.0.4.4                     GigabitEthernet0/0/0/2 00:00:50  00:01:24 1           (DR) P
192.168.2.254*               GigabitEthernet0/0/0/3 00:01:09  00:01:22 1           (DR) B E
PE4#show ip pim neighbor
PIM Neighbor Table
Mode: B - Bidir Capable, DR - Designated Router, N - Default DR Priority,
      P - Proxy Capable, S - State Refresh Capable, G - GenID Capable,
      L - DR Load-balancing Capable
Neighbor          Interface                Uptime/Expires    Ver   DR
Address                                                            Prio/Mode
192.168.3.252     Ethernet0/1              00:00:56/00:01:18 v2    1 / G
10.0.4.2          Ethernet0/0              00:00:57/00:01:32 v2    1 / G
```

- **ネイバーの数には、ルータ自身も入ります。** IOS XR は、どのインターフェイスでも自分を `*` 付きで載せます。Loopback0 の
  ネイバーは PE2 自身の 1 つ、Gi0/0/0/0 は PE1 と PE2 の 2 つです。
- **DR** は、`show pim interface` の最後の列に出て、ネイバーの中では `(DR)` の印が付きます。PE2 の線では、PE1 との線の DR は PE2
  (10.0.12.2 は 10.0.12.1 より大きい)、P1 との線は P1(10.0.2.11)、PE4 との線は PE4(10.0.4.4)です。
- **フラグ**は、各ネイバーに何ができるかを表します。IOS XR のルータは `B`(bidir capable)、PE4 は `P`(proxy capable)です。
  PE4 は、IOS XR のルータを `G`(GenID capable)付きで表示します。

| コマンド(IOS XR) | 読むところ |
|---|---|
| `show pim interface` | どのインターフェイスで PIM が動くか(`on`/`off`)、ネイバーの数、Hello の間隔、DR プライオリティと DR |
| `show pim neighbor` | インターフェイスごとのネイバー、DR、それぞれに何ができるか |
| `show igmp interface <IF>` | バージョン、タイマー、クエリア |
| `show igmp groups [<グループ>] [detail]` | インターフェイスごとのグループ、最後のレポーター、送信元の一覧 |
| `show pim group-map [<グループ>]` | グループがどの範囲に入るか、そのモード(`SM`・`SSM`・`DM`・`NO`)と RP |
| `show pim rpf [<アドレス>]` | 送信元か RP への RPF インターフェイスと RPF ネイバー、その元になった経路 |
| `show pim topology [<グループ>]` | PIM のエントリ: (*,G) と (S,G)、RPF ネイバーへの Join か Prune、出力インターフェイスごとの理由(`LI` は IGMP から、`Join` はネイバーから) |
| `show mrib route [<グループ>]` | PIM と IGMP から作るマルチキャストのルーティング テーブル: 受け取るインターフェイス(`A`)と転送するインターフェイス(`F`) |
| `show mfib route <グループ> detail` | 転送のエントリとパケットの数 |

「このルータはチャネルをどこで受け取り、どこへ送るか」にいちばん短く答えるのは `show mrib route` です。切り替えの後の PE2
では、(*,G) は Gi0/0/0/1(P1 から)で、(S,G) は Gi0/0/0/0(PE1 から)で受け取り、どちらも Gi0/0/0/2 と Gi0/0/0/3 へ転送します。

```console
RP/0/RP0/CPU0:PE2#show mrib route 239.1.1.1
...
(*,239.1.1.1) RPF nbr: 10.0.2.11 Flags: C RPF
  Up: 00:00:44
  Incoming Interface List
    GigabitEthernet0/0/0/1 Flags: A NS, Up: 00:00:44
  Outgoing Interface List
    GigabitEthernet0/0/0/2 Flags: F NS, Up: 00:00:41
    GigabitEthernet0/0/0/3 Flags: F NS LI, Up: 00:00:44

(192.168.1.1,239.1.1.1) RPF nbr: 10.0.12.1 Flags: RPF
  Up: 00:00:14
  Incoming Interface List
    GigabitEthernet0/0/0/0 Flags: A, Up: 00:00:14
  Outgoing Interface List
    GigabitEthernet0/0/0/2 Flags: F NS, Up: 00:00:14
    GigabitEthernet0/0/0/3 Flags: F NS, Up: 00:00:14
```

`show mfib route <グループ> detail` は数を数えます。この仮想機(IOS XRd)では、`SW Forwarding Counts` が、ルータが転送した
パケットに合わせて、入ったパケット・出たパケット・出たバイトの順に増えます。`SW Failure Counts` は、捨てたパケットを理由ごとに
数え、最初が RPF です。2.5 節では、この数で、P1 が取り出した Register を確かめました。

IOS XE では、`show ip mroute` が 1 つの表にこれを全部載せます。入力インターフェイスと RPF ネイバー、出力インターフェイス、
フラグ(`S` スパース、`C` つながったインターフェイスにメンバー、`J` 送信元ツリーへ加わる、`T` 送信元ツリーの上)です。
`show ip pim interface`・`show ip pim neighbor`・`show ip igmp interface` は、上の IOS XR のコマンドにあたります。

### 3.6 落とし穴

- **`multicast-routing` なしの `router pim`**: どのインターフェイスでも PIM も IGMP も動かない(`No interfaces found for VRF default.`)。
- **アドレス ファミリが片方だけ**: IPv4 と IPv6 は別々に有効にする。IPv6 の `interface all enable` は、IPv4 には何もしない。
- **RP を設定していないルータがある、または 1 台だけ別の RP**: 受信者の Join と送信元の Register は、同じルータに届かなければ
  ならない。別々のルータへ行くと、何も届かない。
- **RP へ向かうインターフェイスで PIM を止めた**: (*,G) は `RPF: Null,0.0.0.0`、`show pim interface` ではそのインターフェイスが `off`。
- **共有ツリーに留める設定が 1 台だけ**: 切り替える下流のルータが、どのみち (S,G) を引き込む(3.4 節)。設定は、全部のラスト
  ホップ ルータに入れる。
- **1 つの LAN に 2 つの IGMP のバージョン**: 既定は IOS XR がバージョン 3、IOS XE がバージョン 2。LAN の全ルータを 1 つの
  バージョンにそろえる。
- **LAN の DR でないルータの `join-group`**: グループを LAN へ流すのは DR で、そのコピーは、もう 1 台のルータには RPF チェックに
  合わないインターフェイスから届く。PE3 の ACCESS-3 のインターフェイスに `join-group 239.9.9.9` を置くと(そこの DR は PE4)、
  SRC1 の ping に答えたのは PE4 だけだった。ACCESS-2 の DR である PE2 に置くと、PE2 がすべてに答えた。
- **1 分前に使ったグループで試す**: Join と (S,G) エントリは、原因が無くなってから最大 210 秒残る。そのため、故障が何も変えて
  いないように見えることがある。新しいグループで試す。
- **RP の状態を消す**: RP で `clear pim topology` をすると、次の定期の Join まで(最大 60 秒)受信者には何も届かない。
- **`clear igmp groups`**: IOS XR のコマンドは単数形の `clear igmp group`。複数形は受け付けない。

## 実践

ラボ **XRT-16** で課題 M14-1 と M14-2 に取り組みます。ラボの初めの状態では、IPv4 のマルチキャストはどこにも設定されていません。

<p class="tolab"><a href="/_learn?id=XRT-16">ワークスペースでラボ XRT-16 を開く</a> — <a href="f1-m14-practice.html">課題 M14-1、M14-2</a></p>

:::note
このページの出力は、このページの設定(課題とは違う値)で、XRT-16 の上で取得しました。PE1・PE2・P1・PE3 は IOS XRd 26.1.1、
PE4 とホスト役は IOS XE 17.15(IOL)です。一部の出力と「やってみる」の結果の例は、PE1・PE2・P1 が XRT-16 と同じ名前と
アドレスを持つ PoC の盤面のものです。そこでは PE1 と PE2 が IOS XRv 9000 26.1.1 で、PE4 の位置にいた IOS XE 17.15 のルータは
別のアドレスでした。その盤面から取ったもの: IGMP バージョン 1 の出力、`static-group` の出力、
RP へ向かうインターフェイスで PIM を止めた時、PE2 だけの `spt-threshold infinity`、状態を消した RP、残る Join。RP に受信者が
いない時の Register-Stop と、IOS XE の IGMP と PIM の既定は、以前の PoC で IOS XE 17.15 だけを使って測りました。
出典: Multicast Configuration Guide for Cisco 8000 Series Routers, IOS XR 26.1.x–26.3.x の「Implementing Layer-3 Multicast
Routing」(既定ではどのインターフェイスも有効でなく、multicast routing configuration mode で有効にすること、既定はスパース
モード、最初のデータ パケットが届いた時の送信元ツリーへの切り替え、既定で MLDv2)。Multicast Command Reference for Cisco 8000
Series Routers(IGMP の既定、`multicast-routing` で有効にしていないインターフェイスには IGMP と PIM の下の `enable`/`disable` が
効かないこと、既定の SSM の範囲 232/8、`spt-threshold infinity [group-list]`、`join-group` と `static-group`、`join-group` が
優先すること)。Cisco IOS XE の IP マルチキャストの設定ガイドとコマンド リファレンス(アドレスの範囲、IGMP のクエリア、
`ip pim spt-threshold`、`ip igmp join-group` と `ip igmp static-group`、`show ip mroute` の `J` フラグ)。RFC 2236(IGMPv2、
224.0.0.2 宛ての Leave)、RFC 3376(IGMPv3、224.0.0.22 宛てのレポート、7.3.1 節の 1 つの LAN に 1 つのバージョン)、RFC 4604
(SSM のための IGMPv3)、RFC 7761(PIM-SM: 4.3.2 節の DR の選び方、Join/Prune の周期 60 秒と保持時間 210 秒、Register と
Register-Stop、(S,G,rpt) の Prune)。いずれも 2026 年 11 月に確認。
次の項目は実測によるものです。XRd がマルチキャストを転送し、MFIB で数えること(XRd のマルチキャストを書いた Cisco の文書は
ありません。IOS XRv 9000 では、パケットが届いているのに同じカウンタが 0 のままでした)、`multicast-routing` なしの
`router pim` の出力、ACCESS-3 のクエリアと DR、Decapstunnel の番号(盤面と時期によって 0・1・2 が出ました)、フラグ、ping の数。
文書と機器が食い違う所・文書に記述が無い所: コマンド リファレンスは IGMP の querier timeout を 120 秒としていますが、IOS XR は
125 秒と表示します(RFC 3376 の式の値)。上の出力にも出ますが、このページでは数値として扱いません。RFC 3376 は 1 つの LAN に
1 つの IGMP のバージョンを求めていますが、盤面は 2 つで始まります。
:::
