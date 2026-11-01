# M11 — E-Line と疑似回線

この単元では、顧客のイーサネットのフレームを、ルーティングに触れずにそのままコアの向こうへ運ぶサービス、
**L2VPN** を扱います。CCNP Service Provider のブループリントの 4.2(L2VPN とキャリア イーサネット)と 4.1.a(EVPN)にあたります。
単元は 3 つのページと付録に分かれています。

| ページ | 中身 | 課題 |
|---|---|---|
| このページ | L2VPN で何が嬉しいか、フレームをラベルに包む仕組み、LDP の疑似回線 | M11-1、M11-2 |
| EVPN-VPWS | 疑似回線を BGP で作る | M11-3、M11-4 |
| Q-in-Q | 顧客の VLAN をまとめて運ぶ | M11-5 |
| 付録 | E-LAN、E-Tree、マルチホーム、イーサネット OAM、G.8032、802.1ah | — |

ラボは XRT-11 です。ラボ XRT-10 の続きで、同じ四角形のコア、同じ VPN の顧客、M10 の課題を終えた XR01 と XR02 です。
新しいプロバイダー エッジ(PE)の XR03 が RT01 の先に加わり、顧客 B のサイト 3 を収容しています。出力は IOS XRv 9000 26.1.1
(XR01、XR03)、IOS XRd 26.1.1(XR02)、IOL 上の IOS XE 17.15(他のルータ)で取得しました。

:::topo
nodes:
  CEA1: {at: [0, 1.1], label: "CEA1 (A, site 1)"}
  CEB1: {at: [0, 2.3], label: "CEB1 (B, site 1)"}
  XR01: {at: [1.6, 1.7], label: "XR01 (PE)"}
  RT01: {at: [3.2, 1.0], label: "RT01 (P)"}
  RT03: {at: [3.2, 2.4], label: "RT03 (P)"}
  XR02: {at: [3.2, 3.5], label: "XR02 (RR, PCE)"}
  RT02: {at: [4.8, 1.7], label: "RT02 (PE)"}
  XR03: {at: [4.8, 0.2], label: "XR03 (PE, new)"}
  CEA2: {at: [6.4, 1.3], label: "CEA2 (A, site 2)"}
  CEB2: {at: [6.4, 2.2], label: "CEB2 (B, site 2)"}
  CEB3: {at: [6.4, 0.2], label: "CEB3 (B, site 3)"}
links:
  - [CEA1, XR01, "L3VPN + VLAN 100"]
  - [CEB1, XR01, "L3VPN + VLANs"]
  - [XR01, RT01, "PRIMARY 10"]
  - [XR01, RT03, "BACKUP 100"]
  - [RT01, RT02, "CORE-A 10"]
  - [RT03, RT02, "CORE-B 100"]
  - [RT03, XR02, "RR-LINK 10"]
  - [RT01, XR03, "CORE-C 10"]
  - [RT02, CEA2, "L3VPN + VLAN 200"]
  - [RT02, CEB2, "L3VPN + VLANs"]
  - [XR03, CEB3, "VLANs"]
frames:
  - {label: "AS 65000 (IS-IS CORE, SR-MPLS)", nodes: [XR01, RT01, RT03, RT02, XR02, XR03]}
:::

コアのリンクの数字は IS-IS のメトリックです。顧客 A と B のサイト 1・2 は、M9 からのレイヤ 3 VPN をタグなしで使ったまま、
同じポートのタグ付きのサブインタフェースで L2VPN を足します。サイト 3 は L2VPN だけです。

## 1. 何が嬉しいのか

### 1.1 L3VPN では足りないとき

M9 の L3VPN では、プロバイダーが顧客のルーティングに加わります。PE は顧客と BGP を話し、顧客のルートを VRF に入れて、
コアの向こうへ広告しました。顧客から見ると、プロバイダーは 1 台の大きなルータです。

これでは困る顧客がいます。自社のルータどうしで OSPF や IS-IS を直接話したい、自社のルーティングの設計をプロバイダーに
見せたくない、IP 以外のフレームも運びたい、あるいは、拠点どうしを同じ VLAN でつなぎたい、という顧客です。
こうした顧客が欲しいのは「拠点どうしを 1 本のイーサネットのケーブルでつないだのと同じ」サービスです。

