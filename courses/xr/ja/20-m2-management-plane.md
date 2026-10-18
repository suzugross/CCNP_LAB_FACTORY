# M2 — 管理プレーンの保護

IOS で堅牢化したルータには、いつも同じ問いがありました。誰がログインでき、どんな権限を持ち、どこから入れて、
ルータ自身に宛てたトラフィックをどれだけ受け付けるか。IOS XR でも問いは同じです。
答えの組み立て方が違い、そのうち 2 つ(権限とルータ宛てのトラフィック)は、何も設定しないうちから仕組みが動いています。

ここに示す出力は、すべて IOS XRv 9000 リリース 24.3.1 で取得したものです。

## 1. 権限はタスク ID

IOS はユーザに 0〜15 の特権レベルを与え、コマンドをレベルに割り当てます。IOS XR にレベルはありません。
どのコマンドも 1 つ以上の **タスク ID**(`ospf`、`rib`、`interface`、`aaa`、`bgp` など百ほど)に属し、
ユーザは各タスク ID を、読み取り・書き込み・実行・デバッグの 4 つの権限のいくつかと一緒に持ちます。

部品は 3 層で組み合わさります。

| 層 | 持つもの |
|---|---|
| **タスク グループ** | タスク ID と権限(他のタスク グループも含められる) |
| **ユーザ グループ** | タスク グループ(と他のユーザ グループ) |
| **ユーザ** | 1 つ以上のユーザ グループへの所属 |

よくある用途には定義済みのユーザ グループがあります。`root-lr`、`netadmin`、`sysadmin`、`operator`、
`cisco-support`、`read-only-tg` などです。ログインに使うラボのアカウントは `root-lr` と `cisco-support` に入っています。

`show user tasks` が、いまのセッションでできることを一覧にします。監視用に作ったアカウントでは次のとおりです。

```console
RP/0/RP0/CPU0:XR01#show user tasks
Task:       basic-services  : READ    WRITE    EXECUTE
Task:            interface  : READ             EXECUTE
Task:                 ospf  : READ
Task:                  rib  : READ
```

### コマンドに必要なタスクは何か

当て推量は要りません。`describe` の後にコマンド行を続けると、そのコマンドを実行せずに、必要なタスク ID を教えてくれます。

```console
RP/0/RP0/CPU0:XR01#describe show route
The command is defined in ip_rib_cmds.parser

User needs ALL of the following taskids:

	rib (READ)
```

答えは誰が尋ねるかで変わります。ラボのアカウントで `describe ping 10.0.12.2` を打つと
`root-system (EXECUTE)` と `basic-services (READ WRITE EXECUTE)` が表示されます。上の監視用アカウントで同じコマンドを打つと
`basic-services` だけが表示され、ping も通ります。`root-system` はそもそもタスク グループに入れられません。
アカウントを作るときは、そのアカウントでログインしてコマンドを確かめます。

### 権限が足りないときの見え方

ユーザのタスクの外にある exec コマンドは、その場で拒否されます。

```console
RP/0/RP0/CPU0:XR01#show route
% This command is not authorized
```

コンフィギュレーション モードは違います。ユーザは入れますが、すべての行が拒否されるので、コミットするものが何も残りません。

```console
RP/0/RP0/CPU0:XR01(config)#router ospf 1
% This command is not authorized
RP/0/RP0/CPU0:XR01(config)#commit
No configuration changes to commit.
```

`show running-config` は失敗すらしません。ユーザが読める部分を表示し、残りを省きます。監視用アカウントには、
すべてのインターフェイスが名前と説明だけで見え、アドレスは見えません。OSPF プロセスは全体が見えます。

```console
interface GigabitEthernet0/0/0/0
 description LINK1 to RT01
!
router ospf 1
 router-id 1.1.1.1
 area 0
  ...
```

何かが省かれたことは、どこにも表示されません。「アドレスが入っていない」設定を誰かから受け取ったら、このことを思い出します。

