# M4 — IS-IS をさらに深く

M4 の最初のページでは、どの IS-IS ネットワークにも要るものを扱いました。このページでは、プロバイダーのネットワークで
毎日使い、しかも後の単元では改めて出てこないものを 4 つ足します。認証、ブロードキャスト セグメントと DIS、要約、
エリア アドレスです。オーバーロード、タイマー、BFD、グレースフル リスタートは M7(高可用性)で、MPLS とセグメント
ルーティングのための IS-IS の拡張は M8 と M10 で扱います。

このページの出力は、IOS XRd 26.1.1 と IOL 上の IOS XE 17.15 で取ったものです(ラボ XRT-05)。

## 1. 認証

### 1.1 何を認証するか

IS-IS が認証するのはセッションではなく PDU で、認証の場所は 2 つに分かれています。

| 対象 | 範囲 | IOS XR での設定 | IOS での設定 |
|---|---|---|---|
| ハロー | 1 つのインターフェイスの IIH | `router isis` のインターフェイスの下に `hello-password` | インターフェイスに `isis authentication …` |
| データベース | 1 つのレベルの LSP とシーケンス番号 PDU(CSNP・PSNP) | `router isis` の下に `lsp-password` | `router isis` の下に `authentication …` |

どちらもレベルごとに設定します。レベルを付けなければレベル 1 とレベル 2 の両方に効きます。ポイントツーポイント
リンクでは 1 つのハローが両方のレベルを兼ねるので、ハローについてはレベルの指定に意味がありません。

認証の値は PDU の中の TLV(タイプ 10)で運ばれます。値は、リンク上の誰でも読める平文のパスワードか、PDU 全体の
HMAC-MD5 ダイジェスト(RFC 5304)です。HMAC-MD5 の TLV にはキー ID が入らないので、両端のルータはキー文字列を
そろえる必要がありますが、キーの番号はそろえなくて構いません。より強いアルゴリズム(HMAC-SHA、RFC 5310)では
キー ID が加わります。

### 1.2 IOS XR のキー チェーン

キー チェーンは、キーに名前・文字列・アルゴリズム・使ってよい期間を与えます。IOS XR はそのすべてに厳格で、しかも
コミットの時点で必ず教えてくれるとは限りません。

| 項目 | IOS XR の動作 |
|---|---|
| `key-string clear <文字列>` | 文字列を保存し、以後は暗号化した形で表示する。`clear` が既定 |
| `key-string password <文字列>` | **暗号化済み**の形を期待する。平文を渡すとコミットが失敗する: `'Key Chain Server Process' detected the 'fatal' condition 'Incorrect or NULL parameter(s)'` |
| `cryptographic-algorithm` が無い | コミットは通るが、ダイジェストを計算できない。キーは使われない |
| `accept-lifetime` / `send-lifetime` が無い | コミットは通るが、キーが有効にならない。キーは使われない |
| `hello-password keychain` で存在しないキー チェーンを指定 | コミットは通り、受け取ったハローはすべて認証に失敗する |

キーが使えるかどうかは `show key chain` が教えてくれます。有効期間の無いキーは `Not configured` と表示され、
`[Valid now]` が付きません。

```console
RP/0/RP0/CPU0:XR01#show key chain ISIS-L2
Key-chain: ISIS-L2 -

  timezone -- local
  Key 1 -- text "01310454550E4B5D711E18"
    Cryptographic-Algorithm -- HMAC_MD5
    Send lifetime -- Not configured
    Accept lifetime -- Not configured
```

両方の有効期間を設定すると、こうなります。

```console
    Send lifetime --  00:00:00, 01 Jan 2026 - Always valid  [Valid now]
    Accept lifetime -- 00:00:00, 01 Jan 2026 - Always valid [Valid now]
```

:::note
Cisco のキー チェーンの設定ガイドは、有効期間なしで設定したキーは無効で「設定時に拒否される」と書いています。
IOS XRd 26.1.1 では、そのキーはコミットで受け付けられ、ただ使われないだけで、最終的な結果(認証の失敗)は同じです。
同じガイドは有効期間のコマンドを任意としています。キーが使われるかどうかは、コミットではなく `show key chain` で確かめます。
:::

### 1.3 食い違いはどう見えるか

認証を設定していないルータは、認証を検査しません。ダイジェストの付いた PDU も受け入れ、自分の PDU には何も付けません。
認証を設定したルータは、正しいダイジェストの無い PDU をすべて捨てます。そのため、途中までの変更は片側にだけ現れます。

