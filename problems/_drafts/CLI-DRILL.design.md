# コマンドの素振り台(BL-278)— 試作の記録

2026-11-15 ユーザ依頼「コマンドシミュレータの試作品を、今起動中のラボには手をつけずに」で着手。BL-278 の取り決め
(本格的なシミュレータではなく素振り・入口は読み物と独立の 2 つ・手始めは J1・採ったヘルプの文言は公開側に置かない)に沿って作った。

## 1. 置き場と動かし方

| 物 | 置き場 | 公開 |
|---|---|---|
| CLI の動き(DOM に依らない) | `games/cli-drill/junos.js` | 公開 |
| 画面(家・お題・ルールの枠・読み物に埋め込む形・試験) | `games/cli-drill/index.html` | 公開 |
| 構文の骨組み(どの語がどこに置けるか・値の型・show の並び) | `games/cli-drill/syntax/junos.txt` | 公開 |
| 練習(J1 のお題 8 本)・盤面(初めの設定とトポロジファイルの場所) | `games/cli-drill/drills/junos-j1.yml` | 公開 |
| 実機の記録の再現の試験(20 件) | `games/cli-drill/tests/junos.yml` | 公開 |
| 組み立て・配信・試験の道具 | `topologies/cli_drill.py`(harvest / build / serve / selftest) | 公開 |
| 実機から採った `?` の一覧 | `private/cli-drill/junos/help.json`(harvest が作る) | 非公開 |
| 公式文書の文言(モードのコマンドの一覧) | `private/cli-drill/junos/doc.json` | 非公開 |
| 束ねたもの(配信する物) | `private/cli-drill/site/` | 非公開 |

```
python3 topologies/cli_drill.py harvest      # poc/junos/*.log から ? の一覧を採る
python3 topologies/cli_drill.py build        # 束ねる(harvest 済みでなければ先に走る)
python3 topologies/cli_drill.py serve        # 0.0.0.0:8894 で配信(コンテナの中だけ。開発コンテナが LAN に出すのは 8899・8897 だけ)
python3 topologies/cli_drill.py selftest     # 見えないブラウザで ?selftest=1(お題 8×4 項目＋記録の再現 20 件)
```

★LAN から開くのは **`http://10.1.10.3:8899/_read/_cli-drill/`**。build が束を `reading/_cli-drill/`(.gitignore 済み)へも写し、ポータルの
`/_read/`(reading/ をディスクからそのまま配る)に乗せる。コード変更もポータルの再起動も要らない。`_` で始まるので棚には載らず、
Drive への同期(`reading/_offline/` だけ)にも入らない。

画面の URL 引数: `?drill=<ID>`(そのお題から)・`&embed=1`(読み物の枠に埋め込む形)・`?demo=reading`(読み物の区切りの見本)・
`?drill=j1-ps-1&uitest=1`(キー操作の試験。j1-ps-1 専用)。記録は閲覧者のブラウザの localStorage に「解いたお題」だけ。

## 1.5 盤面の図(2026-11-16 ユーザ要望で追加)

お題の画面の課題文の下に、盤面の図を出す(隠す/出すは閲覧者のブラウザに覚える。読み物に埋め込む形では初めは隠す)。

- **一次情報から機械的に起こす**(目で写さない): 練習の `topology:` に書いたトポロジファイル(JNT-02 の clab.yml)の
  ノード・リンク・座標(labels の graph-posX/Y)と、各ノードの startup-config(Junos は set の形にして・FRR は frr.conf)から
  `cli_drill.py` の `topo_model` が組み立て時に作る。種類の判定(`clab_ops.node_family`・ホスト役)と ethN → 機器の中の名前
  (`lab_console.clab_if`)はワークスペースの結線図と共通の関数。
- 図に出すもの: 機器(名前・lo のアドレス・AS)、リンク(両端の口の名前・アドレスの末尾・網)、リンクの札(両端の口が同じ area に
  入っていれば `OSPF area …`・片方の BGP の neighbor が相手の口のアドレスなら eBGP/iBGP)。太枠= そのお題で打つ機器。
- 機器を押すと要点(口とアドレスと description・router-id と AS・静的経路・OSPF の口・BGP の相手・FRR が network で送る経路と
  default-originate)。network で出す経路のための Null0 の静的経路は「BGP で送る経路」の欄に含めて、静的経路の欄には出さない。
- 両端のアドレスの網が食い違えば組み立てを止める。練習の機器が図に無くても止める。selftest で横並び・縦並びの両方を描いて確かめる。
- 並び: 横並びの字が 3/4 より小さくなる幅(スマホなど)では縦並び。図は初めの設定のもので、お題で設定を変えても変わらない(ルールの枠に注記)。

## 2. 出す文の 3 種類(取り違えない仕組み)

