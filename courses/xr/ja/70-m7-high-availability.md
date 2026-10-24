# M7 — 高可用性

プロバイダのネットワークには、一部が故障したり再起動したりしている間も転送を続けることが求められます。この単元では、
そのために IOS XR が備える 4 つの道具と、それぞれの IS-IS 側の動きを扱います。リンクのバンドル、BFD、オーバーロード
ビット、そしてルーティング プロセスを損失なく再起動すること(グレースフル リスタート、NSF、NSR)です。CCNP Service
Provider のブループリントでは 2.8 にあたります。

このページの出力は、IOS XRv 9000 26.1.1 と、隣接ルータとしての Catalyst 8000V(IOS XE 17.15)および IOL 上の IOS XE
17.15 で取得しました(ラボ XRT-06)。秒数はそのラボで測った値で、保証された値ではありません。

## 1. リンクのバンドル

### 1.1 IOS XR のバンドル

IOS XR は、リンク アグリゲーションのグループを**バンドル**と呼びます。論理インターフェイスは `Bundle-Ether<n>` で、物理
インターフェイスは自身の設定の下で `bundle id <n>` によって参加します。アドレス、MTU、ルーティング プロトコルはバンドル
インターフェイスに属し、メンバーには L3 の設定を置きません。

`bundle id` の `mode` キーワードで、メンバーのネゴシエーションの仕方が決まります。

| モード | 動作 |
|---|---|
| `active` | LACP を動作させ、自分から LACPDU を送る |
| `passive` | LACP を動作させるが、LACPDU を送ってくる相手に応答するだけ |
| `on` | LACP を使わない。ポートがアップになればすぐにメンバーとして使う |

キーワードを省いたときも `mode on` になります。`show running-config` には `bundle id 1 mode on` と表示されます。
静的なメンバーはポートの状態だけを信じます。相手側が LACP を動作させていると、相手は来ない LACPDU を待ち続けて自分の
メンバーをグループに入れず、静的な側はそのメンバーへトラフィックを送り込みます。

```console
RP/0/RP0/CPU0:XR01#show bundle Bundle-Ether1
  Status:                                    Up
  Local links <active/standby/configured>:   2 / 0 / 2
  LACP:                                      Not operational
  Gi0/0/0/0             Local            Active       0x8000, 0x0000     1000000
  Gi0/0/0/1             Local            Active       0x8000, 0x0000     1000000

RT01#show etherchannel summary
1	Po1(RD)		LACP	 Gi1(susp) Gi2(susp)
```

XR01 からはバンドルが正常に見えますが、何も運びません。両端が passive の場合も LACP は始まらず、両側ともダウンのままです。
ラボの Catalyst 8000V は、ルーテッドのポート チャネルについて `active` と `passive` しか持たず、メンバーのモードをその場で
変えることもできません。いったんメンバーをチャネル グループから外す必要があります。

### 1.2 LACP が故障したメンバーに気づくしくみ

メンバーは、ポートがダウンしないまま故障することがあります。伝送網の中の障害や、変換器の向こうで遠端がシャットダウン
された場合です。それに気づけるのは LACP だけです。各端は、相手が求める間隔で LACPDU を送り、3 回続けて届かなかった
メンバーを外します。

| 相手の要求 | LACPDU の間隔 | メンバーが外れるまで |
|---|---|---|
| slow(既定) | 30 秒 | 90 秒 |
| fast | 1 秒 | 3 秒 |

IOS XR では、メンバーの下の `lacp period short` が相手に fast の間隔を求めます。`show lacp` のアクターの状態に `F` が
付いていれば、要求が出ています。ラボでは、遠端をシャットダウンしたメンバーを XR01 が外すまでに、slow のままでは 72 秒、
`lacp period short` を入れると 6 秒未満でした。

バンドルの下の `bundle minimum-active links <n>` は、バンドルがアップになるのに使用中でなければならないメンバーの数を
決めます。その数を下回るとバンドル全体がダウンし、残りのメンバーはスタンバイになり、ルーティング プロトコルが
トラフィックを別の経路へ移します。

