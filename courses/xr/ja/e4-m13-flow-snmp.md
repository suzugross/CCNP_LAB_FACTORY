# M13 — フローを数え、問い合わせる: NetFlow/IPFIX と SNMP

前のページまでで、モデルを通してルータを設定し、テレメトリでカウンタを流しました。このページでは、ほぼすべてのルータで
プロバイダーが今も使っている、古くからの道具を 2 つ扱います。ルータを通って誰が誰と話しているかを数えるフロー レコードと、
管理ステーションが機器を読み取り、何か起きたときに知らせを受ける SNMP です。

ブループリントの 5.8(NetFlow/IPFIX の設定と
確認)と 5.10(SNMP v2c/v3 の設定と確認)にあたります。XRT-15 の盤面の IOS XR には NetFlow が無いので、フローは PE2(IOS XE)
で取り、SNMP は XR01 で扱います。

## 1. 何が嬉しいのか

### 1.1 困りごと: 誰が何を送っているのか、予備の線は生きているか

顧客 A は、PE2(GigabitEthernet2)を通して通信を送ります。NMS チームは、誰が何を送っているかを知りたいと考えています。
顧客 A のどのホストが、どのアドレスと、どのプロトコルで、どれだけ話しているかです。GigabitEthernet2 のインターフェイスの
カウンタは合計しか出しません。入ったパケットとバイトがいくつ、出たのがいくつ、です。回線が埋まったとき、カウンタは埋まった
ことは教えてくれますが、誰が埋めたかは教えてくれません。

XR01 から CE1 への予備の線(GigabitEthernet0/0/0/2)は、主の線が切れるまで何も運びません。予備の線が落ちても顧客は気づかず、
必要になったその日まで誰にも分かりません。NMS チームは、誰かがログインして見に行かなくても、すべてのルータがすぐに知らせて
くれることを望んでいます。

:::topo
nodes:
  CE1: {at: [0, 0], kind: host}
  PE2: [1.6, 1]
  XR01: [3.8, 1]
  SW1: [2.7, 2]
  SRV01: {at: [2.7, 3], kind: host, label: "SRV01 (NMS)"}
links:
  - {a: CE1, b: PE2, la: "Et0/0", lb: "Gi2"}
  - {a: PE2, b: XR01, la: "Gi1", lb: "Gi0/0/0/0"}
  - {a: CE1, b: XR01, label: "予備  Et0/1 – Gi0/0/0/2", t: 0.55}
  - {a: PE2, b: SW1, la: "Gi3 .2"}
  - {a: XR01, b: SW1, la: "Gi0/0/0/1 .1"}
  - {a: SW1, b: SRV01, label: "10.0.50.0/24  .10"}
:::

### 1.2 それ以前の手: カウンタ、ポーリング、キャプチャ

- **ルータを 1 台ずつ見る**: 機器ごとに `show interfaces`。合計しか分からず、分かるのも誰かが見ている間だけです。
- **カウンタをポーリングする**: ステーションが、数分ごとに全インターフェイスのカウンタ(ifTable)を読み、差分からグラフを
  描きます。多数の機器について「どれだけ」には答えられますが、「誰が」にはやはり答えられません。仕組みは 2.5 節で
  扱います。
- **パケットをキャプチャする**: 回線の通信を解析器に写します(SPAN や、ホストでの tcpdump)。誰が、も含めてすべてが
  見えますが、プロバイダーの流量では多すぎて取っておけません。見たい場所ごとに写しのポートも要ります。

### 1.3 答え: フロー レコードと管理のプロトコル

- **フロー レコード**(NetFlow、IPFIX): ルータ自身がパケットを会話ごとにまとめ、フローごとに 1 つのレコード(アドレス、
  ポート、数)にして、収集役(コレクタ)へ送ります。レコードはキャプチャよりはるかに小さく、カウンタよりはるかに中身が
  あります。NetFlow は Cisco のもので、バージョン 9 でテンプレートを取り入れました。IPFIX は、それをもとにした IETF の
  標準です。
- **SNMP**(Simple Network Management Protocol): ステーションがすべての機器からカウンタや状態を読み取り(ポーリング)、
  機器が何か起きたときにステーションへ知らせる(トラップ)ための、1 つのプロトコルです。バージョン 2c は簡単ですが
  守りがありません。バージョン 3 は、ユーザ、認証、暗号化を加えます。

テレメトリ(前のページ)は、同じカウンタを、もっと頻繁に、もっと効率よく送り出します。それでも SNMP はほとんどの機器と
ほとんどの NMS に入っており、フロー レコードはカウンタでは答えられない問いに答えます。

## 2. 仕組み

### 2.1 フローとフロー キャッシュ

フローとは、1 つの観測点(インターフェイスの、1 つの向き)を通り、ヘッダーのいくつかの欄が同じ値を持つパケットの集まり
です。「同じフローかどうか」を決める欄を**キー**の欄と呼びます。レコードが持つそれ以外の欄は**非キー**の欄です。フローの
パケットについて足し上げるカウンタ、最初と最後のパケットの時刻などです。

従来の NetFlow は、7 つのキーで固定でした。送信元と宛先のアドレス、送信元と宛先のポート、プロトコル、ToS のバイト、
入力インターフェイスです。Flexible NetFlow(IOS XE)では、キーを選べます。`match` の行がキー、`collect` の行が非キーの
欄です。キーを減らすと、より多くのパケットが 1 つのフローにまとまり(キーが 2 つのアドレスだけなら、ホストの組ごとに
1 フロー)、キーを増やすと細かく分かれます。

ルータは、フローを**フロー キャッシュ**に持ちます。モニタは、パケットごとにキーの欄を取り出し、同じキーのエントリを探して
足し込みます。無ければ作ります。

CE1 の Loopback100 から XR01 の Loopback0 へ ping を 37 発送ると、37 個のエコー要求は
アドレスも、プロトコル(ICMP)も、「ポート」も同じなので、37 パケットの 1 つのエントリになります。ICMP にポートはありません。
NetFlow は、ICMP のタイプとコードを宛先ポートの場所に入れ、nfdump はそれを `8.0`(エコー要求)と表示します。

結果の例(SRV01。キーはアドレス、プロトコル、ポート、入力インターフェイスのレコード):

```console
$ nfdump -R /var/cache/nfdump/lab -o extended -c 10 'src ip 192.168.100.1'
Date first seen             Duration     Proto      Src IP Addr:Port          Dst IP Addr:Port     Flags Tos  Packets    Bytes      pps      bps    Bpp Flows
2026-11-10 14:27:08.500     00:00:00.049 ICMP     192.168.100.1:0     ->       10.255.0.1:8.0   ........   0       37    27676      755    4.5 M    748     1
Summary: total flows: 1, total bytes: 27676, total packets: 37, avg bps: 4.5 M, avg pps: 755, avg bpp: 748
```

