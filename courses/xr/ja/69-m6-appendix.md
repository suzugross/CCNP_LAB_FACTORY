# M6 追補 — 付録

本文で手短にしか扱わなかったことをまとめます。VPN で使う best-external、PIC Core と PIC Edge、IOS XRd と IOS XRv 9000 の差、
RIB に入らない BGP の経路の扱いです。続けて、IOS XR と IOS XE の既定値とコマンドの対応、公式文書と機器が食い違った点を
並べます。VPN の best-external、PIC Core、IOS XE の追加パスは、この追補では試していません。

## 1. best-external: VPN で使う機能

`advertise best-external` は、ローカルで選んだ最良の経路が iBGP のネイバーから来たものであるときに、eBGP の経路の中で最良の
もの(best-external)を、iBGP のネイバーと RR へ広告させます。BGP が best-external を計算するのは、最良が iBGP の経路で
あるときだけです。

この盤面の PE3 が、ちょうどその立場です。最良は PE2 を経由する iBGP の経路(ローカル プリファレンス 200)で、X2 から
学習した経路が best-external になります。PE3 に設定すると、X2 の経路に `best-external` が付き、RR1 へ広告されます
(PE3 の抜粋)。

```console
RP/0/RP0/CPU0:PE3#show bgp 203.0.113.0/24
...
Paths: (2 available, best #1)
...
  65100
    10.255.0.2 (metric 20) from 10.255.0.21 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
...
  Path #2: Received by speaker 0
  Advertised IPv4 Unicast paths to peers (in unique update groups):
    10.255.0.21
  65100
    172.16.3.1 from 172.16.3.1 (10.100.255.2)
      Origin IGP, metric 11, localpref 100, valid, external, best-external
```

これで RR1 は 2 本の経路を持ちますが、反射するのは最良の 1 本だけで、PE1 が知る経路は PE2 を経由する 1 本のままです。
best-external だけでは、PE2 が落ちたときの途切れは短くなりません。予備の出口が広告しても、話は RR で止まります。

Cisco の文書が `advertise best-external` を置くアドレス ファミリは、VRF の IPv4/IPv6、VPNv4/VPNv6、L2VPN、ラベル付き
ユニキャストです。素の IPv4/IPv6 ユニキャストは一覧になく、ASR 9000 の Routing Command Reference は「Unlabelled
best-external is not supported as it may create routing loop」と書いています。

ASR 9000 の 26.x のガイドには、VRF ごとのラベル(per-VRF)では、同じアドレス ファミリの best-external に対応しない、
ループの恐れがあるから、という注もあります。どちらの文書も、ループの中身は書いていません。

この盤面で起きたのは、次の送り返しです。予備の経路を入口まで届けたうえで、入口の PE1 にだけ PIC を入れて PE2 を P1 から
切ると、途切れは 3.01 秒でした。
入口の BGP の next-hop の追跡を 10 秒に延ばしても 2.93 秒で、入口は BGP を待たずに予備の PE3 へ切り替えています
(入口が IOS XRv 9000 のとき。XRd の入口は 3 節)。

止まっていたのは PE3 です。ラベルなしの網では、PE3 に届いたパケットは IP で引き直されます。PE3 の最良はまだ PE2 を経由する
iBGP の経路なので、パケットは PE2 へ向けて送り返され、届きません。PE3 の BGP が最良を選び直すのは、自分の next-hop の追跡の
遅延(3 秒)が過ぎてからです。予備の出口は 3 秒の間、律儀に主の出口へ送り返します。

VPN では、入口は予備の PE が経路に付けた VPN ラベルを積んで送ります。ラベルがプレフィックスごとか CE ごとなら、予備の PE は
そのラベルで CE へそのまま送り、IP で引き直しません(M9 の付録の 1.1 節)。VRF ごとのラベルでは VRF のテーブルで
引き直すので、上の注はこの送り返しと同じ形を指していると読めます。

文書とこの仮想機は食い違います。IOS XRd 26.1.1 と IOS XRv 9000 26.1.1 は、素の IPv4 ユニキャストの
`advertise best-external` をコミットで受け付け、上の出力のとおり効きます。文書が対応しないと書く設定が、黙って通ります。

このラボは使いません。課題 M6-5 は best-external を使わないよう指定し、PE3 は追加パス
(`set path-selection backup 1 advertise`)で、X2 の経路を予備として RR1 へ送ります。追加パスは、IPv4 ユニキャストでも
使える機能として文書に載っています。