ネイバーがハローを認証していて XR01 がしていないとき、XR01 はネイバーのハローを見て `Init` と表示し、ネイバーは
XR01 のハローを捨てます。隣接はいつまでも上がりません。XR01 がハローを認証しているのに使えないキーを指定している
ときは、捨てているのは XR01 の側で、インターフェイスの表示にそう出ます。

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/1 | include "Rejected|Received"
  Last IIH Received:        12:59:15 (00:02:16 ago), 1496 octets
  Last PDU Rejected:        13:01:29 (2.18 sec ago), 1496 octets, P2P IIH, Authentication Failed
```

ハローは合っていて、LSP はネイバーだけが認証しているとき、隣接は上がり、XR01 はネイバーの LSP を受け入れます。
XR01 はバックボーンの経路をすべて持ちます。ネイバーは XR01 の LSP を捨てるので、バックボーンには XR01 のエリアへの
経路がありません。手がかりがもう 1 つあります。ルータのホスト名は LSP(TLV 137)で運ばれるので、XR01 の LSP を
捨てたネイバーは、XR01 をシステム ID で表示します。

```console
RT02#show clns neighbors
System Id       Interface     SNPA                State  Holdtime  Type Protocol
0102.5500.0001  Et0/0         5254.00dd.b44f      Up     29        L2   IS-IS
RT03            Et0/1         aabb.cc00.3410      Up     24        L2   IS-IS
RT03            Et0/2         aabb.cc00.3420      Up     8         L2   IS-IS
```

### 1.4 あるレベルを認証しないままにする

レベルを付けない `lsp-password` は、レベル 1 も認証します。認証しないレベル 1 のネイバーは XR01 の LSP を引き続き
受け入れますが、XR01 はそのネイバーの LSP とシーケンス番号 PDU を捨てるようになります。その場では何も起きません。
XR01 はすでに持っているネイバーの LSP のコピーを保ち続けます。次にネイバーがプレフィックスを変えて新しい LSP を
フラッディングしたとき、XR01 はそれを拒否し、古いコピーのまま経路を計算し続けます。

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/0 | include "Rejected|Received"
  Last IIH Received:        13:07:00 (3.29 sec ago), 1496 octets
  Last PDU Rejected:        13:07:02 (0.84 sec ago), 285 octets, L1 LSP, Authentication Failed
```

IS-IS は寿命(最大 1200 秒)の尽きた LSP を取り除くので、古いコピーが寿命を迎えると、ネイバーの経路も消えます。
変更から 20 分後に現れる障害は、その変更と結び付けにくいものです。レベルは明示してください。

## 2. ブロードキャスト セグメントと DIS

### 2.1 擬似ノード

ブロードキャスト セグメントでは、すべてのルータがそこにいる他のすべてのルータと隣接を作ります。各ルータが他の全員を
LSP にネイバーとして載せると、n 台のセグメントはデータベースに n × (n − 1) 個のネイバー項目を加えます。IS-IS はこれを
避けるため、レベルごとに **DIS**(指定中間システム)を選出します。DIS はセグメントのための LSP、**擬似ノード** LSP を
もう 1 つ生成します。セグメント上のルータは DIS も含めて、そのセグメントのネイバーとして擬似ノードだけを載せ、
擬似ノードはすべてのルータをメトリック 0 で載せます。

擬似ノードの LSP ID は、DIS のシステム ID に 0 でない回線番号を続けたものです。`XR01.01-00` は、XR01 が自分の LAN
インターフェイスの 1 つのために生成する擬似ノードです。

DIS は、自分が持っているすべての LSP の一覧である CSNP も、10 秒ごとにセグメントへ送ります。自分のデータベースで
LSP が欠けているか古いと気づいたルータは、PSNP でそれを要求します。バックアップ DIS はありません。DIS が落ちると
残りのルータが新しい DIS を選出し、新しい DIS が新しい擬似ノード LSP を生成します。

### 2.2 選出

**優先度**(0〜127、既定 64)の最も高いルータが DIS になります。同点なら MAC アドレス(SNPA)の大きい方が勝ちます。
優先度はレベルごとに設定し、同じセグメントでもレベル 1 とレベル 2 で DIS が別になることがあります。

OSPF の DR と違い、DIS は**プリエンプティブ**です。優先度のより高いルータが現れた時点でその役割を取り、古い DIS は
自分の擬似ノード LSP をパージし(残り寿命 0 で表示されます)、新しい DIS が擬似ノード LSP を生成します。MAC アドレスで
決まった役割は、ルータを交換したとき、ラボでは作り直したときに変わることがあります。役割を固定するには、そのルータに
他のどのルータよりも高い優先度を与えます。

