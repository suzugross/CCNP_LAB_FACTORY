# M10 — SR ポリシーと PCE

このページは、一部のトラフィックだけに最短でない道を通らせる仕組みと、その道を中央で計算する仕組みを扱います。
ブループリントの 3.3.c(SR によるトラフィック エンジニアリング)と 3.3.e(パス計算要素)にあたり、課題 M10-4 と M10-5 で
使います。前のページ「セグメント ルーティングの仕組み」の 2 節(ラベルを重ねて経由地を書く)を先に読んでください。

## 1. 何が嬉しいのか

### 1.1 同じネクスト ホップ、違う道

課題 M10-4 では、顧客 A だけを RT03 経由にし、顧客 B は今のままにします。ここで困るのは、顧客 A のルート 10.101.2.0/24 も
顧客 B のルート 10.102.2.0/24 も、ネクスト ホップが同じ RT02 のループバック(10.255.0.12)だということです。XR01 は
ネクスト ホップへの道を 1 本(16012 で RT01 へ)しか持たないので、「RT02 への道」を変えれば両方が動きます。

欲しいのは、ルートごとに、同じネクスト ホップへの別の道を選べることです。**SR ポリシー**は、ラベルの重ね方(道順)に
「カラー 100 で RT02 へ」のような名前を付けたものです。ルートにカラー 100 の印を付けると、そのルートだけがその道を
使います。印の無いルートは、ふつうの最短パスのままです。

これで嬉しいのは次の点です。

- 設定はヘッドエンドの XR01 だけです。RT01、RT02、RT03 とルート リフレクタは何も変えず、トンネルのシグナリングもありません。
- 道の選び方を、サービスの意図(「低遅延」「このリンクを避ける」)として表せます。カラーは BGP の拡張コミュニティなので、
  ルートを広告する側で付けておけば、受け取った PE が意図に合う道を選びます。
- ポリシーを前もって書いておく必要もありません。あるカラーのルートが届いたときに、ヘッドエンドが雛形から道を作れます
  (2.3 節)。

### 1.2 1 台からは見えないもの

ヘッドエンドは、自分の IGP のエリアのトポロジを見ることができます。しかし、他のヘッドエンドが選んだ道や、エリアの外の
トポロジは見えません。たとえば 2 台の PE から同じ宛先への 2 本の道を、リンクを共有しないように置くには、両方の道を
見る者が要ります。それが**パス計算要素**(PCE)で、ネットワーク全体を見て道を計算し、ヘッドエンドに渡します(3 節)。

## 2. SR ポリシー

### 2.1 カラー、エンドポイント、候補パス

RFC 9256 は、SR ポリシーを 3 つのもので識別します。ヘッドエンド、**カラー**(意図を表す数)、**エンドポイント**(道の終点)
です。ポリシーは 1 つ以上の**候補パス**を持ち、それぞれに優先度があります。有効なもののうち、優先度の最も高いものが
使われます。候補パスは、明示的(設定に書いたラベルの並び)か、動的(ヘッドエンドか PCE が制約から計算する)です。
各ポリシーには**バインディング SID** が付きます。このラベルで届いたパケットは、そのポリシーに乗ります。

IOS XR はポリシーを `segment-routing` → `traffic-eng` の下に置きます。明示的なパスは、ラベル(またはネクスト ホップ)の
並べ方を `segment-list` に書き、ポリシーがそれを参照します。前のページの 2.3 節の道順を、そのまま書いたポリシーです。

```console
RP/0/RP0/CPU0:XR01#show segment-routing traffic-eng policy color 100
Color: 100, End-point: 10.255.0.12
  Name: srte_c_100_ep_10.255.0.12
  Status:
    Admin: up  Operational: up for 00:00:12 (since Oct 29 23:30:50.259)
  Candidate-paths:
    Preference: 100 (configuration) (active)
      Name: CUST-A-VIA-RT03
      Explicit: segment-list VIA-RT03 (valid)
          SID[0]: 16013
          SID[1]: 16012
  Attributes:
    Binding SID: 24003
```