端末に出す文は出どころで色を分ける(画面のルールの枠に凡例)。

| 種類 | 色 | 中身 |
|---|---|---|
| dev | 白 | 実機の記録にある文言そのもの(エラー・commit の結果・`?` の一覧の行) |
| doc | 青 | 公式文書(CLI User Guide)の文言(運用・設定モードの `?`・`<[Enter]>`) |
| dim | 薄い | 語と形は実機の設定にあるが、`?` の説明の文はまだ採っていない語 |
| sim | 黄 | 素振り台の注記。実機の文言を採っていない場面と、扱わないこと |

★実機の文言を採っていない場面(設定モードの知らない語・値の誤りなど)は、それらしい文を作らず sim の注記で出す。

## 3. 実機の記録で確かめた動き(selftest の「記録」20 件)

- `show | compare` の形(見出しの切り方・+ が先で − が後・M の値は − が先): e2e/s1-1.log と 1 字違わず一致。
- `show` の「子が 1 つの入れ物は 1 行にまとめる」は文ごとの性質: `then accept;`・`family inet {`・`route … next-hop …;`・
  `community … members …;` はまとめ、`from { route-filter …; }` はまとめない(expJ1-examples.log・expJ0-cli.log)。骨組みの `@1`。
- 並び: group の中= type → import → export → peer-as → neighbor・then の中= local-preference → community、accept が最後・
  from の中= protocol → route-filter(いずれも記録の show)。
- `missing argument.` とキャレットの位置(入れ物で終わる set・policy-statement の名前で終わる set)。
- `?` の一覧 8 階層(interfaces *・policy-options・policy-options defaults(+ route-filter)・policy-statement *・protocols bgp・
  bgp defaults・bgp group *)は記録の行をそのまま出す。
- commit のライセンスの warning(bgp → ospf の順)・`commit complete`・`configuration check succeeds`・
  定義のないポリシー/prefix-list の `Policy error` と `error: configuration check-out failed`。
- exit の yes/no・入り直した時の `The configuration has been changed but not committed`・`rollback 0` の `load complete`・
  `warning: statement not found`・運用モードの `unknown command.`・`syntax error, expecting <command>.`(configure し忘れの set)。
- 空白と Tab の補完・`?` の後に打った行が残る: 公式文書 CLI User Guide p.39〜40・p.62〜64。

## 4. 記録どうしが揺れている・まだ確かめていない所(実機から木を採る時に照合する)

| 論点 | いまの扱い | 根拠・残り |
|---|---|---|
| `show \| compare` の字下げ | 印＋空白 3(4 桁)に揃えた | 記録 10 例で見出しにより 3〜6 桁と揺れる(`-  host-name`・`+    description`・`+     filter POC-T`)。規則は未解明 |
| 一番上の並び | interfaces → routing-options → policy-options → protocols | policy-options が protocols より先なのは compare の記録 3 例から。show の全体の並びは未採取 |
| `!確認` の付いた語(骨組み) | 置いた | bgp/ospf の階層の import/export の並び・from の prefix-list の形・then の external の形 |
| 設定モードの知らない語・値の誤り | sim の注記 | 実機の文言(syntax error. など)は未採取 |
| accept と reject | 片方を置くと他方が消える | 未確認 |
| edit で無い項目に入る | 作らない(set した時に作る) | 未確認 |
| community が未定義 | commit を止め、sim の注記 | 実機の文言は未採取(断られることも未確認) |
| term の外の from の prefix-list 未定義 | commit を止め、sim の注記 | 文言は term の中の場合だけ採ってある |
| 運用モードの `show configuration`(全体) | 先頭の行(Last commit など)を出さない | 未採取 |
| `?` の候補の出方(ユーザ指摘 2026-11-16「実機と少し違う」) | 採れていない階層は骨組みの語だけを字の順・値の札は `<ポリシーの名前>` のような日本語 | 採ってある 8 階層では実機は語ごとに説明が付く。値の札の実機の形は記録に無い(未採取)。木を実機から採る時に一覧ごと差し替える。ほかの違いがあればユーザに場所を聞いて足す |
| 並びの変更の compare | 「並びが変わった」と sim の注記 | 実機は前後の項目を文脈として出す(e2e/s1-3.log の `term BOGONS { ... }`)。形は未解明 |

## 5. 扱わないこと(sim の注記で「扱わない」と出す)

経路表・BGP の隣接などの状態(`show route`・`test policy`・`show bgp …`)、`configure private/exclusive`、`commit confirmed`、
`deactivate`・`annotate`・`copy`・`rename`・`load` ほか、パイプは `| display set` と設定モードの `| compare` だけ、
leaf-list の `insert`(import の並べ替えは delete → `set … [ A B ]` で)、`?` の一覧にあるが骨組みに無い語(hold-time など)。

## 6. 練習(J1・8 本)

