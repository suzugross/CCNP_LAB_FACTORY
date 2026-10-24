# M8 — MPLS と LDP

プロバイダのコアは、顧客のルートを知らないまま、エッジの間で顧客のトラフィックを運びます。それを可能にするのがラベル
です。この単元では、IOS XR が LDP でラベル スイッチド パスを作るしくみを扱います。ネイバーとセッション、ラベル交換の保護、
IS-IS と LDP の足並みをそろえること、リンクの障害の間もセッションを保つこと、そして MPLS OAM によるパスの確認です。
CCNP Service Provider のブループリントでは 3.1(LDP 同期、セッション保護、LDP ネイバー、MPLS OAM)と 1.5.d(LDP の認証と
ラベル割り当てのフィルタリング)にあたります。同じ 3.1 の Unified MPLS は、続きの単元で扱います。

このページの出力は、IOS XRd 26.1.1 と、IOL 上の IOS XE 17.15 ルータ 3 台で取得しました(ラボ XRT-07)。同じ手順を
IOS XRv 9000 26.1.1 でも行い、同じ結果になりました。秒数はそのラボで測った値で、保証された値ではありません。

## 1. プロバイダのコアのラベル

### 1.1 BGP を持たないコア

ラボでは、顧客 A のネットワークが 2 台のプロバイダー エッジ(PE)ルータの配下にあります。XR01 の配下の 10.30.0.0/16 と、
RT02 の配下の 10.20.0.0/16 です。2 台の PE はこれらのルートを、ループバックをネクストホップにして iBGP で交換します。
コア ルータの RT01 と RT03 は IS-IS だけを実行しています。すべてのループバックとリンクを知っていますが、顧客のルートは
1 つも知りません。

これはプロバイダのコアのよくある設計です。コア ルータは顧客ルートの完全なテーブルを持たず、顧客を追加しても触るのは
エッジだけで済みます。ただし 1 つ結果が伴います。XR01 が顧客のパケットをただの IP として送ると、RT01 は 10.20.0.1 を
調べ、何も見つけられず、パケットを廃棄します。

```console
RT01#show ip route 10.20.0.0
% Subnet not in table

RP/0/RP0/CPU0:XR01#ping 10.20.0.1 source Loopback100 count 5
.....
Success rate is 0 percent (0/5)
```

MPLS はこれをラベルで解決します。XR01 は 10.20.0.0/16 を BGP で調べ、ネクストホップの 10.255.0.12(RT02 のループバック)
を見つけます。そしてパケットの前にラベルを付けます。RT01 が 10.255.0.12/32 に結び付けたラベルです。RT01 はラベルだけを
見て転送し、宛先アドレスを読むことはありません。1 つのラベルが表すパケットの集まりを **FEC**(forwarding equivalence
class)と呼びます。LDP では、FEC はルーティング テーブルのプレフィックスです。

### 1.2 ラベル スイッチング

各ルータはラベル転送テーブル(LFIB)を持ちます。エントリには、この入力ローカル ラベルのパケットを、このインターフェイス
から、この出力ラベルで送る、と書かれています。ラベル付きのパケットを受け取ったルータは、ラベルを次のルータのラベルに
**付け替える**(swap)か、**取り除き**(pop)ます。IOS XR ではテーブルは `show mpls forwarding`、IOS では
`show mpls forwarding-table` です。

```console
RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24000  Pop         10.255.0.11/32     Gi0/0/0/0    10.0.1.11       2340
24001  Pop         10.0.12.0/24       Gi0/0/0/0    10.0.1.11       0
24002  16          10.255.0.12/32     Gi0/0/0/0    10.0.1.11       0
24003  Unlabelled  10.255.0.13/32     Gi0/0/0/1    10.0.3.13       520
24004  17          10.0.23.0/24       Gi0/0/0/0    10.0.1.11       0

RT01#show mpls forwarding-table
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
16         Pop Label  10.255.0.12/32   666           Et0/1      10.0.12.12
20         Pop Label  10.255.0.1/32    1487          Et0/0      10.0.1.1
```