IOS XR 7.8.1 からは、VPN で PE ごとに違う RD を使うとき、最良の経路と best-external の経路を、追加パスなしで送る機能も
あります。既定で有効で、止められません(NCS 5500 の BGP のガイド(25.x)の「BGP Advertisement without Additional Paths」)。
RD が違えば VPNv4 の経路として別のものになるので(M9)、RR が 1 本に絞ることはありません。

## 2. PIC Core と PIC Edge

PIC(Prefix Independent Convergence)の名前は、切り替えにかかる時間が経路の数によらないことから来ています。IOS XR の
フォワーディング テーブルは階層になっていて、BGP の経路は自分の next-hop の共有のエントリを指し、そのエントリが IGP の道を
指します。ASR 9000 の IOS XR 5.1.1 のリリース ノートは、FIB の更新は経路によらず、コアの障害にもエッジの障害にも、MPLS が
あってもなくても当てはまる、と書いています。

PIC Core は、コアの中の障害で、BGP の next-hop への IGP の道が替わる場合です。next-hop にはまだ届くので、替えるのは共有の
IGP のエントリ 1 か所だけで、それを指すすべての BGP の経路が一度に新しい道へ移ります。予備の BGP の経路は要りません。

ASR 9000 のガイド(26.x)の「BGP PIC for RIB and FIB」には、「Recursive PIC activation at third level and beyond, on failure
trigger at the first (IGP) level」とあります。IGP の段(1 段目)の障害をきっかけに、3 段目より上の再帰でも PIC が働く、という書き方です。

ただし、今の IOS XR の設定ガイドは「PIC Core」を別の機能として定義しておらず、既定で有効かどうかも書いていません。
名前が別に出てくるのは、Cisco 8000 の BGP のガイド(7.2.x)の BGP-LU の節(PIC core に対応、PIC edge には非対応)などです。
このページも、IOS XR の PIC Core の既定については何も言いません。

PIC Edge は、BGP の next-hop そのものが消える場合です。出口の PE が落ちたときや、出口の PE と隣の AS の間の線が切れたとき
です。IGP の道を替えても届かないので、別の next-hop を持つ 2 本目の BGP の経路を、あらかじめ計算してフォワーディング
テーブルに入れておきます。IOS XR では `set path-selection backup 1 install` がそれです。

ASR 9000 のガイド(24.x、26.x)は、その目的を「install a backup path into the forwarding table and provide prefix
independent convergence (PIC) in case of a PE-CE link failure」と書いています。RIB と CEF に入る予備の経路は 1 本までです
(TAC のテクニカル ノート 217097)。

IOS XE では、PIC Core は既定で有効で、`cef table output-chain build favor memory-utilization` で止め、
`cef table output-chain build favor convergence-speed` で戻します。PIC Edge は `bgp additional-paths install` で、PIC Core が
有効なときだけ働きます(ASR 900 の IOS XE 17.1 の BGP のガイド)。IOL では試していません。

この盤面では、各 PE から P1 への線は 1 本です。課題 M6-6 で切るのはコアのリンク(P1─PE2)ですが、PE2 へのほかの道が
ないので、PE1 から見ると next-hop の PE2 そのものが消えます。働くのは PIC Edge です。コアに別の道がないので、コアの中で
道を替える話は起きようがありません。

## 3. IOS XRd と IOS XRv 9000 の差

このラボの XR のうち、PE1 だけが IOS XRv 9000 で、PE2、PE3、P1、RR1 は IOS XRd です。BGP の設定のコマンドは 2 つで
同じでした。BGP のコマンドの `?` の一覧(追加パス、PIC、GTSM、認証、上限、ダンプニング、集約)はすべて一致し、何も設定
しないときの既定値(5.1 節)も同じです。違ったのは、
障害の気づき方と、PIC の切り替えにかかる時間です。

CML でリンクを止めても、XRd のインターフェイスは落ちません。IS-IS はホールド タイムの 30 秒まで隣接を保ち、15 秒止めて
戻すと、隣接は一度も落ちません(CML のリンクの停止でインターフェイスが落ちないのは IOS XRv 9000 も同じです。M10 の 3 節)。
そのうえ XRd は、IS-IS の BFD のセッションを作りません。`show bfd session` は空で、隣接の表の BFD の欄は `Init` のままです。
XRv 9000 では BFD が動きます(M7)。

