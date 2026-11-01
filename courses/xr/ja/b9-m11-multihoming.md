# M11 追補 — EVPN のマルチホーム

前のページでは、拠点 1、2、3 を EVPN で 1 つの E-LAN にしました。このページでは、2 台の PE に同時に収容されたスイッチ
である拠点 4 を加え、その 2 本のリンクを両方とも使います。ラボは引き続き XRT-12 で、課題 M11-8 がこのページにあたります。

:::topo
nodes:
  SW1: {at: [0, 1.4], label: "SW1(拠点 4)"}
  XE1: {at: [1.9, 0.4], label: "XE1(PE)"}
  XE2: {at: [1.9, 2.4], label: "XE2(PE)"}
  P1: {at: [3.8, 1.4], label: "P1(P、RR)"}
  XE3: {at: [5.7, 1.4], label: "XE3(PE)"}
  CE3: {at: [7.6, 1.4], label: "CE3(拠点 3)"}
links:
  - [SW1, XE1, "Et0/0 — Gi3"]
  - [SW1, XE2, "Et0/1 — Gi3"]
  - [XE1, P1, "CORE-1"]
  - [XE2, P1, "CORE-2"]
  - [P1, XE3, "CORE-3"]
  - [XE3, CE3, "Gi2"]
frames:
  - {label: "SW1 では 1 つの LACP の束(Po1)", nodes: [SW1]}
:::

SW1 は 2 本のリンクを LACP で Port-channel1 に束ね、そこで VLAN 200 を使います(172.31.200.4)。拠点 1 と 2 は図から
省いています。これまでどおり XE1 と XE2 につながっています。

## 1. 何が嬉しいのか

### 1.1 1 つの拠点を 2 台の PE に

拠点 4 は、PE 1 台の故障や、PE へのリンク 1 本の故障では止まらないようにしたい拠点です。そこで SW1 を 2 台の PE、XE1 と
XE2 に収容します。すると、リンクが 1 本のときには無かった問いが出てきます。SW1 → XE1 → XE2 → SW1 とフレームが回るのを、
何が止めるのでしょうか。

### 1.2 それまでの手: 2 本のうち 1 本は待つ

PE の助けが無ければ、プロバイダーの網を通るループは本当に起きます。VPLS では、SW1 からのブロードキャストが XE1 に入り、
疑似回線で XE2 へ渡り、XE2 のリンクから SW1 へ戻ってきます。よくある手当ては、どれも 1 本のリンクを遊ばせます。

- SW1 で(あるいは PE をまたいで)**スパニング ツリー**を動かし、1 本を止める。
- **アクティブ/スタンバイ**の収容: 片方の PE だけが転送し、もう片方のリンクか疑似回線は、1 台目が落ちるまで待機する。
- **マルチシャーシのリンク アグリゲーション**(mLACP、vPC など): 2 台の PE を 1 台に見せる。VPN の外に、2 台の PE の間だけの
  プロトコルを持つ。

どれも動きますが、帯域の半分を使わずにおくか、2 台の PE しか話さないプロトコルを 1 つ足すことになります。

### 1.3 この技術の答え: イーサネット セグメント

EVPN は、マルチホームを VPN そのものに組み込みます。1 台のお客さまの機器を複数の PE につなぐリンクの集まりが
**イーサネット セグメント**(ES)で、両方の PE が設定する識別子(ESI)で名前を付けます。ESI があると、PE は BGP で互いを
知り、EVPN の決まり(2 章)がループと重複したフレームを取り除きます。こうして 2 本のリンクが同時に転送でき(**all-active**)、
SW1 には 1 つの束に見えます。

## 2. 仕組み

### 2.1 イーサネット セグメントの識別子

ESI は 10 オクテットです。1 オクテットの**タイプ**の後に、9 オクテットの値が続きます。ここで関係するタイプは 2 つです。

- **タイプ 0**: 9 オクテットを運用者が決めます。プロバイダーはふつう番号の決め方から作ります。このラボもそうです
  (`0000.0000.0000.0000.0401`= タイプ 00 と、値 00.00.00.00.00.00.00.04.01)。
- **タイプ 3**: MAC アドレス(6 オクテット)と、ローカルな番号(3 オクテット)から作ります。

IOS XE は ESI 全体を、タイプを先頭に、4 桁の 16 進を 5 組並べて表示します。`identifier type 0` が受け取るのは、値の
9 オクテットだけを点で区切ったものです。全部 0 の ESI は「1 台の PE だけに収容した拠点」という意味で、前のページの ESI の
列が 0 だったのはそのためです。

