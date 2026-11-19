# J1 — BGP にポリシーを当てる

## 1. BGP でポリシーが要になる理由

### 1.1 困りごと: 受け入れすぎ、出さなすぎ

前のページまでで、JUN02 は ISP からの経路を選べるようになりました。残りは逆向きです。社内のネットワークを ISP に知らせないと、
ISP から社内へ戻る経路がありません。そして、知らせる経路は少ないほどよい。ISP へは社内のネットワークをまとめた 1 本だけを出したいのです。

### 1.2 それ以前の手

IOS では、BGP へ出す経路を `network` 文か `redistribute` で BGP テーブルに入れ、`aggregate-address` でまとめ、
`neighbor … route-map … out` で絞ります。IOS XR では、IOS XR トラック M6 で見たとおり、ポリシーの無い eBGP ネイバーには何も出しません。
`route-policy … out` を当てて初めて経路が出ます。

### 1.3 Junos の答え

Junos の BGP には `network` 文がありません。何を広告するかは **export ポリシー**がルーティング テーブルから選びます。OSPF への export と
同じ書き方です。まとめた経路は `routing-options aggregate` でルーティング テーブルに作り、export ポリシーで選んで出します。

## 2. 仕組み

### 2.1 BGP の最小の設定

JNT-02 の JUN02 には、初めから次の BGP の設定があります。BGP の単元はまだ先なので、ここでは各行の意味だけを押さえます。

:::config JUN02 — ISP との eBGP セッション(初めから入っている設定)
set routing-options autonomous-system 65000        ## 自分の AS 番号。BGP の設定の外、routing-options に書く
set protocols bgp group ISP type external          ## ネイバーはグループにまとめる。この group のネイバーは eBGP
set protocols bgp group ISP peer-as 64500          ## ネイバーの AS 番号(group の全員に効く)
set protocols bgp group ISP neighbor 10.0.23.2     ## ネイバーのアドレス。group の下に並べる
:::

IOS の `router bgp 65000` と `neighbor 10.0.23.2 remote-as 64500` を、AS 番号・group・neighbor に分けて書く形です。
commit と `show bgp summary` では、OSPF と同じく `requires 'BGP' license` の知らせが出ますが、BGP は動きます(付録)。

### 2.2 BGP のデフォルト ポリシー

ポリシーが無ければ、JUN02 は ISP の経路をすべて受け入れ、何も広告しません(見取り図のページの 2.1 節の出力)。
理由は 2 つです。

- **既定の import は、受け取った経路をすべて受け入れる。**`show bgp summary` の `Default eBGP mode: advertise - accept, receive - accept`
  がそれを示します。Juniper は RFC 8212(ポリシーの無い eBGP では経路を交換しない)の振る舞いを、既存の設定を壊さないために
  既定では入れていません。入れたい時は `set protocols bgp defaults ebgp no-policy` の下で選びます。
- **既定の export は、使っている BGP の経路だけを広告する。**JUN02 の BGP の経路は、すべて ISP から来たものです。Junos は、
  ある eBGP ネイバーから学んだ経路を、そのネイバーと同じ AS の eBGP ネイバーへは広告しません。ですから出すものがありません。
  OSPF の経路・direct のネットワーク・集約経路は BGP の経路ではないので、export ポリシーで選ばないかぎり出ません。

### 2.3 import で拒んだ経路は hidden に残る

import ポリシーが拒んだ経路は、捨てられずにルーティング テーブルに **hidden** として残ります。使われませんが、何が来ていて、なぜ使われないかを
後から見られます。

```console
admin@jun02> show bgp summary
Threading mode: BGP I/O
Default eBGP mode: advertise - accept, receive - accept
Groups: 1 Peers: 1 Down peers: 0
Table          Tot Paths  Act Paths Suppressed    History Damp State    Pending
inet.0
                      10          4          0          0          0          0
Peer                     AS      InPkt     OutPkt    OutQ   Flaps Last Up/Dwn State|#Active/Received/Accepted/Damped...
10.0.23.2             64500         47         47       0       0       20:12 Establ
  inet.0: 4/10/4/0

admin@jun02> show route 198.51.100.128/25 hidden extensive | match reason
                Hidden reason: Rejected by import policy
```

`4/10/4/0` は、10 本受け取り、4 本を受け入れて使っているという意味です。拒んだ 6 本は `show route receive-protocol bgp 10.0.23.2 hidden`
で一覧できます。

### 2.4 ポリシーを書く階層: global・group・neighbor

BGP では、import と export を 3 つの階層に書けます。`protocols bgp` の直下(すべてのネイバー)、`group` の下(その group のネイバー)、
`neighbor` の下(そのネイバーだけ)です。Juniper の文書は「neighbor の import・export は group のものを置き換え、group のものは
BGP 全体のものを置き換える」と書いています。**足し算ではありません。**

