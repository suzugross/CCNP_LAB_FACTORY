# M10 — セグメント ルーティングの仕組み

この単元では、コアのラベルを LDP から**セグメント ルーティング**(SR)に替え、その上で、障害のときの迂回と、一部の
トラフィックだけに別の道を通らせることを扱います。CCNP Service Provider のブループリントの 3.3 にあたります。
単元は 3 つのページと付録に分かれています。

| ページ | 中身 | 課題 |
|---|---|---|
| このページ | SR で何が嬉しいか、ラベルで道順を書く仕組み、LDP からの移行 | M10-1、M10-2 |
| TI-LFA | リンクが切れたときに、すぐに迂回する | M10-3 |
| SR ポリシーと PCE | 一部のトラフィックだけ別の道を通らせる、道を中央で計算する | M10-4、M10-5 |
| 付録 | フレキシブル アルゴリズム、SRv6、SID の衝突 | — |

ラボは XRT-10 です。ラボ XRT-09 の続きで、同じ四角形のコア、同じ VPN の顧客、M9 の課題を終えた XR01 と XR02 です。
IOS ルータは既に SR を動かしていて、XR01 が LDP から移る最後のルータです。

:::topo
nodes:
  CEA1: {at: [0, 0.3], label: "CEA1 (A, site 1)"}
  CEB1: {at: [0, 1.5], label: "CEB1 (B, site 1)"}
  XR01: {at: [1.6, 0.9], label: "XR01 (PE) idx 1"}
  RT01: {at: [3.2, 0.2], label: "RT01 (P) idx 11"}
  RT03: {at: [3.2, 1.6], label: "RT03 (P) idx 13"}
  XR02: {at: [3.2, 2.7], label: "XR02 (RR, PCE)"}
  RT02: {at: [4.8, 0.9], label: "RT02 (PE) idx 12"}
  CEA2: {at: [6.4, 0.4], label: "CEA2 (A, site 2)"}
  CEB2: {at: [6.4, 1.4], label: "CEB2 (B, site 2)"}
links:
  - [CEA1, XR01, "CUST-A"]
  - [CEB1, XR01, "CUST-B"]
  - [XR01, RT01, "PRIMARY 10"]
  - [XR01, RT03, "BACKUP 100"]
  - [RT01, RT02, "CORE-A 10"]
  - [RT03, RT02, "CORE-B 100"]
  - [RT03, XR02, "RR-LINK 10"]
  - [RT02, CEA2, "CUST-A"]
  - [RT02, CEB2, "CUST-B"]
frames:
  - {label: "AS 65000 (IS-IS CORE, SR-MPLS)", nodes: [XR01, RT01, RT03, RT02, XR02]}
:::

コアのリンクの数字は IS-IS のメトリック、「idx」は各ルータのループバックに付けた番号(プレフィックス SID のインデックス。
2.1 節)です。XRT-09 の共有サービスとインターネットは XR01 の向こうに今もありますが、この単元では出てきません。

## 1. 何が嬉しいのか

### 1.1 LDP の困りごと: 経路とラベルを別々のプロトコルが運ぶ

M8 と M9 のコアでは、IS-IS が経路を計算し、LDP がその経路で使うラベルを配っていました。2 つは別々のプロトコルで、
別々に動きます。そのため、IS-IS は新しいリンクを使い始めたのに、そのリンクの LDP のセッションがまだ上がっておらず、
ラベルの無いパケットがコアで捨てられる、ということが起きます。M8 で LDP-IGP 同期とセッション保護を設定したのは、
このずれを埋めるためでした。

もう 1 つは、ラベルの値がルータごとに違うことです。LDP では、各ルータが自分でラベルを選びます。M8 のラボでは、RT02 の
ループバック宛てのラベルは、RT01 では 16、XR01 では 24002 でした。パケットがどこへ向かっているかを調べるには、
ホップごとに表を引くことになります。

SR では、ラベルは IS-IS が経路と一緒に運びます。経路はあるのにラベルが無い、というずれは起きず、LDP そのものが
要らなくなります。ラベルの値は宛先ごとに 1 つに決まり、どのルータでも同じです(2 節)。

### 1.2 IGP は宛先ごとに 1 本の道しか選べない

IGP は、宛先ごとに最短のパスを 1 本計算し、その宛先へのトラフィックはすべてそこを通ります。ラボでは、XR01 から RT02 への
トラフィックは、顧客 A のものも顧客 B のものも、PRIMARY と RT01 を通ります(メトリック 20。RT03 経由は 200)。

ところが、トラフィックによって違う道を通らせたいことがあります。課題 M10-4 では、RT01 の保守のために顧客 A だけを
RT03 経由にし、顧客 B は今のままにします。課題 M10-5 では、どのリンクも共有しない 2 本の道を用意します。

SR の前の手は、どれも重いものでした。