IOS XE 17 のガイドは、ここで食い違っています。マルチホームの章は「タイプ 3 だけをサポート」と書き、IRB 付きの EVPN の章の
設定例には「タイプ 0 と 3 の両方をサポート」と注記があります。Catalyst 8000V 17.15.1a はタイプ 0 を受け付け、下のとおり
広告しました。

### 2.2 経路の種類 4: PE どうしが見つけ合い、転送役を選ぶ

ESI を持つ各 PE は、**種類 4** の経路(イーサネット セグメントの経路)を 1 つ広告します。そのルート ターゲットは ESI から
作られるので、取り込むのは同じセグメントの PE だけです。これで XE1 と XE2 は、同じセグメントを共有していると知ります。

続いて、EVPN インスタンスごとに 1 台の **指定フォワーダー**(DF)を選びます。BUM のフレーム(ブロードキャスト、宛先の
分からないユニキャスト、マルチキャスト)をコアから SW1 へ下ろすのは、そのセグメントの中で DF だけです。DF が無いと、拠点 3
からのブロードキャストは、それぞれの PE を通って SW1 に 2 回届きます。既定の決め方は RFC 7432 にあります。セグメントの PE を
アドレスの順に並べて 0 から番号を振り(**序数**)、VLAN を PE の台数で割った余りと同じ番号の PE が DF です。分かっている
ユニキャストのフレームには関係しません。どちらの PE が届けても構いません。

```console
XE1#show l2vpn evpn ethernet-segment detail
EVPN Ethernet Segment ID: 0000.0000.0000.0000.0401
  Local Discriminator:    4
  Interface:              Po1
  Redundancy mode:        all-active
  DF election wait time:  3 seconds
  Split Horizon label:    19
  State:                  Ready
  Encapsulation:          mpls
  Ordinal:                0
  Core Isolation:         No
  RD:                     10.255.0.41:1
    Export-RTs:           65000:200
  Forwarder List:         10.255.0.41 10.255.0.42
```

`Forwarder List` にはセグメントの 2 台の PE が、`Ordinal` にはその中でのこの PE の番号が出ます(XE2 は 1)。DF の選出は、
セグメントが上がってから 3 秒待ちます。両方の PE の種類 4 の経路が届いてから決めるためです。

### 2.3 経路の種類 1: エイリアシング

セグメントの各 PE は、**種類 1** の経路(イーサネットの自動検出)も広告します。セグメント全体のもの(イーサネット タグ
4294967295)と、EVPN インスタンスごとのもの(イーサネット タグ 0)です。

```console
XE1#show bgp l2vpn evpn route-type 1
BGP routing table entry for [1][10.255.0.41:1][00000000000000000401][4294967295]/23, version 34
      Extended Community: RT:65000:200 EVPN LABEL:0x0:Label-304
BGP routing table entry for [1][10.255.0.41:200][00000000000000000401][0]/23, version 44
  Local, imported path from [1][10.255.0.42:200][00000000000000000401][0]/23 (global)
    10.255.0.42 (metric 30) (via default) from 10.255.0.51 (10.255.0.51)
```

XE3 のような遠い PE にとって、これらの経路は「セグメント 0401 には XE1 からも XE2 からも届く」という意味です。そのため、
ESI 付きの種類 2 の経路で SW1 の MAC が届くと、SW1 からのフレームを片方の PE しか見ていなくても、XE3 はその MAC 宛ての
フレームをどちらの PE へも送れます。これが **エイリアシング**で、遠い側から見た all-active の負荷分散を成り立たせます。

```console
XE3#show l2vpn evpn mac
MAC Address    EVI   BD    ESI                      Ether Tag  Next Hop(s)
-------------- ----- ----- ------------------------ ---------- ---------------
aabb.cc00.6900 200   200   0000.0000.0000.0000.0000 0          10.255.0.41
aabb.cc00.6a00 200   200   0000.0000.0000.0000.0000 0          10.255.0.42
aabb.cc00.6b00 200   200   0000.0000.0000.0000.0000 0          Gi2:200
aabb.cc80.6800 200   200   0000.0000.0000.0000.0401 0          10.255.0.41
                                                               10.255.0.42
```

最後の行が SW1 のものです。ESI は 0401、次ホップは 2 つです。CE1 と CE2(1 台の PE だけに収容。ESI 0)は 1 つずつです。

### 2.4 リンクが切れたとき: 全部の MAC を 1 回の取り消しで