`SID[0]: 16013`(まず RT03 へ)、`SID[1]: 16012`(次に RT02 へ)が、重ねるラベルです。経由するルータには特別なものは
要りません。RT01、RT02、RT03 は、いつもどおりプレフィックス SID で転送するだけです。ポリシーの状態はヘッドエンドに
しかありません。

このポリシーの設定です。

:::config XR01 — 手で書いた道順のポリシー
segment-routing
 traffic-eng
  segment-list VIA-RT03                   ## 道順(ラベルの並び)に名前を付ける
   index 10 mpls label 16013              ## 1 枚目: まず RT03 へ。RT03 は XR01 の隣なので、PHP で実際には積まれない
   index 20 mpls label 16012              ## 2 枚目: 次に RT02 へ。index の小さいものほど外側に積む
  !
  policy CUST-A-VIA-RT03                  ## ポリシーの名前(XR01 の中だけの名前)
   color 100 end-point ipv4 10.255.0.12   ## ポリシーを識別するもの: カラーとエンドポイント(ヘッドエンドは XR01 自身)
   candidate-paths
    preference 100                        ## 候補パスの優先度。有効なもののうち、最も大きいものが使われる
     explicit segment-list VIA-RT03       ## この候補パスは明示的: 上の道順を使う
    !
   !
  !
 !
!
:::

### 2.2 カラーで誘導する

ポリシーは、何かを誘導するまでトラフィックを運びません。誘導の仕組みが**自動ステアリング**で、BGP のルートの
ネクスト ホップを解決するところで働きます(RFC 9256)。XR01 が顧客のルートを転送テーブルに入れる手順を追います。

1. XR01 は、顧客 A のルート 10.101.2.0/24 を受け取ります。ネクスト ホップは 10.255.0.12 です。
2. ふつうなら、XR01 はネクスト ホップへの IGP のルートを引き、16012 を付けて RT01 へ送ります(前のページの 2.2 節)。
3. ルートが BGP の**カラー拡張コミュニティ** 100 を持ち、XR01 に「カラー 100、エンドポイント 10.255.0.12」のポリシーが
   あれば、XR01 は IGP のルートの代わりにそのポリシーを引きます。パケットにはポリシーのラベルが付きます(前のページの
   2.3 節)。
4. 顧客 B のルートにはカラーが無いので、2 のままです。

ふつうは、出口の PE がルートを広告するときにカラーを付けます。ラボでは RT02 はカラーを付けず、ルート リフレクタも
変えられないので、XR01 がルートを受け取るときに付けます。XR02 との VPNv4 のセッションの入力のルート ポリシーで、
顧客 A のルート ターゲットに一致したら、100 を持つ `extcommunity-set opaque` で `set extcommunity color` を行います。
するとルートは、カラーとバインディング SID を表示します。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A 10.101.2.0/24
...
    10.255.0.12 C:100 (bsid:24003) (metric 30) from 10.255.0.21 (10.255.0.12)
      Received Label 22
      Extended community: Color:100 RT:65000:101
      SR policy color 100, up, not-registered, bsid 24003