バイトは IP ヘッダーから数えます。748 バイトのパケットが 37 個で 27,676 バイトです。エコー応答は別のフローです。送信元と
宛先が逆で、同じ観測点も通りません。応答は XR01 から GigabitEthernet1 で PE2 に入り、GigabitEthernet2 から出ていきます。

入力インターフェイスをキーにすると、同じ会話でも、2 つのインターフェイスから入ってきたものを分けて数えます。レコードは
インターフェイスの名前ではなく、SNMP の番号(ifIndex、2.5 節)を運びます。そのため、収集役は、番号を名前に直すのに SNMP か、
ルータが一緒に送る対応表を必要とします。

### 2.2 タイムアウト: レコードがキャッシュを出るとき

フローには、ルータから見える終わりがありません(TCP の FIN と RST は別)。ルータは、タイマーでフローの終わりを決め、
レコードをエクスポートします。

- **inactive タイムアウト**: このフローのパケットが N 秒来なければ、フローは終わったとみなします。Catalyst 8000V の既定は
  15 秒です。
- **active タイムアウト**: フローはまだ続いているが、エントリを作ってから N 秒たった。ルータはそこまでの分をエクスポート
  し、数え直します。既定は 1800 秒です。
- **キャッシュがいっぱい**: ルータは、場所を空けるために、エントリを早めに出します。

上の ping の列は、最後のパケットから 15 秒でキャッシュを出ました。

```console
PE2#show flow monitor FM-CUST cache format table
  Cache type:                               Normal (Platform cache)
  Cache size:                               200000
  Current entries:                               0
  High Watermark:                                1

  Flows added:                                   1
  Flows aged:                                    1
    - Inactive timeout    (    15 secs)          1

There are no cache entries to display.
```

active タイムアウトが効く場面: 2 時間続くバックアップは 1 つのフローです。既定の 1800 秒では、収集役が聞くのは 30 分に
1 回で、グラフは何も無いところに 30 分ぶんの塊が一度に出ます。

「長く続くフローは少なくとも 60 秒ごとに報告する」という
要件は、active タイムアウト 60 秒のことです。ルータは、このフローについて毎分レコードを送り、それぞれに前回からのバイトと
パケットを入れます(IPFIX はこのカウンタを octetDeltaCount、packetDeltaCount と呼びます)。8000V では、どちらのタイマーも
1〜604800 秒を取ります。

### 2.3 エクスポート: NetFlow v9 と IPFIX のテンプレート

NetFlow のバージョン 5 は、レコードの並びが 1 つに決まっていました。欄をレコードごとに選ぶ今は、並びを収集役に伝える
必要があります。NetFlow v9(RFC 3954)と IPFIX(RFC 7011)は、それを**テンプレート**で行います。

1. エクスポータはテンプレートを送ります。番号(テンプレート ID。256 以上)と、欄の並びとそれぞれの長さです。
2. その後のデータ レコードは、テンプレート ID を名乗ります。データ レコードはただのバイトの列で、収集役はテンプレートを
   使って切り分けます。
3. UDP では、テンプレートが届いた保証がないので、エクスポータは一定の間隔で送り直します(IOS XE の `template data
   timeout`)。ルータより後に起動した収集役や、テンプレートを取りこぼした収集役は、次のテンプレートが届くまでデータを
   読み解けません(RFC 7011 は、その間データ レコードを少しの間取っておいてよいとしています)。

結果の例(PE2。2.1 節で使ったレコードのテンプレート):

```console
PE2#show flow exporter FE-NMS templates
Flow Exporter FE-NMS:
Client: Flow Monitor FM-CUST
  Exporter Format: IPFIX (Version 10)
  Template ID    : 258
  Source ID      : 256
  Record Size    : 49
  Template layout
  _____________________________________________________________________________
  |                 Field                   |    ID | Ent.ID | Offset |  Size |
  -----------------------------------------------------------------------------
  | ipv4 source address                     |     8 |        |      0 |     4 |
  | ipv4 destination address                |    12 |        |      4 |     4 |
  | ip protocol                             |     4 |        |      8 |     1 |
  | transport source-port                   |     7 |        |      9 |     2 |
  | transport destination-port              |    11 |        |     11 |     2 |
  | interface input snmp                    |    10 |        |     13 |     4 |
  | counter bytes long                      |     1 |        |     17 |     8 |
  | counter packets long                    |     2 |        |     25 |     8 |
  | timestamp absolute first                |   152 |        |     33 |     8 |
  | timestamp absolute last                 |   153 |        |     41 |     8 |
  -----------------------------------------------------------------------------
```

1 行が 1 つの欄で、ID は IANA の情報要素の登録簿(RFC 7012)の番号です。8 は sourceIPv4Address、12 は
destinationIPv4Address、4 は protocolIdentifier、7 と 11 は送信元と宛先のポート、10 は ingressInterface(ifIndex)、
1 と 2 は octetDeltaCount と packetDeltaCount、152 と 153 は最初と最後のパケットの時刻(ミリ秒)です。

`long` はカウンタを
8 バイトにします。4 バイトのバイト数のカウンタは 4 GB で一周します。Source ID は観測ドメインで、レコードがルータのどの
部分から来たかを表します。

| | NetFlow v9 | IPFIX |
|---|---|---|
| 定めたところ | Cisco(RFC 3954。情報提供の文書) | IETF の標準(RFC 7011) |
| ヘッダーのバージョン | 9 | 10 |
| ヘッダーにほかに入るもの | レコード数、ルータの稼働時間、時刻、シーケンス番号(エクスポートのパケットを数える)、Source ID | メッセージの長さ、エクスポートの時刻、シーケンス番号(データ レコードを数える)、観測ドメイン ID |
| テンプレート/オプション テンプレートのセット ID | 0 / 1 | 2 / 3 |
| 欄の番号 | Cisco の一覧 | IANA の登録簿。1〜127 は v9 と同じ |
| ベンダー独自の欄 | 無し | 企業番号と組で持てる(`Ent.ID` の列) |
| 可変長の欄 | 無し | 有り(URL やアプリケーション名などの文字列) |
| トランスポートとポート | UDP。ポートは両端で合わせる(2055 がよく使われる) | SCTP(実装は必須)、UDP、TCP。ポート 4739(TLS か DTLS では 4740) |
| 時刻 | ふつうはルータの稼働時間からの相対(欄 22 と 21) | ふつうは絶対時刻(152 と 153) |

IOS XE では `export-protocol ipfix` か `export-protocol netflow-v9` で選び、書かなければ v9 です。`show flow exporter` は
IPFIX を `IPFIX (Version 10)` と表示します。

### 2.4 サンプリング

PE2 はすべてのパケットを見ています。プロバイダーのコアのルータは、毎秒数百ギガビットをハードウェアで転送します。パケット
ごとにキャッシュを引き、短いフローごとにレコードを送っていては、ラインカードも収集役も追いつきません。そこで、そうした
ルータは**サンプリング**します。N 個に 1 個のパケットだけを見て(通信の規則的な並びに数がだまされないよう、ランダムに
選ぶ)、収集役が数を N 倍します。

