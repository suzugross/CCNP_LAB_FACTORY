# M12 — マーキングと MPLS の QoS のモデル

この単元では、プロバイダーのコアを流れるパケットを、扱いで分けることと、悪いパケットから守ることを扱います。
CCNP Service Provider のブループリントでは、4.5 の QoS サービスの実装(分類とマーキング、輻輳回避・ポリシング・シェーピング)と、
1.7 のデータプレーンのセキュリティの実装(uRPF・ACL・RTBH・MACsec)にあたります。1.4 の QoS アーキテクチャ(MPLS の QoS の
モデル、TE の QoS、DiffServ と IntServ、信頼の境界、IPv6 のフロー ラベル)も、このページと付録で説明します。
単元は 3 つのページと付録に分かれています。

| ページ | 中身 | 課題 |
|---|---|---|
| このページ | 印で扱いを分けると何が嬉しいか、DSCP と EXP、ラベルの上の印を 1 ホップずつ追う、3 つのモデル、IOS XR での組み方 | M12-1 |
| ポリシングとシェーピング | 契約の速さで絞る、出口で待たせて均す、優先して送る | M12-2、M12-3 |
| データプレーンの保護 | 偽の送信元を落とす(uRPF)、基盤を守る ACL、攻撃を遠隔で捨てる(RTBH) | M12-4、M12-5 |
| 付録 | TE と QoS(DS-TE ほか)、IntServ と RSVP、IPv6 のフロー ラベル、MACsec、XRv 9000 の対応 | — |

ラボは XRT-14 です。P1 を挟んで、XR01 と PE2 がプロバイダー エッジ(PE)です。XR01 はインターネットとの接続点も兼ねます。
P1 は BGP を持たないコアのルータで、RR1 はルート リフレクタです。RR1 は P1 の脇にぶら下がり、顧客のパケットの経路には
入りません。このページの出力は、IOS XRv 9000 26.1.1(XR01)、IOS XRd 26.1.1(RR1)、IOL 上の IOS XE 17.15(他のルータ)で
取得しました。

:::topo
nodes:
  CE1: {at: [0, 0], label: "CE1 (A のサイト 1)"}
  CUST1: {at: [0, 1.2], label: "CUST1"}
  INET: {at: [1.6, 2.2], label: "INET (インターネット)"}
  XR01: {at: [1.6, 0.6], label: "XR01 (PE)"}
  RR1: {at: [3.2, -0.6], label: "RR1 (RR)"}
  P1: {at: [3.2, 0.6], label: "P1 (P)"}
  PE2: {at: [4.8, 0.6], label: "PE2 (PE)"}
  CE2: {at: [6.4, 0], label: "CE2 (A のサイト 2)"}
  CUST2: {at: [6.4, 1.2], label: "CUST2"}
links:
  - [CE1, XR01, "VRF A"]
  - [CUST1, XR01, "global"]
  - [INET, XR01, "global"]
  - [XR01, P1, "CORE-1"]
  - [P1, PE2, "CORE-2"]
  - [P1, RR1, "RR-LINK"]
  - [PE2, CE2, "VRF A"]
  - [PE2, CUST2, "global"]
frames:
  - {label: "AS 65000 (IS-IS CORE、LDP)", nodes: [XR01, P1, PE2, RR1]}
:::

顧客 A は 2 つのサイトを持ち、L3VPN(VRF A)でつながっています。サイト 1 には電話と PC、サイト 2 には音声サーバと業務の
システムがあります。CUST1 と CUST2 はインターネットへの接続を買った顧客で、INET はインターネットの役です(ページ
「データプレーンの保護」)。

## 1. 何が嬉しいのか

### 1.1 困りごと: 1 本のコアを、急ぐパケットと待てるパケットが共有する

顧客 A の電話の音声は、遅れや揺れに弱いパケットです。音声のパケットが 100 ms 余計に待たされると会話が途切れ、数 % が
落ちると声が欠けます。同じ回線を、ファイルの転送やバックアップのような、少し待っても困らない大量のパケットも通ります。