```

`C:100 (bsid:24003)` が、このルートがポリシーに結び付いた印です。CEF は、ルートをポリシーを通して解決します
(`next hop srte_c_100_ep_10.255.0.12 labels imposed {ImplNull 22}`)。22 は VPN のラベルで、その上のラベルはポリシーが付け
ます。顧客 B は最短パスのままです。CEA1 からの traceroute は RT03(10.0.3.13)を、CEB1 からのものは RT01(10.0.1.11)を
通ります(前のページの 2.2 節と 2.3 節の traceroute)。

カラーを付ける部分を、設定にまとめると次の形です。

:::config fold XR01 — 受け取るときに顧客 A のルートにカラー 100 を付ける
extcommunity-set opaque COLOR-100      ## カラーの値。カラーは拡張コミュニティの一種で、ここに数を書く
  100
end-set
!
extcommunity-set rt CUST-A-RT          ## 照合に使う、顧客 A のルート ターゲット(単元 M9)
  65000:101
end-set
!
route-policy FROM-RR
  if extcommunity rt matches-any CUST-A-RT then
    set extcommunity color COLOR-100   ## 顧客 A のルートにだけ、カラー 100 を足す
  endif
  pass                                 ## 残りのルートも受け入れる。IOS XR のルート ポリシーは、通すとも変えるともしなかったルートを捨てる
end-policy
!
router bgp 65000
 neighbor 10.255.0.21                  ## ルート リフレクタ(XR02)
  address-family vpnv4 unicast
   route-policy FROM-RR in             ## 受け取るときに適用する
  !
 !
!
:::

:::note
Segment Routing のコンフィギュレーション ガイド(IOS XR 26.x、「Configure SR-TE Policies」)は、カラーを設定できるルート
ポリシーの付け先を挙げ、VRF の import のポリシーを、照合はできるが設定はできない場所としています。それでも IOS XR 26.1.1 は、
VRF の import のポリシー(`vrf CUST-B` → `address-family ipv4 unicast` → `import route-policy`)でも `set extcommunity color` を
受け付け、ルートにカラーを付けてポリシーに誘導します(`SR policy color 100, up, registered`)。ラボ XRT-10 はどちらの
場所も受け付けます。模範解はガイドに従い、VPNv4 のセッションでカラーを付けます。
:::

### 2.3 オンデマンドのポリシー

エンドポイントとカラーの組ごとにポリシーを書くのは、PE が増えると追いつきません。**オンデマンド ネクスト ホップ**
(ODN)は、ポリシーの雛形です。あるカラーで新しいネクスト ホップを持つ最初の BGP のルートが届いたとき、ヘッドエンドが
雛形からポリシーを作り、道を計算します。設定は `segment-routing` → `traffic-eng` → `on-demand color 100` → `dynamic` で、
メトリックの種類と制約を付けます。

道にあるリンクを避けさせるには、リンクに**アフィニティ**を塗り、その色を除外させます。アフィニティは名前を付けた
ビットです。`affinity-map` → `name RT01-MAINT bit-position 0` で名前を決め、`traffic-eng` の下のインターフェイス →
`affinity` → その名前でリンクに塗り、雛形の `dynamic` の下の `affinity` → `exclude-any` → その名前で除外します。

道を計算するには、SR-TE のプロセスがトポロジを知っていなければなりません。IS-IS がそれを渡すのは、`router isis` の下に
`distribute link-state` があるときだけです。ガイドは、どの SR-TE ポリシーよりも先にそれを設定するよう書いています。
無いと、オンデマンドのポリシーは down のままで、ルートは何の警告もなく IGP のパスに戻ります。

```console
    Preference: 200 (BGP ODN) (inactive)
      Name: bgp_c_100_ep_10.255.0.12_discr_200
      Dynamic (inactive)
      Last error: Source node not found in topology
