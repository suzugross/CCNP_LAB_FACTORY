# M10 — TI-LFA

このページは、リンクが切れたときに、IGP が新しい道を計算し終えるのを待たずに迂回させる仕組みを扱います。ブループリントの
3.3.d にあたり、課題 M10-3 で使います。前のページ「セグメント ルーティングの仕組み」の 2 節(ラベルを重ねて経由地を書く)を
先に読んでください。

## 1. 何が嬉しいのか

### 1.1 リンクが切れてから直るまで

PRIMARY が切れたとします。IS-IS がふつうに直すには、次の手順が要ります。

1. XR01 と RT01 が障害に気づく(BFD なら 300 ms、IS-IS の hello だけなら最長 30 秒)。
2. 変化を LSP で全ルータに知らせる(フラッディング)。
3. 各ルータが最短パスを計算し直す(SPF)。
4. 各ルータが転送テーブルを書き換える。プレフィックスが多ければ、ここに時間がかかる。

2〜4 が終わるまで、PRIMARY へ送られたパケットは失われます。このラボほど小さなネットワークなら 100 ms ほどですが、
プレフィックスの多い大きなネットワークでは秒の単位になります。

**高速再ルーティング**(FRR)は、2〜4 を待たないための仕組みです。障害の隣のルータ(**ローカル修復点**。ここでは XR01)が、
「このリンクが切れたらこう送る」という迂回の道を前もって計算し、転送テーブルに入れておきます。障害に気づいた瞬間に
それに切り替え、止まる時間を 1 の検出の時間だけにします。その間に、IS-IS はいつもどおり収束します。

### 1.2 これまでの迂回の穴

迂回の道の作り方は、SR の前からありました。

- **ループ フリー代替パス**(LFA、RFC 5286): パケットを別の隣のルータに渡すだけです。ただし、その隣のルータが、宛先への
  最短パスとしてパケットを送り返してこない場合に限ります。この条件はトポロジ次第で、満たす隣が無い宛先が残ります。
- **リモート LFA**(RFC 7490): もっと遠いルータまでトンネルで運んでから放します。LDP のターゲット セッションが要り、
  それでもすべての宛先はカバーできません。
- **RSVP-TE の FRR**: 迂回用のトンネルを前もって張っておきます。トンネルの状態が、通り道のルータに要ります。

**TI-LFA**(トポロジに依存しない LFA、RFC 9855)は、迂回の道順を SR のラベルで書きます。どんなトポロジでも道順は書けるので、
すべての宛先を保護できます。設定はローカル修復点だけで、トンネルもターゲット セッションも要りません。

## 2. 仕組み: 迂回の道順をラベルで書いておく

### 2.1 ただ隣に渡すと、送り返される

XR01 が、RT01 のループバック(16011)宛てのパケットを PRIMARY で送っているとします。PRIMARY が切れたら、XR01 に残る隣は
RT03 だけです。では、パケットを 16011 のまま RT03 に渡せばよいでしょうか。

RT03 から RT01 へは、XR01 を戻る道(BACKUP 100 + PRIMARY 10 = 110)と、RT02 を通る道(CORE-B 100 + CORE-A 10 = 110)が
同じコストです。障害の直後、RT03 はまだ障害を知らないので、パケットの一部を XR01 へ、つまり切れた PRIMARY へ送り返します。
これが、RT01 のループバック宛てに通常の LFA が無い理由です。

RT02 のループバック宛てなら、事情が違います。RT03 から RT02 へは、直結の 100 が XR01 を戻る 120 より短いので、RT03 は
送り返しません。RT02 宛てには通常の LFA があります。

### 2.2 経由地を 1 つ足す

送り返しを防ぐには、RT03 に「まず RT02 へ」と命じれば足ります。RT03 から RT02 は直結が最短で、RT02 から RT01 は CORE-A
の直結が最短です。どちらの区間も PRIMARY を通りません。そこで XR01 は、迂回のときに 16011 の上に RT02 の 16012 を
重ねて、RT03 へ送ります。