```console
RP/0/RP0/CPU0:XR01#show bundle Bundle-Ether1
  Status:                                    Down
  Local links <active/standby/configured>:   0 / 1 / 2
  Minimum active links / bandwidth:          2 / 1 kbps
  Gi0/0/0/0             Local            Standby      0x8000, 0x0001     1000000
  Gi0/0/0/1             Local            Configured   0x8000, 0x0002     1000000
```

最低本数がなければ、バンドルは半分の帯域で 1 本のメンバーのままアップを続けます。それが正しいのは、半分の帯域で
足りる場合だけです。最低本数は両端で別々に設定するものなので、実際のネットワークでは両端をそろえておくべきです。

:::try
ポートを落とさずにメンバーを故障させ、XR01 がそれをいつまで使い続けるかを見ます。課題 M7-2 を解く前に一度、
解いた後にもう一度行います。

1. CML で、XR01 GigabitEthernet0/0/0/0 と RT01 GigabitEthernet1 の間のリンクを選びます。その **Settings** タブで
   **Loss** を 100 にし、**Enable** にチェックを入れて **Apply** を押します。両側のポートはアップのままで、リンク上の
   フレームはすべて失われます。
2. XR01 で `show bundle Bundle-Ether1` を数秒ごとに実行します。Gi0/0/0/0 が `Active` でなくなる時点と、バンドル全体に
   起きることを記録します。
3. 同じタブの **Reset** を押して故障を終わらせ、両方のメンバーが再び `Active` になったことを確かめます。

ラボで測った結果: 既定の slow のレートでは、メンバーが抜けたのは 68 秒後でした(相手の LACPDU は最大 90 秒途絶えることが
あります)。`lacp period short` では 5 秒以内です。最小のアクティブ リンク数が 2 なので、その時点でバンドル全体がダウンし、
メンバーは `Standby` から `Configured` になり、RT01 から RT02 へのトラフィックはバックアップ リンクを通りました。
:::

### 1.3 IOS XR の MTU

IOS XR の `mtu` コマンドは L2 ヘッダを数に含めます。IOS と IOS XE が数えるのは、その後ろの部分だけです。Ethernet の
ヘッダは 14 バイトで、2 つの MAC アドレスとタイプ フィールドです(PPP と HDLC では 4 バイト)。フレームの末尾にある
4 バイトの FCS は、どちらも数えません。

```text
| dest MAC 6 | source MAC 6 | type 2 |       payload (IP, MPLS, ...)       | FCS 4 |
|<------ Layer 2 header: 14 ------->|<--------------- 1500 -------------->|
|<-------------------------- mtu on IOS XR: 1514 ------------------------>|
                                     |<----------- mtu on IOS: 1500 ----->|
```

したがって、IOS XR の 1514 と IOS の 1500 は同じフレームを表しています。IOS XR の Ethernet のインターフェイスや
バンドルの既定値は 1514、IOS の既定値は 1500 です。IOS の隣接ルータに合わせるには、IOS XR 側を 14 バイト大きくします。

| やりたいこと | IOS 側 | IOS XR 側 |
|---|---|---|
| 既定(IP に 1500) | `mtu 1500`(既定) | `mtu 1514`(既定) |
| ジャンボ フレーム(IP に 9000) | `mtu 9000` | `mtu 9014` |

罠は逆の習慣、つまり両側に同じ数字を入れることです。どちらの設定も正しく見え、IOS XR 側だけが 14 バイト小さくなります。

| 両側に入れた値 | IOS で IP に使える大きさ | IOS XR で IP に使える大きさ |
|---|---|---|
| `mtu 1500` | 1500 | 1486 |
| `mtu 9000` | 9000 | 8986 |

IOS XR は、インターフェイスの上の各プロトコルの MTU を、ヘッダを引いて決めます。`show ipv4 interface` は両方の数字を、
`show im database interface` はすべてのプロトコルを表示します。

```console
RP/0/RP0/CPU0:XR01#show ipv4 interface Bundle-Ether1 | include MTU
  MTU is 1514 (1500 is available to IP)

RP/0/RP0/CPU0:XR01#show im database interface GigabitEthernet0/0/0/2
...
Interface GigabitEthernet0/0/0/2, ifh 0x01000020 (up, 1514)
...
  Protocol        Caps (state, mtu)
  --------        -----------------
  None            ether (up, 1514)
  arp             arp (up, 1500)
  clns            clns (up, 1500)
  ipv4            ipv4 (up, 1500)
```

