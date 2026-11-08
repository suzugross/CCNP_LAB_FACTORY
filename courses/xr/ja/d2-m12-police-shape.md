# M12 — ポリシングとシェーピング

前のページでは、パケットに印を付けて、どのクラスかをコアに伝えました。このページでは、その印を使って、量を決めます。
契約の速さを超えた分をどうするか(ポリシング)、混んだ出口でどう並べるか(シェーピングとキュー)です。ブループリントの
4.5.b(輻輳回避、トラフィック ポリシング、シェーピング)にあたります。

## 1. 何が嬉しいのか

### 1.1 困りごと: 契約の速さと、混んだ出口

顧客 A は、業務の通信(AF11 や AF21)について「ふだんは 256 kbps まで、混んでいなければ 512 kbps まで」のような契約を
結んでいます。顧客の CE は回線の速さ(1 Gbps のポートなど)で送れるので、契約を超えた分をプロバイダーが入口で抑えなければ、
1 つの顧客がコアを使い切り、ほかの顧客の取り分を奪います。

反対の向きにも困りごとがあります。顧客のサイトへの出口は、ポートが 1 Gbps でも、その先の契約が 2 Mbps のことがあります。
プロバイダーが 1 Gbps で送り出すと、その先の機器(顧客のアクセス回線の装置など)で、どれを捨てるかの判断なしにパケットが
捨てられます。音声も大量のデータも区別されません。

### 1.2 それ以前の手

- **回線の速さで契約を作る**: 2 Mbps の契約には 2 Mbps の回線を引けば、物理の速さが上限になります。ところが、契約を変える
  たびに回線を引き直すことになり、1 本の太い回線に何人もの顧客を収容することもできません。
- **入口で全部捨てる**: 契約を超えた分を一律に捨てれば、コアは守れます。ところが、TCP は少しの欠落で送る速さを大きく下げるので、
  「少し超えた分は運んで、混んだときだけ先に捨てる」という柔らかい扱いができません。

### 1.3 ポリシングとシェーピングの答え

- **ポリシング**: 入ってくる速さを測り、契約に収まる分・少し超えた分・大きく超えた分の 3 つ(または 2 つ)に色分けします。
  色ごとに「そのまま運ぶ」「印を付け替えて運ぶ」「捨てる」を決めます。待たせないので遅れは増えませんが、超えた分は
  その場で処理されます。
- **シェーピング**: 出ていく速さを決めた値に均します。超えた分はキューで待たせ、少し後に送ります。捨てる代わりに遅らせるので、
  TCP にやさしい一方、遅れが増えます。
- **キューと優先**: 出口に複数のキューを作り、音声のキューを先に送ります(優先キュー)。待たされるのは急がない通信の方です。

## 2. 仕組み

### 2.1 トークン バケツ: 1 速度 2 色

ポリサは、トークンの入ったバケツで速さを測ります。バケツには契約の速さ(CIR、Committed Information Rate)でトークンが
貯まり、容量はバースト(Bc)です。パケットが来たとき、その長さ分のトークンがあれば**適合**(conform)で、トークンを使います。
足りなければ**超過**(exceed)です。

- バケツが満杯なら、Bc までは一度に送ってもよい(瞬間的な固まりを許す)ということです。
- 長い目で見ると、適合する量は CIR × 時間 + Bc です。

XR01 で、AF11 のクラスに 64 kbps のポリサを当て、CE1 から 500 バイトの ping を間を空けずに送りました。数えた 876 発のうち適合は
5 発で、残りの 871 発は超過として捨てられました。

```console
RP/0/RP0/CPU0:XR01#show policy-map interface GigabitEthernet0/0/0/1 input
...
Class BULK
  Classification statistics          (packets/bytes)     (rate - kbps)
    Matched             :                 876/453768               0
    Transmitted         : N/A
    Total Dropped       :                 871/451178               0
  Policing statistics                (packets/bytes)     (rate - kbps)
    Policed(conform)    :                   5/2590                 0
    Policed(exceed)     :                 871/451178               0
    Policed(violate)    :                   0/0                    0
    Policed and dropped :                 871/451178
```

### 2.2 2 速度 3 色

2 つ目のバケツを足すと、色が 3 つになります(RFC 2698 の trTCM)。1 つ目は契約の速さ(CIR)、2 つ目は最大の速さ
(PIR、Peak Information Rate)で貯まります。