- **メトリックを変える**: 全員の道が変わります。顧客 A のルートも顧客 B のルートも、ネクスト ホップは同じ RT02 の
  ループバックなので、片方だけを動かすことはできません。
- **ポリシー ベース ルーティング**: 道の途中のすべてのルータに、ホップごとの設定が要ります。
- **RSVP-TE のトンネル**: 入口のルータがトンネルを張り、通り道のすべてのルータがトンネルごとの状態を持ち、更新し続けます。
  PE どうしをフルメッシュで結ぶと、トンネルの数は PE の数のほぼ 2 乗で増えます。

SR では、入口のルータがパケットに「どこを経由するか」をラベルで書き込みます。途中のルータは道ごとの状態を何も持たず、
いつもどおりラベルで転送するだけです(2.3 節)。

### 1.3 障害で止まる時間

リンクが切れると、IGP は障害に気づき、それを全ルータに知らせ、各ルータで最短パスを計算し直し、転送テーブルを
書き換えます。それが終わるまでパケットは失われます。障害の隣のルータに迂回の道を前もって用意させる仕組み(LFA)は
以前からありましたが、トポロジによっては迂回の道が見つかりません。このラボの四角形でも、RT01 のループバック宛てには
見つかりません。SR を使う **TI-LFA** は、どのトポロジでも迂回の道を用意できます(ページ「TI-LFA」)。

### 1.4 困りごとと SR の答え

| 困りごと | SR の答え | 場所 |
|---|---|---|
| 経路とラベルを別々のプロトコルが運び、ずれる | IS-IS がラベルも運ぶ(プレフィックス SID) | このページ、課題 M10-1・M10-2 |
| 障害のときに迂回の道が無いことがある | 迂回の道順をラベルで書いておく(TI-LFA) | 「TI-LFA」、課題 M10-3 |
| 一部のトラフィックだけ別の道を通らせたい | 道順に名前を付け、カラーで振り分ける(SR ポリシー) | 「SR ポリシーと PCE」、課題 M10-4 |
| 重ならない道を、全体を見て計算したい | 中央の計算役(PCE) | 「SR ポリシーと PCE」、課題 M10-5 |
| 遅延など、別の基準での最短パスも欲しい | 基準ごとの最短パス(フレキシブル アルゴリズム) | 付録 |

## 2. 仕組み: ラベルで道順を書く

### 2.1 ルータに番号を配る

SR では、各ルータのループバックに番号を 1 つ決めます。この番号が**インデックス**です。ラボでは、ループバックのアドレスの
最後のオクテットにしています。RT02(10.255.0.12)は 12 です。番号は RT02 に 1 回設定するだけで、IS-IS がループバックの
プレフィックスと一緒に全ルータへ配ります。

各ルータは、ラベルのために確保した範囲、**SR グローバル ブロック**(SRGB)の先頭に番号を足して、ラベルにします。
既定のブロックは IOS XR でも IOS XE でも 16000〜23999 なので、RT02 のラベルはどのルータでも 16000 + 12 = **16012** です。
16012 は「RT02 へ、最短パスで行け」という意味になります。この命令を**セグメント**、それを名指す値を**セグメント識別子**
(SID)と呼びます。ループバックのプレフィックスに付けたものが**プレフィックス SID** です。

各ルータは、自分の IS-IS の最短パスで RT02 への次のホップを決め、「16012 で受けたら、16012 のまま次のホップへ送る」
というエントリを転送テーブルに作ります。LDP との違いは、ラベルの値を誰にも聞かずに決められることです。

| RT02 宛てに受け付けるラベル | LDP | SR |
|---|---|---|
| XR01 | XR01 が選んだ値(M8 のラボで 24002) | 16012 |
| RT01 | RT01 が選んだ値(M8 のラボで 16) | 16012 |
| RT03 | RT03 が選んだ値 | 16012 |

### 2.2 ラベル 1 枚: 最短パスでそのルータへ

顧客 B のパケットを、CEB1 から CEB2 まで追います。XR01 は、VPN のルート 10.102.2.0/24 のネクスト ホップが RT02 なので、
VPN のラベル(M9)の上に RT02 のラベル 16012 を付け、最短パスの次のホップの RT01 へ送ります。RT01 は RT02 の 1 つ手前
なので、16012 を外します(PHP。M8 と同じです)。RT02 は VPN のラベルを見て、パケットを顧客 B の VRF へ渡します。

:::topo
nodes:
  CEB1: {at: [0, 1], kind: host}
  XR01: [1.3, 1]
  RT01: [2.6, 0.15]
  RT03: [2.6, 1.85]
  RT02: [3.9, 1]
  CEB2: {at: [5.2, 1], kind: host}
links:
  - [CEB1, XR01, "IP"]
  - [XR01, RT01, "16012 | 24"]
  - [RT01, RT02, "24"]
  - [RT02, CEB2, "IP"]
  - {a: XR01, b: RT03, style: dashed}
  - {a: RT03, b: RT02, style: dashed}