大きなフローの合計は平均として正しく出ますが、小さなフローはまるごと見落とすことがあります。容量の計画、量による課金、
攻撃の発見には足りますが、特定の 1 パケットが通ったことの証明には使えません。

IOS XR は、割合を `sampler-map`(`random 1 out-of N`)に書き、インターフェイスでモニタと一緒に指定します(3.2 節)。
IOS XE にも同じ考えがあります(`sampler`、`mode random 1 out-of N`、`ip flow monitor M sampler S input`)。

エクスポータは、
サンプリングの割合をオプションのデータとして収集役へ送れるので(IOS XR の `options sampler-table`)、収集役は N を知る
ことができます。

### 2.5 SNMP: マネージャ、エージェント、MIB

SNMP は 3 つの部分でできています。

- **マネージャ**: NMS(このラボの SRV01)。問い合わせ、知らせを待ち受けます。
- **エージェント**: 各機器(XR01)の上のプロセス。答え、知らせます。
- **MIB**(Management Information Base): エージェントに問い合わせられる項目の、取り決めの集まり。項目ごとに **OID**
  (オブジェクト識別子)があり、世界で 1 つの木の中の、数字の道筋です。1.3.6.1 は「internet」、1.3.6.1.2.1 はどの
  エージェントも持つ標準の集まり MIB-II、1.3.6.1.4.1.9 は Cisco 独自の枝です。

| オブジェクト | OID | 中身 |
|---|---|---|
| sysName | 1.3.6.1.2.1.1.5.0 | 機器の名前(`XR01`) |
| sysUpTime | 1.3.6.1.2.1.1.3.0 | エージェントが動き始めてからの時間(100 分の 1 秒単位) |
| ifDescr | 1.3.6.1.2.1.2.2.1.2.*ifIndex* | インターフェイスの名前。インターフェイスごとに 1 行(ifTable) |
| ifInOctets | 1.3.6.1.2.1.2.2.1.10.*ifIndex* | 受信したバイト数。32 ビット |
| ifHCInOctets | 1.3.6.1.2.1.31.1.1.1.6.*ifIndex* | 受信したバイト数。64 ビット(ifXTable) |

操作は次のとおりです。

| 操作 | 向き | すること |
|---|---|---|
| Get | マネージャ → エージェント、UDP 161 | 指定した OID を読む |
| GetNext | マネージャ → エージェント | 木の中の次の OID を読む。繰り返すと表をたどれる(`snmpwalk`) |
| GetBulk(v2c、v3) | マネージャ → エージェント | 多数の GetNext を 1 回の要求で |
| Set | マネージャ → エージェント | 書き込む(書き込みの権限が要る) |
| Response | エージェント → マネージャ | 上の操作への答え |
| Trap、Inform | エージェント → マネージャ、UDP 162 | 出来事を知らせる(2.8 節) |

結果の例(SRV01 から。2 つのオブジェクトの Get と、ifDescr のウォーク):

```console
$ snmpget -v2c -c PocRO 10.0.50.1 1.3.6.1.2.1.1.5.0 1.3.6.1.2.1.1.3.0
iso.3.6.1.2.1.1.5.0 = STRING: "XR01"
iso.3.6.1.2.1.1.3.0 = Timeticks: (2026) 0:00:20.26
$ snmpwalk -v2c -c PocRO 10.0.50.1 1.3.6.1.2.1.2.2.1.2 | head
iso.3.6.1.2.1.2.2.1.2.2 = STRING: "Null0"
iso.3.6.1.2.1.2.2.1.2.3 = STRING: "MgmtEth0/RP0/CPU0/0"
iso.3.6.1.2.1.2.2.1.2.6 = STRING: "GigabitEthernet0/0/0/0"
iso.3.6.1.2.1.2.2.1.2.7 = STRING: "GigabitEthernet0/0/0/1"
iso.3.6.1.2.1.2.2.1.2.8 = STRING: "Loopback0"
```

SRV01 には MIB のファイルを読み込ませていないので、道具は OID を数字(`iso.3.6.1…`)で表示します。読み込ませれば、
1 行目は `SNMPv2-MIB::sysName.0` と出ます。

ifDescr の各行の最後の数字が **ifIndex** で、エージェントがインターフェイスに
付けた番号です。名前から決まるものではなく、ルータごとに違います。このラボの XR01 では、GigabitEthernet0/0/0/2 が 6 です。
再起動で番号が振り直されることがあり、番号で持っているグラフが崩れます。`snmp-server ifindex persist` は番号を保ちます。

カウンタは、エージェントが動き始めてからの合計です。マネージャは 2 回読み、差をその間の時間で割ります。32 ビットの
ifInOctets は 4 GB で一周し、1 Gb/s ならおよそ 34 秒です。5 分ごとのポーリングなら、64 ビットの ifHCInOctets を使います。
64 ビットのカウンタには v2c か v3 が要ります。

### 2.6 SNMPv2c: コミュニティとアクセス リスト

バージョン 1 と 2c には、ユーザがありません。要求は**コミュニティ** ストリングを運び、エージェントはそのコミュニティを
知っていれば答えます。RO(読み取り専用)は読み取りだけ、RW は書き込みも許します。この文字列はすべてのパケットに平文で
入っているので、通信を見られる人なら誰でも使い回せます。

IOS XR では、コミュニティに付けた IPv4 のアクセス リストで、使ってよい送信元を絞ります。アクセス リストが許さない送信元
からの要求には、**何も答えません**。マネージャは、ただタイムアウトします。XR は、これを `show snmp` の
`Unknown community name` に数えます。コミュニティの間違いと同じ数え方なので、マネージャの側からは 2 つを見分けられません。

結果の例(XR01。アクセス リストが許さない送信元から、1 回の要求とその再送を受けた後):

```console
RP/0/RP0/CPU0:XR01#show snmp | include "Unknown community|Trap PDUs|pkts sent"
    2 Unknown community name
    0 Trap PDUs
             Number of pkts sent: 0
```

`show snmp group` は、コミュニティを 1 つのグループとして、v1 と v2c の 2 回並べ、読み取りと通知に既定のビュー
`v1default`(1.3.6.1 のすべて)を示します(3.4 節)。XR01 がそもそもどこで SNMP に答えるかは、別の話です。MPP の設定が無い
間は、有効にした管理のプロトコルはすべてのインターフェイスで受け付けられます(M2)。アクセス リストに加えて、MPP でも
絞ります。

### 2.7 SNMPv3: ユーザ、グループ、ビュー、エンジン ID

SNMPv3(RFC 3411〜3418)は、コミュニティを 2 つのモデルに置き換えます。