XR01 は RT02 宛ての顧客 A のパケットをラベル 16 で送ります。RT01 の自分のローカル ラベル 16 のエントリは `Pop Label` です。
RT02 はパスの最後のルータで、1 ホップ手前でラベルを外すようネイバーに求めています。これが **PHP**(penultimate hop
popping、最終ホップの 1 つ手前でのポップ)です。出口のルータは自分のプレフィックスについて予約済みのラベル 3、
**implicit null** をアドバタイズし、その手前のルータがポップします。RT02 はただの IP パケットを受け取り、自分のテーブルで
ルーティングします。そのテーブルでは顧客 A のネットワークが直接接続です。

`Unlabelled` は、ルータがローカル ラベルを持っているのに、ネクストホップからラベルを受け取っていないことを意味します。
ルータはラベルを外してただの IP としてパケットを送ります。ネクストホップが出口なら問題ありませんが、そのルートを持たない
コア ルータなら、ブラック ホールになります。上の出力で RT03 のループバックのエントリが `Unlabelled` なのは、RT03 との
セッションがまだ上がっていなかったからです。IOS XR はラベルを 24000 から、IOS は 16 から割り当てます。

## 2. LDP ネイバー

### 2.1 ディスカバリとセッション

Label Distribution Protocol(LDP、RFC 5036)は、各プレフィックスにローカル ラベルを結び付け、それをネイバーに知らせます。
2 台の LDP ルータは **リンク hello** で互いを見つけます。224.0.0.2 の UDP ポート 646 宛てのパケットで、各 LDP インターフェイス
で 5 秒ごとに送られ、15 秒保持されます。hello は 2 つの値を運びます。

| 値 | 中身 |
|---|---|
| LDP ID | ルータ ID とラベル空間。`10.255.0.1:0` と書く(0 = 全インターフェイスで 1 つのラベル空間) |
| トランスポート アドレス | ルータが TCP セッションに使うアドレス。既定はルータ ID |

2 台のルータは次に、トランスポート アドレスどうしの間で、ポート 646 への TCP セッションを開きます。開くのはトランスポート
アドレスの大きい側です(アクティブ ロール)。セッション上で、アドレスとラベルのバインディングを交換します。各ルータは、
最良パス上のネイバーだけでなく、すべてのネイバーからのバインディングを保持します。ルーティングが変わったとき、新しい
パスをすぐに使えるようにするためです(リベラル ラベル保持)。セッションは、ネイバーへの hello の隣接が少なくとも 1 つ
残っている間アップし続けます。

IOS XR の既定値は `show mpls ldp parameters` にあります。リンク hello は 5 秒ごとで 15 秒保持、ターゲット hello は 10 秒ごとで
90 秒保持、セッションのホールド タイムは 180 秒でキープアライブは 60 秒ごとです。

### 2.2 IOS XR の LDP

IOS XR には、インターフェイスの `mpls ip` がありません。LDP は独立したプロセスで、インターフェイスはその下に並べます。

```text
mpls ldp
 interface GigabitEthernet0/0/0/0
 interface GigabitEthernet0/0/0/1
```

既定の VRF では IPv4 が暗黙に有効になります。ループバックは LDP インターフェイスにできませんが、その /32 にはラベルが
付きます。`show mpls interfaces` は LDP が動作しているインターフェイスの一覧を表示します。

```console
RP/0/RP0/CPU0:XR01#show mpls interfaces
Interface                  LDP      Tunnel   Static   Enabled
-------------------------- -------- -------- -------- --------
GigabitEthernet0/0/0/0     Yes      No       No       Yes
GigabitEthernet0/0/0/1     Yes      No       No       Yes
```

インターフェイスを並べる代わりに、`router isis CORE` → `address-family ipv4 unicast` の下の `mpls ldp auto-config` で、
すべての IS-IS インターフェイスで LDP を動作させることもできます。このとき `show mpls ldp interface brief` は、
`IGP-Auto-Cfg` 列が 1 で `Config` が `N` のインターフェイスを表示します。

### 2.3 LDP ID とトランスポート アドレス

IOS XR は LDP ID を次の順で選びます。`mpls ldp` の下の `router-id`、次にシステムのルータ ID です。システムのルータ ID は
`show router-id` で見られ、リリース 26.1.1 にはそれを設定するグローバルのコマンドがありません。ラボでは Loopback0
(10.255.0.1)でした。Loopback1 のほうがアドレスが大きく、Loopback100 のほうが番号が大きいにもかかわらずです。
コンフィギュレーション ガイドは、ほかの変更で LDP ID が動かないよう、`mpls ldp` の下で `router-id` を設定することを
推奨しています。