| 色 | 条件 | よくある扱い |
|---|---|---|
| 適合(conform) | CIR のバケツにトークンがある | そのまま運ぶ |
| 超過(exceed) | CIR のバケツは空、PIR のバケツにはある | 捨てられやすい印に付け替えて運ぶ(AF11 → AF12) |
| 違反(violate) | どちらのバケツも空 | 捨てる |

付け替えた AF12 は、同じクラス(AF1)のまま運ばれるので、順番は入れ替わりません。コアや出口が混んだときに、AF11 より
先に捨てられるだけです。CIR 64 kbps・PIR 1 Mbps で同じように送ると、XR01 は適合 5・超過 41・違反 789 と数え、サイト 2 の
CE2 は AF11 を 5 発、AF12 を 41 発受け取りました。数は 1 発単位で一致します。

```console
RP/0/RP0/CPU0:XR01#show policy-map interface GigabitEthernet0/0/0/1 input
...
    Policed(conform)    :                   5/2590                 0
    Policed(exceed)     :                  41/21238                0
    Policed(violate)    :                 789/408702               0
    Policed and dropped :                 789/408702

```

CE2 の入力の数えるだけのポリシーは、同じ時間に D-AF11 を 5 発、D-AF12 を 41 発と数えました。

### 2.3 シェーピング: 待たせて均す

シェーパも同じトークン バケツで速さを測りますが、トークンが足りないパケットを捨てずに、キューで待たせます。トークンが
貯まったら送ります。出ていく速さは、どれだけ速く入ってきても、決めた速さを超えません。

XR01 の CE1 側の出力に、100 kbps のシェーパを当てて、CE2 から 1000 バイトのパケットを約 4 Mbps で送りました。XR01 が
CE1 へ送り出したのは 11878 発のうち 205 発(約 76 kbps)で、残りは、キューがあふれて末尾で捨てられました。

```console
RP/0/RP0/CPU0:XR01#show policy-map interface GigabitEthernet0/0/0/1 output
...
Class class-default
    Matched             :               11878/12073804             0
    Transmitted         :                 205/190690               0
    Total Dropped       :               11673/11883114             0
  Policy CE-OUT-CHILD Class class-default
...
      Taildropped(packets/bytes)           : 11673/11883114
```

待たせる分、遅れが増えます。1000 バイトの ping は、ふだん 2 ms のところ、平均 63 ms・最大 82 ms かかりました。100 kbps で
1000 バイトを送り出すのに 80 ms かかるので、キューの中で 1 個分待った計算です(2.7 節)。

### 2.4 キューと優先: LLQ

出口に、クラスごとのキューを作ります。**優先キュー**(IOS の LLQ、XR の `priority level 1`)に入ったパケットは、ほかの
キューより先に送られるので、混んでいても待ちません。その代わり、優先キューが出口を使い切ると、ほかのキューが一切
送れなくなります。そのため、優先キューには必ずポリサで上限を付けます(ASR 9000 のガイドも「優先のトラフィックを
制限するポリサを設定する必要がある」)。

ほかのクラスには、出口の残りを分け合う割合を決めます(`bandwidth remaining`)。決めなかったクラスは、残りを等しく
分けます。

### 2.5 階層の QoS

「顧客ごとに 2 Mbps に整形し、その 2 Mbps の中で音声を優先する」には、2 段のポリシーが要ります。

- **親**: 全部のパケット(`class-default`)を 2 Mbps に整形する。親には `class-default` だけを書きます。パケットは階層ごとに
  1 つのクラスにしか入らないので、親でほかのクラスに入ったパケットは子を通らず、優先キューにも入りません(IOS XRv 9000 は、
  この形もエラーなくコミットします)。
- **子**: 親が送り出す 2 Mbps の中で、クラスごとのキュー(優先と残り)を作る。親の `class-default` に `service-policy <子>` と
  書きます(向きの `input`/`output` は付けません)。

親が「量」を、子が「順番」を決めます。1 本のポートに何人もの顧客をサブインターフェイスで収容するときは、サブインターフェイス
ごとに親を当てて、顧客ごとの契約の速さを作ります。

### 2.6 輻輳回避: WRED

キューがあふれるまで待ってから末尾で捨てると(テール ドロップ)、そのキューを通る TCP のセッションが一斉に欠落を受けて、
一斉に速さを落とし、一斉に戻ります。回線が波打つように使われ、平均の使用率が下がります。