そのため、課題 M6-6 の Check は、リンクを止めるのでなく、P1 の PE2 向けのインターフェイスを shutdown します。
インターフェイスが落ちれば P1 の IS-IS はすぐに隣接を落とすので、測っているのは、IGP が PE2 が消えたことを伝える速さと、
各 PE の反応です。

PIC の切り替えにかかる時間は、入口の PE の機種で違いました。比べた盤面には入口の PE が 2 台あり(XRd の入口と、ラボの
PE1 と同じ XRv 9000 の入口)、同じ設定で PE2 を P1 から切りました。XRv 9000 の入口は 0.18 秒と 0.15 秒、XRd の入口は
2.96 秒、3.02 秒、3.01 秒でした。追加パスで予備を配る形(ラボの形)でも、XRv 9000 は 0.18 秒、XRd は 3.01 秒です。

XRd の入口でも、`show bgp`、`show route … detail`、`show cef … detail` は予備の経路を XRv 9000 と同じ形で表示しました。
入口の BGP の next-hop の追跡を 10 秒にしてあっても約 3 秒だったので、入口の BGP を待っていたのでもありません。何が
XRd の入口の約 3 秒を決めているかは、切り分けていません。

XRd が予備へ切り替えた場面もあります。予備の出口の PE3(XRd)は、直結の eBGP の予備へ切り替わっていて、XRv 9000 の入口の
0.18 秒は、それがあってのものです。

表示の上では、`show cef … detail` の `LW-LDI` の行が 2 つの機種で違いました。予備を入れた後の、ラボの PE1(XRv 9000)と
PE3(XRd)の抜粋です。

```console
RP/0/RP0/CPU0:PE1#show cef 203.0.113.0/24 detail
...
  LW-LDI[type=3, refc=1, ptr=0xf92ee58, sh-ldi=0xf86ad50]
...
   via 10.255.0.2/32, 3 dependencies, recursive [flags 0x6000]
...
   via 10.255.0.3/32, 2 dependencies, recursive, backup [flags 0x6100]
```

```console
RP/0/RP0/CPU0:PE3#show cef 203.0.113.0/24 detail
...
  LW-LDI[type=0, refc=0, ptr=0x0, sh-ldi=0x0]
...
   via 10.255.0.2/32, 2 dependencies, recursive [flags 0x6000]
...
   via 172.16.3.1/32, 2 dependencies, recursive, bgp-ext, backup [flags 0x6120]
```

XRv 9000 は `type=3` とポインタを、XRd は `type=0` と 0 を表示します。XRd では、見たどの経路でもこの行は同じでした
(比べた盤面の XRd の入口、予備を持つ PE2 と PE3)。切り替えの時間の差と同じ向きに分かれる表示ですが、この行が原因だとは
確かめていません。PE3 は `type=0` のまま、直結の予備へ切り替わっています。表示は 2 つとも予備を載せていて、違うのは通信が
戻るまでの時間です。

ラボは、PIC の切り替えを通信で測る入口の PE1 だけを IOS XRv 9000 にし、ほかの XR を XRd にしています。

## 4. RIB に入らない経路と bgp suppress-inactive

BGP の最良の経路が、RIB では、アドミニストレーティブ ディスタンスの小さい別の経路に負けることがあります。PE2 に
10.199.9.0/24 の static(Null0、ディスタンス 1)を置くと、X1 から学習した BGP の経路(eBGP、20)は RIB に入りません。

IOS XR は、この経路をそのまま広告します。BGP の表では `*>` のままで、凡例には `r RIB-failure` があるのに、`r` は
付きません。PE2 は RR1 へこの経路を広告し、RR1 の最良にもなりました(PE2 の抜粋)。

```console
RP/0/RP0/CPU0:PE2#show route 10.199.9.0/24

Routing entry for 10.199.9.0/24
  Known via "static", distance 1, metric 0 (connected)
...
    directly connected, via Null0
...
RP/0/RP0/CPU0:PE2#show bgp
...
Status codes: s suppressed, d damped, h history, * valid, > best
              i - internal, r RIB-failure, S stale, N Nexthop-discard
Origin codes: i - IGP, e - EGP, ? - incomplete
   Network            Next Hop            Metric LocPrf Weight Path
* i10.199.9.0/24      10.255.0.3                    100      0 65100 i
*>                    172.16.2.1               0    200      0 65100 i
...
RP/0/RP0/CPU0:PE2#show bgp neighbor 10.255.0.21 advertised-routes
Network            Next Hop        From            AS Path
10.199.9.0/24      10.255.0.2      172.16.2.1      65100i
203.0.113.0/24     10.255.0.2      172.16.2.1      65100i
```