区切り= 読み物 J1 のページに合わせて 3 つ(policy-statement・route-filter・BGP)。盤面= JNT-02 の初めの設定(startup.cfg を
set の形にして読む。骨組みで読めない行があれば画面と selftest に出る)。お題の値は読み物の設定例から少しずらした。
確かめ方は commit 済みの設定の display set を照合(`$X` は解く人が決める名前・`*`・`**`・どれか 1 つ・順・打ったコマンドの記録)。
結果は「満たした/何個中何個/順/使ったコマンド」までで、正しい行そのものは出さない(答えの例はボタンを押した時だけ)。

## 7. 次の段(未着手)

1. **木を実機から採る**: CML を止めた時に vJunos-Evolved を 1 台起こし、`?` を巡回して骨組みの全階層の一覧と、値の札
   (`<policy_name>` など)・`<[Enter]>` の出る所・設定モードの誤りの文言を採る。§4 の論点を照合する。採る道具は公開側
   (`cli_drill.py crawl` の予定)。
2. **ポータルに正式に置く**: いまは `/_read/_cli-drill/` に間借り。Games の棚に載せるなら pack_home と経路を足す(ポータルの再起動が要る＝ワークスペースの接続が切れるので、ユーザの了承を取って)。
3. **読み物の区切り**: gen_reading.py に `:::drill <ID>` の記法(区切りの枠＋押すと開く埋め込み)。いまは `?demo=reading` の見本だけ。
4. 日英の切り替え(教材の標準)・J0・J2 の練習・XR の素振り台(→ 2026-11-16 着手。§8)。
5. **FRR を相手にする(2026-11-16 ユーザ案・containerlab が動いている時に回す)**:
   ① 盤面 JUN01 ─ OSPF ─ FRR1(雛形 POC-CLABFRR-01＋静的経路)。端末を機器ごとに切り替え、JUN01 の commit 済みの export
   ポリシーを評価して FRR1 の `show ip route`・`show ip ospf database external` などに載せる(commit 前は載らない)。隣接は
   「両端が同じ網・同じ area なら Full」とし、崩し(MTU・hello の不一致など)は扱わない。Junos が export した経路の既定の
   metric/type・FRR の表示の細部は vJunos×FRR の実機で採る。
   ② FRR の vtysh を別のエンジンで(configure terminal・モードごとのプロンプト・no・打った瞬間に効く・show running-config・
   write memory)。同じ要件を JUN01 は policy-statement、FRR1 は route-map＋redistribute で書き、相手側の経路表で同じ結果になる
   ことを見る。FRR は「IOS 風」で Cisco IOS ではない= 画面に FRR と明記し、IOS との違いは確かめた物だけ注記。

## 8. IOS XR(XR トラック M0・M1)— 2026-11-16

ユーザ指示「CML が動いている間は CML でできる範囲を。XR などはメモリに余裕があれば試験ラボで」＋素振り台の約束
(CLAUDE.md「コマンドの素振り台の約束」= 実機の動きを必ず確かめ、外れない形に)。XRT-01(XR01= IOS XRv 9000 24.3.1・RT01/RT02= IOL)
を試験用に起こし(XRT-15 には触れない・CML のメモリは 47GB 中 10GB 使用だった)、台本どおりに打って記録を採ってから作った。

### 8.1 置き場

| 物 | 置き場 | 公開 |
|---|---|---|
| CLI の動き | `games/cli-drill/iosxr.js`(約 1500 行) | 公開 |
| 骨組み(語・値の型・running-config の並び・下位モードの名前) | `games/cli-drill/syntax/iosxr.txt` | 公開 |
| 練習(M0 4 本・M1 5 本) | `games/cli-drill/drills/iosxr-m0m1.yml` | 公開 |
| 採取の台本 | `games/cli-drill/capture/iosxr/*.txt` | 公開 |
| 再現の試験の一覧(どの記録を・どの手を外すか) | `games/cli-drill/tests/iosxr.yml` | 公開 |
| 実機の記録(台本ごと) | `private/cli-drill/iosxr/raw/*.log` | 非公開 |
| ? の一覧(記録から採る・96 文脈) | `private/cli-drill/iosxr/help.json` | 非公開 |
| 盤面(稼働中の設定・コミット 8 回の履歴と各回の中身) | `private/cli-drill/iosxr/boards/XRT-01-XR01.json` | 非公開 |
| 盤面の図の一次情報(構築時の CML のラボ定義と day0 の控え) | `private/cli-drill/iosxr/boards/XRT-01.lab.yaml`・`.day0/` | 非公開 |

