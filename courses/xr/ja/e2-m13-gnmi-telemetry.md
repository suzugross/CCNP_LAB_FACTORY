# M13 — 状態を流す: gNMI・テレメトリ・TLS

前のページでは、データ モデルを通してルータの設定を変えました。このページは逆向きで、ルータの状態を、流れとして外へ
出します。ルータが自分のカウンタを決まった間隔で読んで収集役へ送り出すか、収集役が gNMI でそれを購読します。どちらも
gRPC の上で動き、TLS で守ります。ブループリントの 5.7(gRPC と gNMI、TCP、TLS と相互 TLS の証明書を使ったダイヤルインと
ダイヤルアウトの設定)にあたります。盤面は XRT-15 で、このページで使う部分は 2 節の初めに描きます。

## 1. 何が嬉しいのか

### 1.1 困りごと: 5 分ごとの問い合わせでは、20 秒の混雑が見えない

NMS チームは、XR01 のインターフェイスがどれだけ混んでいるかを知りたいと考えています。平均で 30% しか流れていない回線でも、
20 秒ずつ満杯になることがあり、顧客のパケットが落ちるのはその 20 秒の間です。そうした瞬間の混雑を見るには、全部のルータの
全部のインターフェイスで、10 秒ほどおきにカウンタを読む必要があります。

それだけの頻度で、尋ねて読むのは重い作業です。1 回読むごとに要求と応答が往復し、ルータは値を 1 つずつ引き、NMS は
ルータごとにタイマーを回し続けます。ルータが数百台あれば、NMS は尋ねることに追われ、ルータは答えることに CPU を使います。

### 1.2 それ以前の手: SNMP の問い合わせと CLI の読み取り

- **SNMP の問い合わせ**(ポーリング): NMS がルータに MIB のオブジェクト(インターフェイスごとの入出力のオクテット数など)を
  GET や GETBULK で尋ねます。間隔は 5 分がふつうです。数百のインターフェイスの表をたどるには、何往復もかかります。値には
  読んだ時刻が付かず、NMS が応答を受けた時刻を付けます。SNMP そのものは「フローを数え、問い合わせる」のページで扱います。
- **CLI の読み取り**(スクレイピング): スクリプトが SSH でログインし、`show interfaces` を実行して、文字の中から数字を
  切り出します。その文字は人が読むためのものです。リリースや機種で変わり、スクリプトは黙って壊れます。

どちらも外から尋ねる方式で、5 分ごとに尋ねれば 5 分の平均しか得られません。ほかの時間は空いている回線が 20 秒だけ 100% に
なっても、約 7% と見えます。

### 1.3 流す、という答え

- **尋ねる代わりに送る**: ルータが、決まった間隔で(または値が変わったときに)自分のカウンタを読み、張ったままの接続で
  送ります。収集役は受け取るだけです。
- **データ モデルで名前を付ける**: 何を送るかは YANG のパスで指定します。NETCONF と同じモデルです(前のページ)。値は、
  名前、キー(どのインターフェイスか)、読んだ時刻と一緒に届きます。
- **線の上では小さく**: データは 2 進の形(GPB、Google Protocol Buffers)に符号化され、gRPC で運ばれます。全インターフェイス
  の 1 回分の採取が、1 つのメッセージで届きます。
- **守られている**: TLS が接続を暗号化し、両端が相手の証明書を確かめられます。

Cisco はこれをモデル駆動テレメトリ(MDT)と呼びます。始め方は 2 つあります。XR01 が収集役へ接続する(ダイヤルアウト)か、
収集役が XR01 へ接続して gNMI で購読する(ダイヤルイン)かです。2.3 節で比べます。

## 2. 仕組み: 1 つのカウンタを XR01 から収集役まで

XRT-15 では、XR01 と SRV01(NMS)が NMS の区画 10.0.50.0/24 を共有します。SRV01 では、テレメトリの収集役 telegraf
(TCP 57500 で待ち受け、TLS の gRPC だけを受け付ける)と、gNMI のクライアント gnmic が動いています。XR01 の gRPC の
サーバは、設定すると TCP 57400 で待ち受けます。

:::topo
nodes:
  PE2: {at: [0, 0], label: "PE2"}
  XR01: {at: [2.6, 0], label: "XR01 (gRPC 57400)"}
  SW1: {at: [1.3, 1.2], kind: sw, label: "SW1"}
  SRV01: {at: [1.3, 2.4], kind: host, label: "SRV01 (telegraf 57500, gnmic)"}
links:
  - [PE2, XR01, "CORE 10.0.12.0/24"]
  - {a: XR01, b: SW1, la: "Gi0/0/0/1 .1"}
  - {a: PE2, b: SW1, la: "Gi3 .2"}
  - {a: SW1, b: SRV01, lb: "ens3 .10"}
frames:
  - {label: "NMS の区画 10.0.50.0/24", nodes: [SW1, SRV01]}
:::

### 2.1 gRPC と gNMI

**gRPC** は、別の機械の上の関数を呼び出すための仕組み(リモート プロシージャ コール)で、Google が作りました。HTTP/2 の
上で動きます。1 本の TCP の接続で、たくさんの呼び出しを別々のストリームとして同時に運び、どちらの側も 1 本のストリームで
好きなだけ送り続けられます。終わりのない採取の流れを送れるのは、このためです。メッセージは protocol buffers(protobuf)
で決めます。メッセージの形を `.proto` のファイルに書き、小さな 2 進の形で送ります。

**gNMI**(gRPC Network Management Interface)は、OpenConfig がネットワーク機器の管理のために決めた、gRPC のサービスです。
呼び出し(RPC)は 4 つです。

| RPC | すること |
|---|---|
| Capabilities | 機器が、対応するモデルとエンコードを知らせる |
| Get | パスの下のデータを、その時点の写しとして読む |
| Set | 設定を変える(更新・置き換え・削除) |
| Subscribe | パスの下のデータを、今もこの先も送るよう頼む(2.2 節) |