### 1.2 以前の手

プロバイダーは以前、拠点の間に専用線を引くか、フレーム リレーや ATM の仮想回線を売っていました。どちらも、コアとは
別の網と機器を持つことになります。

イーサネットの時代になると、メトロ イーサネットのスイッチで顧客ごとに VLAN を割り当てる手が広まりました。ところが VLAN の
番号は 4094 個しかなく、プロバイダーの網全体がスパニング ツリーの 1 つの領域になります。網が大きくなるほど、番号は足りず、
障害の影響は広がります。

### 1.3 MPLS の答え: フレームをラベルに包む

MPLS のコアは、ラベルの付いたパケットなら中身が何であっても運びます。M9 では IP パケットにラベルを付けました。同じように、
顧客のイーサネットのフレームを丸ごとラベルで包めば、コアは何も知らないまま、それを向こうの PE へ運びます。
この包んだ通り道を**疑似回線**(pseudowire、PW)と呼びます。

コアの中に VLAN もスパニング ツリーもありません。顧客の VLAN の番号はポートの中でだけ意味を持つので、顧客ごとに同じ番号を
使っても構いません。コアのラベルは、M10 の SR のものがそのまま使えます。

### 1.4 サービスの型

イーサネットのサービスは、つなぐ相手の数で型が分かれます(MEF の定義)。

| 型 | つなぎ方 | 仕組みの例 | このラボの XR |
|---|---|---|---|
| E-Line | 2 地点を 1 対 1 | 疑似回線(LDP)、EVPN-VPWS | 実践する |
| E-LAN | 多地点を互いに | VPLS、EVPN の E-LAN | 付録だけ |
| E-Tree | 根と葉。葉どうしは通さない | EVPN の E-Tree | 付録だけ |
| E-Access | 顧客と、別の事業者の網の境界 | E-Line の一種 | 付録だけ |

E-Line を作る仕組みを、IETF では **VPWS**(Virtual Private Wire Service)と呼びます。このラボの IOS XRv 9000 は、L2VPN のうち
VPWS だけを実行します。`show l2vpn capability` が `VPLS allowed: N`、`VPWS allowed: Y` と表示し、ブリッジ ドメインの設定は
コミットで拒否されます。そのため、E-LAN などは付録で扱います。

## 2. 仕組み: フレームをラベルに包む

### 2.1 アタッチメント回線と疑似回線

E-Line は 3 つの部品でできています。

- **アタッチメント回線**(AC): 顧客の CE と PE をつなぐ区間です。ここでは、ポートのうち特定の VLAN のフレームを拾う
  サブインタフェースです。
- **疑似回線**: PE と PE の間で、コアを通ってフレームを運ぶ区間です。両端の PE が、同じ番号(**PW ID**、VC ID とも呼びます)で
  同じ疑似回線だと確かめ合います。
- **クロスコネクト**: PE の中で、AC と疑似回線をつなぎます。AC から入ったフレームは疑似回線へ、疑似回線から来たフレームは
  AC へ出ます。MAC アドレスは見ません。

顧客 A の E-Line(課題 M11-1)では、XR01 の AC は CEA1 の VLAN 100、RT02 の AC は CEA2 の VLAN 200 で、疑似回線の
PW ID は 100 です。

### 2.2 1 ホップずつ: CEA1 から CEA2 へ

CEA1 が VLAN 100 で送ったフレームが CEA2 に届くまでを追います。ラベルの値は、ラボのある構築で測ったものです
(疑似回線のラベルは構築のたびに変わります)。

:::topo
nodes:
  CEA1: [0, 1]
  XR01: [1.5, 1]
  RT01: [3, 1]
  RT02: [4.5, 1]
  CEA2: [6, 1]
links:
  - [CEA1, XR01, "tag 100 | IP"]
  - [XR01, RT01, "16012 | 16 | frame"]
  - [RT01, RT02, "16 | frame"]
  - [RT02, CEA2, "tag 200 | IP"]
:::