- **USM**(User-based Security Model、RFC 3414): ユーザが誰で、メッセージをどう守るか。ユーザは、認証のプロトコルと
  パスワード(ここでは SHA。どのメッセージも鍵付きのハッシュを持つので、偽物や書き換えられたメッセージは拒まれる)と、
  暗号化のプロトコルとパスワード(ここでは AES 128、RFC 3826。中身が暗号化される)を持ちます。セキュリティの段階は 3 つ
  です。**noAuthNoPriv**(ユーザ名だけ)、**authNoPriv**(認証あり)、**authPriv**(認証と暗号化)。IOS XR は `noauth`、
  `auth`、`priv` と書きます。
- **VACM**(View-based Access Control Model、RFC 3415): ユーザが何に触れてよいか。ユーザは**グループ**に属します。
  グループは、セキュリティの段階と、最大 3 つの**ビュー**(読み取り用、書き込み用、通知用)を持ちます。ビューは、OID の
  部分木の集まりで、それぞれ `included`(含める)か `excluded`(除く)です。

パスワードは、そのままでは使いません。エージェントは、パスワードを鍵に変え、さらに自分の**エンジン ID**(この SNMP の
エンジンを識別する番号)でその鍵を**ローカライズ**します(RFC 3414 の 2.6 節)。同じパスワードでも、ルータごとに鍵が
違うので、1 台のルータから鍵が漏れても、ほかのルータは開きません。

両端で同じ鍵を作るには、両端が、そのメッセージについて**権威を持つ**(authoritative)側のエンジン ID を知っている必要が
あります。Get や Set では、それはエージェントです。マネージャは最初のやり取りで XR01 のエンジン ID を知り、snmpget は
これを自分で行います。

**トラップ**では送り手が権威を持ち、事前のやり取りが無いので、受け手が XR01 のエンジン ID を前もって
知っていなければなりません。SRV01 のトラップの受け手が `createUser -e 0x<エンジン ID>` で設定されているのはそのためで、
ラボが XR01 のエンジン ID を `snmp-server engineID local` で固定しているのもそのためです。ID が変わると、受け手の鍵が
合わなくなります。

```console
RP/0/RP0/CPU0:XR01#show snmp engineid
SNMP engineID 00000009030000000aff0001
RP/0/RP0/CPU0:XR01#show running-config snmp-server
...
snmp-server user USR-V3 GRP-V3 v3 auth sha encrypted 1522040F253F3F2C796166 priv aes 128 encrypted 097C410A29171E045A5E57
...
```

ユーザは `clear` でパスワードを入れ、コミットすると running-config には `encrypted` で出ます。パスワードが違うと、
`snmpget: Authentication failure (incorrect password, community or key)` で拒まれます。コミュニティのアクセス リストは
v3 には効きません。SRV01 をアクセス リストから外すと、v2c は答えが無くなりましたが、v3 は sysName を読めました。

### 2.8 トラップとインフォーム

ポーリングでは、リンクが落ちたことは次のポーリング、つまり数分後に分かります。代わりに、エージェントは、何か起きたその
ときにマネージャへ**通知**を送れます。宛先は UDP の 162 番です。

- **トラップ**: 1 回送るだけで、受け取りの確認がありません。失われても誰も気づきません。
- **インフォーム**(v2c と v3): 受け手は Response で答え、エージェントは答えがあるまで(またはあきらめるまで)送り直します。
  v3 のインフォームでは受け手が権威を持つ側なので、エージェントが受け手のエンジン ID を知る必要があります。

通知は変数の並びです。SNMPv2 の形では、最初の 2 つが必ず sysUpTime.0 と、通知の名前である snmpTrapOID.0 です(RFC 3416)。
linkDown は 1.3.6.1.6.3.1.1.5.3、linkUp は 1.3.6.1.6.3.1.1.5.4 です(RFC 2863)。XR01 のトラップには、さらにインターフェイス
の ifIndex、ifDescr、ifType と、Cisco 独自の文字列(`down` か `up`)が入っていました。

結果の例(SRV01 のトラップのログ。トラップ 1 つが長い 1 行):

```console
2026-11-10 14:43:21 <UNKNOWN> [UDP: [10.0.50.1]:161->[10.0.50.10]:162]:
.1.3.6.1.2.1.1.3.0 = Timeticks: (283007) 0:47:10.07	.1.3.6.1.6.3.1.1.4.1.0 = OID: .1.3.6.1.6.3.1.1.5.3	.1.3.6.1.2.1.2.2.1.1.6 = INTEGER: 6	.1.3.6.1.2.1.2.2.1.2.6 = STRING: "GigabitEthernet0/0/0/2"	.1.3.6.1.2.1.2.2.1.3.6 = INTEGER: 6	.1.3.6.1.4.1.9.9.276.1.1.2.1.3.6 = STRING: "down"
2026-11-10 14:43:26 <UNKNOWN> [UDP: [10.0.50.1]:161->[10.0.50.10]:162]:
.1.3.6.1.2.1.1.3.0 = Timeticks: (283503) 0:47:15.03	.1.3.6.1.6.3.1.1.4.1.0 = OID: .1.3.6.1.6.3.1.1.5.4	.1.3.6.1.2.1.2.2.1.1.6 = INTEGER: 6	.1.3.6.1.2.1.2.2.1.2.6 = STRING: "GigabitEthernet0/0/0/2"	.1.3.6.1.2.1.2.2.1.3.6 = INTEGER: 6	.1.3.6.1.4.1.9.9.276.1.1.2.1.3.6 = STRING: "up"
```

どの出来事を通知にするかは `snmp-server traps …` で、誰に、どのバージョンで、どのユーザとして送るかは `snmp-server host` で
選びます。SNMPv3 では、さらにユーザのグループが通知を許している必要があります。

XR01 では、グループに**通知のビュー**
(notify)を持たせて初めてトラップが出ました。無いときは、`show snmp group` の `notifyview` が空で、`show snmp` の
Trap PDUs は 0 のままでした。コマンド リファレンスは、`snmp-server host` が通知のビューを自分で作るので設定しないように
と書いていますが、XR01 ではそうなりませんでした(リリースは補足に)。

### 2.9 押さえどころ

- フローは、1 つの観測点を 1 つの向きに通る、キーの欄が同じパケット。`match` がキー、`collect` が非キーの欄。ping の 1 列は
  1 フロー。
- レコードがキャッシュを出るのは、inactive タイムアウト(15 秒)、active タイムアウト(既定 1800 秒。「60 秒ごとに報告」は
  active 60)、キャッシュがいっぱいのとき。
- v9 と IPFIX は先にテンプレートを送り、収集役はそれが無いとデータを読めない。IPFIX はバージョン 10、IANA の欄の番号、
  UDP 4739。
- 速いルータは N 個に 1 個をサンプリングし、収集役が N 倍する。
- SNMP: マネージャが UDP 161 でエージェントの MIB をポーリングし、エージェントは UDP 162 へトラップとインフォームを送る。
- v2c: コミュニティは平文。アクセス リストが許さない送信元には答えない(`Unknown community name`)。
- v3: USM(認証 SHA、暗号化 AES、3 つの段階)と VACM(読み取り・書き込み・通知のビューを持つグループ)。鍵はエンジン ID で
  ローカライズされるので、トラップの受け手は送り手のエンジン ID を知っている必要がある。XR01 では、トラップにグループの
  通知のビューが要る。