gNMI のパスは、YANG の木の中の場所を 1 段ずつ指し、リストのキーを角かっこに書きます。例えば
`/interfaces/interface[name=Loopback0]/state` です。パスがどの木に属するかを、**オリジン**(origin)と呼びます。オリジンが
無ければ OpenConfig だと、gNMI の仕様は決めています。IOS XR 独自のモデルは、`Cisco-IOS-XR-shellutil-oper:system-time/uptime`
のように、先頭にモジュールの名前を付けて指します。XR は、応答のパスにオリジンを書き入れます(`openconfig:/…`、
`Cisco-IOS-XR-shellutil-oper:/…`)。

gNMI のメッセージの中の値は、要求が指定した形で符号化されます。IOS XR 26.1.1 は、Capabilities で **JSON_IETF**(YANG の
データの規則で書く JSON。RFC 7951)だけを知らせ、gnmic の既定の素の JSON を拒みます。Get は
`unsupported get-request encoding: JSON` で失敗します。gnmic には `-e json_ietf` を付けます。

```console
# SRV01 で(TLS の指定はここでは省く。2.5 節で扱う)
$ gnmic -a 10.0.50.1:57400 -u <user> -p <password> -e json_ietf … capabilities
gNMI version: 0.10.0
supported models:
  - Cisco-IOS-XR-um-hw-module-shut-cfg, Cisco Systems, Inc., 2022-03-08
  - Cisco-IOS-XR-sysmgr-oper, Cisco Systems, Inc., 2021-04-29
...
supported encodings:
  - JSON_IETF
$ gnmic -a 10.0.50.1:57400 -u <user> -p <password> -e json_ietf … get --path '/interfaces/interface[name=Loopback0]/state'
...
        "Path": "openconfig:/interfaces/interface[name=Loopback0]/state",
        "values": {
          "interfaces/interface/state": {
            "admin-status": "UP",
            "counters": {
              "carrier-transitions": "1"
            },
...
            "name": "Loopback0",
            "oper-status": "UP",
            "type": "iana-if-type:softwareLoopback"
$ gnmic -a 10.0.50.1:57400 -u <user> -p <password> -e json_ietf … get --path Cisco-IOS-XR-shellutil-oper:system-time/uptime
...
        "Path": "Cisco-IOS-XR-shellutil-oper:/system-time/uptime",
        "values": {
          "system-time/uptime": {
            "host-name": "XR01",
            "uptime": 824
```

Set は、NETCONF と同じように設定を変えます。gNMI で入れた変更を、XR はコミット履歴に Line `ems`(gRPC を受け持つ
プロセス)、Client `YANG Frame` として残します。NETCONF の変更なら Line は `netconf` です。

```console
RP/0/RP0/CPU0:XR01#show configuration commit list 4
SNo. Label/ID              User      Line                Client      Time Stamp
~~~~ ~~~~~~~~              ~~~~      ~~~~                ~~~~~~      ~~~~~~~~~~
1    1000000024            SUZUKI    ems                 YANG Frame  Tue Nov 10 13:41:00 2026
2    1000000023            SUZUKI    vty0:node0_RP0_CPU  CLI         Tue Nov 10 13:40:37 2026
...
```

### 2.2 Subscribe: STREAM・ONCE・POLL

Subscribe の要求は、パスを並べ、それをどう受け取りたいかを伝えます。要求全体のモードは、次の 3 つのどれかです。

| モード | 起きること |
|---|---|
| STREAM | 呼び出しが開いたままになり、機器が送り続ける。パスごとにサブモードを持つ(下記) |
| ONCE | 機器が今の値を 1 回送り、`sync_response` で終わりを示して、呼び出しを閉じる |
| POLL | 呼び出しが開いたままになり、クライアントが poll のメッセージを送るたびに、機器が今の値を送る |

STREAM では、パスごとのサブモードで、いつ値を送るかが決まります。

- **SAMPLE**: 採取の間隔ごとに、値が変わっていてもいなくても送ります。いつも変わり続けるカウンタに向きます。
- **ON_CHANGE**: 最初に全部の値を 1 回送り、その後は値が変わったときだけ送ります。インターフェイスの oper-status のように、
  めったに変わらない状態に向きます。Telemetry のガイドは、状態の葉(リーフ)に限るとしています。
- **TARGET_DEFINED**: 葉ごとに SAMPLE か ON_CHANGE かを、機器が選びます。

STREAM は、最初に全部の値を 1 回送り、続けて `sync_response` を送ります。これで、クライアントは完全な写しを持ったと
分かります。その後は、採取か変化の分だけが続きます。

XR01 では、OpenConfig のパスで、ONCE、STREAM の SAMPLE(10 秒ごと)、STREAM の ON_CHANGE の Subscribe が動きました。
次は Loopback0 のカウンタを ONCE で受けた例です(ループバックには、そこにカウンタが 1 つしかありません)。

```console
$ gnmic -a 10.0.50.1:57400 -u <user> -p <password> -e json_ietf … subscribe --path '/interfaces/interface[name=Loopback0]/state/counters' --mode once
{
  "source": "10.0.50.1:57400",
  "subscription-name": "default-1794316110",
  "timestamp": 1794316112062859674,
  "time": "2026-11-10T13:08:32.062859674Z",
  "prefix": "openconfig:/",
  "updates": [
    {
      "Path": "interfaces/interface[name=Loopback0]/state",
      "values": {
        "interfaces/interface/state": {
          "counters": {
            "carrier-transitions": "1"
          }
        }
      }
    }
  ]
}
{
  "sync-response": true
}
```

ルータに設定するテレメトリも、同じ選択を 1 つの数で表します。`sample-interval` をミリ秒で書けば採取、0 にすれば
イベント駆動(値が変わったときに送る)です。

### 2.3 ダイヤルインとダイヤルアウト

違いは、どちらが接続を開くかです。