## 2. 管理セッションを受け付ける場所

IOS では、管理アクセスを回線ごとに絞ります。VTY 回線の `access-class`、回線ごとの `transport input` です。
IOS XR には代わりに、ルータ全体を対象にした機能があります。**Management Plane Protection(MPP)** です。

- MPP の設定が 1 つも無い間は、有効になっている管理プロトコルはすべてのインターフェイスで受け付けられます。
- どれか 1 つのインターフェイスを MPP の下に設定した時点で、プロトコルは許可したインターフェイスでだけ受け付けられます。
  他のインターフェイスは破棄します。
- インターフェイスは 2 種類です。**out-of-band**(管理インターフェイス。VRF もここで指定します)と **inband**
  (データ トラフィックも運ぶインターフェイス)。項目ごとにプロトコルを許可し、相手を限ることもできます。

効果は、ローカルの待ち受けの表 `show lpts bindings brief` に表れます(LPTS は 4 節で扱います)。
MPP の前は、SSH と Telnet のサーバがあらゆるインターフェイスで待ち受けています。

```console
 0/RP0/CPU0 TCP        LR IPV4 TCP    default   any          any,22 any
 0/RP0/CPU0 TCP        LR IPV4 TCP    default   any          any,23 any
 0/RP0/CPU0 TCP        LR IPV4 TCP    MGMT      any          any,22 any
```

SSH を管理インターフェイスだけに、Telnet を 1 つのデータ インターフェイスの 1 つの相手だけに許可すると、次のようになります。

```console
 0/RP0/CPU0 TCP        LR IPV4 TCP    default   Gi0/0/0/0    any,23 2.2.2.2
 0/RP0/CPU0 TCP        LR IPV4 TCP    MGMT      Mg0/RP0/CPU0/0 any,22 any
```

他の送信元からの Telnet は `% Connection refused by remote host` になります。`show mgmt-plane` は
同じ設定をインターフェイスごとに一覧にします。

### 自分を締め出さない

MPP は、このトラックで初めて、いま打っているセッションを切り得る機能です。`commit confirmed`(M1)はこのためにあります。
ラボで分かったことをもう 1 つ。

- 確認待ちのコミットがある状態で **コンフィギュレーション モードを抜ける** と、その場で取り消されます(M1)。
- そうではなく **セッションが切れた** 場合(締め出された場合)は、試行状態のままタイマーが切れるまで残り、
  それから取り消されます。その間、**他のセッションはコミットできません**。

```console
% Cannot commit because there is an unexpired trial/rollback session '00001000-00004dab-00000000'.
```

履歴には取り消しが独立した 1 件として残り、Client 列に `Rollback` と表示されます。

## 3. AAA サーバでのログイン

部品は IOS で知っているものと同じで、呼び方が少し違います。

| 部品 | IOS XR では |
|---|---|
| サーバとその鍵 | グローバルに、アドレスで定義する |
| サーバ グループ | サーバを並べた名前付きのグループ |
| 要求の送信元アドレス | プロトコルごと、VRF ごとに設定する |
| 認証・認可・アカウンティング | 方式リスト(`default` か名前付き) |
| セッションが使うリスト | **回線テンプレート**(`line console`、`line default`、名前付きのテンプレート) |

### 要求はどこから来るか

送信元インターフェイスを指定しないと、XR01 はサーバに向いたインターフェイスのアドレスから TACACS+ の要求を送ります。
サーバがルータをループバックで知っているなら、そのアドレスの鍵を持っていません。サーバのログにそう出ます。

```console
tac_plus[3146]: connect from 10.0.50.1 [10.0.50.1]
tac_plus[3146]: Error 10.0.50.1 : Invalid AUTHEN/START packet (check keys)
```

ルータの側では、何も壊れていないように見えます。次の点のせいで、ローカル アカウントは相変わらずログインできるからです。

### 次の方式が使われるとき