:::

線の上の数字は、そのリンクを通るときに付いているラベルで、左がいちばん上です。24 は顧客 B の VPN のラベルで、構築の
たびに値が変わります。CEB1 からの traceroute に、同じものが出ます。

```console
CEB1#traceroute 10.102.2.1 source 10.102.1.1 numeric timeout 1 probe 1
Type escape sequence to abort.
Tracing the route to 10.102.2.1
VRF info: (vrf in name/id, vrf out name/id)
  1 172.16.21.1 3 msec
  2 10.0.1.11 [MPLS: Labels 16012/24 Exp 0] 2 msec
  3 172.16.22.1 [MPLS: Label 24 Exp 0] 1 msec
  4 172.16.22.2 1 msec
```

2 番目のホップ(RT01)には 16012 と 24 の 2 枚が、3 番目のホップ(RT02)には 24 だけが届いています。ここまでの働きは
LDP と同じで、違うのはラベルの値だけです。

### 2.3 ラベルを重ねて経由地を書く

顧客 A のパケットには RT03 を通らせたいとします(課題 M10-4)。XR01 はラベルを重ねます。いちばん上に「RT03 へ最短で」の
16013、その下に「RT02 へ最短で」の 16012、いちばん下に VPN のラベルです。各ルータは**いちばん上のラベルだけ**を見て
転送し、そのラベルの宛先の 1 つ手前でそれを外します(PHP)。すると、次のラベルがいちばん上になります。

1. XR01: いちばん上は 16013 です。RT03 は XR01 の隣なので、XR01 自身が「1 つ手前」です。XR01 は 16013 を付けずに
   RT03 へ出します。リンクを通るのは 16012 と VPN のラベルです。
2. RT03: いちばん上の 16012 を見ます。RT03 から RT02 への最短パスは CORE-B の直結(100。XR01 と RT01 を戻ると 120)
   なので、そこへ送ります。RT02 の 1 つ手前なので、16012 を外します。
3. RT02: VPN のラベルを見て、パケットを顧客 A の VRF へ渡します。

:::topo
nodes:
  CEA1: {at: [0, 1], kind: host}
  XR01: [1.3, 1]
  RT01: [2.6, 0.15]
  RT03: [2.6, 1.85]
  RT02: [3.9, 1]
  CEA2: {at: [5.2, 1], kind: host}
links:
  - [CEA1, XR01, "IP"]
  - {a: XR01, b: RT01, style: dashed}
  - {a: RT01, b: RT02, style: dashed}
  - [XR01, RT03, "16012 | 22"]
  - [RT03, RT02, "22"]
  - [RT02, CEA2, "IP"]
:::

```console
CEA1#traceroute 10.101.2.1 source 10.101.1.1 numeric timeout 1 probe 1
Type escape sequence to abort.
Tracing the route to 10.101.2.1
VRF info: (vrf in name/id, vrf out name/id)
  1 172.16.11.1 [AS 64500] 2 msec
  2 10.0.3.13 [AS 64500] [MPLS: Labels 16012/22 Exp 0] 2 msec
  3 172.16.12.1 [AS 64500] [MPLS: Label 22 Exp 0] 1 msec
  4 172.16.12.2 [AS 64500] 2 msec
```

22 は顧客 A の VPN のラベルです。`[AS 64500]` は IOS の traceroute が CEA1 の BGP の表から添える AS 番号(M9 のインターネット
の AS)で、ラベルとは関係ありません。押さえどころは 3 つです。

- 道を決めたのは XR01 だけです。RT03 と RT02 は「16012 は RT02 へ」というふだんの表で転送しただけで、顧客 A の道について
  何も知りません。設定も、道ごとの状態も要りません。
- 経由地と経由地の間は最短パスです。その区間に等コストのパスがあれば分散し、リンクが落ちれば IGP が直します。
- 顧客 B のパケットは 2.2 節のままです。ラベルを重ねるのは、XR01 が選んだパケットだけです。

### 2.4 リンクを指定する: 隣接 SID

経由地をルータで書くと、そこから先は最短パスです。特定のリンクを通らせたいときは、**隣接 SID** を使います。「このリンク
から出よ」という命令で、1 台のルータの 1 本のリンクに付き、そのルータの上でだけ効きます(ローカル)。IS-IS が
リンクごとに自動で割り当て、アドバタイズします。XR01 の RT01 へのリンクは 24011、RT03 へのリンクは 24013 です(3.2 節)。

そのルータでしか効かないラベルを、なぜアドバタイズするのでしょうか。他のルータが道順に書けるようにするためです。「どのルータの、どのリンクが、どの番号か」はエリアの全ルータが知りますが、転送テーブルに入れるのは持ち主だけです。番号はルータごとに振るので、別のルータが同じ番号を自分のリンクに使っていても構いません(ラボの IOL は 22〜27 のような小さい番号を振ります)。