```
source poc/xr/env.sh                       # 機器のログイン(NODE_USER/NODE_PASS)
python3 topologies/cli_drill.py session --host <XR の管理 IP> --script games/cli-drill/capture/iosxr/<台本>.txt --out private/cli-drill/iosxr/raw/<名前>.log
python3 topologies/cli_drill.py xr-board --log private/cli-drill/iosxr/raw/board.log --out private/cli-drill/iosxr/boards/XRT-01-XR01.json
python3 topologies/cli_drill.py selftest   # build で ? の一覧を記録から採り直す。XR の記録の再現 8 本＋期限切れ(仮想時間)
```
台本: 末尾 `?` は Enter なしで送って記録の後に行を消す・末尾 `<TAB>` は Tab・`#SLEEP n` は待って機器が自分から出した表示を記録。
★採取の後は盤面へ戻す(`rollback configuration to-exclude CHG2001`)。確認つきコミットの途中でセッションが切れると、期限まで
他のセッションからコミットできない(記録 gaps4.log の文言)ので、台本では問いに必ず答える。

### 8.2 試験(実機の記録を同じ順に打ち直す)

`tests/iosxr.yml` の記録 14 本を、盤面から素振り台で打ち直し、手ごとの出力(時刻は伏せる)と次のプロンプトを突き合わせる。
観察 51 手・M1 82 手・モード 126 手・並び 58 手・足りない場面 26 手・略した語 6＋5 手・確認つきの end 13 手、
口の名前と大小文字(§8.7)の 6 本、すべて一致。
外した手は理由つきで試験の一覧に書いた(前の採取で履歴が増えていた手・素振り台が扱わない語)。期限切れは仮想時間で 31 秒進めて確かめる。

### 8.3 実機の記録で確かめて入れた動き

- プロンプト `RP/0/RP0/CPU0:XR01#`・`(config)#`・下位モード名(config-if・config-ospf・config-ospf-ar・config-ospf-ar-if・config-vrf(-af)・
  config-static(-afi)・config-bgp(-af/-nbr/-nbr-af)・config-ntp)。show・configure・commit の頭に時刻の行。
- ? の一覧はモードと打ってある語ごとに実機の行そのまま。既にある名前(vrf ?・router ospf ?)と履歴(rollback configuration ?・
  load rollback changes ?)は今の中身で並べ直す(幅は最長の語＋2)。語の途中の ? と Tab の候補は字の順に横 4 列(4 列目は詰める)。
- 略した語: Enter では cisco-support の語を数えない(conf → configure・co は曖昧)。Tab と ? には出る(conf+Tab → configur)。
- 誤り: `% Invalid input detected at '^' marker.` の ^ は「今のモードの語で打てた所までの字の次」(値の誤りは値の頭・IPv4 は誤った区切りの頭)。
  `% Incomplete command.`・`% Ambiguous command:  "…"`(? の時は末尾の空白も入る)。下位モードで通らない文は上のモードで試し、
  どこでも通らない時は今のモードの誤りを出す(router ospf を config-if で打つと caret は「ro」の次)。? は上のモードへ回らない。
- 編集中の設定: show configuration は変更の形(消した文は `no <語>`・description は末尾に空白)。入っただけの塊も出る。
  show commit changes diff は印 3 字(`+`・`-`・`<-`/`+>`)。中の変化が消すだけの塊は祖先まで `-`。追加の塊の `!` は印なし。
- コミット: 成功は時刻だけ・変化なし `No configuration changes to commit.`・ラベルの重複・定義の無いポリシーで pseudo-atomic の失敗
  (編集中の設定は残る・ID を使わない)・show configuration failed の形。履歴の一覧・detail の桁(Line は一覧で 18 字に切る)・
  コメントの形(前に空白 3・後ろに 1)・changes/rollback changes の形(戻しは「その回で新しく作った塊は no <塊>」)・
  router static を消す時は中の経路を 1 つずつ消す形(@nest)。type 7 の鍵(盤面の 3 つを復号して同じ方式と確認・先頭の 2 桁は乱数)。
- rollback configuration last N / to-exclude X の結びの行・load rollback changes の `Loading.`。end/exit で変更があると
  yes/no/cancel(cancel は設定モードの一番上へ・ほかの答えは `% Invalid input.`)。
- 確認つきコミット: 確定で `% Confirming commit for trial session.`。期限切れは画面に何も出さずに戻り履歴に Rollback(Line は vty)。
  end/exit で「Do you wish to exit? [no]:」→ yes はその場で戻す(Line は rollback)・no は設定モードの一番上へ・ほかは `% Please answer 'yes' or 'no'.`。
  期限切れの後に同じセッションでコミットすると「One or more commits have occurred …」と問う。
- 表示の並び: 一番上= hostname・domain・username・vrf・line・vty-pool・ntp・interface・router static・router ospf・router bgp・ssh・telnet。
  IF は種類(Loopback→MgmtEth→Gi)と番号の順・VRF は名前の長さ→字の順・OSPF の IF の下= cost・authentication・message-digest-key・
  network・passive・dead-interval・hello-interval・IF の下= description・vrf・ipv4・ipv6・shutdown。`passive` だけは passive enable・
  `authentication` だけはそのまま。