IOS XR では、インターフェイスの表示に LAN ID(擬似ノード)と、自分と DIS の優先度が出ます。

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/3 | include "Media|LAN ID|Priority"
  Media Type:               LAN
    LAN ID:                 XR01.01
    Priority (Local/DIS):   100/100
```

`show isis interface brief` は、自分が DIS になっているセグメントで隣接の数に `*` を付けます。
IOS では、`show clns interface` が同じ情報を `DR ID` として表示します。

### 2.3 ポイントツーポイントとブロードキャスト

M4 の最初のページで見た食い違いは、逆向きにも起きます。LAN ハローを送るルータに面した LAN のインターフェイスを
IOS XR でポイントツーポイントにすると、そのハローを拒否します。

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/3 | include "Media|Rejected"
  Media Type:               P2P
  Last PDU Rejected:        13:10:32 (2.26 sec ago), 1497 octets, L2 LAN IIH, LAN IIH on P2P Interface
```

3 台以上のルータがいるセグメントはポイントツーポイントにできません。ちょうど 2 台のセグメントは、両端がそろえれば
ポイントツーポイントにでき、そのときは DIS も擬似ノードもありません。

## 3. 要約

### 3.1 どこで、どのように

L1/L2 ルータは、範囲の中のプレフィックスの代わりにその範囲を広告できます。IOS XR では `summary-prefix` を
`router isis` のアドレス ファミリの下に置くので、IPv4 と IPv6 は別々に要約します。レベルの指定は、要約を受け取る
レベルを表します。レベルを付けなければ、要約は両方のレベルに効きます。

| 動作 | 内容 |
|---|---|
| メトリック | 範囲の中のプレフィックスのうち最も小さいメトリック |
| 破棄ルート | ルータは範囲を Null0 向けに登録する(`type manual summary`)。範囲の中の使われていない部分へのトラフィックは、デフォルト ルートに乗らずにここで捨てられる |
| 取り下げ | 範囲の中のプレフィックスが 1 つも到達可能でなくなると、要約は取り下げられる |

```console
RP/0/RP0/CPU0:XR01#show route ipv4 10.11.0.0/16

Routing entry for 10.11.0.0/16
  Known via "isis CORE", distance 115, metric 20 (summary), type manual summary
  Installed Oct 22 13:14:04.553 for 00:00:42
  Routing Descriptor Blocks
    directly connected, via Null0
      Route metric is 20
  No advertising protos.
```

IOS XR は自分のレベル 2 の LSP の中で IPv6 の要約を `IPv6-External 2001:db8:1011::/48` と表示します。IOS ルータは
それを普通のレベル 2 のルートとして登録します。

### 3.2 何を失うか

要約はわざと詳細を隠します。バックボーンにはアクセス LAN が 1 つ落ちたことが見えなくなり、そのときに何も再計算
しません。代償は OSPF と同じです。エリアに L1/L2 ルータが 2 台あって、どちらも同じ要約を広告すると、バックボーンは
ある LAN にどちらが近いかを区別できなくなります。MPLS で必要になるループバックのように、個別のルートが要る
プレフィックスは範囲の外に置きます。

## 4. エリア アドレス

### 4.1 複数の NET

ルータは NET を **3 つ**まで持てます。システム ID はすべて同じでなければならず、違ってよいのはエリアの部分だけです。
IOS XR はそれ以外をコミットの時点で拒否します。

```console
!!% System ID must not change: 0102.5500.0001
!!% Maximum area address count exceeded: maximum number of area addresses is 3
```

レベル 1 の隣接に必要なのは、**1 つ**の共通のエリア アドレスで、すべてではありません。したがって NET を 2 つ持つ
ルータは同時に両方のエリアに属し、2 つのエリアは 1 つのレベル 1 エリアにまとまります。`show isis` は、ルータに
設定したエリア(`Manual area address(es)`)と、ネイバーから学んだレベル 1 エリア全体のエリア(`Routing for area
address(es)`)を表示します。共通のエリア アドレスが無くなると、レベル 1 の隣接はダウンし、隣接ログに `Area
addr/level differ`、最後に拒否した PDU に `Level or Area Addr mismatch` と出ます。

### 4.2 エリアの番号の付け替え