重ねるラベルには、プレフィックス SID と隣接 SID を混ぜられます。たとえば「RT03 へ行き、RT03 の RT02 へのリンクから出る」は、
16013 の下に、RT03 の RT02 へのリンクの隣接 SID を置きます。TI-LFA は、最短パスだけでは迂回できないときにこれを使います
(ページ「TI-LFA」)。

つまり隣接 SID が効くのは、先頭のラベルとして持ち主に届いたときだけです。上の例で 16013 を先に置くのは、パケットを RT03 まで運ぶためです。RT03 は XR01 の隣なので 16013 は PHP で外れます。BACKUP のメトリックを 10 にしたときの TI-LFA の迂回は、実際に `{ImplNull 23 16011}` を積みました(23 が RT03 の RT02 へのリンク。ページ「TI-LFA」の 2.3 節)。先頭のまま別のルータに届けば、そのルータは自分の 23 として読むことになります。

### 2.5 誰が、どのパケットに、どの道順を書くか

ラベルを書くのは、パスの入口のルータ、**ヘッドエンド**です。ラボでは XR01 です。残る問いは 3 つで、この単元の残りの
ページがそれに答えます。

- **障害のとき**: 迂回の道順を前もって計算し、転送テーブルに入れておきます。TI-LFA です。
- **どのパケットに**: 何もしなければ、パケットは最短パス(ラベル 1 枚)を通ります。別の道順を書くのは、**SR ポリシー**に
  誘導したパケットだけです。誘導の目印は、BGP のルートに付けた**カラー**です。
- **道順を誰が決めるか**: 人が設定に書く(明示的)、ヘッドエンドがトポロジと制約から計算する(動的)、または中央の
  **PCE** が計算します。

### 2.6 セグメントの種類

RFC 8402 は、セグメントを次のように分けています。ブループリントはこれらの説明を求めています。

- **プレフィックス セグメント**: プレフィックスまで最短パスで運びます。グローバルで、ドメインの全ルータが同じ値を
  使います。**ノード セグメント**は、ルータ自身のループバックのプレフィックス セグメントで、N フラグが立ちます
  (「このプレフィックスはこのノード」)。
- **エニーキャスト セグメント**: 複数のルータが同じプレフィックスに同じ SID をアドバタイズし、パケットは最も近いものへ
  行きます。N フラグは立てません。
- **隣接セグメント**: 1 台のルータの 1 本のリンクから出します。ローカルです。
- **BGP のセグメント**: BGP のプレフィックス SID は、BGP のルートに SID を付けます(RFC 8669。M8 の Unified MPLS の
  ラベル付きユニキャストと組み合わせます)。BGP のピアリング SID(PeerNode、PeerAdj、PeerSet)は、別の AS のピアへの
  出口を名指します。SR での出口ピア エンジニアリングのやり方です。
- **バインディング セグメント**(バインディング SID): SR ポリシー全体を名指します。このラベルで届いたパケットは、
  そのポリシーに誘導されます。

SR-MPLS では SID は MPLS のラベルで、データ プレーンは M8 と同じ、付ける・付け替える・外すです。SRv6 では SID は
IPv6 のアドレスです(付録)。SID を運ぶのは IGP で、IS-IS(RFC 8667)にも OSPF にも拡張があり、BGP も運べます。

### 2.7 ブロックの細部

ブロックは、ルータごとに違っても構いません。そのときルータは、送るラベルを次のホップのブロックで、受けるラベルを
自分のブロックで計算します(RFC 8660)。実際には、すべてのルータに同じブロックを与え、1 つのラベルがどこでも同じ
プレフィックスを指すようにします。隣接 SID とバインディング SID は別の範囲から来ます。動的に割り当てるものや、手で
設定するものは、**SR ローカル ブロック**(SRLB、既定で 15000〜15999)からです。

プレフィックス SID は、1 つ手前のルータにしてほしいことをフラグで伝えます。**N** はノード SID の印、**P**(no PHP)は
ラベルを外さないよう求め、**E** は代わりに explicit null を付けるよう求めます(RFC 8667)。IOS XR では、プレフィックス SID の
`explicit-null` がそれらを立てます。何も立っていなければ PHP で、2.2 節のとおり 1 つ手前で外れます。

## 3. IOS XR の IS-IS で SR を動かす

### 3.1 設定の置き場

置き場は 3 つです。

- ブロック: `segment-routing` → `global-block <先頭> <末尾>`。無ければ既定値が使われます。ガイドは、IGP の下ではなく
  ここで設定するよう勧めています。
- IGP での SR: `router isis <インスタンス>` → `address-family ipv4 unicast` → `segment-routing mpls`。SR の情報は IS-IS の
  拡張 TLV の中で運ばれるので、ワイド メトリック(`metric-style wide`)が要ります。
