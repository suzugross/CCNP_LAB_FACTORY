# M4 — IS-IS

CCNP Enterprise は OSPF と EIGRP を扱い、IS-IS にはほとんど触れません。一方、サービス プロバイダのコアの多くは IS-IS で動いており、
このトラックの後半(MPLS、セグメント ルーティング)もその上に積み上げます。そこでこの単元は、ほかの単元と違うことをします。
まずプロトコルそのものを、役に立つところでは OSPF と比べながら説明し、そのうえで IOS XR での書き方を示します。

この単元の出力は、IOS XRd 26.1.1 と IOL 上の IOS XE 17.15(ラボ XRT-04)で取得したものです。同じ IS-IS のコマンドは
IOS XRv 9000 26.1.1 でも同じ結果になりました。

## 1. IS-IS は何が違うか

IS-IS は OSPF と同じリンクステート プロトコルです。各ルータが自分の情報をフラッディングし、全ルータが同じデータベースを持ち、
全ルータがその上で SPF を計算します。違いは細部にあり、その多くは 1 つの事実から来ています。**IS-IS は IP の上で動きません。**
パケットはレイヤ 2 のフレームに直接載ります。もともと OSI のプロトコル スタック向けに作られ、IP は後から「運べる情報の 1 つ」として
加えられました。

この単元で出会う結果は次のとおりです。

- ルータは IP アドレスではなく、OSI のアドレスで識別されます(2 節)。
- プロトコルを足すのに IS-IS の新しいバージョンは要りません。IPv6 は同じプロセスの中で、新しいフィールドで運ばれます(8 節)。
  「IS-ISv3」はありません。
- ルータが広告するものはすべて、型の付いたフィールド **TLV**(タイプ・長さ・値)の並びです。新しい機能は新しい TLV の型です。
  ルータは理解できない型の TLV を読み飛ばします。だから拡張が容易で、同時に、いくつかの食い違いが黙って起きます(7 節)。

## 2. アドレス: NET

IS-IS のルータはそれぞれ **NET**(network entity title)を持ちます。16 進数のまとまりをドットで区切って書く OSI のアドレスです。

```console
49.0001.0102.5500.0001.00
\_____/ \____________/ \/
 area     system ID    NSEL
```

| 部分 | 長さ | 意味 |
|---|---|---|
| エリア アドレス | 1〜13 バイト | ルータが属するエリア。システム ID より前の全部。先頭は AFI で、`49` は私設のアドレスに慣例として使う値。 |
| システム ID | 6 バイト | ルータを識別する。IS-IS のドメイン全体で一意でなければならない。OSPF のルータ ID の役割。 |
| NSEL | 1 バイト | NET では常に `00`(「ルータ自身」の意味)。 |

NET は、OSI のネットワーク層アドレス全般を指す **NSAP**(network service access point)アドレスの一種です。
NSAP では最後の 1 オクテット(セレクタ)が、パケットがノード上のどの相手宛てかを示します。NET はセレクタが `00` の NSAP、
つまりルータ自身です。技術ブログでは、NET のことを「NSAP アドレス」と書いている例が多くあります。

同じものに出会う呼び名は次のとおりです。

| 呼び名 | 指すもの | 出会う場所 |
|---|---|---|
| NET(network entity title) | ルータのアドレス。セレクタは `00` | Cisco の IOS と IOS XR(`net` コマンド)、RFC 1142 |
| NSAP アドレス | OSI のネットワーク層アドレス全般。NET の意味で使われることも多い | OSI の規格、多くのブログ |
| ISO アドレス | NET | Juniper。インターフェイス(推奨はループバック)に設定する(`family iso address`) |
| NSEL、N-selector、SEL | 最後の 1 オクテット | Cisco、Juniper、RFC 1142 |
| システム ID、SysID | セレクタの前の 6 オクテット | どこでも |

エリアの言い方も 2 通りあります。OSI のアドレス形式は、システム ID より前の部分を AFI、IDI、上位の DSP に分けます(RFC 1237)。
そのため「49 が AFI、0001 がエリア ID」と書く文書があります。IS-IS 自身は、システム ID より前の全部を 1 つの値、
**エリア アドレス**として扱います(RFC 1142 の 7.1.1)。2 台のルータは共通のエリア アドレスを持つとき同じエリアにあり(1 台に、エリア アドレスだけが違う NET を
複数与えることもできます)、IOS XR も `Area Address: 49.0001` と表示します。このトラックで「エリア」と言うときは、エリア アドレスのことです。