## 3. 組む

### 3.1 IOS XE の Flexible NetFlow

Flexible NetFlow は、名前で互いを参照する 4 つの部分でできています。**レコード**(何をフローとし、何を数えるか)、
**エクスポータ**(レコードをどこへ、どの形式で送るか)、**モニタ**(レコードと 1 つ以上のエクスポータを結ぶキャッシュと、
そのタイムアウト)、そしてモニタを向き付きで付けるインターフェイスです。

例は、顧客 A がコアへ送る量を ToS ごとに数えます。キーはポートの代わりに ToS のバイトにし、PE2 のコア側の
GigabitEthernet1 の出力を見ます。図は、CE1 からの 37 個のエコー要求を、PE2 を通って SRV01 まで追います。図の番号に
カーソルを置くと(スマホでは押すと)、その部分の設定が出ます。

:::walk
legend: 紫は PE2 の中だけのもの。橙は PE2 が収集役へ送るもの。
rows:
  - {node: CE1, kind: host, say: ["~ping 10.255.0.1 source Loopback100 を 748 バイトで 37 発"]}
  - {wire: "[[IP 192.168.100.1 → 10.255.0.1 ICMP 8.0]] _× 37、ToS 0"}
  - panel: PE2
    sub: Catalyst 8000V
    items:
      - say: ["~Gi2(顧客 A)から入り、10.255.0.1 へのルートで Gi1 へ。NetFlow ではない"]
      - ref: 1
        head: "**Gi1 の出力** `ip flow monitor FM-CORE output`"
        say: ["Gi1 から出る各パケットをモニタに見せる。パケットはそのまま XR01 へ"]
      - ref: 2
        head: "**モニタ** `flow monitor FM-CORE`"
        say: ["レコードが決めるキーで、キャッシュを引く"]
      - ref: 3
        head: "**レコード** `flow record FR-CORE`"
        say: ["キー: ToS 0、ICMP、192.168.100.1 → 10.255.0.1、出力 Gi1"]
        match:
          - ["1 発目", false, "このキーのエントリは無い → 新しく作る"]
          - ["2〜37 発目", true, "同じキー → +1 パケット、+748 バイト"]
      - say: ["[[~ToS 0 · ICMP · 192.168.100.1 → 10.255.0.1 · Gi1]] [[~37 pkts · 27676 B]]", "_キャッシュのエントリ。最初と最後のパケットの時刻も持つ"]
      - ref: 2
        head: "**タイムアウト** `cache timeout inactive 10` / `active 300`"
        say: ["最後の ping から 10 秒でフローは終わり、エントリがキャッシュを出る"]
      - ref: 4
        head: "**エクスポータ** `flow exporter FE-V9`"
        say: ["NetFlow v9 で、Loopback0(10.255.0.2)から 10.0.50.10 の UDP 4739 へ"]
        then: ["→ 先にテンプレート(ID と欄の並び)、続いてデータ レコード"]
  - {wire: "[[=UDP 10.255.0.2 → 10.0.50.10:4739]] [[!v9 テンプレート]] [[!データ: 1 レコード]]"}
  - {node: SRV01, kind: host, say: ["nfcapd がテンプレートを覚えてレコードを解き、1 分ごとにファイルへ", "~`nfdump`: 1 フロー、37 パケット、27676 バイト"]}
  - aside: 代わりに Gi1 の入力にモニタを付けると
    say:
      - "~Gi1 の入力に見えるのは XR01 から戻るもの: [[IP 10.255.0.1 → 192.168.100.1 ICMP 0.0]]"
      - "~別のフローで、37 個のエコー要求は記録されない"
  - aside: "エクスポータを別のポートへ(`transport udp 2055`)"
    say:
      - "~nfcapd は UDP 4739 でしか待っていないので、レコードは失われる"
      - "~UDP に受け取りの確認は無い: `show flow exporter` の `Destination Port` と見比べる"
  - aside: "エクスポータに `source` が無いと"
    say:
      - "~レコードは出口のインターフェイスのアドレスから出る: 10.255.0.2 ではなく 10.0.50.2(Gi3)"
      - "~出口が変わると、収集役には別のエクスポータに見える"
:::

:::config fold PE2 — コアへ送る通信を ToS ごとに数え、NetFlow v9 でエクスポートする
flow record FR-CORE                           ## ③ 何をフローとし、何を数えるか
 match ipv4 tos                               ## キー: ToS のバイト(DSCP と ECN のビット)
 match ipv4 protocol                          ## キー: ICMP、TCP、UDP など
 match ipv4 source address                    ## キー
 match ipv4 destination address               ## キー
 match interface output                       ## キー: パケットが出ていくインターフェイス
 collect counter bytes long                   ## 非キー: バイト数。8 バイトのカウンタ
 collect counter packets long                 ## 非キー: パケット数。8 バイトのカウンタ
 collect timestamp absolute first             ## 非キー: 最初のパケットの時刻(稼働時間ではなく日時)
 collect timestamp absolute last              ## 非キー: 最後のパケットの時刻
!
flow exporter FE-V9                           ## ④ レコードの送り先
 destination 10.0.50.10                       ## SRV01
 source Loopback0                             ## 出口のインターフェイスにかかわらず 10.255.0.2 から送る
 transport udp 4739                           ## 収集役が待っているポート
 export-protocol netflow-v9                   ## 形式。IPFIX なら `ipfix`。書かなければ v9
!
flow monitor FM-CORE                          ## ② レコードとエクスポータを結ぶキャッシュ
 record FR-CORE
 exporter FE-V9                               ## エクスポータは複数書ける
 cache timeout active 300                     ## 続いているフローを 300 秒ごとに報告する
 cache timeout inactive 10                    ## 最後のパケットから 10 秒でフローは終わり
!
interface GigabitEthernet1                    ## ① XR01(コア)へ
 ip flow monitor FM-CORE output               ## ここから出ていくパケットを見る
:::

部分は、レコード、エクスポータ、モニタ、インターフェイスの順に作ります。どの部分も、その前の部分を名前で指すからです。
エクスポータの `template data timeout` は、テンプレートを送り直す間隔を決めます。IOS XE には、従来の 7 つのキーを持つ
`record netflow ipv4 original-input` のような、出来合いのレコードもあります。

### 3.2 IOS XR の NetFlow(参考)

**このラボの XR01(XRd)では、また XRv 9000 でも、NetFlow は使えません。** そこでは `flow` のコマンドは BGP FlowSpec を
設定するもので、`flow exporter-map` は拒まれます。このラボのフローの課題が PE2 にあるのは、そのためです。

結果の例(XR01):