1. XR01 は、VLAN 100 のフレームを AC で拾い、タグを外します。
2. 疑似回線のラベル **16** を付けます。これは RT02 が「この疑似回線のフレームは 16 を付けて送ってくれ」と XR01 に伝えた値です。
3. その外側に、RT02 へのトランスポートのラベル **16012**(RT02 のプレフィックス SID。M10)を付け、PRIMARY へ送ります。
4. RT01 は 16012 を見て RT02 へ送ります。RT02 の 1 つ手前なので、16012 を外します。
5. RT02 は 16 を見て、それが CEA2 向きの疑似回線だと分かります。ラベルを外し、AC の VLAN 200 のタグを付けて CEA2 へ送ります。

逆向きでは、RT02 が `{16001 24031}` を付けます。16001 は XR01 へのトランスポート、24031 は XR01 が RT02 に伝えた疑似回線の
ラベルです。疑似回線のラベルは、受け取る側が決めます。L3VPN の VPN のラベルと同じ考え方です。

### 2.3 疑似回線のラベルを配る: targeted LDP

疑似回線のラベルは、両端の PE が LDP で交換します。隣り合っていない PE どうしなので、LDP はリンクではなく相手のループバックに
直接 hello を送ります。これを **targeted LDP** と呼びます。交換する内容は次のとおりです(RFC 8077 の FEC 128)。

- **PW ID**: 両端で同じでなければ、組になりません。
- **ラベル**: 相手に付けてほしい疑似回線のラベル。
- **インタフェースのパラメータ**: AC の **MTU** と、フレームの扱い(**PW タイプ**)、**コントロール ワード**の有無。

IOS XR 26.1.1 は、`mpls ldp` の設定が無くても、疑似回線の相手とは targeted のセッションを張りました。ラボの XR01 は、
M10-2 で LDP を外したままです。それでも、疑似回線を設定すると RT02 とのセッションが上がり、疑似回線を外すとセッションは
消えました。`show mpls ldp summary` は `Interfaces: 0 LDP configured` を表示します。コアのリンクでは LDP は動かず、
トランスポートのラベルは SR のままです。

### 2.4 タグの扱い: rewrite と PW タイプ

AC のサブインタフェースは、どの VLAN のフレームを拾うか(`encapsulation`)と、拾ったフレームのタグをどうするか(`rewrite`)を
決めます。IOS XR の既定では、タグは**そのまま残ります**。

- `rewrite ingress tag pop 1 symmetric`: 入るときに外側のタグを 1 枚外し、出るときに同じタグを付け直します。
  疑似回線の中を通るのはタグの無いフレームなので、両端の VLAN が違っても構いません。
- `rewrite ingress tag translate 1-to-1 dot1q <VLAN> symmetric`: タグの番号を付け替えます。
- `rewrite ingress tag push dot1q <VLAN> symmetric`: タグを 1 枚足します。

`symmetric` は、入りと出で逆の操作をするという意味で、IOS XR ではこれしか選べません。

疑似回線の中のフレームの形は、**PW タイプ**で取り決めます。IOS XR の既定はタイプ 5(Ethernet)で、フレームをそのまま
運びます。`transport-mode vlan` にするとタイプ 4(Ethernet VLAN)になり、VLAN のタグが付いていることを前提にします。
両端の PW タイプが違うと疑似回線は上がりません。XR 同士では `Error: PW type mismatched` で down になりました。IOS XE は
相手に合わせる(autosense)ので、相手が IOS XE だとこの食い違いは表に出ませんでした。

### 2.5 MTU: 3 つの数

E-Line では、MTU が 3 か所で効きます。

- **AC の MTU**: 両端の PE が LDP で伝え合い、**違うと疑似回線は上がりません**。IOS XR の AC の MTU は、親のポートの MTU から
  イーサネットのヘッダ(14 バイト)を引き、外さずに残すタグ 1 枚ごとに 4 バイトを足した値です。ポートが既定の 1514 なら、
  `pop 1` の AC は 1500、タグを残した AC は 1504 です。IOS XE は L2 のヘッダを数えずに 1500 と伝えます。