| | ダイヤルイン | ダイヤルアウト |
|---|---|---|
| 接続する側 | 収集役が、XR01 の gRPC のサーバ(57400)へ | XR01 が、収集役(XRT-15 では 57500)へ |
| 何を送るかを決める側 | 収集役の要求(gNMI の Subscribe: パス・モード・間隔) | XR01 の設定(センサー グループ・サブスクリプション・宛先グループ) |
| 運び方 | gRPC だけ | gRPC・TCP・UDP |
| XR01 に要るもの | `grpc` | `telemetry model-driven`、TLS なら CA のファイル |
| 切れた後 | 収集役が接続し直し、購読し直す | XR01 が自分で試し続ける |
| ファイアウォールで通す向き | 収集役 → ルータ | ルータ → 収集役 |

**ダイヤルイン。** 収集役がルータへ接続して頼みます。gNMI の Subscribe はダイヤルインです。gnmic が要求の中でパスを
指定するので、XR01 には gRPC のサーバのほかに設定が要りません。IOS XR 独自のテレメトリも、ダイヤルインで動かせます。
宛先グループを持たないサブスクリプションをルータに設定しておくと、gRPC のサーバへ接続してきた収集役がそれを受け取ります。

**ダイヤルアウト。** ルータが収集役へ接続し、設定に書いたものを送ります。収集役は待ち受けるだけです。収集役が再起動すると、
XR01 は切れたことに気づいて自分で接続し直します。ラボでは 1 分以内に戻りました。

ダイヤルアウトは、gRPC・TCP・UDP を使えます。TCP は、同じ符号化のメッセージを、gRPC も TLS も使わずに運びます。UDP には
セッションがありません。XR01 は、誰かが待ち受けていてもいなくても宛先を Active と表示し、メッセージは 1 つのデータグラムに
収まる必要があります(最大 65,507 バイト)。Telemetry のガイドは、本番に UDP を勧めていません。

ダイヤルアウトは、決まったデータを決まった収集役へ送るのに向きます。何をどこへ送るかはルータの設定にあり、収集役はルータの
一覧を持たなくて済みます。ダイヤルインは、障害対応で使う道具のように、何を読むかをクライアントが自分で決める場合に向きます。

### 2.4 エンコードとセンサー パス

ダイヤルアウトでは、採取の符号化の形を宛先グループで決めます。

| エンコード | 何が運ばれるか | 収集役に要るもの |
|---|---|---|
| `gpb`(compact GPB) | 値に、フィールドの番号だけが付く。いちばん小さい | どの番号が何かを知るための、パスごとの `.proto` のファイル |
| `self-describing-gpb`(キーと値の GPB) | 値ごとに名前が付く | パスごとのものは要らない。telegraf はそのまま解ける |
| `json` | 文字 | パスごとのものは要らない |

**センサー パス**は、`<モジュール>:<パス>` と書く YANG のパスです。コロンの後ろにスラッシュは付けません。例えば
`openconfig-interfaces:interfaces/interface/state/counters` です。XR は、自分の持つモデルでパスを引きます。見つかれば
**Resolved** で、XR は最も近いコンテナから集めます。表示は `openconfig-interfaces:interfaces/interface/state{counters}`
で、コンテナ `state` を `counters` に絞った、という意味です。

パスは、このリリースにある必要があります。ガイドやほかの所の例の多くは、ネイティブのパス
`Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/latest/generic-counters` を使っています。IOS XR 26.1.1
(XRd と XRv 9000 のどちらも)には、このパスがありません。

| パス | gNMI の Get | センサー パスとして |
|---|---|---|
| `openconfig-interfaces:interfaces/interface/state/counters` | カウンタが返る | Resolved。採取が届く |
| `Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/latest/generic-counters` | NotFound | Not Resolved、`Invalid sensor path`。何も送られない |

解決できないパスを 1 つ含むセンサー グループは **Partial** と表示され、解決できたパスはそのまま送られます。パスが欠けている
ことは収集役に知らされないので、ルータの側で状態を確かめます(3.4 節)。

SRV01 では、telegraf が採取を JSON の行に直します。1 行に 1 つのオブジェクトです。インターフェイスごとに、1 回の採取で
2 行になります。17 個のフィールド(`counters/in_pkts`・`counters/out_pkts`・`counters/in_octets` など)の行と、
`counters/carrier_transitions` の行です。タグには、送ったルータ(`source`)、サブスクリプション、インターフェイス(`name`)、
パスが入ります。

### 2.5 TLS と相互 TLS: 誰が何を証明するか

TLS は、最初の gRPC のメッセージの前に 2 つの仕事をします。クライアントが正しいサーバと話していると確かめられるようにする
ことと、接続を暗号化する鍵を用意することです。サーバは**証明書**を見せます。証明書は、公開鍵と名前を、認証局(CA)が
署名したものです。クライアントは 3 つを確かめます。信頼する CA が署名したこと、今日が有効期間の内であること、接続しよう
とした名前かアドレスが証明書に載っていること(サブジェクト代替名、SAN)です。続いてサーバは、証明書に対応する秘密鍵を
持っていることを証明します。秘密鍵は持ち主の外へ出ません。行き来するのは証明書だけです。

**相互 TLS**(mTLS)では、サーバもクライアントに証明書を求め、自分の信頼する CA で同じように確かめます。こうなると、
両側に 2 つずつ要ります。自分を証明するための自分の証明書と鍵と、相手を確かめるための、相手の証明書に署名した CA の
証明書です。

XRT-15 での部品は、次のとおりです。

| 接続 | 証明書を見せる側 | 確かめる側と、使うもの | XR01 のファイル |
|---|---|---|---|
| gNMI のダイヤルイン(TLS) | XR01: `ems.pem`(CN ems.cisco.com、自己署名) | SRV01 の gnmic: CA のファイルと名前。または確かめない(`--skip-verify`) | `/misc/config/grpc/ems.pem`・`ems.key` |
| gNMI のダイヤルイン(相互 TLS。上に加えて) | SRV01: `client.pem`(CN nms-gnmi、NMS-LAB-CA が署名) | XR01: `ca.cert` の CA | `/misc/config/grpc/ca.cert` |
| テレメトリのダイヤルアウト(TLS) | SRV01 の telegraf: CN collector.nms.lab、NMS-LAB-CA が署名 | XR01: `dialout.pem` の CA と、`tls-hostname` の名前(無ければアドレス) | `/misc/config/grpc/dialout/dialout.pem` |