トランスポート アドレスは、`mpls ldp` → `address-family ipv4` の `discovery transport-address` で(グローバルにか
インターフェイスごとに)設定しない限り、LDP ID に従います。どちらにしても、すべての LDP ネイバーがそこへのルートを持って
いる必要があります。ネイバーがルートを持っていないと、hello は行き来し続けますが、それ以外は何も起きません。XR01 の
ネイバー一覧は空のままで、XR01 は自分のトランスポート アドレスを `show mpls ldp parameters` でしか表示しません。
ネイバーのほうははっきり言います。

```console
RT01#show mpls ldp discovery detail
	Ethernet0/0 (ldp): xmit/recv
	    LDP Id: 10.255.0.1:0; no route to transport addr
	      Src IP addr: 10.0.1.1; Transport IP addr: 10.255.255.1

RP/0/RP0/CPU0:XR01#show mpls ldp parameters
  Router ID: 10.255.0.1
    Transport address:
      IPv4: 10.255.255.1
```

LDP ID は正しく見えます。トランスポート アドレスだけが、IS-IS が運んでいないループバックを指しています。通常のルールは、
両方に 1 つのループバックを使い、それを /32 として IGP にアドバタイズすることです。

## 3. ラベル配布の保護

### 3.1 認証

LDP セッションは TCP の MD5 署名オプションで保護できます。各 TCP セグメントが、共有キーで計算したダイジェストを運びます。
IOS XR では、キーはネイバーごとに、その LDP ID で `mpls ldp` の下に設定します。
`neighbor 10.255.0.13:0 password clear <key>` です。実行コンフィギュレーションには、`neighbor` ブロックの下に暗号化された
形でだけ残ります。LDP ID を付けない `neighbor password <key>` はすべてのネイバーに共通の既定値を設定し、
`neighbor <id>:0 password disable` は 1 つを除外します。

IOS では、キーは `mpls ldp neighbor <address> password <key>` で、`mpls ldp password required` はキーの無いセッションを
すべて拒否します。`for <acl>` が無いと、このルールは誰もキーを与えていないネイバーも含め、すべてのネイバーに適用されます。

両側は、食い違いを別々の言葉で報告します。

| 状況 | メッセージ |
|---|---|
| ネイバーが署名し、XR01 にそのキーが無い | XR01: `%IP-TCP-3-NOAUTH : Authentication info not programmed for the packet received from 10.255.0.13` |
| XR01 が署名し、ネイバーにキーが無い | XR01: `%IP-TCP-3-BADAUTH : Invalid MD5 digest from 10.255.0.11` |
| IOS がキーを要求し、ネイバーが何も送らない | IOS: `%TCP-6-BADAUTH: No MD5 digest from 10.255.255.1(57070) to 10.255.0.13(646)` |
| IOS がキーを要求し、そのピアのキーを持っていない | IOS: `%LDP-4-PWD: MD5 protection is required for peer 10.255.0.12:0, no password configured` |

新しいキーを受け取った IOS ルータは、既存のセッションをリセットされるまで保ちます。IOS XR はコミットの時点でセッションを
リセットします。

:::try
キーを持たないネイバーに既定のパスワードが何をするかを見ます。課題 M8-2 の後に行います。

1. XR01 の `mpls ldp` の下に `neighbor password clear CoreLdp-2026`(LDP ID なし)を加えてコミットします。
2. `show mpls ldp neighbor brief` と `show logging last 10` を実行し、XR01 で Loopback100 から 10.20.0.1 へ ping します。
3. `no neighbor password` でその行を外してコミットし、1 分以内に RT01 とのセッションが戻ることを確かめます。

ラボで測った結果: コミットの時点で RT01 とのセッションがダウンし、XR01 は `%IP-TCP-3-BADAUTH : Invalid MD5 digest from
10.255.0.11` を 10〜14 秒ごとに記録しました。RT03 とのセッションはアップのままでした。RT03 用のキーが既定値より優先される
からです。顧客 A のトラフィックは、行を外すまで止まりました。
:::

### 3.2 ラベルを受け取るプレフィックス

既定では LDP は、BGP が入れたものを除くルーティング テーブルのすべてのプレフィックスに、ローカル ラベルを結び付けます。
ループバック、リンクのネットワーク、そして XR01 の顧客 A の 10.30.0.0/16 のような接続されたネットワークです。それを
すべてのネイバーにアドバタイズします。BGP のルートのネクストホップになるのは PE のループバックだけなので、そのラベルの
ほとんどは使われません。