XE1 が SW1 へのリンクを失うと、セグメントの種類 1 の経路を取り消します。すると XE3 は、そのセグメントの先にある**すべての**
MAC から、一度に XE1 を外します。MAC ごとの種類 2 の経路の取り消しを待ちません(**一括の取り消し**、mass withdrawal)。
MAC が千個あるセグメントでも、1 回の BGP の更新で切り替わります。

ラボでは、SW1 から CE3 へ ping を打っている間に XE1 の Gi3 を shutdown しました。3 秒後には、XE3 は SW1 の MAC を XE2 の先
だけに持ち、SW1 は Et0/0 を束から外していて、ping は止まりませんでした。Gi3 を戻すと、2 つの次ホップが戻りました。

### 2.5 セグメントのスプリット ホライズン

ループの残りが 1 つあります。SW1 からのブロードキャストが XE1 に届くと、E-LAN のすべての PE へコピーされ、XE2 にも届きます。
XE2 も SW1 のセグメントにいるので、DF なら、そのフレームを SW1 へ戻してしまいます。それを防ぐため、各 PE はセグメントの
**スプリット ホライズンのラベル**(ESI ラベル。上の `Split Horizon label: 19`)を広告します。XE1 は、セグメント 0401 から来た
BUM のフレームを XE2 へ送るとき、XE2 のスプリット ホライズンのラベルを付けます。XE2 はそれを見て、そのセグメントへは
出しません。

## 3. IOS XE での設定

### 3.1 設定

2 台の PE は、セグメントについて同じ設定を持ちます。ESI と冗長化の方式、セグメントに属する Port-channel、そして
Port-channel の上の EFP を E-LAN のブリッジ ドメインに入れることです。

:::config fold Catalyst 8000V(IOS XE 17.15)— 拠点 4 を all-active で二重に収容する XE1 の分(XE2 も同じ)
l2vpn evpn ethernet-segment 4                      ## セグメント。4 はローカルな番号(識別のための数)にすぎない
 identifier type 0 00.00.00.00.00.00.00.04.01      ## 9 オクテットの値。0000.0000.0000.0000.0401 と表示される
 redundancy all-active                             ## 両方の PE が転送する(このプラットフォームではこれだけ)
!
interface Port-channel1
 no ip address
 lacp device-id 0000.0000.0004                     ## SW1 に送る LACP のシステム ID。両方の PE で同じ値
 evpn ethernet-segment 4                           ## この束がセグメント
 service instance 200 ethernet
  encapsulation dot1q 200
  rewrite ingress tag pop 1 symmetric
  exit                                             ## service instance と Port-channel を抜ける
 exit
interface GigabitEthernet3
 channel-group 1 mode active                       ## SW1 へのリンク。この PE では Po1 のただ 1 つのメンバー
!
bridge-domain 200
 member Port-channel1 service-instance 200         ## 拠点 4 を前のページの E-LAN に加える
!
:::

各 PE は SW1 へのリンクを 1 本ずつ持つので、それぞれの Port-channel のメンバーは 1 本です。SW1 から見える束は、各 PE への
リンク 1 本ずつでできています。

### 3.2 LACP: 2 台の PE、1 つの相手

LACP が束ねるのは、相手の端が同じ **システム ID** を名乗っているリンクだけです。何もしなければ XE1 と XE2 はそれぞれ自分の
ID を名乗り、SW1 には相手が 2 つに見えます。`lacp device-id` は、その Port-channel で PE が名乗る ID を決めます。両方の PE で
同じなら、どの MAC アドレスでも構いません。ラボで、この行を XE1 だけに入れたときです。

```console
SW1#show etherchannel summary
1      Po1(SU)         LACP        Et0/0(P)        Et0/1(s)
SW1#show lacp neighbor
Et0/0         SA     32768     0000.0000.0004   0s  0x0    0x1    0x4     0x3D
Et0/1         SA     32768     001e.140a.fb00   0s  0x0    0x1    0x4     0xD
```

SW1 は Et0/0 を残し(`P`= 束の中)、Et0/1 を suspended にしました(`s`)。Et0/1 の相手が別のシステム ID だったからです。
XE2 の Port-channel は down のままでした。両方の PE に入れると、SW1 は `Et0/0(P) Et0/1(P)` になりました。

### 3.3 出力の読み方

- `show l2vpn evpn ethernet-segment detail`: ESI、方式、セグメントの PE(`Forwarder List`)、スプリット ホライズンのラベル。
- `show bgp l2vpn evpn route-type 4` と `route-type 1`: 両方の PE からのセグメントの経路。
- 遠い PE の `show l2vpn evpn mac`: セグメントの先の MAC と、その ESI と 2 つの次ホップ。
- SW1 の `show etherchannel summary` と `show lacp neighbor`: 2 本とも束に入っているか、リンクごとの相手のシステム ID。