gRPC を初めて設定すると、XR は自分用の証明書を作ります。`ems.pem` と鍵の `ems.key` で、CN と SAN は `ems.cisco.com`、自分で
署名し、有効期間は 20 年です。保証する CA は無く、名前も XR01 のアドレスではありません。接続先のアドレスで確かめるクライアント
は、`x509: cannot validate certificate for 10.0.50.1 because it doesn't contain any IP SANs` で失敗します。それでも確かめたい
クライアントは、この証明書そのものを CA のファイルとして使い(`openssl s_client` で取り出せます)、名前 `ems.cisco.com` で
確かめます(gnmic の `--tls-server-name`)。本番では、運用者の CA が署名した証明書を XR に持たせます。

TLS が証明するのは、どの機械どうしが話しているかです。ユーザも引き続き確かめます。gRPC の呼び出しはどれも、メタデータに
ユーザ名とパスワードを載せ、XR はそれを SSH のログインと同じように AAA で確かめます。`tls-mutual` に
`certificate-authentication` を足すと、XR はユーザ名をクライアント証明書の CN から取ります。

ダイヤルアウトでは役が入れ替わります。XR01 が TLS のクライアントで、収集役がサーバです。XR01 は、収集役の証明書を
`dialout.pem` の CA で確かめ、名前も確かめます。`tls-hostname` を設定していればその名前、無ければ宛先のアドレスです。
Telemetry のガイドは、名前が証明書の CN と合う必要があると書いています。ラボの収集役の証明書は、`collector.nms.lab` を CN と
SAN の両方に持ち、アドレス 10.0.50.10 も SAN に持つので、アドレスで確かめても通ります。XR01 は、ダイヤルアウトで自分の
証明書を見せません。証明書を求める収集役は、接続を受け付けないままです。

### 2.6 押さえどころ

- テレメトリは、YANG のパスで名前を付けたデータを、GPB に符号化し、張ったままの接続で送り出す。gNMI は Capabilities・Get・
  Set・Subscribe の 4 つの呼び出しを持つ gRPC のサービス。
- Subscribe は STREAM(SAMPLE・ON_CHANGE・TARGET_DEFINED)・ONCE・POLL。ルータの設定では、採取の間隔をミリ秒で、0 なら変化時。
- ダイヤルインは収集役が接続する(gNMI。gRPC だけ)。ダイヤルアウトは XR が接続する(3 つの塊。gRPC・TCP・UDP)。
- 26.1.1 の XR の gNMI は JSON_IETF だけ。古いネイティブのインターフェイスのパスは無い。センサー パスがすべて Resolved か確かめる。
- TLS では、サーバが証明書を見せ、クライアントが CA・日付・名前を確かめる。相互 TLS では、サーバもクライアントを確かめる。
  XR では、`ems.pem` をクライアントに見せ、`ca.cert` でクライアントを、`dialout/dialout.pem` で収集役を確かめる。

## 3. IOS XR で組む

### 3.1 gRPC のサーバ: TLS と相互 TLS

gRPC のサーバは、`grpc` を設定するまで止まっています。`no-tls` を書かなければ TLS で話し、`tls-mutual` を書くと、すべての
クライアントに証明書を求めます。`vrf` の行が無ければ、グローバルのルーティング テーブルで、XR01 のすべてのアドレスで待ち
受けます。gNMI も同じポートで受けます。

図は、SRV01 の gnmic がクライアント証明書を持って接続するまでの順です。図の番号にカーソルを置くと(スマホでは押すと)、
その部分の設定が出ます。

:::walk
legend: "最初の gNMI のメッセージの前に TLS を張る。青い番号は XR01 に与えるもの。"
rows:
  - {node: SRV01, kind: host, say: ["gnmic に `--tls-cert client.pem --tls-key client.key`", "~ラボのアカウントを `-u` と `-p` に"]}
  - {wire: "[[TCP 10.0.50.10 → 10.0.50.1:57400]] [[=TLS hello]]"}
  - panel: XR01
    sub: gRPC のサーバ(プロセス emsd)
    items:
      - ref: 1
        head: "**待ち受ける** `grpc`  `port 57400`  `address-family ipv4`"
        say: ["`no-tls` が無いので TLS で話す"]
      - say: ["自分の証明書 `ems.pem` を見せる(CN ems.cisco.com、自己署名)", "~SRV01 は確かめる(`--tls-ca` と `--tls-server-name`)か、省く(`--skip-verify`)"]
      - ref: 2
        head: "**クライアントの証明書を求める** `tls-mutual`"
        say: ["SRV01 が見せた証明書を調べる"]
        match:
          - ["証明書なし", false, "tls: certificate required"]
          - ["ca.cert に無い CA の署名", false, "tls: bad certificate"]
          - ["ca.cert の CA(NMS-LAB-CA)の署名", true, "受け付ける"]
      - ref: 3
        head: "**信頼する CA** `/misc/config/grpc/ca.cert`"
        say: ["ファイル。emsd の起動時に読む。差し替えたら `process restart emsd`"]
      - say: ["~TLS が張れた。呼び出しごとにユーザ名とパスワード → AAA", "~→ Capabilities・Get・Set・Subscribe"]
  - aside: "TLS を使わないクライアント(`--insecure`)"
    say: ["~サーバは TLS の hello を待つ → `error reading server preface: EOF`"]
  - aside: "クライアントが ems.pem を接続先のアドレスで確かめる"
    say: ["~`cannot validate certificate for 10.0.50.1 because it doesn't contain any IP SANs`", "~→ 証明書の名前で確かめる: `--tls-server-name ems.cisco.com`"]
:::

:::config fold XR01 — 証明書を見せるクライアントだけを受け付ける、ポート 57400 の gRPC のサーバ
grpc                                          ## ① gRPC のサーバ(プロセス emsd)を動かす。gNMI もこれを使う
 port 57400                                   ## ① 既定のポート。範囲は 57344〜57999
 address-family ipv4                          ## ① IPv4 で待ち受ける。vrf の行が無いので、グローバルのテーブルで
 tls-mutual                                   ## ② すべてのクライアントに証明書を求め、ca.cert で確かめる