IOS XR には、これを絞る場所が 3 つあり、どれも `mpls ldp` → `address-family ipv4` → `label` の下にあります。

| コマンド | 絞るもの |
|---|---|
| `local allocate for {host-routes \| <acl>}` | そもそもローカル ラベルを受け取るプレフィックス |
| `local advertise to <ldp-id> for <acl>`(と `interface`) | どのローカル ラベルをどのネイバーに送るか |
| `remote accept from <ldp-id> for <acl>` | ネイバーからのどのラベルを保持するか |

ACL はプレフィックスに一致する IPv4 アクセス リストです。送信側と受信側のどちらで絞っても済むときは、コンフィギュレーション
ガイドは送信側での絞り込みを推奨しています。`allocate for host-routes` があると、XR01 は /32 にだけラベルを持ちます。

```console
RP/0/RP0/CPU0:XR01#show mpls ldp bindings brief
Prefix              Local      Advertised  Remote Bindings
                    Label        (peers)       (peers)
------------------  ---------  ----------  ---------------
10.0.1.0/24         -                   0                2
10.0.12.0/24        -                   0                2
10.30.0.1/32        ImpNull             2                0
10.255.0.1/32       ImpNull             2                2
10.255.0.12/32      24002               2                2
10.255.255.1/32     ImpNull             2                0
```

リンクのネットワークのリモート バインディングは残ります。RT01 と RT03 から来たもので、両者はまだそれにラベルを割り当てて
います。XR01 がもうアドバタイズしないローカル ラベルは、数分後に転送テーブルから消えます。IOS で同じ絞り込みをするのは、
`mpls ldp label` の下の `allocate global host-routes` です。

## 4. LDP と IS-IS の同期

### 4.1 ブラック ホール

IS-IS と LDP は別々に動作します。リンクで LDP に障害が起きても IS-IS がアップのままなら、IS-IS はそのリンクを選び続け、
ルータはトラフィックをラベルなしでそこへ送ります。それが害になるかは、受け取るのが誰かで決まります。次のルータが出口なら、
そのルータがただのパケットを自分でルーティングします。BGP を持たないコア ルータなら、パケットは廃棄されます。

ラボでは、XR01 が入口で、RT01 がコア ルータです。PRIMARY で LDP がダウンし IS-IS がアップしていると、XR01 の RT02 の
エントリは `Unlabelled` になり、顧客 A のトラフィックは止まりました。

```console
RP/0/RP0/CPU0:XR01#show mpls forwarding prefix 10.255.0.12/32
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24002  Unlabelled  10.255.0.12/32     Gi0/0/0/0    10.0.1.11       107

RP/0/RP0/CPU0:XR01#ping 10.20.0.1 source Loopback100 count 5
.....
Success rate is 0 percent (0/5)
```

逆方向は動き続けました。RT01 は RT02 のパケットをラベル付きで受け取り、ただの IP として XR01 に送りましたが、XR01 が
出口だからです。

:::try
IS-IS をアップのまま、PRIMARY で LDP を失わせます。課題 M8-3 の前に一度、後にもう一度行います。

1. XR01 の `mpls ldp` の下から `interface GigabitEthernet0/0/0/0` を外してコミットします。IS-IS はそのリンクで動作し続けます。
2. `show mpls forwarding prefix 10.255.0.12/32`、`show isis database verbose XR01.00-00 | include Metric`、
   `ping 10.20.0.1 source Loopback100 count 5` を実行します。
3. `interface GigabitEthernet0/0/0/0` を `mpls ldp` の下に戻してコミットします。

ラボで測った結果: 課題 M8-3 の前は、エントリは Gi0/0/0/0 のまま `Unlabelled` になり、RT01 へのメトリックは 10 のままで、
ping はすべて失われました。課題 M8-3 の後は、XR01 はすぐに RT01 へのリンクをメトリック 16777214 でアドバタイズし、ルートは
BACKUP に移り、ping はルートが移る間に 3 発失われてから通りました。
:::

### 4.2 IOS XR の同期

LDP-IGP 同期(RFC 5443)では、LDP がそのリンクで準備できるまで、IS-IS はリンクを使用可能な最大のメトリックでアドバタイズ
します。ワイド メトリックでは 16777214(0xFFFFFE)です。0xFFFFFF は予約されていて、リンクをトポロジから外してしまうので、
リンクは最後の手段として使える状態に残ります。IOS XR では、IS-IS でインターフェイスとアドレス ファミリーごとに有効に
します。