```console
RP/0/RP0/CPU0:XR01(config)#flow ?
  address-family  Address Family Identifier Type (IPv4/IPv6)
  apply-group     Apply configuration from a group
  exclude-group   Exclude apply-group configuration from a group
  local-install   Local installation of FlowSpec policy
  vrf             VRF configuration
  <cr>
RP/0/RP0/CPU0:XR01(config)#flow exporter-map FEM
                                  ^
% Invalid input detected at '^' marker.
```

ASR 9000 のように NetFlow をハードウェアに持つルータでは、IOS XR は 3 つのマップとインターフェイスの 1 行で組みます。
下の設定は、文書にある形を、この盤面のアドレスで書いたものです。読んで比べるためのもので、ラボでは試せません。

:::config ASR 9000 の IOS XR — コアの線で 1000 個に 1 個をサンプリングし、IPFIX でエクスポートする(XRd では不可)
flow exporter-map FEM-NMS                     ## レコードの送り先
 version ipfix                                ## または `version v9`
  template data timeout 300                   ## テンプレートを 300 秒ごとに送り直す
  options interface-table timeout 300         ## ifIndex とインターフェイス名の対応表も送る
  options sampler-table timeout 300           ## サンプリングの割合も送る
 !
 transport udp 4739
 source Loopback0                             ## 必須。無いとエクスポータは無効のまま
 destination 10.0.50.10
!
flow monitor-map FMM-CORE                     ## キャッシュ
 record ipv4                                  ## キーを 1 つずつ組むのではなく、決まった形のレコード
 exporter FEM-NMS                             ## エクスポータは 8 つまで
 cache entries 65535                          ## 既定の大きさ
 cache timeout active 300                     ## 既定は active 1800 秒、inactive 15 秒
 cache timeout inactive 15
!
sampler-map SM-1K                             ## サンプリングの割合
 random 1 out-of 1000                         ## 1000 個に 1 個をランダムに
!
interface GigabitEthernet0/0/0/0
 flow ipv4 monitor FMM-CORE sampler SM-1K ingress   ## モニタ、サンプラー、向きを 1 行で
:::

IOS XE との違いは、部分がマップであること、レコードを決まった種類から選ぶこと、インターフェイスの行がサンプラーを指し
(コマンド リファレンスでは必須の形)、`ingress` か `egress` と書くことです。

確かめるには `show flow monitor FMM-CORE cache
location 0/0/CPU0`(キャッシュはラインカードごと)、`show flow exporter-map FEM-NMS`、`show sampler-map SM-1K` を使います。
ガイドは、管理インターフェイスからのエクスポートは避けるようにとも書いています。

### 3.3 IOS XR の SNMP

最初の `snmp-server` のコマンドで、SNMPv3 も含めてエージェントが動き始めます。v2c なら、コミュニティとそのアクセス リスト
だけで足ります。例は、10.0.50.20 にある NMS チームの運用ステーション向けです(このラボには作っていません)。

:::config fold XR01 — SNMPv2c の読み取りを運用ステーションだけに許す
ipv4 access-list OPS-HOSTS                    ## コミュニティを使ってよい送信元
 10 permit ipv4 host 10.0.50.20 any           ## 運用ステーション
!
snmp-server community OPS-RO RO IPv4 OPS-HOSTS   ## 読み取り専用。OPS-HOSTS が許す送信元にだけ答える
:::

SNMPv3 のトラップでは、XR01 の設定の 6 つの部分と、受け手の 1 行が、1 つの出来事に順に効きます。図は、XR01 からステーション
までの linkDown を追います。番号にカーソルを置くと(スマホでは押すと)、その行の設定が出ます。

:::walk
legend: 線の上はトラップ。橙は SNMPv3 が加えるもの。XR01 の段をすべて通らないと、何も送られない。
rows:
  - panel: XR01
    sub: エージェント
    items:
      - say: ["~GigabitEthernet0/0/0/2(CE1 への予備の線)が落ちる"]
      - ref: 1
        head: "**通知にする出来事か** `snmp-server traps snmp linkdown`"
        say: ["通知を作る: linkDown(.1.3.6.1.6.3.1.1.5.3)。ifIndex 6、ifDescr、ifType 付き"]
      - ref: 2
        head: "**誰に、どう送るか** `snmp-server host 10.0.50.20 traps version 3 priv ops-mon`"
        say: ["10.0.50.20 の UDP 162 へトラップで。SNMPv3 の authPriv、ユーザ ops-mon として"]
      - ref: 3
        head: "**ユーザ** `snmp-server user ops-mon OPS-V3 v3 auth sha … priv aes 128 …`"
        say: ["2 つのパスワードを持ち、グループ OPS-V3 に属する"]
      - ref: 4
        head: "**グループ** `snmp-server group OPS-V3 v3 priv …`"
        match:
          - ["v3 priv", true, "host の行は priv を求める: 段階を満たす"]
          - ["notify OPS-ALL", true, "このグループは通知を受け取れる"]
      - ref: 5
        head: "**通知のビュー** `snmp-server view OPS-ALL 1.3.6.1 included`"
        match:
          - ["linkDown, ifIndex, ifDescr, ifType", true, "すべて 1.3.6.1 の下 → 送ってよい"]
      - ref: 6
        head: "**鍵** `snmp-server engineID local 00:00:00:09:03:00:00:00:0a:ff:00:01`"
        say: ["パスワードを、このエンジン ID でローカライズした鍵にする", "トラップに署名(SHA)し、暗号化(AES)する"]
  - {wire: "[[=10.0.50.1 → 10.0.50.20:162]] [[!エンジン ID · ユーザ]] [[!署名 · 暗号化]]"}
  - panel: OPS
    sub: 10.0.50.20、snmptrapd
    items:
      - ref: 7
        head: "**送り手を知っている** `createUser -e 0x00000009030000000aff0001 ops-mon …`"
        say: ["同じパスワードと XR01 のエンジン ID から、同じ鍵を作る"]
        then: ["→ 署名を確かめ、復号し、トラップをログに書く"]
  - aside: "④に `notify OPS-ALL` が無いと"
    say:
      - "~`show snmp group` の notifyview は空、`show snmp` の Trap PDUs は 0。XR01 から何も出ない"
  - aside: XR01 のエンジン ID を知らない受け手
    say:
      - "~XR01 の鍵を作れない: トラップを確かめることも復号することもできない"
  - aside: OPS-HOSTS が許さない SRV01 から v2c でポーリングすると
    say:
      - "[[UDP 10.0.50.10 → 10.0.50.1:161 community OPS-RO]] ~答えが無い"
      - "~XR01 は `show snmp` の `Unknown community name` に数える"
:::