- **大小文字と口の名前(2026-11-16 ユーザ指摘で採取= §8.7)**: 語は大小文字を区別しない・Tab は打った字のまま残りを足す・
  空白では補わない・型と番号は分けて打ってよい・口の下位モードの一覧は口の型ごと。

### 8.4 確かめていない・揺れる所(素振り台は注記で出すか、決めの形で出す)

| 論点 | いまの扱い |
|---|---|
| rollback の「N items committed in 1 sec (N-1)items/sec」・load の「N bytes parsed …」 | 数え方が分からないので行を省いて注記(実機の 3 例は rate = 数−1) |
| rollback configuration to X の結びの行 | 注記 |
| 1 桁の日の時刻の形(Mon Nov  6 か Mon Nov 6 か) | 空白 1 つで出す(未採取) |
| 複数回をまとめた commit changes last 2 以上 | 扱わない(実機は各回をつなげた形= gaps1.log) |
| 確認待ちの間にさらに変更を足した commit | 注記 |
| remote-as の無い隣接の失敗の文言・ラベルが英字で始まらない時の文言 | 注記 |
| 「他のセッションのコミット」の問いに no と答えた時の表示 | 注記 |
| 設定を同じ値で打ち直した時の show configuration | 差分で出す(実機は打った文を出すかもしれない) |

### 8.5 扱わないこと

configure exclusive・複数セッション・commit replace・best-effort・show configuration merge/sessions/lock・経路表と隣接などの状態・
RPL の定義(route-policy の付け所だけある)・骨組みに無い語(cisco-support の語を含む。注記で「扱わない」と出す)。

### 8.6 盤面の図

CML の問題は構築時に生成される `lab.yaml`(ノード・座標・IF の名前・リンク)を控え、`topo_model_cml` で起こす。アドレス・OSPF・BGP は
盤面の記録がある機器はその running-config、ほかは lab.yaml の day0 から。管理網の部品と管理用の口は描かない。図の口の名前は短い名前
(XR の ? の「short name is Gi」・IOS の Et)。同じ 2 台の間に並ぶリンクは線をずらして箱を広げる。BGP の札は両端の neighbor が
互いを指す時だけ(片方だけの設定では張れない。Junos の盤面の図も同じ規則に直した)。狭い画面は字を 0.85 倍より小さくせず横へずらして見る。

## 9. 教材への組み込み(XR M0・M1 の先行投入)— 2026-11-16

ユーザ「実際の教材として先行投入できますか」。実機の記録から作った **XR M0・M1 だけ**を入れた。Junos J1 は `?` の一覧を
実機から採っていない(§4)ので、約束 1(実機から外れない)により見送り= containerlab が動く時に木を採ってから入れる。

### 9.1 記法 `:::drill`(正典= `topologies/gen_reading.py` の docstring)

- `:::drill <ID> [<ID> …]`(1 行・閉じは無い)。gen_reading がお題のボタンの並んだ区切りにする。番号(M1-2 …)と題名は
  `drills/*.yml` から引く(番号の振り方は素振り台の家の画面と同じ)。知らない ID はビルドを止め、素振り台の置き場
  (`reading/_cli-drill/`)に無いお題・ページの言語の題名が無いお題は警告する。
- ボタン → その下に枠 `../_cli-drill/?drill=<ID>&embed=1&lang=<ページの言語>`。同じボタンで閉じる(中身は残る)・
  別のお題はその枠で開き直す。持ち出しの 1 枚(Drive)では行ごと落とし、file:// では隠す。用語集の札は区切りの中に付けない
  (`glossary.py` の SKIP_CLASSES に drillbreak)。
- 枠の高さ: 素振り台が中身(main)の高さを `postMessage {ccnpDrillH}` で知らせ、読み物が枠を合わせる。測り直しの合図は
  ResizeObserver・MutationObserver(結果・答えの例・図の開閉)・窓の resize の 3 つ(見えない枠で ResizeObserver が来ない場面があった)。
  枠の中は縦のスクロールバーを出さない(バーの出入りで幅が変わり、折り返しと高さが揺れた= 試験で 27px ずれた)。
  端末の高さは埋め込みの時 20rem に固定(vh で決めると枠の高さと輪になる)。

### 9.2 置いた所(日英とも同じ位置。言語の切替の位置合わせ= 2 版の子の数をそろえる)