**WRED**(Weighted Random Early Detection)は、キューが長くなり始めた段階で、確率で少しずつ捨てます。キューの長さが
最小のしきい値を超えると捨て始め、最大のしきい値に近づくほど高い確率で捨てます。「Weighted」は、印ごとにしきい値を変える
ことです。AF12 のしきい値を AF11 より低くすれば、混み始めたとき AF12 が先に捨てられます(RFC 2597 の 4 節は、AF の捨てられ
にくさを実装する例として RED を挙げています)。WRED はキューのあるクラスでしか動かないので、同じクラスに `shape`・
`bandwidth`・`bandwidth remaining` のどれかが要ります。

### 2.7 押さえどころと、XRv 9000 で分かったこと

- ポリシングは**測って色分けし、その場で処理する**(遅れなし)。シェーピングは**待たせて均す**(遅れが増える)。
- 3 色は「運ぶ・付け替えて運ぶ・捨てる」。付け替えは同じ AF のクラスの中で(順番を保つ)。
- 優先キューには必ず上限のポリサ。親で整形・子で優先、の 2 段で顧客ごとの契約を作る。

XRv 9000 26.1.1(このラボの XR01)では、次のことが分かりました。課題の確認はこれに合わせてあります。

| 項目 | 結果 |
|---|---|
| ポリサ(1 速度 2 色・2 速度 3 色・付け替え) | 効く。数も相手の CE で数えたものと一致する |
| シェーパと優先キュー | 速さは絞れる。優先のクラスも数える。ただしキューは 1 個分ほどしか溜まらない(表示の Q-Limit は 0) |
| WRED | 設定は入るが、捨てた数がいつも 0 と表示され、効き目を確かめられない |
| 無ライセンスの速さ | 公式文書は「200 kbps に制限」と書くが、このラボでは約 4 Mbps 通った |
| カウンタ | 10〜30 秒遅れて増える |

そのため、このラボでは、遅れの差で優先の効き目を見るのではなく、ポリシーの形(`show qos interface`)と、相手の CE が数えた
印で確かめます。WRED は仕組みと書き方だけを知っておきます。

## 3. IOS XR で組む

### 3.1 ポリサ

1 速度 2 色は、`police rate` と、色ごとの動作を書きます。

:::config XR01 — 大量のデータを 64 kbps に抑える(1 速度 2 色)
policy-map CE-IN
 class BULK
  set mpls experimental imposition 2
  police rate 64 kbps                         ## 契約の速さ。単位は bps・kbps・mbps・gbps・pps。最小は 64 kbps
   conform-action transmit                    ## 適合はそのまま
   exceed-action drop                         ## 超過は捨てる
  !
 !
 end-policy-map
:::

2 速度 3 色は、`peak-rate` を足し、超過と違反の動作を分けます。超過の動作に印を書くと、その印も「クラスの印の数」に入ります
(1 クラス 2 種類まで。前のページの 3.5 節)。

:::config fold XR01 — 大量のデータに契約と最大の 2 つの速さを付ける(2 速度 3 色)
policy-map CE-IN
 class BULK
  set mpls experimental imposition 2          ## 印の 1 種類目
  police rate 64 kbps peak-rate 1 mbps        ## CIR と PIR
   conform-action transmit
   exceed-action set dscp af12                ## 印の 2 種類目。ここに qos-group も足すとコミットが拒まれる
   violate-action drop
  !
 !
 end-policy-map
:::

バーストを書かないと、XRv 9000 は 64 kbps に 1600 バイト、1 Mbps に 12500 バイト(100 ms 分)を選びました
(`show qos interface` の `Burst: … (0 Default)`)。

```console
RP/0/RP0/CPU0:XR01#show qos interface GigabitEthernet0/0/0/1 input
...
Level: 0 Policy: CE-IN Class: BULK
...
Policer Profile: 0 (TrTCM)
Conform: 64 kbps (64 kbps) Burst: 1600 bytes (0 Default)
Peak: 1000 kbps (1 mbps) Burst: 12500 bytes (0 Default)
Child Policer Conform: set exp-imp 2
Child Policer Exceed: set exp-imp 2   set dscp 12
Child Policer Violate: DROP
```

`TrTCM` は 2 速度 3 色の印です。`set dscp 12` は AF12 の 10 進の値です。

### 3.2 整形と優先(階層)

親で 100 kbps に整形し、子で EF を優先(上限 32 kbps)にします。子の残りのクラスには、キューの長さを決めています。