バンドルに `mtu 1500` を入れると、同じコマンドが IP に残る大きさを表示します。

```console
RP/0/RP0/CPU0:XR01#show ipv4 interface Bundle-Ether1 | include MTU
  MTU is 1500 (1486 is available to IP)
```

`ipv4 mtu`、`ipv6 mtu`、`mpls mtu` は、1 つのプロトコルの MTU を設定します。意味は両方のシステムで同じ(L3 の大きさ)ですが、
IOS XR では、インターフェイスの `mtu` が残す大きさに収まるときだけ効きます。技術ノートの例では、`mpls mtu 1508` は
インターフェイスに `mtu 1522` を入れるまで 1500 のままです。サブインターフェイスは、メイン インターフェイスの MTU に
VLAN タグ 1 つにつき 4 バイトを足して受け継ぐので、IP は 1500 を保ちます(技術ノートによる。ラボでは測っていません)。

IS-IS は、Ethernet の上で使う LLC ヘッダの分として、さらに 3 バイトを引きます。ラボでの測定は次のとおりです。

| XR01 のバンドルの `mtu` | IP に使える大きさ | IS-IS の MTU |
|---|---|---|
| 1514(既定) | 1500 | 1497 |
| 1500 | 1486 | 1483 |
| 9000 | 8986 | 8983 |

IS-IS は、ハローをインターフェイスの MTU いっぱいまで埋める(パディングする)ので、食い違いにすぐ気づきます(既定では
XR01 のハローは 1497 オクテット、RT01 のハローは 1496 オクテットでした)。ルータは自身の MTU より大きいハローを捨てます。
バンドルに `mtu 1500` を入れると、XR01 は RT01 のハローを拒否し、さらに最大の LSP(既定で 1492 バイト)がもう収まらないと警告します。

```console
RP/0/RP0/CPU0:XR01#show isis interface Bundle-Ether1
  Last PDU Rejected:        13:57:29 (3.75 sec ago), 1496 octets, P2P IIH, PDU larger than our MTU
    MTU:                    1483 (MTU is too small: L2 lsp-mtu is 1492)

RT01#show clns neighbors
XR01            Po1           0003.a004.5331      Init   22        L2   IS-IS
```

RT01 は XR01 のハローを受け取り続けますが、そこに RT01 が載っていないので、Init で止まります。XR01 は、保持時間が
切れたところで隣接を落とします。バンドルに `mtu 9000` を入れると逆になり、RT01 が XR01 の 8983 オクテットのハローを捨て、
XR01 が Init で止まります。どちらの向きでも、両側とも Up にはなりません。MTU の小さい側がハローを捨て、
MTU の大きい側が Init で待ちます。

パディングは、まさにこの食い違いを見つけるためにあります。切ることもできます(IOS XR では `hello-padding disable`)が、
ラボでは何も変わりませんでした。XR01 が拒否していたのは、RT01 がパディングした RT01 のハローだったからです。そうやって
隣接を上げられる場合でも、食い違いは残ります。小さい方の MTU を超える LSP や IP パケットは、相変わらず失われます。

OSPF では、同じ食い違いが別の形で現れます。データベース記述パケットは送り手のインターフェイスの MTU を運び、
ルータは自身より大きい MTU を告げるものを拒否する(RFC 2328)ので、隣接は ExStart か Exchange で止まります。
IOS の `ip ospf mtu-ignore` と IOS XR の `mtu-ignore enable` はこの検査を切りますが、パディングを切るのと同じく、
食い違いはそのまま残ります(技術ノートと RFC によるもので、ラボは IS-IS を使っており測っていません)。

ルーティング プロトコルが上がる場合でも、小さい方の MTU を超えるパケットは失われます。境目は、DF ビットを立てた ping で
探します。どちらのシステムでも `size` は IP データグラム全体の大きさで、オプションは `df-bit` です(IOS XR は
`donotfrag` も受け付けます)。XR01 と RT01 の間の既定の MTU では次のとおりです。