### 3.4 うまくいかないとき

| 間違い | ラボで見えたこと |
|---|---|
| `lacp device-id` が片方の PE だけ、または 2 台で違う | SW1 は 1 本だけ束ね、もう 1 本を suspended にする。もう片方の PE の Port-channel は down のまま |
| 2 台の PE で ESI が違う(たとえば片方だけタイプ 3) | 各 PE が自分だけのセグメントにいる。遠い PE は SW1 の MAC に 2 つの次ホップを持たなくなる |
| ESI の値を表示どおりに書く(`0000.0000.0000.0000.0401`) | 受け付けない。`identifier type 0` が取るのは値の 9 オクテットを点で区切ったもの |

Catalyst 8000V にあるのは `redundancy all-active` だけです。**single-active**(IOS XR やほかのプラットフォームにある)では、
VLAN ごとに DF だけが転送し、もう一方の PE のリンクは待機します。そのときお客さまの機器は、PE をまたぐ束を必要としません。

:::try
セグメントのリンクを 1 本落とします。課題 M11-8 の後に行ってください。

1. SW1 で `ping 172.31.200.3 repeat 100000 timeout 1` を始めます(Ctrl+Shift+6 で止まります)。
2. XE1 で GigabitEthernet3 を shutdown します。XE3 で `show l2vpn evpn mac` を何度か実行します。SW1(2 つめのコンソール)で
   `show etherchannel summary` を実行します。
3. XE1 で GigabitEthernet3 を戻し、30 秒ほど待ってもう一度見ます。

ラボでの結果: 3 秒以内に XE3 は SW1 の MAC を 10.255.0.42 の先だけに持ち、SW1 では Et0/0 が待機(`w`)の後に suspended
(`s`)になり、ping は止まりませんでした。このラボの SW1 は `lacp rate fast` で動いています。IOL-L2 はリンクの向こう側が
落ちたことを受け取れないので、LACP で気づくしかありません。
:::

### 3.5 IOS XR では

IOS XR では、セグメントを `evpn` → `interface Bundle-Ether<n>` → `ethernet-segment` → `identifier type 0 <値>` の下に
書き、all-active が既定です。`load-balancing-mode single-active` で single-active になります。お客さまの機器にリンクを
束ねさせるには、両方の PE の束が同じ LACP のシステム ID を持つことも必要です(束の下の `lacp system mac <MAC>`)。束の
サブインタフェースが、アタッチメント回線としてブリッジ ドメインに入ります。

## 4. コマンド名の対照

| IOS XE では | IOS XR では |
|---|---|
| `l2vpn evpn ethernet-segment <n>` → `identifier type 0 <9 オクテット>`、`redundancy all-active` | `evpn` → `interface Bundle-Ether<n>` → `ethernet-segment` → `identifier type 0 <値>` |
| `interface Port-channel<n>` → `evpn ethernet-segment <n>` | (セグメントは `evpn` の下で束に設定する) |
| `lacp device-id <MAC>` | `lacp system mac <MAC>`(束の下) |
| (single-active は無い) | `load-balancing-mode single-active` |
| `show l2vpn evpn ethernet-segment detail` | `show evpn ethernet-segment detail` |

## 実践

ラボ **XRT-12** で、課題 M11-8 に取り組んでください。その後、次のページ「イーサネット OAM」へ進みます。

<p class="tolab"><a href="/_learn?id=XRT-12">ワークスペースでラボ XRT-12 を開く</a> — <a href="ba-m11-practice-5.html">課題</a></p>

:::note
出典: MPLS Configuration Guide, Cisco IOS XE 17.x(EVPN Multihoming。EVPN over MPLS with IRB。後者の設定例は Port-channel に
`lacp device-id` を持つ)。どちらの章も名指ししているのは ASR 1000 だけです。ASR 9000 と NCS 5500 の L2VPN の
コンフィギュレーション ガイド、IOS XR 7.10.x(EVPN Features。NCS 5500 の例は両方の PE に同じ `lacp system mac` を設定する)と、
Cisco の技術文書「Configure EVPN Route Types and Their Functions on IOS XR Routers」(2026)。RFC 7432(イーサネット セグメント、
経路の種類 1 と 4、DF の選出、エイリアシング、一括の取り消し、ESI ラベル)。いずれも 2026 年 11 月に確認しました。出力、
LACP のふるまい、切り替わりの時間は、ラボ XRT-12(Catalyst 8000V 17.15.1a、IOL-L2 17.15)での測定によります。
:::