コアのリンクが空いている間は、どちらもすぐに届きます。困るのは混んだときです。出口のキューが大量のパケットで埋まると、
後から来た音声のパケットはその後ろで待たされ、キューがあふれれば同じように捨てられます。ルータが「どれが急ぐパケットか」を
知らなければ、扱いを分けることはできません。

### 1.2 それ以前の手

2 つの手がありました。

- **帯域を余らせる**: 混まないだけの帯域を用意すれば、扱いを分ける必要はありません。ところが、帯域の需要は増え続け、
  いちばん混む瞬間に合わせて全部のリンクを太くするのは高くつきます。障害で迂回したときにも混みます。
- **流れごとに予約する(IntServ)**: アプリケーションが「この流れにこれだけの帯域を」と RSVP で道すがらのルータに予約し、
  ルータは流れごとの状態を持って守ります(RFC 1633、RFC 2205)。保証は確かですが、コアのルータが、何十万という流れの状態を
  持ち続けることになり、プロバイダーのコアでは規模が合いません(付録)。

### 1.3 DiffServ の答え

DiffServ(Differentiated Services)は、流れを覚える代わりに、**パケットに印を付けて**扱いを決めます(RFC 2475)。

- ネットワークの**縁**(顧客を収容する PE)で、パケットを分類し、印を付けます。印の付け方は、顧客との契約で決めます。
- **中**(コア)のルータは、印だけを見て扱いを決めます。流れを覚えず、印の種類(たかだか数個のクラス)だけを知っていれば
  済みます。
- 同じ印のパケットはまとめて同じ扱いを受けます。この扱いを **PHB**(Per-Hop Behavior、ホップごとの振る舞い)と呼びます。

縁の PE が重い仕事(分類・契約の確認・印付け)を引き受け、コアは軽い仕事(印を見て並べる)だけをする、という分担です。
MPLS のコアでは、印がラベルの上にも載ります(2.3 節)。

## 2. 仕組み: 1 つのパケットを 1 ホップずつ

### 2.1 IP の印: DSCP

IP のヘッダには、扱いの印のための 8 ビット(IPv4 の ToS、IPv6 の Traffic Class)があります。DiffServ はそのうち上位の
6 ビットを **DSCP**(DiffServ Code Point)として使います(RFC 2474 の 3 節)。残りの 2 ビットは輻輳の通知(ECN)用です。
よく使う値は次のとおりです。

| 名前 | DSCP(2 進/10 進) | ToS のバイト | 上位 3 ビット | 意味 |
|---|---|---|---|---|
| EF | 101110 / 46 | 0xb8 | 5 | 遅れと揺れを小さく、決まった速さまで最優先(RFC 3246) |
| AF21 | 010010 / 18 | 0x48 | 2 | AF のクラス 2、捨てられにくさ 1(RFC 2597) |
| AF22 | 010100 / 20 | 0x50 | 2 | AF のクラス 2、捨てられにくさ 2(混めば AF21 より先に捨てる) |
| AF11 | 001010 / 10 | 0x28 | 1 | AF のクラス 1、捨てられにくさ 1 |
| CS6 | 110000 / 48 | 0xc0 | 6 | ネットワークの制御(ルーティング プロトコル) |
| 既定(BE) | 000000 / 0 | 0x00 | 0 | 特別な扱いなし |

AF(Assured Forwarding)は 4 つのクラスと 3 段の捨てられにくさの組で、AF*xy* の *x* がクラス、*y* が捨てられやすさです
(大きいほど先に捨てる)。同じクラスの中では、パケットの順番を入れ替えてはならないので、契約を超えた分は「捨てる」代わりに
「AF22 に付け替えて運ぶ」ことができます(ページ「ポリシングとシェーピング」)。上位 3 ビットは、DSCP の前の IP
Precedence と同じ位置です。

### 2.2 信頼の境界