- プレフィックス SID: `router isis <インスタンス>` → `interface Loopback0` → `address-family ipv4 unicast` →
  `prefix-sid index <n>`(または `absolute <ラベル>`)。

IOS XR は、コミットのときに順序を検査します。アドレス ファミリーで SR が有効になっていないと、プレフィックス SID は
拒否されます。

```console
router isis CORE
 interface Loopback0
  address-family ipv4 unicast
   prefix-sid index 1
!!% Feature not supported: Segment-routing is not enabled for IPv4 Unicast
```

IOS XE はやり方が違います。SR は全体のモード `segment-routing mpls` で有効にし、ルータ自身のループバックのプレフィックス
SID は、そこにある表 `connected-prefix-sid-map` → `address-family ipv4` に `10.255.0.12/32 index 12 range 1` のように
書きます。IS-IS には `router isis` の下の `segment-routing mpls` だけが要ります。ラボの IOS ルータはそのように設定されています。

ここまでの置き場を、XR01 の設定としてまとめると次の形です。右の列は、その行が何をするかです。ブロックは既定値(16000〜23999)のままなので、`segment-routing` の行は要りません。続けて、ラボの IOS XE ルータ(RT02)の SR の部分を載せます。同じ部品が、別の場所にあります。

:::config fold XR01(IOS XR)— IS-IS で SR を動かす最小の形
router isis CORE
 is-type level-2-only
 net 49.0001.0100.0000.0001.00
 address-family ipv4 unicast
  metric-style wide      ## SR の情報は IS-IS の拡張 TLV に載るので、ワイド メトリックが前提(ラボでは最初から入っている)
  segment-routing mpls   ## この IS-IS で SR を使う。ブロックと SID をアドバタイズし、SR のラベルを転送テーブルに入れる
 !
 interface Loopback0
  passive                ## ループバックでは隣接を作らない(アドレスはアドバタイズする)
  address-family ipv4 unicast
   prefix-sid index 1    ## XR01 の番号。どのルータもブロックの先頭にこれを足した 16001 を、XR01 宛てのラベルにする
  !
 !
!
:::

:::config RT02(IOS XE)— ラボの据え付けの設定から、SR の部分の抜粋
segment-routing mpls                 ## SR-MPLS を全体で有効にする。IOS XE では IGP の SR より先に要る
 !
 set-attributes
  address-family ipv4
   sr-label-preferred                ## LDP と SR の両方のラベルがあれば、SR のほうを積む(4.1 節)
  exit-address-family
 !
 connected-prefix-sid-map
  address-family ipv4
   10.255.0.12/32 index 12 range 1   ## 自分のループバックの番号(16012)。range 1 = このプレフィックス 1 つだけ
  exit-address-family
!
router isis CORE
 net 49.0001.0100.0000.0012.00
 is-type level-2-only
 metric-style wide                   ## IOS XR と同じく前提
 segment-routing mpls                ## この IS-IS で SR の情報をアドバタイズする
!
:::

IOS XR の OSPF にも、同じ 3 つの部品があります(`router ospf` の下の `segment-routing mpls`、エリアのループバックの下の
プレフィックス SID)。ブループリントの 3 つ目の制御プレーンは BGP です。ラベル付きユニキャストのルートにプレフィックス SID
を付けられ(`segment-routing` と、ルート ポリシーでのラベル インデックス)、IGP のドメインをまたいで SR を運びます。

### 3.2 ルータがアドバタイズするもの

各ルータは、ブロックをルータ能力 TLV で、プレフィックス SID をプレフィックスと一緒に、隣接 SID をリンクと一緒に
アドバタイズします。課題 M10-1 の後の XR01 です。

```console
RP/0/RP0/CPU0:XR01#show isis database verbose XR01.00-00
...
  Router Cap:     10.255.0.1 D:0 S:0
    Segment Routing: I:1 V:0
    SRGB Base: 16000 Range: 8000
    Node Maximum SID Depth:
      Label Imposition: 10
  Metric: 10         IS-Extended RT01.00
    ADJ-SID: F:0 B:0 V:1 L:1 S:0 P:0 weight:0 Adjacency-sid:24011
  Metric: 100        IS-Extended RT03.00
    ADJ-SID: F:0 B:0 V:1 L:1 S:0 P:0 weight:0 Adjacency-sid:24013
  Metric: 0          IP-Extended 10.255.0.1/32
    Prefix-SID Index: 1, Algorithm:0, R:0 N:1 P:0 E:0 V:0 L:0
```