:::config fold XR01 — SNMPv3 で system グループを読ませ、リンクのトラップを authPriv で送る
snmp-server engineID local 00:00:00:09:03:00:00:00:0a:ff:00:01   ## ⑥ エンジン ID(ラボでは固定。変えない)
snmp-server view OPS-SYS 1.3.6.1.2.1.1 included   ## system グループだけのビュー(sysName、sysUpTime など)
snmp-server view OPS-ALL 1.3.6.1 included     ## ⑤ internet の下すべてのビュー
snmp-server group OPS-V3 v3 priv read OPS-SYS notify OPS-ALL   ## ④ authPriv。system グループを読み、通知を受け取れる
snmp-server user ops-mon OPS-V3 v3 auth sha clear OpsAuth-26 priv aes 128 clear OpsPriv-26   ## ③ コミット後は `encrypted` で出る
snmp-server host 10.0.50.20 traps version 3 priv ops-mon   ## ② ステーションへ、ops-mon として authPriv でトラップを送る
snmp-server traps snmp linkup                 ## ① 通知にする出来事
snmp-server traps snmp linkdown               ## ①
snmp-server ifindex persist                   ## 再起動をまたいでインターフェイスの番号を保つ
:::

:::config OPS(10.0.50.20)— ops-mon のトラップの受け手(snmptrapd の設定ファイル)
createUser -e 0x00000009030000000aff0001 ops-mon SHA OpsAuth-26 AES OpsPriv-26   ## ⑦ XR01 のエンジン ID 付きのユーザ(0x を付け、コロンは無し)
authUser log ops-mon priv                     ## ops-mon のトラップを、authPriv のものだけ記録する
:::

このラボの SRV01 のトラップの受け手(snmptrapd-lab)も、ユーザ nms-trap について同じ形で設定してあります。インフォームに
するには、host の行の `traps` を `informs` にします。IOS XR 25.4.x から、暗号化に DES と 3DES は使えません。AES を使います。

### 3.4 確かめ方

| 見たいこと | コマンド |
|---|---|
| インターフェイスに付いたモニタとその向き | `show flow interface <IF>` |
| モニタのレコード、エクスポータ、タイムアウト | `show flow monitor <名前>` |
| 今キャッシュにあるフローと、フローが出た理由 | `show flow monitor <名前> cache format table` |
| レコードをどこへ、どう送るか | `show flow exporter <名前>` |
| 収集役が受け取る欄 | `show flow exporter <名前> templates`(2.3 節) |
| 送った数 | `show flow exporter <名前> statistics` |
| 収集役に届いたもの | SRV01 で `nfdump -R /var/cache/nfdump/lab -o extended '<条件>'` |
| エージェントの数(拒んだコミュニティ、送ったトラップ) | `show snmp` |
| グループとビュー、ユーザ、トラップの宛先、エンジン ID | `show snmp group`・`show snmp user`・`show snmp host`・`show snmp engineid` |
| NMS からの読み取り | SRV01 で `snmpget`・`snmpwalk` |
| トラップの受け手に届いたもの | SRV01 の `/var/log/snmptrapd-lab.log` |

結果の例(PE2。GigabitEthernet2 の入力に付け、IPFIX でエクスポートするモニタ):

```console
PE2#show flow interface GigabitEthernet2
Interface GigabitEthernet2
  FNF:  monitor:          FM-CUST
        direction:        Input
        traffic(ip):      on

PE2#show flow monitor
Flow Monitor FM-CUST:
  Description:       User defined
  Flow Record:       FR-CUST
  Flow Exporter:     FE-NMS
  Cache:
    Type:                 normal (Platform cache)
    Status:               allocated
    Size:                 200000 entries
    Inactive Timeout:     15 secs
    Active Timeout:       60 secs

    Trans end aging:   off

PE2#show flow exporter FE-NMS
Flow Exporter FE-NMS:
  Description:              User defined
  Export protocol:          IPFIX (Version 10)
  Transport Configuration:
    Destination type:       IP
    Destination IP address: 10.0.50.10
    Source IP address:      10.255.0.2
    Source Interface:       Loopback0
    Transport Protocol:     UDP
    Destination Port:       4739
    Source Port:            54542
    DSCP:                   0x0
    TTL:                    255
    Output Features:        Used

PE2#show flow exporter FE-NMS statistics
Flow Exporter FE-NMS:
  Packet send statistics (last cleared 00:01:01 ago):
    Successfully sent:         2                     (104 bytes)

  Client send statistics:
    Client: Flow Monitor FM-CUST
      Records added:           1
        - sent:                1
      Bytes added:             49
        - sent:                49
```

`Records added: 1` は 2.1 節の ping の列で、1 フローです。49 バイトは、テンプレートのレコードの大きさです。SRV01 の nfcapd は
1 分ごとに新しいファイルを始めるので、フローが `nfdump` に出るまで、通信から最大で 1〜2 分かかります(2.1 節の例では
50 秒以内に出ました)。

結果の例(XR01 の SNMP の側。課題 M13-6 の後に GigabitEthernet0/0/0/2 を 1 回落として戻した):

```console
RP/0/RP0/CPU0:XR01#show snmp host
Notification host: 10.0.50.10 udp-port: 162  type: trap
user: nms-trap      security model: v3 priv
RP/0/RP0/CPU0:XR01#show snmp user
  User Name: nms-trap
  EngineId: localSnmpID
  storage-type: nonvolatile        active
RP/0/RP0/CPU0:XR01#show snmp | include "Trap PDUs|pkts sent|dropped"
    2 Trap PDUs
             Number of pkts sent: 2
          Number of pkts dropped: 0
    Number of Informs dropped: 0 
```

`show snmp host` は、XR01 がトラップの宛先ごとに実際に使うセキュリティの段階を示し、`Trap PDUs` は送ったトラップを数え
ます。ここでは linkDown と linkUp が 1 つずつです。

結果の例(コミュニティ `PocRO` と、通知のビューの無い v3 のグループ `GRP-V3` を持つルータ):

```console
RP/0/RP0/CPU0:XR01#show snmp group
groupname: PocRO                         security model:snmpv1
readview : v1default                     writeview: 
notifyview: v1default
row status: active

groupname: PocRO                         security model:snmpv2c
readview : v1default                     writeview: 
notifyview: v1default
row status: active

groupname: GRP-V3                        security model:usm
readview : VIEW-ALL                      writeview: 
notifyview: 
row status: active
```

コミュニティは `v1default` で 2 回(v1 と v2c)出ます。v3 のグループの `notifyview` は空で、このグループでは XR01 は v3 の
トラップを送りません(2.8 節)。

:::try
コミュニティのアクセス リストが SNMPv3 に触れないことを確かめます。課題 M13-6 を終えた後に行い、最後に元に戻します。

1. SRV01 で `snmpget -v2c -c NMS-RO 10.0.50.1 1.3.6.1.2.1.1.5.0` と、課題の確かめ方にある SNMPv3 の `snmpget`(ユーザ
   nms-trap)を実行します。どちらも `XR01` を返します。
2. XR01 で、`NMS-ONLY` の SRV01 を許す行を消してコミットします。2 つのコマンドをもう一度実行し、
   `show snmp | include "Unknown community"` を見ます。