| ページ | 節の後 | お題 |
|---|---|---|
| M0 | §5 コミットするまで何も起きない | M0-1(Loopback と show configuration) |
| M0 | §8 最初の読み替え(§3 の木構造の 3 つ。どれも commit が要るので §5 より後) | M0-2 OSPF・M0-3 VRF・M0-4 静的経路 |
| M1 | §2 コミットは全か無か | M1-1 拒否の理由を読む |
| M1 | §3 すべてのコミットが記録される | M1-2 ラベルとコメント |
| M1 | §4 元に戻す | M1-3 1 回だけ取り消す・M1-4 まとめて戻す |
| M1 | §5 自分で元に戻るコミット | M1-5 確認つきコミット |

お題の並びを節の順に合わせて M1 の ID を振り直した(旧 xr-m1-3 → xr-m1-1、旧 xr-m1-1 → xr-m1-2、旧 xr-m1-2 → xr-m1-3)。

### 9.3 2 言語

- 教材は英語が既定の版なので、XR のお題の文言(unit・title・task・cmd の say・sayNg)は `{ja, en}`。画面の文言は index.html の辞書 `W`、
  素振り台の注記(黄)は iosxr.js の `J(ja, en)`(create の `opt.lang`・checkDrill は `sim.lang`)。実機の文言(白)は言語に依らない。
- 言語= `?lang=` → localStorage `ccnp-lang`(読み物・問題の切替と同じ鍵)→ 日本語。単体で開いた時は帯のボタンで切り替える。
  埋め込みの時は帯が無いので、枠の上に「ルール」と「別のタブで開く」を出す。
- Junos は画面の枠だけ英語になり、お題と注記は日本語のまま(J1 は教材に入れていない。入れる時に `{ja, en}` にする)。

### 9.4 試験

- `cli_drill.py selftest`(NG 0): 画面の文言の鍵が日英でそろう・XR のお題の文言が日英にある・英語の素振り台で答えの例と
  記録 8 本を打ち直して出力に日本語が出ない、を足した。
- 画面の試験(`?drill=<ID>&uitest=1[&lang=en]`)を日英で(xr-m0-1・j1-ps-1。NG 0)。
- `cli_drill.py embedtest`(新設・NG 0): 区切りを持つ読み物のページをポータルと同じ配置(/_read/ → reading/)で日英それぞれ開き、
  `tests/embed.html` が区切りのボタンを 1 つずつ押して、枠が開く・URL の言語・お題の言語・枠の高さ= 中身・答えの例で確かめが通る・
  結果の分だけ枠が伸びる・閉じて開き直すと中身が残る・2 版の子と区切りの数がそろう・区切りに用語集の札が無い、を確かめる
  (M0 39/35 項目・M1 52/47 項目)。幅 390px でも別に開いて崩れないことを目で確かめた。
- ラボのワークスペースの Reading タブ(枠の中の枠)は sandbox を持たないので、同じ動きで開く(lab_console の iframe)。

### 8.7 口の名前と大小文字(2026-11-16 ユーザ指摘「OSPF の中で interface Lo + Tab の後、空白のまま 40 と打つと誤り・loo では Tab が効かない」)

素振り台が骨組みから推していた所で、実機で採っていなかった。XRT-01 をもう一度試験用に起こして(XRT-15 には触れない・CML 47GB 中 10GB)、
台本 `capture/iosxr/ifnames*.txt` の 6 本を採った(コミットはせず abort で捨てる)。分かったこと:

| 場面 | 実機(XRv 9000 24.3.1) | 直す前の素振り台 |
|---|---|---|
| `interface Lo` + Tab | `interface Loopback `(空白つき) | 同じ |
| `interface Loopback 40`・`Lo 44`・`LOOPBACK 42`・`loopback41`・`lo43` | どれも通り、`Loopback40` などにまとまる(OSPF の中・show running-config interface も同じ) | 型と番号を分けると誤り |
| `interface lo`・`loo`・`LOO`・`gi` + Tab | 打った字のまま残りを足す(`loopback `・`LOOpback `・`gigabitEthernet `) | 小文字は補えない |
| `interface L` + Tab | 候補 `Loopback  lpts`(大小文字を区別しない) | Loopback だけを補う |
| `ROU` + Tab・`router OS` + Tab・`DESC` + Tab | `ROUte`・`router OSpf`・`DESCri`(共通の所まで・打った字のまま) | — |
| `lo?`・`ROU?` | `Loopback`・`route-policy  router`(正規の綴り) | 誤り |
| `INTERFACE`・`Router ospf`・`IPV4 address`・`Description`・`network POINT-TO-POINT`・`SHOW RUNNING-CONFIG`・`COMMIT`・`ROOT`・`EXIT`・`ABORT`・END の問いへの `NO` | どれも通る(表示は正規の綴り) | 区別していた |
| `int` + 空白 + `Lo` + Tab | `int Loopback `(空白では語を補わない) | 空白で `interface ` に補っていた(Junos の動きを当てていた) |
| `rou ospf 1 ar` + Tab | `% Ambiguous command:  "rou ospf 1 ar"` | — |
| `interface Loopback ?`・`Loopback 4?`・`Loopback40?` | `  <0-2147483647>  `(説明なし・一覧の形) | 誤り |
| `interface Null ?` | `  <0-0>  ` | — |
| `interface GigabitEthernet ?`・`MgmtEth ?` | 機器にある口の番号＋R/S/I/P の行(一覧の形) | — |
| `GigabitEthernet 0/0?`・`Gi0/0/0/?` | 口の番号と `R/S/I/P/B or R/S/I/P` を横に並べる形 | — |
| `Gi0/0` + Tab・`Gi0/0/0/` + Tab・`Gi0/0/0/3` + Tab・`Loopback 4` + Tab | `Gi0/0/0/`・候補の 4 つを並べる・`Gi0/0/0/3 `・何も起きない | — |
| `cost 5?`・`ipv4 address 10.1?` | `<1-65535>  `・`A.B.C.D/prefix  `(語の途中の ? と同じ横並びの形・説明なし) | 誤り |
| `interface Loopback`・`interface Lo`(型だけで Enter) | `% Incomplete command.` | 誤りの印 |
| `interface Loopback abc`・`interface Loopback 40 50` | 誤った語(abc・50)の頭に `^` | — |
| 口の下位モードの `?`(config-if・config-ospf-ar-if) | 口の型で一覧が違う(Gi の下は 57 項目・Loopback の下は 31 項目。OSPF の中も Gi に bfd・mpls など) | Loopback の一覧を出していた |
| 下位モードの `abort` | 下位モードの `?` の一覧に無いが通る | 誤り(小文字でも) |

入れ方:
- 語の比べ方を `pfx`(頭が合う)・`same`(同じ)にそろえ、大小文字を区別しない(名前・ラベル・説明などの値は区別する)。
- 口の名前の値は、型だけの語(`ifTypeOf`。頭 2 字から)の次の語と合わせて 1 つの名前にする(`ifJoin`)。型だけで終われば途中、合わなければ次の語の頭に誤りの印。
- `?` の一覧の鍵: 口の名前は Loopback が `*`、ほかは `*@<型>`。口の下位モードも型ごと(`config-if@GigabitEthernet|`)。
  採る道具(`harvest_xr`)は、下位モードへ入った手の口の型をモードに付けて残す。採っていない型の下位モードは薄い語＋注記。
- 番号の途中の `?` は型の種類で形を分ける(range= 一覧の形・inst= 横並び)。値の途中の `?` は、その形の値の札(`<a-b>`・`A.B.C.D…`・`R/S/I/P…`)も並べる。
- XR の素振り台は空白で語を補わない(画面の空白の処理は Junos だけが補う)。

罠(作る時): `create()` の中に同じ名前の変数(盤面の最後の変更の時刻 `lc`)があって比べる関数を隠した・`_steps` のプロンプトは「手の前」(下位モードへ入った手の口の型は次の手のプロンプトで受ける)・
`?` は上のモードへ回らない(下位モードの `hostname ?` は誤り)ので、下位モードの「途中」は上のモードの途中より優先しない。


## 10. IOS XR M14 マルチキャスト(XRd 26.1.1)— 2026-11-18(BL-283)

ユーザ「素振りはいかがでしょうか。実装できそうですか」→ 着手。学習ラボ XRT-16(稼働中・白紙)には触れず、同じ盤面・同じ初めの設定の
試験ラボ `_POC-XRDRILL16`(problems/ に保持・CML のメモリは 50.6GB 中 11.1GB 使用だった)を起こして PE2 で採取し、撤収した。

### 10.1 置き場と版の組
| 物 | 置き場 |
|---|---|
| 採取の台本 | `games/cli-drill/capture/iosxr/m14board.txt`・`m14explore.txt`・`m14cfg.txt`〜`m14cfg4.txt` |
| 実機の記録 | `private/cli-drill/iosxr/raw/xrd-26.1.1/*.log`(非公開) |
| 盤面 | `private/cli-drill/iosxr/boards/XRT-16-PE2.json`(コミットの履歴は空= XRd は day0 の設定)・図の元 `XRT-16.lab.yaml`(XRT-16 の生成物の控え) |
| お題 | `games/cli-drill/drills/iosxr-m14.yml`(6 本。読み物 f0 §3.2・§3.3・§3.4、f2 §3.1・§3.3、f4 §3.1 の終わり) |
| 再現の試験 | `games/cli-drill/tests/iosxr-m14.yml`(記録 6 本) |