IOS XR の文書は、RIB に入らない経路を広告するかどうかを書いていません。`bgp suppress-inactive` に当たるコマンドもなく、
`router bgp` の下の `bgp ?` にも、アドレス ファミリの下の `bgp ?` にも、相当するものはありません。凡例に載っている印が、
表に付くとは限りません。

IOS XE は表示が違います。同じ形を X2 に作ると(10.199.9.0/24 の static、Null0)、X1 から iBGP で学習した経路に
`RIB-failure(17)` が付き、`show ip bgp rib-failure` は理由を `Higher admin distance` と表示し、広告の一覧では `r>i` に
なります。それでも広告はします。

```console
X2#show ip bgp rib-failure
  Network            Next Hop                      RIB-failure   RIB-NH Matches
10.199.9.0/24      10.100.255.1        Higher admin distance              n/a
X2#show ip bgp neighbors 172.16.3.254 advertised-routes
...
     Network          Next Hop            Metric LocPrf Weight Path
 r>i  10.199.9.0/24    10.100.255.1             0    100      0 i
 *>   203.0.113.0      10.100.23.3             11         32768 i
```

TAC のテクニカル ノート 213286 は、IOS は RIB-failure の経路も広告すると書き、IOS XE 17.x のガイドは、アドレス ファミリの
下の `bgp suppress-inactive` で、そうした経路(inactive な経路)をどの BGP ネイバーにも広告しなくなると書いています。
TAC の文書には、止まるのは、BGP の next-hop が RIB の同じ経路の next-hop と違う経路だけ、という注があります。

IOL 17.15 の X2 では、`bgp suppress-inactive` を設定し、`clear ip bgp 172.16.3.254 soft out` で出し直しても、
`clear ip bgp 172.16.3.254` でセッションを張り直しても、10.199.9.0/24 を広告し続けました。

```console
X2#show running-config | section router bgp
router bgp 65100
...
 address-family ipv4
  bgp suppress-inactive
...
X2#show ip bgp rib-failure
  Network            Next Hop                      RIB-failure   RIB-NH Matches
10.199.9.0/24      10.100.255.1        Higher admin distance              Yes
X2#clear ip bgp 172.16.3.254
X2#show ip bgp neighbors 172.16.3.254 advertised-routes
...
     Network          Next Hop            Metric LocPrf Weight Path
 r>i  10.199.9.0/24    10.100.255.1             0    100      0 i
 *>   203.0.113.0      10.100.23.3             11         32768 i
```

設定した後は、`RIB-NH Matches` の欄が `n/a` から `Yes` に変わっています。欄の名前どおりに読めば、RIB の経路(Null0)と
next-hop が一致する扱いで、TAC の注の対象から外れたことになります。なぜ `Yes` になるかは確かめていません。文書と機器の
食い違いとして記録し(6.1 節)、課題の正否には使いません。

SPCOR の 1.5.c「BGP prefix suppression」という語は、Cisco の文書には見当たりません。この追補は、それを「受け取りすぎない」の
ページの 3 つ(経路数の上限、ダンプニング、集約)として扱い、`bgp suppress-inactive` には、名前の近い IOS XE の機能として
ここで触れるだけにしています。

## 5. 既定値とコマンドの対応(IOS XR と IOS XE)

下の値と書き方は、IOS XR は IOS XRd 26.1.1(既定値と `?` の一覧は IOS XRv 9000 26.1.1 でも同じ)、IOS XE は IOL 17.15 で
確かめたものと、文書に書かれたものです。IOS XE の欄の「—」は、この追補で確かめておらず、参照した文書にも無いことを表します。

### 5.1 既定値