```

あれば、ポリシーはすぐに上がります(`Dynamic (valid)`、`SID[0]: 16013 [Prefix-SID, 10.255.0.13]`、
`SID[1]: 16012 [Prefix-SID, 10.255.0.12]`)。PRIMARY を除いたトポロジで RT02 への最短を計算すると、2.1 節で手で書いた道順と
同じになります。IOS XR 26.1.1 のオンデマンドのポリシーは、2 つの候補パスを持ちます。ヘッドエンドが計算する優先度 200 と、
PCE(3 節)が設定されていればそれに任せる優先度 100 です。

オンデマンドのポリシーの部品を、設定にまとめると次の形です。

:::config fold XR01 — PRIMARY を避けるオンデマンドのポリシー
router isis CORE
 distribute link-state               ## IS-IS のトポロジを SR-TE のプロセス(と PCE)に渡す。無いとポリシーは down のまま
!
segment-routing
 traffic-eng
  affinity-map
   name RT01-MAINT bit-position 0    ## リンクの色(アフィニティ)の名前を、ビットの位置に結び付ける
  !
  interface GigabitEthernet0/0/0/0   ## PRIMARY
   affinity
    name RT01-MAINT                  ## このリンクを塗る
   !
  !
  on-demand color 100                ## 雛形: カラー 100 のルートが新しいネクスト ホップで届いたら、ポリシーを作る
   dynamic                           ## 道はヘッドエンド(XR01)が計算する
    metric
     type igp                        ## 何を最小にするか: IGP のメトリック
    !
    affinity
     exclude-any
      name RT01-MAINT                ## この色の付いたリンクは使わない
     !
    !
   !
  !
 !
!
:::

:::try
SR-TE からトポロジを取り上げます。課題 M10-4 の後・課題 M10-5 の前に行い、課題 M10-5 の後にもう一度行います。

1. XR01 の `router isis CORE` の下から `distribute link-state` を外してコミットします。
2. XR01 で `show segment-routing traffic-eng policy color 100 detail` と `show bgp vrf CUST-A 10.101.2.0/24` を、CEA1 で
   `traceroute 10.101.2.1 source Loopback10 numeric` を実行します。
3. 行を戻してコミットし、同じコマンドをもう一度実行します。

結果の例: 課題 M10-5 の前では、ポリシーは `Last error: Source node not found in topology` で down になり、BGP の
ルートはバインディング SID を失い、顧客 A のトラフィックは RT01 経由に戻りました。課題 M10-5 の後では、同じ手順で顧客から
見えるものは何も変わりませんでした。優先度 200 の候補パスは同じエラーで inactive になり、XR02 に任せた優先度 100 のものが
引き継ぎ(`Dynamic (pce 10.255.0.21) (valid)`)、CEA1 の traceroute は RT03 を通ったままでした。PCE も PRIMARY の
アフィニティを知っていて、それを避けました。行を戻すと、15 秒以内に優先度 200 が再び使われました。
:::

## 3. パス計算要素

### 3.1 PCE と PCC

**パス計算要素**(PCE)は、道の計算を引き受けるサーバです。ヘッドエンドは**パス計算クライアント**(PCC)として、PCEP
というプロトコルで道を依頼します。ステートフルな PCE は、渡した道を覚えていて、トポロジが変われば計算し直し、変更を
ヘッドエンドに送ります(RFC 8664 が PCEP に SR を加えています)。

IOS XR では、PCE は `pce` → `address ipv4 <アドレス>` で動きます。トポロジは、自分の IGP から `distribute link-state` で、
または他のエリアについては BGP-LS で学習します。ガイドは SR-PCE に IOS XRv 9000 を勧めています。IOS XRd のデータシートは、
XRd の制御プレーン版を、転送をほとんどしない役割、ルート リフレクタと PCE に向けています。ラボでは XR02(XRd)がその
両方です。

PCC は `segment-routing` → `traffic-eng` → `pcc` → `source-address ipv4` と `pce address ipv4` です。候補パスを `dynamic` →
`pcep` にすると、計算は PCE に任されます。PCE が計算し、ヘッドエンドがそれを転送テーブルに入れます。

```console
RP/0/RP0/CPU0:XR02#show pce ipv4 peer
Peer address: 10.255.0.1
  State: Up
  Capabilities: Stateful, Segment-Routing, Update, Instantiation, SRv6, SR-P2MP

RP/0/RP0/CPU0:XR02#show pce ipv4 topology summary
Nodes:
  Total:                       5
Prefix SIDs:
  Total:                       4
Adjacency SIDs:
  Total:                      13
```

PCE は、起動してから道を計算し始めるまでに約 40 秒かかります(`Topology Ready Summary: Ready: no` とタイマー)。

設定は両側に分かれます。

:::config fold XR02 — PCE
pce
 address ipv4 10.255.0.21   ## PCE として PCEP の接続を待つアドレス(自分のループバック)
!
router isis CORE
 distribute link-state      ## PCE にトポロジを渡す(2.3 節の XR01 と同じ行)
!
:::

:::config fold XR01 — PCC
segment-routing
 traffic-eng
  pcc
   source-address ipv4 10.255.0.1   ## PCEP のセッションの送信元(自分のループバック)
   pce address ipv4 10.255.0.21     ## 道を依頼する PCE
  !
 !
!
:::

### 3.2 交わってはならない道

リンクを共有してはならない 2 つのポリシーには、両方を見る者が要ります。ヘッドエンドでは、2 つの候補パスが同じ
**disjointness のグループ**を名指し(`constraints` → `disjoint-path group-id 1 type link`)、PCE がそれらを離して置きます。
ラボでは、PCE はカラー 201 を RT01 経由の最短パス(16012、メトリック 20)に、カラー 202 を RT03 経由(16013 の次に 16012、
メトリック 200)に置きます。

```console
RP/0/RP0/CPU0:XR02#show pce association
Association: Type Link-Disjoint, Group 1, Not Strict
 Associated LSPs:
  LSP[0]:
   PCC 10.255.0.1, tunnel name cfg_DISJ-2_discr_100,  PLSP ID 3, tunnel ID 4, LSP ID 2, Configured on PCC
  LSP[1]:
   PCC 10.255.0.1, tunnel name cfg_DISJ-1_discr_100,  PLSP ID 2, tunnel ID 3, LSP ID 2, Configured on PCC
 Status: Satisfied