!
:::

ラボで初めて gNMI を試すときは、次のように TLS なしでサーバを動かせます。本番向けではありません。ユーザ名とパスワードが、
暗号化されずにネットワークを流れます。ポートは、範囲の中の空いているものなら何でもかまいません。

:::config XR01 — TLS を使わない gRPC のサーバ(ラボでの試験だけ)
grpc
 port 57401                                   ## 57344〜57999 の別のポート
 no-tls                                       ## 素の gRPC。クライアントは gnmic --insecure で接続する
 address-family ipv4
!
:::

`grpc` の塊が持つサーバは 1 つなので、これは 2 台目のサーバを足すのではなく、上の設定を置き換えます。`tls-mutual` が
設定されている間は、XR は `no-tls` を拒みます。先に `tls-mutual` を外します。

```console
RP/0/RP0/CPU0:XR01(config-grpc)#no-tls
RP/0/RP0/CPU0:XR01(config-grpc)#commit

% Failed to commit one or more configuration items during a pseudo-atomic operation. All changes made have been reverted. Please issue 'show configuration failed [inheritance]' from this session to view the errors
RP/0/RP0/CPU0:XR01(config-grpc)#show configuration failed
...
grpc
 no-tls
!!% Invalid argument: Remove grpc tls mutual first!
```

### 3.2 IOS XR に証明書を置く

証明書は設定の行ではありません。Linux のファイル システムの `/misc/config/grpc` の下に置くファイルで、XR が自分で作った
ファイルと並びます。

```console
RP/0/RP0/CPU0:XR01#run ls -la /misc/config/grpc/
total 32
drwxr-xr-x.  5 root root 4096 Nov 10 13:08 .
drwxr-xr-x. 16 root root 4096 Nov 10 13:08 ..
-rw-r--r--.  1 root root 1545 Nov 10 13:08 ca.cert
drwx------.  2 root root 4096 Nov 10 13:20 dialout
-rw-------.  1 root root 1679 Nov 10 13:08 ems.key
-rw-r--r--.  1 root root 1545 Nov 10 13:08 ems.pem
drwxr-xr-x.  2 root root 4096 Nov 10 12:55 gnsi
drwxr-xr-x.  2 root root 4096 Nov 10 13:08 trustpoint
```

XR の `copy` は、XR 自身のファイル システム(`harddisk:` など)にしか書けません。`/misc/config` へ直接写すと失敗します。

```console
RP/0/RP0/CPU0:XR01#copy http://10.0.50.10:8000/ca.pem /misc/config/grpc/dialout/dialout.pem
Copy: /misc/config/grpc/dialout/dialout.pem : path outside filesystem

Error: Copy failed with error 'Destination path is invalid'
```

そこで 2 段階にします。`copy` で `harddisk:` へ写し、`run` で Linux の `cp` を使って先へ写します。`copy` の写し元には
http・tftp・ftp・sftp・scp を使えます。XRT-15 では、SRV01 で `~/pki` を配る小さな Web サーバを動かせば足ります。`copy` は
写し先のファイル名を尋ねるので(`Destination filename [/harddisk:/…]?`)、Enter を押します。

`ca.cert` は、gRPC のプロセス emsd が起動するときに読まれます。差し替えたら emsd を再起動します。それまで XR は古い CA を
使い続け、新しい CA の証明書を持つクライアントにも `tls: bad certificate` を返します。テレメトリのダイヤルアウトは、
再起動の間も続きました。

`dialout.pem` は、再起動が要りません。XR は、次に収集役へ接続するときにこれを読み、接続は自分で試し直します。

:::config fold XR01 — NMS の CA を、gRPC のサーバとダイヤルアウトが探す場所に置く(EXEC モード)
copy http://10.0.50.10:8000/ca.pem harddisk:/nms-lab-ca.pem   ## SRV01 から CA の証明書(公開のもの。鍵ではない)を取ってくる
run cp /harddisk:/nms-lab-ca.pem /misc/config/grpc/ca.cert   ## ③ ダイヤルイン: クライアント証明書の署名元であるべき CA
process restart emsd                          ## ③ emsd は ca.cert を起動時にだけ読む
run cp /harddisk:/nms-lab-ca.pem /misc/config/grpc/dialout/dialout.pem   ## ダイヤルアウト: 収集役の証明書を確かめる CA
:::

XR の上で証明書を読むには、`run` で `openssl` を使います。サブジェクト・発行者・SAN を、相手が期待するものと比べます。

```console
RP/0/RP0/CPU0:XR01#run openssl x509 -in /misc/config/grpc/ems.pem -noout -subject -issuer -ext subjectAltName -dates
subject=C=US, ST=CA, L=San Jose, street=3700 Cisco Way, postalCode=95134, O=Cisco Systems, Inc., OU=CSG, CN=ems.cisco.com, serialNumber=638B85D4E4A
issuer=C=US, ST=CA, L=San Jose, street=3700 Cisco Way, postalCode=95134, O=Cisco Systems, Inc., OU=CSG, CN=ems.cisco.com, serialNumber=638B85D4E4A
X509v3 Subject Alternative Name:
    DNS:ems.cisco.com
notBefore=Nov 10 13:08:16 2026 GMT
notAfter=Nov 10 13:08:16 2046 GMT
```

サブジェクトと発行者が同じなので、自分で署名した証明書です。SRV01 では、`openssl s_client -connect <アドレス>:<ポート>
</dev/null | openssl x509 -noout -subject -issuer -ext subjectAltName` で、サーバが見せる証明書を読めます。XR01 の gRPC の
サーバでも、収集役でも同じです。

新しいリリースでは、gRPC の証明書を gNSI で管理する SSL プロファイルへ移しつつあり、ガイドは `/misc/config/grpc` の証明書を
将来のリリースで非推奨にすると書いています。26.1.1 では、gRPC のサーバとダイヤルアウトが使うのは、これらのファイルです。

### 3.3 ダイヤルアウト: センサー グループ・宛先グループ・サブスクリプション