「サーバ グループ、次にローカル」という方式リストは、「サーバを試し、だめならローカルを試す」という意味では**ありません**。
Cisco の AAA ガイドには *"The subsequent methods of authentication are used only if the initial method returns an
error, not if the request is rejected."* とあります(後続の認証方式は、最初の方式がエラーを返した場合にだけ使われ、要求が拒否された場合には使われない)。

- サーバが「そのユーザはいない」と答える → ログインは失敗します。ローカル アカウントは参照されません。
- サーバが応答しない、またはやり取りが失敗する(鍵の誤り、送信元アドレスの誤り)→ ローカル アカウントが使われます。

したがって、サーバが動き出すと、ルータにだけ存在するアカウントはログインできなくなります。たいていはそれが望みどおりです。
鍵の不一致が見過ごされやすいのも、このためです。大事なものはローカルへのフォールバックで全部動いてしまいます。

### サーバから来る権限

TACACS+ サーバは、IOS XR のユーザに属性 `task` で権限を与えます。値にはタスク ID と権限、ユーザ グループ、またはその両方を並べます。
Cisco のガイドは例として `task = "rwx:bgp,#operator"` を挙げています。`#` の後は **ユーザ グループ** です。
ログイン後、`show user group` にサーバが割り当てたグループが、`show user tasks` に結果のタスクが表示されます。

ラボでは、`aaa authorization` の行を 1 つも設定しないうちから、サーバのユーザにタスクが届きました。
ルータはログインのたびにもう 1 度サーバに問い合わせていました。コンフィギュレーション ガイドの例は `aaa authorization exec` を使っています。
動作を明示したいなら設定し、自分のリリースで確かめます。

### コンソール

コンソールは `line console` テンプレートを使い、そのテンプレートが他のリストを指定しない限り `default` の方式リストを使います。
コンソールで常にローカル アカウントを使いたいなら、専用の方式リストを作り、テンプレートからそれを指す必要があります。

### 戻ってきたサーバ

サーバが応答しなくなると、XR01 はサーバをダウンと判断して保留にします。状態は `show tacacs` で見えます。

```console
Server: 10.0.50.10/49 opens=52 closes=47 aborts=8 errors=0
	status=down single-connect=false family=IPv4
	idle-timeout=0 on-hold=true
```

ラボでは、サーバが再び動き出してから約 25 秒の間、ログインがローカル アカウントに落ち続けました。
保留の時間は設定できます(`holddown-time`。グローバルにもサーバごとにも)。フォールバックを試すときはこれを覚えておきます。
サーバを再び起動したら、`status=up` になるのを待ってからサーバ経由の経路を試します。

## 4. ルータ宛てのトラフィック: LPTS

IOS では、ルート プロセッサを Control Plane Policing で守ります。気になるトラフィックのクラス マップを書き、
ポリシーをコントロール プレーンに付けます。そうするまで、何も制限されません。

IOS XR は最初から制限しています。**Local Packet Transport Services(LPTS)** は、ルータ宛てのすべてのパケットを
*流れ*(既知のネイバーからの OSPF、設定済みピアからの BGP、SSH、ICMP など)に仕分け、パケットがルート プロセッサに届く前に、
ラインカードのハードウェアで流れごとに制限します。クラスは書きません。既にある流れのレートを変えます。

ポリサーの表はラインカード単位です。

```console
RP/0/RP0/CPU0:XR01#show lpts pifib hardware police location 0/0/CPU0
flow_type            priority sw_police_id hw_policer_addr Cur. Rate  burst static_avgrate avgrate_type AggrAccepts   AggrDrops
OSPF-mc-known        high     2            217             2000       1000  2000           Static       84626         0
OSPF-mc-default      low      3            218             1500       750   1500           Static       2             0
ICMP-local           medium   12           227             1500       750   1500           Static       0             0
SSH-known            medium   27           242             300        150   300            Static       0             0
SSH-default          low      28           243             200        100   200            Static       0             0
ICMP-default         low      53           268             1500       750   1500           Static       168           0
```