| 項目 | IOS XR | IOS XE | どこに書いてあるか |
|---|---|---|---|
| 追加パスの能力 | 交渉しない(`Additional-paths operation: None`) | — | ASR 9000 の Routing Command Reference、機器 |
| 追加パスで 1 つの経路に広告するパスの数 | 32 まで(`additional-paths advertise-limit` で 33〜96) | — | NCS 5500 の BGP のガイド(25.x)、機器(`?` の `default 32`) |
| 予備の経路のインストール(PIC Edge) | selection のポリシーの `install` で入れる | `bgp additional-paths install` で入れる | ASR 9000 のガイド(24.x、26.x)。ASR 900 の IOS XE 17.1 のガイド |
| PIC Core | 文書に定義も既定の記述もない(2 節) | 有効 | ASR 900 の IOS XE 17.1 のガイド |
| next-hop の追跡の遅延(VPNv4/VPNv6 以外) | critical 3000 ms、non-critical 10000 ms | — | ASR 9000 と Cisco 8000 のコマンド リファレンス、機器(`show bgp nexthops`) |
| next-hop の追跡の遅延(VPNv4/VPNv6) | critical 50 ms(7.10.1 から。それまでは 0 ms)、non-critical 10000 ms | — | ASR 9000 のコマンド リファレンス |
| fast-external-fallover | 有効。直結の eBGP は `Fast fallover is enabled`、iBGP は `Fast fallover is not enabled` | — | ASR 9000 のコマンド リファレンス、機器 |
| GTSM | 無効 | — | ASR 9000 のコマンド リファレンス |
| 経路数の上限 | 設定しないネイバーの表示には上限の行(`Maximum prefixes allowed`)が出ない。文書は割れている(6.2 節) | — | 機器 |
| 経路数の上限の警告 | 上限の 75 % | — | ASR 9000 と Cisco 8000 のコマンド リファレンス |
| 経路数の上限を超えたとき | Cease を送ってセッションを切り、`clear bgp` か `restart` の時間まで `Idle (PfxCt)` | — | 同上、機器 |
| ダンプニング | 無効。半減期 15 分、reuse 750、suppress 2000、最大抑制時間は半減期の 4 倍(60 分) | — | ASR 9000 のコマンド リファレンス、機器(`half life 00:15:00, suppress value 2000, reuse value 750`、`Maximum suppress time 01:00:00`) |
| ダンプニングのペナルティ | フラップ 1 回に 1000 で、積み上がる。ネイバーのリセットでは足さない | — | ASR 9000 のガイド(26.x)の「Route Dampening」 |
| 集約の ATOMIC_AGGREGATE | `as-set` を付けない限り付く | — | ASR 9000 のコマンド リファレンス、機器(`aggregated, atomic-aggregate`) |
| RIB に入らない BGP の経路 | 広告する。表は `*>` のまま | 広告する(`r>i`)。文書では `bgp suppress-inactive` で止まる | 機器。TAC 213286、IOS XE 17.x のガイド |

### 5.2 設定

IOS XR の列の「アドレス ファミリ」は `router bgp` → `address-family ipv4 unicast`、「ネイバー」は `router bgp` → `neighbor <アドレス>`、
「ネイバーの アドレス ファミリ」はその下の `address-family ipv4 unicast` です。場所を書いていない `route-policy`、`key chain`、`tcp ao` は
グローバルの設定です。IOS XE の列は、`key chain` と `cef` の行のほかは `router bgp` の下に置きます。