親と子のポリシーは、名前で入れ子になります。インターフェイスが親を指し、親の class-default が子を指します。図は、サイト 1 へ
向かうパケットが通る順です。図の番号にカーソルを置くと(スマホでは押すと)、その部分の設定が出ます。

:::walk
rows:
  - {node: P1, say: ["~サイト 1 宛ての音声(EF)と、1000 バイトのデータが来る"]}
  - {wire: "[[IP EF]] [[IP データ]] [[IP データ]]"}
  - panel: XR01
    sub: サイト 1 への出口(Gi0/0/0/1 の出力)
    items:
      - ref: 1
        head: "**親** `service-policy output CE-OUT`"
        say: ["親のクラスは class-default だけ。どのパケットもここに入り、書いてある子へ渡る"]
        match:
          - ["class class-default", true, "全部 → `service-policy CE-OUT-CHILD`"]
      - ref: 2
        head: "**子** `policy-map CE-OUT-CHILD` 親から来たパケットを仕分けて並べる"
        match:
          - ["class VOICE  match dscp ef", true, "EF → 優先キュー"]
          - ["class class-default", true, "データ → 残りのキュー"]
        then:
          - "[[IP EF]] 優先キュー(`priority level 1`・上限 `police rate 32 kbps`)"
          - "[[IP データ]] [[IP データ]] 残りのキュー(`queue-limit 20 packets`)"
      - ref: 3
        head: "**親の整形** `shape average 100 kbps`"
        say: ["子のキューから選ばれたパケットを、出口全体で 100 kbps に抑えて送る。超えた分は待つ"]
  - {wire: "[[IP EF]] [[IP データ]] _合わせて 100 kbps まで"}
  - {node: CE1, kind: host}
  - aside: "親に class-default 以外のクラスを書くと"
    say: ["~親でそのクラスに入ったパケットは子を通らない → 優先キューに入らず、残りのキューで待つ(コミットは通る)"]
:::

:::config fold XR01 — サイト 1 への出口を整形し、音声を優先する
policy-map CE-OUT-CHILD                       ## ② 子= 順番
 class VOICE
  priority level 1                            ## 優先キュー
  police rate 32 kbps                         ## 優先には上限が要る
  !
 !
 class class-default
  queue-limit 20 packets                      ## 残りのキューの長さ
 !
 end-policy-map
!
policy-map CE-OUT                             ## ① 親= 量。クラスは class-default だけ
 class class-default
  shape average 100 kbps                      ## ③ 出口全体の速さ
  service-policy CE-OUT-CHILD                 ## 子を入れる。input/output は付けない
 !
 end-policy-map
!
interface GigabitEthernet0/0/0/1              ## ① 親を出力に当てる
 service-policy output CE-OUT
:::

```console
RP/0/RP0/CPU0:XR01#show qos interface GigabitEthernet0/0/0/1 output
Interface: GigabitEthernet0_0_0_1 output
Bandwidth configured: 100 kbps Bandwidth programmed: 100 kbps
ANCP user configured: 0 kbps ANCP programmed in HW: 0 kbps
Port Shaper programmed in HW: 100 kbps
Policy: CE-OUT Total number of classes: 3
----------------------------------------------------------------------
Level: 0 Policy: CE-OUT Class: class-default
Bandwidth: 0 kbps, BW sum for Level 0: 0 kbps, Excess Ratio: 1
Shape Info: rate 100 kbps, burst 1250 bytes,
QueueID: N/A
----------------------------------------------------------------------
Level: 1 Policy: CE-OUT-CHILD Class: VOICE
Bandwidth: 0 kbps, BW sum for Level 1: 0 kbps, Excess Ratio: 0
Parent Policy: CE-OUT Class: class-default
QueueID: 32 (Priority 1)
Queue Limit: 0 kbytes
Policer Profile: 0 (Single)
Conform: 32 kbps (32 kbps) Burst: 1600 bytes (0 Default)
...
Level: 1 Policy: CE-OUT-CHILD Class: class-default
...
QueueID: 33 (Priority Normal)
Queue Limit: 5 kbytes (20 packets)
```

親の `Shape Info` と、子の `QueueID: 32 (Priority 1)`(優先キュー)・`QueueID: 33 (Priority Normal)` が、2 段の形です。
同じクラスに `bandwidth`・`priority`・`shape average` を一緒に書くことはできません(ASR 9000 のガイド)。

### 3.3 WRED の書き方

WRED は、キューのあるクラスに `random-detect` を書きます。既定のしきい値なら `random-detect default`、印ごとに分けるなら
`random-detect dscp <値> <最小> <最大>` です(1 クラスにしきい値の組は 2 つまで)。