:::topo
nodes:
  XR01: [0, 1]
  RT01: [1.4, 0.15]
  RT03: [1.4, 1.85]
  RT02: [2.8, 1]
links:
  - {a: XR01, b: RT01, label: "× PRIMARY", style: dashed}
  - [XR01, RT03, "16012 | 16011"]
  - [RT03, RT02, "16011"]
  - [RT02, RT01, "IP"]
:::

RT03 は 16012 を見て RT02 へ送り、その 1 つ手前なので 16012 を外します。RT02 は 16011 を見て RT01 へ送り、その 1 つ手前
なので 16011 を外します。RT01 にはただの IP パケットが届きます。

この迂回の道(XR01 → RT03 → RT02 → RT01)は、PRIMARY が無くなった後に IS-IS が収束して選ぶ道そのものです。TI-LFA は
**収束後の道**を前もって計算し、そこをたどらせるラベルを選びます。迂回の間と収束の後で道が同じなので、収束の途中で
パケットが 3 本目の道を通ることはありません。

### 2.3 経由地の選び方: P 空間と Q 空間

TI-LFA は、経由地を次の 2 つの集合から選びます。

- **P 空間**: XR01 がパケットを隣(ここでは RT03)に渡したとき、そこから切れたリンクを通らずに最短パスで着けるルータ。
  四角形のルータでは RT03 と RT02 です。
- **Q 空間**: そこから宛先まで、切れたリンクを通らずに最短パスで着けるルータ。RT01 宛てなら RT02(と RT01 自身)です。

両方に入るルータがあれば、それを経由地にすれば済みます。ラベルは「経由地へ」と「宛先へ」の 2 枚です。出力ではこの
ルータを P ノードと呼んでいます。ここでは RT02 で、2.2 節の 16012 がそれです。

両方に入るルータが無いこともあります。PoC で BACKUP のメトリックを 10 にし、CORE-B を 100 のままにすると、RT03 から RT02
へは XR01 と PRIMARY を戻るほうが安くなり(10 + 10 + 10 = 30)、RT02 は P 空間から外れました。このとき TI-LFA は、P 空間の
最後のルータ(RT03)から Q 空間の最初のルータ(RT02)へ、隣接 SID でリンクを指定してつなぎます。

```console
       Backup path: TI-LFA (link), via 10.0.3.13, GigabitEthernet0/0/0/1 RT03, SRGB Base: 16000, Weight: 0, Metric: 130
         P node: RT03.00 [10.255.0.13], Label: ImpNull
         Q node: RT02.00 [10.255.0.12], Label: 23
         Prefix label: 16011
```

ラベル 23 は、RT03 の RT02 へのリンク(CORE-B)の隣接 SID です(RT03 の `show mpls forwarding-table` が `10.0.23.12-A` として
並べます)。RT03 は XR01 の隣なので、RT03 へのラベルは付けません(`ImpNull`)。CEF のエントリでは、迂回は
`{ImplNull 23 16011}` でした。

### 2.4 四角形での実際

元のメトリックに戻した四角形で、XR01 が RT01 のループバック宛てに用意した迂回です。

```console
RP/0/RP0/CPU0:XR01#show isis fast-reroute 10.255.0.11/32 detail
L2 10.255.0.11/32 [20/115] Label: 16011, medium priority
     via 10.0.1.11, GigabitEthernet0/0/0/0, Label: ImpNull, RT01, SRGB Base: 16000, Weight: 0
       Backup path: TI-LFA (link), via 10.0.3.13, GigabitEthernet0/0/0/1 RT03, SRGB Base: 16000, Weight: 0, Metric: 220
         P node: RT02.00 [10.255.0.12], Label: 16012
         Prefix label: 16011
         Backup-src: RT01.00
       P: No, TM: 220, LC: No, NP: No, D: No, SRLG: Yes

RP/0/RP0/CPU0:XR01#show cef 10.255.0.11/32 detail
...
   via 10.0.1.11/32, GigabitEthernet0/0/0/0, 4 dependencies, weight 0, class 0, protected [flags 0x400]
     local label 16011      labels imposed {ImplNull}
   via 10.0.3.13/32, GigabitEthernet0/0/0/1, 8 dependencies, weight 0, class 0, backup (TI-LFA) [flags 0xb00]
    next hop 10.0.3.13/32, Repair Node(s): 10.255.0.12
     local label 16011      labels imposed {16012 16011}
```