group ISP に import `FILTER-IN` と export `SERVERS-OUT` がある所へ、neighbor の下に `import TAG-198` を足すと、そのネイバーには
TAG-198 だけが当たりました。FILTER-IN が外れたので、ISP の 10 本がすべて受け入れられています。置き換わるのは書いた向きだけで、
export は group のものが残りました。

```console
admin@jun02> show bgp neighbor 10.0.23.2 | match "Import|Export"
  Export: [ SERVERS-OUT ] Import: [ TAG-198 ]

admin@jun02> show bgp summary
...
10.0.23.2             64500         50         50       0       0       21:07 Establ
  inet.0: 10/10/10/0
```

`show bgp neighbor ネイバー` の `Import:`・`Export:` の行は、そのネイバーに実際に効いているポリシーを、評価される順に見せます。

### 2.5 属性を変える: local-preference・community・AS パス・MED

BGP の属性は、ポリシーの `then` で書き換えます。どれも評価を終わらせないアクションです。

| アクション | 書き換えるもの | 使いどころ |
|---|---|---|
| `local-preference 150` | LOCAL_PREF(大きいほど好まれる。AS の中だけで使う) | import で、受け取った経路の好みを決める |
| `community add 名前` | community を足す(`set` は置き換え、`delete` は外す) | 経路にタグを付けて、後のポリシーで選ぶ |
| `as-path-prepend "65000 65000"` | AS パスの先頭に AS 番号を足す | export で、相手から見たパスを長く見せる |
| `metric 50` | BGP では MED | export で、隣接 AS に入口の好みを伝える |

community は、`policy-options` の下で名前を付けてから使います(`set policy-options community CUST members 65000:200`)。
書き換えた結果は `show route … detail` で見られます。`Preference: 170/-151` の後ろの数は local-preference から作られる値で、
local-preference が 100 なら `-101`、150 なら `-151`、200 なら `-201` と出ます。

```console
admin@jun02> show route 198.51.100.0/24 exact detail table inet.0

inet.0: 19 destinations, 19 routes (13 active, 0 holddown, 6 hidden)
198.51.100.0/24 (1 entry, 1 announced)
        *BGP    Preference: 170/-151
                Next hop: 10.0.23.2 via et-0/0/1.0, selected
                State: <Active Ext>
                Local AS: 65000 Peer AS: 64500
                Age: 7 	Metric: 0
                AS path: 64500 I
                Communities: 65000:200
                Accepted
                Localpref: 150
```

(出力は、ここで使わない行を省いています。)

### 2.6 集約経路を出す

まとめた経路は、`routing-options aggregate route 172.16.0.0/16` でルーティング テーブルに作ります。集約経路が使われるのは、その範囲の中に
**寄与する経路**(contributing route)が 1 本でもある間だけです。

```console
admin@jun02> show route 172.16.0.0/16 exact detail

inet.0: 20 destinations, 20 routes (14 active, 0 holddown, 6 hidden)
172.16.0.0/16 (1 entry, 1 announced)
        *Aggregate Preference: 130
                Next hop type: Reject, Next hop index: 0
                State: <Active Int Ext>
                Local AS: 65000
                AS path: I  (LocalAgg)
                Contributing Routes (2):
                	172.16.10.0/24 proto OSPF
                	172.16.20.0/24 proto OSPF
```

(出力は、ここで使わない行を省いています。)

- preference は 130 です。
- ネクスト ホップは `Reject` です。集約の範囲の中で、より細かい経路が無い宛先へのパケットは、ここで捨てられます。
  IOS の `aggregate-address` が作る Null0 への経路にあたります。
- 寄与する経路が 1 本も無くなると、集約経路は hidden になります(`State: <Hidden Int Ext>`)。JUN01 の OSPF への export を
  外すと、そうなりました。

集約経路も BGP の経路ではないので、export ポリシーで `from protocol aggregate` を選ぶまで出ません。出すと、AS パスは
`65000 65000 [65000] I` のように表示されます。角括弧は、eBGP ネイバーへ送る時に先頭に付く自分の AS です。ISP の FRR1 では
`65000 65000 65000` と、集約したルータが `aggregated by 65000 192.168.0.2` と見えます。

## 3. 設定例

### 3.1 ISP へ自社のネットワークを /24 のまま、MED を付けて出す

JUN02 が、OSPF で学んだ社内の /24 を、MED 50 を付けて ISP へ出します(集約はしない形)。

:::config JUN02 — OSPF で学んだ社内のネットワークを ISP へ
set policy-options policy-statement SERVERS-OUT term SERVERS from protocol ospf                   ## 出どころが OSPF の経路
set policy-options policy-statement SERVERS-OUT term SERVERS from route-filter 172.16.0.0/16 longer ## 172.16.0.0/16 の中の細かい経路
set policy-options policy-statement SERVERS-OUT term SERVERS then metric 50                       ## BGP では MED
set policy-options policy-statement SERVERS-OUT term SERVERS then accept                          ## 
set policy-options policy-statement SERVERS-OUT term REST then reject                             ## ほかは出さない(BGP の既定の export に任せない)
set protocols bgp group ISP export SERVERS-OUT                                                    ## ISP の group の出口に当てる
:::