:::config XR01 — 残りのキューに、印ごとの WRED(XRv 9000 では効き目を確かめられない)
policy-map CE-OUT-CHILD
 class class-default
  queue-limit 20 packets
  random-detect dscp af11 10 packets 20 packets   ## AF11 は 10 個から捨て始め、20 個で全部捨てる
  random-detect dscp default 5 packets 10 packets ## 印なしは早めに捨て始める
 !
 end-policy-map
:::

XRv 9000 はこの設定を受け付けますが、WRED が捨てた数を示す `show policy-map interface` の `RED random drops` と
`Taildropped` は、0 のままでした(2.7 節)。

### 3.4 IOS XE で書くと

IOS XE の書き方の違いは、ポリサの速さの単位(既定は bps)と、超過の付け替えの書き方です。

:::config PE2(IOS XE)— 業務のデータに 2 速度 3 色のポリサ
policy-map POLICE-DATA
 class DATA
  police cir 256000 pir 512000                ## bps で書く
   conform-action transmit
   exceed-action set-dscp-transmit af22       ## 付け替えて運ぶ
   violate-action drop
:::

当てると、`show policy-map POLICE-DATA` は `police cir 256000 bc 8000 pir 512000 be 16000` と、バーストの既定値(bc・be、
バイト)を足して表示します。

### 3.5 確かめ方

| 見たいこと | コマンド |
|---|---|
| ポリシーが装置にどう入ったか(速さ・バースト・キュー・動作) | `show qos interface <IF> input`・`output` |
| クラスごと・色ごとに数えた数 | `show policy-map interface <IF> input`・`output`(★数十秒待つ) |
| 数を消す | `clear qos counters interface <IF> input`・`output` |
| 相手が受け取った印 | 相手の機器の入力に、数えるだけのポリシー(このラボの CE1・CE2 の `COUNT-DSCP`) |

:::try
ポリサの 3 色を、送った側と受けた側の両方で数えます。課題 M12-2 を終えた後に行います(設定は変えません)。

1. XR01 で `clear qos counters interface GigabitEthernet0/0/0/1 input`、CE2 で `clear counters Ethernet0/0` を実行します。
2. CE1 で `ping 10.21.2.1 source Loopback21 repeat 1000 size 500 timeout 0` を実行します(応答を待たないので、成功率は 0 と
   表示されます)。
3. すぐに XR01 で `show policy-map interface GigabitEthernet0/0/0/1 input` を見て、30 秒後にもう一度見ます。CE2 で
   `show policy-map interface Ethernet0/0 input` を見ます。

結果の例: すぐに見た XR01 の数は、DATA のクラスの Matched も色ごとの数も 0 でした。30 秒後には Matched 924、
適合 15・超過 15・違反 894(捨てた)になりました。CE2 の `COUNT-DSCP` は D-AF21 を 15、D-AF22 を 15 と数え、XR01 の適合と
超過の数に一致しました。
:::

## 実践

ラボ **XRT-14** で課題 M12-2 と M12-3 に取り組みます。課題 M12-3 では、前のページの出口の PE(3.3 節)と、このページの
整形と優先を組み合わせます。

<p class="tolab"><a href="/_learn?id=XRT-14">ワークスペースでラボ XRT-14 を開く</a> — <a href="d3-m12-practice-2.html">課題 M12-2、M12-3</a></p>

:::note
このページの出力は、前のページと同じ盤面で取得しました。
出典: RFC 2698(trTCM)、RFC 2597(4 節)、RFC 3246(2 節)。ASR 9000 の Modular QoS Configuration Guide と Modular QoS Command Reference
(IOS XR 24.x。`police` の構文と単位・最小 64 kbps・既定のバースト、`shape average`、`priority level` とポリサ、`bandwidth remaining`、
`queue-limit`、`random-detect` とキューの要件、階層のポリシーの決まり)。IOS XRv 9000 の Installation and Configuration Guide
(スマート ライセンスの章・データ プレーンの章)と IOS XR 25.1.1 のリリース ノート。いずれも 2026 年 11 月に確認。次の項目は、PoC の
盤面(XRT-14 と同じ形)での実測によるものです。ポリサの色ごとの数と相手の CE の数の一致、既定のバースト、シェーパの送り出した量と
遅れ、キューの深さ、WRED の数、無ライセンスでの通過量、カウンタの遅れ。
:::