`SRGB Base: 16000 Range: 8000` がブロック、`Prefix-SID Index: 1` が XR01 の番号、`N:1` がノード SID の印です。IOS XR の
隣接 SID は動的なラベル(24011、24013)で、IOL ルータのものは IOS の動的な範囲から取った小さな数(22〜27)です。
XR01 は全ルータの番号からラベルの表を作り、転送テーブルにエントリを入れます。2.1 節の表を、XR01 が実際に作ったものです。

```console
RP/0/RP0/CPU0:XR01#show isis segment-routing label table
IS-IS CORE  IPv4 Unicast  IS Label Table
Label         Prefix                   Algorithm    Interface
----------    ----------------         ---------    ---------
16001         10.255.0.1/32            SPF          Loopback0
16011         10.255.0.11/32           SPF
16012         10.255.0.12/32           SPF
16013         10.255.0.13/32           SPF

RP/0/RP0/CPU0:XR01#show mpls forwarding | include "160[0-9][0-9]"
16001  Aggregate   SR Pfx (idx 1)     default                      0
16011  Pop         SR Pfx (idx 11)    Gi0/0/0/0    10.0.1.11       0
16012  16012       SR Pfx (idx 12)    Gi0/0/0/0    10.0.1.11       0
16013  Pop         SR Pfx (idx 13)    Gi0/0/0/1    10.0.3.13       0
```

16012 で受けたら 16012 のまま RT01 へ、が 2.1 節のエントリです。隣のルータのラベル(16011 と 16013)は `Pop` です。
XR01 自身がそれらの 1 つ手前だからです(2.3 節の手順 1 と同じ)。

### 3.3 小さすぎるブロック

ブロックには、ドメインのすべての番号が収まらなければなりません。ルータは、全ルータの番号を自分のブロックでラベルに
変えるからです。番号が収まらないと、IOS XR はそのプレフィックスの SR のエントリをまったく作りません。

ラボ XRT-10 は、変更 CHG-1301 が残したそのようなブロック、16000〜16009(「10 台に 10 個のラベル」)で始まります。
IOS ルータの番号 11〜13 は収まりません。XR01 のラベルの表には自分のプレフィックスだけが並び、XR01 は LDP のラベルで
送り続けます。XR01 には理由を示すログが出ません。警告するのは隣のルータです。XR01 へ送るラベルを XR01 のブロックで
計算しようとして、XR01 の LSP に小さな範囲を見つけます。

```console
RT01#show logging | include SID
*Oct 29 22:49:45.984: %CLNS-4-SIDRANGE: Prefix-sid index 13 for 10.255.0.13/32 is out of SRGB range 10 via 10.0.1.1
```

ブロックの変更は、新しいラベルが空いていれば、再起動なしですぐに効きます。IS-IS が変更をログに出します。

```console
%ROUTING-ISIS-6-SRGB_INFO : ISIS (CORE): SRGB (index 0, 16000 23999, SRGB_ALLOCATED, 0x1) modified to (16000 16009), global cfg change, disabling SR
%ROUTING-BGP-2-SR_CFG_CHANGED : SRGB range config has been changed. BGP's labels have to be re-programmed as per new range, 'process restart bgp' needed
%ROUTING-ISIS-6-SRGB_INFO : ISIS (CORE): SRGB (index 0, 16000 16009, SRGB_ALLOCATED, 0x0) allocation complete, enabling SR
```

BGP の行が関係するのは、BGP がプレフィックス SID を使うときだけです。ガイドは、ブロックの変更は通信を乱し、新しい
ラベルが既に使われていれば再起動が要ると警告しています。ラボではラベルが空いていて、変更は約 5 秒で済みます。

:::try
LDP が無くなった後で、もう一度ブロックを縮めます。課題 M10-2 の後に行います。

1. XR01 の `segment-routing` の下で `global-block 16000 16009` を設定してコミットします。
2. XR01 で `show isis segment-routing label table`、`show cef vrf CUST-A 10.101.2.0/24 detail`、`show logging last 10` を、
   CEA1 で `ping 10.101.2.1 source Loopback10` を、RT01 で `show logging | include SID` を実行します。
3. 行を外して(`no global-block`)コミットし、同じコマンドをもう一度実行します。

結果の例: 15 秒以内に、XR01 のラベルの表には自分のプレフィックス(16001)だけが残りました。CEF では両方の顧客の
VPN のルートが `unresolved` と `drop adjacency` になり、顧客 A の SR ポリシーは `Last error: unresolved first label (16013)` で
down になりました。CEA1 と CEB1 からサイト 2 への ping は失敗し(0 percent)、RT01 は
`%CLNS-4-SIDRANGE: Prefix-sid index 13 for 10.255.0.13/32 is out of SRGB range 10 via 10.0.1.1` をログに出しました。行を外すと、
15 秒以内にラベルの表はそろい、ping は成功しました。
:::

## 4. LDP から SR へ

### 4.1 1 つのプレフィックスに 2 つのラベル