印は、パケットを作った機器が付けます。顧客の電話は自分のパケットに EF を付けますが、顧客の PC が、自分のパケットを速くしたくて
EF を付けることもあります。プロバイダーが顧客の印をそのまま信じると、契約していないパケットが最優先で運ばれ、本当の音声を
押しのけます。

そこで、プロバイダーは自分の網の入口に**信頼の境界**を置きます。PE が顧客から受け取ったパケットを分類し、契約に合わない
印を付け直してから、コアへ入れます。どこまでの印を信じるかは契約で決めます。たとえば「EF は音声網宛てのものだけ、
ほかの EF は既定に戻す」です(課題 M12-1)。企業の網の中でも同じ考え方で、IP 電話は信じて PC は信じない、のように
境界を置きます。

### 2.3 ラベルの上の印: EXP

MPLS のコアのルータは、パケットのいちばん上のラベルだけを見て転送します(M8)。ラベルの下の IP ヘッダまで読まずに扱いを
決めるには、印がラベルの上にも要ります。ラベルの 32 ビットのうち 3 ビットがそのための場所で、**EXP**(Experimental)と
呼ばれてきました。今の規格での名前は **TC**(Traffic Class)です(RFC 5462)。キャプチャの表示も `tc` です。

3 ビットなので、印は 8 種類までです。この 3 ビットでホップごとの扱い(PHB)を決める LSP を **E-LSP** といいます
(RFC 3270 の 1.2 節)。クラスごとに別のラベル(別の LSP)を張り、ラベルでクラスを表す **L-LSP** もあります(1.3 節)。
ふつうのコアは E-LSP です。このラボも E-LSP で、LDP のラベルはクラスを問わず 1 本です。

### 2.4 線の上で追う: 方策が何も無いとき

顧客 A のサイト 1 からサイト 2 へ、3 種類のパケットを送ります。宛先ごとに、CE1 が EF・AF11・印なしを付けます。XR01 にも PE2 にも
QoS のポリシーを入れていない状態で、線の上のパケットを CML のリンクで捕まえました。

:::topo
nodes:
  CE1: {at: [0, 0.5], kind: host}
  XR01: [1.4, 0.5]
  P1: [2.8, 0.5]
  PE2: [4.2, 0.5]
  CE2: {at: [5.6, 0.5], kind: host}
links:
  - [CE1, XR01, "IP EF"]
  - [XR01, P1, "16(5) | 23(5)"]
  - [P1, PE2, "23(5)"]
  - [PE2, CE2, "IP EF"]
:::

線の上の数字はラベルで、括弧の中が EXP です。左がいちばん上です。

```console
# XR01 → P1 の線(EF・AF11 の順)
MPLS (label 16, tc 5, ttl 254) (label 23, tc 5, [S], ttl 254) IP (tos 0xb8, ttl 254, proto ICMP (1)) 10.46.0.1 > 10.46.0.2: ICMP echo request, id 11, seq 0
MPLS (label 16, tc 1, ttl 254) (label 24, tc 1, [S], ttl 254) IP (tos 0x28, ttl 254, ...) 10.10.0.1 > 10.10.0.2: ICMP echo request, id 12, seq 0
# P1 → PE2 の線
MPLS (label 23, tc 5, [S], ttl 253) IP (tos 0xb8, ttl 254, proto ICMP (1)) 10.46.0.1 > 10.46.0.2: ICMP echo request, id 11, seq 0
# PE2 → CE2 の線
IP (tos 0xb8, ttl 252, proto ICMP (1)) 10.46.0.1 > 10.46.0.2: ICMP echo request, id 11, seq 0
```

1 ホップずつ読みます。

1. CE1 は、EF(ToS 0xb8)の IP パケットを XR01 へ送ります。
2. XR01 は、2 枚のラベル(外側= P1 が PE2 のループバックに付けた LDP のラベル 16、内側= PE2 が VRF A のこの経路に付けた VPN の
   ラベル 23)を積みます。ポリシーが無いので、**DSCP の上位 3 ビット(EF なら 5、AF11 なら 1)を、積んだラベルの全部の EXP に
   写します**。