- *known* と *default* は、たいていのプロトコルの 2 つの半分です。設定済みのピアや確立済みのセッションからのトラフィックと、
  それ以外です。知らないホストからの SSH は、少ない枠しかもらえません。
- `avgrate_type` は、既定のレートなら `Static`、設定したレートなら `Global` です。
- カウンタを見れば、パケットがどの流れに入ったかが分かります。ルータ自身のアドレスへの ping は `ICMP-default` ではなく
  `ICMP-local` に数えられます。
- ルート プロセッサのロケーションを指定すると、`This command is only supported on LC` と返ります。

ポリサーは平均だけでなくバーストも制限します。ICMP-local を 50 pps にすると、毎秒 5 回の ping はすべて通り、
ping の連打は約 60 % を失い、IOS の ping(応答が届くとすぐ次のエコーを送る)は 3 発に 1 発を失います。

```console
RT01#ping 10.0.12.1 repeat 5
!!.!!
Success rate is 80 percent (4/5), round-trip min/avg/max = 2/2/4 ms
```

ルータからの ping を「何かが壊れている」証拠とする前に、このことを思い出します。

## 5. アクセス リスト

ACL は IOS と同じように働き、書き方が違います。

- IPv4 の ACL は `ipv4 access-list <名前>` です。番号付きという別の種類はありません。`101` も受け付けますが、名前としてです。
- すべての行に行番号があります。省略すると、XR が 10、20、30… と振ります。
- ACL はインターフェイスの下で、方向を `ingress` か `egress` と明記して適用します。
- アドレスには、プレフィックス長もワイルドカード マスクも使えます。

ACL がトラフィックに対して行うことは IOS と同じです。インターフェイスの入力 ACL は、ルータ宛てのトラフィックもフィルタします。
暗黙の拒否で終わるリストはネイバーからの OSPF hello も落とし、Dead タイマーが切れると隣接関係が落ちます。
ラボでは、TCP だけを許可する入力 ACL で、そのリンクの OSPF 隣接関係が落ちました。

## 6. 習慣の何が変わるか

| IOS では | IOS XR では |
|---|---|
| ユーザに `privilege 15` か独自の特権レベルを与える | タスク ID から権限を組む: タスク グループ → ユーザ グループ → ユーザ |
| コマンドに必要な特権レベルを推測する | `describe <コマンド>`。使う本人のアカウントで |
| VTY 回線に `access-class` を付ける | Management Plane Protection。インターフェイスとプロトコルごと |
| 何かを守る前に CoPP を書く | LPTS は既に制限している。1 つの流れのレートを変える |
| サーバ障害は表に出ると信じる | `show tacacs` を見る。動いているローカルへのフォールバックは、死んだサーバを隠す |

## 実践

ラボ **XRT-02** に移り、M2 の課題に取り組みます。いくつかの課題は XR01 から締め出される可能性があり、確認は管理インターフェイス経由で
XR01 に到達します。危険な変更は、それぞれ確認つきコミットとして計画します。

<p class="tolab"><a href="/_learn?id=XRT-02">ワークスペースでラボ XRT-02 を開く</a> — <a href="21-m2-practice.html">課題の一覧</a></p>

:::note
出典: ASR 9000 向け IOS XR コンフィギュレーション ガイド(System Security の *Configuring AAA Services*、
*Implementing Management Plane Protection*、IP Addresses and Services の *Implementing LPTS*)と各コマンド リファレンス(2026 年 10 月に確認)。
次の点は文書ではなく 24.3.1 の実測によります。`show running-config` が読めない部分を省くこと、`describe` の答えがユーザで変わること、
`aaa authorization exec` なしでタスクが届くこと、約 25 秒の保留、ICMP-local のポリサーのバーストの挙動。他のリリースでは、頼る前に確かめてください。
:::