```text
router isis CORE
 interface GigabitEthernet0/0/0/0
  address-family ipv4 unicast
   mpls ldp sync
```

LDP がリンクを準備できたとみなすのは、そのリンクに hello の隣接があり、そのネイバーとのセッションがアップしていて、
ラベルの交換が済んだときです。`show mpls ldp igp sync` はリンクごとの状態を、`show isis interface` は
`MPLS LDP Sync (L1/L2)` と `LDPv4 Sync Status` を表示します。

```console
RP/0/RP0/CPU0:XR01#show mpls ldp igp sync
GigabitEthernet0/0/0/0:
  VRF: 'default' (0x60000000)
  Sync delay: 10 sec
  Sync status: Not ready (No hello adjacency)
GigabitEthernet0/0/0/1:
  VRF: 'default' (0x60000000)
  Sync delay: 10 sec
  Sync status: Ready
    Peers:
      10.255.0.13:0

RP/0/RP0/CPU0:XR01#show isis database verbose XR01.00-00
  Metric: 16777214   IS-Extended RT01.00
  Metric: 100        IS-Extended RT03.00
```

`mpls ldp` の下の `igp sync delay on-session-up <5-300>` は、LDP がそのリンクで再び準備できてから、その秒数だけリンクを
高いメトリックのままにします。その間、状態は `Deferred (8 sec remaining)` と表示されます。ラボでは、新しいセッションの後に
も、セッション保護が保っていたセッションにリンクの hello が戻ったときにも働きました(5.2 節)。リリース 26.1.1 には、
LDP プロセスの起動時のための 2 つ目の形 `on-proc-restart` があり、素の `igp sync delay <秒>` はありません。

各ルータが決めるのは、リンクの自分の方向だけです。XR01 の同期は XR01 のトラフィックをリンクから遠ざけ、RT01 の同期は
RT01 のトラフィックを遠ざけます。IOS では、`router isis` の下の `mpls ldp sync` で、LDP を動作させているすべての
インターフェイスで有効になります。ラボでは、XR01 がまだ LDP をまったく動作させていない間から、RT01 は XR01 へのリンクを
16777214 でアドバタイズしていました。

## 5. セッション保護

### 5.1 ターゲット hello でセッションを保つ

LDP セッションは、最後の hello の隣接が終わると終わります。PRIMARY に障害が起きると、RT01 からのリンク hello が止まり、
隣接は 15 秒でタイムアウトし、セッションはダウンし、XR01 は RT01 のラベルを忘れます。リンクが戻ると、リンクがラベル付きの
トラフィックを運べるようになる前に、セッションを作り直してラベルを交換し直す必要があります。

**セッション保護**は、同じネイバーへの 2 つ目の隣接を加えます。**ターゲット hello** です。ネイバーの LDP ID 宛てのユニ
キャストの UDP として送られ、ルーティングがどの経路でも届けられます。PRIMARY がダウンしている間はターゲットの隣接が
セッションを保ち、ラベルは残ります。IOS XR では `mpls ldp` の下の 1 行です。

```text
mpls ldp
 session protection [for <acl>] [duration <seconds>]
```

ACL はネイバーを LDP ID で選びます。`duration` が無いと、リリース 26.1.1 はリンクの隣接が終わってから 86400 秒(24 時間)
セッションを保ちます。コマンド リファレンスも同じ既定値を示していますが、コンフィギュレーション ガイドは保護が無期限だと
書いています。ネイバーはターゲット hello に応答する必要があります。IOS では `mpls ldp discovery targeted-hello accept`、
IOS XR では `mpls ldp` → `address-family ipv4` の下の `discovery targeted-hello accept` です。自分もセッション保護を
動作させているネイバーは、それが無くても応答します(RFC 5036 の 3.5.2)。

`show mpls ldp neighbor <id> detail` が状態を表示します。

| 状態 | 意味 |
|---|---|
| `Incomplete` | ターゲット hello を送っているが、ネイバーが応答しない |
| `Ready` | ターゲットの隣接と、少なくとも 1 つのリンクの隣接がアップしている |
| `Protecting` | ターゲットの隣接だけがアップしている。ホールドアップ タイマーが動いている |