ダイヤルアウトは、`telemetry model-driven` の下の 3 つの塊で組みます。**センサー グループ**は何を読むか、**宛先グループ**は
どこへどう送るかを決め、**サブスクリプション**が、間隔と送信元のインターフェイスを添えて、2 つを名前で結び付けます。

例は、XR01 の稼働時間とインターフェイスのカウンタを 30 秒ごとに送るものです。図は、GigabitEthernet0/0/0/0 のカウンタの
1 回分の採取が、TLS の gRPC で SRV01 の telegraf に届くまでの順です。図の番号にカーソルを置くと(スマホでは押すと)、
その塊が出ます。

:::walk
legend: "1 回分の採取が収集役へ向かう。青い番号は telemetry model-driven の下の塊。"
rows:
  - panel: XR01
    sub: telemetry model-driven
    items:
      - ref: 1
        head: "**何を読むか** `sensor-group SG-HEALTH`"
        say: ["パスごとに、このリリースの YANG のモデルで引く"]
        match:
          - ["openconfig-interfaces:interfaces/interface/state/counters", true, "Resolved"]
        then: ["→ 全インターフェイスのカウンタ: in-pkts・out-pkts・in-octets …"]
      - ref: 2
        head: "**いつ・どこへ** `subscription SUB-NMS-TLS`"
        say: ["`sensor-group-id SG-HEALTH sample-interval 30000`: 30 秒ごと"]
        then: ["→ `destination-id DG-NMS-TLS`", "→ `source-interface Loopback0`: 接続の送信元は 10.255.0.1"]
      - ref: 3
        head: "**どこへ・どう** `destination-group DG-NMS-TLS`"
        say: ["10.0.50.10 のポート 57500、`encoding self-describing-gpb`"]
      - ref: 4
        head: "**収集役を確かめる** `protocol grpc tls-hostname collector.nms.lab`"
        say: ["XR01 が TLS のクライアント。telegraf が証明書を見せる"]
        match:
          - ["dialout/dialout.pem の CA の署名", true, "NMS-LAB-CA"]
          - ["collector.nms.lab が証明書の名前にある", true, "合う"]
  - {wire: "[[TCP 10.255.0.1 → 10.0.50.10:57500]] [[=TLS]] [[=gRPC]] [[GPB: in-pkts …]]"}
  - {node: SRV01, kind: host, say: ["telegraf が採取を解く", "_/var/log/telegraf/mdt.json にインターフェイスごとに JSON を 2 行"]}
  - aside: "CA のファイルが無い、または tls-hostname が証明書に無い名前"
    say: ["~④で落ちる。TLS のハンドシェイクが失敗 → 宛先は NA のまま。SRV01 には何も届かない", "~サブスクリプションは ACTIVE のこともある。理由は `show grpc trace ems` に"]
  - aside: "解決できないセンサー パス"
    say: ["~① `Cisco-IOS-XR-infra-statsd-oper:…/latest/generic-counters` → Not Resolved", "~グループは Partial。解決できたパスは送られる"]
:::

まず、素の TCP で 3 つの塊を見ます。証明書なしで形が分かります。ラボの収集役は 57500 で TLS の gRPC しか受け付けないので、
TCP の宛先には別の収集役が要ります(telegraf は TCP でも待ち受けられます。ここではポート 57000)。

:::config XR01 — 稼働時間とインターフェイスのカウンタを、30 秒ごとに TCP の収集役へ送る
telemetry model-driven
 destination-group DG-NMS-TCP                 ## ③ どこへ、どう送るか
  address-family ipv4 10.0.50.10 port 57000   ## 収集役のアドレスとポート
   encoding self-describing-gpb               ## 値ごとに名前を付けて運ぶ
   protocol tcp                               ## 素の TCP。gRPC も TLS も使わない
  !
 !
 sensor-group SG-HEALTH                       ## ① 何を読むか
  sensor-path Cisco-IOS-XR-shellutil-oper:system-time/uptime   ## ネイティブのモデル: XR01 の稼働時間
  sensor-path openconfig-interfaces:interfaces/interface/state/counters   ## OpenConfig: 全インターフェイスのカウンタ
 !
 subscription SUB-NMS-TCP                     ## ② 2 つを結び付ける
  sensor-group-id SG-HEALTH sample-interval 30000   ## 30,000 ミリ秒ごと。0 なら変化時
  destination-id DG-NMS-TCP
  source-interface Loopback0                  ## 接続の送信元を Loopback0 のアドレスにする
 !
!
:::

TLS の gRPC にするときに変わるのは、宛先だけです。`protocol grpc` と、確かめる名前です。確かめに使う CA は、3.2 節の
`dialout.pem` のファイルです。

:::config fold XR01 — 同じデータを TLS の gRPC の収集役へ送り、その証明書を確かめる
telemetry model-driven
 destination-group DG-NMS-TLS                 ## ③
  address-family ipv4 10.0.50.10 port 57500   ## SRV01 の telegraf(TLS の gRPC)
   encoding self-describing-gpb
   protocol grpc tls-hostname collector.nms.lab   ## ④ TLS。収集役の証明書がこの名前を持つこと
  !
 !
 subscription SUB-NMS-TLS                     ## ②
  sensor-group-id SG-HEALTH sample-interval 30000   ## ① 同じセンサー グループ
  destination-id DG-NMS-TLS
  source-interface Loopback0
 !
!
:::

`protocol grpc` だけでも TLS を使い、証明書を宛先のアドレスで確かめます(ラボの証明書は SAN に 10.0.50.10 を持つので
通ります)。`protocol grpc no-tls` は、gRPC を暗号化せずに送ります。

### 3.4 確かめ方

**gRPC のサーバ。** `show grpc` で、ポート・VRF・TLS の設定が分かります(`show grpc status` はありません)。全体の出力の
`Service ports gNMI : none` は、gNMI が自分のポートを持たず、主のポートを使うという意味です。