3. 行を戻してコミットします。

結果の例: SRV01 をアクセス リストから外すと、v2c の要求は `Timeout: No Response from 10.0.50.1.` で終わり、v3 の要求は
`STRING: "XR01"` を返し続けました。`Unknown community name` は 2 増えました(要求とその再送)。
:::

### 3.5 落とし穴

- **`show snmp host` を running-config と見比べる。** このリリースでは、既にある host の行を `auth` から `priv` に変えると
  (`priv` の行を上から入れても、古い行を消して新しい行を入れるのを 1 回のコミットで行っても)、running-config は変わるのに
  `show snmp host` は `v3 auth` のままで、authPriv しか受けない受け手にトラップは届きませんでした。行を消してコミットし、
  それから入れてコミットします。

```console
RP/0/RP0/CPU0:XR01#show running-config snmp-server host
snmp-server host 10.0.50.10 traps version 3 priv nms-trap

RP/0/RP0/CPU0:XR01#show snmp host
Notification host: 10.0.50.10 udp-port: 162  type: trap
user: nms-trap      security model: v3 auth
```

- **host の行の段階は、グループの段階と組になる。** host の行が `auth` でグループが `priv` のとき、XR01 は何も送りません
  でした(`Trap PDUs` は 0 のまま)。
- **コミュニティのアクセス リストは SNMPv3 を守らない。** v3 のユーザはこれで絞られません。XR01 がそもそもどの
  インターフェイスで答えるかを絞るには、MPP(M2)を使います。
- **試験の出来事は物理インターフェイスで起こす。** ここで linkDown と linkUp のトラップを確かめたのは、ラボの確認と同じく
  GigabitEthernet のインターフェイスです。ループバックは確かな試験になりません(補足を参照)。
- **受け手は送り手のエンジン ID を知っている必要がある。** XR01 のエンジン ID が変わると、受け手の鍵が合わなくなります。
  ラボでは `snmp-server engineID local` に触れません。
- **DES ではなく AES。** IOS XR 25.4.x から、SNMPv3 の暗号化に DES と 3DES は使えません。
- **収集役に届くまで待つ。** inactive タイムアウトの 15 秒と nfcapd の 1 分ごとのファイルで、フローが見えるまで最大で
  1〜2 分かかります。先にルータのキャッシュと `show flow exporter … statistics` を見ます。
- **IOS XE のタイムアウト。** 8000V のモニタは、`cache timeout active` と `inactive` に 1〜604800 秒を取ります。
  `export-protocol` を書かないと、エクスポータは IPFIX ではなく NetFlow v9 を送ります。
- **使用中のレコードはロックされる。** モニタが使っているレコードは変えられず(`% Flow Record: Failed to field add: Object
  is in use`)、モニタのレコードは新しい名前を上から入れても置き換わりません
  (`% Flow Monitor: Failed to set record: Already there is an existing record configured`)。先にモニタから `record` を
  外します。エクスポータが使用中の間は、`export-protocol` も変えられません。

## 実践

ラボ **XRT-15** で課題 M13-5 と M13-6 に取り組みます。

<p class="tolab"><a href="/_learn?id=XRT-15">ワークスペースでラボ XRT-15 を開く</a> — <a href="e5-m13-practice-3.html">課題 M13-5、M13-6</a></p>

:::note
このページの出力は、XRT-15 の盤面(XR01 は IOS XRd 26.1.1、PE2 は Catalyst 8000V の IOS XE 17.15.1a)で取得しました。
ただし、次のものはこの単元の PoC の盤面(同じアドレス。XRv 9000 26.1.1 の XR01 と XRd 26.1.1 の XR01 で、両者の動きは
同じ)によるものです。コミュニティ `PocRO` での `snmpget` と `snmpwalk`、`show snmp group`、`USR-V3` の出る
`show running-config snmp-server`、パスワード違いとアクセス リストの試験、XR01 の `flow ?`。

次の項目は実測によります。ping の 1 列が 1 フローになること、それが 15 秒でキャッシュを出て 50 秒で nfdump に出たこと。
XRd と XRv 9000 の 26.1.1 に NetFlow が無いこと(XRd には `xr-netflow-stubs` のパッケージしか無く、`flow` は FlowSpec)。
コミュニティのアクセス リスト(答えない、`Unknown community name`、v3 には効かない)。通知のビュー。host の行が `v3 auth` の
ままになること(XRd 26.1.1。文書に記述なし)。host の行が `auth` でグループが `priv` だと何も送られないこと。

使用中のレコードの
ロックは IOL の IOS XE 17.15 で測りました。IOL ではモニタに `cache timeout` がそもそも無く、レコードに稼働時間からの時刻しか
入れられません(そのとき nfdump の日付は 1970-01-01 になります)。

機器で確かめきれていない点が 2 つあります。ループバックの shutdown ではトラップが出ませんでしたが、そのときグループには
通知のビューが無かったので、この試験では何も決まりません。送り手のエンジン ID を知らない受け手は、単独では試していません。
そこは RFC 3414 によっています。

文書と機器が食い違う点: System Management のコマンド リファレンスは、`snmp-server host` がそのユーザの通知のビューを作るので
グループには設定しないように、と書いています。XRd と XRv 9000 の 26.1.1 では、通知のビューの無いグループは `notifyview` が
空で v3 のトラップを送らず、`notify` を足すと送りました。

NCS 5500 のガイドは、SNMP は既定で管理インターフェイスでだけ答える
と書いていますが、XRd と XRv 9000 の 26.1.1 では、MPP の設定なしで XR01 が NMS の区画で答えました(M2 の説明のとおり)。

出典: RFC 3954(NetFlow v9)、RFC 7011(3.1・3.3.2・3.4.1・9.3・10.1 節)、RFC 7012 と IANA の IPFIX の情報要素の登録簿、
RFC 3411〜3418(3414 は USM、3415 は VACM、3416 は PDU、3418 は SNMPv2-MIB)、RFC 3826(AES)、RFC 1901(v2c)、RFC 2863
(IF-MIB、linkDown と linkUp)。ASR 9000 の Netflow Configuration Guide と Command Reference(IOS XR 7.9.x と 25.x。
exporter-map、monitor-map、sampler-map、既定値、必須の送信元インターフェイス)、Cisco IOS XE 17.x の Network Services
Configuration Guide(Flexible NetFlow、IPFIX のエクスポート)と Catalyst 9500 の IOS XE 17.17 のガイドの Flexible NetFlow の章
(既定のエクスポートの形式)、NCS 5500 の System Management Configuration Guide(IOS XR 26.x の Implementing SNMP。最初の
コマンドで v3 も有効、25.4.x からの DES と 3DES、`ifindex persist`)と NCS 5500 の System Management Command Reference
(`snmp-server group`、`host`、`engineid`)。いずれも 2026 年 11 月に確認。
:::