複数の NET は、エリアの番号を停止なしで付け替える方法です。エリアのすべてのルータに新しいエリア アドレスを足し、
それからすべてのルータから古いものを削除します。どの段階でも、ネイバーどうしは少なくとも 1 つのエリアを共有しています。

IOS XR では、この 2 つの段階を 2 つのコミットにする必要があります。1 つのコミットで NET を置き換えると(古いものを
`no net` し、新しいものを `net` する)、システム ID が同じで、ネイバーがすでに両方のエリアを持っていても、ルータの
**すべての**隣接が、レベル 2 も含めて張り直されます。

```console
RP/0/RP0/CPU0:XR01#show isis adjacency-log
  IS-IS CORE  Level 1  Adjacency Log             Capacity: 100, Size: 2
When          System          Interface          State   Details
--- Thu Oct 22 2026 ---
13:18:36.328  RT01            Gi0/0/0/0          d -> i
13:18:36.632  RT01            Gi0/0/0/0          i -> u  New adjacency
  IS-IS CORE  Level 2  Adjacency Log             Capacity: 100, Size: 6
When          System          Interface          State   Details
--- Thu Oct 22 2026 ---
13:18:36.028  RT03            Gi0/0/0/3          d -> u  New adjacency
13:18:36.326  RT03            Gi0/0/0/2          d -> i
13:18:36.326  RT02            Gi0/0/0/1          d -> i
13:18:36.498  RT02            Gi0/0/0/3          d -> u  New adjacency
13:18:36.628  RT03            Gi0/0/0/2          i -> u  New adjacency
13:18:36.630  RT02            Gi0/0/0/1          i -> u  New adjacency
```

新しい NET を足すコミットと古い NET を外すコミットを分けると、ログには何も増えませんでした。`show isis
adjacency-log` は、設定なしでレベルごとに直近 100 件の状態変化を保持しており、変更が何かを乱したかどうかを確かめる
いちばん手早い方法です。

## 5. コマンド名

| IOS | IOS XR |
|---|---|
| インターフェイスに `isis authentication mode md5` ＋ `isis authentication key-chain …` | `router isis` のインターフェイスの下に `hello-password keychain …` |
| `router isis` の下に `authentication mode md5` ＋ `authentication key-chain …` | `router isis` の下に `lsp-password keychain … [level 1 \| 2]` |
| `show key chain` | `show key chain` |
| `isis priority …` | `router isis` のインターフェイスの下に `priority … [level 1 \| 2]` |
| `show clns interface`(`DR ID`) | `show isis interface <名前>`(`LAN ID`・`Priority (Local/DIS)`) |
| `router isis` の下に `summary-address …` | `router isis` のアドレス ファミリの下に `summary-prefix … [level 1 \| 2]` |
| `net …`(複数) | `net …`(複数・3 つまで) |
| `show clns neighbors detail`(`Uptime`) | `show isis adjacency-log` |

## 実践

ラボ **XRT-05** に進み、M4 の 2 つ目の課題に取り組みます。XRT-04 の終わりから始まります。

<p class="tolab"><a href="/_learn?id=XRT-05">ワークスペースでラボ XRT-05 を開く</a> — <a href="43-m4-practice-2.html">課題</a></p>

:::note
出典: Cisco 8000 と NCS 5500 の IOS XR *IS-IS コマンド リファレンス*(`lsp-password` と `hello-password`・レベルを
付けないと両方のレベル・`lsp-password` が SNP も認証すること・`summary-prefix` とそのメトリックと破棄ルート・`priority`
とプリエンプティブな DIS・NET は 3 つまででシステム ID は 1 つ・`show isis adjacency-log`)、IOS XR の*キー チェーン
管理*の設定ガイドとコマンド リファレンス(`key-string clear | password`・暗号アルゴリズム・有効期間)。いずれも
2026 年 10 月に確認。IOS XE 17.x の *IP Routing Configuration Guide*「Enhancing Security in an IS-IS Network」
(ハローはインターフェイス、LSP と SNP はインスタンス)、RFC 5304(HMAC-MD5・キー ID なし)と RFC 5310、RFC 1142
(ISO 10589 の本文: DIS と擬似ノード)。次は IOS XRd 26.1.1 と IOS XE 17.15 での実測によります: コミット時のメッセージ、
コミットは通るのに使われないキー、拒否した PDU の表示、LSP の片側だけの受け入れ、レベル 1 を認証したときの遅れて
現れる影響、インターフェイスの一覧の `*`、要約の `IPv6-External` という表示、1 つのコミットで NET を置き換えたときに
すべての隣接が張り直されること。
:::