| すること | IOS XR | IOS XE |
|---|---|---|
| 追加パスを送る、受ける能力 | アドレス ファミリ の `additional-paths send`、`additional-paths receive`(iBGP のネイバーすべて。ネイバーごとは `capability additional-paths …`)。能力は OPEN で交渉するので、張り直すまで効かない(RFC 7911) | — |
| どのパスを配るか、入れるか | `route-policy` の `set path-selection backup 1 advertise`(配る)、`… install`(フォワーディング テーブルへ)、`… advertise install`(両方)。アドレス ファミリ の `additional-paths selection route-policy <名前>` で付ける | — |
| 予備の経路をフォワーディング テーブルへ(PIC Edge) | 上の `install` | `bgp additional-paths install`(PIC Core が有効なとき) |
| PIC Core を止める、戻す | (文書に記述なし) | `cef table output-chain build favor memory-utilization`、`cef table output-chain build favor convergence-speed` |
| best-external | アドレス ファミリ の `advertise best-external`(文書では VRF、VPNv4/VPNv6、ラベル付きユニキャストなど) | — |
| next-hop の追跡の遅延 | アドレス ファミリ の `nexthop trigger-delay {critical \| non-critical} <ms>` | — |
| fast-external-fallover を止める | `router bgp` の下の `bgp fast-external-fallover disable` | — |
| GTSM | ネイバーの `ttl-security`(ホップ数の引数なし。受けるのは TTL 255 だけで、送るのも 255) | `neighbor <アドレス> ttl-security hops <1-254>`(受けるのは 255 − hops 以上) |
| GTSM と `ebgp-multihop` | 両方を書ける(文書では `ttl-security` が勝つ) | 一緒には書けない(`Remove ttl-security before configuring ebgp-multihop`) |
| MD5 認証 | ネイバーの `password {clear \| encrypted} <文字列>` | `neighbor <アドレス> password <文字列>` |
| キー チェーン認証 | ネイバーの `keychain <名前>`(RFC 2385 の MD5 認証とは別の方式。IOS XE の `password` とはつながらない) | — |
| TCP-AO のキー | `key chain <名前>` → `key <ID>` → `key-string clear <鍵>`、`cryptographic-algorithm AES-128-CMAC-96`、`send-lifetime`、`accept-lifetime` | `key chain <名前> tcp` → `key <ID>` → `key-string <鍵>`(16 進で 32 桁か 64 桁)、`cryptographic-algorithm aes-128-cmac`、`send-id`、`recv-id` |
| TCP-AO の SendID と ReceiveID | `tcp ao` → `keychain <名前>` → `key <ID> SendID <n> ReceiveID <n>` | 上のキーの下の `send-id`、`recv-id` |
| TCP-AO をネイバーに | ネイバーの `ao <名前> include-tcp-options enable` | `neighbor <アドレス> ao <名前> include-tcp-options` |
| 1 つのネイバーに 2 つの方式 | コミットで拒む(`Password and Keychain/AO based authentication together`) | どちらか一方だけ(MD5 と TCP-AO) |
| 経路数の上限 | ネイバーの アドレス ファミリ の `maximum-prefix <上限> [<しきい値 %>] [discard-extra-paths] [warning-only] [restart <分>]` | `neighbor <アドレス> maximum-prefix <上限> [<しきい値>] [restart <分>] [warning-only]`(IOS XE 17.x のガイド「Configuring a Basic BGP Network」・機器では試していない) |
| ダンプニング | アドレス ファミリ の `bgp dampening [<半減期> [<reuse> <suppress> <最大抑制時間>]]`、または `bgp dampening route-policy <名前>`(ポリシーの `set dampening`) | — |
| 集約 | アドレス ファミリ の `aggregate-address <プレフィックス/長さ> [as-set] [summary-only] [route-policy <名前>]` | `aggregate-address <アドレス> <マスク> [as-set] [summary-only] [suppress-map <名前>]`(同じガイド・機器では試していない) |
| より詳細な経路の一部だけを止める | 集約の `route-policy` の中の `suppress-route` | `suppress-map` |
| 止めた経路を一部のネイバーにだけ出す | ネイバーの出力の `route-policy` の中の `unsuppress-route` | `unsuppress-map` |
| RIB に入らない経路を広告しない | (相当するものなし) | アドレス ファミリの下の `bgp suppress-inactive` |

IOS XE の `suppress-map` と `unsuppress-map` は、IOS XE 17.x のガイドの節「Suppressing and Unsuppressing the Advertisement
of Aggregated Routes Using BGP」のもので、この追補では試していません。IOS XR には、どちらのコマンドもありません。

### 5.3 show と clear

| すること | IOS XR | IOS XE |
|---|---|---|
| next-hop の追跡の遅延を見る | `show bgp nexthops` | — |
| 予備の経路を見る | `show bgp <プレフィックス>`(`backup, add-path`)、`show route <プレフィックス> detail`(`BGP backup path`)、`show cef <プレフィックス> detail`(`backup`) | — |
| 追加パスの交渉を見る | `show bgp neighbor <アドレス>`(`Additional-paths operation: …`) | — |
| GTSM を見る | `show bgp neighbor <アドレス>`(`TTL security is configured`) | `show ip bgp neighbors <アドレス>`(`Mininum incoming TTL 254, Outgoing TTL 255`) |
| 認証を見る | `show tcp authentication keychain <名前>`(TCP-AO) | `show ip bgp neighbors <アドレス>`(`Option Flags` の `md5`、`TCP AO`) |
| 経路数の上限を見る | `show bgp neighbor <アドレス>`(`Maximum prefixes allowed …`、`Threshold for warning message …`) | — |
| 経路数の上限を超えたネイバー | `show bgp summary`(`Idle (PfxCt)`) | — |
| ダンプニングを見る | `show bgp dampened-paths`、`show bgp flap-statistics`、`show bgp <プレフィックス>`(`Dampinfo`) | — |
| 集約で止めた経路 | `show bgp`(行頭の `s`)、`show bgp <プレフィックス>`(`Advertisements of this net are suppressed by an aggregate.`) | — |
| RIB に入らない経路 | (印は付かない) | `show ip bgp rib-failure` |
| セッションを張り直す | `clear bgp <アドレス>` | `clear ip bgp <アドレス>` |
| 更新だけを出し直す | `clear bgp ipv4 unicast <アドレス> soft`(`clear bgp ipv4 unicast <アドレス>` の後ろには `soft` か `long-lived-stale` が要り、それだけでは張り直せない) | `clear ip bgp <アドレス> soft out` |
| ダンプニングを消す | `clear bgp ipv4 unicast dampening [<プレフィックス>]` | — |