3. P1 は外側のラベルだけを見ます。PE2 の 1 つ手前なので、外側を外して(PHP)PE2 へ送ります。残った内側の EXP は 5 のままです。
4. PE2 は内側のラベルを外し、IP パケットを CE2 へ送ります。DSCP は、CE1 が付けた EF のままです。

逆向き(CE2 からサイト 1)も同じで、PE2(IOS XE)も DSCP の上位 3 ビットを EXP に写しました。公式文書にも、ラベルを積むとき
「識別した precedence・DSCP・EXP の値を EXP に使う」(ASR 9000)、「DSCP の最初の 3 ビットを、積むすべてのラベルの EXP に
写す」(IOS の TAC 文書)とあります。ラベルを外すときは、ポリシーが無ければ DSCP を書き換えません。

### 2.5 3 つのモデル: 顧客の印とプロバイダーの印

プロバイダーは、顧客の DSCP とは別の、自分のクラス分けでコアを運用したいことがあります。顧客は自社の DSCP を自分の
決まりで付けていて、それをサイトの間でそのまま運んでほしいと考えます。この 2 つの印(顧客の DSCP とプロバイダーの EXP)の
関係を、RFC 3270 は 3 つのモデルで整理しています(2.6 節。TTL の扱いも同じ 3 つで、RFC 3443)。

| モデル | 入口の PE(IP → ラベル) | コア | 出口の PE(ラベル → IP) |
|---|---|---|---|
| ユニフォーム | DSCP から EXP を決める | EXP で扱う。付け替えることもある | **EXP を DSCP に写し戻す**(コアでの格下げが顧客にも見える) |
| パイプ | プロバイダーの方針で EXP を付ける | EXP で扱う | DSCP は**そのまま**。出口のキューは **EXP** で決める |
| ショート パイプ | プロバイダーの方針で EXP を付ける | EXP で扱う | DSCP は**そのまま**。出口のキューは**顧客の DSCP** で決める |

ユニフォームは、印が網全体で 1 つという考え方です(印はいつも外側に 1 つだけ意味があり、外すときに下へ写す)。パイプと
ショート パイプは、顧客の印を「トンネルの中の荷物」として触らずに運び、プロバイダーの印は外側にだけ付けます。2 つの違いは、
出口の PE が顧客へ送り出すときに、どちらの印でキューを決めるかです。

XR01 で、AF11 に EXP 2 を付けてみます(DSCP はそのまま)。コアでは EXP 2、顧客に届くのは AF11 のままです。これがパイプと
ショート パイプの入口の形です(設定は 3.2 節)。

```console
# XR01 → P1 の線(AF11 に EXP 2 を付けた後)
MPLS (label 16, tc 2, ttl 254) (label 24, tc 2, [S], ttl 254) IP (tos 0x28, ttl 254, ...) 10.10.0.1 > 10.10.0.2: ICMP echo request, id 15, seq 0
# PE2 → CE2 の線
IP (tos 0x28, ttl 252, ...) 10.10.0.1 > 10.10.0.2: ICMP echo request, id 15, seq 0
```

### 2.6 PHP と explicit null: コアで付け替えた印はどこへ行くか

コアのルータが EXP を付け替えることがあります。混雑への備えとして、あるクラスを格下げする、などです。P1 で、XR01 から来た
EXP 5 を 0 に付け替えてみます(IOS XE の `set mpls experimental topmost 0`)。P1 は付け替えた数を数えますが、PE2 に届いた
パケットの EXP は 5 のままでした。

```console
# P1 → PE2 の線(P1 が EXP 5 を 0 に付け替えた後)
MPLS (label 23, tc 5, [S], ttl 253) IP (tos 0xb8, ttl 254, proto ICMP (1)) 10.46.0.1 > 10.46.0.2: ICMP echo request, id 17, seq 0
```