```console
RP/0/RP0/CPU0:XR01#show mpls ldp neighbor 10.255.0.11:0 detail
  LDP Discovery Sources:
    IPv4: (2)
      GigabitEthernet0/0/0/0
      Targeted Hello (10.255.0.1 -> 10.255.0.11, active)
  Session Protection:
    Enabled, state: Ready
    ACL: 'LDP-SP', Duration: 600 sec
```

ターゲット hello を受け入れない RT03 に対しては、状態は `Incomplete` のままで、`show mpls ldp discovery` はそのターゲット
hello を `xmit` だけと表示します。

### 5.2 保護と同期を組み合わせる

セッション保護が保つのはセッションで、リンクではありません。PRIMARY がダウンしている間はそこに hello の隣接が無いので、
同期はリンクを高いメトリックのままにし、トラフィックは BACKUP を使います。ラボでは、黙った故障の 12 秒以内にリンク hello が
タイムアウトしてトラフィックが BACKUP に移り、PRIMARY の IS-IS の隣接はその後さらに 10 秒ほどアップのままでした。
同期は、セッションが残るかどうかにかかわらず、LDP がリンクを失った時点でトラフィックを移します。

PRIMARY が戻ったとき、セッションは RT01 のラベルをすべて持ったまま残っています。リンク hello が再開し、10 秒の待ちが働き
(`Sync status: Deferred (8 sec remaining)`)、ラボではリンクの 12 秒後にトラフィックが PRIMARY に戻りました。保護が無いと、
セッションは障害の間に終わっていて、まず新しいセッションを作る必要があり、トラフィックが戻ったのは約 20 秒後でした。
この差は、交換するラベルの数が多いほど大きくなります。

:::try
ポートを落とさずに PRIMARY を切断し、RT01 とのセッションを見ます。課題 M8-4 の後に行います。

1. CML で、XR01 GigabitEthernet0/0/0/0 と RT01 Ethernet0/0 の間のリンクを選びます。その **Settings** タブで **Loss** を 100
   にし、**Enable** にチェックを入れて **Apply** を押します。
2. XR01 で `show mpls ldp neighbor 10.255.0.11:0 detail` と `show mpls ldp bindings 10.255.0.12/32` を数秒ごとに 1 分間
   実行します。状態が変わる時点と、RT01 のラベルが残っているかを記録します。
3. 同じタブの **Reset** を押します。`show mpls ldp neighbor 10.255.0.11:0` を実行し、`Up time` を障害の前と比べます。

ラボで測った結果: 12 秒以内に状態は `Protecting` になり、継続時間からカウントダウンする `Holdup timer remaining` が
表示され、10.255.0.11:0 からのバインディングは残りました。RT01 との IS-IS の隣接がまだアップしている間に、RT02 へのルートは
BACKUP に移りました。Reset の後、`Up time` はそのまま続き、10 秒の待ちの後にルートは PRIMARY に戻りました。保護が無いと、
セッションは障害の間に終わり、Reset の後は新しいセッションでした。
:::

## 6. MPLS OAM

### 6.1 LSP ping と traceroute

ラベル スイッチド パスが壊れていても、普通の ping は成功することがあります。ラベルの無いパケットでも、たどり着ける場合が
あるからです。MPLS OAM(RFC 8029)はパスそのものを試験します。**MPLS エコー要求**は、どのルータも IP として転送しない
ように 127.0.0.1 を宛先にした、ポート 3503 宛ての UDP パケットです。試験する FEC を運び、その FEC のラベルを付けて送られ
ます。出口はエコー応答を返し、既定ではただの UDP パケットとして返します。LSP traceroute は TTL を増やしながら要求を送り、
各ルータはそのラベルをどう扱うかを報告します。

IOS XR は、グローバル コマンド `mpls oam` を入れて初めて MPLS OAM を動作させます。自分が始める試験にも、応答する要求にも
必要です。無いと、試験はすぐに止まります。

```console
RP/0/RP0/CPU0:XR01#ping mpls ipv4 10.255.0.12/32 repeat 3
% MPLS Embedded Management Subsystem is not running.
To enable, use 'mpls oam' global config command.
```

そして、RT02 からの traceroute は XR01 の手前のルータで終わります。IOS は何も設定しなくても応答します。