```console
RP/0/RP0/CPU0:XR01#ping 10.0.1.11 size 1500 df-bit count 3
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/2/3 ms
RP/0/RP0/CPU0:XR01#ping 10.0.1.11 size 1501 df-bit count 3
Success rate is 0 percent (0/3)
```

## 2. BFD

### 2.1 BFD が加えるもの

IGP は、ハローが途絶えたことで隣接ルータの死を知ります。IOS XR の IS-IS は、既定では 30 秒後に隣接をダウンとします。
BFD(RFC 5880)は、2 つのインターフェイスの間で動く別の軽いハロー プロトコルで、ミリ秒単位の間隔で動作し、BFD を
利用するルーティング プロトコルに経路が失われたことを伝えます。障害を検出するまでの時間は、相手の乗数 × 合意した
間隔で、方向ごとに違う値になり得ます。

シングルホップのセッション(RFC 5881)では、IOS XR は相手が対応していれば**エコー**機能を使います。XR01 は自分宛ての
パケットを送り、相手がそれを送り返します。遅い非同期のパケットは、セッションを維持するためだけに流れます。
`show bfd session` には両方の値が表示されます。

```console
RP/0/RP0/CPU0:XR01#show bfd session
Interface           Dest Addr           Local det time(int*mult)      State
                                    Echo             Async   H/W   NPU
------------------- --------------- ---------------- ---------------- ----------
Gi0/0/0/2           10.0.2.12       300ms(100ms*3)   6s(2s*3)         UP
```

セッションがダウンした後、IOS XR は再びアップにするまでしばらく待ちます(ダンプニング。2 秒から始まり、フラップの
たびに長くなります)。そのとき `show bfd session` には `DOWN DAMP` と表示されます。

### 2.2 IOS XR の IS-IS に BFD を使う

IOS XR では、ルーティング プロトコルの BFD はインターフェイスではなくプロトコルの中で設定します。`router isis` の
インターフェイスの下で、`bfd fast-detect ipv4` がセッションを始め、`bfd minimum-interval` と `bfd multiplier` が
タイマーを決めます(既定は 150 ms と 3)。IOS はインターフェイスの `bfd interval` でタイマーを決め、`isis bfd` または
`bfd all-interfaces` で IS-IS に対して BFD を有効にします。

ラボでは、プライマリ パスの黙った障害(両端のポートはアップのまま、すべてのパケットが廃棄される)で、BFD なしでは
トラフィックが 22 秒止まり、100 ms × 3 の BFD ありでは 1 秒でした。XR01 は理由を記録しました。

```console
%L2-BFD-6-SESSION_STATE_DOWN : BFD session to neighbor 10.0.2.12 on interface GigabitEthernet0/0/0/2 has gone down. Reason: Echo function failed
%ROUTING-ISIS-5-ADJCHANGE : ISIS (CORE): Adjacency to RT02 (GigabitEthernet0/0/0/2) (L2) Down, BFD session DOWN
```

IS-IS に対して BFD を有効にしたルータは、そのことをハローでも知らせます(BFD-enabled TLV、RFC 6213)。両端がそうすると、
IOS XR は BFD を必須とみなし、BFD のセッションがアップになるまで隣接を **Init** に留めます。

```console
RP/0/RP0/CPU0:XR01#show isis adjacency detail
RT01           BE1                      *PtoP*         Init  25   not up   Yes Init None
  Topology (not running): [IPv4 Unicast (BFD is down)]
  BFD Status:             Neighbor Not Useable (BFD Required)
```

相手が TLV を知らせなければ、隣接は BFD がダウンのままでもアップになります(`BFD Configured, but Not Required`)。
したがって、TLV を知らせているのにインターフェイスに BFD のタイマーが無い相手とは、隣接がいつまでも Init のままです。

:::try
プライマリ パスを黙って壊し、トラフィックが止まる時間を数えます。課題 M7-4 を解く前に一度、解いた後にもう一度行います。