付け替えたのは外側のラベルで、P1 はそのラベルを PHP で外したからです。外したラベルの EXP は、下のラベルにも IP にも
写されません(IOS の TAC 文書も「ラベルを外すとき、EXP は新しく出てきたラベルに写さない」と書いています)。PHP のままだと、
**コアでの付け替えは出口の PE に届きません**。

出口の PE が explicit null を広告すると、P1 は外側を外さずにラベル 0 に替えて送ります。付け替えた EXP は、そのラベル 0 に
乗って PE2 まで届きます。

:::topo
nodes:
  XR01: [0, 0.5]
  P1: [1.6, 0.5]
  PE2: [3.2, 0.5]
links:
  - [XR01, P1, "16(5) | 23(5)"]
  - [P1, PE2, "0(0) | 23(5)"]
:::

```console
# P1 → PE2 の線(PE2 が explicit null を広告した後)
MPLS (label 0 (IPv4 explicit NULL), tc 0, ttl 253) (label 23, tc 5, [S], ttl 254) IP (tos 0xb8, ttl 254, proto ICMP (1)) 10.46.0.1 > 10.46.0.2: ICMP echo request, id 20, seq 0
```

RFC 3270 が「パイプは PHP なしでだけ動く」(2.6.2 節)と書くのはこのためです。ユニフォームでも、コアでの付け替えを出口で
受け取るには、外側のラベルが出口まで残っている必要があります。ショート パイプは、出口で顧客の DSCP を見るので、PHP のままで
動きます。L3VPN では内側の VPN のラベルが出口まで残るので、入口の PE が付けた EXP は PHP の後も出口で読めます。インターネットの
ように 1 枚のラベルで運ぶ通信は、PHP の後はラベルが無くなり、EXP も消えます(このラボでは CUST1 から CUST2 への通信)。

### 2.7 TTL も同じ話

ラベルの上の 8 ビットの TTL にも、同じ 3 つのモデルがあります(RFC 3443)。既定はユニフォームで、ラベルを積むときに IP の
TTL をラベルへ写し、外すときに戻します。そのため顧客の traceroute に、コアのルータが 1 ホップずつ見えます。

```console
CE1#traceroute 10.100.2.1 source Loopback100 probe 1 timeout 2
  1 172.16.1.254 4 msec
  2 10.0.1.51 [MPLS: Labels 16/21 Exp 0] 3 msec
  3 172.16.2.254 [MPLS: Labels 0/21 Exp 0] 2 msec
  4 172.16.2.1 2 msec
```

3 ホップ目のラベルが `0/21` なのは、この測定のときに PE2 が explicit null を広告していたからです(2.6 節)。

XR01 で `mpls ip-ttl-propagate disable` にすると、XR01 は積むラベルの TTL を 255 にします。コアの中で TTL が尽きなくなり、
P1(10.0.1.51)が traceroute から消えました。コアの作りを顧客から隠したいプロバイダーが使います(パイプの TTL)。

```console
CE1#traceroute 10.100.2.1 source Loopback100 probe 1 timeout 2
  1 172.16.1.254 2 msec
  2 172.16.2.254 [MPLS: Labels 0/21 Exp 0] 2 msec
  3 172.16.2.1 2 msec
```

### 2.8 押さえどころ

- 印は縁の PE で付け、コアは印だけを見る(DiffServ)。どこまで顧客の印を信じるかを、入口の PE で決める(信頼の境界)。
- MPLS のコアでは、印はラベルの 3 ビット(EXP、今の名前は TC)にも載る。方策が無ければ、DSCP の上位 3 ビットが、積んだ
  全部のラベルへ写る。外すときに DSCP は変わらない。
- 3 つのモデルの違いは、出口の PE が「EXP を DSCP に写し戻すか」と「どちらの印でキューを決めるか」。
- コアで付け替えた EXP は、PHP で外側ごと消える。出口まで届けるには explicit null。