## 6. 公式文書と実機が食い違った点

文書と機器が食い違う所では、この追補のページは機器がどう動いたかを書き、文書の名前を添えます。機器は、IOS XR では IOS XRd
26.1.1 と IOS XRv 9000 26.1.1、IOS XE では IOL 17.15 です。

### 6.1 文書と機器の動きが違った点

- **素の IPv4 ユニキャストの best-external。** ASR 9000 の Routing Command Reference は、ラベルなしの best-external には
  対応しない(ループの恐れ)と書き、置き場の一覧に素の IPv4 ユニキャストがありません。2 つの仮想機は、どちらもコミットで
  受け付け、効きます(1 節)。課題 M6-5 は best-external を使わないよう指定し、予備の道は追加パスで配ります。
- **片側だけの GTSM。** 同じ Command Reference は、片側だけだとセッションは OpenSent か OpenConfirm まで進み、ホールド
  タイムで落ちると書いています。PE2(IOS XR)だけに `ttl-security` を入れると、TCP の接続ができず、X1 は `Idle`
  (`… due to Active open failed`)のままでした。X1 は TTL 1 で送っていて(キャプチャ)、PE2 は TTL 255 しか受け付けません。
  課題 M6-7 が求めるのは、両側を設定して確立した状態です。
- **IOS XE の GTSM が送る TTL。** IOS XE 17.x のガイドは、`ttl-security hops` が守るのは入る向きだけで、出ていく
  パケットには効かないと書いています。RFC 5082(3 節)は、送る TTL を 255 と定めています(MUST)。X1 は `Outgoing TTL 255`
  と表示し、キャプチャでも、設定の前に 1 だった X1 の TTL が 255 になりました。この追補は RFC と機器のとおりに書き、
  課題 M6-7 の Check もこの表示を読みます。
- **IOS XE の `bgp suppress-inactive`。** IOS XE のガイドと TAC 213286 は、RIB に入らない経路を広告しなくなると書いています。
  IOL 17.15 は、soft out の後もセッションを張り直した後も広告し続けました(4 節)。
- **IOS XRd の PIC。** 文書と食い違うというより、文書に無い振る舞いです。XRd の入口の PE は、予備の経路を表示しながら、
  PE2 が消えたときの途切れが約 3 秒でした(3 節)。PIC の切り替えを通信で見せるラボでは、入口を IOS XRv 9000 にします。

### 6.2 文書どうしが食い違う点

- **経路数の上限の既定値。** ASR 9000 の Routing Command Reference は、アドレス ファミリごとの既定値(IPv4 ユニキャストは
  1048576 など)を挙げ、同じ項目の履歴で、7.3.1 で既定値をなくし、設定が必要になったと書いています。NCS 5500 の BGP の
  ガイド(25.x)の「BGP Default Limits」は 512K(IPv4 ユニキャスト)、128K(IPv6 ユニキャスト)、512K(VPNv4 ユニキャスト)です。
- **経路数の上限の出力例。** ASR 9000 のガイド(26.x)の例は `Maximum prefixes allowed 1048576`、Command Reference の例は
  `maximum limit 524288` で、Cisco 8000 の BGP Command Reference には既定値の一覧がありません。26.1.1 の機器は、
  `maximum-prefix` を書かないネイバーに上限の行を表示しません。この追補は上限を必ず書き、既定値には頼りません。
- **BGP のキー チェーンの暗号。** Routing Command Reference(`keychain`)は、BGP が使えるのは HMAC-MD5 と HMAC-SHA1-12 だけ
  と書き、System Security Command Reference は AES-128-CMAC-96 と HMAC-SHA1-96 も挙げています。機器では、
  AES-128-CMAC-96 のキー チェーンを使う TCP-AO の BGP のセッションが確立しました(課題 M6-8)。