1. RT01 で、RT02 のサービス網へ ping を打ち、そのまま流しておきます。
   `ping 10.20.0.1 source Loopback1 repeat 20000 timeout 1`。ドット 1 つが、トラフィックの無いおよそ 1 秒です。
2. CML で、SW01 と RT02 の間のリンクを選びます。その **Settings** タブで **Loss** を 100 にし、**Enable** にチェックを
   入れて **Apply** を押します。
3. ドットが止まったら(トラフィックがバックアップ リンクへ移ったら)、同じタブの **Reset** を押します。Ctrl+Shift+6 で
   ping を止めてドットを数え、XR01 のログを `show logging | include "BFD|ADJCHANGE"` で読みます。

ラボで測った結果: BFD なしでは、IS-IS の保持時間が切れるまで 22〜28 秒トラフィックが止まりました(長さは、故障の前に
最後のハローがいつ届いたかで変わります)。BFD あり(100 ms × 3 と 250 ms × 3 の両方を試しました)では失われた応答は 1 つで、
XR01 は `Echo function failed` を記録しました。
:::

### 2.3 BFD とバンドル

バンドルでは、BFD を 2 つの方法で動かせます。**BFD over bundle members**(BoB、RFC 7130)は、メンバーのリンクごとに
1 つのセッションを動かし(UDP ポート 6784)、バンドル インターフェイスの下で設定し、セッションが落ちたメンバーを外します。
**BFD over the logical bundle**(BLB)は、バンドル インターフェイスでルーティング プロトコルに BFD を有効にしたときに
そのプロトコルが始めるもので、バンドル全体で 1 つのセッションです。IOS XRv 9000 の BLB のセッションには、`bfd` の下の
`bfd multipath include location` が必要です。無いと XR01 は `No resources for session … on interface Bundle-Ether1`
を記録します。

どちらも、ポート チャネルで BFD を動かす相手が必要です。ラボの Catalyst 8000V はそれをしないので、XRT-06 では BFD を
プライマリ リンクだけで使い、バンドルは LACP に任せます。応答しない相手に対して BoB を設定すると、メンバーはセッションを
いつまでも待ち、バンドルはそれまでの状態のままです。

## 3. オーバーロード ビット

### 3.1 何をするのか

すべての LSP は**オーバーロード**(OL)ビットを持っています。他のルータは、オーバーロード中のルータを通過には使いませんが、
そのルータ自身がアドバタイズするプレフィックスには到達し続けます(ISO 10589、RFC 3787)。`show isis database` は
このビットを `ATT/P/OL` 列に表示します。

```console
RP/0/RP0/CPU0:XR01#show isis database
XR01.00-00          * 0x00000018   0xff94        1188 /*            0/0/1
```

`router isis` の下の `set-overload-bit` は、取り除くまでビットを立てます。メンテナンスの前に、ルータへのアクセスを
失わずにルータを通過経路から外すのはこの方法です。ラボでは、RT01 はすぐに RT02 宛てのトラフィックをバックアップ
リンクへ送り、XR01 のループバックにはバンドル経由で到達し続けました。作業後にビットを立てたままにすると、ルータは
警報もなくすべての経路から外れたままになります。

:::try
このビットが経路に何をするかを見ます。課題 M7-1 の後(バンドルが動いている必要があります)、ビットを取り除く課題 M7-3 の前に行います。

1. XR01 で `show isis database` を実行すると、XR01 自身の LSP の OL 列に 1 が表示されます。
2. RT01 で `show ip route 10.20.0.0` と `traceroute 10.20.0.1 source Loopback1 numeric` を実行すると、RT02 のサービス網への
   経路が、XR01 を通らずバックアップ リンク(GigabitEthernet3)を通っていることが分かります。
3. RT01 で `ping 10.255.0.1` を実行すると、バンドル経由で XR01 のループバックにはまだ届きます。オーバーロードのルータは
   通過に使われなくなるだけで、切り離されるわけではありません。

ラボでは、経路は GigabitEthernet3 経由でメトリック 1010、traceroute は 1 ホップで RT02(10.0.12.12)に届きました。
課題 M7-3 の後は、同じコマンドで XR01 を通る経路が表示されます。
:::

### 3.2 起動時