★**`?` の一覧は版・機種ごとの組に分けた**: `raw/` の直下= 既定の組(XRT-01 の XRv 9000 24.3.1)、`raw/<組>/`= 別の組。
`harvest_xr` が組ごとに採り、束の `helpSets` に入れる。盤面の JSON の `helpset`(xr-board が記録の置き場から付ける)が組を選ぶ。
組どうしは混ぜない(`router ?` などの一覧が版で違う)。M14 の盤面は XRd 26.1.1 の組だけを見る。

### 10.2 記録で確かめて入れた動き(syntax/iosxr.txt の頭の注記に印の意味)
- 並び: hostname → logging → username → vrf → line → vty-pool → alias → **ipv4 access-list**(名前の長さ → 字の順)→ interface →
  router isis → **multicast-routing → router igmp → router pim** → ssh。
- ACL の行は打った形のまま(`238.0.0.0/8` と `238.5.0.0 0.0.255.255` を直さない)。番号を省くと最大＋10。同じ番号は置き換え。
  `ip any any` は曖昧。`10 permit ipv4 238.5.0.0` で Enter は `% Incomplete command.`。
- 選べる語: `bsr candidate-rp`・`bsr candidate-bsr` は順が自由で、表示は決まった順に直り既定の値が書き足される
  (`hash-mask-len 30 priority 1`・`priority 192 interval 60`)。`bidir` は最後(後ろに何も書けない)で、bidir の有無で別の文。
  `rp-address A [ACL] [override] [bidir]` は順が決まっている(`bi`・`ov` は語として読む)。bidir の有無で別の文。並び= override → 印なし → bidir、アドレスの順。
- `?` の一覧で記録の無い組み合わせ(`priority 20 group-list X ?` など)は、頭だけの一覧から使った語を除いて出す(記録の 3 例がその形)。
- 空の塊: multicast-routing と router igmp は入ると空の塊も別にでき、running-config・編集中・コミットの中身で本体の後ろに
  「名前 / !」が出る(この編集で入った時だけ。1 行の no で辿っただけでは出ない)。部分の show running-config と差分には出ない。
  戻しでは multicast-routing が「multicast-routing / !」、router igmp が「no router igmp」。
- 消える塊: router pim の address-family は中身が無くなると消え、入っただけでは表示に出ない。multicast-routing の address-family と
  router igmp の口の塊は空でも残る。
- 消した行の表示: 編集中は `no 20`・`no rp-address 10.255.0.4`(区別の値まで)、`no bsr candidate-rp 10.255.0.2 priority 192 interval 60`
  (区別の値＋既定の値。差分の `-` の行も同じ)、L の文は語だけ(`no spt-threshold infinity`・`no bsr candidate-bsr`・`no version`)。
  コミットの中身・戻しは値まで。ACL と pim の address-family を丸ごと消す戻しは中の文を 1 つずつ消す形。差分で中を消すだけの塊の行に `-` を付けない
  (M0・M1 の router ospf は付く= 組で違う)。
- 1 行の途中の `no`(`router pim address-family ipv4 no rp-address …`)は誤り(印は no の頭)。
- `rp-address 10.255.0.300` の誤りの印は最後の 0(IP name or address の型。`ipv4 address` の型と違う)。
- 履歴の空の盤面: `The commit database is empty.`・running-config の頭は `!! No configuration change since last restart`。
  最初のコミットも `rollback configuration last 1` で戻せる(戻し先= 盤面)。
- 扱わない語(`ipv6 ?`・`accept-register ?`・pim の口の中など)でも、実機の `?` の一覧があればそれを出す。今のモードの一覧にある語は上のモードで試さない。

### 10.3 試験
selftest: お題 6 本(盤面・初めは満たさない・答えの例で満たす・注記が出ない)＋記録 6 本の再現(盤面 9 手・1 周目 108 手・設定の形 95・85・46・35 手)すべて一致。
M0・M1 の記録 14 本も一致のまま。embedtest(f0・f2・f4 を日英)NG 0・uitest(xr-m0-1 日英・j1-ps-1)NG 0。
外した手(理由は tests/iosxr-m14.yml): show version(扱わない)・前の採取の名残と履歴に依る手(m14cfg2 の 2 手・m14cfg3 の 5 手・m14cfg4 の 1 手)。

### 10.4 確かめていない・揺れる所
| 論点 | いまの扱い |
|---|---|
| 入っただけの router pim のコミット | 実機はコミットを 1 つ作った(m14cfg3.log)。素振り台は「No configuration changes to commit.」 |
| logging・router isis・ipv6 access-list・router mld の並びの位置 | 盤面の順に置いた(!確認) |
| `rp-address A` と `rp-address A ACL`(bidir なし)を続けて打った時 | 置き換えとした(bidir の有無で別の文になるのは記録あり) |
| join-group・static-group の消し方の表示 | 既定の形 |
| 差分で中身の無い空の塊の形 | 出さない |
| 新しいモードの中の扱わない語(pim の口の中・mld の中・accept-register) | 注記(扱わない) |