## 3. IOS XR で組む

### 3.1 MQC の部品

IOS XR の QoS は、IOS と同じ MQC(Modular QoS CLI)の 3 段で書きます。

| 部品 | 役割 | IOS との違い |
|---|---|---|
| `class-map` | パケットを分ける条件(`match dscp`、`match mpls experimental topmost`、`match access-group ipv4`、`match qos-group` など) | 最後に `end-class-map`。`match-any`(どれか)と `match-all`(全部)を明示する |
| `policy-map` | クラスごとの動作(`set`、`police`、`shape`、`priority` など) | 最後に `end-policy-map`。クラスに書いた順に調べる |
| `service-policy` | インターフェイスに、向き(`input`/`output`)を付けて当てる | 同じ |

印の付け方は次のとおりです。

| 動作 | 意味 | 書ける向き |
|---|---|---|
| `set dscp <値>` | IP の DSCP を書き換える | 入力・出力 |
| `set mpls experimental imposition <0-7>` | 積むラベル**全部**の EXP | 入力だけ(ラベルを積む前に決める) |
| `set mpls experimental topmost <0-7>` | いちばん上のラベルの EXP | 入力・出力 |
| `set qos-group <値>` | 装置の中だけの番号(線には出ない)。入力で付けて、出力で `match qos-group` で読む | 入力だけ |

`qos-group` は、入力で読んだことを出力まで運ぶための装置の中の印です。出口の PE で、コア側の入力で EXP を読み、顧客側の
出力でそれを使うときに要ります(3.3 節)。ASR 9000 のガイドは「set は入力だけ、match は出力だけ」と定めています。

### 3.2 入口の PE: 分類して EXP を付ける

2.5 節で使った設定です。顧客 A のサイト 1 から受け取るパケットを、EF(音声)・AF11(大量のデータ)・その他に分け、
プロバイダーの EXP を付けます。DSCP は触りません。

:::config XR01 — サイト 1 から受け取るパケットに EXP を付ける
class-map match-any VOICE                     ## 音声のクラス。条件が 1 つなら any でも all でも同じ
 match dscp ef
 end-class-map                                ## XR はクラスの終わりを書く
!
class-map match-any BULK
 match dscp af11
 end-class-map
!
policy-map CE-IN
 class VOICE
  set mpls experimental imposition 5          ## 積むラベル全部に EXP 5
 !
 class BULK
  set mpls experimental imposition 2          ## 顧客の AF11(上位 3 ビットは 1)を、コアでは 2 として扱う
 !
 class class-default
  set mpls experimental imposition 0          ## 残りは 0。書かなければ DSCP の上位 3 ビットが写る
 !
 end-policy-map
!
interface GigabitEthernet0/0/0/1              ## CE1 へのインターフェイス(VRF A)
 service-policy input CE-IN                   ## 入力に当てる。imposition は入力でだけ書ける
:::

信頼の境界(2.2 節)で顧客の印を付け直すときは、クラスに `set dscp` を足します。たとえば「宛先が音声網でない EF」のクラスを
作り(`class-map match-all` で `match dscp ef` と宛先の ACL を組み合わせる、か、先に音声網宛ての EF のクラスを置いて残りの EF を
後ろのクラスで拾う)、そこで `set dscp default` にします。

IOS XE で同じことをすると次のようになります(ラボの PE2 の据え付けの設定から)。`end-class-map` は無く、`set mpls experimental
imposition` の書き方は同じです。

:::config PE2(IOS XE)— CE2 から受け取るパケットに EXP を付ける(据え付けの設定から抜粋)
class-map match-any VOICE
 match dscp ef
class-map match-any DATA
 match dscp af21
!
policy-map CE-IN
 class VOICE
  set mpls experimental imposition 5
 class DATA
  set mpls experimental imposition 3
 class class-default
  set mpls experimental imposition 0
!
interface Ethernet0/1
 service-policy input CE-IN