- **ポートの MTU**: 親のポートの MTU を上げると、そのポートのすべての AC の MTU が上がります。サブインタフェースの `mtu` は
  親を超えられず、ラボでは 9018 と設定しても AC は 1500 のままでした。
- **コアの MTU**: 包んだフレームは、顧客のパケットにイーサネットのヘッダ(14)とラベル(1 枚 4)を足した大きさになり、
  コアで分割はされません。ラボのコアは 1500 なので、DF ビット付きで通るのは IP で 1478 バイトまででした(1478 + 14 + 8 = 1500)。
  実際の網では、コアの MTU を顧客の MTU より大きくします。IOL のイーサネットは MTU を変えられないので、このラボでは扱いません。

## 3. IOS XR で E-Line を作る

### 3.1 設定の置き場

E-Line は、AC のサブインタフェースと、`l2vpn` の下のクロスコネクトの 2 か所に書きます。

:::config fold XR01(IOS XR)— LDP の疑似回線の E-Line(課題 M11-1 の答え)
interface GigabitEthernet0/0/0/2.100 l2transport   ## l2transport= L3 の IF ではなく AC として使う。IP アドレスは持てない
 encapsulation dot1q 100                           ## このポートで VLAN 100 のフレームを拾う
 rewrite ingress tag pop 1 symmetric               ## 入るときにタグを外し、出るときに付け直す。疑似回線にはタグなしで載る
!
l2vpn
 xconnect group CUST-A                             ## クロスコネクトをまとめる名前(自由)
  p2p A-100                                        ## 1 本の E-Line(名前は自由)
   interface GigabitEthernet0/0/0/2.100            ## 一方の端= AC
   neighbor ipv4 10.255.0.12 pw-id 100             ## もう一方の端= RT02 との疑似回線。PW ID は両端で同じ
   !
  !
 !
!
:::

`mpls ldp` は書いていません。2.3 節のとおり、IOS XR は疑似回線の相手と targeted のセッションを自分で張ります。

:::config RT02(IOS XE)— ラボの据え付けの設定から、顧客 A の E-Line の部分
interface Ethernet0/2.200                          ## CEA2 の VLAN 200 を拾うサブインタフェース(親のポートは L3VPN)
 encapsulation dot1Q 200
 xconnect 10.255.0.1 100 encapsulation mpls        ## XR01 への疑似回線(PW ID 100)。サブインタフェースの xconnect はタグを外して運ぶ
!
:::

IOS XE には、EVC(`service instance`)と `l2vpn xconnect context` を使う新しい書き方もあります。ラボの RT02 は、
サブインタフェースに `xconnect` を書く古い書き方です。どちらでも、XR とは PW タイプ 5 でつながりました。

### 3.2 状態の読み方

`show l2vpn xconnect` は、E-Line ごとに 1 行を表示します。AC(Segment 1)と疑似回線(Segment 2)の両方が UP のときに、
E-Line 全体が UP になります。

```console
RP/0/RP0/CPU0:XR01#show l2vpn xconnect
XConnect                   Segment 1                       Segment 2
Group      Name       ST   Description            ST       Description            ST
------------------------   -----------------------------   -----------------------------
CUST-A     A-100      UP   Gi0/0/0/2.100          UP       10.255.0.12     100    UP
```

詳細(`show l2vpn xconnect detail`)では、両端が伝え合った値が Local と Remote の列に並びます。上がらないときは、この表の
どの行が食い違っているかを見ます。

```console
  PW: neighbor 10.255.0.12, PW ID 100, state is up ( established )
    PW type Ethernet, control word disabled, interworking none
      MPLS         Local                          Remote
      ------------ ------------------------------ -----------------------------
      Label        24031                          16
      MTU          1500                           1500
      Control word disabled                       disabled
      PW type      Ethernet                       Ethernet
```

RT02 では `show l2vpn atom vc` と `show l2vpn atom vc vcid 100 detail` で同じことが分かります。詳細の
`imposed label stack {16001 24031}` は、RT02 が付ける 2 枚のラベル(2.2 節)です。

### 3.3 上がらないときの読み方