システム ID は、読み戻せるようにループバック アドレスから作ることがよくあります。各オクテットを 3 桁で書き、
12 桁を 4 桁ずつに区切り直します。

```console
10.255.0.1  →  010.255.000.001  →  0102.5500.0001
```

これは慣習の 1 つで、決まりではありません。Juniper のガイドは、本番ではシステム ID を MAC アドレスなどのハードウェアの識別子から
作ることを勧めています。ドメイン内のシステム ID がすべて一意であれば、どちらでも動きます。

NET が意味することに注意してください。**ルータは丸ごと 1 つのエリアに属します。** OSPF ではエリアはインターフェイスの属性で、
2 つのエリアの境界はルータ(ABR)の中を通ります。IS-IS ではエリアはルータの属性で、2 つのエリアの境界はリンクの上を通ります。

## 3. レベルと隣接

IS-IS には、OSPF のバックボーン エリアとそれ以外のエリアの代わりに、2 つのルーティングのレベルがあります。

| レベル | 知っていること | OSPF で近い役割 |
|---|---|---|
| レベル 1(L1) | 自分のエリアのトポロジだけ | 非バックボーン エリアの内部ルータ |
| レベル 2(L2) | バックボーンのトポロジと、全エリアのプレフィックス | バックボーン ルータ |
| レベル 1-2(L1/L2) | 両方。データベースを 2 つ持ち、それぞれで SPF を計算する | ABR |

**バックボーン**はエリア番号ではありません。レベル 2 で動く全ルータがつながってできる鎖のことで、それらのルータが
どのエリアに属していても構いません。1 つのバックボーンが多くのエリアにまたがることもあります。

隣接はそこから決まります。

| 両方のネイバーが動かしているのが… | できるもの |
|---|---|
| レベル 1 で、エリアが共通 | L1 の隣接 |
| レベル 1 で、エリアが違う | レベル 1 では何もできない |
| レベル 2 | エリアにかかわらず L2 の隣接 |
| レベル 1 と 2 で、同じエリア | L1 と L2 の隣接 |

ルータは既定で両方のレベルを動かします。IOS でも IOS XR でも同じです。レベルはルータ全体で(*IS タイプ*)、または
インターフェイスごとに(*サーキット タイプ*)絞れます。両方のレベルを動かすルータは、指定しない限りすべてのインターフェイスで
両方のレベルのハローを送ります。片方のレベルには決して応答するネイバーがいない場所でも送ります。

## 4. ハロー、ポイントツーポイント リンク、DIS

ブロードキャスト ネットワーク(既定ではイーサネット)では、IS-IS はレベルごとに **DIS**(designated intermediate system)を選出します。
OSPF の DR にあたる役です。バックアップの DIS は無く、選出はプリエンプティブ(より良いルータが現れれば即座に交代)で、
各ルータは DIS とだけでなく、セグメント上のほかの全ルータと隣接を作ります。

プロバイダのネットワークのリンクの多くは、ちょうど 2 台のルータをつなぎます。これを**ポイントツーポイント**として設定すると、
DIS の選出も、DIS がセグメントのために作る余分なデータベースの項目(*疑似ノード*)も無くなります。両端がそろっている必要があります。
ポイントツーポイントのハローとブロードキャストのハローは別の種類のパケットで、ルータは想定していない種類を受け入れません。
IOS XR はそれをインターフェイスの表示で、最後に拒否した PDU として知らせます。

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/0 | include "Media|Rejected|DIS"
  Media Type:               LAN
  Last PDU Rejected:        15:00:22 (0.31 sec ago), 1496 octets, P2P IIH, P2P IIH on LAN Interface
    Priority (Local/DIS):   64/none (no DIS elected)
    Priority (Local/DIS):   64/none (no DIS elected)