起動したばかりのルータは、データベースが不完全で、BGP を動かしていれば BGP のテーブルも不完全です。早すぎる時点で
引き寄せたトラフィックは失われます。`set-overload-bit on-startup <秒>` はプロセスの起動後に指定した時間だけビットを
立て、`set-overload-bit on-startup wait-for-bgp` は BGP が収束したと通知するまで立てます。`show isis protocol` は、
どれが設定されていて、いまビットが立っているかを表示します。

```console
  Overload Bit Level-2: configured, clear
      on startup until BGP converges
```

3 つの形はすべて同じコマンドなので、ルータが持てるのはどれか 1 つです。ラボでは、ビットが実際に立つ時を測りました。

| プロセスの起動 | LSP の OL ビット |
|---|---|
| コールド スタート、オーバーロードの設定なし | 約 10 秒(データベースがそろうまで) |
| コールド スタート、`on-startup 60` | 約 60 秒 |
| `clear isis process`、`on-startup 60` | 立たない |
| NSF による再起動(4.2 節)、`on-startup 60` | 立たない(`show isis protocol` は `set` と表示するが、LSP には立たない) |

NSF なしのプロセスの再起動は、コールド スタートとして扱われます。NSF を設定すると、プロセスの再起動ではビットが立たなくなり、
起動時のオーバーロードは、ルータ全体のリロードのようなコールド スタートのためのものになります(ラボでは測っていません)。

:::try
起動時のオーバーロードが起きるところを見ます。NSF なしの再起動が要るので、課題 M7-3 の後、課題 M7-5 の前に行います
(または、試す間だけ `nsf` を外し、後で元に戻します)。

1. XR01 で、`process restart isis` で IS-IS を再起動します。
2. RT01 で `show isis database XR01.00-00` を 2〜3 秒ごとに実行し、OL 列を見ます。しばらく 1 が表示され、その後 0 になります。
3. XR01 で `show isis protocol` を実行すると、起動の種類(`Cold Restart`)とオーバーロード ビットの状態が表示されます。

ラボで測った結果: `on-startup wait-for-bgp` では、`process restart isis` のおよそ 5 秒後にビットが立ち、13 秒後には
消えていました。XR01 が `Cold controlled start completed` を記録したころです(BGP は再起動しておらず、収束済みだったため)。
`on-startup 60` ではおよそ 60 秒立ったままで、NSF ありでは立ちませんでした。
:::

## 4. 損失なく再起動する

### 4.1 IOS XR のプロセス

M0 で見たように、IOS XR のルーティング プロトコルは別々のプロセスです。それぞれが保護されたメモリで動き、他を再起動せずに
再起動できます。EXEC モードの `process restart isis` や `process restart bgp` で再起動し、`show processes isis` で最後に
起動した時刻を確かめます。クラッシュも同じ形で終わり、プロセスはシステム マネージャによって起動し直されます。隣接ルータに
何が見えるかは、戻ってきたプロセスが何をするかで決まります。

何も準備しなければ、再起動した IS-IS プロセスはゼロから始まります。隣接ルータを列挙しないハローを送るので、隣接ルータは
隣接を落とし(RT01 は `Down, neighbor forgot us` を記録)、2 秒後に張り直します。その間、ルータを通るトラフィックは
止まります。

### 4.2 IS-IS の NSF

**ノンストップ フォワーディング**は、コントロール プレーンが再起動している間もラインカードの転送テーブルを保ち、
再起動するルータが隣接ルータに気づかれずに状態を作り直せるようにします。IOS XR には IS-IS 用に 2 つの形があり、
`router isis` の下の `nsf` で選びます。

| 形 | 状態の作り直し方 | 隣接ルータに求めること |
|---|---|---|
| `nsf ietf` | 再起動するルータがハローで再起動を知らせ(RFC 8706、旧 RFC 5306)、隣接ルータがデータベースを送り直す | 再起動の通知に対応していること(ヘルパー) |
| `nsf cisco` | ルータが再起動の前に保存しておいた状態を復元する | 何もない |

IOS と IOS XE は、設定なしで IETF のヘルパーとして動作します。XR01 に `nsf ietf` を入れたときのプロセスの再起動は次の
ようになり、RT01 と RT02 のどちらも隣接の変化を記録しませんでした。