読み方です。`via 10.0.1.11` がふだんの道(PRIMARY)、`Backup path: TI-LFA (link), via 10.0.3.13` が迂回の出口(RT03)、
`P node: RT02.00 … Label: 16012` が経由地、`Prefix label: 16011` が宛先のラベルです。`Metric: 220` は収束後の道のメトリック
です。CEF では、ふだんの道に `protected`、迂回に `backup (TI-LFA)` が付き、迂回は `{16012 16011}` を付けます。2.2 節の図
そのものです。

### 2.5 設定

IOS XR では、各インターフェイスに 2 行が要ります。`fast-reroute per-prefix` がプレフィックスごとの保護を有効にし、
`fast-reroute per-prefix ti-lfa` がそれに SR を使わせます。既定はリンクの保護です。ノードの保護と SRLG の保護は、
自分で足すタイブレーカです(`fast-reroute per-prefix tiebreaker node-protecting index <n>`)。迂回に 4 枚以上のラベルが
要るとき、IOS XR はそれを自動の SR-TE ポリシーとして作ります。

ラボの IOS ルータも、`router isis` の下の `fast-reroute per-prefix level-2 all` と `fast-reroute ti-lfa level-2` で、自分の
プレフィックスを保護しています(`show isis fast-reroute ti-lfa tunnel`)。

## 3. 速さを決めるのは、気づくまでの時間

迂回がどれだけ速く効くかは、障害を検出する速さで決まります。CML では、リンクに障害が起きても、リンクを止めても、
IOS XRv 9000 のインターフェイスは落ちません。IS-IS は hello のホールド タイムの 30 秒を待つことになります。BFD(M7)は、
それを BFD の検出時間、ラボと同じ 100 ms × 3 なら 300 ms まで縮めます。

ラボでは、リンク条件で PRIMARY のパケットをすべて落とす間、CEA1 から CEA2 への顧客 A のトラフィックを 10 ms ごとに
測りました。

| XR01 で | 失われた数(1 つ 10 ms) |
|---|---|
| BFD あり、TI-LFA なし | 42 |
| BFD と TI-LFA | 34〜40 |
| BFD あり、TI-LFA なし、SPF を遅らせる(1 秒、最長 5 秒まで伸びる) | 342 と 467 |
| BFD と TI-LFA、SPF を遅らせる(1 秒、最長 5 秒まで伸びる) | 41 と 34 |

この小さなネットワークでは、IS-IS は BFD が知らせてから約 100 ms で収束するので、TI-LFA が稼ぐ時間はわずかで、検出の
時間が大半を占めます。差が見えるのは収束が遅いとき、たとえばプレフィックスの多い大きなネットワークです。ラボでは、
SPF を遅らせてそれを模しました(`spf-interval`。最初の待ちは 1 秒で、変化が続くと最長 5 秒まで伸びます。試験の間は
そうなっていました)。TI-LFA があれば、IS-IS が何をしていても、止まる時間は検出の時間のままです。

ほかに 2 つのことが分かりました。IOS XR の BFD は、フラップするセッションを抑えます(dampening)。障害のたびに、
セッションを再び上げるまでの待ちを長くし(2 秒、次に 5 秒、ラボでは最長 2 分まで)、IS-IS もそれを待ちます。2 回の試行の
間は数分待つか、抑えを無効にしてください(`bfd` → `dampening disable`)。また、ガイドは 50 ms を約束していません。IOS XE の
ガイドは、TI-LFA は「50 ms を保証できない」と書いています。

:::try
TI-LFA を自分で ping で測ります。課題 M10-3 の後に行います。