```console
RT02#traceroute mpls ipv4 10.255.0.1/32 timeout 1 ttl 4
  0 10.0.12.12 MRU 1500 [Labels: 20 Exp: 0]
L 1 10.0.12.11 MRU 1500 [Labels: implicit-null Exp: 0] 1 ms
. 2 *
. 3 *
. 4 *
```

| コード | 意味(RFC 8029 のリターン コード) |
|---|---|
| `!` | 応答したルータがその FEC の出口(3) |
| `L` | ラベル スイッチされ、ラベル付きのインターフェイスから出る(8) |
| `B` | ラベル スイッチされたが、ラベルなしで送り出される |
| `.` | タイムアウトまでに応答が無い |
| `Q` | 要求を送れなかった |
| `N` | その FEC のラベル エントリが無い(11) |

等コストのパスが複数あるときは、IOS XR の `traceroute mpls multipath ipv4 <prefix>` が、127/8 の宛先アドレスを変えながら
それぞれを見つけて試験します。

### 6.2 explicit null と最後のホップ

PHP では出口がただの IP を受け取り、コアがラベルにマークしたトラフィック クラス(EXP ビット)は 1 ホップ手前で失われます。
そのマークが必要なルータは、自分のプレフィックスについて、代わりに予約済みのラベル 0、**explicit null** をアドバタイズ
します。その手前のルータはポップする代わりにラベル 0 に付け替え、出口が自分でラベルを外します。IOS XR では
`mpls ldp` → `address-family ipv4` → `label` → `local` → `advertise` の下の `explicit-null`、IOS では
`mpls ldp explicit-null` です。

```console
RT01#show mpls forwarding-table 10.255.0.1
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
20         explicit-n 10.255.0.1/32    0             Et0/0      10.0.1.1

RT02#traceroute mpls ipv4 10.255.0.1/32 timeout 1 ttl 4
  0 10.0.12.12 MRU 1500 [Labels: 20 Exp: 0]
L 1 10.0.12.11 MRU 1500 [Labels: explicit-null Exp: 0] 1 ms
! 2 10.0.1.1 3 ms
```

ラボでは、XR01 のコミットから RT01 が `Pop Label` から `explicit-n` に切り替わるまで 20〜30 秒かかりました。

:::try
コアを通る普通の traceroute を、課題 M8-5 の前と後で比べます。

1. RT02 で `traceroute 10.30.0.1 source Loopback100 timeout 1 probe 1 ttl 1 4` を実行します。
2. 課題 M8-5 の後、30 秒ほど待ってからもう一度実行します。

ラボで測った結果: 前は、1 ホップ目が `*` で、2 ホップ目が XR01(10.0.1.1)でした。後は、1 ホップ目が
`10.0.12.11 [MPLS: Label 20 Exp 0]` でした。ラベル付きのパケットを TTL で廃棄したコア ルータは、時間超過のメッセージを
パスに沿って先へ送ることができ、出口がそれを送り返します。PHP では RT01 がラベル 20 について次にするのはポップで、
応答は戻ってきませんでした。付け替えるラベル 0 があると、RT01 の応答は XR01 を経由して RT02 に届きました。RT01 自身は
顧客 A へのルートを持っていません。
:::

### 6.3 ラベルと MTU

ラベル 1 つで 4 バイト増えます。ラボのコア リンクの MTU は、IOS では IP について 1500 バイト、IOS XR では Ethernet ヘッダを
含めて 1514 バイトで、ラベル付きのパケットには 1500 バイトが残ります。1500 バイトの IP パケットにラベルを 1 つ付けると
1504 バイトになり、収まりません。

```console
RP/0/RP0/CPU0:XR01#ping 10.20.0.1 source Loopback100 size 1500 df-bit count 3
...
Success rate is 0 percent (0/3)

RP/0/RP0/CPU0:XR01#ping mpls ipv4 10.255.0.12/32 sweep 1490 1510 4 repeat 1
Sending 1, [1490..1510]-byte MPLS Echos to 10.255.0.12/32,
!!!QQQ
```

実際のコアでは、ラベルの分の余裕を残すよう、すべてのコア リンクの MTU を両端で上げます。レイヤ 3 VPN ではラベルが
もう 1 つ増え(単元 M9)、ほかのサービスではさらに増えます。

:::try
ラベル付きでコアを通る最大のパケットを見つけます。