SR と LDP は、問題なく並んで動きます。ラベルを別々の範囲から取り、別々のプロトコルでアドバタイズするからです。ただし、
あるプレフィックスに両方のラベルを持つルータは、パケットにどちらを付けるかを選ばなければなりません。RFC 8661 は、
既定では LDP のラベルを選ぶべきだとしていて、IOS XR はそうします。

そのため、IS-IS で SR を有効にしただけでは、XR01 は LDP のラベルで送り続けます。RT02 に向けては RT01 の LDP の
ラベルのままです(ある構築では `labels imposed {18}`。LDP のラベルは構築のたびに変わります)。IS-IS のアドレス ファミリー
の `segment-routing mpls sr-prefer` が、この選択を逆にします。

```console
RP/0/RP0/CPU0:XR01#show cef 10.255.0.12/32 detail
10.255.0.12/32, version 118, labeled SR, internal 0x1000001 0x8310 (ptr 0x1063c048) [1], 0x600 (0x107d52d8), 0xa28 (0xf1546f8)
...
   via 10.0.1.11/32, GigabitEthernet0/0/0/0, 6 dependencies, weight 0, class 0 [flags 0x0]
    next hop 10.0.1.11/32
    remote adjacency
     local label 16012      labels imposed {16012}
```

IOS XE で同じことをするのは、`segment-routing mpls` → `set-attributes` → `address-family ipv4` → `sr-label-preferred` です。
VPN のルートは、何もしなくてもついてきます。VPN のルートはネクスト ホップのループバックへのラベルを通して解決される
ので、顧客 A のサイト 2 へのトラフィックは、VPN のラベルの上に RT02 のプレフィックス SID を積んで出ていきます(その構築
では `{16012 26}`)。

移行の間は、しばらく両方のプロトコルが共存します。2 つの向きが同時に切り替わる必要はありません。次のホップがまだ SR を
動かしていなければ、IOS ルータは 2 つを自分でつなぎさえします。XR01 が SR を動かす前、RT01 は、XR01 を通る RT03 宛ての
トラフィックを XR01 の LDP のラベルで送っていました。

逆に、SR だけを動かすルータは、SID を持たないルータに到達できません。それを解くのが**マッピング サーバ**で、SID を
持てないルータに代わって SID をアドバタイズします(`segment-routing` → `mapping-server` → `prefix-sid-map`、IS-IS では
`segment-routing prefix-sid-map advertise-local` でアドバタイズ)。IOS XR のガイドと RFC 8661 は、それが要るのは SR から
LDP への向きだけだとしています。

:::try
既定の優先を見ます。課題 M10-1 の後、LDP がまだ動いている間に行います。

1. XR01 の `router isis CORE` → `address-family ipv4 unicast` の下で、`segment-routing mpls sr-prefer` を
   `segment-routing mpls` に置き換えてコミットします。
2. XR01 で `show cef 10.255.0.12/32 detail` と `show cef vrf CUST-A 10.101.2.0/24 detail` を実行します。
3. `sr-prefer` を戻してコミットし、同じコマンドを実行します。

結果の例: コミットから 15 秒以内に、XR01 は RT01 の LDP のラベルに戻りました。RT02 に向けて `labels imposed {18}`、
顧客 A のルートは `{18 26}` です。`sr-prefer` を戻すと、再び `{16012}` と `{16012 26}` を表示しました(LDP のラベルと VPN の
ラベルはある構築のもので、構築のたびに変わります)。
:::

### 4.2 LDP を止める

LDP のラベルを使うものが無くなれば、LDP は外せます。`no mpls ldp` の 1 行で XR01 の LDP は止まり、VPN のトラフィックは
SR のラベルで流れ続けます。

ただし、LDP-IGP 同期(M8)の設定は IS-IS の下に残り、働き続けます。同期は「リンクの上で LDP が上がっているときだけ、
そのリンクを通常のメトリックでアドバタイズする」機能です。XR01 のどこにも LDP が無くなると、IOS XR は両方のコアの
リンクを最大のメトリックでアドバタイズします。

```console
RP/0/RP0/CPU0:XR01#show isis database verbose XR01.00-00 | include IS-Extended
  Metric: 16777214   IS-Extended RT01.00
  Metric: 16777214   IS-Extended RT03.00
```

ラボでは何も壊れません。XR01 には他に入り口が無く、顧客のトラフィックは通り続けるからです。もっと大きなネットワーク
なら、他のルータは XR01 のリンクを避け、TI-LFA の迂回の道も誤ったメトリックで計算されることになります。2 つの
インターフェイスから `mpls ldp sync` を外すと、10 と 100 に戻ります。

IOS は振る舞いが違います。IOS の同期は、LDP が設定されていないリンクを対象から外します。インターフェイスに
`no mpls ip` があると、`show mpls ldp igp sync` は「LDP not configured」と表示し、メトリックは通常のままです。リンクに LDP が
設定されたまま相手を失っている間は、IOS XR と同じくメトリックは最大になります。ラボの IOS ルータは、XR01 とのリンクに
`no mpls ldp igp sync` を入れて準備してあり、XR01 が先に LDP を止められるようにしてあります。