`REST` を書かないと、ISP 以外から学んだ BGP の経路(この盤面には無いが、ほかの ISP や iBGP から来るもの)が、BGP の既定の
export で出ていきます。出口のポリシーは、最後に拒む term で閉じておくのが安全です。

結果の例(このとき JUN01 は 172.16.20.0/24 だけを OSPF に出していた):

```console
admin@jun02> show route advertising-protocol bgp 10.0.23.2

inet.0: 19 destinations, 19 routes (13 active, 0 holddown, 6 hidden)
  Prefix                  Nexthop              MED     Lclpref    AS path
* 172.16.20.0/24          Self                 50                 I
```

```console
frr1# show bgp ipv4 unicast 172.16.20.0/24
BGP routing table entry for 172.16.20.0/24, version 12
Paths: (1 available, best #1, table default)
  Advertised to peers:
  10.0.23.1
  65000
    10.0.23.1 from 10.0.23.1 (192.168.0.2)
      Origin IGP, metric 50, valid, external, best (First path received)
```

### 3.2 受け取る経路にタグを付ける: ポリシーの中に term を差し込む

見取り図のページの 2.2 節では、タグを付けるポリシーをポリシー チェーンの前に置きました。同じことは、1 つのポリシーの中に term を差し込んでも
できます。JUN02 の FILTER-IN に、192.0.2.0/24 に local-preference 120 と community 65000:200 を付ける term を、受け入れる term の
前に足します。

:::config JUN02 — FILTER-IN の中で 1 本の経路にタグを付ける
set policy-options community CUST members 65000:200                                    ## 付ける community に名前を付ける
set policy-options policy-statement FILTER-IN term MARK from route-filter 192.0.2.0/24 exact ## 192.0.2.0/24 そのものだけ
set policy-options policy-statement FILTER-IN term MARK then local-preference 120      ## 属性を変えるだけ。accept は書かない
set policy-options policy-statement FILTER-IN term MARK then community add CUST        ## 
insert policy-options policy-statement FILTER-IN term MARK before term LEN             ## 受け入れる term(LEN)の前へ。末尾のままだと届かない
:::

```console
admin@jun02> show route community 65000:200 detail | match "^[0-9]|Localpref|Communities"
192.0.2.0/24 (1 entry, 1 announced)
                Communities: 65000:200
                Localpref: 120
```

### 3.3 IOS・IOS XR から Junos へ

| IOS では | IOS XR では | Junos では |
|---|---|---|
| `router bgp 65000` | `router bgp 65000` | `set routing-options autonomous-system 65000` |
| `neighbor 10.0.23.2 remote-as 64500` | `neighbor 10.0.23.2 remote-as 64500` | `group ISP type external`・`peer-as 64500`・`neighbor 10.0.23.2` |
| `network`・`redistribute` で BGP テーブルに入れる | 同じ | export ポリシーがルーティング テーブルから選ぶ |
| `aggregate-address 172.16.0.0 255.255.0.0 summary-only` | `aggregate-address 172.16.0.0/16 summary-only` | `routing-options aggregate route 172.16.0.0/16` と export ポリシー |
| `neighbor … route-map 名前 in`・`out` | `route-policy 名前 in`・`out` | `import 名前`・`export 名前`(global・group・neighbor) |
| eBGP にポリシーが無い: すべて通る | eBGP にポリシーが無い: 何も通らない | ポリシーが無い: 受け入れは全部、広告は BGP の経路だけ |
| `set local-preference 150` | `set local-preference 150` | `then local-preference 150` |
| `set as-path prepend 65000 65000` | `prepend as-path 65000 2` | `then as-path-prepend "65000 65000"` |
| `set community 65000:200 additive` | `set community … additive` | `then community add 名前` |

## 実践

ラボ **JNT-02** に移り、課題 J1-4 と J1-5 に取り組みます。

<p class="tolab"><a href="/_learn?id=JNT-02">ワークスペースでラボ JNT-02 を開く</a> — <a href="16-j1-practice-3.html">課題</a></p>

:::note
出典: Juniper Networks『BGP User Guide』(2026-07-09)の RFC 8212 の例外の記述と「Implicit filter for Default EBGP Route Propagation
Behavior without Policies」、受け取った経路を同じ AS の eBGP の隣へ返さない決まり(advertise-peer-as)。
『Routing Policies, Firewall Filters, and Traffic Policers User Guide』(2026-06-23)の「Example: Applying Routing Policies at
Different Levels of the BGP Hierarchy」(neighbor は group を、group は全体を置き換える)と、属性を変える動作の表。
IOS XR の振る舞いは IOS XR トラック M5・M6 による。出力は containerlab の vJunos-Evolved(Junos OS Evolved 26.2R1.7)と
FRRouting 10.7.1 で取ったものです。
:::