```console
RP/0/RP0/CPU0:XR01#show grpc | include "TLS|Port|Address family|VRF"
Address family                          : ipv4
Port                                    : 57400
VRF                                     : global-vrf
TLS                                     : enabled
TLS mutual                              : enabled
TLS v1.0                                : enabled
TLS Minimum Version                     : TLS 1.0
TLS Maximum Version                     : TLS 1.3
TLS cipher suites
  Default TLS1.3                        : aes_128_gcm_sha256
```

**gNMI のクライアントが失敗するとき。** gnmic のエラーの文が、足りない部品を教えてくれます。パスの要らない `capabilities` で
先に試します。

| gnmic の表示(抜粋) | 意味 |
|---|---|
| `Error while dialing: dial tcp 10.0.50.1:57400 …` | そこで待ち受けているものが無い。`grpc` が無い・ポート違い・VRF 違い |
| `error reading server preface: EOF` | クライアントが素の gRPC(`--insecure`)で TLS のサーバへ |
| `x509: cannot validate certificate for 10.0.50.1 because it doesn't contain any IP SANs` | クライアントがサーバの証明書をアドレスで確かめている。名前で確かめる(`--tls-server-name`)か、確かめを省く |
| `remote error: tls: certificate required` | `tls-mutual` で、クライアントが証明書を見せていない |
| `remote error: tls: bad certificate` | クライアントの証明書が `ca.cert` の CA の署名ではない。または `ca.cert` を差し替えて emsd を再起動していない |
| `unsupported get-request encoding: JSON` | gnmic の既定のエンコード。`-e json_ietf` を付ける |

**テレメトリ。** 要約から細部へ、3 つのコマンドがあります。`show telemetry model-driven subscription [名前]`、
`show telemetry model-driven sensor-group [名前]`、`show telemetry model-driven destination [名前]` です。下の出力は、別の名前で
試したときのものです。センサー グループ SG-IF に OpenConfig のカウンタのパスと infra-statsd のパスを入れ、SUB-TCP は 57000 の
TCP の収集役へ、SUB-TLS は 57600 の TLS の gRPC の収集役へ(名前 collector.lab で確かめる)、SUB-MTLS はクライアント証明書を
求める 57700 の収集役へ送りました。まず、どの収集役も待ち受けていないとき:

```console
RP/0/RP0/CPU0:XR01#show telemetry model-driven subscription
Subscription:  SUB-TCP  ID:  12                State: NA
-------------
  Sensor groups:
  Id                               Interval(ms)               State
  SG-IF                            10000                      Partial

  Destination Groups:
  Id       Encoding            Transport   State   Port    Vrf                               IP
  DG-TCP   self-describing-gpb tcp         NA      57000                                     10.0.50.10
    TLS :             False
...
RP/0/RP0/CPU0:XR01#show telemetry model-driven sensor-group
  Sensor Group Id:SG-IF
    ID:                 12
    Sensor Path:        openconfig-interfaces:interfaces/interface/state/counters
    Sensor Path State:  Resolved
    Sensor Path:        Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/latest/generic-counters
    Sensor Path State:  Not Resolved
      Status:           Invalid sensor path
```

収集役が待ち受けてから:

```console
RP/0/RP0/CPU0:XR01#show telemetry model-driven subscription
Subscription:  SUB-TCP  ID:  12                State: ACTIVE
-------------
  Sensor groups:
  Id                               Interval(ms)               State
  SG-IF                            10000                      Partial

  Destination Groups:
  Id       Encoding            Transport   State   Port    Vrf                               IP
  DG-TCP   self-describing-gpb tcp         Active  57000                                     10.0.50.10
    TLS :             False
...
RP/0/RP0/CPU0:XR01#show telemetry model-driven destination DG-TLS
  Destination Group Id:  DG-TLS
  --------------------
    Destination IP:       10.0.50.10
    Destination Port:     57600
    Subscription:         SUB-TLS
    State:                Active
    Encoding:             self-describing-gpb
    Transport:            grpc
    TLS :                 collector.lab
    Total bytes sent:     18282
    Total packets sent:   12
    Last Sent time:       2026-11-10 13:23:35.4233576752 +0000
...
    Collection Groups:
    ------------------
      Id: 11
      Sample Interval:      10000 ms
...
      Sensor Path:          openconfig-interfaces:interfaces/interface/state{counters}
RP/0/RP0/CPU0:XR01#show telemetry model-driven destination DG-MTLS
  Destination Group Id:  DG-MTLS
  --------------------
    Destination IP:       10.0.50.10
    Destination Port:     57700
    Subscription:         SUB-MTLS
    State:                NA
    Encoding:             self-describing-gpb
    Transport:            grpc
    TLS :                 collector.lab
...
```

- **Sensor Path State**: パスごとに `Resolved` か `Not Resolved`(理由は `Status` に)。一部のパスが解決できないセンサー
  グループは、サブスクリプションの表示で `Partial` になります。解決できたパスは送られます。
- **宛先の State**: `Active` は接続して送っている、`NA` は接続していない(誰も待ち受けていない・TLS の失敗・経路が無い)
  という意味です。XR01 から何かが出ているかは、この行で分かります。
- **サブスクリプションの State**: これだけで判断しないでください。証明書に無い名前を `tls-hostname` にしたとき、
  サブスクリプションは `ACTIVE` で、その宛先は `NA` でした。
- **TLS**: TLS なしは `False`。TLS なら、XR01 が収集役の証明書を照らす名前(またはアドレス)です。
- **Total packets sent**: 宛先が Active の間、採取のたびに増えます。

**宛先が NA の理由。** show のコマンドは理由を出しません。TLS のハンドシェイクの失敗と、そのとき XR01 が確かめたサーバ名のような、
接続が失敗した理由は、`show grpc trace ems` にあります(`last 20` を付けると最後の行だけを見られます)。ファイルは
`run ls -la /misc/config/grpc/dialout/` で、収集役の証明書は SRV01 から `openssl s_client` で確かめます(3.2 節)。

**収集役の側。** telegraf は、1 行に 1 つの JSON のオブジェクトを書きます。`jq` で、1 つのインターフェイスの行と、欲しい
フィールドを取り出します。ここではサブスクリプションが 10 秒ごとに採取しています。1 回の採取で 2 行(`timestamp` が同じ)、
1 行目は 17 個のフィールドで、カウンタが増えていき、2 行目は `carrier_transitions` だけです。