```

`Status: Satisfied` は、条件を満たす組を置けたという意味です。「Not Strict」は、離れた組が存在しないときに、PCE が
離れていない道に戻ってもよいという意味です。strict のグループなら、むしろポリシーを down のままにします。

2 本のポリシーの設定です。

:::config fold XR01 — PCE に計算を任せる 2 本のポリシー
segment-routing
 traffic-eng
  policy DISJ-1
   color 201 end-point ipv4 10.255.0.12
   candidate-paths
    preference 100
     dynamic
      pcep                                 ## 道の計算を PCE に任せる
      !
      metric
       type igp
      !
     !
     constraints
      disjoint-path group-id 1 type link   ## グループ 1 の他のポリシーと、リンクを共有しない
     !
    !
   !
  !
  policy DISJ-2                            ## もう 1 本。カラーだけが違う
   color 202 end-point ipv4 10.255.0.12
   candidate-paths
    preference 100
     dynamic
      pcep
      !
      metric
       type igp
      !
     !
     constraints
      disjoint-path group-id 1 type link
     !
    !
   !
  !
 !
!
:::

:::try
制約を取り去ります。課題 M10-5 の後に行います。

1. XR01 で、DISJ-1 と DISJ-2 の両方から `constraints` を外してコミットします。
2. XR01 で `show segment-routing traffic-eng policy color 201 detail` と `… color 202 detail` を、XR02 で
   `show pce association` と `show pce lsp detail` を実行します。
3. 制約を戻してコミットします。

結果の例: 両方のポリシーが RT01 経由の最短パス(`SID[0]: 16012`、メトリック 20)に移りました。`show pce association`
にはグループが無くなり、`show pce lsp detail` は両方の道を `LSP Role: Single LSP` と表示しました。制約を戻すと、30 秒以内に
カラー 202 は再び RT03 経由(16013、16012、メトリック 200)に移りました。
:::

## 4. コマンド名

| 目的 | IOS XR では |
|---|---|
| ポリシー、明示的なパス | `segment-routing` → `traffic-eng` → `policy`、`segment-list` |
| カラーを付ける | ルート ポリシーの `set extcommunity color`(`extcommunity-set opaque`) |
| オンデマンドのポリシー | `segment-routing` → `traffic-eng` → `on-demand color <カラー>` |
| トポロジを SR-TE と PCE に渡す | `router isis` → `distribute link-state` |
| PCE、PCC | `pce` → `address ipv4`、`segment-routing` → `traffic-eng` → `pcc` |
| 確かめる | `show segment-routing traffic-eng policy color <カラー> detail`、`show pce ipv4 peer`、`show pce association` |

## 実践

ラボ **XRT-10** で、課題 M10-4 と M10-5 に取り組みます。フレキシブル アルゴリズムと SRv6 は付録にあります。

<p class="tolab"><a href="/_learn?id=XRT-10&amp;step=m10t4">ワークスペースで課題 M10-4 を開く</a> — <a href="a5-m10-practice-3.html">課題</a></p>

:::note
出典: Segment Routing Configuration Guide for the ASR 9000, IOS XR 26.1.x–26.3.x(2026。SR-TE ポリシー、ODN、自動
ステアリング、アフィニティ、SR-PCE)とそのコマンド リファレンス(2025)。IOS XRd のデータシート(2026)。RFC 8664、9256。
いずれも 2026 年 10 月に確認しました。`distribute link-state` の無いオンデマンドのポリシー、VRF の import のポリシーで付けた
カラー、XRd の PCE は、ラボ XRT-10 とその PoC での測定によります。
:::