```

ここでは XR01 がリンクを LAN として扱い、RT01 はポイントツーポイントのハロー(IIH= IS-IS のハロー)を送っています。
どちらの側も相手をネイバーとして表示しません。

## 5. データベース: LSP と TLV

各ルータはレベルごとに 1 つの **LSP**(link-state PDU)をフラッディングし、大きくなるとフラグメントに分けます。LSP ID は
システム ID、疑似ノード番号(ルータ自身は `00`)、フラグメント番号から成ります。

```console
0102.5500.0001.00-00
```

IOS と IOS XR は、分かっている場所ではシステム ID の代わりにホスト名を表示します。ルータが自分のホスト名を LSP で広告する(TLV 137)からです。
対応は `show isis hostname` で見られます。LSP の寿命は既定で 1200 秒で、持ち主はその前に更新します。

よく読むことになる TLV は次のとおりです。

| TLV | 運ぶもの |
|---|---|
| 1 | ルータのエリア アドレス |
| 129 | 対応するプロトコル(NLPID として表示: `0xcc` IPv4、`0x8e` IPv6) |
| 137 | ホスト名 |
| 2 / 22 | ネイバー(IS reachability)、ナロー形式 / ワイド形式 |
| 128、130 / 135 | IPv4 プレフィックス、ナロー形式 / ワイド形式 |
| 236 | IPv6 プレフィックス |
| 229、222、237 | マルチトポロジ: ルータが動かすトポロジと、トポロジごとのネイバーと IPv6 プレフィックス |

プレフィックスは SPF の木の葉にあたります。トポロジが変わらずにプレフィックスだけが変わったとき、ルータはそのプレフィックスの
経路だけを計算し直します(部分経路計算)。SPF 全体はやり直しません。

## 6. レベルのあいだ: ATT ビットと経路の漏らし

**レベル 1 からレベル 2** へは自動で流れます。L1/L2 ルータは、自分のエリアのプレフィックスを自分の L2 の LSP に入れます。

**レベル 2 からレベル 1** へは、既定では流れません。L1 ルータは自分のエリアの外を何も知りません。その代わりに、バックボーンを通じて
ほかのエリアに届く L1/L2 ルータが、L1 の LSP に **ATT(attached)ビット**を立て、L1 ルータはそれを立てている最寄りのルータに向けて
デフォルト ルートを入れます。設定なしでできる、OSPF の完全スタブ エリアに似た形です。このビットは `show isis database` の
`ATT/P/OL` の列に出ます。

ATT ビットは、レベル 2 が実際に機能していることが前提です。レベル 2 の隣接は上がっているのに、レベル 2 で学んだものを何も使えない
L1/L2 ルータ(どうしてそうなるかは 7 節)は、このビットを下ろします。するとエリア内のすべての L1 ルータからデフォルト ルートが消えます。

デフォルト ルートで足りないこともあります。MPLS は遠くのループバックごとにラベルを必要とし(M8)、デフォルト ルートで選ばれる出口が
最善とは限りません。選んだ L2 のプレフィックスを L1 へ写すことを**経路の漏らし**(route leaking)と呼びます。漏らしたプレフィックスには
**up/down ビット**(「レベル 2 から降りてきた」)が付き、L1/L2 ルータは印の付いたプレフィックスを決してレベル 2 へ戻しません。
同じエリアの 2 台の L1/L2 ルータのあいだのループを防いでいるのがこのビットです。IOS は漏らした経路を `ia`(inter-area)と表示します。

## 7. メトリック: ナローとワイド

すべてのインターフェイスのメトリックは、帯域幅にかかわらず既定で **10** です。OSPF と違い、IS-IS は指示しない限り帯域幅から
コストを出しません。

メトリックは、ルータからそのインターフェイスを通って**出ていく**コストです。リンクの両端がそれぞれ自分の値を設定し、
片方向 10、逆方向 1000 というリンクもありえます。

元々の IS-IS はメトリックに 6 ビットしか与えていません。この**ナロー** メトリックは、リンクあたり 1〜63、経路あたり 1023 までです。
**ワイド** メトリック(リンクあたり 24 ビット、16,777,214 まで)は後から、新しい TLV(ネイバーは 22、IPv4 プレフィックスは 135)で
加わりました。トラフィック エンジニアリングとセグメント ルーティングはワイド メトリックを必要とするので、プロバイダのネットワークは
ワイドへ移っています。IOS も IOS XR も、既定ではいまもナロー メトリックを生成します。

2 つの形式は相互に翻訳されません。ナローしか受け入れないルータは TLV 22 と 135 を読み飛ばし、ワイドしか受け入れないルータは
TLV 2、128、130 を読み飛ばします。そういう 2 台も隣接は作り(ハローはメトリックを運ばない)、LSP も交換しますが、互いのネイバーと
プレフィックスについての記述を無視します。ラボで、まだナローのままの XR01 は、ワイド形式で書かれた RT02 の LSP を持っています。

```console
RP/0/RP0/CPU0:XR01#show isis database detail level 2 RT02.00-00