疑似回線が上がらないとき、IOS XR の詳細の最後に `Error:` の行が出ます。ラボで起こした食い違いと、その表示です。

| 食い違い | XR の表示(相手も XR) | 相手が IOS XE のとき |
|---|---|---|
| AC の MTU(ポートの MTU、タグを外し忘れた AC) | `Error: MTU mismatched` | IOS XE も `Last error: Pseudowire MTU mismatch with peer` |
| PW タイプ(片側だけ `transport-mode vlan`) | `Error: PW type mismatched` | IOS XE が合わせて up |
| コントロール ワード(片側だけ有効) | `Error: illegal control word` | IOS XE が合わせて up |
| PW ID | 相手のラベルが届かず、`Remote` の列が空のまま | 同じ |

同じ `MTU mismatched` でも原因は 1 つではありません。ポートの MTU を上げた AC と、タグを外し忘れた AC は、どちらも
この表示になります。MTU の列の数字(9000 か 1504 か)を見れば、どちらかが分かります。

:::try
タグを外し忘れた AC が、疑似回線をどう止めるかを見ます。課題 M11-1 の後に行います。

1. XR01 で、`interface GigabitEthernet0/0/0/2.100 l2transport` の下の `rewrite ingress tag pop 1 symmetric` を外してコミットします。
2. XR01 で `show l2vpn xconnect detail`、RT02 で `show l2vpn atom vc vcid 100 detail` を実行し、CEA1 から `ping 172.31.10.2` を実行します。
3. rewrite を戻してコミットし、同じコマンドをもう一度実行します。

ラボで測った結果: XR01 の AC の MTU は 1504 になり、疑似回線は `Error: MTU mismatched` で down になりました(RT02 は
`Last error: Pseudowire MTU mismatch with peer`、MTU の列は 1500 と 1504)。ping は失敗しました。戻すと 30 秒以内に up になりました。
:::

## 4. コマンド名

| IOS XE では | IOS XR では |
|---|---|
| サブインタフェースの `encapsulation dot1Q <VLAN>` + `xconnect <相手> <VC ID> encapsulation mpls` | `interface … l2transport` + `l2vpn` → `xconnect group` → `p2p` → `interface` と `neighbor ipv4 <相手> pw-id <ID>` |
| `service instance <n> ethernet` → `rewrite ingress tag pop 1 symmetric` | `l2transport` のサブインタフェースの `rewrite ingress tag pop 1 symmetric` |
| `show l2vpn atom vc [vcid <ID> detail]` | `show l2vpn xconnect [detail]` |
| `show mpls l2transport vc`(古い書き方) | `show l2vpn xconnect` |
| `show mpls ldp neighbor` | `show mpls ldp neighbor brief`、`show mpls ldp discovery` |

## 実践

ラボ **XRT-11** に行き、課題 M11-1 と M11-2 に取り組みます。XR01 と XR03 は IOS XRv 9000 なので、ラボの構築には 15 分ほど
かかります。終わったら、次のページ「EVPN-VPWS」に進みます。

<p class="tolab"><a href="/_learn?id=XRT-11">ワークスペースでラボ XRT-11 を開く</a> — <a href="b1-m11-practice.html">課題</a></p>

:::note
出典: L2VPN and Ethernet Services Configuration Guide for the ASR 9000, IOS XR 25.x(2025。ポイントツーポイントのレイヤ 2 サービス、
キャリア イーサネットのモデル)と、そのコマンド リファレンス。IOS XRv 9000 のリリース ノート 24.1.1(対応する L2VPN は VPWS)。
IOS XE 17 の MPLS Configuration Guide(Any Transport over MPLS、L2VPN Protocol-Based CLIs)。TAC の文書「MTU Behavior on Cisco IOS XR
and Cisco IOS Routers」(116350)と「Understand IOS XR L2VPN Services and Features」(116453)。RFC 8077、4448。いずれも 2026 年 11 月に
確認しました。次のものは、ラボ XRT-11 とその PoC での測定によります。ラベル、LDP の設定なしでの targeted のセッション、
AC の MTU の値、サブインタフェースの MTU が効かないこと、DF 付きで通る大きさ、食い違いごとの表示です。
:::