```console
%ROUTING-ISIS-6-INFO_STARTUP_START : ISIS (CORE): IETF NSF controlled start beginning
%ROUTING-ISIS-5-ADJCHANGE : ISIS (CORE): Adjacency to 49.0001.0100.0000.0011 (Bundle-Ether1) (L2) Up, NSF Restart
%ROUTING-ISIS-6-INFO_STARTUP_FINISH : ISIS (CORE): IETF NSF controlled start completed
```

`nsf cisco` でも隣接ルータには何も見えませんでした。XR01 は `Cisco NSF controlled start` と、隣接の
`Restored during NSF` を記録しました。`show isis protocol` は、最後の起動の種類を表示します(`Most recent startup mode:
IETF NSF Restart` または `Cold Restart`)。XR01 自身の隣接テーブルは、どちらの場合も再起動の時点から稼働時間を数えます。確かめる場所は
隣接ルータのログです。

:::try
再起動を、隣接ルータの側から見てみます。課題 M7-5 を解く前に一度、解いた後にもう一度行います。

1. RT01 で、XR01 を通って届く RT02 のループバックへ ping を打ち、そのまま流しておきます。
   `ping 10.255.0.12 source Loopback0 repeat 20000 timeout 1`。失われた応答は 1 つにつき 1 秒かかるので、ドットの数は
   トラフィックが止まった秒数にほぼ等しくなります。
2. 別のコンソールのタブで、XR01 の IS-IS を `process restart isis` で再起動します。
3. ping が終わったら(または Ctrl+Shift+6 で止めたら)ドットを数え、RT01 のログを
   `show logging | include ADJCHANGE` で読みます。

ラボで測った結果: NSF なしでは応答が 1〜2 つ失われ、RT01 は `Down, neighbor forgot us` と、2 秒後に隣接が再び上がったことを
記録しました。NSF ありでは応答は 1 つも失われず、RT01 は隣接の変化を何も記録しませんでした。
:::

### 4.3 BGP のグレースフル リスタート

BGP のグレースフル リスタート(RFC 4724)は、IS-IS の NSF と同じことを BGP で行います。再起動するルータは転送を続け、
ピアはそのルータから学習したルートを保持して stale(古い)と印を付け、セッションが戻ってピアがテーブルを送り直したとき
(End-of-RIB)に置き換えます。RT02 では、stale のルートに `S` が付きます。

```console
RT02#show ip bgp | begin Network
     Network          Next Hop            Metric LocPrf Weight Path
 S>i  10.30.0.0/16     10.255.0.1               0    100      0 i
```

両側にグレースフル リスタートが無いと、RT02 はそのルートを約 5 秒間失いました(`% Subnet not in table`)。

グレースフル リスタートは OPEN メッセージで交換する機能なので、設定した後に開いたセッションにだけ効きます。IOS XR では
`router bgp` の下の `bgp graceful-restart`、IOS でも同じコマンドです。セッションをリセットするまで(IOS XR では
`clear bgp <ネイバー>`)は、相手には
`Graceful-Restart is disabled` や `advertised` だけが表示されたままです。動作していれば、IOS には
`Graceful Restart Capability: advertised and received` と表示されます。リスタート タイム(既定 120 秒)はピアが
セッションを待つ時間の上限、stale パス タイム(360 秒)は stale のルートを保持する時間の上限です。

:::try
XR01 の BGP を再起動し、RT02 が持つ XR01 のプラットフォーム網への経路を見ます。課題 M7-5 を解く前に一度、
解いた後にもう一度行います。

1. XR01 で、`process restart bgp` で BGP を再起動します。
2. RT02 で、すぐに、その後 1〜2 秒ごとに `show ip bgp | include 10.30.0.0` を実行します。

ラボで測った結果: グレースフル リスタートなしでは、経路がおよそ 5 秒消えました(行がまったく表示されません)。
グレースフル リスタートありでは、RT02 は経路を `S`(stale)の印付きで保持し、6〜11 秒後にセッションが戻りました。
:::

### 4.4 NSR