IS-IS CORE (Level-2) Link State Database
LSPID                 LSP Seq Num  LSP Checksum  LSP Holdtime/Rcvd  ATT/P/OL
RT02.00-00            0x00000023   0x5afe        1097 /1200         0/0/0
  Area Address:   49.0002
  NLPID:          0xcc
  NLPID:          0x8e
  Hostname:       RT02
  Metric: 10         IS-Extended RT03.00
  Metric: 10         IS-Extended XR01.00
  IP Address:     10.255.0.2
  Metric: 10         IP-Extended 10.0.12.0/24
  Metric: 10         IP-Extended 10.0.23.0/24
  Metric: 10         IP-Extended 10.255.0.2/32
  Metric: 10         IP-Extended 10.20.0.0/16
  IPv6 Address:   2001:db8:255::2
  Metric: 10         IPv6 2001:db8:12::/64
  Metric: 10         IPv6 2001:db8:23::/64
  Metric: 10         IPv6 2001:db8:255::2/128
  Metric: 10         IPv6 2001:db8:1020::/64
```

そして、両方の隣接が上がっているにもかかわらず、RT02 も RT03 もレベル 2 のトポロジに位置づけられません(`**` は到達不能の意味)。

```console
RP/0/RP0/CPU0:XR01#show isis topology

IS-IS CORE paths to IPv4 Unicast (Level-1) routers
System Id          Metric    Next-Hop           Interface       SNPA
XR01               --
RT01               10        RT01               Gi0/0/0/0       *PtoP*