```console
$ grep '"GigabitEthernet0/0/0/0"' /var/log/telegraf/mdt.json | tail -6 | jq -c '[.timestamp, (.fields|keys|length), .fields["counters/in_pkts"], .fields["counters/out_pkts"], .fields["counters/in_unicast_pkts"]]'
[1794321912,17,732,658,284]
[1794321912,1,null,null,null]
[1794321922,17,733,659,284]
[1794321922,1,null,null,null]
[1794321932,17,734,660,284]
[1794321932,1,null,null,null]
```

:::try
名前の取り違えがどう見えるかを確かめます。課題 M13-4 を終えた後に行い、最後に必ず元に戻します。

1. XR01 で、`SUB-IF` が使う宛先グループの `protocol` の行を `protocol grpc tls-hostname telemetry.nms.lab` に変えて、
   コミットします。
2. 30 秒ほど待ってから、`show telemetry model-driven subscription SUB-IF | include "State|TLS"` を見ます。サブスクリプションの
   State と、宛先の State を比べます。
3. `show grpc trace ems last 15` を見て、サーバ名と理由を探します。
4. `protocol` の行を元に戻してコミットします。1 分以内に、宛先が Active に戻ることを確かめます。

結果の例: サブスクリプションは `State: ACTIVE`、宛先は `State: NA` と `TLS : telemetry.nms.lab` でした。トレースには
`Creating new client transport to "{Addr: \"10.0.50.10:57500\", ServerName: \"telemetry.nms.lab\", …` と
`connection error: desc = "transport: authentication handshake failed: tls: failed to verify certificate: x509:
certificate is valid for collector.n…`(行はそこで切れている)がありました。行を戻すと、30 秒以内に宛先が Active に戻りました。
:::

### 3.5 落とし穴

- **gNMI で素の JSON**: XR 26.1.1 は拒みます。gnmic には `-e json_ietf`。
- **古い例から写したパス**: infra-statsd のインターフェイスのパスは、26.1.1 では `Not Resolved`。コミットのたびに、
  センサー パスがすべて `Resolved` かを確かめる。
- **`ca.cert` を差し替えただけ**: emsd は起動時にしか読まない。`process restart emsd`。
- **`copy` で `/misc/config` へ直接**: 拒まれる(`path outside filesystem`)。先に `harddisk:` へ写し、`run cp`。
- **サブスクリプションの State だけを見る**: 何も届いていなくても `ACTIVE` のことがある。宛先の State が `Active` で、
  `Total packets sent` が増えていること。
- **証明書に無い名前の tls-hostname**: 収集役の証明書の名前を `openssl s_client` で読んで、そのどれかを使う。証明書が
  アドレスを持つなら、`tls-hostname` を省いてもよい。
- **クライアント証明書を求める収集役**: XR はダイヤルアウトで証明書を見せないので、宛先は `NA` のまま。
- **`tls-mutual` と `no-tls`**: 拒まれる(`Remove grpc tls mutual first!`)。
- **ems.pem をアドレスで確かめる**: 名前は `ems.cisco.com` しか持たない。その名前で確かめるか、ラボでは確かめを省く。

## 実践

ラボ **XRT-15** で課題 M13-3 と M13-4 に取り組みます。SRV01 では、NMS の CA とクライアント証明書が `~/pki` にあります。

<p class="tolab"><a href="/_learn?id=XRT-15">ワークスペースでラボ XRT-15 を開く</a> — <a href="e3-m13-practice-2.html">課題 M13-3、M13-4</a></p>

:::note
このページの出力は、IOS XRd 26.1.1(XRT-15 の XR01)と、IOS XRv 9000 26.1.1 と IOS XRd 26.1.1 を並べて試した PoC の盤面
(2 つは同じ動きでした)で、Ubuntu 24.04 の gnmic 0.49.1 と telegraf 1.32.3 を使って取得しました。
出典: gNMI の仕様(openconfig/reference の 2.3 節・2.7 節・3.1 節・3.5 節)、RFC 7951(YANG のデータの JSON の書き方)。
Cisco 8000(累積版)と ASR 9000(IOS XR 26.x)の Programmability Configuration Guide(`grpc` のキーワード、ポートの範囲と既定、
認証の方式〔TLS ありのメタデータ・TLS なし・相互 TLS・証明書による認証〕、自己署名の証明書のファイル、25.4.1 からの SSL
プロファイルへの移行)。Cisco 8000(累積版、2026 年)と NCS 5500(IOS XR 26.x)の Telemetry Configuration Guide(ダイヤルインと
ダイヤルアウト、3 つの塊、運び方とエンコード、UDP、ダイヤルアウトの TLS と `tls-hostname`、ダイヤルアウトの CA の置き場、
採取の間隔、gNMI の購読のモード、show のコマンド、`Cisco-IOS-XR-shellutil-oper:system-time/uptime` を使うセンサー グループの例)。
いずれも 2026 年 11 月に確認。
次の項目は実測によるものです。エンコードが JSON_IETF だけであること、Get と Subscribe の結果、エラーの文、`/misc/config/grpc`
の下のファイルと emsd の再起動、`copy` が `/misc/config` を拒むこと、解決できるパスとできないパス、サブスクリプションと宛先の
状態、`show grpc trace ems` の理由、XR がダイヤルアウトでクライアント証明書を見せないこと、telegraf の行。
文書と機器が食い違う所・文書に記述が無い所: gNMI の仕様は両端に素の JSON への対応を求めていますが、XR 26.1.1 は JSON_IETF
しか出しません。Telemetry のガイドは名前が CN と合う必要があると書いていますが、ラボの証明書は名前を CN と SAN の両方に
持つので、XR がどちらを確かめているかは切り分けていません。`ca.cert` を差し替えた後の emsd の再起動と、ダイヤルアウトの
クライアント証明書については、ガイドに記述がありません。IOS XR 24.1.1 から、`grpc gnmi port` で gNMI に専用のポート(既定
9339)を持たせられます。ここでは使っていません。
:::