移行を終えた XR01 の IS-IS の全体です(課題 M10-1 と M10-2 を終えた状態)。`mpls ldp` の塊は丸ごと無くなり、インターフェイスからは `mpls ldp sync` が消えています。BFD の行は単元 M7 のものです。

:::config fold XR01 — 移行を終えた IS-IS の全体
router isis CORE
 is-type level-2-only
 net 49.0001.0100.0000.0001.00
 log adjacency changes
 address-family ipv4 unicast
  metric-style wide
  segment-routing mpls sr-prefer    ## SR を有効にし、LDP のラベルもある間は SR のほうを積む(4.1 節)
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
   prefix-sid index 1               ## XR01 宛ては 16001
  !
 !
 interface GigabitEthernet0/0/0/0   ## PRIMARY(RT01 へ)
  bfd minimum-interval 100          ## 単元 M7 の BFD。障害に気づく速さを決める(ページ「TI-LFA」の 3 節)
  bfd multiplier 3
  bfd fast-detect ipv4
  point-to-point
  address-family ipv4 unicast
   metric 10                        ## `mpls ldp sync` はもう無い。残すと 16777214 でアドバタイズされる
  !
 !
 interface GigabitEthernet0/0/0/1   ## BACKUP(RT03 へ)
  bfd minimum-interval 100
  bfd multiplier 3
  bfd fast-detect ipv4
  point-to-point
  address-family ipv4 unicast
   metric 100
  !
 !
!
:::

:::try
わざと同期を残します。課題 M10-2 の後に行います。

1. XR01 の `router isis CORE` → `interface GigabitEthernet0/0/0/1` → `address-family ipv4 unicast` の下に `mpls ldp sync` を
   足してコミットします。
2. XR01 で `show isis database verbose XR01.00-00` を、RT02 で `show isis database verbose XR01.00-00` と
   `show ip route 10.255.0.1` を実行します。
3. 行を外してコミットします。

結果の例: XR01 は RT03 へのリンクを 16777214、RT01 へのリンクを 10 でアドバタイズしました。RT02 も XR01 の LSP で
同じものを見て、10.255.0.1 へのルートは RT01 経由のメトリック 20 のまま、自分の TI-LFA の迂回の道は RT03 経由でした。
行を外すと、RT03 へのリンクのメトリックは 100 に戻りました。
:::

## 5. コマンド名

| IOS XE では | IOS XR では |
|---|---|
| `segment-routing mpls`(全体。IGP の SR より先に要る) | `segment-routing`(ブロック)+ IS-IS のアドレス ファミリーの `segment-routing mpls` |
| `segment-routing mpls` → `global-block` | `segment-routing` → `global-block` |
| `connected-prefix-sid-map` → `address-family ipv4` → `<プレフィックス> index <n> range 1` | IS-IS のループバックの下の `prefix-sid index <n>` |
| `set-attributes` → `address-family ipv4` → `sr-label-preferred` | IS-IS のアドレス ファミリーの `segment-routing mpls sr-prefer` |
| `show isis segment-routing` | `show isis segment-routing label table` |
| `show mpls forwarding-table labels <ラベル>` | `show mpls forwarding labels <ラベル>` |

## 実践

ラボ **XRT-10** に行き、課題 M10-1 と M10-2 に取り組みます。XR01 は IOS XRv 9000 なので、ラボの構築には 10 分ほどかかります。
終わったら、次のページ「TI-LFA」に進みます。

<p class="tolab"><a href="/_learn?id=XRT-10">ワークスペースでラボ XRT-10 を開く</a> — <a href="a1-m10-practice.html">課題</a></p>

:::note
このページの出力は、IOS XRv 9000 26.1.1(XR01)、IOS XRd 26.1.1(XR02)、IOL 上の IOS XE 17.15(他のルータ)で取得しました。
出典: Segment Routing Configuration Guide for the ASR 9000, IOS XR 26.1.x–26.3.x(2026。SRGB と SRLB、IS-IS の SR、マッピング
サーバ)とそのコマンド リファレンス(2025)。Cisco 8000 の SR のガイド、リリース 24.x(IS-IS)。IOS XE Segment Routing
Configuration Guide(2026。IS-IS の SR)。TAC の文書「Segment Routing Overview and Migration Guidelines」(2020)。RFC 8402、
8660、8661、8667、8669。いずれも 2026 年 10 月に確認しました。次のものは、ラボ XRT-10 とその PoC での測定によります。
traceroute のラベル、コミットのエラー、出力、小さすぎるブロックとブロックの変更にかかる時間、LDP の既定の優先、残った同期です。
:::