IS-IS CORE paths to IPv4 Unicast (Level-2) routers
System Id          Metric    Next-Hop           Interface       SNPA
XR01               --
RT02               **
RT03               **
```

この状態の XR01 は、ATT ビットを下ろしたレベル 1 の LSP を送ります(6 節)。そのため RT01 にはデフォルト ルートがありません。

メトリックの形式はレベルごとに選べるので、エリアはナローのまま、バックボーンだけをワイドへ移すことができます。ルータがレベルごとに
何を生成し、何を受け入れているかは `show isis` が示します。

ナローのレベルに 63 を超える値を書いても拒否されません。IOS XR はそれをコミットし、63 を広告し、警告をログに残します。

```console
RP/0/RP0/CPU0:Oct 21 15:28:01.197 UTC: isis[1003]: %ROUTING-ISIS-4-WD_METRIC_NOT_CONF : ISIS (CORE): In the topology IPv4 Unicast GigabitEthernet0/0/0/0 has a wide metric of 100 but level L1 is configured to generate narrow metrics.  Maximum narrow value 63 is used instead
```

## 8. IPv6: トポロジは 1 つか、複数か

IS-IS は IPv6 を 2 通りの方法で運べます。

| | 単一トポロジ | マルチトポロジ |
|---|---|---|
| SPF | IPv4 と IPv6 をまとめて 1 回 | トポロジごとに 1 回(IPv6 はトポロジ 2) |
| IPv6 プレフィックスの置き場 | TLV 236(IPv4 の TLV と並ぶ) | TLV 237(ネイバーは TLV 222) |
| 前提 | すべてのインターフェイスが同じプロトコルの組を動かすこと。さもないと IPv6 のパケットが運べない経路を通る | ワイド メトリック(マルチトポロジの TLV にはワイド形式しか無い) |
| IOS | 既定 | 設定が要る |
| IOS XR | 設定が要る | 既定 |

最後の 2 行をもう一度読んでください。**IOS と IOS XR は既定が逆です。**

両方とも既定のままだと、隣接は上がるのに IPv6 は交換されません。IOS XR は、隣接がどのトポロジを運んでいるかを示します。

```console
RP/0/RP0/CPU0:XR01#show isis adjacency detail
...
RT01           Gi0/0/0/0                *PtoP*         Up    29   00:00:37 Yes None None
  Area Address:           49.0001
  Neighbor IPv4 Address:  10.0.11.2*
  Topology:               IPv4 Unicast
  Topology (not running): [IPv6 Unicast (neighbor doesn't participate)]
```

IOS は、トポロジを告げてくるネイバーを `M-ISIS` と表示します。

```console
RT01#show clns neighbors
System Id       Interface     SNPA                State  Holdtime  Type Protocol
XR01            Et0/0         5254.00d3.7fa0      Up     25        L1   M-ISIS
```

単一トポロジで「すべてのインターフェイスが同じプロトコルを動かす」という規則は、IOS が隣接の段階で強制します。IPv4 と IPv6 を
動かす IOS ルータは、ハローで IPv4 しか告げないネイバーを受け入れません。そのネイバーは IOS XR 側では `Init` のままになり、
IOS 側にはまったく現れません。理由は IOS ルータの `debug isis adj-packets` が示します(`No usable IPv6 linklocal addresses in serial IIH`)。

IOS では、単一トポロジのとき 1 つのインターフェイス メトリックが両方のプロトコルに効きます。**IOS XR は、どちらのモードでも、
インターフェイスごとのメトリックをアドレス ファミリごとに持ちます。** 単一トポロジでは共通の SPF が IPv4 のネイバーのメトリックを
使いますが、リンクの IPv6 プレフィックスは、そのインターフェイスの IPv6 のメトリックで広告されます。

## 9. IOS XR での IS-IS

OSPF(M3)と同じく、すべてが 1 つのブロック `router isis <インスタンス>` の中にあり、インスタンス名は必須です。
ブロックの中には 3 種類のアドレス ファミリの節があります。

```console
router isis CORE
 net 49.0001.0102.5500.0001.00
 address-family ipv4 unicast        ← IPv4 のトポロジ全体
 !
 interface GigabitEthernet0/0/0/1
  point-to-point
  address-family ipv4 unicast       ← このインターフェイスの IPv4
  !
 !
```

| 場所 | 置くもの |
|---|---|
| プロセス | NET、IS タイプ、タイマー、LSP の認証 |
| プロセスの下の `address-family` | トポロジ全体の設定: メトリックの形式、単一トポロジ、経路の漏らし、再配布 |
| インターフェイス | ネットワーク タイプ、サーキット タイプ、ハローの設定、passive |
| インターフェイスの下の `address-family` | **そのインターフェイスでそのプロトコルを動かすかどうか**、とそのメトリック |

IOS の習慣で見落とすのは最後の行です。`router isis` の下に並べても、アドレス ファミリの無いインターフェイスは何もしません。

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/0
GigabitEthernet0/0/0/0      Disabled (No topologies cfg on the intf)
```

IOS でインターフェイスに書く `ip router isis` が、これと同じ判断にあたります。リリース 26.1.1 では、インターフェイスの下の
アドレス ファミリだけで隣接ができ、経路も交換されました。プロセスの下のアドレス ファミリは、その設定を置く場所です。

全体を見るには `show isis interface brief` を使います。2 つの `Adjs` の列はレベルごとの隣接の数(`-` はそのインターフェイスで
そのレベルが止まっている印)、`Topos` の列は動いているアドレス ファミリと設定したアドレス ファミリの数です。

```console
RP/0/RP0/CPU0:XR01#show isis interface brief

IS-IS CORE Interfaces
    Interface      All     Adjs    Adj Topos  Adv Topos  CLNS   MTU    Prio
                   OK    L1   L2    Run/Cfg    Run/Cfg                L1   L2
-----------------  ---  ---------  ---------  ---------  ----  ----  --------
Lo0                Yes    0    0      2/2        2/2     Up    1500    -    -
Gi0/0/0/0          Yes    1    -      2/2        2/2     Up    1497    -    -
Gi0/0/0/1          Yes    -    1      2/2        2/2     Up    1497    -    -
Gi0/0/0/2          Yes    -    1      2/2        2/2     Up    1497    -    -
```

ほかにラボで測ったこと:

- ループバックはハローを送りません(メディア タイプが `Loop`)。`passive` を付けるのは慣例で、必須ではありません。
- 隣接の変化は既定ではログに出ません(`log adjacency changes` で出るようになります)。
- NET を変えると、すべての隣接がいったん落ちます。古い LSP はパージされ、しばらくのあいだ `Purge Originator` と残り寿命 0 の形で
  データベースに残ります。

## 10. ルート ポリシーで漏らす

IOS XR では、経路の漏らしはルート ポリシー(M5)のアタッチ ポイントです。プロセスのアドレス ファミリの下で
`propagate level 2 into level 1 route-policy <名前>` と書くと、ポリシーが pass したレベル 2 の経路がレベル 1 へ写されます。
ポリシーなしの形はありません。アドレス ファミリごとに別の `propagate` 文を書きますが、両方で同じポリシーを使えます。
1 つの prefix-set に IPv4 と IPv6 のエントリを入れられるからです。

`show rpl route-policy <名前> attachpoints` は、このアタッチ ポイントを `inter-area-propagate` と表示します。XR01 のレベル 1 の LSP では、
漏らしたプレフィックスに印が付きます。

```console
RP/0/RP0/CPU0:XR01#show isis database detail level 1 XR01.00-00
...
  Metric: 10         IP 10.0.11.0/24
  Metric: 10         IP 10.255.0.1/32
  Metric: 20         IP-Interarea 10.255.0.2/32
  Metric: 30         IP-Interarea 10.255.0.3/32
  Metric: 10         IS RT01.00
  Metric: 10         IPv6 2001:db8:11::/64
  Metric: 10         IPv6 2001:db8:255::1/128
  Metric: 20         IPv6-Interarea 2001:db8:255::2/128
  Metric: 30         IPv6-Interarea 2001:db8:255::3/128
```

RT01 はそれをエリア間の経路として、ATT ビットが引き続き与えるデフォルト ルートと並べて入れます。

```console
RT01#show ip route isis
...
i*L1  0.0.0.0/0 [115/10] via 10.0.11.1, 00:02:44, Ethernet0/0
      10.0.0.0/8 is variably subnetted, 8 subnets, 3 masks
i L1     10.255.0.1/32 [115/20] via 10.0.11.1, 00:02:44, Ethernet0/0
i ia     10.255.0.2/32 [115/30] via 10.0.11.1, 00:00:29, Ethernet0/0
i ia     10.255.0.3/32 [115/40] via 10.0.11.1, 00:00:29, Ethernet0/0
```

prefix-set のエントリ `<プレフィックス> eq <長さ>` は、範囲の中でちょうどその長さのプレフィックスに一致します。
長さの範囲に一致する `ge` と `le`(M5)の仲間です。

## 11. コマンド名

| IOS | IOS XR |
|---|---|
| `show clns neighbors`、`show isis neighbors` | `show isis adjacency`、`show isis neighbors` |
| `show clns interface`、`show isis interface` | `show isis interface [brief]` |
| `show isis protocol`、`show clns protocol` | `show isis` |
| `show isis database [detail]` | `show isis database [detail] [level 1 \| 2] [LSP ID]` |
| `show isis topology` | `show isis topology`(IPv4)、`show isis ipv6 topology` |
| `show ip route isis` | `show route isis` |
| `show ipv6 route isis` | `show route ipv6 isis` |
| `debug isis adj-packets` | `show isis interface <名前>`(最後に拒否した PDU とその理由) |
| インターフェイスの `ip router isis` / `ipv6 router isis` | `router isis` の中のインターフェイスの下の `address-family ipv4 unicast` / `ipv6 unicast` |
| `isis network point-to-point` | `router isis` の中のインターフェイスの下の `point-to-point` |
| `isis circuit-type …` | `router isis` の中のインターフェイスの下の `circuit-type …` |
| `isis metric …` | インターフェイスのアドレス ファミリの下の `metric …` |

## 実践

ラボ **XRT-04** に移り、M4 の課題に取り組んでください。

<p class="tolab"><a href="/_learn?id=XRT-04">ラボ XRT-04 をワークスペースで開く</a> — <a href="41-m4-practice.html">課題</a></p>

:::note
出典: RFC 1142(ISO 10589 の本文。エリア アドレスは 7.1.1)、RFC 1237(NSAP の形式)、IOS の *IS-IS Overview and Basic Configuration*
(NET とそのセレクタ)、Junos の *IS-IS User Guide*(Juniper での呼び名と置き場所、システム ID の勧め)、ASR 9000 向け IOS XR の *Routing Configuration Guide*、*Implementing IS-IS*(既定: 各インスタンスはレベル 1 と 2、IPv6 は単一トポロジを
設定しない限りマルチトポロジ、単一トポロジは全インターフェイスで同じアドレス ファミリが必要)と *Implementing Routing Policy*
(inter-area-propagate のアタッチ ポイント)、2026 年 10 月に確認。RFC 5305(ワイド メトリック)、RFC 5308(IPv6)、RFC 5120(マルチトポロジ)、
RFC 5302(up/down ビット)。次は IOS XRd 26.1.1 と IOS XE 17.15 の実測によるものです: 拒否した PDU の表示、インターフェイスの
アドレス ファミリだけで足りること、メトリック形式の食い違いで ATT ビットが下りること、63 への切り詰めと警告、IOS の隣接チェックと
その debug の表示、単一トポロジでのアドレス ファミリごとのインターフェイス メトリック、ログの既定。
`49` が私設の AFI だという点は解説資料での説明で、この単元では規格と Cisco の文書の中には見つけられませんでした。
:::