**ノンストップ ルーティング**はさらに先へ進みます。スタンバイのルート プロセッサが、BGP の TCP セッションを含む
プロトコルの状態の同期したコピーを持ち、隣接ルータをまったく関与させずに引き継ぎます。ルート プロセッサが 2 枚
必要です。IOS XRv 9000 でも `router isis` や `router bgp` の下の `nsr` は受け付けますが、ルート プロセッサが 1 枚では
状態は `Not Ready` のままで、プロセスの再起動は相変わらず NSF が処理します。このリリースでは、BGP の NSR は既定で
有効になっていました(`show bgp process` に `Non-stop routing is enabled`)。ただし、既定値について文書どうしの記述は
一致していません。

| 事象 | 守るもの |
|---|---|
| プロセスの再起動やクラッシュ | NSF / グレースフル リスタート |
| アクティブなルート プロセッサの故障 | NSR(と、予備としての NSF) |

## 5. コマンド名

| IOS | IOS XR |
|---|---|
| メンバーの `channel-group <n> mode active` | メンバーの `bundle id <n> mode active` |
| `interface Port-channel<n>` | `interface Bundle-Ether<n>` |
| メンバーの `lacp rate fast` | メンバーの `lacp period short` |
| ポート チャネルの `lacp min-bundle <n>` | バンドルの `bundle minimum-active links <n>` |
| `show etherchannel summary`、`show lacp neighbor` | `show bundle`、`show lacp` |
| `mtu`、`ip mtu`(ヘッダを含まない) | `mtu`(L2 ヘッダを含む) |
| インターフェイスの `bfd interval … min_rx … multiplier …` + `isis bfd` | `router isis` のインターフェイスの下の `bfd fast-detect ipv4`、`bfd minimum-interval`、`bfd multiplier` |
| `show bfd neighbors` | `show bfd session` |
| `router isis` の下の `set-overload-bit [on-startup …]` | `router isis` の下の `set-overload-bit [on-startup {<秒> \| wait-for-bgp}]` |
| `router isis` の下の `nsf ietf` | `router isis` の下の `nsf {ietf \| cisco}` |
| `bgp graceful-restart` | `bgp graceful-restart` |

## 実践

ラボ **XRT-06** で M7 の課題に取り組んでください。このラボは IOS XRv 9000 を使うので、構築に約 10 分かかります。

<p class="tolab"><a href="/_learn?id=XRT-06">ワークスペースでラボ XRT-06 を開く</a> — <a href="71-m7-practice.html">課題</a></p>

:::note
出典: IOS XR の *Interface and Hardware Component* のコンフィギュレーション ガイドとコマンド リファレンスの
「Configuring Link Bundling」(モードと既定の `on`、`bundle minimum-active links`、`lacp period short`)、XRv 9000 の
リリース ノート(LACP の周期の下限 200 ms、BFD over logical bundle)、技術ノート「MTU Behavior on Cisco IOS XR and Cisco
IOS Routers」と IS-IS のコマンド リファレンス(ハローのパディング)、IOS XR の *Routing* のコンフィギュレーション
ガイドとコマンド リファレンスの「Implementing BFD」「Implementing IS-IS」(BFD のタイマーと既定値、BoB、BLB と
`bfd multipath include location`、`set-overload-bit` と起動時の形、NSF、ルート プロセッサ 2 枚専用の NSR)、
IOS XR の *BGP* のコンフィギュレーション ガイドとコマンド リファレンス(グレースフル リスタートとそのタイマー、BGP の
NSR)、IOS XE 17.x のガイド(NSF awareness、BGP のグレースフル リスタート、BFD)。2026 年 10 月に確認しました。
RFC 5880、5881、7130、6213、3787、4724、8706、RFC 2328(OSPF のデータベース記述パケットの MTU)。次のものはラボ XRT-06
での測定によります。アップと表示される静的なバンドル、LACP の検出時間、各プロトコルの MTU と MTU のメッセージ、境目での
DF ビット付きの ping、BFD の時間と Init の状態、起動時のオーバーロード ビット、NSF による再起動の
メッセージ、RT02 の stale のルート、`Not Ready` の状態の NSR、BGP の NSR の既定値。
:::