1. XR01 で、DF ビットを立てて Loopback100 から 10.20.0.1 へ、`size 1500` と `size 1496` で 1 回ずつ ping します。
2. `ping mpls ipv4 10.255.0.12/32 sweep 1490 1510 4 repeat 1` を実行し、`!` が `Q` に変わる位置を読みます。
3. XR01 の Loopback0 から RT02 の Loopback0 へ、`size 1500 df-bit` で ping します。

ラボで測った結果: 1500 バイトは両方向とも失敗し、1496 は通りました。sweep は 1490〜1498 を送り、1502 以上は送れません
でした。ループバックどうしの 1500 バイトの ping も失敗しました。XR01 は、LDP のプレフィックス宛ての自分のトラフィックにも
ラベルを付けるからです。
:::

## 7. コマンド名

| IOS では | IOS XR では |
|---|---|
| インターフェイスの `mpls ip` | `mpls ldp` の下の `interface <name>`(または IS-IS の `mpls ldp auto-config`) |
| `mpls ldp router-id Loopback0 force` | `mpls ldp` の下の `router-id <address>` |
| インターフェイスの `mpls ldp discovery transport-address` | `mpls ldp` → `address-family ipv4`(またはインターフェイス)の下の `discovery transport-address` |
| `mpls ldp neighbor <address> password <key>` | `mpls ldp` の下の `neighbor <ldp-id>:0 password clear <key>` |
| `mpls ldp password required` | (相当するものは無い。ネイバーごとのキーか既定のキー) |
| `mpls ldp label` の下の `allocate global host-routes` | `label` → `local` の下の `allocate for host-routes` |
| `router isis` の下の `mpls ldp sync` | `router isis` のインターフェイスのアドレス ファミリーの下の `mpls ldp sync` |
| `mpls ldp session protection [for <acl>] [duration …]` | `mpls ldp` の下の `session protection [for <acl>] [duration …]` |
| `mpls ldp discovery targeted-hello accept` | `mpls ldp` → `address-family ipv4` の下の `discovery targeted-hello accept` |
| `mpls ldp explicit-null` | `label` → `local` → `advertise` の下の `explicit-null` |
| (既定で有効) | `mpls oam` |
| `show mpls forwarding-table`、`show mpls ldp bindings` | `show mpls forwarding`、`show mpls ldp bindings` |
| `show mpls ldp discovery detail` | `show mpls ldp discovery`、`show mpls ldp parameters` |

## 実践

ラボ **XRT-07** で M8 の課題に取り組んでください。このラボは IOS XRd を使うので、構築は約 4 分です。

<p class="tolab"><a href="/_learn?id=XRT-07">ワークスペースでラボ XRT-07 を開く</a> — <a href="81-m8-practice.html">課題</a></p>

:::note
出典: IOS XR の *MPLS* のコンフィギュレーション ガイド(ASR 9000、リリース 26.1.x〜26.3.x)とコマンド リファレンスの
「Implementing MPLS Label Distribution Protocol」(LDP の有効化と暗黙の IPv4 アドレス ファミリー、ルータ ID の順、
トランスポート アドレス、ネイバーのパスワードと既定のパスワード、ラベルの割り当て・アドバタイズ・受け入れの制御、
explicit null、セッション保護とその状態、IGP 同期と遅延)と「Implementing MPLS OAM」、IOS XR の *Routing* の
コンフィギュレーション ガイドとコマンド リファレンスの「Implementing IS-IS」(MPLS LDP IS-IS 同期、メトリック 16777214、
`mpls ldp auto-config`)、IOS XE 17.x の MPLS のコンフィギュレーション ガイドの「MPLS LDP Session Protection」と
「MPLS LDP MD5 Global Configuration」(2026 年 10 月に確認)、RFC 5036(LDP、アクティブ ロール、ターゲット hello)、
RFC 5443(LDP-IGP 同期)、RFC 8029(LSP ping と traceroute、リターン コード)。次の項目はラボ XRT-07 での実測による
ものです。Loopback0 から取られる LDP ID、ルートの無いトランスポート アドレスとそのメッセージ、両側の MD5 のメッセージと
コミット時のリセット、`allocate for host-routes` の後のラベル、同期が無いときのブラック ホール、セッション保護の間の
`Not ready (No hello adjacency)` の状態、既定の継続時間 86400 秒、送受両方に必要な `mpls oam`、explicit null での
traceroute、ラベル 1 つでの MTU。
:::