:::

### 3.3 出口の PE: EXP を受け継ぐ

ユニフォームの出口を XR01 で作ります(CE2 からサイト 1 へのパケット)。P1 は PE2 から来た EXP 5 を 0 に付け替えています。
XR01 は、コア側の入力で外側のラベルの EXP を読んで qos-group に移し、CE1 側の出力で qos-group を DSCP に写します。
PHP のままだと付け替えが届かないので(2.6 節)、XR01 から explicit null を広告します。

:::config fold XR01 — 出口でコアの EXP を顧客の DSCP に写し戻す(ユニフォーム)
mpls ldp
 address-family ipv4
  label
   local
    advertise
     explicit-null                            ## 自分のループバックに、0 を付けたまま渡してと頼む(PHP をやめる)
!
class-map match-any EXP5
 match mpls experimental topmost 5            ## コア側の入力では、いちばん上のラベルの EXP が読める
 end-class-map
class-map match-any EXP0
 match mpls experimental topmost 0
 end-class-map
!
policy-map CORE-IN
 class EXP5
  set qos-group 5                             ## 読んだ EXP を、装置の中の印に移す(入力でだけ付けられる)
 !
 class EXP0
  set qos-group 7
 !
 end-policy-map
!
class-map match-any QG7
 match qos-group 7                            ## 出力でだけ読める
 end-class-map
!
policy-map CE-OUT-UNIFORM
 class QG7
  set dscp default                            ## コアで 0 にされたものは、顧客にも 0 で渡す
 !
 end-policy-map
!
interface GigabitEthernet0/0/0/0              ## P1 へのインターフェイス
 service-policy input CORE-IN
!
interface GigabitEthernet0/0/0/1              ## CE1 へのインターフェイス
 service-policy output CE-OUT-UNIFORM
:::

ラボで測った結果: explicit null を広告する前は、XR01 に届くラベルは内側の 1 枚(`label 24007, tc 5`)で、CORE-IN は EXP 5 と
数え、CE1 には EF のまま届きました。広告した後は `label 0 (IPv4 explicit NULL), tc 0` が付いて届き、EXP0 のクラスに数えられ、
CE1 には DSCP 0 で届きました。

```console
# P1 → XR01 の線(XR01 が explicit null を広告した後)
MPLS (label 0 (IPv4 explicit NULL), tc 0, ttl 253) (label 24007, tc 5, [S], ttl 254) IP (tos 0xb8, ttl 254, proto ICMP (1)) 10.46.0.2 > 10.46.0.1: ICMP echo request, id 9, seq 0
# XR01 → CE1 の線
IP (tos 0x0, ttl 252, proto ICMP (1)) 10.46.0.2 > 10.46.0.1: ICMP echo request, id 9, seq 0
```

パイプにするなら、出力の `set dscp` を書かず、qos-group で出口のキューを決めます。ショート パイプなら、入力の CORE-IN は
要らず、出力で顧客の DSCP(`match dscp`)でキューを決めます。キューの作り方はページ「ポリシングとシェーピング」で扱います。

### 3.4 確かめ方

```console
RP/0/RP0/CPU0:XR01#show qos interface GigabitEthernet0/0/0/1 input
Interface: GigabitEthernet0_0_0_1 input
Bandwidth configured: 1000000 kbps Bandwidth programmed: 1000000 kbps
...
Policy: CE-IN Total number of classes: 3
----------------------------------------------------------------------
Level: 0 Policy: CE-IN Class: VOICE
Bandwidth: 0 kbps, BW sum for Level 0: 0 kbps, Excess Ratio: 0
QueueID: 25 (Port Default)
Child Mark: set exp-imp 5   set qos-grp 5
...
RP/0/RP0/CPU0:XR01#show policy-map interface GigabitEthernet0/0/0/1 input
...
Class VOICE
  Classification statistics          (packets/bytes)     (rate - kbps)
    Matched             :                   3/354                  0
    Transmitted         : N/A
    Total Dropped       :                   0/0                    0
```