1. XR01 の `router isis CORE` → `address-family ipv4 unicast` の下に
   `spf-interval initial-wait 5000 secondary-wait 5000 maximum-wait 10000` を足してコミットします。大きなネットワークを模します。
2. CEB1 で `ping 10.102.2.1 source Loopback10 repeat 10000 timeout 1` を始めます(課題 M10-4 の後は顧客 A が PRIMARY を避けるので、
   顧客 B を使います)。その間に、CML で PRIMARY に 100 % の損失のリンク条件を入れ(リンクの Link Conditions タブ)、10 秒後に
   外します。
3. XR01 で GigabitEthernet0/0/0/0 から `fast-reroute` の 2 行を外してコミットし、2 分待ってから(BFD の抑え)、手順 2 をもう一度
   行います。
4. `fast-reroute` の行を戻し、`spf-interval` を外してコミットします。

ラボで測った結果: TI-LFA があると毎回 1 個、無いと毎回 6 個の ping が失われました(それぞれ 2 回ずつ)。ping のタイムアウトは
1 秒なので、1 個は 1 秒より短い停止(BFD の 300 ms)を、6 個はそれに SPF の前の 5 秒の待ちが加わったことを表します。通常の
SPF のタイマーで TI-LFA があるときも、失われたのは 1 個でした。障害のたびに、リンク条件を外した後も、BFD の抑えが RT01 との
隣接を 40〜120 秒落としたままにしました。
:::

## 4. マイクロループ

迂回が効いた後も、IS-IS はいつもどおり収束します。そのとき、ルータはみな同じ瞬間に転送テーブルを書き換えるわけでは
ありません。ルータ A が新しい表で B へ送り、B はまだ古い表で A へ送り返す、という短い間があると、パケットは 2 台の間を
行き来して失われます。これが**マイクロループ**です。TI-LFA は障害の直後の迂回を受け持ちますが、その後の収束の間の
ループは扱いません(RFC 9855)。

IOS XR には別の機能、IS-IS のアドレス ファミリーの `microloop avoidance segment-routing` があります。トポロジが変わった後
しばらく(`microloop avoidance rib-update-delay`、既定で 5000 ms)、XR01 は影響を受けるトラフィックを、ラベルを重ねて書いた
ループの無い道で送り、他のルータの表がそろってから新しい最短パスに切り替えます。`show isis protocol` は
`Microloop avoidance: Enabled` と `Type: Segment Routing` を表示します。IOS XR では既定で無効です。IOL ルータは
`show isis fast-reroute summary` で `enabled for segment-routing microloop avoidance` と表示します。

## 5. コマンド名

| IOS XE では | IOS XR では |
|---|---|
| `fast-reroute per-prefix level-2 all` + `fast-reroute ti-lfa level-2`(`router isis` の下) | `fast-reroute per-prefix` + `fast-reroute per-prefix ti-lfa`(インターフェイスごと) |
| `show isis fast-reroute ti-lfa tunnel` | `show isis fast-reroute <プレフィックス> detail` |
| `show isis fast-reroute summary` | `show isis fast-reroute summary` |

## 実践

ラボ **XRT-10** で、課題 M10-3 に取り組みます。終わったら、次のページ「SR ポリシーと PCE」に進みます。

<p class="tolab"><a href="/_learn?id=XRT-10&amp;step=m10t3">ワークスペースで課題 M10-3 を開く</a> — <a href="a3-m10-practice-2.html">課題</a></p>

:::note
出典: Segment Routing Configuration Guide for the ASR 9000, IOS XR 26.1.x–26.3.x(2026。TI-LFA、マイクロループ回避)と
そのコマンド リファレンス(2025)。IOS XE Segment Routing Configuration Guide(2026。TI-LFA)。RFC 5286、7490、9855。
いずれも 2026 年 10 月に確認しました。迂回の道とラベル、P ノードと Q ノード、止まった時間の測定、BFD の抑えは、ラボ
XRT-10 とその PoC での測定によります。
:::