- **書式の一覧に無いキーワード。** Routing Command Reference の `set path-selection` の書式には `multipath` がなく、
  NCS 5500 のガイドと TAC 217097 は使っています。`maximum-prefix` の書式には `discard-extra-paths` がなく、Cisco 8000 の
  Command Reference と ASR 9000 のガイドにはあります。機器の `?` は、どちらも一覧に表示します。
- **TCP-AO の綴り。** IOS XR の文書には、`accept-ao-mismatch-connection`(System Security Command Reference とガイドの例)、
  `accept-ao-mismatch-connections`(ガイドの書式)、「accept-non-ao-connections」(ガイドの本文)が並びます。機器では
  試していません。
- **`tcp ao` のキーの書式。** `key 1 SendID 5 ReceiveID 5`(Command Reference)と `key-id <id> send_id … receive_id …`
  (ガイドの書式)の 2 通りがあります。機器では `key <ID> SendID <n> ReceiveID <n>` の形が通りました。
- **TCP-AO の鍵の書き方。** IOS XE のガイドは、鍵を 16 進で 32 桁か 64 桁と定め、IOS XR のガイドの例は `keys1` のような
  文字列です。課題 M6-8 は、両側で同じ 16 進 32 桁の鍵を使います。
- **`password inheritance-disable`。** ASR 9000 と Cisco 8000 のコマンド リファレンスには `password-disable` だけが
  あります。機器の `password ?` は `inheritance-disable` を表示し、ネイバーの `?` は `password-disable` を
  「(Deprecated from 7.4.1) Replaced by password inheritance-disable」と表示します。

こうした点は、紙面の問題の正誤には使いません。ラボの課題は、食い違いのある機能を避けた形(best-external でなく追加パス、
既定値に頼らない上限)で組み、Check は機器がどう動いたか(セッションの確立、届いた経路、途切れの長さ、機器の表示)を見ます。

:::note
出典: RFC 7911(4 節・5 節)、RFC 5082(2 節・3 節)、RFC 5925、RFC 2385。Cisco: ASR 9000 の Routing Command Reference
(2026-09-08)、Cisco 8000 の BGP Command Reference(2026-09-11)、NCS 5500 の BGP Configuration Guide(IOS XR 25.1.x–25.4.x)、
ASR 9000 の Routing Configuration Guide(IOS XR 24.1.x–24.4.x と 26.1.x–26.3.x の「Implementing BGP」、24.x の「Implementing
Routing Policy」)、ASR 9000 の System Security Command Reference の「Keychain Management Commands」、Cisco 8000 の BGP
Configuration Guide(IOS XR 7.2.x)、ASR 9000 の IOS XR 5.1.1 のリリース ノート、TAC のテクニカル ノート 217097「Configure
and Verify BGP Path Selection in IOS-XR」と 213286「Understand BGP RIB-Failure and BGP Suppress-Inactive Command」、IOS XE
17.x の IP Routing Configuration Guide(「Configuring BGP Neighbor Session Options」「BGP Support for TCP Authentication
Option」「Configuring a Basic BGP Network」)、ASR 900 の IOS XE 17.1 の BGP Configuration Guide(「BGP PIC Edge for IP and
MPLS-VPN」)。SPCOR(350-501)のブループリント。いずれも 2026 年 11 月に確認。実測(2026-11-21): ラボ XRT-17(PE1 が IOS XRv
9000 26.1.1、PE2・PE3・P1・RR1 が IOS XRd 26.1.1、CE1・X1・X2・T が IOL 17.15)で、3 節の `LW-LDI` の行と、6.2 節の TCP-AO
の鍵と `tcp ao` のキー。同じ盤面の PE1 を IOS XRd 26.1.1 にし、入口の PE をもう 1 台(IOS XRv 9000 26.1.1)とその顧客を
足した盤面で、1 節の best-external と途切れの時間、3 節のリンクの停止と切り替えの時間と XRd の `LW-LDI` の行、4 節、5 節の
機器で確かめた値と表示と `?` の一覧、6.1 節の GTSM と `bgp suppress-inactive`。途切れは CE から T(203.0.113.1)への IP SLA の
udp-jitter(10 ms ごと、片道)で数え、障害は P1 の PE2 向けのインターフェイスの shutdown で起こしました。
:::