- `show qos interface` は、ポリシーがハードウェア(XRv 9000 ではデータプレーン)にどう入ったかを示します。`Child Mark:` の行が
  付ける印です。
- `show policy-map interface` は、クラスごとに数えた数です。★XRv 9000 では、この数がパケットを流してから **10〜30 秒遅れて**
  増えました。流してすぐに見ると 0 のままです。
- コアの中の EXP は、P のルータで数えるのが手軽です(このラボでは P1 の `COUNT-EXP`。IOS XE の `show policy-map interface
  Ethernet0/0 input`)。

:::try
方策が無いときの EXP の写り方を、ラボで確かめます。課題 M12-1 を終えた後に行い、最後に必ず元に戻します。

1. XR01 で、CE1 側のインターフェイスから入力のポリシーを外します(`no service-policy input <名前>` をコミット)。
2. P1 で `clear counters Ethernet0/0` を実行し、CE1 で `ping 10.21.2.1 source Loopback21 repeat 10` を実行します。
3. P1 で `show policy-map interface Ethernet0/0 input` を見ます。業務のパケット(AF21)は、どのクラスに数えられたでしょうか。
4. XR01 のポリシーを戻します。

ラボで測った結果: `COUNT-EXP` の EXP5・EXP3・EXP1・EXP0 はどれも 0 のままで、`class-default` が 11 増えました(10 発と、
ほかのパケット 1 つ)。AF21 の上位 3 ビットの 2 が EXP に写り、P1 の数えるクラスのどれにも当たらなかったからです。
:::

### 3.5 落とし穴

- **1 つのクラスに付けられる印は 2 種類まで**: XRv 9000 は、EXP と qos-group を付けたクラスのポリサに、超えた分の
  `set dscp` を足すと、`only two mark types are allowed per class` でコミットを拒みました(ASR 9000 のガイドも「1 クラスに
  set は 2 つまで」)。ポリサの動作の中の印も数に入ります。
- **qos-group は入力で付けて出力で読む**: 逆には書けません。出口の PE で EXP を DSCP に写すには、入力と出力の 2 つの
  ポリシーが要ります。
- **PHP は付け替えを消す**: コアでの付け替えを出口で使うなら explicit null(2.6 節)。
- **カウンタが遅れる**: 確かめるときは 30 秒ほど待つ(3.4 節)。

## 実践

ラボ **XRT-14** で課題 M12-1 に取り組みます。XR01 は IOS XRv 9000 なので、ラボの構築に約 10 分かかります。

<p class="tolab"><a href="/_learn?id=XRT-14">ワークスペースでラボ XRT-14 を開く</a> — <a href="d1-m12-practice.html">課題 M12-1</a></p>

:::note
出典: RFC 2474(3 節・4 節)、RFC 2475(2 節)、RFC 2597(2 節・6 節)、RFC 3246(2 節)、RFC 1633、RFC 2205、RFC 3270(1.2 節・1.3 節・
2.6 節)、RFC 3443(3 節)、RFC 5462。ASR 9000 の Modular QoS Configuration Guide と Modular QoS Command Reference(IOS XR 24.x。
既定のマーキング、qos-group と discard-class の向き、1 クラスの set の数、MPLS QoS の 3 つのモードの表と出口の PE の例)、ASR 9000 の
MPLS Command Reference(`mpls ip-ttl-propagate disable`、LDP の `explicit-null`)、Cisco の TAC 文書「DiffServ Tunneling Modes for
MPLS Networks」(47815)。いずれも 2026 年 11 月に確認。次の項目は、PoC の盤面(XRT-14 と同じ形)での実測によるものです。方策が無いときの
EXP(XR01 と PE2 の両方)、PHP で付け替えが消えること、explicit null での受け渡し、ユニフォームの出口、TTL、カウンタの遅れ、
1 クラスの印の数(線の上は CML のリンクのキャプチャ)。
:::
