# XR トラック — IOS XR を「読む→ワークスペースで実践」で学ぶ基盤(BL-246)

2026-10-12 ユーザ発案・同日の調査と方針合意をまとめたもの。**第一弾(M0+M1)まで実装済み(同日・§11)**。

## 1. ねらいと前提

- IOS XR の操作と設定を体系的に身につける。進む向きは**ゆるく CCNP SP(SPCOR 350-501 v1.1)のブループリント寄り**。
  試験対策の網羅ではなく、XR で手が動くことを先に置く。
- 学習者は **CCNP Enterprise 取得済み**が前提。技術そのもの(OSPF・BGP・再配送・VRF・MPLS L3VPN)は既知として扱い、
  新しいのは XR の作法だけ、という組み方にする。IS-IS・SR・L2VPN など Enterprise に薄い技術だけ解説を厚くする。
- **自分で考える・自分で調べることを促す構造**にする。hostname を変えて commit するだけの課題は作らない。

## 2. 1 単元のサイクル

**① 読み物でその単元を学ぶ → ② 学習テストとしてワークスペースで実践する**

| 段 | 中身 | 道具 |
|---|---|---|
| ① 読み物 | 仕組みの解説(なぜそうなっているか・IOS との違い)。コマンドの網羅はしない | `gen_reading.py`(BL-230) |
| ② 学習テスト | 挙動で指定した課題を、例なしで組む。左=課題／右=コンソール | ワークスペース(BL-234)＋中間チェック(BL-232) |

- 読み物は翻訳ではなく**公式資料をもとに書き下ろす**。原書の体裁を写す決まり(CLAUDE.md「読み物」§2)の対象外。
  出典は公開の公式文書だけなので、ソースは公開側に置ける(書名・商用教材の名前は出てこない)。
- 学習テストはパックとノルマの対象外(学習目的ラボの扱い)。記録に残すのは単元末の確認問だけ。

## 3. 課題の作り(難度の方針)

- **コマンド例は既定で見せない**。課題は機能名でなく挙動で指定する。
- 読み物は「仕組み」まで。どのコマンドで扱うかは課題側で自分で探させる。
- 最初の単元で**調べ方**を扱う(`?`・階層を指定した設定表示・公式コマンドリファレンスの引き方)。
  以後の課題は「該当する公式ガイドの章」だけを参照先として示す。
- **ヒントは段階式**(キーワード → 参照先の節 → コマンド例)。開いた段数を記録する。
- **確認は状態と挙動で見る**(打ったコマンドは見ない)。通過後に模範解と別解を出す。
- 題材の型は 3 つ:
  1. **移植**: IOS なら組める要件を XR で組む(既存の構築問の要件書を流用し、対象の 1 台を XR にする)。
  2. **仕組みを使う**: XR にしかない仕組みを、理由のある場面で使わせる(下の M1 の例)。
  3. **TS**: XR の作法に由来する不具合を直す(既定で shutdown・ポリシー未適用で経路が通らない 等)。

## 4. 言語

- **英語を基本**にし、日本語でも出せるようにする。
- 原文を英語で書き、日本語は隣に訳を置く(紙面の `en/` と向きが逆。置き場と照合の仕組みは実装時に決める)。
- 採点は状態を見るので言語に依存しない。
- **読み物も 1 冊で日英切替**(2026-10-13・BL-248)。`courses/xr/book.yml` は 1 つ(`lang: en`・`alt_lang: ja`)。Drive だけは言語ごとに別の 1 枚。
- **画面での日英切替は BL-236 の残り(c)「ページ内の日英切替」に乗る**(2026-10-12 ユーザ方針= そちらを先に作り、
  XR トラックは別セッションで後から始める)。XR トラック側で独自の切替を作らない。

## 4.5 読み物の持ち出し(2026-10-12 ユーザ要望)

- 既存の読み物と同じく **Drive へ同期してスマホで読めるようにする**(`read.sh bundle --split` → `read.sh sync`)。
- **正本はリポの Markdown 1 つ**。Drive 側は生成物で、同期は一方向(Drive 上で直さない)。こうしておけば二重管理にならない。
- ワークスペースの左枠に出す解説と、Drive に出す読み物は**同じソースから描く**(別々に書かない)。
- 課題文は持ち出し版にも載せる(予習用)。ヒントと模範解は載せない。
- ★同期は宛先の余計なファイルを消す。既存のリモートは別の読み物のフォルダに固定してあるので、
  **XR トラック用に宛先フォルダ(リモート)を別に作る**。同じ宛先に向けると既存の持ち出し版が消える。
- **宛先は用意済み(2026-10-12)**= rclone のリモート `gdrive_xr`(ユーザ指定の専用フォルダに固定・作成時点で空)。
  言語ごとに下位フォルダを分け、`book.yml` の `drive:` は `gdrive_xr:en`／`gdrive_xr:ja` のように書く(同期が互いを消さないように)。

## 5. 単元の並び(SPCOR v1.1 との対応)

ブループリント原典= `private/blueprints/350-501-SPCOR-v1.1.ja.txt`(Cisco 公開 PDF の抽出・2026-10-12 取得)。

| 単元 | 内容 | SPCOR 項番 | 盤面 |
|---|---|---|---|
| M0 | 入り方と調べ方(構造・IF 名・既定で shutdown・ヘルプ・リファレンスの引き方)・ソフトウェア構造 | 1.2 | XR 1 |
| M1 | 設定の管理(編集中と稼働中・履歴・確認つきコミット・ロールバック・失敗の読み方・排他・全体差し替え) | — | XR 1 |
| M2 | 基本設定と管理プレーン(ユーザとタスクグループ・AAA・SSH・管理 VRF・ACL・制御プレーン保護) | 1.5.a 1.6.b 1.7.b | XR 1+IOL |
| M3 | OSPF(v2/v3)を XR で | 2.2 2.6 | XR 1+IOL |
| M4 | IS-IS(IPv4/IPv6・エリア・単一/マルチトポロジ・メトリック) | 2.1 2.6 | XR 1+IOL |
| M4 追補 | IS-IS の 2 周目(認証・broadcast と DIS・要約・複数のエリア アドレス)。§18 | 2.1 2.6 | XRd 1+IOL+L2 |
| M5 | ルーティングポリシー言語(route-map との対比・適用点) | 2.5 | XR 1+IOL |
| M6 | BGP(隣接・アドレスファミリ・属性・パス選択・再配送) | 2.3 2.4 2.6 | XR 1+IOL |
| M7 | 高可用性(BFD・NSF/NSR・リンク集約) | 2.8 | XR 1+IOL |
| M8 | MPLS LDP(隣接・同期・セッション保護・OAM・認証とラベルフィルタ)。§20。3.1.d Unified MPLS は M8 追補(§20.8) | 3.1 1.5.d | XRd 1+IOL 3 |
| M8 追補 | Unified MPLS(IGP の分割・境界の 2 インスタンス・BGP ラベル付きユニキャスト・RR の next-hop-self)。§21 | 3.1.d | XRd 1+IOL 5 |
| M9 | L3VPN(Intra-AS・共有サービス) | 4.3 | XR 1+IOL |
| M10 | セグメントルーティング(セグメント種別・IGP 制御プレーン・TI-LFA。SR-TE・SRv6 は読み物中心) | 3.3 | XR 1〜2+IOL |
| M11 | L2VPN とキャリアイーサネット(VLAN タグ操作・E-Line/E-LAN・EVPN) | 4.1.a 4.2 | XR 2+IOL |
| M12 | データプレーンの保護と QoS(uRPF・RTBH・分類/マーキング・ポリシング/シェーピング) | 1.7 4.5 | XR 1+IOL |
| M13 | 自動化とアシュアランス(NETCONF/RESTCONF・gRPC/gNMI テレメトリ・NetFlow・SNMP) | 5.7〜5.10 | XR 1+Linux |

- describe 級で実機に載らない項目(1.1 アーキテクチャ・1.3 仮想化・2.7 IPv6 移行・3.2 TE・4.1 Inter-AS/CSC/mVPN・5.1〜5.6)は
  読み物と紙面で受ける。ラボ化は後回し。
- 並びは目安。M0〜M6 が「XR で手が動く」までの本線、M7 以降が SP 本編。
- **実施順(2026-10-17 ユーザ合意)= M0 → M1 → M2 → M3(短く)→ M5 RPL → M6 BGP → M4 IS-IS → M7 以降**。
  XR のルーティングで一番の壁は RPL(eBGP はポリシーなしでは経路を送受しない)なので、Enterprise の知識が効く範囲で
  RPL・BGP まで先に進み、Enterprise で薄い IS-IS(読み物を厚くする単元)を後ろに回す。単元番号は変えない。
- **IS-IS の深め方(2026-10-22 ユーザ合意)**= 深掘り専用の区画は作らず、2 段で深める。
  ① **M4 追補**(§18)= M7 以降の流れで自然に出てこない論点(認証・broadcast と DIS・要約・複数のエリア アドレス)を、
  M4 の盤面を広げた短い課題で拾う。② **M7 以降の盤面の IGP は IS-IS に統一**し、単元ごとに IS-IS の論点を 1〜2 個載せる
  (M7= BFD・NSF・オーバーロード ビット・タイマー／M8= LDP と IS-IS の同期／M10= prefix-SID・TI-LFA)。
  実施順は M4 → **M4 追補 → M7** → M8 以降。
- **トラック全体の段取り(2026-10-27 ユーザ方針)**= 3 段で進める。
  ① **1 周目(いまの段・BL-246)**= XR に慣れるための SPCOR 準拠の単元を、この表の計画どおり M13 まで貯める。
  ② **2 周目(BL-257)**= ひと段落したら、単元ごとに SPCOR 向けに中身を充実させる(読み物の深掘り・ラボ問・紙面問を順次)。
     2026-10-30 決定= M0〜M9 の読み物を CLAUDE.md §6 の丁寧さ(技術そのものから・何が嬉しいのか→仕組みの図→XR の設定)に書き直すのもここで行う(手本= M10・§23.9)。
  ③ **SPRI(BL-256)**= SPCOR でやれることがなくなったら、SPRI に同じ手順で進む。調査結果は [XR-SPRI.design.md](XR-SPRI.design.md)。
  先回りして次の段の作業を始めない(SPRI の追補・新単元は ③ まで手を付けない)。

### M1 の課題案(最初の試作)

| 課題 | ねらい |
|---|---|
| 管理アクセスに影響する変更を、締め出されても放置すれば元に戻る形で入れる | 確認つきコミットを理由のある場面で使う |
| 2 つの変更を別々の履歴として入れ、先に入れた方だけを取り消す(後の変更は残す) | 履歴の単位・選んで戻す手段を自分で探す |
| 未定義のポリシーを参照する変更を入れ、失敗の原因と「一部だけ入ったか・何も入らなかったか」を答える | 失敗の読み方・全か無かの扱い |
| 別セッションが編集中の状態で変更を入れる。次に他人が同時に編集できない形で作業する | セッションの衝突と排他 |
| 設定全体を差し替える操作で、何が消えるかを入れる前に示す | 危険な操作の前に差分を見る |
| 「昨日から OSPF の隣接が落ちている」を履歴から特定し、その変更だけ戻す | 履歴を使った切り分け(TS) |

- TS の課題は、起動後に変更を複数回に分けて入れて履歴を仕込む投入手順が要る(初期設定の一括投入では履歴が 1 件)。
- 「先に入れた方だけを取り消す」手段は 24.3.1 の実機で未確認。課題にする前に確かめる。

## 6. 環境の制約(2026-10-12 実測)

- XRv9000(24.3.1)は 1 台あたり 7 vCPU(既定 4 では挙動が不安定・ユーザ申告)・割当 20GB・実使用 約 17GB。
  XR の内側から見えるメモリは 6GB で使用 約 2.3GB、残りは外側の固定費 → 割当を削る余地は小さい。
- ホストは 16 コア・47GB。**同時 2 台が上限、既定は 1 台+IOL**。XR ラボの起動中は日次パックのラボと同時に動かせない。
- 3 台以上を並べるならコンテナ版を containerlab 側で動かす案がある(未検証・イメージ入手に契約が要る)。

## 7. 使う部品と足りないもの

| 部品 | 状態 |
|---|---|
| ワークスペース(左=課題／右=コンソール) | あり(`lab_console.py`。ルータ種別に iosxrv9000 を登録済) |
| 読み物の描画 | あり(`gen_reading.py`) |
| 中間チェック | あり(`lab.sh checkpoint`。コマンドラインから) |
| Genie の XR 用パーサ・接続プラグイン | venv に導入済(パーサ 77 本・iosxrv9k プラグイン) |
| ワークスペースの左枠に読み物の体裁で課題を出す | なし |
| 課題ごとの確認ボタン(画面から中間チェックを呼ぶ) | なし |
| 段階式ヒントと開封の記録 | なし |
| XR の初期投入・採点経路・生成器の対応 | なし |
| Ansible の XR 用コレクション | 未導入 |

- コンソールは解答者と採点で共有される(BL-234 実測)。確認は管理 IF 経由の SSH で行うか、特権モードに戻ってから押す約束にする。

## 8. 着手前の PoC(XR 1 台+IOL 1 台)

1. 初期設定の自動投入が効くか。
2. 管理 IF 経由の SSH で採点できるか(ホスト鍵の生成が実行コマンドで、初期設定に書けない可能性)。だめならコンソール経路。
3. Genie で `show` を構造化できるか。
4. 起動から採点可能になるまでの時間。
5. ワークスペースのコンソールで XR に貼り付けたときの取りこぼし(BL-235 ②)。
6. M1 の各課題の挙動(選んで戻す・失敗時の扱い・排他)を実機で確定。

- **PoC 完了(2026-10-12)**= 6 項目すべて確認。結果は [poc/xr/README.md](../../poc/xr/README.md)。要点= 初期投入は CML のノード定義の設定ファイルが編集可であることが前提／採点は既存の SSH 経路がそのまま通る(XR は become を切る)／起動 約 8 分／M1 の課題の挙動はすべて確定(確認つきコミットは設定モードを抜けると取り消される、が新たに分かった落とし穴)。

## 9. 裏どりのソース

| 種類 | 資料 |
|---|---|
| 公式・設定ガイド | ASR 9000 向け IOS XR 24.x 系(System Setup・System Management・Interface・Routing・MPLS・L3VPN・L2VPN・Segment Routing・System Security・Programmability・Telemetry) |
| 公式・コマンドリファレンス | 同系列の各巻 |
| 公式・仮想ルータ | 仮想ルータの導入・設定ガイド(仮想版の対応機能) |
| 公式・旧版 | 3.x 系の入門ガイド(CLI の基本・履歴とロールバックが章立て。古いが骨格は同じ) |
| 実機 | XRv9000 24.3.1 |

- 現行の設定ガイドにコミット周りのまとまった章は見つからなかった(2026-10-12)。旧版ガイド+実機で固める。
- 解説サイト・問題集に XR の分は期待しにくい(未調査)。実質「公式+実機」で確認する。

## 10. 第一弾の計画(2026-10-12・実施済み= 結果は §11)

**範囲= M0(入り方と調べ方)+M1(設定の管理)**。読み物(英語+日本語)→ Drive 同期 → ワークスペースでの学習テスト、までを 1 周通す。
盤面は **XR 1 台+IOL 1 台の 1 ラボを M0 と M1 で共用**する(XR は起動が遅いので、単元ごとに立て直さない)。

### 10.1 事前に分かっていること(2026-10-12 CML のノード定義を確認)

- 初期設定は ISO の `iosxr_config.txt` で投入できる(起動完了の目印= `%MGBL-CVAC-4-CONFIG_DONE`)。
- IF の並び= slot0 `MgmtEth0/RP0/CPU0/0`・slot1〜2 は使用不可・slot3 から `GigabitEthernet0/0/0/0`。
- ノード定義の既定は 7 vCPU・20GB(変更済み)。起動のタイムアウトは 3600 秒。
- 採点は `grade.py` がチェックごとに `genie_os` を受けるので、XR 用の指定を足すだけで載る。
- `device_profiles` に XR の family が無い。初期設定のテンプレートも IOS 用しか無い。

### 10.2 段取り

| 段 | やること | 終わりの条件 |
|---|---|---|
| P0 PoC | §8 の 6 項目を XR 1+IOL 1 で実測。記録は `poc/xr/README.md` | 採点経路(SSH かコンソール)と起動時間が決まり、M1 の各課題の挙動が確定 |
| P1 基盤 | ①`device_profiles` に XR の family・初期設定テンプレート・起動待ち ②採点の XR 対応 ③履歴を仕込む投入手順(起動後に変更を複数回に分けて入れる) | `lab.sh` で XR 入りのラボが立ち、白紙 0 点・模範解 100 点が出る |
| P2 画面 | ワークスペースの学習モード= 左枠に課題(読み物の体裁)・課題ごとの確認ボタン(中間チェックを呼ぶ)・段階式ヒントと開封の記録 | 実ブラウザで 課題→確認→ヒント→通過後の模範解 が通る |
| P3 中身 | M0・M1 の読み物(英語が原文・日本語訳を隣に)と学習テスト。論点ごとに公式+実機で裏どりし、照合表を残す | 読み物がビルドでき、学習テストが E2E で通る |
| P4 配信 | 章ごとに束ねて `gdrive_xr:en`／`gdrive_xr:ja` へ同期。CATALOG・CURRICULUM に登録 | スマホの Drive で読める |

- P0 が P1〜P3 の前提。P2 と P3 は並行できる。
- 画面の日英切替(BL-236 残り c)は待たない。第一弾は英語版と日本語版を別々に出力し、切替ができたら乗せ替える。

### 10.3 M0 の中身(案)

読み物= XR の構造(プロセスが分かれていること・設定が階層で持たれること)、IF の名前と既定の状態、IOS と違う基本の表示、
ヘルプと公式リファレンスの引き方。

学習テスト= **設定が「ほぼ」入った XR を渡し、隣の IOL と疎通させる**。調べないと進めない形にする。

| 課題 | ねらい |
|---|---|
| 隣の IOL と IPv4/IPv6 で疎通させる(XR 側は IF が既定の状態のまま・アドレスは片方だけ入っている) | IF の既定・アドレスの書き方 |
| IOL との OSPF 隣接を上げる(プロセスはあるが IF が入っていない／エリアが違う) | 階層の中に IF を書く作法・部分だけ表示する方法 |
| 指定の VRF に属する IF と経路だけを示す表示を、設定全体を出さずに得る。その結果を使って誤った所属を直す | 表示の絞り込み・VRF の書き方 |
| 管理用の到達性を壊さずに、データ側の既定経路を入れる | 管理 IF とデータ IF の区別 |

### 10.4 M1 の中身

§5 の「M1 の課題案」のとおり。OSPF の隣接を題材にする TS は M0 で上げた隣接をそのまま使う。

### 10.5 着手時に決めること

1. PoC に使う XR(試験用ラボの 2 台を止めて、こちらの手順で 1 台立てるのが素直。3 台目は載らない)。
2. 読み物と課題のソースの置き場(公開側。案= `courses/xr/<単元>/`)。
3. 学習テストの記録の扱い(ノルマ外。単元末の確認問だけ `records/` に残す)。

## 11. 第一弾の結果(2026-10-12)

| 段 | 結果 |
|---|---|
| P0 PoC | 完了。記録= [poc/xr/README.md](../../poc/xr/README.md) |
| P1 基盤 | `device_profiles.iosxr`・`baseline_router_iosxr.cfg.j2`(ラボ指紋・SSH の rate-limit・VTY の本数を含む)・`grade.yml`(XR は become を切る)・`topologies/xr_bringup.py`(履歴の仕込み。`initial/<node>.commits.yml` があれば `lab_up.yml` が呼ぶ) |
| P2 画面 | `lab_console.py --learn <ID>`(入口= `scripts/lab.sh learn <ID>`・既定 8896)。左に Steps タブ= 課題ごとの確認(中間チェックを 1 回・約 10 秒)・段階式ヒント・模範解(通過後かヒント全開後)。ヒントと模範解はサーバが開いた分だけ返す。記録= `records/learn/<ID>.jsonl`。★実ブラウザでの確認は未(API 経由の動作と画面の JS の構文確認まで) |
| P3 中身 | ラボ `XRT-01`(XR01+RT01+RT02)。課題= M0 4 本・M1 6 本(うち M1-5 は確認なし)。`task.en.md` が原文・`task.md` が日本語。読み物= `courses/xr/en`・`ja`(M0・M1)。実践ページは課題文から `scripts/course.sh` が切り出す(二重に持たない) |
| P4 配信 | `scripts/course.sh xr sync` で `gdrive_xr:en`／`gdrive_xr:ja` に単元ごと 1 枚ずつ(計 4 枚)。CATALOG(タグ tutorial)・CURRICULUM(領域 M・U-M0/U-M1)・units.yml に登録 |

実機 E2E(まっさらな構築から)= 白紙 0 → M0 の模範解後 55 → M1 の模範解後 100。課題ごとの確認は白紙で通らず、模範解後に通る。
M1-4(排他)は、RT01 から Telnet で入った 2 本目のセッションがロックを持っている間だけ通ることを確認。

### 計画から変えた点

- **M1-4 の 2 本目のセッションは Telnet**(RT01 → 10.0.12.1)。IOL の SSH クライアントは XR と折り合わず接続できなかった。
- **M0-3**: 「アドレスを持つ IF を VRF に移すとコミットが拒否される」は 24.3.1 では起きず、アドレスは残った(想定と逆)。課題は成立するので、読み物では IOS との違いとして扱った。
- **M1-5(全体の差し替え)は確認なし**。何も変更しない課題なので、状態で判定できない。模範解は最初から開ける。
- **履歴の仕込み**は起動直後だと初期設定の最後のコミットと順が混ざる・一時的に失敗する → 開始前に 25 秒待ち、失敗時は確定だけやり直す。

### 追加(2026-10-15)

- **M1-7(変更を完全に取り消す)**を追加。M1-6 は「原因の特定」が主題なので戻し方は自由のまま(手で `no` を打っても正解)。
  M1-7 は、仕込みの CHG2001 が既存の値を書き換えて消している(LINK3 の MD5 鍵・hello/dead・Loopback101 の説明)ので、
  鍵だけは暗号化された形でしか見えず手で打ち直せない → 禁止事項を書かずに履歴からの取り消しへ誘導する。
  `rollback configuration to CHG2001` でも戻るが、後のコミット(自分の作業)まで消える= 確認で落ちる。
  実機(24.3.1)で `load rollback changes` が暗号化された鍵・消したタイマー・説明文を元どおりに戻し、隣接が元の鍵で上がることを確認(poc/xr/expG.log)。
  RT01 は `service password-encryption` で鍵を平文で見せない。
- **ラベルのやり直し**: 正しいラベルを内容の足りないコミットに付けると二度と通らない(XR のラベルは使い回せず、個別に消せない)。
  チェックに `commit_label:` を足し、`{label}` を「ラベル か -2, -3 …」の最新に解決する(`_grade_attempt.yml`)。

### 作って分かった注意点(次の単元でも効く)

- 仕込みの道具は、字下げの無い行の前で `root` に戻る。サブモードのまま流すと、その中で有効な語(例: OSPF の area の中の `interface Loopback101`)として入ってしまう(2026-10-15 実発)。
- 確認で「ある語が無いこと」を見るときは範囲を絞る。LINK3 が正しく認証を使うようになって、設定全体に `message-digest` が無いことを見ていた M1-6 の確認が誤って落ちた。
- IOL の `show ip ospf interface` は MD5 認証を `Cryptographic authentication enabled` と表示する。

- XR の SSH は既定で毎分 60 接続・VTY 5 本。続けて採点すると接続が切られ、**出力がエラー文になって否定条件だけのチェックが誤って通る**。
  対処= baseline で `ssh server rate-limit 600`・`vty-pool default 0 30`。チェックは否定条件だけで作らない(肯定条件と同じ項目に入れる)。
- `| include a|b` は XR では不可。`| include "a|b"` と引用符で囲む。採点のコマンドでも同じ。
- `show ip interface brief`・`show ip route` は XR でも通る(`ip` は非推奨の別名)。「XR に `show ip` は無い」とは書けない。
- 確認つきコミットの確定後、履歴に残るラベルは確認つきコミット側に付く。ラベルは一意(失敗したコミットのラベルは消費されない)。
- `end` で未コミットの行があると `Uncommitted changes found, commit them before exiting(yes/no/cancel)? [cancel]:` と聞かれる。
  自動投入の道具が確認に yes と答える作りだと、意図しない設定が入る(PoC の道具で実発)。

## 12. M2 管理プレーン(2026-10-17 設計中・PoC中)

**範囲= SPCOR 1.5.a(LPTS)・1.6.b(AAA と TACACS)・1.7.b(ACL)＋XR の権限モデル(タスク ID)と管理プレーン保護(MPP)。**
ラボは新しく `XRT-02` を立て、**M2 と M3(OSPF・短く)で共用**する(XR の起動が遅いので 2 単元で 1 ラボ= XRT-01 と同じ考え方)。

### 12.1 盤面(案)

XR01(IOS XR)＋RT01(IOL・データ側の相手。Telnet/ping の発信元)＋SRV01(Ubuntu・AAA サーバ)。M3 用に RT02 を足すかは M3 の設計で決める。

### 12.2 課題(案)

| 課題 | 挙動での指定 | XR で新しいこと | 確認の方法 |
|---|---|---|---|
| M2-1 権限 | 運用担当のアカウントは、ルーティング表・OSPF の状態・IF の状態を見られて、ping と IF カウンタのクリアができ、設定は一切変えられない | タスク ID・タスクグループ・ユーザグループ。**`describe <コマンド>` で必要なタスク ID を自分で調べる** | 採点側がそのアカウントで実ログインし、許可/拒否を実際に打って見る(新設の `exec: local` 想定) |
| M2-2 MPP | SSH は管理 IF からだけ受ける。データ側からは RT01 の Loopback0 だけが Telnet で入れる | `control-plane management-plane`(帯域内/帯域外)。M1 の確認つきコミットを理由のある場面で再び使う | RT01 から発信元を変えて Telnet(許可 1・拒否 2)＋管理 IF の SSH が生きていること |
| M2-3 AAA | ログインは SRV01 で認証する。サーバにしかいないユーザでも入れて、サーバの指定どおりの権限になる。サーバが落ちている時だけローカルで入れる。コンソールは常にローカル | AAA の方式リスト・サーバ側からタスクグループを渡す | サーバのユーザで入れること・権限・サーバ停止中のローカル(破壊フェーズは SRV01 上の 1 本のスクリプト= GEN-AAAGRP と同じ作り) |
| M2-4 LPTS | XR01 宛ての ICMP echo を毎秒 N 個に絞る。通過する ICMP と他のプロトコルには影響させない | LPTS(IOS の CoPP にあたる。クラスを作らず、既定で全部の流れに上限がある) | LPTS の表で ICMP-local の上限値＋RT01 からの連打で AggrDrops が増え、通常の ping は通ること |
| M2-5 ACL(軽め・移植型) | データ側 IF で偽装送信元(自分の Loopback・私設の範囲など)を入力で落とす。OSPF の隣接は保つ | XR の ACL の書き方(行番号・`ingress`)。入力 ACL が自分宛ての OSPF も落とすので、許可を忘れると隣接が落ちる(IOS と同じ挙動= XR 固有ではない) | 偽装送信元の ping が落ちること＋隣接 FULL |

### 12.3 PoC の結果(2026-10-17・XRT-01 の XR01 を借りて実測。記録= `poc/xr/expM2-*.log`)

- **権限(E3)**: タスクグループ→ユーザグループ→ユーザで作ると、そのユーザは
  - 許可の無い `show` は `% This command is not authorized`。`configure` には入れるが、行ごとに `not authorized` で何もコミットされない。
  - ★`show running-config` は**読める部分だけが表示される**(IF は名前と説明だけ・IP は出ない 等)。エラーにならない。
  - `describe <コマンド>` が必要なタスク ID を出す(例: ping = root-system EXECUTE と basic-services READ WRITE EXECUTE・`show route` = rib READ・`clear counters interface` = interface EXECUTE)。M2-1 の調べ方の核にする。
- **MPP(E2)**: 帯域外に管理 IF(VRF MGMT)と `allow SSH` を書くと、データ側 IF の Telnet と SSH は `Connection refused`、
  管理 IF の SSH は生きたまま。`show lpts bindings brief` の受付が `Mg0/RP0/CPU0/0` に限定されたことで確かめられる。`show mgmt-plane` でも見える。
- **確認つきコミットの続き(新しい落とし穴)**: 確認待ちで**設定モードを抜けずにセッションが切れた**場合は即取り消しにならず、
  期限まで試行状態で残る。その間は**他のセッションからコミットできない**(`Cannot commit because there is an unexpired trial/rollback session`)。
  M1 で書いた「設定モードを抜けると即取り消し」は `end`/`exit` で抜けた場合の話。
- **TACACS+**: Ubuntu 24.04 の標準リポジトリにサーバのパッケージが無い。ソースからのビルド(tac_plus-ng)を SRV01 で試す。
  だめなら RADIUS(FreeRADIUS は GEN-AAAGRP で実績あり)に切り替える。
- **LPTS(E4)**: `lpts pifib hardware police` の下の `flow icmp local rate 10` が XRv9000 でも効く。RT01 から `timeout 0` で 1000 発 → 
  `show lpts pifib hardware police location 0/0/CPU0` の ICMP-local で AggrDrops 964。上限 10 だと通常の ping(20 発)も半分落ちる
  (burst 5)。課題の値は 50〜100 程度にして、通常の ping は通る形にする。★表示は LC(`0/0/CPU0`)でしか出ない(`0/RP0/CPU0` は「only supported on LC」)。
  XR01 宛ての ping は ICMP-local に数えられる(ICMP-default ではない)。
- **ACL(E5)**: LINK2 に入力 ACL(TCP だけ許可)を当てると OSPF の隣接が dead で落ちた= 自分宛ての制御トラフィックも落とす。IOS と同じなので
  XR 固有の題材にはならない → M2-5 は軽い移植型にする。ACE ごとの一致件数は既定では出ない(要確認: 統計の有効化)。
- 後始末= `rollback configuration to M1-7` で PoC の変更をすべて取り消した(poc/xr/expM2-restore.log)。

### 12.4 実装で足すもの

1. 採点の `exec: local`(採点機から指定の資格情報で SSH し、許可/拒否を実際に打つ)。M2-1 と M2-3 で使う。
2. SRV01(Ubuntu)の AAA サーバ。TACACS+ はソースからビルド(cloud-init で)→ 起動時間と成否を測る。
3. 課題文(英日)・`learn.yml`(段階式ヒント・模範解)・読み物 M2(英日)。


### 12.5 実装の結果(2026-10-18)

- ラボ `XRT-02`(XR01+RT01(IOL)+SRV01(Ubuntu・TACACS+))。課題 M2-1〜M2-5・読み物 `courses/xr/{en,ja}/20-m2-management-plane.md`。
- 採点に `exec: local` を追加(`_grade_attempt.yml`。shell と同じタスクで採点機から実行・資格情報は環境変数)。道具= `topologies/login_probe.py`
  (指定ユーザで SSH して行を流す/IOS 機から送信元を変えて Telnet/前後に Linux ノードでコマンド/`--wait-tacacs`)。
- SRV01 の TACACS+ = Ubuntu 22.04 系の `tacacs+` 4.0.4.27a の .deb を、依存の `python` を外して導入(cloud-init・約 1 分で稼働)。
  受け付けるクライアントは 1.1.1.1 だけ(host 単位の鍵)。

### 12.6 計画・PoC から変えた点(実機で分かったこと)

| 論点 | 計画/想定 | 実機(24.3.1) |
|---|---|---|
| ping に要るタスク | `describe ping` が root-system EXECUTE も要求 | root-system はタスクグループに入れられない(構文エラー)。当のユーザで `describe` すると basic-services だけ。**describe の答えは打つユーザで変わる** |
| 送信元 IF なしの TACACS+ | 応答なし→タイムアウト待ちの後にローカル | サーバが鍵不一致で即切断(ログ= Invalid AUTHEN/START packet)→ XR は即エラー扱いでローカルへ。待ちは無い |
| `aaa authorization exec` | サーバの `task` を受け取るのに必要(公式の例は全部これを書く) | 無くても task が届く(ログイン 1 回でサーバへ 2 接続)。模範解からは外し、補足で触れる。公式に「無いとどうなるか」の記述は無い |
| サーバ停止後の復帰 | 起こせばすぐ使われる | XR は on-hold・status=down のまま約 25 秒使わない(`holddown-time` で変更可)。採点はサーバを止めた後 `--wait-tacacs` で status=up を待つ(待たないと続くログインがローカルに落ちて誤失敗。2 回に 1 回の割で再現した) |
| M2-4 の「通常の ping は通る」 | RT01 から ping | IOL の ping は応答直後に次を送るので上限 50 では 3 発目が毎回落ちる(!!.!!)。確認は SRV01(Linux)から= 0.2 秒間隔は全通・`ping -f` は約 6 割落ちる(既定 1500 pps では 0%) |
| `show aaa …` の設定表示 | `show running-config aaa authentication login` | 不完全コマンド。`show running-config aaa` で全体を取る |
| MPP のコミット直後 | — | 管理 IF の SSH が約 1 秒拒否される(続けて流す投入スクリプトが当たった。人の操作では気づかない程度) |
| ACL の書式 | 行番号は手で打つ | 省略すると 10・20… が自動で付く。`101` のような数字も名前として通る |

### 12.7 公式文書での裏どり(2026-10-18・ASR 9000 24.x の System Security ガイド/コマンドリファレンス)

- `task` 属性の `#名前` は **ユーザグループ**(ガイド「the pound sign (#) indicates that a user group follows」)。サーバ側の `#netadmin` 等はこれに従う。
- 次の方式は「エラーのときだけ・拒否のときは使わない」(ガイド「used only if the initial method returns an error, not if the request is rejected」)。
- `tacacs source-interface <IF> vrf <VRF>`・MPP(既定は無効で全 IF が受ける/設定すると指定 IF 以外は破棄)・LPTS のフロー icmp-local と表示コマンド= 確認済み。
- 文書に記述が無く実測だけに拠るもの= `show running-config` の権限による省略・`describe` のユーザ依存・authorization なしで task が届く・保留約 25 秒・ポリサーのバースト。読み物の注記に列挙した。
- 通し検証(2026-10-18)= 作り直した XRT-02 で白紙 0 → 模範解(`poc/xr/solve_xrt02.sh`)100。学習モードの API 経由で 5 課題とも通過(所要 12〜60 秒・制限 240 秒)。

## 13. M3 OSPF(2026-10-18 完了)

XRT-02 に同居(RT02 と LINK2・LINK3 を追加・最終採点の配点 M2 60 / M3 40)。

| 課題 | 中身 | 実機で分かったこと |
|---|---|---|
| M3-1 | プロセス単位 `passive enable`+LINK1 だけ解除の初期設定で、LINK2 の隣接が上がらない(TS)。設計規則(新しい IF は明示しない限り黙る)を残して直す | `show ospf interface` に「No Hellos (Passive interface)」。`show running-config router ospf 1 inheritance detail` は継承した passive を**注記しない** |
| M3-2 | OSPFv3 で IPv6 ループバックを交換 | ネットワーク タイプ不一致で FULL/DR・ルートなし(M0-2 と同じ罠が再現)。★XR の IPv6 ルート表は OSPFv3 のルートを `Known via "ospf 1"` と表示(ospfv3 ではない) |
| M3-3 | エリア 1 を完全スタブ+`range 172.16.0.0/22`。初期は RT02 だけ stub(フラグ不一致で隣接なし) | `range` は `range … advertise` と表示される。★IOS の `show ip route` はクラスフル見出しの下にプレフィックス長なしで並べる(採点の正規表現は見出し「172.16.0.0/22 is subnetted, 1 subnets」で見る) |

- RT01 の LINK2 はコスト 100(予備)。等コストだとゲスト網の通信が LINK2 から入り、M2-5 の ACL(LINK1 の入力)をすり抜ける。
- 採点の不具合(既存)を修正: `grade.yml` の「XR は become しない」が、XR を見ないチェックポイントでも XR01 を `_graded` に入れ、
  指紋照合が `labid_exec is undefined` で止まった → 採点対象のノードに絞った。
- 公式(Routing Configuration Guide「OSPF Hierarchical CLI and CLI Inheritance」)と食い違いは無し。上の 2 点(inheritance detail・ospf 表示)は実測のみ。


## 14. XRv9000 と XRd の比較 PoC(2026-10-18・M5/M6 着手前)

**方針(2026-10-18 ユーザ指示)**= 可能な限り XRd を使う。XRv9000 と明らかな差が出る単元(機能が無い・挙動や表示が違い学習不足になる)は
XRv9000 を優先。「本物の手触りが掴める範囲で XRd を許容」。判定は単元ごと(今回は M5 RPL・M6 BGP と基本。M7 以降は着手時に同じ要領で)。

- 盤面= `problems/_POC-XRCMP`(同じアドレスの 2 系統を独立に組む。A= RT01─XRV01(XRv9000 26.1.1)─RT02、B= RT03─XRD01(XRd 26.1.1)─RT04)。
  版の差を混ぜないよう 26.1.1 どうしで比べる(既定の XRv9000 は 24.3.1)。ノード単位の機種・版の差し替えに
  `node_xr_platforms`・`node_images` を `gen_cml_lab.py` に足した。
- 手順= `poc/xr/cmp_m5m6.sh`(base / rpl / bgp)を両機種へ同じ順で流し、ログ `poc/xr/cmp-{xrv,xrd}-*.log` を突き合わせる。
- 判定の基準= コマンドが無い・拒否される／挙動が違う／show の出力が違い読み物・採点がずれる、のどれかに当たれば XRv9000。

### 14.1 結果(2026-10-18 実測・ログ `poc/xr/cmp-{xrv,xrd}-{base,rpl,bgp}.log`)

CML の XRd は **XRd Control Plane**(`show version`= "cisco XRd Control Plane")。公式のデータシートは
「XRd Control Plane provides minimal forwarding capabilities, which is adequate for peering or southbound interfacing」
(用途は vRR・PCE)。実測もこの位置づけどおりで、**制御プレーンは同じ・転送と一部の機能に差**。

| 区分 | 論点 | XRv9000 26.1.1 | XRd 26.1.1 |
|---|---|---|---|
| 基本 | 起動(BOOTED まで) | **約 3 分**(24.3.1 は約 8 分) | 約 2 分 |
| 基本 | パッケージ | 1 個の一体イメージ | 884 個(XR 116)の分割パッケージ |
| 基本 | exec の `show` 第 1 階層 | 371 語 | 289 語 |
| 基本 | XRd に無い主なもの | — | **ntp・ipsla・telnet(設定)・pbr**・ppp/pppoe/l2tp/vpdn・subscriber・performance-mgmt・eigrp(show)・msdp・nve・`ethernet`(設定) |
| 基本 | 本線の機能(設定・show とも) | あり | あり= router(ospf/isis/bgp)・RPL 一式・mpls・l2vpn・evpn・segment-routing・bfd・lacp・policy-map/class-map・flowspec・telemetry・netconf-yang・grpc・lpts・rsvp・srlg |
| M5 | ポリシーなし eBGP= `!` 付き・受信 0・「defaults to 'drop'」「No policy: 5」 | 同 | 同(出力も一致) |
| M5 | prefix-set(ge/le)・community-set・as-path-set・引数つき・`apply`・if/elseif | 同 | 同 |
| M5 | 末尾まで pass しない経路は破棄(11.11.11.11・/26 が落ちる) | 同 | 同 |
| M5 | 使用中の prefix-set を書き換え→ clear なしで 15 秒以内に反映(既存の set は丸ごと置換の警告) | 同 | 同 |
| M5 | 未定義ポリシーの適用・使用中ポリシーの削除・適用点に無い属性(OSPF 再配送で community)→ コミット失敗と `show configuration failed` の文言 | 同 | 同 |
| M5 | `show rpl route-policy X attachpoints`・`show rpl prefix-set X attachpoints`・`show rpl active/inactive route-policy`・`show bgp … policy` | 同 | 同 |
| M5 | `received routes` は soft-reconfiguration inbound が要る(無いと案内文) | 同 | 同 |
| M6 | RR・next-hop-self・`bestpath-compare`・advertised-routes・IPv6 AF の設定 | 同 | 同 |
| 転送 | 通過 ICMP(ping 20 発・1500 バイト・DF) | 100% | 100% |
| 転送 | **通過する TCP/UDP** | 正常 | ★**L4 チェックサムが壊れて出る**(CML のリンク捕捉で入口 `udp sum ok`→出口 `bad udp cksum`・TCP も `incorrect`)。受け側 IOL の checksum errors が増え、traceroute の 2 ホップ目以降は `*`、XRd 越しの SSH はバナーが返らない |
| M7 | BFD(IOL と単一ホップ・BGP に `bfd fast-detect`) | UP | ★**セッションが作られない**(設定は通るが `show bfd session`・`summary` が空。IOL からの BFD パケットは正常に届いている) |

- XRd 自身が出す TCP(BGP)は正常。壊れるのは **XRd を通り抜ける** TCP/UDP。CML の xrd ノード定義は全 IF に
  `XR_INTERFACES=…,chksum` を付けている(チェックサムの付け直しの指定)。これが通過パケットにも働いて壊している可能性があるが未検証
  (確かめるには `chksum` を外した別のノード定義が要る= CML の定義を足す操作なのでユーザ判断)。

### 14.2 判定

| 単元 | 機種 | 理由 |
|---|---|---|
| M5 RPL | **XRd** | 挙動・表示・エラー文まで一致 |
| M6 BGP | **XRd**(条件つき) | 制御プレーンは一致。ただし盤面で「XRd を通り抜ける TCP/UDP」を作らない(IOL どうしのセッションを XRd 越しに張らない・XRd 越しの SSH/traceroute を確認手段にしない)。確認は ping と XR 自身の show で |
| M4 IS-IS | **XRd**(2026-10-21 確定・§17.4) | 制御プレーンのみ。比較 PoC で全出力一致 |
| M7 高可用性 | **XRv9000** | BFD が動かない |
| M8〜M12(MPLS 転送・L3VPN・SR の転送・L2VPN・QoS・uRPF) | **XRv9000**(見込み) | Control Plane 版は転送が最小限。着手時に確認。★M8 は比較 PoC で差なし → XRd(§20.6) |
| M13 自動化 | XRd(見込み) | netconf-yang・grpc・telemetry はあり。着手時に確認 |

## 15. M5 RPL(2026-10-18 設計・実装中)

ラボ `XRT-03`(M5 RPL。M6 BGP でも同じ盤面を使う想定)。**XR01 は XRd**(§14.2 の判定。problem.yml で `node_xr_platforms` に固定)。
XRd 越しの TCP/UDP は作らない= BGP はすべて XR01 で終端し、確認は XR01 と各 IOL の show で行う。

### 15.1 盤面

| リンク | XR01 | 相手 | アドレス |
|---|---|---|---|
| ISP-A | Gi0/0/0/0 | RT01(AS 65101) | 10.0.11.0/24(.1 / .2) |
| ISP-B | Gi0/0/0/1 | RT02(AS 65102) | 10.0.12.0/24 |
| CUST | Gi0/0/0/2 | RT03(顧客・AS 65201) | 10.0.13.0/24 |

- XR01= AS 65000・Lo0 1.1.1.1・自社のプレフィックス 203.0.113.0/24(Null0 の static+`network`)。
- RT01 が送るもの: 0/0・11.0.0.0/8(65101)・12.1.0.0/16 と 13.1.1.0/24(65101 65301)・13.1.2.0/25(長すぎ)・
  10.10.0.0/16・172.20.0.0/16・192.168.50.0/24(私設)。
- RT02 が送るもの: 0/0・11.0.0.0/8(65102 65101)・12.1.0.0/16 と 13.1.1.0/24(65102 65301)・14.2.0.0/16(65102 だけ)・
  13.1.4.0/26(長すぎ)・172.31.0.0/16(私設)。
- RT03 が送るもの: 198.51.100.0/24(65201:500 65000:1001= ISP-A へ出さない合図)・198.51.101.0/24(65000:1002= ISP-B へ出さない合図)・
  198.51.100.128/25(長すぎ)・13.1.1.0/24(経路 65201 65101= 顧客が他所の経路を漏らす)・198.51.100.0/24 は 65201 を 2 回前置。

### 15.2 課題

| 課題 | 中身 | ねらい(RPL の論点) |
|---|---|---|
| M5-1 | (TS)両 ISP と Established なのに何も送受していない。ISP-A は方針なし、ISP-B には同僚が入れた「私設だけ落とす」つもりの方針がある。両 ISP から全部受け、各 ISP へは 203.0.113.0/24 だけ出す | eBGP の既定の拒否・**pass しないまま末尾に来た経路は捨てる**(route-map の「最後の permit を書き忘れ」と見え方が違う)・prefix-set |
| M5-2 | 両 ISP から デフォルト・私設(長さ問わず)・/24 より長いもの を受けない | prefix-set の ge/le・同じ set を 2 か所で使う |
| M5-3 | ISP-A を主(LP 200)・ISP-B を従(LP 100)。受けた経路に 65000:101/102 を付ける。**ポリシーの定義は 1 つ**で両 ISP に付ける(3 社目が来ても定義を増やさない)。M5-2 の濾過はそのまま効かせる | 引数つきポリシー・`apply` で既存の濾過を呼ぶ・set community |
| M5-4 | 顧客から: 198.51.100.0/23 の内側(/24 まで)・顧客 AS が起点(前置は可)のものだけ受ける。顧客の経路を両 ISP に出す(65000:1002 付きは ISP-B へ出さない・65000:1001 は ISP-A へ出さない)。65000:* は ISP へ漏らさず、顧客の 65201:* は届ける。顧客へは XR01 の持つ経路を全部渡す | as-path-set(ios-regex)・community での条件分岐・`delete community in`・send-community-ebgp との関係 |

- 実機で確かめる論点(PoC): set だけを実行して pass を書かずに末尾に来た経路の扱い(「set は暗黙の pass」か)/
  `delete community in (65000:*)` の書き方/前置つき経路の ios-regex/ M5-1 の `!` 表示と方針ありの ISP-B の見え方の違い。

### 15.3 PoC の結果(2026-10-18・XRT-03 の XR01= XRd。記録 `poc/xr/expM5-sem*.log`)

| 論点 | 実機の挙動 |
|---|---|
| 出発点の見え方 | 方針なしの ISP-A は「eBGP neighbor with no inbound or outbound policy; defaults to 'drop'」、入力だけある ISP-B は「no outbound policy」。summary は 3 隣接とも `0!`。ISP-B は受けた 7 本を全部「By policy」で捨てる(ISPB-IN に pass が無い) |
| set だけのポリシー | **set を実行した経路は受け入れられる**(set が暗黙の pass)。`set local-preference 150` だけ→全経路が LP 150 で入る。`if … then set … endif` だけ→条件に合った経路だけが入り、合わない経路は捨てられる |
| as-path の判定 | `ios-regex '^65201(_65201)*$'` と `as-path originates-from '65201'` のどちらでも、前置つき(65201 65201 65201)は通し、漏れ(65201 65101)は落とす |
| community | `community matches-any (65000:1002)`+`drop`、`community-set` に `65000:*`、`delete community in <set>` が通る。ISP 側には 65201:500 だけが届く(要 `send-community-ebgp`) |
| ★IOS 側の注意 | IOL は起動直後の BGP がしばらく最良経路を選ばない(update-delay)。構築直後に経路が 0 本に見えても 1〜2 分待つ |

### 15.4 実装の結果(2026-10-18)

- 成果物= `problems/XRT-03`(課題 4 本・課題ごとの確認 `grading.m5t1〜4.yml`・最終 `grading.yml` 配点 25/20/25/30・学習モード `learn.yml`)、
  読み物 `courses/xr/{en,ja}/50-m5-rpl.md`・実践 `51-m5-practice.md`(課題文から切り出し)。模範解の投入= `poc/xr/solve_xrt03.sh`。
- 実機 E2E= 作り直したラボで白紙 0(最終・課題ごと全部)→ 模範解 100(最終・課題ごと全部)。記録 `poc/xr/expM5-e2e.log`。
- 計画から変えた点: M5-1 の模範解は ISPB-IN を直して流用せず、両 ISP 向けの名前 `ISP-FILTER` に付け替え(後の `apply` が読みやすい)。
  M5-2 は PRIVATE の set を太らせず、条件にインラインの set を足す(set の名前と中身を一致させる)。
  顧客の 198.51.100.0/24 に 65000:1001 を足し、2 本の顧客経路が「片方は ISP-A だけ・もう片方は ISP-B だけ」になるよう対称にした。
- 追加で分かったこと: パラメータを足した定義だけを先にコミットすると「Mismatch in number of parameters passed to policy at an attachpoint」で失敗
  (定義と付け所を同じコミットで変える)。iBGP には `send-community-ebgp` なしでもコミュニティが届く。
- 基盤の修正: `xr_reset.py` — ①`rollback configuration to <ID>` は「その回も含めて取り消す」(ヘルプ「up to (and including)」)。
  BL-254 の実装は 1 回戻りすぎていた(XRv9000 では最後の回が ZTP の後始末なので表に出なかった)→ `to-exclude <ID>` に修正
  ②XRd は初期設定が履歴に残らない→ 戻り先を `first-boot` と記録し、`to <最古の ID>` で戻す ③XRd は起動が速く、
  構築直後の記録の時点で SSH が開いていない→ 記録は最大 5 分つなぎ直す。

## 16. M6 BGP(2026-10-18 設計・実装中)

**XRT-03 に同居**させ、M5 を終えた状態から M6 に進む(ユーザ要望「M5〜M6 まで通せるように」)。XR01 は引き続き XRd。
盤面に **RT04(IOL・AS 65000 の社内ルータ)** を足す。XR01 Gi0/0/0/3 ── RT04 Et0/0(10.0.14.0/24)。XR01 と RT04 は OSPF エリア 0
(リンク・両者の Lo0。RT04 の社内 LAN 203.0.113.128/26・203.0.113.192/26 も OSPF)。プロバイダ・顧客のリンクは OSPF に入れない。
RT04 の BGP は据え付け済み(`neighbor 1.1.1.1 remote-as 65000 update-source Loopback0`)。XR01 の初期設定には 4.4.4.4 の隣接を
**update-source なし**で置く(M5 の間は Active のまま= 課題文で M6 の対象と明記)。BGP の TCP は XR01 で終端するので XRd の制約に触れない。

| 課題 | 中身 | ねらい |
|---|---|---|
| M6-1 | (TS)RT04 との iBGP が上がらない。上げたうえで、RT04 がプロバイダと顧客の経路を使える(ルート表に入る)ようにする。リンクのサブネットを OSPF に入れてはならない | update-source(ループバック間 iBGP)・iBGP には RFC 8212 の既定の拒否が無い・next-hop-self |
| M6-2 | 社内 LAN(OSPF で学ぶ 203.0.113.0/24 より長いもの)を顧客に渡す。ループバックやリンクは渡さない。プロバイダには引き続き /24 だけ | 再配送の付け所に RPL(`redistribute ospf 1 route-policy`)・既存の ISP-OUT の完全一致が /26 を止めること |
| M6-3 | インターネットからの着信は ISP-A を優先: ISP-B へ出す経路(自社・顧客)は AS パスを 3 つ長くする。ISP-A へは変えない。ISP-B に出す経路の範囲は M5 のまま | prepend・★`apply` の後の set は、適用先が pass しなかった経路まで受け入れる(漏れる)→ `if apply … then` か、ISP-OUT に引数を足す |
| M6-4 | 両プロバイダに共通の設定(コミュニティ送信・受信上限 1000 と 80% で警告)を 1 か所に持つ。3 社目は「アドレス・AS・引数」だけで足せる形に | neighbor-group・af-group と継承・`show bgp neighbor … configuration` の出どころ表示 |

### 16.1 PoC の結果(2026-10-18・XRT-03 の XR01= XRd。M5 の模範解を入れた状態で実測)

| 論点 | 実機の挙動 |
|---|---|
| `apply` の後の prepend | `apply ISP-OUT(1002)` → `prepend as-path own-as 3` の方針で、ISP-OUT が pass しなかった経路(ISP-A の経路・65000:1002 付きの顧客経路)まで ISP-B に出た= **書き換えが受け入れになり漏れる** |
| `if apply … then` | `if apply ISP-OUT(1002) then prepend … endif` で、ISP-OUT が通すものだけが prepend されて出る |
| `prepend as-path own-as 0` | コミットは通り、何もしない(ISP-A は 65000 のまま)。引数 `$pp` で ISP ごとに 0/3 を渡す書き方も成立 |
| 参照中の方針の引数の数を変える | `Policy [ISP-OUT] was used with (1) parameter(s) in policy [T-B-OUT], but [ISP-OUT] is defined with (2) parameter(s).` でコミット失敗(apply 先も検査される) |
| neighbor-group / af-group | `show bgp neighbor X configuration` が値ごとに出どころを表示(`maximum-prefix 1000 80 [n:ISP a:ISP-AF]`)。`show bgp neighbor-group ISP configuration` も同様。`show running-config … inheritance` は継承分を展開しない |

### 16.2 実装の結果(2026-10-18)

- 成果物= XRT-03 に RT04 と CORE リンクを追加(`initial/RT04.cfg.j2`・XR01 に OSPF と 4.4.4.4 の隣接)、課題 M6-1〜4(`grading.m6t1〜4.yml`)、
  最終 `grading.yml` を M5 50(12/10/13/15)/ M6 50(15/10/15/10)に組み直し、`learn.yml` に M6 の 4 課題、
  読み物 `courses/xr/{en,ja}/60-m6-bgp.md`・実践 `61-m6-practice.md`。模範解= `poc/xr/solve_xrt03.sh`(m6t1〜4 を追加)。
- 実機 E2E= 構築直後へ戻した状態で、最終と課題ごとの 8 本がすべて 0 → M5〜M6 の模範解ですべて 100(`poc/xr/expM56-e2e.log`)。
  誤答の判別= `apply ISP-OUT(…)` の後に prepend を置く書き方で M6-3 は 70 点(漏れを見る項目が不合格)。
- M6 を入れた後も M5 の確認 4 本は 100 のまま(プリペンド後の経路長でも M5 の正規表現が一致するよう確認)。
- 追加で分かったこと: RT04 では update-source だけ入れた段階で `10.0.11.2 (inaccessible)`・no best path(next-hop-self の必要が見える)。
  iBGP には方針なしで経路が届き、コミュニティも届く。`show bgp ipv4 unicast X bestpath-compare` は負けたパスの末尾に負けた理由を出す
  (「Lower local preference than best path (path #1)」)。
- M6-1 の確認「リンクを OSPF に入れていない」は白紙でも通るので、RT04 のルート表の肯定条件と同じ項目にまとめた。

## 17. M4 IS-IS(2026-10-21 完了)

**範囲= SPCOR 2.1(IS-IS の実装 IPv4/IPv6: a ルート広告・b エリアの付番・c 単一/マルチトポロジ・d メトリック)と 2.6(隣接・広告)。**
Enterprise の CCNP では IS-IS をほぼ扱わないので、**この単元だけは技術そのものを読み物で厚く説明する**(§1 の方針)。
ラボは新しく `XRT-04`。XR01 は XRd の見込み(§14.2)→ 着手時に XRv9000 26.1.1 と同じ手順で比べる(`poc/xr/isis_poc.sh`・盤面 `_POC-XRCMP`)。

### 17.1 盤面(案)

| リンク | XR01 | 相手 | アドレス |
|---|---|---|---|
| ACCESS | Gi0/0/0/0 | RT01(IOL・L1 だけ・area 49.0001) | 10.0.11.0/24・2001:db8:11::/64 |
| CORE-A | Gi0/0/0/1 | RT02(IOL・L2 だけ・area 49.0002) | 10.0.12.0/24・2001:db8:12::/64 |
| CORE-B | Gi0/0/0/2 | RT03(IOL・L2 だけ・area 49.0003) | 10.0.13.0/24・2001:db8:13::/64 |
| (RT02─RT03) | — | RT02 Et0/1 ─ RT03 Et0/1 | 10.0.23.0/24・2001:db8:23::/64 |

- XR01= L1/L2・area 49.0001。ループバックは 10.255.0.0/24 から(XR01 .1・RT01 .11・RT02 .2・RT03 .3)、IPv6 は 2001:db8:255::<同じ番号>/128。
  システム ID はループバックから作る慣習(10.255.0.1 → 0102.5500.0001)。
- バックボーン(RT02・RT03)は wide メトリックへ移行済み。RT03 の CORE-B 側は予備リンクとしてメトリック 1000。
  RT02・RT03 はサービス網(10.20.0.0/16・10.30.0.0/16)も IS-IS に載せている。
- IOL はすべて IPv6 を単一トポロジ(IOS の既定)で運用。

### 17.2 課題(案)

| 課題 | 中身 | ねらい(SPCOR) |
|---|---|---|
| M4-1 | (構築)XR01 を IS-IS に参加させる。NET は慣習どおり・RT01 と L1、バックボーンと L2。各リンクは相手のレベルだけ・p2p・ループバックはハローを出さない | NET とエリア・レベルと隣接の規則・XR の設定の木(プロセスと IF のアドレス ファミリ)(2.1.b 2.6.a) |
| M4-2 | (TS)L2 の隣接は上がっているのにバックボーンと経路を交換しない。直す。CORE-B は予備(両方向 1000) | narrow と wide の不一致・レベルごとの metric-style・メトリックは片方向(2.1.d) |
| M4-3 | IPv6 も IS-IS で運ぶ(IOS 側は変えない) | XR の既定はマルチトポロジ・IOS の既定は単一トポロジ(2.1.c) |
| M4-4 | RT01 にバックボーンのループバック(/32・/128)だけを個別の経路で渡す。その他の他エリアの経路は既定経路のまま | ATT ビットと既定経路・L2→L1 の漏らし(up/down ビット)に RPL(2.1.a・M5 の再利用) |

### 17.3 PoC で確かめること

1. IOL(17.x)の IS-IS の可否と書式。
2. XR で IF を並べただけ(アドレス ファミリなし)・IF にだけ AF・プロセスにも AF、の各段の見え方。
3. 既定(metric-style・is-type・ハローのパディング・隣接のログ)。
4. narrow/wide の不一致の症状(隣接・DB・経路・ATT ビット)。narrow のまま 1000 を書いたとき。レベルごとの wide。
5. IPv6: IOS の単一トポロジと XR の既定の組み合わせの症状、`single-topology` での解消。IOS の adjacency-check で隣接が落ちるか。
6. `propagate level 2 into level 1` の書式・RPL・IPv6・ATT の既定経路が残るか。
7. XRv9000 と XRd で上の見え方が一致するか。

### 17.4 PoC の結果(2026-10-21・盤面 `_POC-XRCMP` に IS-IS を載せて XRv9000 26.1.1 と XRd 26.1.1 へ同じ手順。記録 `poc/xr/isis-{xrv,xrd}-*.log`)

**判定= M4 は XRd**。両機種の出力は PID・時刻・MAC・LSP の通番以外すべて一致(IS-IS は L2 で直接運ばれるので XRd のチェックサム問題にも触れない)。

| 論点 | 実機の挙動 |
|---|---|
| IOL の IS-IS | IOL(IOS XE 17.15)で動く。既定= level-1-2・narrow(生成/受け入れとも)・IPv6 は単一トポロジ |
| IF を並べただけ(AF なし) | `show isis interface X` = `Disabled (No topologies cfg on the intf)`・brief の All OK が `No`・隣接ゼロ |
| IF にだけ AF(プロセスに無し) | **それだけで隣接も経路も成立**(26.1.1)。プロセスの AF はトポロジ全体の設定の置き場 |
| XR 既定 | is-type level-1-2・Narrow/Narrow・IF メトリック 10・L1 LSP に ATT=1・IPv6 はマルチトポロジ・`log adjacency changes` なし(ADJCHANGE が出ない) |
| broadcast(XR 既定)× p2p(IOL) | 双方隣接なし。XR の `show isis interface` に `Last PDU Rejected: … P2P IIH, P2P IIH on LAN Interface` |
| narrow × wide(L2) | 隣接は Up・LSP も届く(相手は `IS-Extended`/`IP-Extended`)が経路ゼロ・`show isis topology` が `**`。★**XR は ATT ビットを 0 にする→ L1 ルータの既定経路も消える** |
| `metric-style wide level 2` | L2 だけ wide。ATT=1 に戻り L1(narrow の IOL)の既定経路も復活。両レベル wide にすると narrow の L1 ルータは経路を全部失う |
| narrow のレベルに 1000 | コミットは通る→ **63 に切り詰めて広告**・`%ROUTING-ISIS-4-WD_METRIC_NOT_CONF … Maximum narrow value 63 is used instead`。help は `<1-63> for narrow, <1-16777214> for wide` |
| IOL が IPv4+IPv6(ST)・XR が IPv4 だけ | **IOS が隣接を張らない**(XR は `Init`・IOS 側は表示なし)。IOS の `debug isis adj-packets` = `No usable IPv6 linklocal addresses in serial IIH` |
| XR 既定(MT)× IOS 既定(ST) | 隣接 Up(IOS は Protocol `M-ISIS`)。XR の adjacency detail= `Topology (not running): [IPv6 Unicast (neighbor doesn't participate)]`・IPv6 経路ゼロ(IOS の L1 には ATT の `::/0` だけ) |
| `single-topology` | 解消(隣接は 1 回 flap)。★IF メトリックは AF ごと= IPv4 側だけ 1000 だとリンクの IPv6 プレフィックスは 10 で広告(SPF の経路は IPv4 の IS 到達性に従う) |
| `propagate level 2 into level 1` | `route-policy` が必須(ポリシーなしの形は Incomplete)。AF ごとに書く・同じポリシーを両 AF に付けられる(prefix-set に v4/v6 混在可・`eq` も可)。attachpoints= `inter-area-propagate`。L1 LSP= `IP-Interarea`/`IPv6-Interarea`、IOS= `i ia`/`IA`。ATT の既定経路は残る。narrow の L1 へは 63 で頭打ち |
| NET の付け替え | 1 コミット(`no net` + `net`)で可。全隣接がいったん落ち、古い LSP は `Purge Originator` で残り寿命 0。IOS は以後しばらく XR を system ID で表示する |
| その他 | ループバックは Media Type `Loop`= ハローを出さない(passive は慣例)。passive にするとループバックのプレフィックスのメトリックが 0 になる。★`advertise passive-only` を入れて外すと IPv4 の `propagate` の漏らしが戻らない(両機種・`propagate` を入れ直すと戻る。原因未切り分け= 課題では使わない) |

### 17.5 実装の結果(2026-10-21)

- 盤面は 17.1 どおり(XR01= XRd・RT01 L1 narrow・RT02/RT03 L2 wide・IOL は全部 IPv6 単一トポロジ・RT03 の CORE-B 側は 1000)。
  XR01 の初期設定= 同僚の書きかけ(`router isis CORE` に慣習外の NET と IF を並べただけ)。
- 課題(17.2 から変えた点):
  - M4-1 に「IPv4 と IPv6 の両方を Loopback0 と 3 リンクで」を入れた(IOS の隣接チェックで IPv4 だけでは張れないため)。
    ループバックは元々ハローを出さないので「passive」は要件から外した。白紙の原因は 3 つ(AF なし・broadcast/p2p・IPv4 だけ)。
  - M4-2 の確認に「RT01 が経路を保つ」を入れ、両レベル wide の誤答を判別(実測 55 点)。
  - M4-3 に「リンクのサブネットも IPv4 と同じ経路」を足した= XR の AF ごとの IF メトリックを問う(`single-topology` だけの誤答は 80 点)。
  - M4-4 の「新しいループバックも XR01 を変えずに届く」は、採点のあいだだけ RT02 に Loopback99 を足して見る(`login_probe.py` に
    `--pre-cli`/`--post-cli`/`--settle` を追加)。/32 を列挙する誤答は 60 点。
- 成果物= `problems/XRT-04`(課題ごとの確認 `grading.m4t1〜4.yml`・最終 `grading.yml` 各 25 点・`learn.yml`)、読み物
  `courses/xr/{en,ja}/40-m4-isis.md`(この単元だけ技術そのものを厚く= 12 節)・実践 `41-m4-practice.md`。模範解= `poc/xr/solve_xrt04.sh`。
- 実機 E2E= 構築直後へ戻して白紙 0(最終・課題ごと 4 本とも)→ 模範解 100(同)。`learn.yml` の模範解の文字列を逐語で流しても 100
  (XR がサブモードをまたぐ入力を親へたどって受け付けることも確認)。ワークスペースの Check(API)でも M4-4 が通ることを確認(約 36 秒)。
  記録 `poc/xr/expM4-*.log`。
- 公式文書(ASR 9000 の Routing Configuration Guide「Implementing IS-IS」「Implementing Routing Policy」)と食い違いは無し。
  文書に記述が無く実測だけに拠るもの= 17.4 の表のうち、拒否 PDU の表示・IF の AF だけで足りること・ATT の連動・63 への切り詰めと警告・
  IOS の隣接チェックの表示・AF ごとの IF メトリック・ログの既定・NET 変更後の IOS の表示・advertise passive-only の件。

### 17.6 用語の追記(2026-10-21・ユーザ指摘「Juniper や技術ブログとアドレスの呼び名が違う(NSAP など)」)

読み物 §2 に、呼び名の対応表(NET・NSAP アドレス・ISO アドレス・NSEL/N-selector/SEL・システム ID)・エリアの 2 通りの言い方・
システム ID の 2 つの流儀を足した(日英)。裏どり:

| 論点 | ソース | 結果 |
|---|---|---|
| エリア アドレス= システム ID と SEL を除いた上位部分全体 | RFC 1142(ISO 10589 の本文)7.1.1 | 確認。XR の表示 `Area Address: 49.0001` とも一致 |
| AFI・IDI・HO-DSP の分け方([IDP, HO-DSP] がエリア アドレス) | RFC 1237 3.2 | 確認 |
| NET= NSEL を 00 にした NSAP・NSEL は最後の 1 オクテット・複数 NET はエリア部分だけ違ってよい | Cisco IOS「IS-IS Overview and Basic Configuration」・NX-OS コマンド リファレンス | 確認 |
| Juniper の呼び名と置き場所(`family iso address`・推奨は lo0)・システム ID は本番では MAC 等から | Junos IS-IS User Guide / IS-IS Overview | 他ベンダの補足として記載(信頼順のソース外) |
| AFI `49` = 私設 | フォーラム・解説サイトのみ(規格・Cisco 公式では見つからず) | 断定を「慣例として私設に使う値」に弱め、注記に「解説資料での説明」と明記 |

## 18. M4 追補 — IS-IS の 2 周目(2026-10-22 完了= 18.8)

**ねらい**= M4 は SPCOR 2.1 の a〜d を一通り押さえたが、SP の IGP として使い込むには薄い(認証・broadcast と DIS・要約・
複数のエリア アドレスが手つかず。DIS・LSP は読み物だけ)。このうち M7 以降の流れで自然に出てこないものを、
M4 の盤面を広げた短い課題で拾う(§5 の「IS-IS の深め方」①)。オーバーロード ビット・タイマー・BFD・NSF は M7 へ回す(§19)。

- ラボは新しく **`XRT-05`**(XRT-04 は解答済みのまま残す)。**初期状態= M4-1〜4 を解き終えた状態**+下の仕込み。
  M4 をもう一度解かずに M4-5 から始められるようにする(XRT-03 の M6 は M5 からの通しだったが、M4 は解き終えているため)。
- XR01 は **XRd**(§17.4 で IS-IS は XRv9000 と一致)。約束は M4 と同じ= **設定するのは XR01 だけ**(IOS 側は据え付け)。
- 読み物は M4 の章に 2 ページ足す= `42-m4-isis-deeper.md`(解説)と `43-m4-practice-2.md`(実践・課題文から切り出し)。
  既存の `40-m4-isis.md` は書き換えない(読み終えた本の段落の並びを崩さない)。

### 18.1 盤面(案)= XRT-04 に共用セグメントを 1 本足す

| リンク | XR01 | 相手 | アドレス |
|---|---|---|---|
| ACCESS | Gi0/0/0/0 | RT01 Et0/0 | 10.0.11.0/24・2001:db8:11::/64(XRT-04 と同じ) |
| CORE-A | Gi0/0/0/1 | RT02 Et0/0 | 10.0.12.0/24・2001:db8:12::/64(同) |
| CORE-B | Gi0/0/0/2 | RT03 Et0/0 | 10.0.13.0/24・2001:db8:13::/64(同) |
| (RT02─RT03) | — | RT02 Et0/1 ─ RT03 Et0/1 | 10.0.23.0/24・2001:db8:23::/64(同) |
| **SVC-LAN**(新) | Gi0/0/0/3 | SW01(非管理スイッチ)に RT02 Et0/2・RT03 Et0/2 | 10.0.100.0/24・2001:db8:100::/64(.1/.2/.3) |

- RT01 のアクセス LAN を 1 本の /16 から**ループバック 4 本**(10.11.1.0/24〜10.11.4.0/24・2001:db8:1011:1::/64〜:4::/64)に変える= 要約の題材。
- 仕込み(据え付け側の設定)= RT02・RT03 のレベル 2 に HMAC-MD5 の認証(ハローと LSP/SNP の両方・鍵チェーン)。
  RT03 の SVC-LAN 側に DIS の優先度(既定 64 より高い値)。M4-8 の案によっては RT01 にも NET を足す。
- problem.yml は `lab.switches: [SW01]`(gen_cml_lab の非管理スイッチ)・XR01 の slot 6 → Gi0/0/0/3。

### 18.2 課題(案)

| 課題 | 中身 | 論点 |
|---|---|---|
| M4-5 | (TS)昨夜、セキュリティ部門がバックボーン(レベル 2)に認証を入れたが、XR01 の分が作業から漏れた。XR01 を合わせる。RT01(旧型・認証なし)は経路を保つ | ハローの認証と LSP/SNP の認証は別物(ハローだけ直すと隣接は上がるのに経路が来ない)・XR の鍵チェーン・**レベルを付けずに入れると L1 にも効いて RT01 の経路を失う**(暗黙の最小変更) |
| M4-6 | SVC-LAN を IS-IS に載せる。この LAN ではレベル 2 の隣接だけを作り、**XR01 を DIS にする**(RT02・RT03 は変えない) | broadcast と p2p(M4-1 の癖で p2p にすると隣接しない)・優先度と同点時の SNPA・**IS-IS の DIS は奪い取る**(OSPF の DR と違う)・擬似ノード LSP と CSNP |
| M4-7 | バックボーンへは RT01 のアクセス LAN を IPv4・IPv6 とも**要約 1 本ずつ**で出す。エリア 49.0001 の中は個別のまま。M4-4 のループバックの漏らしは保つ | L1→L2 の要約は L1/L2 ルータで・AF ごと・レベルの指定・要約のメトリックと破棄経路・構成要素が全部消えたら要約も消える |
| M4-8 | エリア アドレスの付け替え(または併合)。**RT01 との L1 隣接と経路を落とさずに**行う | 複数のエリア アドレス(最大 3)・L1 隣接は共通のエリアが 1 つあれば成立・L2 LSP に載るエリアの和集合・付け替えの順序 |

- **M4-8 は 2 案から PoC で選ぶ**。
  - 案 A(付け替え)= RT01 は新旧両方の NET を持って据え付け済み。XR01 を新エリアへ移し、旧 NET を外す。
    1 コミットで入れ替えても隣接が落ちないなら課題として薄い(§17.4 で落ちたのはシステム ID も変えたため)→ その場合は案 B。
  - 案 B(併合)= RT01 は新しいエリア番号で据え付けられて届いた。XR01 は既存エリアのまま RT01 と L1 で隣接する。
  - 採点の「隣接を落とさない」は、XR の `show isis adjacency-log`(隣接の状態変化の履歴)か IOS 側の隣接の Uptime で見る想定。PoC で確定。
- 再配送(static を RPL つきでレベル 2 へ)は M4-7 に足すかを PoC 後に判断(課題が重くなるなら読み物だけ)。

### 18.3 PoC で確かめること(XRd 26.1.1+IOL 17.15。XRT-05 の盤面をそのまま PoC に使う)

1. 認証: XR の鍵チェーン(暗号アルゴリズム・有効期間の既定で鍵が有効か)と IOS の HMAC-MD5 の相互接続。
   ハローだけ合わせた時の症状(隣接 Up・LSP 拒否の見え方と数え方)。SNP の認証の扱い(XR の `snp send-only` 等の選択肢と IOS の既定)。
   レベル指定なしで LSP の認証を入れた時に、認証なしの RT01 の L1 LSP がどうなるか。
2. XRd が broadcast の LAN で隣接・DIS 選出できるか(IS-IS のマルチキャスト MAC を受け取れるか)。優先度のレベル指定・奪い取りの見え方。
3. 要約: レベル指定なしの既定・メトリック・XR が破棄経路(Null0)を入れるか・IPv6 の要約。M4-4 の propagate との干渉。
4. 複数エリア: 同じシステム ID で NET を 2 つ・1 コミットで入れ替えた時に隣接が落ちるか・`adjacency-log` の内容。
5. 白紙(初期状態)から模範解までの通しと、各課題の誤答の点数(M4 と同じく誤答を判別できるか)。

### 18.4 裏どりのソース(実装時)

- ASR 9000 Routing Configuration Guide「Implementing IS-IS」(認証・要約・優先度・NET)・System Security Configuration Guide の鍵チェーン。
- RFC 5304(IS-IS の HMAC-MD5)・RFC 5310(汎用の暗号認証)・RFC 1195(IP の IS-IS)・ISO 10589(RFC 1142)の DIS と擬似ノード。
- IOS 側= IS-IS の認証・要約の設定ガイド(IOS XE 17.x)。

### 18.5 PoC の結果(2026-10-22・XRT-05 の盤面= XRd 26.1.1+IOL 17.15。手順 `poc/xr/isis2_poc.sh`・記録 `poc/xr/isis2-*.log`)

| 論点 | 実機の挙動 |
|---|---|
| 初期状態(バックボーンだけ認証) | XR01 は相手のハローを受けて L2 隣接が `Init` のまま(XR は認証を設定していないので検査しない・相手は XR の無認証ハローを捨てる)。L2 隣接が無いので **ATT ビットが下り、RT01 は既定経路も失う** |
| 鍵 `key-string password <平文>` | **コミット失敗**= `'Key Chain Server Process' detected the 'fatal' condition 'Incorrect or NULL parameter(s)'`。`password` は暗号化済みの形を渡す指定で、平文は `clear`(既定)。表示は `key-string password 0131…`(暗号化して保存) |
| 存在しない鍵チェーンを `hello-password keychain` で参照 | **コミットは通る**(RPL の未定義参照と違う)→ 受けたハローを全部捨てる= `Last PDU Rejected: … P2P IIH, Authentication Failed`。隣接は `Init` からも消える |
| 鍵に暗号アルゴリズムが無い/有効期間が無い | どちらも**コミットは通るが鍵が使われず**、ハローは `Authentication Failed`。`show key chain` に `Cryptographic-Algorithm -- Not configured`・`Send/Accept lifetime -- Not configured`(`[Valid now]` が出ない)。両方そろえた直後に隣接 Up |
| ハローだけ合わせた状態 | 隣接は Up。XR はバックボーンの LSP を受け入れて経路を持つ(XR に LSP の認証が無い=検査しない)。**RT02 は XR の LSP を捨てる**= バックボーンにエリア 49.0001 の経路が無い・RT02 の隣接表で XR01 がホスト名でなく `0102.5500.0001` のまま(ホスト名は LSP で運ばれるため)。RT01 は既定経路が戻るが行きだけ |
| `lsp-password keychain … level 2` | 全経路が交換される。XR の L2 LSP に `Auth: Algorithm HMAC-MD5, Length: 17` |
| **レベルなしの `lsp-password`**(両レベルに効く) | 認証なしの RT01 は XR の認証つき L1 LSP を受け入れる(IOS は認証を設定していなければ検査しない)。逆に XR は **RT01 が作り直した L1 LSP を `L1 LSP, Authentication Failed` で捨て、古い版を持ち続ける**= その場では何も起きず、RT01 の経路の変化が届かなくなる(寿命が切れると RT01 の経路を全部失う)。RT01 の PSNP も捨てるので LSP の再送が増える。→ 採点は M4-4 と同じく、採点中だけ RT01 に経路を足して XR に届くかで見る |
| 共用 LAN を p2p で載せる | 隣接しない。`Last PDU Rejected: … L2 LAN IIH, LAN IIH on P2P Interface`(M4-1 の表示の逆向き) |
| 共用 LAN(broadcast)・XRd | **XRd でも LAN の隣接・DIS 選出が成立**(IS-IS のマルチキャストを受ける)。`show isis interface` の `LAN ID: RT03.01`・`Priority (Local/DIS): 64/80` |
| 優先度 100 | **その場で DIS を奪う**。RT03 の擬似ノード LSP(RT03.01-00)は寿命 0 で消され、XR01.01-00 が現れる。IOS 側は `DR ID: XR01.01`。レベルなしの `priority` は両レベル、`level 2` 付きは L2 だけ |
| LAN の circuit-type を外す | L1 のハローも出す(L1 は相手がいないので `no DIS elected`)。L2 だけの相手とは問題なく L2 で隣接 |
| `summary-prefix`(レベルなし/`level 2`) | この盤面ではどちらも L2 に要約 1 本(L1 へ要約する対象が無いため差が出ない)。XR に **Null0 の破棄経路**(`type manual summary`)。メトリックは構成要素の最小(20)。構成要素が全部消えると要約も消える。★XR は自分の L2 LSP で **IPv6 の要約を `IPv6-External` と表示**(IOS 側は普通の I2) |
| NET を 1 コミットで入れ替え(システム ID 同じ・エリアだけ変更) | **XR01 の全隣接(RT01 の L1 も、バックボーンの L2・LAN も)が同時に落ちて張り直す**(相手が新旧両方のエリアを持っていても)。`show isis adjacency-log` に全隣接の `d -> i`→`i -> u` が同じ時刻で並ぶ |
| NET を足す → 別のコミットで旧 NET を外す | **隣接は 1 本も落ちない**(隣接ログに変化なし) |
| 相手(RT01)が新エリアだけ | XR の L1 隣接が `u -> d  Area addr/level differ`・`Last PDU Rejected: … Level or Area Addr mismatch`。XR に 2 つ目の NET を足すと戻る(エリアの併合) |
| システム ID の違う NET・4 つ目のエリア | コミット失敗= `System ID must not change: 0102.5500.0001`・`Maximum area address count exceeded: maximum number of area addresses is 3` |
| 採点の材料 | `show configuration commit list N detail` に各コミットの時刻、`show isis adjacency-log [level 1|2] [last n]` に状態変化の時刻。同じ機器の時計なので突き合わせられる |

- 気づき(課題外)= XRd の管理 IF で `Duplicate IP address 10.1.10.11 … sourced by 5254.0093.c03d` が起動直後に 1 回出た(撤収直後の旧ラボの残りの可能性・SSH は正常)。

### 18.6 公式文書との突き合わせ(2026-10-22・Cisco 8000/NCS 5500 の IS-IS コマンド リファレンスと設定ガイド・鍵チェーン管理・IOS XE 17.x の IS-IS セキュリティ・RFC 5304)

| 論点 | 公式 | 実機 | 判定 |
|---|---|---|---|
| `lsp-password`/`hello-password`/`summary-prefix`/`priority` のレベル省略 | 両レベル | 同(要約は L2 で差が出ない) | 一致 |
| `lsp-password` が SNP も認証する | 「all IS-IS LSPs … as well as for all SN PDUs」 | RT01 の PSNP を捨てて再送が増える | 一致 |
| DIS は優先度の高い新参に奪われる・同点は MAC の大きい方 | 記載あり(NCS 5500 のリファレンス) | 奪う | 一致 |
| NET は最大 3・システム ID は全 NET で同じ | 記載あり | コミット時に拒否 | 一致 |
| 要約は破棄経路を入れる・メトリックは構成要素の最小 | 記載あり | 同 | 一致 |
| `key-string [clear\|password]`(既定 clear) | 記載あり | password に平文= コミット失敗 | 一致 |
| 暗号アルゴリズムが無いと MAC の計算・検証が無効 | 記載あり | 認証失敗 | 一致 |
| **有効期間の無い鍵** | 設定ガイドの注記= 「無効とみなし、**設定時に拒否する**」。同じガイドの手順とコマンド リファレンスでは有効期間は任意(既定なし) | **コミットは通る**が鍵は使われない(認証失敗) | **食い違い**(無効という点は一致・「設定時に拒否」が実機と違う)→ ユーザ判断待ち。それまで課題では「有効期間が要る」ことを正解の根拠にしない |
| IOS: プロセスの `authentication` は LSP・CSNP・PSNP、IF の `isis authentication` はハロー | 記載あり | 同 | 一致 |
| HMAC-MD5 の TLV に鍵 ID は無い(機種間で鍵番号を合わせなくてよい) | RFC 5304 | XR と IOS とも key 1 なので未検証 | 補足に留める |
| `show isis adjacency-log` | 記載あり(既定で記録するかは記載なし) | 既定で記録(`log adjacency changes` なし) | 実測で補う |

### 18.7 PoC を受けた課題の確定案

- **M4-5(認証の TS)**= 据え付け側の作業票(鍵チェーン名・鍵番号・鍵・HMAC-MD5・「2026-01-01 から無期限」)を課題文に載せる。
  罠= `key-string password`・アルゴリズム・有効期間・ハローと LSP の 2 つ・レベル(L1 に効かせると RT01 の経路の変化が届かない)。
  採点= L2 隣接 Up/RT02 が XR01 の LSP と RT01 側の経路を持つ/RT01 がサービス網に届く/**採点中だけ RT01 に Loopback を足して XR01 に届く**(`login_probe.py --pre-cli`)。
  ★有効期間の件は 18.6 の食い違いの判断待ち。
- **M4-6(LAN と DIS)**= SVC-LAN を L2 だけ・broadcast・ハロー認証つきで載せ、XR01 を DIS に(RT03 は優先度 80= 表示から自分で見つける)。
  採点= XR01 の Gi0/0/0/3 に RT02・RT03 の L2 隣接(SNPA が MAC)/RT02 の `show clns interface` で `DR ID: XR01.01`/XR01 の LAN に L1 のハローが無い。
- **M4-7(要約)**= IPv4 `10.11.0.0/16`・IPv6 `2001:db8:1011::/48` をバックボーンへ 1 本ずつ。採点= RT02 に /16・/48 があり /24・/64 が無い・RT01 のループバックは個別に残る。
  誤答の判別= `level 1` だけにすると L2 に効かない。
- **M4-8(エリアの付け替え)= 案 A に確定**。RT01 は新旧 2 つの NET(49.0001・49.0010)で据え付けておく(`initial/RT01.cfg.j2` に追加済み)。
  要件= XR01 を 49.0010 へ移し 49.0001 を外す・作業中に XR01 の隣接を 1 本も落とさない。
  採点= XR01 の手動エリアが 49.0010 だけ/RT01 との L1 隣接 Up/**49.0010 を初めて入れたコミットの時刻以降、隣接ログに状態変化が無い**
  (採点機側の小さなスクリプトで commit list と adjacency-log を突き合わせる= 実装で作る)。1 コミットの入れ替えは全隣接が張り直されて落ちる。
- 再配送は見送り(M4-7 を軽く保つ。M7 以降の盤面で必要になれば拾う)。

### 18.8 実装の結果(2026-10-22)

- 鍵の有効期間の食い違い(18.6)= **ユーザ判断(2026-10-22)で実機の挙動のまま出題し、読み物と模範解に注記**(公式は「設定時に拒否」・XRd 26.1.1 はコミットが通り鍵が使われない)。
- 成果物= `problems/XRT-05`(課題ごとの確認 `grading.m4t5〜8.yml`・最終 `grading.yml` 各 25 点・`learn.yml`・課題文 日英)、
  読み物 `courses/xr/{en,ja}/42-m4-isis-deeper.md`(認証・LAN と DIS・要約・エリア アドレス・コマンド名の 5 節。日英で見出しと段落の数を機械照合)・
  実践 `43-m4-practice-2.md`(`course.sh` が課題文から切り出す)。模範解= `poc/xr/solve_xrt05.sh`(誤答の再現つき)。
- 採点に `login_probe.py xr-adj-since <NODE> '<regex>'`= 差分が regex に一致する最新のコミットを探し、その時刻以降の
  `show isis adjacency-log` の状態変化を数える(0 件で `== ADJ STABLE`)。★`show configuration commit list <n>` の n の上限は
  その時点のコミット数(超えると入力エラー)→ 件数なしで全件を取る。
- 課題文の M4-5 は作業指示の表(対象= 「レベル 2 のすべての IS-IS パケット」・キー チェーン・キー・HMAC-MD5・有効期間)で渡す
  (ハローと LSP の 2 か所に分かれることは自分で見つける)。M4-6 の「再起動しても DIS を保つ」で優先度 > 80 を要求(同点は MAC で決まる)。
  M4-8 は「隣接がダウンしたら 49.0001 だけに戻してやり直す」を課題文に明記(採点は最新の追加コミットから見る)。
- 実機 E2E(記録 `poc/xr/expM4b-*.log`)= 白紙 0(最終・課題ごと 4 本とも)→ 模範解 100。誤答= LSP 認証のレベルなし 75・
  要約を level 1 だけ 0・NET の 1 コミット入れ替え 60(戻してやり直すと 100)。`learn.yml` の模範解を逐語で流しても 100。
  `lab.sh reset` で白紙 0 に戻ることも確認。★XR の `show isis interface brief` は自分が DIS の LAN で隣接数に `*`(優先度を 64 に下げると消える)。
- ワークスペースの API(`/api/learn`)で課題文の切り出し・ヒント数・読み物の節へのリンクを確認。
- ★2026-10-23 採点の不具合を修正(ユーザの解答で判明)= M4-6 の優先度を `show isis interface brief` の Prio 列で見ていたが、
  この列は**レベルを付けない `priority` だけ**を表示し、`priority 127 level 2` は `-` のまま(DIS にはなっている)→ 正しい解答が落ちた。
  詳細表示 `show isis interface <IF>` の `Circuit Type`・`Media Type`・`Priority (Local/DIS)`・AF ごとの `Adjacency Formation: Running` で見るよう変更
  (`grading.m4t6.yml`・`grading.yml`)。E2E はレベルなしの `priority 100` しか試していなかった= 別解(レベル付き)も E2E に入れること。

## 19. M7 高可用性(2026-10-22 方針・未着手)

**範囲= SPCOR 2.8(a NSF/グレースフル リスタート・b NSR・c BFD・d リンク集約)。機種は XRv9000**(§14.2= XRd は BFD のセッションを作らない)。
版は **26.1.1**(起動 約 3 分。24.3.1 は約 8 分)を `node_images` で指定する見込み。**IGP は IS-IS**(§5 の「IS-IS の深め方」②)。
ラボは **`XRT-06`**(XRT-05 は M4 追補)。

### 19.1 盤面(案)

| リンク | XR01(XRv9000) | 相手 | 役割 |
|---|---|---|---|
| BUNDLE | Gi0/0/0/0・Gi0/0/0/1 → Bundle-Ether | RT01 Et0/0・Et0/1 → Port-channel | リンク集約(LACP) |
| PRIMARY | Gi0/0/0/2 | SW01(IOL-L2)経由で RT02 Et0/0 | 間にスイッチ= **XR 側のポートは up のまま先が死ぬ**状況を作れる |
| BACKUP | — | RT01 Et0/2 ─ RT02 Et0/2(メトリック大) | 予備経路 |

- IS-IS はレベル 2 だけ・wide。XR01 と RT02 はループバック間で iBGP(BGP のグレースフル リスタートとオーバーロード ビットの題材)。

### 19.2 課題(案)

| 課題 | 中身 | SPCOR と IS-IS の論点 |
|---|---|---|
| M7-1 | RT01 との 2 本を LACP で 1 本の束にする。1 本だけでは使わない(最低本数) | 2.8.d・束の上の IS-IS |
| M7-2 | (TS)束の上で IS-IS の隣接が上がらない、など。候補= XR の MTU は L2 ヘッダ込みで数える(`mtu 1500` は L3 で 1486)× IS-IS のハローのパディング・LACP のモードの食い違い | 2.8.d・ハローのパディングで MTU の食い違いを見つける IS-IS の仕組み |
| M7-3 | RT02 への主経路が、ポートは up のまま死んでも 1 秒以内に予備へ切り替わる | 2.8.c・IS-IS に BFD・SPF/LSP 生成のタイマー |
| M7-4 | XR01 のルーティング プロセスを再起動しても、隣接と転送を落とさない | 2.8.a・IS-IS の NSF(IETF)・BGP のグレースフル リスタート・XR のプロセス構造(M0 の復習) |
| M7-5 | (候補)メンテナンス前に XR01 を通過経路から外す(XR01 宛ては残す)・起動直後は BGP が揃うまで通過させない | オーバーロード ビット(手動と on-startup wait-for-bgp)。起動時の挙動を採点するには再起動が要るので、課題にするかは PoC 後 |

- **NSR(2.8.b)** は RP が 1 枚の XRv9000 では本来の動きをしない見込み= まず読み物で扱い、ラボ化は PoC の結果で決める。
- 採点= M7-3 は採点中だけ SW01 の RT02 側ポートを止めて、RT01 からの連続 ping の欠落で切り替え時間を測る。
  M7-4 は採点中だけ XR01 で `process restart`。どちらも `login_probe.py` の `--pre-cli`/`--post-cli` の延長(XR に対して打つ口が要る)。

### 19.3 PoC で確かめること(XRv9000 26.1.1+IOL 17.15)

1. 26.1.1 の必要 vCPU・メモリ(24.3.1 は 7 vCPU・20GB)と起動時間。日次パックのラボと同居できるか。
2. Bundle-Ether と IOL の Port-channel(LACP)の相互接続・最低本数・食い違い(モード・MTU)の症状。
3. BFD の下限(仮想機で 1 秒以内が安定するか)・IS-IS に張る形・束の上の BFD(メンバごとか束全体か)。
4. `process restart isis`/`bgp` でグレースフル リスタートが効くか(IOL の隣接の Uptime がリセットされないか・ping の欠落)。IOL の IETF ヘルパーの既定。
5. RP 1 枚での NSR の設定と表示。
6. オーバーロード ビットの手動設定の見え方・on-startup の採点の可否。

### 19.4 その先の見通し(メモ)

- M8 以降も転送が要るので XRv9000 が中心。ただし XRd は公式に vRR・PCE 向けの位置づけ(§14.1)なので、M9 の VPNv4 ルート リフレクタ・
  M10 の PCE のように**転送しない役に XRd を足せば**、XRv9000 1 台+XRd 数台で「XR 複数台」の盤面が作れる(同時 2 台の上限を回避)。

### 19.5 公式文書・RFC での裏どり(2026-10-23・PoC の前に。xrdocs.io は取得していない)

参照= NCS 5500 Routing CG/CR 26.x(IS-IS・BFD)・BGP CG/CR 26.x(NCS 5500・Cisco 8000)・ASR 9000 Routing CR(BFD)・Routing CG 7.8.x/7.11.x・
Interface CR/CG(Link Bundling)・System Management CR(process)・XRv9000 リリースノート 24.3.1/25.1.1/26.1.1 と設置ガイド・
技術ノート 116350(XR と IOS の MTU)/119399(IS-IS hello padding)/211432(SPF 既定の変更)・IOS XE 17.x(BFD・IEEE 802.3ad・NSF awareness・
SR の routing-default-optimize)・RFC 4724/8706/3787/5880/5881/7130。

| 論点 | 公式・RFC の記述(要旨) | PoC で見ること |
|---|---|---|
| XRv9000 の資源 | 24.3.1= 最小 2 コア・12GB(10G IF で 19GB 推奨)。26.1.1= ESXi 表だけで最小 4 コア・24GB(KVM 表なし) | 26.1.1 を CML の既定(7 vCPU/20GB)で動かした実使用 |
| 束 | `bundle id N mode {active\|passive\|on}`・**mode を省くと on**(LACP なし)。最低本数を下回ると束は down。XRv9000 の LACP 周期の下限 200 ms。片側 on・片側 LACP の挙動は XR の文書に無い | on×active・passive×passive の症状 |
| MTU | XR の `mtu` は L2 ヘッダ込み(Ethernet 既定 1514・IP は 1500)。束とメンバの MTU の関係は記載なし | `mtu 1500` の束で IS-IS の隣接 |
| hello padding | XR・IOS とも既定で有効(IOS は MTU いっぱいまで埋める)。MTU が違うと「隣接が上がらない」(状態名の記述は無い)。padding を切るだけでは足りない | 上がらない側と状態 |
| BFD | IS-IS の `bfd minimum-interval` 既定 150 ms・multiplier 3。ソフトウェア動作は 150 ms 以上を推奨(最小 3×50 ms)。XRv9000 固有の下限は記載なし。BLB は XRv9000 の対応表にある(6.1.2〜)・BoB は無い。ASR9K/NCS では BLB に `bfd multipath include location` が無いとセッションを作らない。`bfd bundle coexistence bob-blb` の要否は XRv9000 の記載なし | 下限・束の上の BFD・multipath の要否 |
| 検出時間 | RFC 5880= 相手の Detect Mult × 合意した間隔(方向ごとに違い得る)。単一ホップ UDP 3784・TTL 255。micro-BFD(RFC 7130)はメンバごと・UDP 6784 | — |
| SPF の既定 | XR= spf-interval・lsp-gen-interval とも 50/200/5000 ms。**IOS XE も routing-default-optimize で 50/200/5000 ms**(旧 5500/5500/10000。変更版は文書で 16.5.1 と 17.3.2 に割れる) | IOL 17.15 の既定 |
| IS-IS NSF | `nsf {cisco\|ietf}` 既定無効。きっかけ= RP 切替・**管理者の process restart**・アップグレード。ietf は相手に RFC 5306(現 8706)のヘルパーが要る・相手が無ければ冷えた起動。`show isis protocol` の「Process startup mode」で判定。`process restart` は文書上 Admin EXEC | XR EXEC から打てるか・相手の隣接が切れないか |
| IS-IS NSR | **dual RP 専用**。process restart を守るのは NSF、RP 切替を守るのは NSR。XRv9000 は Active/Standby の冗長を持たない | 設定と表示だけ(読み物で扱う) |
| BGP GR | `bgp graceful-restart` 既定無効・OPEN で能力を交換(両側が広告して成立)・入れた後はセッションのやり直しが要る。restart 120 s・stalepath 360 s・purge 600 s。BGP の NSR は standby RP への SSO で、process restart ではネイバーが落ちる。**BGP NSR の既定が文書で食い違う**(NCS 5500 CG「既定で有効」・8000 CR「無効」) | `show bgp process` の NSR 行 |
| IOS XE のヘルパー | IGP(IS-IS)の NSF awareness は対応イメージで自動。**BGP は `bgp graceful-restart` を入れないと能力を広告しない** | IOL・Cat8000v で |
| オーバーロード | `set-overload-bit [on-startup {秒\|wait-for-bgp}] [level] [advertise …]`。CR は on-startup を「再起動の後」、CG は「プロセスの起動と再起動」と書き、どちらも **NSF の再起動・切替では使わない**。wait-for-bgp の上限・収束の定義は XR の文書に無い(10 分は旧 IOS の技術ノート)。OL の装置は通過に使われないが、直結のプレフィックスには届く(RFC 3787)。`show isis database` の ATT/P/OL 列 | NSF なしの process restart・clear isis process で OL が立つか |
| プロセス | 各プロセスは保護されたアドレス空間で動き、他に影響せず個別に再起動できる(ASR 9000 Overview の HA 章) | — |

- IOL 17.15 ルータ(iol-xe)の LACP は**使えない**(PoC 1 回目で実測・`poc/xr/ha-a-iol-lacp.log`)。束の相手役は Cat8000v 17.15 に替えた。

### 19.6 PoC の結果(2026-10-23・盤面 `problems/_POC-XRHA`= XRv9000 26.1.1+Cat8000v 17.15+IOL 17.15。手順 `poc/xr/ha_poc.sh`・記録 `poc/xr/ha-*.log`)

**盤面の変更**= RT01(束の相手)を **Cat8000v** に替えた。IOL ルータの LACP は壊れている(day0 の `channel-group` は無言で捨てられ、
手で入れると「Invalid channel group number」を返しつつ設定には残り、`show lacp internal` は同じ行を出し続ける。`poc/xr/ha-a-iol-lacp.log`)。
Cat8000v はデータ IF が 3 本(Gi1〜3)= 束 2 本+予備 1 本でちょうど。**Cat8000v には `mode on` が無い**(active/passive だけ)・
**束のモードはその場で替えられない**(`no channel-group` してから付け直す)。

1. **資源**= 構築 約 9〜10 分(lab.sh provision 全体)。XRv9000 26.1.1 は CML の既定(7 vCPU/20GB)で起動・XR から見えるメモリ 6GB(空き 3.2GB)。
   この盤面を足した CML の使用量= 約 24GB(XRT-05 だけの時 4.7GB → 28.4GB/47GB)。割当 vCPU 8(XR 7+Cat8000v 1)。日次パックのラボと同居できる。
2. **束**= active⇔active で上がる(`show bundle` Up 2/0/2・RT01 `Po1(RU)`)。passive×active も上がる。**passive⇔passive は最初から組むと上がらない**
   (XR は Down・メンバ Configured、RT01 は susp)。**XR を `mode on`・相手 LACP**= XR は束 Up(LACP Not operational・メンバ Active)だが、
   RT01 はメンバを susp のまま → **XR からは正常に見えて ping 0%**(片側だけ上がる TS の題材)。
   **CML では相手のポートを shutdown しても XR 側のキャリアは落ちない**= XR は LACP の失効で抜く。既定(slow・30 s 周期)で **72 秒**、
   XR のメンバに `lacp period short` を入れると相手に速い送信を求め(XR の Actor に F)、**6 秒以内**(測り方の刻み 5 秒)。RT01 の `lacp rate fast` も受け付ける。
   `bundle minimum-active links 2` で 1 本抜けると束ごと Down(残り 1 本は Standby「due to minimum-active link configuration」)。
3. **束の上の IS-IS と MTU**= 既定で隣接 Up(XR の CLNS MTU 1497)。**XR の束に `mtu 1500`**(IPv4 1486)→ XR は RT01 のハローを
   「Last PDU Rejected … 1496 octets, P2P IIH, **PDU larger than our MTU**」で捨て、`show isis interface` は「MTU: 1483 (**MTU is too small: L2 lsp-mtu is 1492**)」。
   XR は Holdtime expired で落とし、RT01 は XR を **Init**(neighbor forgot us)。**逆に `mtu 9000`** → XR のハロー(8983 まで埋める)を RT01 が捨て、
   XR 側が Init・上がっては「3-way state down」で落ちる。どちらの向きも症状がはっきり出る(M7-2 の候補に使える)。
   Cat8000v の起動ログ「%CLNS-6-DFT_OPT: Protocol timers for fast convergence are Enabled」= IOS XE の既定は 50/200/5000 ms(§19.5 と一致)。
4. **黙った故障の作り方**= CML のリンク条件 `loss 100`(`poc/xr/cml_link.py <ID> RT02 SW01 loss 100|clear`)。両端のポートは up/up のまま
   パケットだけ消える。採点機から CML の API で入れて戻せる(相手役の設定を触らない)。測り方= RT01 から `ping … repeat 20000 timeout 1`
   (`poc/xr/pingloss.py`)= 落ちた ping は 1 秒待つので欠落数 ≒ 止まった秒数。
5. **BFD**= **BFD なし**で欠落 **22 秒**(Holdtime 30 秒の残りで落ちる)。**BFD 100 ms×3**(XR= IS-IS の IF に `bfd fast-detect ipv4`・
   RT02= IF に `bfd interval 100 min_rx 100 multiplier 3`+`isis bfd`)で欠落 **1 秒**(= 1 秒以内)。XR は単一ホップを **echo 方式**で張る
   (`show bfd session`= Echo 300ms(100ms*3)・Async 6s(2s*3))。落ちた理由は「Echo function failed」→ IS-IS は「Down, BFD session DOWN」。
   落ちた後は**ダンプニング**(「entered Dampened state (initial: 2000 ms …)」・`DOWN DAMP`)。`bfd minimum-interval` は 50・15・3 もコミットは通る
   (実際の間隔は相手の 100 ms で決まる)。IOS XE の既定は `spf-interval 5 50 200` 等(routing-default-optimize)= 相手役を詰める必要はない。
6. **BFD と隣接(RFC 6213)**= 相手がハローに BFD-enabled TLV を載せる(`isis bfd`)と XR は「**BFD Required**」になり、BFD が上がるまで
   隣接を **Init** に留める(`show isis adjacency` の BFD 列 Init・detail に「Topology (not running): [IPv4 Unicast (BFD is down)]」
   「Neighbor Not Useable (BFD Required)」)。相手が TLV を出さなければ「BFD Configured, but Not Required」で BFD が DOWN でも Up のまま。
   **相手が `isis bfd` だけで IF の `bfd interval` が無い** → XR は Init で固まり、相手は XR を Down(TS の題材)。
7. **束の上の BFD**= **Cat8000v の Port-channel は BFD を持たない**(`bfd interval` が Invalid)→ BLB はこの盤面では成立しない。
   XR は「No resources for session … Bundle-Ether1」を出し、`bfd multipath include location 0/0/CPU0` を入れると「Lack of resources condition has cleared」
   (XRv9000 でも ASR9K/NCS と同じく multipath が要る)。相手が TLV を出していたため束の上の隣接が Init に落ちた(片付け済み)。
   BoB(メンバごと)は XR が受け付け、メンバは「Waiting indefinitely for peer to establish session」で束は Up のまま。
   → **M7 の BFD は主経路(束でない IF)で扱い、束の上の BFD は読み物で説明する**。
8. **IS-IS のグレースフル リスタート**= `process restart isis` は **XR EXEC から打てる**(文書の表記は Admin EXEC)・確認なしで即再起動
   (「%OS-SYSMGR-4-PROC_RESTART_NAME : User … requested a restart of process isis」)。**NSF なし**= 相手(Cat8000v)は
   「Down, **neighbor forgot us**」→ 2 秒後に Up(ping の欠落 2)。**`nsf ietf`**= XR「IETF NSF controlled start beginning」→
   隣接は「Up, NSF Restart」→ 約 10 秒で completed。**相手のログに ADJCHANGE が出ず、ping の欠落 0**。IOS XE のヘルパーは設定なしで働く
   (`show isis nsf` は自分が再起動する側として「NSF is DISABLED」と出るだけ)。XR 自身の隣接表の Changed は再起動で 0 に戻る
   → **採点は相手側のログ(再起動以降に ADJCHANGE が無い)と ping の欠落で見る**。
9. **NSR(RP 1 枚)**= `router isis … nsr` はコミットが通り「ISIS NSR is configured」だが `show isis nsr status` は **Not Ready**(standby なし)。
   NSR と NSF を両方入れた状態の process restart も IETF NSF で処理される(欠落 0)= 公式「process restart を守るのは NSF」と一致。
   **BGP の NSR は既定で有効**(設定前から「Non-stop routing is enabled」・NCS 5500 CG と一致・8000 CR の「無効」とは食い違う)・
   `show bgp nsr` は「NSR state not ready: Wait for standby ready msg」。→ NSR は読み物で扱い、ラボの課題にしない。
10. **XR の出力フィルタ**= `| include -i …` は使えない(「% Can't handle special action '|'」)。大文字小文字は正規表現で吸収する。
11. **BGP のグレースフル リスタート**(XR が広告する経路 10.30.0.0/16 を RT02 で見る)= 両側に `bgp graceful-restart` → XR の
    `process restart bgp` の 3 秒後、RT02 は **`S>i 10.30.0.0/16`(Stale)で経路を保持**・セッションが戻ると S が外れる(約 6 秒)。
    **RT02 の GR を外す**と同じ時点で「% Subnet not in table」(5 秒後に戻る)。RT02 のログ「Down **NSF peer closed the session**」= ヘルパーとして扱った印。
    能力は OPEN で交換するので、入れた後はセッションのやり直しが要る(XR 側だけ入れた時点では RT02 に「Graceful-Restart is disabled」・XR に「GR Awareness: received」)。
    IOL 17.15 の `show running-config all` は restart-time 120・stalepath-time 360 だが、`show ip bgp neighbors` は「restart-time 900 seconds, stalepath-time 1800 seconds」と出る(表示の違い・影響なし)。
    → **採点は XR の process restart の直後 1〜6 秒に RT02 で経路が消えないこと**(数回取って 1 回でも消えたら不合格)。
12. **オーバーロード ビット(手動)**= `set-overload-bit` → XR の LSP が `0/0/1`(ATT/P/OL)。RT01 の 10.20.0.0/16 は予備(metric 1010・Gi3)へ、
    **XR01 のループバック宛ては束のまま(metric 10)**= 通過だけ外れて XR 自身には届く(RFC 3787・公式と一致)。
13. **オーバーロード ビットの起動時**(3〜13 秒刻みで LSP の ATT/P/OL と `show isis protocol` の「Most recent startup mode」「Overload Bit」を見た。`poc/xr/ha-f2.log`)=
    | 条件 | OL |
    |---|---|
    | `nsf ietf`・OL の設定なし → process restart | 立たない(IETF NSF Restart) |
    | NSF なし・OL の設定なし → process restart | **約 10 秒だけ立つ**(Cold Restart。冷えた起動で LSPDB がそろうまで= RFC 8706 の起動時の動きと整合) |
    | NSF なし+`on-startup 60` → process restart | **約 60 秒立つ**(+49 s で set・+62 s で clear)= **process restart でも効く**(CG の「プロセスの起動と再起動」と一致。CR の「再起動の後」より広い) |
    | NSF なし+`on-startup wait-for-bgp` → process restart | 約 10 秒で消える(BGP は再起動していない= 既に収束済み) |
    | NSF なし+`on-startup 60` → `clear isis process` | 立たない |
    | `nsf ietf`+`on-startup 60` → process restart | `show isis protocol` は「configured, **set**」が約 60 秒続くが、**LSP は作り直されず OL は広告されない**(公式「NSF の再起動では使わない」と実質一致・表示だけ食い違う) |
    → M7-4 で `nsf ietf` を入れると、**on-startup は process restart では採点できない**(本物の再起動= reload は数分かかる)。
14. **TS の連鎖**(`poc/xr/ha-g.log`)= メンバに `bundle id 1`(モード省略)→ 設定上は **`bundle id 1 mode on`** と表示・束 Up・LACP Not operational・
    ping 0%・RT01 は susp。モードを active に直すと ping は通るが、束に `mtu 1500` が残っていれば IS-IS は RT01 で Init・XR は「PDU larger than our MTU」。
    MTU を直して Up。**1 段直すと次の症状が見える 2 段の TS** として成立。

### 19.7 PoC を受けた課題の確定案(2026-10-23)

盤面= §19.1 のまま、**RT01 だけ Cat8000v**(XR01= XRv9000 26.1.1・RT02= IOL・SW01= 非管理スイッチ)。IGP= IS-IS L2・wide。XR01⇔RT02 は iBGP。

| 課題 | 中身(挙動で指定) | 採点(挙動) |
|---|---|---|
| M7-1(TS) | 「RT01 との束は Up と表示されるのに RT01 と通信できない。IS-IS も上がらない」= 仕込み 2 段(メンバの `bundle id 1` がモード省略= 静的/束の `mtu 1500`)。RT01 側は変えない | LACP Operational・RT01 で Po1(RU)・束の上の隣接 Up・RT01→XR01 の ping |
| M7-2 | 束の運用要件= 2 本そろわないと使わない・メンバの故障(相手のポートが落ちてもこちらのポートは up のまま)を **5 秒以内**に検知して束から外す | 採点中だけ RT01 Gi2 を shutdown → 8 秒後に XR の束が Down・IS-IS は予備へ → 戻す(`--pre-cli/--post-cli` を Cat8000v に) |
| M7-3 | RT02 への主経路が「ポートは up のまま」死んでも **1 秒以内**に予備へ(RT02 は BFD 100 ms×3 と `isis bfd` を据え付け) | 採点中だけ CML のリンク条件 loss 100(RT02-SW01)→ RT01 の連続 ping の欠落 ≤ 2 → 戻す |
| M7-4 | XR01 のルーティング プロセス(IS-IS・BGP)を再起動しても、隣接と転送を落とさない(RT02 は `bgp graceful-restart` を据え付け。XR 側は入れた後にセッションのやり直しが要る= 気づかせる) | 採点中だけ `process restart isis` → RT01 に ADJCHANGE が出ない・ping の欠落 0/`process restart bgp` → 1〜6 秒の間 RT02 で XR の経路が消えない |
| M7-5 | メンテナンス前に XR01 を**通過経路から外す**(XR01 宛て・管理は残す。IF は止めない) | RT01→RT02 が予備経由・RT01→XR01 の Lo0 は束経由・束と主経路の隣接は Up のまま(メトリックで逃がす別解も挙動では通る→ レビューで OL を示す) |

- **読み物で扱う(ラボにしない)**= NSR(RP 1 枚では Not Ready)・束の上の BFD(BoB/BLB と `bfd multipath include location`)・
  on-startup(NSF と同時には process restart で効かない・冷えた起動では効く)・BFD の echo 方式とダンプニング・RFC 6213 の「BFD Required」で隣接が Init に留まる仕組み。
- 実装で足すもの= ①採点から CML のリンク条件を入れて戻す(`cml_link.py` を `exec: local` から)②XR に対する `--pre-cli`(process restart)③採点用の ping の欠落計測(`pingloss.py` を login_probe に取り込む)④Cat8000v を学習用ラボで使う配線(初期設定テンプレートは IOS XE)。
- 構築 約 10 分・CML 使用 約 24GB(同時 2 台の XRv9000 上限に対して 1 台)。

### 19.8 実装の結果(2026-10-23)

- 成果物= `problems/XRT-06`(課題ごとの確認 `grading.m7t1〜5.yml`・最終 `grading.yml`= M7-1 22・M7-2 18・M7-3 20・M7-4 20・M7-5 20・`learn.yml`・課題文 日英)、
  読み物 `courses/xr/{en,ja}/70-m7-high-availability.md`(束・BFD・オーバーロード ビット・損失なく再起動する・コマンド名の 5 節。日英で 75 ブロック・見出し 19 を照合)・
  実践 `71-m7-practice.md`(`course.sh` が課題文から切り出す)・Drive 同期済み。模範解= `poc/xr/solve_xrt06.sh`(誤答・別解つき)・E2E= `poc/xr/e2e_xrt06.sh`。
- **§19.7 から変えた点**= 課題の並びを M7-1 束の TS → M7-2 束の要件 → **M7-3 オーバーロード ビットの消し忘れの TS(+ on-startup wait-for-bgp)** → M7-4 BFD → M7-5 NSF/GR にした。
  「通過だけ外す」を最後の課題にすると、最終状態で OL が立ち、M7-3/M7-4 の切り替え試験が XR01 を通らずに素通りで合格するため。
  消し忘れ(素の `set-overload-bit`)を初期設定に仕込み、要件は「通過を戻しつつ、起動直後は BGP がそろうまで通過させない」= 同じコマンドの形の置き換え。
  起動時の挙動は NSF(M7-5)と両立しない(§19.6-13)ので、`show isis protocol` の表示で見る。
- 採点で故障を起こす= `login_probe.py` に方式 3 つ(`ping-loss`= 途中で CML のリンク条件 loss 100・最長の欠落・`== FAULT DURING PING`/
  `log-delta`= 前後の `show logging` の新しい行/`watch`= 先にログインしてから引き金を引き、直後に N 回取る)と `--fail-link A:B`・`--post-settle N`。
  経路が XR01 経由であることも ping-loss の出力(`show ip route`)で見る(OL が残っていると素通りになる)。故障を起こす Check は 1〜2 分(学習モードの上限 240 秒の内)・最終は約 4 分。
- 実機 E2E(記録 `poc/xr/expM7-*.log`)= 白紙 0(最終・課題ごと 5 本とも)→ 模範解 100・learn.yml の模範解を逐語で流しても 5 本とも 1 回目で 100・
  `lab.sh reset` 後に白紙 0。誤答= 最低本数だけ 30・LACP の周期だけ 0・OL を外すだけ 70・on-startup 60 は 70・BFD なし(欠落 22)0・GR を入れてセッションをやり直さない 40。
  別解= XR を passive・BFD の間隔は既定(150 ms × 3 で欠落 1)・`nsf cisco`(「Cisco NSF controlled start」「Restored during NSF」)も 100。
- **実装で分かったこと**:
  1. 白紙でも M7-1 の ping が通った= 束が壊れていても XR01 のアドレスには予備経由(RT02 → 主経路)で届く(OL は XR01 自身のプレフィックスを妨げない)。
     → RT01 からは `source Port-channel1`、XR01 からは `ping … size 1500 df-bit`(XR の DF は `df-bit` か `donotfrag`)で束に限った。
  2. **XR01 側でハローのパディングを切っても隣接は上がらない**= XR01 が拒否しているのは RT01 がパディングした RT01 のハロー(公式の技術ノート
     「パディングを切るだけでは隣接は上がらない」と一致)。読み物と模範解の説明を実測に合わせて直した。
  3. `show isis protocol` は「Overload Bit Level-2: configured, clear」と「on startup until BGP converges」の間に「interarea prefixes suppressed, …」の行を挟む
     (`include` で絞ると見えない)= 採点の正規表現は間の行を許す。
  4. XR のセッションのリセットは `clear bgp 10.255.0.12`(`clear bgp ipv4 unicast <ネイバー>` は soft/long-lived-stale を求めて不完全)。`… graceful` は GR を伴うハード リセット。
     GR を入れてリセットしないと 1 回目の Check は落ちるが、Check 自身の BGP の再起動で張り直されるので 2 回目は通る(模範解に書いた)。
  5. **XR の rollback は `set-overload-bit` → `set-overload-bit on-startup wait-for-bgp` の置き換えを戻さない**(26.1.1。巻き戻しの差分にその行が出ない)。
     さらに巻き戻しでは BGP の機能の交換がセッションに残る。→ `xr_reset.py` に problem.yml の `xr_reset_exec`(戻した後にそのノードで流す CLI の行)を足し、
     XRT-06 は `set-overload-bit` を入れ直して `clear bgp 10.255.0.12`。
  6. RT01 に `lacp min-bundle 2` を入れると、1 本止めた時に RT01 が残りのメンバも止め、XR の最低本数の採点が素通りになる見込み= 入れない(テンプレートから外した)。
  7. BFD を入れた主経路でも、`nsf ietf` の IS-IS の再起動で RT02 の隣接は落ちない(BFD のセッションは保たれる)。

### 19.8 「やってみる」の手順での測り直し(2026-10-24・XRT-06。解く側と同じ起こし方= CML のリンク条件・process restart・RT 側は ping と show だけ)

ユーザ要望(設定をなぞるだけで実感が無い)で M7 の読み物に `:::try` を 6 つ足し、ワークスペースの課題カードの小窓にも出した。
答え合わせの値はこの手順で測り直した(XR01 は M7 を解き終えた状態から一時的に外して測り、最後に running-config の全文が測る前と一致することを確認)。
記録= 作業場所の e1〜e6 のログ(リポには置いていない)。

| 囲み | 起こし方 | 結果 |
|---|---|---|
| 1.2 束 | CML のリンク条件 loss 100 を XR01 Gi0/0/0/0–RT01 Gi1 に | `lacp period short`= 5 秒以内に抜け、最小 2 本で束ごと Down(メンバは Standby→Configured)。slow= **68 秒**(PoC は RT01 のポート断で 72 秒) |
| 2.2 BFD | loss 100 を SW01–RT02 に・RT01 から `ping 10.20.0.1 source Loopback1 repeat 40000 timeout 1` | BFD あり(250 ms×3)= 欠落 1・`Echo function failed`。BFD なし= **28 秒**(PoC は 22 秒= 保持時間 30 秒のどこで落ちたかで変わる) |
| 3.1 OL | 素の `set-overload-bit` | RT01 の 10.20.0.0/16 は Gi3・メトリック 1010、traceroute は 1 ホップ(10.0.12.12)、XR01 の Lo0 へは届く |
| 3.2 起動時 | `on-startup wait-for-bgp`・NSF なしで `process restart isis` | RT01 の `show isis database XR01.00-00` の OL 列= 約 5 秒後に 1、13 秒後までに 0(XR01 の `Cold controlled start completed` は +10 秒) |
| 4.2 NSF | RT01 から Lo0→RT02 Lo0 の ping を流しつつ `process restart isis` | NSF なし= 欠落 1(PoC は 2)・RT01 に `neighbor forgot us`→2 秒後 Up。`nsf cisco`= 欠落 0・RT01 に変化なし |
| 4.3 BGP GR | `process restart bgp`・RT02 で `show ip bgp \| include 10.30.0.0` | GR あり= `S>i` が約 11 秒(PoC は約 6 秒)。XR01 の GR を外して張り直し= 行が約 5 秒消える |

- 中断の事故: 測定の途中で会話の画面が止まり、裏で前の処理が 3.1・3.2 を進めていた(同じ XR01 に 2 つの作業が同時にコミット)。以後は
  コミットにコメント「try-it measurement (Claude)」を付け、`show configuration commit list detail` で他の作業の有無を見ながら進めた。

## 20. M8 MPLS LDP(2026-10-24 完了= 課題の確定案 §20.7・実装の結果 §20.9)

**範囲= SPCOR 3.1(a LDP 同期・b セッション保護・c LDP ネイバー・e MPLS OAM)と 1.5.d(LDP の認証とラベル割り当ての絞り込み)**。
3.1.d Unified MPLS(BGP ラベル付きユニキャストで IGP の領域をまたぐ)は盤面に 2 つめの IGP 領域が要るので **M8 追補**に分ける(§20.6)。
IS-IS の論点= **LDP と IS-IS の同期**(§5 の「IS-IS の深め方」②)。ラボは **`XRT-07`**。
機種= **XRd 26.1.1**(PoC で XRv9000 と比べて差なし= §20.6。当初は「MPLS の転送が要るので XRv9000」と見込んでいた)。
2026-10-24 ユーザが XRT-06 を全通過 → PoC の資源を空けるため撤収(ユーザ了承)。

### 20.1 盤面(案)= 四角形。XR01 は PE、コアは BGP を動かさない

| リンク | 端 | 相手 | IS-IS メトリック | 役割 |
|---|---|---|---|---|
| PRIMARY | XR01 Gi0/0/0/0 | RT01 Et0/0 | 10 | 主経路 |
| CORE-A | RT01 Et0/1 | RT02 Et0/0 | 10 | 主経路 |
| BACKUP | XR01 Gi0/0/0/1 | RT03 Et0/0 | 100 | 予備経路 |
| CORE-B | RT03 Et0/1 | RT02 Et0/1 | 100 | 予備経路 |

- XR01(XRv9000)と RT02(IOL)が PE= ループバック間で iBGP(AS 65000)。お客さまの経路(XR01 Lo100 10.30/16・RT02 Lo100 10.20/16)は BGP だけで運ぶ。
  **RT01・RT03 は BGP を動かさない**= ラベルで運ばないとお客さまの通信は P で捨てられる(MPLS が要る理由がそのまま見える)。
- **XR01 を P でなく PE にした理由**= 同期の効き目が XR 側に出るのは、XR が「ラベルが無いと次のルータが捨てる」位置にいる時だけ。
  XR01 を P にして両隣が PE だと、XR の先のリンクで LDP が落ちても XR はラベルを外して隣の PE(出口)へ渡すだけで通ってしまい、XR の同期は試験に出ない。
  XR01 が入口の PE なら、XR01–RT01 の LDP が落ちた時に XR01 はラベルなしで RT01(BGP なし)へ投げる= 捨てられる → XR の同期が要る。逆向き(RT02→XR01)は
  RT01 が出口の XR01 へラベルなしで渡すだけなので通る。
- セッション保護= XR01–RT01 のリンクが落ちても、XR01→RT03→RT02→RT01 の道で targeted ハローを交わしてセッションとラベルを保つ。
- 筋書き(案)= 「IOS のルータは社内の標準どおりに組んである。XR01 は古い PE と入れ替わった新顔で、MPLS のコアにまだ入っていない」。
  IOS 側(LDP・同期・targeted の受け入れ・RT03 のパスワード)は据え付け、学ぶ側は XR01 を標準に合わせる。

### 20.2 課題(案・PoC で確定)

| 課題 | 中身(挙動で指定) | SPCOR |
|---|---|---|
| M8-1(構築+TS) | お客さまの通信がコアを通るようにする(コアに BGP を入れない)。LDP の ID は Lo0 のアドレス。仕込み= XR01 の既定の LDP ID が IS-IS に載らないループバックになり、ハローは見えるのにセッションが上がらない(制約= そのループバックを IS-IS に載せない・全体の router-id は変えない) | 3.1.c |
| M8-2 | LDP の守り= RT03 はパスワードの無いセッションを受けない(値は課題文で渡す)・XR01 はホスト経路(/32)にだけラベルを割り当てる | 1.5.d |
| M8-3 | コアのリンクで IS-IS は上がっているのに LDP が上がっていない間は、XR01 はそのリンクで通さない | 3.1.a・IS-IS |
| M8-4 | XR01–RT01 のリンクが切れても RT01 とのセッションとラベルを保つ(保つのは最長 N 分)。戻った時にセッションの張り直しを待たない | 3.1.b |
| M8-5 | RT02 の運用者が MPLS の ping/traceroute で XR01 までの LSP を確かめられる(XR01 が応える) | 3.1.e |

- 並びは「前の課題ができている」前提で積む(M8-3 の採点の迂回は RT03 とのセッション= M8-2 の後)。
- 採点で故障を起こす(案)= M8-3: 採点中だけ RT01 の XR01 側の IF で `no mpls ip`(IS-IS は上がったまま LDP だけ落ちる)→ XR01 の LSP のメトリックと
  お客さまの ping/M8-4: 採点中だけ CML のリンク条件 loss 100(XR01–RT01)→ セッションが残る・ラベルが残る・戻した後に稼働時間がリセットされない。

### 20.3 PoC で確かめること(盤面 `problems/_POC-XRLDP`= XRv9000 26.1.1+IOL 17.15 ×3、脇に XRd 26.1.1+IOL ×2)

1. 資源・構築時間。LDP なしでお客さまの通信が RT01 で捨てられること(BGP フリー コアの出発点)。
2. XR の LDP の ID の決まり方(`mpls ldp router-id` なし= 全体の router-id か・最大のループバックか)と、ID(=転送アドレス)に届かない時の両側の表示。
3. XR ⇔ IOS の MD5。片側だけの時の症状とログ。XR の全体の既定パスワードを入れると他の隣(パスワードなし)はどうなるか。
4. `label local allocate for host-routes` の効き目(XR の束縛・RT01 から見た束縛・通信への影響)。
5. 同期= XR の設定場所・広告するメトリックの値・相手の `no mpls ip` で効くか・同期なしでお客さまの通信が捨てられること・セッション保護との関係
   (リンクのハローが無くセッションは targeted で生きている時の同期の状態)。
6. セッション保護= IOS が targeted ハローを受け入れない時の状態・受け入れた時の Protecting の表示・束縛の保持・戻した後の稼働時間・保持時間。
7. OAM= XR が応えるのに `mpls oam` が要るか・XR から打つのに要るか・IOS の既定・traceroute の表示。
8. 脇の系統= XRd が LDP を張り、ラベルで転送するか(RT04 → XR02 → RT05 のお客さまの ping)。

### 20.4 PoC の結果(2026-10-24・XRv9000 26.1.1+IOL 17.15。盤面 `problems/_POC-XRLDP`・手順 `poc/xr/ldp_poc.sh`・記録 `poc/xr/ldp-*.log`)

公式文書の裏どり(§20.5)で「文書だけでは決まらない」とした点を中心に測った。

1. **資源**= 構築 約 10 分(XR01 は起動 4 分)。XR から見えるメモリ 6GB(空き 3GB)。XRT-06 撤収後の CML にこの盤面+脇の XRd 系統を載せて余裕あり。
2. **出発点**= LDP なしで XR01 Lo100 ⇔ RT02 Lo100 の ping は**両向きとも 0%**。RT01 は 10.20/16 を知らない(`% Subnet not in table`)。
   RT02→XR01 向きは RT01 までラベルで届くが、XR01 の返りがラベルなしで RT01 に入って捨てられる(ping は往復が要る)。
3. **LDP の ID**= `mpls ldp router-id` なしでも **Lo0(10.255.0.1)**。アドレス最大の Lo1(10.255.255.1)も番号最大の Lo100 も選ばれない。
   `show router-id` = Loopback0。**XR に全体の `router-id` の設定コマンドは無い**(`router-id` は Invalid input)。
   公式の順番(LDP の設定 → 全体の router-id(IP ARM が決める)→ 番号最大のループバック)のうち、ARM が Lo0 を選んだ形。
   → 「既定の ID が届かないループバックになる」仕込みは作れない。
4. **転送アドレスだけをずらす仕込み**(M8-1 に採用)= `mpls ldp address-family ipv4 discovery transport-address 10.255.255.1`。
   コミットした瞬間に両方のセッションが落ち(RT01 に「DOWN (TCP connection closed by peer)」)、以後上がらない。
   XR の `show mpls ldp discovery` は相手のハローを受け続け(xmit/recv・LDP Id と相手の Transport address も見える)、`show mpls ldp neighbor brief` は空。
   **XR 自身の転送アドレスは `show mpls ldp parameters` の Transport address にだけ出る**(LDP ID は 10.255.0.1:0 のままで正しく見える)。
   RT01 の `show mpls ldp discovery detail` に「LDP Id: 10.255.0.1:0; **no route to transport addr**」「Transport IP addr: 10.255.255.1」。
5. **有効化**= `mpls ldp` → `interface X` だけで IPv4 も有効(既定 VRF)。40 秒以内にセッション Oper・LFIB は 24000 から。
   お客さまの ping 100%。traceroute では**BGP を持たない P(RT01)のホップが `*`**(XR から・RT02 からとも)= 読み物の題材。
6. **MD5**= RT03 にだけパスワード(`mpls ldp neighbor 10.255.0.1 password …`)を入れても、**既存のセッションは切れない**(`clear` で張り直させて初めて落ちる)。
   落ちた後、XR01 に `%IP-TCP-3-NOAUTH : Authentication info not programmed for the packet received from 10.255.0.13:… to 10.255.0.1:646`(約 12 秒ごと)・RT03 は何も出さない。
   XR01 に `mpls ldp` → `neighbor 10.255.0.13:0 password clear …`(running-config は `neighbor` の下の階層形・encrypted で保存)→ 40 秒以内に Oper・
   XR は「TCP connection: …; **MD5 on**」、RT03 は「Password: required, neighbor, in use」。
   **XR の全体の既定パスワード**(`mpls ldp` → `neighbor password clear …`)は、**コミットした瞬間に**パスワードなしの RT01 とのセッションを落とす
   (XR に `%IP-TCP-3-BADAUTH : Invalid MD5 digest from 10.255.0.11`)。外せば戻る。
   ★IOS の `mpls ldp password required`(対象の ACL なし)は**全ての相手**に効く= PoC で RT03 に入れたら RT02 とのセッションが落ち(RT03 に
   `%LDP-4-PWD: MD5 protection is required for peer 10.255.0.12:0, no password configured` が約 30 秒ごと)、予備経路の戻りがラベルなしで RT03 に入って
   捨てられた(BGP フリー コアの典型的な事故がそのまま起きた)。→ 本番の盤面は RT02 ⇔ RT03 にもパスワードを据え付ける。
7. **ホスト経路だけ**= `mpls ldp` → `address-family ipv4` → `label` → `local` → `allocate for host-routes`。XR の `show mpls ldp bindings brief` で
   /24 の Advertised(peers)が 0 になり、RT01 の `show mpls ldp bindings neighbor 10.255.0.1` は /32 だけ(XR01 の Lo0・Lo1・Lo100 の /32・コアの Lo0)。
   通信への影響なし。リンクの /24 のローカル ラベルは数分で LFIB から消える。
8. **同期**= `router isis CORE` → `interface X` → `address-family ipv4 unicast` → `mpls ldp sync`。
   同期なしで RT01 の XR01 側に `no mpls ip`= XR01 は IS-IS の隣接 Up のまま RT01 経由・LFIB は **Unlabelled** → **お客さまの ping 0%**。
   同期を入れると即座に `Sync status: Not ready (No hello adjacency)`・XR01 の LSP で RT01 向けが **Metric: 16777214** → 予備(RT03 経由・ラベル 16)へ・ping 100%。
   RT01 の LDP を戻すと 10 秒以内に Ready・メトリック 10 に戻る。
   `igp sync delay` の形は **`on-session-up <5-300>` と `on-proc-restart` の 2 つだけ**(素の `igp sync delay <秒>` は無い)。
9. **セッション保護**= `mpls ldp` → `session protection`。**既定の保持時間 86400 秒(24 時間)**(公式のコマンド リファレンスの既定どおり。設定ガイドの「無期限」は 26.1.1 では違う)。
   RT01 が targeted ハローを受け入れないと **`state: Incomplete`**(XR の discovery に `10.255.0.1 -> 10.255.0.11 (active), xmit` だけ)。
   RT01 に `mpls ldp discovery targeted-hello accept` で **`Ready`**(Discovery Sources にリンクと Targeted Hello の 2 つ)。
   CML のリンク条件 loss 100 で XR01–RT01 を黙って落とすと、約 20 秒で **`Protecting`・Holdup timer remaining**・RT01 からの束縛を保持・
   戻した後も Up time が連続(2:04 → 4:01)。
10. **保護と同期の関係**(文書で決まらなかった点)= **リンクのハローが消えると、セッションが targeted で生きていても同期は `Not ready (No hello adjacency)`**
    (RFC 5443 の「リンクにハロー隣接があること」と同じ)。リンクを黙って落とした時は、IS-IS の保持時間切れ(+29 秒)より先に、
    LDP のハローの保持時間切れ(+18 秒)でメトリックを上げて予備へ逃げた。RT01 で `no mpls ip`(IS-IS は上がったまま)でも同じ= M8-3 の採点は M8-4 の後でも成り立つ。
11. **OAM**= XR01 に `mpls oam` が無いと、RT02 からの LSP ping は 0%・LSP traceroute は RT01(`L`)の先が `.` の連続。
    XR01 から打つと「**% MPLS Embedded Management Subsystem is not running. To enable, use 'mpls oam' global config command.**」。
    `mpls oam` を入れると両方とも成功(RT02 の trace の最後が `! 2 10.0.1.1`)。`traceroute mpls multipath` も動く(ECMP なし= Path 0 だけ)。IOS(RT01・RT02)は設定なしで応える。
12. **MTU**= XR の IF の MTU 1514(L2 込み)。ラベル 1 枚ぶんで **1500 バイトの DF 付きは両向きとも 0%**・1496 は 100%。
    XR の `ping mpls … sweep 1490 1510 4` は 1500 を超えると `Q`(送れない)。= 読み物の「やってみる」の題材(直すには IOS 側も要るので課題にはしない)。
13. **XRd(脇の系統・XR02)**= LDP を張り、**ラベルを付け替えて転送する**(RT04→RT05 のお客さまの ping 100%・traceroute に `[MPLS: Label 24000]`・IOS からの LSP ping 成功)。
    **ラベル付きの通過なら TCP も正常**(RT04→RT05 の SSH のバナーが返る・RT05 のチェックサム エラーが増えない)。XR02 の LDP を外して**ラベルなしの通過にすると壊れる**
    (バナーが返らない・RT05 の TCP/UDP のチェックサム エラーが増える・traceroute の 2 ホップ目以降 `*`= §14.1 と同じ)。
    → M8 は XRd でも成り立つ見込み。同じ四角形の XRd 版 `_POC-XRLDPD` で同じ手順を流して比べる(§20.5 の後)。

### 20.5 公式文書・RFC での裏どり(2026-10-24・PoC と並行。xrdocs.io は取得していない)

参照= MPLS Configuration Guide for ASR 9000, IOS XR 26.1.x–26.3.x(2026-09-11 更新・以下 CG)/MPLS Command Reference for ASR 9000(累積版・2026-09-11 更新・以下 CR)/
Routing CG・CR の IS-IS 章(2026-09-08 更新)/IOS XE 17.x MPLS CG の「LDP Session Protection」「LDP MD5 Global Configuration」/
Cisco IOS XRd Data Sheet(2026-04-09)/RFC 5036・5443・8029・8277。抽出テキストは作業場所(リポには置かない)。

| 論点 | 文書 | 実機(§20.4) | 扱い |
|---|---|---|---|
| LDP の ID | CR: LDP の設定 → 全体の router-id → 番号最大のループバック | Lo0(ARM の選択)。全体の `router-id` の設定コマンドは無い | 実機に合わせ「XR は既定で Lo0」と書く。根拠は `show router-id` |
| 転送アドレス | CR: 既定は LDP の ID。`address-family ipv4 discovery transport-address` | 一致。ずらすと即セッション断 | M8-1 の仕込み |
| IF の AF | CG: 既定 VRF では IF の `address-family ipv4` は不要(後方互換) | 一致 | — |
| 同期の値 | IS-IS CR: wide で 16777214(最大−1) | 一致 | — |
| 同期の条件 | XR の文書は「リンク上にセッション」とだけ。RFC 5443 は「リンクにハロー隣接」 | **RFC どおり**(ハローが消えれば保護中でも Not ready) | 実機に合わせる |
| 同期の遅延 | CR: `igp sync delay` 5–300/CG の例だけ `on-session-up` | `on-session-up <5-300>`・`on-proc-restart` だけ | 実機の形で書く |
| 保護の既定 | CR の既定「24 時間」/同じ CR の例と CG は「無期限」 | **86400 秒** | CR の既定どおり。CG の記述との違いを読み物に注記 |
| 保護の相手 | IOS XE CG: 両側で保護するか、片側が targeted を受け入れる。RFC 5036 §3.5.2 も同じ | 受け入れなしは Incomplete | RT01 に受け入れを据え付け |
| MD5 | CR: `neighbor <ID>:0 password`・全体の既定は CG の例の階層形 | 一致(running-config も階層形) | — |
| ラベルの絞り込み | CG: `label local allocate for host-routes`/広告と受け入れの絞り込みは広告側を推奨 | 一致 | — |
| `mpls oam` | CR: 既定で無効。送る側/応える側に要るかは明記なし(SR の文書だけ「送る側の前提」) | **送る側も応える側も要る** | 実機に合わせる |
| XRd の転送 | データシート: Control Plane は「最小限の転送」。MPLS を転送するかの明記なし | ラベル付きは正常・ラベルなしの通過で L4 チェックサムが壊れる | 比較 PoC で機種を決める |

### 20.6 XRd との比較(2026-10-24・同じ四角形の XRd 版 `problems/_POC-XRLDPD`= XR01 を XRd 26.1.1 に。同じ手順 `PID=_POC-XRLDPD poc/xr/ldp_poc.sh`・記録 `poc/xr/ldpd-*.log`)

- 構築 約 4 分(XRv9000 版は約 10 分)。b(既定の ID= Lo0・`show router-id`)・bt(転送アドレスの仕込み= no route to transport addr)・b2・c・d・e(同期なしで
  Unlabelled・同期で 16777214)・f(保護の既定 86400 秒・Incomplete → Ready)・f3(Protecting・束縛の保持・同期は No hello adjacency)・f4・g(`mpls oam` は送る側も
  応える側も要る・同じエラー文)・mtu(1500 DF は 0%・1496 は 100%・sweep の `Q`)の**中身はすべて一致**。違いは時刻・カウンタ・`show cef` の内部表示だけ。
- 差 1 つ(課題には効かない)= c-1 で RT03 がセッションを切った直後、XRd の XR01 は古いセッションを 45 秒以上 Up と表示し続けた(`%IP-TCP-3-NOAUTH` は同じく出る)。
  課題の初期状態は最初から RT03 がパスワード必須なので、この場面は起きない。
- XRd の既知の弱点(§14.1)= ラベルなしで通り抜ける TCP/UDP のチェックサムを壊す。この盤面で XR01 を通り抜けるのは RT01 ⇔ RT03 だけ(等コスト)で、
  LDP が動けばラベル付き。採点は ICMP と各機器の show と LSP ping(宛先が XR01 自身)なので影響なし。
- **判定= M8 は XRd**(§14.2 の方針= 明らかな差が出ない単元は XRd)。XRv9000 より軽く(2 vCPU/3GB)、日次パックのラボと同居できる。
  §14.2 の「M8〜M12 は XRv9000 見込み」は M8 について改める。M9 以降も転送の差を単元ごとに確かめる。

### 20.7 PoC を受けた課題の確定案(2026-10-24)

盤面= §20.1 の四角形・**XR01= XRd 26.1.1**・RT01〜RT03= IOL 17.15。IOS 側は「社内の標準どおり」で据え付け(学ぶ側は XR01 だけを触る):
RT01= LDP・`mpls ldp sync`・targeted ハローを受け入れる/RT02= PE(XR01 と iBGP)・LDP・同期・RT03 とパスワード/RT03= LDP・同期・
**パスワード必須**(XR01・RT02 向けの鍵)・targeted ハローは受け入れない。

| 課題 | 中身(挙動で指定) | 採点(挙動) |
|---|---|---|
| M8-1(TS+構築) | 「XR01 は古い PE と入れ替わった。お客さまの通信がコアを通らない」。コアに BGP を入れずに両向き通す・LDP は 2 本のコアのリンクの両方で動かす・Loopback1(NMS 用)は IS-IS に載せない。仕込み= LDP のひな形が入っていて、**転送アドレスが Loopback1**(IF は未登録) | RT01 とのセッション Oper・RT01 の discovery で XR01 の転送アドレスが 10.255.0.1・XR01 の LDP の IF 2 本・RT01 に 10.255.255.1 の経路が無い・お客さまの ping 両向き |
| M8-2 | RT03 はパスワードの無い LDP セッションを受けない(鍵は課題文)。XR01 はホスト経路(/32)にだけラベルを割り当てる | RT03 とのセッション Oper かつ MD5 on・RT01 が XR01 から受けた束縛が /32 だけ・お客さまの ping |
| M8-3 | コアのリンクで IS-IS は上がっているのに LDP が整っていない間は、XR01 はそのリンクで通さない。LDP が整ってから 10 秒は戻さない | 2 本とも同期が有効で遅延 10 秒・採点中だけ RT01 の XR01 側で `no mpls ip` → XR01 の LSP で RT01 向け 16777214・お客さまの ping 両向き → 戻す |
| M8-4 | PRIMARY が切れても RT01 とのセッションと RT01 から受けたラベルを保つ(最長 10 分)。RT03 は targeted を受けないので RT03 には送らない | RT01 は保護 Ready・Duration 600・RT03 には保護なし・採点中だけ CML のリンク条件 loss 100(XR01–RT01)→ Protecting・束縛の保持・お客さまの ping → 戻した後も Up time が続く |
| M8-5 | RT02 の運用者が MPLS の LSP ping/traceroute で XR01 までの LSP を確かめられる(XR01 が応える・XR01 からも打てる)。XR01 宛ては最後までラベル付きで届ける(PHP させない= コアで付けた EXP を XR01 で使う) | RT02 の LSP ping 成功・LSP traceroute が RT01 で explicit-null・XR01 で `!`・RT01 の LFIB が explicit-n・XR01 から RT02 への LSP ping 成功 |

- 並びは前の課題ができている前提で積む(M8-3・M8-4 の迂回は RT03 とのセッション= M8-2 の後)。M8-3 の採点は M8-4 の後でも成り立つ(§20.4-10)。
- **読み物で扱う(ラボにしない)**= MTU(ラベル 1 枚で 1500 の DF が通らない・sweep)・BGP フリー コアの traceroute で P のホップが `*`(explicit-null にすると返る)・
  XR の全体の既定パスワードがパスワードなしの相手を落とす・IOS の `password required` が全員に効く事故(§20.4-6)・LDP の ID の決まり方(XR は Lo0)。
  いずれも「やってみる」の候補。
- 採点で故障を起こす部品は M7 のもの(`login_probe.py` の `--pre-cli/--post-cli`・`--fail-link`・`watch`)をそのまま使う見込み。

### 20.8 その先(M8 追補の案・未着手)

- **Unified MPLS(3.1.d)**= XR01 の先に 2 つめの IGP 領域(アクセス)を足し、XR01 を境界にして BGP ラベル付きユニキャスト(next-hop-self)で
  アクセスの PE のループバックをコアへ運ぶ(IGP 間の再配送なし)。M4 追補と同じく「M8 を解き終えた状態から」のラボにする想定。PoC は M8 の後。
  → **2026-10-24 PoC 完了= §21**。

### 20.9 実装の結果(2026-10-24)

- 成果物= `problems/XRT-07`(XR01= XRd 26.1.1・RT01〜RT03= IOL 17.15・課題ごとの確認 `grading.m8t1〜5.yml`・最終 `grading.yml`=
  M8-1 25・M8-2 20・M8-3 20・M8-4 20・M8-5 15・`learn.yml`(日英)・課題文 日英)、読み物 `courses/xr/{en,ja}/80-m8-mpls-ldp.md`
  (7 節+実践・「やってみる」5 つ・日英で 121 ブロック・見出し 23 を照合)・実践 `81-m8-practice.md`(`course.sh` が課題文から切り出す)・Drive 同期済み。
  模範解= `poc/xr/solve_xrt07.sh`(誤答・別解つき)・E2E= `poc/xr/e2e_xrt07.sh`・記録 `poc/xr/expM8-*.log`。
- 実機 E2E= 白紙 0(課題ごと 5 本・最終)→ 模範解 100(課題ごと・最終とも 1 回目)・learn.yml の模範解を逐語で流して最終 100・`lab.sh reset` 後に白紙 0。
  誤答= IF だけ(転送アドレスはそのまま)20・全体の既定パスワード(RT01 が落ちる)で M8-1 40/M8-2 50・遅延なし 75・全員に保護(RT03 が Incomplete)80・
  `mpls oam` だけ 50・解き終えた後に保護だけ外す → M8-4 0(M8-3 は 100 のまま)・同期だけ外す → M8-3 0。別解= IS-IS の `mpls ldp auto-config`・
  転送アドレスを Lo0 に明示 → M8-1 100。provision 約 4 分。故障を起こす Check= M8-3 約 70 秒・M8-4 約 110 秒(学習モードの上限 240 秒の内)。
- **実装で分かったこと**:
  1. 白紙でも XR01 の LFIB にローカル ラベルが並ぶ(`mpls ldp` のプロセスがあるだけで割り当てる・出力は `Unlabelled`)。採点はラベルが数字であることを見る。
  2. IOS の `mpls ldp sync`(据え付け)は、XR01 がまだ LDP を動かしていない間から RT01→XR01 のリンクを 16777214 にする(IP のプレフィックスも)。
  3. M8-1 の途中(IF だけ足す)では、XR01 の転送アドレスが大きいので XR01 が TCP を開きに行き、RT03 に `%TCP-6-BADAUTH: No MD5 digest from 10.255.255.1` が出る。
     直した後は RT03 の転送アドレスが大きくなり、RT03 が署名つきで開きに来て XR01 に `%IP-TCP-3-NOAUTH`。
  4. **同期の遅延(on-session-up)は、セッション保護で保たれたセッションにリンクの hello が戻った時にも働く**(`Sync status: Deferred (8 sec remaining)`)。
     保護あり= 黙った故障の 12 秒以内に Protecting・同期は Not ready で BACKUP へ(IS-IS の隣接はさらに約 10 秒残る)・戻して 12 秒で PRIMARY へ。
     保護なし= 故障中にセッションが消え、戻した後は新しいセッション(00:00:03)→ Deferred → 約 20 秒で PRIMARY へ。
  5. explicit-null のコミットから RT01 の LFIB が `explicit-n` になるまで 20〜30 秒。RT02 からの顧客の traceroute は、PHP では P のホップが `*`、
     explicit-null では `10.0.12.11 [MPLS: Label 20 Exp 0]` と応える(読み物 6.2 の「やってみる」)。
  6. 「やってみる」の 4.1 は RT01 を触らずに XR01 側で `mpls ldp` から IF を外す形にした(同期なし= Unlabelled で ping 0%・同期あり= 即 16777214 で BACKUP・切り替えの間に 3 発欠落)。
  7. M8-2 を解いた後なら、全体の既定パスワードで落ちるのは RT01 だけ(RT03 は個別の鍵が優先され、セッションも張り直されない)。
  8. ★作業の事故= IOS で `?` のヘルプを引くのに xrsh で「行+?」を送ると、ヘルプの後に残った行が次の行と一緒に実行され、RT01 に
     `mpls ldp explicit-null` と `mpls ldp label`/`allocate global` が入った(気づいて外し、3 台とも初期設定どおりを確認)。IOS でヘルプを引く時は `?` を単独の行で送る。
- **§20.7 から変えた点**= なし(課題・採点の形は確定案のまま)。読み物の 5.2 は実測(上の 4)に合わせ、遅延が保護中のセッションにも働くと書いた。

## 21. M8 追補 — Unified MPLS(SPCOR 3.1.d)(2026-10-24 完了= 課題 §21.6・ユーザ判断 §21.7・実装の結果 §21.8)

§20.8 の案を PoC で確かめた。盤面 `problems/_POC-XRUMPLS`(撤収済み)・手順 `poc/xr/umpls_poc.sh`(段 a〜g・mtu)・記録 `poc/xr/umpls-*.log`。

### 21.1 盤面

XRT-07 の四角形(XR01 は M8-1〜5 を解き終えた設定を初期設定に入れた)の XR01 の先に、アクセスの領域を足した。

```
RT05(アクセスの PE) ── RT04(アクセスの P) ── XR01(境界) ── RT01/RT03(コアの P) ── RT02(コアの PE)
  Lo0 10.255.0.15        Lo0 10.255.0.14        Lo0 10.255.0.1                         Lo0 10.255.0.12
  お客さま B 10.50/16    10.0.45.0/24・10.0.14.0/24(XR01 Gi0/0/0/2)                    お客さま A 10.20/16
```

- アクセスの IGP= IS-IS ACCESS(エリア 49.0002・L2 のみ・wide)。コアの IS-IS CORE とは別のインスタンスで、経路は交換しない。
- XR01 を 2 つの PE(RT02・RT05)の BGP ラベル付きユニキャスト(以下 LU)の RR にし、反映する経路の next hop を自分にする。
  P(RT01・RT03・RT04)は BGP を動かさず、相手の領域のループバックも知らない。
- XRd が XR01 をラベル付きで通り抜ける TCP(PE 同士の直接の iBGP)を壊さないことを確かめた(§14.1 の弱点はラベルなしの通過だけ)。

### 21.2 裏どり(資料)

| 記号 | 資料 | 版 |
|---|---|---|
| A | Cisco TAC「Configure Unified MPLS in Cisco IOS XR」(doc 119191) | 2015(2017 改訂) |
| B | Cisco TAC「Labeled and Unlabeled Together on one BGP Neighbor on IOS-XR」(doc 216498) | 2020-12 |
| C | BGP Command Reference for Cisco 8000 | 2026-09 |
| D | Cisco TAC「Cisco IOS-XR BGP with MPLS Designs」(doc 217202) | 2021 |
| E | IS-IS の設定ガイド: Cisco 8000(24.x・累積版 2026-09)/ ASR 9000 6.5・7.8・24.x/NCS 5500 24.x/NCS 540 26.x | 各版 |
| F | Catalyst 9500 17.14「Configuring Seamless MPLS」・Catalyst 9400 17.12「Inter-AS IPv4 BGP Label Distribution」 | 17.14・17.12 |
| G | RFC 8277(BGP によるラベルの割り当て。RFC 3107 を廃止)・draft-ietf-mpls-seamless-mpls-07(2014・RFC にならず失効) | 2017・2014 |

### 21.3 実測の結果(XRd 26.1.1・IOL 17.15)

| 項目 | 資料 | 実機 | 扱い |
|---|---|---|---|
| LU の形 | C: 近隣の AF `ipv4 labeled-unicast` は、ルータの AF `ipv4 unicast` が前提 | 一致。近隣の AF は LU だけで足りる | — |
| U と LU を同じ近隣に | B: 6.2.1 から可。表は 1 つ | 一致。`show bgp ipv4 unicast` に LU の経路も並ぶ。ラベルの無い経路(自分の 10.30/16)は SAFI 1 で送る | — |
| IOS の send-label | F: 全部の経路にラベルを付けて送る | 一致。`send-label` を足すとセッションを張り直し、以後は SAFI 4 だけで送る | 据え付け側 |
| next-hop-self(RR) | A: 「next-hop-self does not work」・`ibgp policy out enforce-modifications` が要る | **一致**。enforce なし= 反映する経路の next hop を替えない(RT02 で 10.255.0.15 の next hop が自分自身→ 再帰がループして 0%) | 課題の仕込み候補 |
| allocate-label | A・B: 無いとローカル ラベルが無く、LU で送らない | **一致**。enforce あり・allocate なし= 反映が止まる(Not advertised to any peer)。enforce なしなら受けたラベルをそのまま渡す | 課題の仕込み候補 |
| ラベルの番号 | 記述なし | ループバック /32 の BGP のローカル ラベルは LDP と同じ番号(24003 など)。転送表は 1 行で BGP のラベル→ LDP のラベルへ付け替え | 読み物 |
| お客さまの経路 | B: ローカル ラベルの無い経路は NHS の LU 近隣へは送らない | `allocate-label route-policy`(/32 だけ)にすると、XR01 はループバックだけ反映し、お客さまの経路は流さない | 課題の候補 |
| RR のクライアント | RFC 4456 | 片側だけクライアントでも通る(クライアントの経路は全員へ反映)。XR はクライアント指定の付け外しでセッションを張り直す | 採点は挙動で |
| LSP ping | 記述なし(IOS の `fec-type bgp`) | 既定(LDP の FEC)は `Q`。`fec-type bgp` で送れるが、送信元がコアのリンクのアドレスだと相手の PE が返せない(経路が無い)→ `source <Lo0>` で成功。traceroute は向こう側の P が `*` | 読み物(やってみる) |
| MTU | — | コアでもアクセスでもラベルは 2 枚(LDP+BGP)。DF 付きで 1492 は通り 1496 は落ちる | 読み物 |
| XR01 の Lo0 をアクセスへ | **E が割れている**(下) | 2 つの IS-IS インスタンスに Lo0 を載せても、コミットは通り両方で広告される。A の形(Lo0 だけ接続経路として再配送・RPL で絞る)も成立(X フラグ= 外部) | **ユーザ判断待ち**(§21.7) |

IS-IS の資料 E の食い違い:
- Cisco 8000 の設定ガイド(24.x・累積版 2026-09): 「an interface can be associated with only one IS-IS instance」「Instances may not share an interface」。
- ASR 9000 7.8・24.x/NCS 5500 24.x/NCS 540 26.x: 「Multiple IS-IS instances can exist on the same physical interface. However, you must configure different instance-id …」。古い「only a single IS-IS instance」の文は消えている。
- どれもループバック・パッシブの IF には触れていない。XRd 26.1.1 は instance-id なしで受け付けた。

IOS 側で気づいたこと(据え付けの設計に効く):
- PE 同士の直接のセッションで自分のループバックも送ると、相手は「10.255.0.15 の next hop が 10.255.0.15」という経路を持ち、再帰がループしてお客さまの通信が 0% になる
  → 据え付けで、直接のセッションはお客さまの経路だけ送る(prefix-list out)。
- IOS 17.15 の labeled-unicast unique モードの既定は、資料(F の系統)どうしで食い違う。この盤面では同じプレフィックスを SAFI 1 と SAFI 4 で並べないので効かない。

### 21.4 欠けた時の症状(正常な形から 1 つずつ外す・段 f)

| 外したもの | RT02 から見た 10.255.0.15/32 | お客さまの通信 |
|---|---|---|
| `ibgp policy out enforce-modifications` | next hop 10.255.0.15(替わらない)・ラベル imp-null。お客さまの経路も XR01 から流れてくる | 0% |
| `allocate-label` | 経路が消える(XR01 が送らない) | 0%(10.50/16 は inaccessible) |
| RT02 向けの `next-hop-self` | enforce なしと同じ形 | 0% |
| RT05 向けの `route-reflector-client` | 変わらない(RT02 がクライアントなので両向きに反映される) | 通る |

### 21.5 PoC で決めたこと

- **M8 追補も XRd**(ラベル付きの通過は TCP も正常。PE 同士の iBGP が XR01 を通り抜けて上がる)。
- お客さまの経路は **PE 同士の直接の iBGP(据え付け)** が運び、XR01 は PE のループバックだけを LU で運ぶ(本来の Unified MPLS の形。境界にお客さまの経路を持たせない)。
  IOS の `send-label` は全部をラベル付きにするので、XR01 を「サービスの経路は next hop を替えない RR」にする形は IOS と組み合わせにくい(サービスは M9 の VPNv4 で扱う)。

### 21.6 課題の案(ラボ `XRT-08`・XRT-07 を解き終えた状態から・XR01= XRd 26.1.1)

据え付け(学ぶ側は触らない)= RT04(P)・RT05(PE・XR01 と LU・RT02 と直接の iBGP)・RT02 に `send-label` と Lo0 の network と RT05 との直接の iBGP。
XR01 の初期設定= XRT-07 の模範解+アクセスの IF のアドレス+前任者の LU の設定(近隣 2 つ・LU の AF・route-reflector-client・next-hop-self。enforce と allocate-label は無い)。

| 課題 | 中身(挙動で指定) | 採点(挙動) |
|---|---|---|
| M8-6(構築) | 新設のアクセス網に XR01 を参加させる。アクセスの IGP は IS-IS の別インスタンス ACCESS(エリア 49.0002)・LDP も動かす。コアとアクセスの間で経路を交換しない(アクセスに見せてよいのは XR01 自身のループバックだけ) | ACCESS の隣接 Up・RT04 との LDP Oper・RT04/RT05 に 10.255.0.1 の経路・RT04 にコアの経路が無い・RT01 にアクセスの経路が無い |
| M8-7(TS) | 「前任者が境界の BGP を入れたが、RT02 と RT05 の PE 間のセッションが上がらない」。IGP 間で再配送せず、P に BGP を入れずに、お客さま A ⇔ B を通す | RT02 の 10.255.0.15/32 が BGP・next hop 10.255.0.1・ラベル付き(RT05 も同じ)・PE 間のセッション Established・お客さまの ping 両向き・RT02 からの traceroute で RT01 のホップにラベル 2 枚 |
| M8-8 | 境界はお客さまの経路を運ばない。XR01 がラベル付きで反映するのは PE のループバック(/32)だけ | XR01 から RT02・RT05 へ送る LU が /32 だけ・RT02 の 10.50/16 は RT05 からの 1 本だけ・お客さまの ping |

- 配点の案= M8-6 30・M8-7 45・M8-8 25。M8-7 の仕込みは「enforce なし」と「allocate-label なし」の 2 段(片方だけ足すと症状が変わる)。
- 別解(採点は挙動なので通る)= `allocate-label all`(M8-7 まで)・RPL の `set next-hop self`・Lo0 を 2 つのインスタンスに載せる(§21.7 の判断しだい)。
- 誤答の想定= RT05 の Lo0 をコアへ再配送(RT01 に経路が出る→ M8-6/M8-7 で落とす)・enforce だけ・allocate だけ。
- **読み物だけで扱う(やってみる)**= LSP ping の `fec-type bgp` と送信元(応答の戻り道)・traceroute で向こう側の P が `*`・MTU(ラベル 2 枚で 1492)・
  BGP のラベルが LDP と同じ番号・draft の「核→集約は next hop を替えない」設計(この盤面は両向きとも替える= A の 2 つめの形)。
- XRT-07 から引き継ぐ確認= お客さま A'(XR01 の 10.30/16 ⇔ RT02 の 10.20/16)が引き続き通ること(壊していないか)。

### 21.7 ユーザ判断(2026-10-24 決定= 1 は案どおり「挙動で採点・模範解は Lo0 の接続経路の再配送」・2 は §21.6 の 3 本で実装へ)

1. **XR01 の Lo0 をアクセス側へ載せる方法**(公式文書が製品系列で割れている。CLAUDE.md の作問の裏どり 2)。
   案= 採点は挙動だけ(RT04 に 10.255.0.1 があり、コアの経路が無い)で、どちらの形も通す。模範解は資料 A の形(Lo0 だけ接続経路として再配送)。
   読み物には「2 つのインスタンスに載せる形も XRd 26.1.1 では通るが、公式の記述が製品で割れている」と注記する。
   別案= アクセスの IGP を OSPF にする(Lo0 を IS-IS と OSPF の両方に載せるのは問題なし・資料 A も OSPF)。
2. 課題の数と並び(§21.6 の 3 本でよいか)。

### 21.8 実装の結果(2026-10-24)

- 成果物= `problems/XRT-08`(XR01= XRd 26.1.1・RT01〜RT05= IOL 17.15・課題ごとの確認 `grading.m8t6〜8.yml`・最終 `grading.yml`=
  M8-6 30・M8-7 45・M8-8 25・`learn.yml`(日英)・課題文 日英)、読み物 `courses/xr/{en,ja}/82-m8-unified-mpls.md`(6 節+実践・
  「やってみる」4 つ・図は `:::topo`)・実践 `83-m8-practice-2.md`(`course.sh` が課題文から切り出す)。
  模範解= `poc/xr/solve_xrt08.sh`(誤答・別解つき)・逐語= `poc/xr/verbatim.py`・E2E= `poc/xr/e2e_xrt08.sh`・誤答と別解の一括= `poc/xr/e2e_variants_xrt08.sh`・
  やってみるの実測= `poc/xr/try_xrt08.sh`・記録 `poc/xr/expM8b-*.log`。
- 実機 E2E= 白紙 0(課題ごと・最終)→ 模範解 100(課題ごと・最終とも 1 回目)・learn.yml の模範解を逐語で流して最終 100・reset 後 0。
  別解= Lo0 を CORE と ACCESS の両方に載せる → M8-6 100。誤答= Lo0 を載せない 40(隣接と RT01 の束縛は通る)・コアの経路をアクセスへ再配送 80・
  enforce だけ 0・allocate-label だけ 0・allocate-label all のまま送る経路だけ絞る → M8-8 70。provision 約 4 分。
- **実装で分かったこと**:
  1. M8-6 の直後(仕込みのまま)、RT02 の 10.255.0.15/32 は `(inaccessible)`・`Paths: (1 available, no best path)`・ラベル imp-null。
     PE 同士のセッションは `never Idle`。M8-7 を入れると約 30 秒で上がった。
  2. ★`lab.sh reset` で XR01 を戻しても、相手役の BGP セッション(RT02⇔RT05・RT05⇔XR01)は保持時間の 180 秒だけ古い経路ごと残り、
     M8-7 の確認が白紙でも 35 点になった → `xr_reset.py` の `xr_reset_exec` を IOS のノードにも流せるようにし、XRT-08 で
     RT02 `clear ip bgp 10.255.0.15`・RT05 `clear ip bgp *`・XR01 `clear bgp 10.255.0.15` を流す(以後 reset 直後でも 0)。
  3. 構築の直後は IOL の BGP が最良経路を選ばず、XR01 から RT02 のお客さま A への ping が 1〜2 分落ちる(既知・§16 の IOL の癖)。
  4. 2026-10-25 ユーザ要望(「この章は難しい・利点が分からない」)で、やさしい付録 `courses/xr/{en,ja}/84-m8-appendix.md` を足した
     (コマンド抜き・図 5 枚= ラベルの道/道の作り方 3 通りの比較/ラボで誰が何を知っているか/パケット 1 つ/境界の 2 つの仕事の 4 通り)。
     本編 82 の冒頭と learn.yml(M8-6・M8-7 の read:)から開ける。図の道具は全角の幅を見込むようにした(日本語の名前が箱からはみ出していた)。


## 22. M9 L3VPN(SPCOR 4.3)(2026-10-27 設計・PoC中)

**範囲= SPCOR 4.3.a Intra-AS VPN・4.3.b 共有サービス(エクストラネットとインターネット)**。4.1.b Inter-AS(オプション A/B/C)と 4.1.c CSC は
describe 級なので読み物だけで受ける(XR の ASBR の `retain route-target all`・オプション C の LU など)。IOS の L3VPN は ENARSI-MPLS-L3VPN-01〜06 で
済んでいるので、**XR で書き方や動きが違うところ**に絞る。ラボは **`XRT-09`**(XRT-07 を解き終えた状態から)。
2026-10-27 ユーザが XRT-07/08 を全通過 → 撤収して PoC(ユーザ了承)。

### 22.1 盤面(PoC= `problems/_POC-XRL3VPN`・XRd 版と `_POC-XRL3VPNV`・XR01 だけ XRv9000 版)

- コア= XRT-07 の四角形(IS-IS CORE・LDP・同期・セッション保護・RT03 の MD5)。**XR01 と RT02 が PE**、RT01/RT03 は P。
- **XR02= VPNv4 のルート リフレクタ(XRd)**。RT03 の先の行き止まり(10.0.33.0/24・IS-IS だけ・LDP なし)= 転送の道に入らない
  (XRd の公式の位置づけ= vRR そのもの・§19.4 のメモ)。PE 同士は VPNv4 を直接張らず XR02 とだけ。
- お客さま(CE は IOL・据付で変えない):

| サイト | 収容 | VRF | CE の AS | 経路 |
|---|---|---|---|---|
| CEA1 | XR01 Gi0/0/0/2(172.16.11.0/24) | CUST-A(RT 65000:101) | 65101 | LAN 10.101.1.0/24・公開 198.51.100.0/24 |
| CEA2 | RT02 Et0/2(172.16.12.0/24) | CUST-A | 65101(同じ AS) | LAN 10.101.2.0/24 |
| CEB1 | XR01 Gi0/0/0/3(172.16.21.0/24) | CUST-B(RT 65000:102) | 65201 | LAN 10.102.1.0/24 |
| CEB2 | RT02 Et1/0(172.16.22.0/24) | CUST-B | 65202 | LAN 10.102.2.0/24 |
| SVC | XR01 Gi0/0/0/4(172.16.91.0/24・静的) | SVC | — | 共有 10.99.1.0/24(配る)・社内 10.99.2.0/24(配らない) |
| INET | XR01 Gi0/0/0/5(192.0.2.0/24・グローバル) | — | 64500 | 既定経路・203.0.113.0/24 |

- RT の約束= お客さまは自分の RT と、共有サービスが配る 65000:900 を取り込む(RT02 は据付で取り込み済み)。SVC は A・B の RT を取り込む。
- ラボ化では XRT-07 のグローバルの「お客さま A'」(Lo100 の 10.30/16・10.20/16 と XR01⇔RT02 の ipv4 iBGP)を外す想定(VPN のお客さまと名前が紛らわしい)。

### 22.2 課題(案・PoC の結果で確定する)

| 課題 | 中身(挙動で指定) | 主な XR の論点 |
|---|---|---|
| M9-1(構築) | お客さま A の拠点 1(CEA1)を XR01 に収容する(値は課題文で渡す)。VPNv4 は XR02 とだけ張る | 全体の `address-family vpnv4 unicast`・RD は BGP の VRF の下(無いと AF を作れない)・RT は `vrf` の下・PE-CE の eBGP に RPL |
| M9-2(TS) | 「前任者が XR02 をルート リフレクタとして入れたが、拠点どうしが通じない」。PE 同士の直接のセッションは張らない | 仕込み= XR02 の `route-reflector-client` が ipv4 の AF の下だけ+前任者が足した `retain route-target all`(全部持っているのに配らない)。直すと CEA2 には届くが CEA1 には届かない= 2 段目は **XR は CE の AS を含む経路をそもそも送らない**(as-override) |
| M9-3(構築) | 共有サービス= SVC の 10.99.1.0/24 だけを A・B の全拠点に見せる。10.99.2.0/24 は見せない・A と B は互いに見えない・SVC から両方へ届く。SVC の経路には社内の約束どおり 65000:999 も付ける | `export route-policy` と `set extcommunity rt … additive`(無いと 65000:999 が消える)・輸出の方針では経路を落とせない・同じ PE の VRF どうしも RT だけで取り込む |
| M9-4(構築) | インターネット= A の両拠点に既定経路・A の公開セグメントだけをインターネットへ(B は出さない) | `import from default-vrf … advertise-as-vpn`(無いと RT02 側に届かない)・`export to default-vrf`(リモートの拠点の経路は `allow-imported-vpn` が要る)・グローバルの eBGP に RPL |

- 拡張の案(PoC で確かめてから)= M9-4 で A の拠点 2 にも公開セグメント(198.51.100.128/25)を持たせ、`allow-imported-vpn` を要件の側から要るようにする。
- 読み物だけで扱う(やってみる)= ラベルの割り当て方(既定はプレフィックスごと・`label mode per-vrf` で 1 本の Aggregate)・VRF を足した時の
  自動の取り直し(Route refresh)・取り込み先の無い経路の捨て方(PE は Failed RT match に数える)・静的経路での受け渡し(`… vrf default <次ホップ>`)・
  Inter-AS/CSC。

### 22.3 PoC の結果(2026-10-27・XRd 版。手順 `poc/xr/l3vpn_poc.sh`・記録 `poc/xr/l3vpn-{a..k}.log`・TCP の確かめ `poc/xr/tcpprobe.py`)

1. **IF を VRF へ**= アドレスの付いた IF に `vrf CUST-A` を足すコミットは通り、アドレスは残ったまま VRF へ移る(README の記録どおり)。
   直後 5 秒の ping は `UUU`、30 秒後は成功(反映待ち)。★公式文書は「先にアドレスを消さないと拒否」(§22.5)= 食い違い。
2. **BGP の木の順序**= 全体の `address-family vpnv4 unicast` が無いと、VPNv4 の近隣も VRF の AF も「The (parent) address family has not been initialized」で拒否。
   RD の無い VRF に AF を作ると「**The RD for the VRF must be present before an address family is activated**」で拒否(擬似アトミックで同じコミットの全体の AF も戻る)
   → RD 抜けは黙った故障にならない(TS の題材にしない)。全体の VRF モードにも `rd` がある(新しい文書の書き方)。
3. **PE-CE**= RPL なしは隣接が上がって「0!」・`No policy: 2`(M5 と同じ)。PASS を付けると 2 本受ける。
4. **RR**= XR02 に RR の設定が無い(素の iBGP・VRF なし)と、VPNv4 を **受けても全部黙って捨てる**(St/PfxRcd 0・0 accepted・拒否 0)。
   `retain route-target all` を入れると全部保持するが反映しない(RT02 に届かない)。retain を外して両 PE を vpnv4 の AF で
   `route-reflector-client` にすると保持も反映もする(RR は既定で全部保持)。
5. **PE の RT のふるい**= XR01 は取り込み先の無い CUST-B の経路を捨てる(`show bgp vpnv4 unicast rd 10.255.0.12:102` が空)。
   近隣の詳細に `Failed RT match: N` で数が出る。VRF を後から足すと **自動で Route refresh を 1 回送り**、5 秒以内に取り直した。
6. **as-override**= 無いと XR01 は CEA2(AS 65101)の経路を CEA1(AS 65101)へ **送らない**(`Not advertised to any peer`・CEA1 の受信 0)。
   IOS の PE は送って CE 側で落とす(受け側の検査)のと違う。as-override で `65000 65000` になって届き、A の拠点間 ping 成功。
7. **ラベル**= 既定はプレフィックスごと(24004・24005)。`label mode per-vrf` で 1 本(`Aggregate CUST-A: Per-VRF Aggr[V]`)。
   グローバルから取り込んだ既定経路には per-prefix のままでも VRF の 1 本が付く(文書の「接続・集約・ローカルは per-vrf」どおり)。
8. **共有サービス**= `export route-policy` で 10.99.1.0/24 に `set extcommunity rt (65000:900) additive` → RT は 900 と 999。A・B の全拠点が 10.99.1.1 に届き、
   10.99.2.1 と相手のお客さまには届かない。**additive なしだと 999 が消えて 900 だけ**(置き換え)。方針で pass しない経路も輸出はされる(落とせない)。
9. **インターネット**= `import from default-vrf route-policy … ` だけだと既定経路は CEA1 には配られるが VPNv4 に出ない(RT02 に届かない)。
   `advertise-as-vpn` を付けると RT02・CEA2 に届く。`export to default-vrf` で 198.51.100.0/24 がグローバルへ → INET へ。
   リモートの PE から来た経路(10.101.2.0/24)は **`allow-imported-vpn` が無いとグローバルへ出ない**。CEA1 の公開アドレスから INET へ ping 成功。
   静的経路の `0.0.0.0/0 vrf default 192.0.2.2`(VRF の中で次ホップをグローバルに)もコミットが通り経路が入る。
10. ★**XRd の転送**= ping はすべて通る。**TCP/UDP は、XR01 がお客さまから受けてラベルを付ける向き(CEA1→CEA2)と、ラベルなしで通り抜ける向き
    (CEA1→SVC・CEA1→INET)で L4 チェックサムが壊れる**(相手の IOL の TCP/UDP の checksum errors が増える・SSH のバナーが返らない・
    CEA1 からの traceroute は RT02 の先が `*`)。ラベルを外して CE へ出す向き(CEA2→CEA1)は正常。
    → お客さまの traceroute や TCP が片向きだけ死ぬと、解く側が設定の誤りと取り違える。**XR01 は XRv9000 にしたい**(XRv9000 版の比較は §22.4)。

### 22.4 XRv9000 との比較(2026-10-27・盤面 `_POC-XRL3VPNV`= XR01 だけ XRv9000 26.1.1・XR02 は XRd のまま。同じ手順 `PID=_POC-XRL3VPNV poc/xr/l3vpn_poc.sh a…l`・記録 `poc/xr/l3vpnv-*.log`)

- **制御プレーンは §22.3 の 1〜9 がすべて同じ**(拒否の文言・RR の保持と反映・Failed RT match・Route refresh・as-override の送らない動作・
  ラベル(既定 per-prefix 24004/24005・per-vrf で Aggregate 24006)・additive の置き換え・advertise-as-vpn・allow-imported-vpn・静的での受け渡し)。
- **転送は XRv9000 が正常**= CEA1⇔CEA2 の TCP が両向きとも通る(SSH のバナーが返る)・traceroute が両向きとも最後まで出る・
  CEA1⇔SVC(同じ PE の VRF どうし)・CEA1⇔INET(VRF⇔グローバル)の TCP も通る・相手の IOL の checksum errors は 0 のまま。
- 段 l(拠点 2 の公開セグメント 198.51.100.128/25)= `allow-imported-vpn` でグローバルに入り、XR01 の CEF は RT02 へ `labels imposed {16 25}`。
  INET⇔CEA2 の ping・TCP とも両向き正常。CEA2 から INET への traceroute は RT02→RT01(`Labels 22/24006`)→XR01→INET。
- IF を VRF へ(公式との食い違いの補足・`l3vpnv-m*.log`)= XRv9000 でもコミットは拒否されない。グローバル→VRF・VRF→グローバル・
  **既にある** VRF から VRF へ= アドレスを残したまま 30 秒で通る。**移し先の VRF を同じコミットで作って VRF から VRF へ移した時は、30 秒待っても通じなかった**
  (XRd では同じコミットで作ったグローバル→VRF が通った= 原因は切り分けていない)。
- **判定(案)= XR01 は XRv9000 26.1.1、XR02(RR)は XRd 26.1.1**。XRd の PE はお客さまの TCP/UDP を片向きだけ壊し、
  解く側が設定の誤りと取り違える(§22.3-10)。XRv9000 は 1 台なので同時 2 台の上限に収まる(構築は約 10 分)。

### 22.5 公式文書・RFC での裏どり(2026-10-27・PoC と並行。xrdocs.io は取得していない・問題集サイトは使っていない)

| 論点 | 公式の記述(出典) | 実機(XRd 26.1.1) | 判定 |
|---|---|---|---|
| RT と RD の置き場 | RT= `vrf X / address-family ipv4 unicast / import\|export route-target`・RD= `router bgp / vrf X / rd`(Cisco 8000 BGP コマンド リファレンス)。新しい文書は `vrf X / rd` も示す(ASR 9000 BGP 設定ガイド 24.x・Cisco 8000「BGP Route Distinguisher」) | 両方ある(`vrf CUST-A / rd ?` が通る) | 一致。模範解は BGP の VRF の下(どちらが勝つかは未確認) |
| RD の無い VRF | 公式の記述なし(RFC 4364 §4.2= VPN-IPv4 経路には RD が要る) | AF を作るコミットが拒否される | 実機で補う |
| ★IF を VRF へ | 「VRF を付ける・外す・変える前に IPv4/IPv6 アドレスを消すこと。消さないと拒否」(NCS 5500 L3VPN 設定ガイド 7.11・ASR 9000 MPLS L3VPN 設定ガイド 7.11) | 拒否されない・アドレスは残ったまま VRF へ移り、30 秒後には通る | **食い違い(ユーザ判断 §22.6)** |
| 全体の AF が先 | 「近隣の下に AF を作るには、BGP の全体にその AF が要る」(ASR 9000 BGP 設定ガイド 24.x) | 同じ(VRF の AF も全体の vpnv4 が要る) | 一致 |
| RT のふるい | PE は取り込みの RT に合わない経路を RPL なしで捨てる(ASR 9000 ルーティング ポリシー 24.x)。VRF が無く RR でもない XR は経路を持たない(TAC 217202) | 同じ(素の iBGP の XR02 は 0 accepted) | 一致 |
| RR は全部保持 | 「RR は全部の VPNv4 経路を保持する。既定の動作なので all は要らない」・RR クライアントが 1 つでもあれば RR(ASR 9000 BGP 24.x・Cisco 8000 BGP CR) | 同じ | 一致。★コマンド リファレンスの retain の既定値の欄は「全部受ける」と書き、本文・TAC と矛盾 |
| retain route-target | オプション B の ASBR に必須・RR の分割に route-policy 形(Cisco 8000/NCS 5500 BGP CR) | RR でない XR02 に入れると保持するが反映しない(iBGP→iBGP) | 一致(反映しないのは iBGP の原則) |
| VRF を足すと取り直す | 「新しい VRF の RT の経路を持っていなければ RR に Route refresh を送る」(同上) | 1 回送って 5 秒で取り直した | 一致 |
| eBGP に方針 | 「eBGP の近隣は入出の方針が要る。無ければ送受しない」(VRF の例外なし)・7.5.1 から `bgp unsafe-ebgp-policy` | 同じ | 一致 |
| as-override / allowas-in / site-of-origin | VRF の近隣の AF の下(Cisco 8000 BGP CR) | as-override で届く。★XR は as-override が無いと送らない(送る側の検査)| 一致(送らない動作は文書に明記なし・実機で補う) |
| ラベルの割り当て | 既定= プレフィックスごと。`label mode per-vrf\|per-ce\|route-policy`(Cisco 8000/NCS 5500 BGP CR)。Cisco 8000 は per-vrf を明示すること(L3VPN 設定ガイド 7.11) | 既定 per-prefix・per-vrf で Aggregate 1 本 | 一致 |
| 輸出の方針 | `export route-policy`。「この方針で経路は落とせない」(BGP CR)。additive の無い set は RT を置き換えるかは明記なし | 落とせない・additive なしは置き換え | 一致+実機で補う |
| 同じ PE の VRF どうし | 「VPNv4 にする時(または PE の中で VRF から VRF へ流れる時)に輸出の RT を付ける」(ルーティング ポリシー 24.x) | RT だけで取り込む | 一致 |
| VRF とグローバル | `vrf X / address-family ipv4 unicast / import from default-vrf route-policy P [advertise-as-vpn]`・`export to default-vrf route-policy P [allow-imported-vpn]`。方針は必須。advertise-as-vpn が無いと「PE には配らないが CE には配る」。リモートの経路は allow-imported-vpn が要る(ASR 9000 BGP 24.x・4.3.1 から)。TAC 218336 に ASR 9901 での例 | すべて同じ | 一致 |
| 静的での受け渡し | `prefix [vrf 名] 次ホップ`(ASR 9000 静的経路 24.x・XR 12000 CR 4.3)。`vrf default` を書けるかは明記なし | 通る | 実機で補う |
| IOS の PE | `vrf definition`・`bgp default route-target filter`(既定で有効) | — | RT02 は据付 |
| Inter-AS/CSC | RFC 4364 §9・§10。XR のオプション B= ASBR に VRF 不要・`retain route-target all`・eBGP の VPNv4 に方針・相手 ASBR への /32 静的経路(NCS 5500 L3VPN 7.11)。オプション C= LU と `allocate-label`。CSC= VRF の近隣で LU | — | 読み物だけ |
| XRd の転送 | XRd のデータシート= Control Plane 版は「最小限の転送(ピアリングや南向きに足りる程度)」 | §22.3-10 | XRv9000 と比べて決める |

- 出典(題名・版): Cisco 8000 BGP Command Reference(累積・24.x/25.x の履歴つき)／NCS 5500/540/560 BGP Command Reference／
  Routing Configuration Guide for ASR 9000 IOS XR 24.x(Implementing BGP・Implementing Routing Policy・Implementing Static Routes。2026-09 版)／
  L3VPN Configuration Guide for NCS 5500 IOS XR 7.11.x／L3VPN Configuration Guide for Cisco 8000 IOS XR 7.11.x／MPLS L3VPN Configuration Guide for ASR 9000 7.11.x／
  Cisco 8000 BGP Configuration Guide「BGP Route Distinguisher」／XR 12000 Routing Command Reference 4.3.x／TAC 217202「Cisco IOS-XR BGP with MPLS Designs」(2021)／
  TAC 218336「Configure Route Leak between GRT and VRF with IOS XR」／IOS MPLS Command Reference(`bgp default route-target filter`)／IOS XRd Data Sheet／RFC 4364。

### 22.6 ユーザ判断(2026-10-27 決定= 4 点とも案どおり。1= 採点しない・2= XR01 は XRv9000/XR02 は XRd・3= 拠点 2 の公開も入れる・4= 外す)

1. **★公式と実機の食い違い(CLAUDE.md の作問の裏どり 2)= アドレスの付いた IF の VRF を変える**。公式(NCS 5500/ASR 9000 の L3VPN 設定ガイド 7.11)は
   「先にアドレスを消さないと拒否」。実機(XRd・XRv9000 26.1.1)は拒否せず、たいていはアドレスを残したまま通じるが、通じない場合もあった(§22.4)。
   案= **この論点は採点しない**。盤面のお客さま側の IF は最初からアドレスなしにして、課題文で「VRF とアドレス」を渡す(模範解は vrf→アドレスの順)。
   読み物に「文書の規則と 26.1.1 の挙動」を注記する。
2. **機種**= XR01 を XRv9000(§22.4 の判定案)・XR02 を XRd。
3. **課題の並びと中身**= §22.2 の 4 本。M9-4 を拠点 2 の公開セグメントまで広げて `allow-imported-vpn` を要件から要るようにするか(PoC で成立を確認済み)。
4. XRT-07 のグローバルの「お客さま A'」(10.30/16・10.20/16 と XR01⇔RT02 の ipv4 iBGP)を外すか。

### 22.7 課題の確定案(2026-10-27・§22.6 の決定を受けて)

**初期状態**= XRT-07 を解き終えた状態から「お客さま A'」(XR01/RT02 の Lo100 と XR01⇔RT02 の ipv4 iBGP)を外したもの+ 新しいノード。
RT02(VRF CUST-A/B・XR02 への VPNv4)・CE 5 台・INET は据付(変えない)。XR02 は「前任者が入れた RR」= 仕込みあり。
XR01 のお客さま側の IF は説明だけ(アドレスなし= §22.6-1)。機種= XR01 は XRv9000 26.1.1・XR02 は XRd 26.1.1。
公開セグメントは拠点 1 が 198.51.100.0/25(CEA1)・拠点 2 が 198.51.100.128/25(CEA2)。ラボ ID は `XRT-09`。

| 課題 | 中身(挙動で指定・値は課題文で渡す) | 確認(案) |
|---|---|---|
| M9-1(構築) | お客さま A・B の拠点 1(CEA1・CEB1)を XR01 に収容する。VRF・RD・RT・IF のアドレス・CE の AS を表で渡す。VPNv4 はルート リフレクタ XR02 とだけ張る(PE 同士は張らない) | 2 つの VRF の RD/RT・CE との隣接が Established で経路を受けている(`!` なし)・XR01⇔XR02 の VPNv4 が Established で 2 VRF の経路を送っている |
| M9-2(TS) | 「CEA1 と CEA2(B も同じ)の LAN どうしが通じない」。XR02 を直してよい・CE と RT02 は変えない・PE 同士の VPNv4 は張らない | RT02 の両 VRF に XR01 の拠点の経路(Cluster list に XR02)・CEA1 に 10.101.2.0/24・両お客さまの拠点間 ping 両向き・XR02 の両 PE が vpnv4 の RR クライアント・A と B が互いに届かない |
| M9-3(構築) | 共有サービス= SVC(静的)を XR01 に収容。10.99.1.0/24 だけを A・B の全拠点に見せる・10.99.2.0/24 は見せない・SVC から両方へ届く・SVC の経路には 65000:999 も付ける | RT02 の 10.99.1.0/24 の RT が 900 と 999・CEA2/CEB2 から 10.99.1.1 へ ping・10.99.2.0/24 がお客さまの VRF に無い・A⇔B 不通のまま |
| M9-4(構築) | インターネット= INET(AS 64500)とグローバルで eBGP。A の両拠点に既定経路・A の公開セグメント 2 つだけをインターネットへ(B は出さない) | INET の BGP に 198.51.100.0/25 と 128/25 だけ・CEA1/CEA2 の公開アドレスから 203.0.113.10 へ ping・CEA2 に既定経路・B に既定経路が無い |

- 配点の案= M9-1 25・M9-2 35・M9-3 20・M9-4 20。
- M9-2 の仕込み(XR02)= 前任者が `route-reflector-client` を **ipv4 unicast の AF の下**に書き、効かないので `retain route-target all` を足した
  (XR02 は全部持っているのに反映しない)。直すと CEA2 には届くが CEA1 には届かない= 2 段目は XR01 の as-override(M9-1 の設定の続き)。
- 別解(挙動で採点するので通る)= retain を残したまま RR クライアントを足す・`allowas-in` は CE を変えるので不可(制約)・M9-3 の輸出 RT を
  `export route-target` に 900 を足す形(全経路に付く= 10.99.2.0/24 も見えて落ちる)・M9-4 の静的経路での受け渡し(拠点 2 に既定経路が届かない形は落ちる)。
- 誤答の想定= M9-3 で additive を付けない(999 が消える)・M9-4 で advertise-as-vpn なし(CEA2 に既定経路なし)・allow-imported-vpn なし(128/25 が INET に出ない)。
- 読み物 M9(日英)= XR の L3VPN の設定の木(RD と RT の置き場・全体の AF が先)・PE-CE と RPL・RT のふるいと RR・as-override(送らない)・ラベルの割り当て方・
  エクストラネット・VRF とグローバル・Inter-AS/CSC(describe)・IF の VRF 変更の注記(§22.6-1)。やってみる= ラベルの割り当て・Route refresh・Failed RT match・静的での受け渡し。

### 22.8 実装の結果(2026-10-27)

- 成果物= `problems/XRT-09`(XR01= XRv9000 26.1.1・XR02= XRd 26.1.1・RT01〜RT03/CE 4 台/SVC/INET= IOL 17.15・課題ごとの確認 `grading.m9t1〜4.yml`・
  最終 `grading.yml`= M9-1 25・M9-2 35・M9-3 20・M9-4 20・`learn.yml`(日英・M9-2 の模範解は「On XR02:」「On XR01:」の 2 塊)・課題文 日英)、
  読み物 `courses/xr/{en,ja}/90-m9-l3vpn.md`(7 節+実践・「やってみる」6 つ・図は `:::topo`)・実践 `91-m9-practice.md`(`course.sh` が課題文から切り出す)・
  本の部に「VPN サービス」を足した(M9。M11 L2VPN もここに入る想定)。
  模範解= `poc/xr/solve_xrt09.sh`(誤答・別解・undo つき)・逐語= `poc/xr/verbatim.py`(★見出し「On XRnn:」で送り先を替えるよう拡張。見出しの無い従来の模範解は従来どおり)・
  E2E= `poc/xr/e2e_xrt09.sh`・やってみるの実測= `poc/xr/try_xrt09.sh`・記録 `poc/xr/expM9-*.log`。
- 実機 E2E= 白紙 0(課題ごと・最終)→ 模範解 100(課題ごと・最終)・learn.yml の模範解を逐語で流して課題ごと・最終とも 100・reset 後 0(XR02 も仕込みへ戻る)。
  誤答= M9-2 で RR だけ直す 55(CEA2 には届くが CEA1 に届かない)・M9-3 で additive なし 85・900 を VRF 全体の export に 70・M9-4 で advertise-as-vpn なし 65・
  allow-imported-vpn なし 50。別解= XR02 の ipv4 の AF と retain を消す形 100・M9-3 で RT をすべて set する形 100。provision 約 12 分。
- **実装で分かったこと**:
  1. 白紙で M9-4 の「B に既定経路が無い」が通った(否定だけの確認)→ B の拠点間の経路があることを同じ確認に入れた(否定の条件は肯定の条件と組にする= README §4 の規則どおり)。
  2. XR の `show bgp … <prefix>` は出力の最後が `Extended community: RT:… ` の行で終わり、採点は末尾の空白を落とす→ RT の後ろは `\s` でなく `(?!\d)` で見る。
  3. ★RT のふるいの「やってみる」は M9-3 の前に限る。M9-3 以降は VRF SVC が 65000:102 も取り込むので、CUST-B から外しても XR01 は B の経路を持ち続ける
     (最初の測定はこれで失敗)。M9-3 の前なら、外した瞬間に捨て、`clear bgp vpnv4 unicast 10.255.0.21 soft in` の後に `Failed RT match: 2`、戻すと自動で Route refresh(送った回数 2→3)・5 秒以内に戻る。
  4. 既定(per-prefix)でも、グローバルから取り込んだ既定経路には VRF の Aggregate ラベル(24009)が付く。`label mode per-vrf` にすると CE の経路も 24009 にまとまる。
  5. as-override を外すと XR01 は拠点 2 の 2 経路を CEA1 から **取り下げる**(送らない動作)。経路に 65101 を含まない 0/0 と 10.99.1.0/24 は送り続ける。
  6. 学習モードの課題文の切り出し(`lab_console._learn_texts`)は 4 本とも日英で取れた。XRv9000 の XR01 と XRd の XR02 が同じラボにあっても採点・reset はそのまま動く。

## 23. M10 セグメントルーティング(SPCOR 3.3)(2026-10-30 完了= 課題 §23.7・ユーザ判断 §23.6・実装の結果 §23.8)

**範囲= SPCOR 3.3(a セグメントの種類・b SR の制御プレーン・c SR-TE・d TI-LFA・e PCE と PCC・f Flex-Algo・g SRv6)**。
§5 の方針どおり、ラボの本線は **a・b・d**(prefix-SID・LDP からの移行・TI-LFA)。**c・e(SR-TE・PCE)は PoC で成り立てば課題にする**かをユーザ判断に回す。
f・g(Flex-Algo・SRv6)は読み物中心(IOL が対応しなければ「やってみる」も XR だけ)。IS-IS の論点= prefix-SID・TI-LFA(§5 の「IS-IS の深め方」②)。
ラボは **`XRT-10`**(XRT-09 を解き終えた状態から= L3VPN のお客さまを載せたまま、コアを LDP から SR に移す筋書き)。
2026-10-29 ユーザが XRT-09 を全通過 → 撤収して PoC(ユーザ了承)。

### 23.1 盤面(PoC= `problems/_POC-XRSR`= XRT-09 の写し+ `PID=_POC-XRSR poc/xr/solve_xrt09.sh` で M9 を解き終えた状態)

- コア= XRT-07 以来の四角形(IS-IS CORE L2・LDP・同期・セッション保護)。XR01(PE・XRv9000 26.1.1)・RT01/RT03(P・IOL 17.15)・RT02(PE・IOL)。
  メトリックは主経路 10(XR01–RT01–RT02)・予備 100(XR01–RT03–RT02)。RT03–XR02 は 10。
- XR02(XRd 26.1.1)= VPNv4 の RR。転送の道に入らない行き止まり= **PCE の候補**(XRd の公式の位置づけ= vRR・PCE。§19.4)。
- お客さま A/B・共有サービス・インターネットは M9 のまま(L3VPN の通信が移行の前後で止まらないことを見る材料)。
- TI-LFA の見込み(机上)= XR01 が XR01–RT01 を守る時、宛先 RT02 は RT03 が素の LFA(100 < 100+20)。宛先 RT01 は RT03 からの戻りが等コスト(110=110)
  で素の LFA にならず、PQ ノード= RT02 → 修復は「RT02 の node-SID を積んで RT03 へ」。RT03–RT02 だけ 100 にして XR01–RT03 を 10 にすると
  P={RT03}・Q={RT02} が離れ、**adj-SID(RT03→RT02)が要る**修復になる(メトリックの置き方は PoC で決める)。

### 23.2 課題(案・PoC の結果で確定する)

| 課題 | 中身(挙動で指定・値は課題文で渡す) | 主な XR の論点 | SPCOR |
|---|---|---|---|
| M10-1(構築) | コアを LDP から SR へ移す。IOS のルータは据付で SR を有効にしてある(LDP と併存中)。XR01 に SR を入れ、お客さまの通信を止めずに SR のラベルへ乗せ替え、最後に XR01 の LDP を止める(SRGB と index は社内の約束を表で渡す) | IS-IS の AF の `segment-routing mpls`・Lo0 の `prefix-sid`・既定は LDP 優先か(`sr-prefer`)・LDP を止めた後の L3VPN | 3.3.a・3.3.b |
| M10-2(TS) | 「XR01 から RT0x への SR のラベルが無い/通信が切れる」。仕込み案= 前任者が XR01 の SRGB を狭めた(相手の index が範囲外)か SID の衝突(PoC で症状を見て選ぶ) | SRGB と index の関係・`show isis segment-routing …` の表示・SRGB の変更の反映(再起動が要るか) | 3.3.a |
| M10-3(構築) | XR01–RT01 のリンクが切れても、お客さまの通信の欠落を最小にする(BFD は M7 の値)。修復の経路は事前に計算しておく | `fast-reroute per-prefix` + `ti-lfa`・修復のラベル(PQ ノード/adj-SID)・`show isis fast-reroute … detail`・CEF の予備 | 3.3.d・IS-IS |
| M10-4(構築・PoC 次第) | お客さま A の通信だけ予備経路(RT03 経由)を通す。B は最短のまま。色で流し込む | SR-TE のポリシー(色・終点・明示の segment-list)・RPL の `set extcommunity color`・automated steering | 3.3.c |
| M10-5(構築・PoC 次第) | XR02 を PCE にし、XR01 の経路の計算を任せる(条件つきの経路)。XR02 は転送に入れない | `pce`・`distribute link-state`・PCC・過負荷ビット(M7) | 3.3.e |

- 読み物だけで扱う見込み= Flex-Algo(IOL の対応次第)・SRv6(IOL は非対応の見込み= locator と uSID の考え方・XR の設定の形)・BGP の prefix-SID(RFC 8669)・
  anycast SID・mapping server と SR-LDP の継ぎ目(PoC で成り立てば「やってみる」)・microloop avoidance。

### 23.3 PoC で確かめること(盤面 `_POC-XRSR`。手順 `poc/xr/sr_poc.sh`・記録 `poc/xr/sr-*.log`)

1. 資源・構築時間。M9 の模範解を流した後、L3VPN が LDP の上で通っていること(出発点)。
2. **IOL 17.15 の SR-MPLS**= `segment-routing mpls`・`connected-prefix-sid-map`・IS-IS の `segment-routing mpls` が通るか。XR01 と SID を交換し、
   互いの転送表に SR のラベルが載るか。IOL の TI-LFA・Flex-Algo・SRv6 の可否(コマンドが通るか)。
3. XR の SR の設定の木= IS-IS の AF に `segment-routing mpls` が無いまま prefix-sid を書いた時・SRGB の既定と変更(再起動が要るか)・範囲外の index の扱い。
4. **LDP と SR の併存**= 既定でどちらのラベルを積むか(XR・IOL それぞれ)・`sr-prefer`・LDP を止めた後も L3VPN が通るか・止める順序の落とし穴
   (IOL 側の LDP 同期= LDP を止めると IS-IS のメトリックが最大になるか)。
5. 範囲外の index・SID の衝突の症状と表示(M10-2 の仕込みを選ぶ材料)。
6. **TI-LFA**= 四角形のメトリックで修復の経路(PQ ノード/adj-SID)がどう計算されるか・IOL が修復のラベルを正しく転送するか・
   CML のリンク条件で切った時の欠落(BFD あり/なし × TI-LFA あり/なし。`login_probe.py` の ping-loss)。
7. microloop avoidance の設定と表示(読み物用)。
8. **SR-TE**= XR01 で明示経路のポリシー(RT03 経由)・BGP の色で CUST-A だけ流し込む(VPNv4 の受け入れで色を付ける)・ODN。IOL は転送だけで足りるか。
9. **PCE**= XR02(XRd)を PCE に・XR01 を PCC に・動的な経路(条件つき)。XR02 に過負荷ビット。
10. Flex-Algo(XR01 と IOL)・SRv6(XR01・XR02 だけ)・mapping server(RT03 の SR を外して XR01 を mapping server に)は時間があれば。

### 23.4 PoC の結果(2026-10-29・XRv9000 26.1.1+IOL 17.15。盤面 `_POC-XRSR`・手順 `poc/xr/sr_poc.sh a…i`・記録 `poc/xr/sr-*.log`・欠落の測定 `poc/xr/sla_loss.py`)

1. **資源・出発点**= 構築 9 分半。M9 の模範解(`PID=_POC-XRSR poc/xr/solve_xrt09.sh`)で L3VPN が LDP の上で通る(XR01 は RT02 へ `{16 22}`= RT01 の LDP ラベル+VPN ラベル)。
2. **IOL 17.15 は SR-MPLS を持つ**= `segment-routing mpls`(下に connected-prefix-sid-map・global-block・local-block・mapping-server・set-attributes)・
   IS-IS の `segment-routing mpls`/`prefix-sid-map`・`fast-reroute`(ti-lfa・remote-lfa)・`flex-algo`・`microloop avoidance`・`distribute link-state` が通る。
   全体に `segment-routing srv6` の項目もある(公式の SRv6 の対応機種一覧に IOL は無い)。既定の SRGB 16000-23999・SRLB 15000-15999。
   adj-SID は動的ラベル(22〜27 など小さい値)。XR の adj-SID は 24011 など。
3. **XR の SR の木**= IS-IS の AF に `segment-routing mpls` が無いまま Lo0 に `prefix-sid index 1` を書くと、コミットで
   「**Feature not supported: Segment-routing is not enabled for IPv4 Unicast**」と拒否(黙った故障にならない= TS の題材にしない)。
   ★`segment-routing mpls` だけ入って prefix-sid を書き忘れると、XR01 は相手へ SR で送れるが、相手は XR01 へ LDP のラベルしか持たない
   (LDP を止めると XR01 へ届かない)= 構築の確認で拾う。
4. **LDP と SR の併存**= XR01 は既定で **LDP のラベルを積む**(SR のラベル 16012 を持っていても `{16}`)。`segment-routing mpls sr-prefer` で `{16012}`。
   IOL は `segment-routing mpls / set-attributes / address-family ipv4 / sr-label-preferred` で SR 優先(RT02 の XR01 向き 16001)。
   IOL は SR を持たない隣(XR01 に SR を入れる前)へは自動で LDP のラベルに継ぐ(RT01 の 16013 の一方が XR01 の LDP ラベル 24001= SR→LDP の継ぎ目)。
5. **★移行の落とし穴= LDP を止めた後の同期**= XR01 で `no mpls ldp` だけにすると、IS-IS の IF に残った `mpls ldp sync` のせいで
   **XR01 自身が両リンクを最大メトリック 16777214 で広告し続ける**。消すと 10/100 に戻る。
   IOS 側(`mpls ldp sync` を全体に持つ)も LDP の相手が消えて同期が外れ、XR01 向きを 16777214 で広告する。
   IOS は**そのリンクの LDP を外せば同期は効かなくなる**(`no mpls ip`= 「LDP not configured」で 10 に戻る・`no mpls ldp igp sync` でも同じ)。
   → XR は「LDP 全体を消しても、IS-IS 側の同期の設定が残る限り未同期」。課題では IOS 側を据付で整え(XR01 向きの LDP を外す)、XR01 の同期の消し忘れを確認で拾う。
   最大メトリックでも XR01 へは他に道が無いので L3VPN は通る(黙った不具合= TI-LFA の計算や予備経路の選択が狂う)。
6. **SRGB の変更**= XR01 の `segment-routing global-block 16000 16009` は**再起動なしで約 5 秒で反映**(ISIS の SRGB_INFO「disabling SR」→「enabling SR」)。
   BGP は `%ROUTING-BGP-2-SR_CFG_CHANGED … 'process restart bgp' needed` を出す(BGP の prefix-SID を使う時だけ関係)。
   狭めると相手の index 11〜13 が自分の範囲外= XR01 は自分の入ラベルを作れず **相手への SR のラベルを積まない**(`show isis segment-routing label table` から消える)。
   LDP を止めた後なので RT02 への /32 はラベルなし= VPN の経路は **unresolved・drop**(CEA1→CEA2 は `U.U.U.`)。RT01 は `%CLNS-4-SIDRANGE … out of SRGB range 10 via 10.0.1.1` を出す。
   戻すと即座に復旧。= **M10-2 の TS の第一候補**(症状= お客さまの通信が止まる・XR01 のラベル表に相手が無い・相手の DB の SRGB と自分の SRGB の食い違い)。
7. **SID の衝突**(RT03 の Lo0 に RT02 と同じ index 12)= XR01 はラベル表に「`label conflict: 16012 10.255.0.13/32`」・syslog
   「Label Conflict: Prefix-SID label 16012 for algo SPF is used by 10.255.0.12/32 and 10.255.0.13/32」。**XR01 は 10.255.0.12 を採り** RT03 をラベルなしにした
   (RFC 8660 §2.5.1 の「数値の小さい FEC が勝つ」どおり)。★**IOL(RT01)は 10.255.0.13 を採った**(RT02 の対応を捨てた)= XR01 が RT02 宛に積んだ 16012 を
   RT01 が RT03 へ流し、L3VPN は 0%。**RFC と IOL の実装が食い違う**(§23.5・ユーザ判断)。
8. **相手の SRGB を超える index**(XR01= 9000)= コミットは通る。XR01 自身の範囲(8000)も超えるので自分のラベル表からも消える。RT01 は XR01 宛を
   「No Label」(LDP は止めた後)にし、XR01 へ届かない。
9. **TI-LFA**(XR01 の両コア IF に `fast-reroute per-prefix` と `… ti-lfa`)= 保護率 100%。机上どおり= 宛先 RT01 は
   「TI-LFA (link)・P node RT02・Label 16012・Prefix label 16011」(CEF の予備 `{16012 16011}`・Repair Node 10.255.0.12)、宛先 RT02 は素の LFA(Local-LFA)、
   宛先 RT03 は RT01 経由で P node RT02。VPN の経路は /32 の保護をそのまま使う(再帰)。
10. **欠落の測定**(CEA1 の udp-jitter 10 ms 間隔・XR01–RT01 にリンク条件 loss 100。BFD は XR01⇔RT01 で 100 ms × 3、echo で検出)=
    TI-LFA なし 42 個(約 420 ms)・あり 34〜40 個。**この盤面では XR の再計算が速く(検出後 約 100 ms)、差は検出時間に埋もれる**。
    CML のリンクを止めても(キャリア断)XRv9000 の IF は落ちず、検出は BFD の「Echo function failed」= リンク条件と同じ。
    BFD を縮めてくり返すと BFD が dampening に入り(初回 2000 ms・次 5000 ms)、測定が乱れる。→ **採点は修復経路の状態で見る**(欠落では見ない)。
11. **SPF を遅らせた比較**(XR01 に `spf-interval initial-wait 1000 secondary-wait 1000 maximum-wait 5000`・BFD 100 ms × 3・隣接と BFD の Up を待ってから測る)=
    TI-LFA なし 342・467 個(**3.4〜4.7 秒**)/あり 41・34 個(**0.34〜0.41 秒= BFD の検出時間だけ**)。
    → 大きな網の再計算の遅さを SPF の待ちで模すと効き目がはっきり出る= 読み物の「やってみる」に使う(課題の採点には使わない)。
12. **IOL の TI-LFA**(RT01 の `router isis` に `fast-reroute per-prefix level-2 all` と `fast-reroute ti-lfa level-2`)= 隣接が安定していれば保護率 77%。
    XR01 宛は「TI-LFA link-protecting・P node RT03(16013)・RT02 へ」(`show isis rib`)・自動の修復トンネル MPLS-SR-Tunnel。`mpls traffic-eng tunnels` は要らない。
    IOL は既定で「Microloop Avoidance Enable State: enabled for segment-routing」と表示する。★最初の 0% は XR01 の隣接が落ちていた間に見たため(下の 14)。
13. **adj-SID の要る修復**(XR01–RT03 を両側 10・RT03–RT02 は 100)= 机上どおり「P node RT03(ImpNull)・**Q node RT02・Label 23**(RT03→RT02 の adj-SID)」・
    CEF の予備 `{ImplNull 23 16011}`。宛先 RT02 も同じ形(`{ImplNull 23}`)。欠落 28 個× 2 回(約 280 ms= 検出時間)。
14. **★XR の BFD dampening**= 落とすたびに抑止が延び(初回 2000 ms・次 5000 ms… ここでは約 2 分)、その間は隣接が戻らない
    (`show bfd session` で `DOWN DAMP`)。`bfd / dampening disable` で切れる。採点で故障を起こすなら効く(M10 は状態で採点するので起こさない)。
15. **microloop avoidance**(XR01)= `microloop avoidance segment-routing`・`rib-update-delay 3000` がコミットでき、`show isis protocol` に
    「Microloop avoidance: Enabled / Configuration: Type: Segment Routing, RIB update delay: 3000 msec」。
16. **SR-TE**= 明示経路(`segment-list` に 16013・16012)のポリシー 色 100 は即 up(binding SID 24003)。VPNv4 の受け入れ(RR からの neighbor-in)で
    RT 65000:101 の経路に色 100 を set すると CUST-A だけがポリシーに乗る(`show bgp vrf` に `C:100 (bsid:24003)`・CEF が `srte_c_100_ep_10.255.0.12`)。
    CEA1 の traceroute は 2 番目が 10.0.3.13(RT03)、CEB1 は 10.0.1.11(RT01)のまま。IOL は転送だけで足りる。
17. **★ODN の落とし穴**= `on-demand color 100 dynamic`(自分の IF に affinity・exclude-any)は、IS-IS に **`distribute link-state` が無いと
    「Last error: Source node not found in topology」で down**、通信は**黙って IGP の最短経路に戻る**(CEF は {16012 22} で RT01 経由)。
    足すと即 up(16013・16012)。ODN は自動で 2 つの候補(優先 200= 自分で計算・100= PCE に委任)を作る。
18. **★VRF の import での色**= 公式(SR-TE 章の RPL の付け先の表)は「VRF import は match だけ」だが、26.1.1 は `vrf CUST-B / address-family ipv4 unicast /
    import route-policy`(`set extcommunity color`)を**コミットでき、色が付き、流し込みも効いた**(`SR policy color 100, up, registered`・CEB1 の traceroute が RT03 経由)。
    **公式と実機の食い違い**(§23.6)。neighbor-in で付けた時の表示は `not-registered` だったが、CEF は流し込まれていた。
19. **PCE**(XR02= XRd に `pce / address ipv4 10.255.0.21` と IS-IS の `distribute link-state`・XR01 を PCC)= PCE のトポロジに 5 ノード・prefix-SID 4・adj-SID 13
    (起動直後 40 秒は「Ready: no」)。色 201・202 の 2 本に `disjoint-path group-id 1 type link` を付けて `dynamic / pcep` にすると、PCE が
    **201= RT01 経由(16012)・202= RT03 経由(16013・16012)**に分けた(`show pce association`= Link-Disjoint・Satisfied)。XRd で PCE は成立(転送しない役)。
20. **Flex-Algo**(XR01 に `flex-algo 128 / advertise-definition`・Lo0 に `prefix-sid algorithm 128 index 101`)= 遅延(`metric-type delay`)はどのリンクも
    遅延を広告していないので経路ができない。IGP メトリックに替え、IOL 3 台にも `router isis / flex-algo 128` と `connected-prefix-sid-map / address-family ipv4 algorithm 128`
    を入れると、**IOL も参加して algorithm 128 のラベル(16111〜16113)を作る**。参加しない XR02 は除外(`show isis topology flex-algo 128` で `**`)。
    → 盤面で Flex-Algo のラボも成り立つ(affinity での除外は未測)。
21. 測っていないもの= SRv6(コアに IPv6 が無い。IOL にコマンドはあるが公式の対応機種一覧に無い)・mapping server(SR を持たない隣が要る)・anycast SID。読み物で扱う。

### 23.5 公式文書・RFC での裏どり(2026-10-29・PoC と並行。xrdocs.io は取得していない・問題集サイトは使っていない)

参照= Segment Routing Configuration Guide for ASR 9000, IOS XR 26.1.x–26.3.x(2026-09-11 更新・以下 CG)/Segment Routing Command Reference for ASR 9000(2025-12-17 更新・以下 CR)/
SR Configuration Guide for Cisco 8000 24.x の IS-IS 章/TechNote 215215「Segment Routing Overview and Migration Guidelines」(2020)/
IOS XE Segment Routing Configuration Guide(2026-09 更新・版の表記なし)/IOS XE 17.x IP Routing CG「SR with IS-IS v4 Node SID」/IOS XRd Data Sheet(2026-04)/
RFC 8402・8660・8661・8664・8667・9256・9350・9855(TI-LFA・2025-10)/Cisco Live EMEA 2025 BRKSPG-3624・EMEA 2026 BRKSP-2551(信頼順 1.5)。抽出は作業場所(リポには置かない)。

| 論点 | 文書 | 実機(§23.4) | 扱い |
|---|---|---|---|
| SRGB/SRLB の既定 | CG: 16000–23999/15000–15999。`segment-routing global-block`・`local-block`。IGP でなく `segment-routing` の下に書くのを推奨 | 一致(XR・IOL とも) | — |
| SRGB の変更 | CG:「変更は通信を乱し、新しい範囲が全部空いていなければ再起動が要ることがある」。空いている時に即時かは明記なし | 空いていれば約 5 秒で即時(ISIS の SRGB_INFO)。BGP は process restart を求めるログ | 実機で補う |
| prefix-SID の形 | CG/CR: IS-IS の IF の AF に `prefix-sid [algorithm N] {index\|absolute} [n-flag-clear] [explicit-null]`。既定で N フラグ | 一致(N:1) | — |
| `segment-routing mpls` なし | CR:「IS-IS のインスタンスに SR が要る」とだけ | コミットで拒否(Feature not supported) | 実機で補う |
| SR と LDP の既定 | 現行の CG/CR に既定の記述なし。TechNote「Cisco の実装は常に LDP 優先」・RFC 8661 §6.1「既定は LDP を選ぶべき」。`sr-prefer` | 既定 LDP・sr-prefer で SR | 一致(TechNote・RFC) |
| IOS XE の SR 優先 | XE SR CG: `set-attributes / address-family ipv4 / sr-label-preferred` | 一致 | — |
| 範囲外の index | RFC 8402 §3.1.2「使ってはならず、エラーを記録すべき」・RFC 8660 §2.4/§2.10.1。IOS XE CG: 範囲外はラベルを使わない。XR は記述なし | XR は黙ってラベル表から外す(ログなし)・IOL は SIDRANGE のログ | 実機で補う |
| SID の衝突 | RFC 8660 §2.5.1: 既定の決め方(管理距離→ FEC の数値の小さい方)を実装すべき(SHOULD)・別の決め方も可(MAY)・**運用者は同じ領域に同じ決め方のルータを置かなければならない(MUST)**。XR の決め方・表示は記述なし | XR は 10.255.0.12(RFC の既定どおり)・**IOL は 10.255.0.13** | ★食い違い(XR と IOL)。RFC は許すが混在で通信が止まる= 読み物の題材。TS には使わない案(結果が実装に左右される) |
| adj-SID | CG: 動的は動的ラベルの範囲から・再起動で変わる。手動は SRLB から・P2P のみ・既定は保護なし | XR 24011 など・IOL 22〜27 | — |
| mapping server | CG: `segment-routing mapping-server prefix-sid-map` + IS-IS `segment-routing prefix-sid-map advertise-local`(既定は広告しない)。SRMS が要るのは SR→LDP の向きだけ(CG・RFC 8661 §3.1.1。TechNote は LDP→SR にも要ると書く) | 未測(IOL は SR を持たない隣へ自動で LDP に継ぐのを確認) | 読み物(食い違いは注記) |
| TI-LFA の設定 | CG: IF の AF に `fast-reroute per-prefix` と `fast-reroute per-prefix ti-lfa` の 2 行。前提は IS-IS の SR。修復のラベルが 3 枚までは IGP が直接・それを超えると自動の SR-TE(`ipv4 unnumbered mpls traffic-eng Loopback` が要る) | 2 行で保護率 100%(修復は 2 枚以内) | 一致 |
| TI-LFA の既定の保護 | CG: リンク保護。ノード保護・SRLG はタイブレーカで有効化(既定は無効)。XE: node-protecting は既定で無効、srlg-disjoint などは既定で有効 | XR は TI-LFA (link) | 一致 |
| TI-LFA の効き目 | CG/Cisco Live: 検出 BFD で 20–50 ms・切り替え 50 ms 未満・IGP の再収束 約 500 ms。XE CG「50 ms は保証できない」 | 検出(BFD 300 ms)が支配的。再計算が速い盤面では差が小さい | 採点は状態で・やってみるは SPF を遅らせて |
| microloop avoidance | CG: `microloop avoidance segment-routing` 既定は無効・`rib-update-delay` 既定 5000 ms | 一致(§23.4-15)。IOL は既定で有効と表示 | M10-3 に足す案 |
| SR-TE | CG: ポリシーは (色・終点)。明示経路は `segment-list / index N mpls label L`。**head-end は IGP の IF を p2p にし、`distribute link-state` を入れてから**。色の set は neighbor-in/out・VRF export などで可 | 明示経路は distribute link-state なしでも up・**動的(ODN)は無いと down で黙って最短経路へ**(§23.4-16・17) | 一致(落とし穴として使う) |
| 色を付ける場所 | CG の RPL の付け先の表: **VRF import は match だけ**(set 不可) | **26.1.1 は VRF import の set がコミットでき、流し込みも効く**(§23.4-18) | ★食い違い(ユーザ判断)。採点は挙動で(付ける場所を問わない)案 |
| PCE | CG: `pce / address ipv4`・IGP の `distribute link-state` か BGP-LS でトポロジ。PCC は `segment-routing traffic-eng pcc / source-address / pce address`。「SR-PCE には XRv9000 を推奨」。データシート: XRd Control Plane は vRR・PCE 向け | XRd で成立・リンクで離す計算も Satisfied(§23.4-19) | 一致。XR02 は XRd のまま |
| Flex-Algo | CG: `flex-algo 128-255`・定義を広告しないと働かない・遅延を広告しないリンクは除外・Flex-Algo の経路は MPLS→MPLS のエントリだけ(IP→MPLS は入らない)。XE CG: 17.3.1 から(対応機種の一覧なし) | 遅延の定義は経路なし・IGP の定義で IOL も参加(§23.4-20) | 一致。ラボ化はユーザ判断 |
| SRv6 | CG: locator と uSID(f3216)・通過ノードは IPv6 の転送だけ。XE CG: 17.12.1a から・対応機種は ASR1000/C8000 系のみ(IOL は記載なし) | IOL にコマンドはある(未測) | 読み物 |

### 23.6 ユーザ判断(2026-10-29 決定= 1〜3 とも案どおり。1= 5 本で実装・Flex-Algo は読み物+やってみる/2= 挙動で採点・注記/3= 読み物だけ)

1. **課題の範囲**= §23.7 の 5 本(SR 移行+SRGB の TS/LDP の撤去/TI-LFA/SR-TE(ODN)/PCE)で実装するか。Flex-Algo は IOL も参加できる(§23.4-20)が、
   M10 では読み物+「やってみる」に留め、課題化は 2 周目(BL-257)に回す案。
2. **★公式と実機の食い違い= 色を VRF の import で付ける**(公式は「match だけ」・26.1.1 は set が効く。§23.4-18)。案= **採点は挙動で**(CUST-A がポリシーに乗る・B は乗らない)、
   付ける場所は問わない。模範解は公式の付け先(RR からの受け入れ= neighbor-in)にし、読み物に「文書の表と 26.1.1 の挙動」を注記。
3. **SID の衝突で XR と IOL が別の側を採る**(XR= RFC の既定どおり・IOL= 逆。RFC は別の決め方も許すが、運用者に揃えることを求める)。案= 読み物の題材にし、TS にはしない
   (結果が実装に左右される)。M10-1 の TS は決定的な SRGB の食い違いにする。
4. 機種= XR01 は XRv9000(BFD・TI-LFA の転送)・XR02 は XRd(PCE。設定ガイドは SR-PCE に XRv9000 を推すが、XRd のデータシートは PCE 向けと書き、PoC で成立)。
5. TI-LFA は**状態で採点**(修復経路の計算・CEF の予備)。この環境では BFD の検出時間が支配的で欠落の差が出ず、故障を起こすと BFD の dampening で後が乱れるため。

### 23.7 課題の確定案(2026-10-29・§23.6 の決定を受けて)

**初期状態**= XRT-09 を解き終えた状態(L3VPN が LDP の上)+ IOS 側は SR の準備済み(据付= RT01〜RT03 に SR・index 11〜13・`sr-label-preferred`・
IOS どうしの LDP は残す・**XR01 向きの IF は LDP の同期を外してある**= §23.4-5)。XR01 に仕込み= 前任者の SRGB 16000-16009(CHG のコメントつき)。
XR02(RR・XRd)は M9 の模範解のまま。ラボ ID は `XRT-10`。

| 課題 | 中身(挙動で指定・値は課題文で渡す) | 確認(案) | 配点 |
|---|---|---|---|
| M10-1(構築+TS) | XR01 を SR に参加させる(Lo0 の index 1・SRGB は社内の約束= 16000-23999)。XR01 発着のラベル付きの通信を SR のラベルで運ぶ。LDP は切り戻し用に残す。仕込み= 前任者の SRGB(相手の index が範囲外で SR のラベルができず、XR01 は LDP のまま) | XR01 の LSP に SRGB 16000/8000 と prefix-SID 1・XR01 の RT02 向きが {16012}・RT02 の XR01 向きが 16001・LDP の隣接 2 つが残る・両お客さまの拠点間 ping | 30 |
| M10-2(構築) | 切り戻しの期限が過ぎた。XR01 の LDP を止める(IOS 側は待っている) | XR01 に LDP の隣接なし・**XR01 の LSP のメトリックが 10/100**(同期の消し忘れ= 16777214 を拾う)・ping | 15 |
| M10-3(構築) | XR01 のコアの両リンクに、切れた瞬間に使う予備経路を事前に計算させる(リンク保護)。経路が切り替わる間の一時的なループも避ける | FRR の保護率 100%・RT01 の Lo0 の予備が TI-LFA で P ノード RT02・RT02 の Lo0 に予備・microloop avoidance(SR)が有効 | 20 |
| M10-4(構築) | お客さま A の拠点間の通信だけ、XR01–RT01 のリンクを避けて通す(RT01 の保守に備える)。B は最短のまま。経路は XR01 が計算する(固定の経路を書かない)。色 100 は社内の約束 | A の経路に色 100 とポリシー up・ポリシーが動的・CEA1 の traceroute の 2 番目が RT03・CEB1 は RT01 | 20 |
| M10-5(構築) | XR02 を PCE にし、XR01 の 2 本の経路(色 201・202・終点 RT02)を互いにリンクを共有しないように PCE に計算させる | PCEP の隣接・2 本が up で計算元が PCE・片方が RT03 経由・PCE の association が Satisfied | 15 |

- 落とし穴(PoC で確認済み)= SRGB の範囲外(ラベル表から黙って消える)・`sr-prefer` なしは LDP のまま・同期の消し忘れで最大メトリック・
  ODN は `distribute link-state` なしで黙って最短経路・PCE も `distribute link-state` が要る。
- 読み物 M10(日英)= SR の考え方(SID の種類・SRGB と index・PHP)・XR の設定の木・LDP との併存と移行・TI-LFA(P/Q ノード・adj-SID・
  「やってみる」= SPF を遅らせて差を見る §23.4-11)・microloop・SR-TE(色・ODN・BSID)・PCE・Flex-Algo(やってみる)・SRv6(考え方と XR の形)・
  SID の衝突と mapping server(describe)。

### 23.8 実装の結果(2026-10-30)

- 成果物= `problems/XRT-10`(XR01= XRv9000 26.1.1・XR02= XRd 26.1.1・RT01〜RT03/CE 4 台/SVC/INET= IOL 17.15・`initial/XR01.commits.yml`= CHG-1301 の SRGB の仕込み・
  課題ごとの確認 `grading.m10t1〜5.yml`・最終 `grading.yml`= M10-1 30・M10-2 15・M10-3 20・M10-4 20・M10-5 15・`learn.yml`(日英)・課題文 日英)、
  読み物 `courses/xr/{en,ja}/a0-m10-segment-routing.md`(9 節+実践・「やってみる」7 つ・図は `:::topo`)・実践 `a1-m10-practice.md`(`course.sh` が課題文から切り出す)・
  本の章番号は "A0"(2 桁に収まらないので英字始まり= 章とファイル名の並びを M9 の後ろに保つ)・部は「SP の中核」に入れた。
  模範解= `poc/xr/solve_xrt10.sh`(誤答・別解つき)・E2E= `poc/xr/e2e_xrt10.sh`・記録 `poc/xr/expM10-*.log`。
- 初期状態= XRT-09 の M9 の模範解を XR01/XR02 の初期設定に焼き込み、IOS 側に SR の準備(SRGB 既定・index 11〜13・`sr-label-preferred`・TI-LFA・
  Flex-Algo 128 に参加(index 111〜113・定義は持たない= 読み物の「やってみる」用)・XR01 向きの IF は `no mpls ldp igp sync` と BFD 100 ms × 3)。XR01 にもコアの BFD。
- 実機 E2E= 白紙 0(課題ごと 5 本・最終)→ 模範解 100(課題ごと・最終)。誤答= SRGB を直さない 20(RT02→XR01 の 16001 だけ通る)・sr-prefer なし 55・
  同期の消し忘れ 65・素の LFA だけ 20(保護 3・未保護 4)・distribute link-state なし 0・離す条件なし 50(2 本とも RT01 経由)・PCE にトポロジなし 25(2 本とも down)。
- **実装で分かったこと**:
  1. ★`xr_reset.py` の記録がラベル付きのコミット(commits.yml の CHG-1301)を飛ばし、1 つ前の ZTP の回を戻り先にしていた
     (`show configuration commit list` はラベルの付いた回を ID でなくラベルで表示する)→ `list detail` の `CommitId:` を読むよう修正。
     履歴を仕込む XRT-01 のやり直しにも潜んでいた不具合(XRT-01 は reset の導入前に作ったので表に出ていなかった)。
  2. LDP や VPN のラベルの値は構築ごとに変わる(PoC は LDP 16・VPN 22、XRT-10 は 18・26)= 学習モードと読み物の説明は値に頼らない書き方にした。
  3. ★M10-5(PCC)の後は、`distribute link-state` を外しても ODN のポリシーは down にならない= 優先度 100 の PCE に委任した候補パスが引き継ぎ、
     RT03 経由のまま(PCE は XR01 のリンクの affinity を知っていて避けた)。読み物の「やってみる」は M10-4 の後・M10-5 の前に行うよう書き、
     M10-5 の後の挙動も書き添えた。
  4. Flex-Algo のアフィニティは広告する側の向きだけに効く= XR01 側の PRIMARY だけに RED を付けると、XR01 の algorithm 128(16112)は RT03 経由になるが、
     RT01 は XR01 宛てに PRIMARY を使い続ける(`show isis topology flex-algo 128`)。
  5. M10-4 の後は顧客 A が PRIMARY を通らないので、TI-LFA の測定(4.3 の「やってみる」)は顧客 B で行う。
  6. **やり直し・逐語・別解**= `lab.sh reset` 後に白紙 0(XR01 は CHG-1301 の後へ・XR02 は first-boot へ)・learn.yml の模範解を逐語で流して課題ごと 5 本と最終とも 100・
     別解(`global-block 16000 23999` と書く・色を VRF の import で付ける)100・誤答(固定の経路= 明示の segment-list)は M10-4 で 75。
  7. **「やってみる」の測り直し**(解く側と同じ手順。記録 `poc/xr/expM10-try*.log`)= 2.3 ブロックを縮める(両顧客 0%・ポリシーも unresolved first label で down・RT01 に SIDRANGE)/
     3.1 sr-prefer を外す(15 秒で LDP の `{18}` に戻る)/3.2 同期を 1 本戻す(そのリンクだけ 16777214・RT02 のルートは変わらない)/
     4.3 SPF の初回待ちを 5 秒にして顧客 B の ping(TI-LFA あり 1 個・なし 6 個の欠落、各 2 回。1 秒の待ちでは 1 対 2 で差が見えにくかったので 5 秒にした)/
     5.3 distribute link-state を外す(M10-5 の前は down で RT01 経由へ・後は PCE の候補が引き継ぐ= 本文 3.)/6.2 離す条件を外す(2 本とも RT01 経由・グループが消える)/
     7 Flex-Algo(16112 が RT03 経由・RT01 は PRIMARY のまま= 本文 4.)。
  8. 4.3 の表の「SPF を 1 秒遅らせる」の PoC の値(3.4〜4.7 秒)は、変化が続くと待ちが最長 5 秒まで伸びる設定での値= 表に「1 秒、最長 5 秒まで伸びる」と書いた。

### 23.9 読み物の改稿(2026-10-30・ユーザ指摘)

- **指摘**: 「SR は読み物の内容が別次元に難しい」「何が嬉しいのか・どんな問題が解決できるのかがあれば分かりやすい。どういう仕組みでルーティングを
  制御できるのかを噛み砕いてほしい」。
- **原因の見立て**: M3〜M9 は ENARSI で知っている技術の「XR ではこう」で足りたが、SR・TI-LFA・SR ポリシー・PCE は概念そのものが初出なのに
  同じ密度で 1 ページ(51 KB・ブループリント 7 項目)に詰めた。1 段落に新語が 7〜8 個(旧 4.1)、図はトポロジ 1 枚だけ、RFC の節番号・PoC の細部・
  IOS XE との違いが概念の説明に混ざっていた。
- **直し方**: 3 ページ+付録に分割(M4・M8 と同じ形)。各ページの 1 節を「何が嬉しいのか」にし(困りごと→ SR 以前の手→ SR の答え)、仕組みは
  ラボの四角形の上でラベルを 1 ホップずつ追う(図= `:::topo` の線にリンク上のラベルを書く。根拠= PoC の traceroute `16012/24`(RT01 経由)・
  `16012/22`(RT03 経由)= `poc/xr/sr-fg.log`)。TI-LFA は「隣に渡すだけだと送り返される(RT03 から RT01 が 110 対 110)」→「経由地を 1 つ足す」の順。
  ページ= `a0-m10-segment-routing`(何が嬉しいか・仕組み・XR の設定・LDP からの移行= 課題 1・2)/`a2-m10-ti-lfa`(課題 3)/`a4-m10-sr-policy-pce`(課題 4・5)/
  `a6-m10-appendix`(Flex-Algo・SRv6・SID の衝突)。実践ページも 3 枚(`a1`・`a3`・`a5`)= `course.sh` の practice.yml に `tasks:`(課題で絞る)を足した。
  「やってみる」7 つと測定値・出力は旧ページのまま移した。learn.yml の read: と解説の節番号、task.md/task.en.md の冒頭の案内を新しいページに合わせた。
  ラボ・採点は変えていない。日英は見出し・段落・表・囲みの数を一致させてビルド(警告なし)・Drive 同期済み。

### 23.10 設定例の後付け(2026-10-31・ユーザ指示= 以後の教材の恒久方針・CLAUDE.md §6)

- **指示**: 「それは何か・何が嬉しいか・どう設定するかを根本的にもっと懇切丁寧に、config 例も常に提示して」「config の例が無いので自分で
  調べることになるが、まとまった形で見せてもらわないと知識が断片化する」。決定(AskUserQuestion)= 設定例は盤面の上で書き、課題は写しで終わらない
  ようひねる/既存は M10 から今すぐ(M0〜M9 は BL-257 の書き直しで)。
- **記法**: `topologies/gen_reading.py` に `:::config <見出し>` / `:::config fold <見出し>`(左に設定の行・右に行末 `  ## 注記` の列・狭い画面では注記を
  行の下へ・コピーのボタンと手での選択は設定の行だけ・http の配信でも写せるよう textarea に落とす)。見出しは増やしていない(節の番号= learn.yml の read: を保つ)。
- **中身と根拠**(すべて実測): a0 §3.1= XR01 の最小形(fold・M10-1 に近い)+ RT02 の IOS XE(据え付けの設定)/§4.2= 移行後の IS-IS 全体(fold・M10-1/2)。
  a2 §2.5= XR01 の TI-LFA(fold・M10-3)+ RT01 の IOS XE/§4= microloop(fold・`rib-update-delay 3000` は §23.4-15)。a4 §2.1= 明示経路のポリシー
  (§23.4-16・`poc/xr/sr-fg.log`。課題は道順を書かせないので答えではない=畳まない)/§2.2= カラー付け(fold・M10-4)/§2.3= ODN(fold・M10-4)/
  §3.1= PCE と PCC(fold・M10-5)/§3.2= 離した 2 本(fold・M10-5。形は `poc/xr/sr-hi.log` の running-config)。RPL の「通すとも変えるともしなかった
  ルートは捨てる」(既定の drop)は XRT-10 の実機でも確認(`pass` の無い受け入れのポリシーで顧客 B のルートが denied・2026-10-31)。
- XRT-10 の task.md/task.en.md の「コマンド例は示しません」を「課題の中には示さない・読み物の設定例は答えと同形なら畳んである」に書き換えた。

## 24. M11 L2VPN とキャリア イーサネット(SPCOR 4.2・4.1.a)(2026-11-01 完了= 課題 §24.7・ユーザ判断 §24.5・§24.5b-8・実装の結果 §24.8)

**範囲= SPCOR 4.2(a イーサネット サービス E-Line・E-Tree・E-Access・E-LAN/b 802.1ad・802.1ah・G.8032/c イーサネット OAM/d VLAN タグの操作)
と 4.1.a EVPN**。2026-11-01 ユーザが XRT-10 の M10-1〜5 を全通過 → 撤収・M10 の設定例の後付けをコミット(58b8100)→ PoC(ユーザ指示)。
この単元から CLAUDE.md §6 の書き方(技術そのものから丁寧に・機能ごとの設定例を `:::config` で)で最初から書く。

### 24.1 PoC の盤面(`problems/_POC-XRL2VPN`・手順 `poc/xr/l2vpn_poc.sh`・記録 `poc/xr/l2vpn-*.log`)

- コア= XRT-07 以来の四角形(IS-IS CORE L2・LDP・同期。PoC ではパスワードとセッション保護を省いた素の形)。RT01/RT03= P(IOL 17.15)。
- PE を 4 台= **XR01・XR02(どちらも XRv9000 26.1.1)**・**XR03(XRd 26.1.1)**・**RT02(IOL 17.15)**。XR02 は RT03 の先、XR03 は RT01 の先。
  XRv9000 を 2 台(同時の上限)並べたのは、EVPN のマルチホーム(1 台の CE を 2 台の PE に収容)と XR 同士の EVPN を同じ盤面で見るため。
- CE= CE1(XR01)・CE2(RT02)・CE3(XR03)・CE4(XR02)は IOL ルータのサブインタフェースで VLAN を出し分ける(サービスごとに 192.168.<VLAN>.0/24・
  ホスト部= CE の番号。CE4 だけ E-LAN を VLAN 201 で出す= タグの付け替えを見る材料)。SW1(IOL-L2)= XR01 と XR02 に LACP の束で二重に収容。
- 資源= CML ホスト 50.6GB のうち 撤収後の空き 48.8GB(XRv9000 2 台で約 40GB)。

### 24.2 PoC で確かめること

1. **機種の見極め**: XRd(Control Plane 版)が l2transport のサブインタフェース・疑似回線・ブリッジ ドメインを受け付け、フレームを転送するか
   (L3 では PE の向きで TCP/UDP を壊した= §22.4)。XRv9000 の L2VPN(LDP の疑似回線・EVPN-VPWS・EVPN の E-LAN・VPLS)の可否。
2. **IOL 17.15 が相手の PE になれるか**: EVC(service instance)・`l2vpn xconnect context`・サブインタフェースの `xconnect`・VPLS(`l2vpn vfi context`)・
   EVPN(`l2vpn evpn instance`)・CFM。CE の IOL が二重タグ(Q-in-Q)のサブインタフェースを作れるか。
3. **E-Line(LDP の疑似回線)XR01⇔RT02**: 疑似回線が上がるか・VC タイプ(4 か 5)の既定と食い違い・MTU と control word の食い違いの症状(TS の候補)。
4. **EVPN-VPWS XR01⇔XR02**: BGP の l2vpn evpn・source/target の食い違いの症状。
5. **E-LAN**: EVPN の EVI を付けたブリッジ ドメイン(XR01・XR02)・VPLS(XR01⇔RT02)・タグの付け替え(CE4 の VLAN 201)・MAC の学習の表示。
6. **EVPN のマルチホーム**: SW1 を all-active/single-active で収容(ESI・LACP の system ID)・片方の PE を落とした時の挙動。IOL-L2 の LACP が XR の束と組めるか。
7. **E-OAM**: CFM(MEP・CC・ループバック・リンクトレース)・Y.1731 の遅延の測定。IOL 側の CFM の可否。
8. 読み物向けの確認(時間があれば): E-Tree(EVPN の leaf)・802.1ad(dot1ad のカプセル化)・G.8032・PBB-EVPN が XRv9000 で設定として通るか。

### 24.3 PoC の結果(2026-11-01・XRv9000 26.1.1×2+XRd 26.1.1+IOL 17.15。手順 `poc/xr/l2vpn_poc.sh a…i`・記録 `poc/xr/l2vpn-*.log`)

**機種の見極め(いちばん大きい結果)**
1. **XRv9000 は VPWS(ポイント ツー ポイント)だけ**。ブリッジ ドメインはローカル(AC だけ)でもコミットで拒否
   (`VPLS Bridge domains not supported on this platform`・EVI を付けると `Maximum EVI BD configuration reached`)。`show l2vpn capability` も
   `VPLS allowed: N`・`VPWS allowed: Y`(`Bundle AC supported: Y`・`VPWS PW redundancy supported: Y`)。→ **E-LAN(VPLS・EVPN E-LAN)・E-Tree・
   EVPN のマルチホーム(相手の PE が足りない)は XR で手を動かせない**(l2vpn-e.log・l2vpn-e3.log)。
2. **XRv9000 26.1.1 に CFM が無い**(`ethernet cfm` が構文ごと無い・パッケージ一覧に該当なし)。XRd も同じ。IOL ルータの CFM は service が
   `evc`/`port` だけで、CE のサブインタフェースと同じ VLAN の EVC が作れない(`The VLAN ID (100) has already been configured`)・service instance の下に
   MEP を置けない → **E-OAM(CFM・Y.1731)は読み物**(l2vpn-g.log・g2b・g2d)。
3. **XRd(Control Plane 版)は L2 を転送しない**。l2transport のサブインタフェースと LDP の疑似回線は受け付け、疑似回線は up(PW type Ethernet・
   ラベル交換済み)になるが、AC の受信 0・CE の ARP が Incomplete。rewrite を外しても同じ(l2vpn-b.log・b4・b5)。**ルート リフレクタとしては使える**
   (XR03 を l2vpn evpn の RR にして XR01⇔XR02 の EVPN-VPWS が成立)。
4. **IOL 17.15** は EVC・`l2vpn xconnect context`・`interface pseudowire`・VFI・`l2vpn evpn instance`(point-to-point/vlan-based)・CFM の構文をすべて受け付ける
   (l2vpn-p.log)。**LDP の疑似回線は XRv9000 と相互に通る**(PW type Ethernet・ping/TCP 可)。**EVPN-VPWS は制御だけ通り、データは XR→IOL の向きが
   IOL で捨てられる**(IOL の Rx drops が増える・IOL→XR は届く)。IOS は L2 属性の拡張コミュニティ(0x604)を付けず、control word のつまみも無い。
   XR の pw-class の control-word は EVPN-VPWS に当てられない(`EVPN VPWS doesn't support this pw-class config`)。→ **EVPN は XR 同士だけ**(l2vpn-d2*.log)。
   CE の IOL は二重タグ(`encapsulation dot1Q 400 second-dot1q 10`)のサブインタフェースを作れる。

**E-Line(LDP の疑似回線)XR01⇔RT02**(l2vpn-c.log・c3)
5. XR は AC に `rewrite ingress tag pop 1 symmetric` → 既定で PW type Ethernet(タイプ 5)・control word なし・MTU 1500。IOS 側は EVC+`l2vpn xconnect context`。
6. **疑似回線の上の大きさの上限= IP 1478 バイト**(DF 付きで 1478 は通り 1479 は落ちる= 1478+イーサネット 14+ラベル 2 枚 8 = コアの 1500)。
   **IOL のイーサネットは MTU を変えられない**(`does not support user settable mtu`)→ コアを広げて 1500 を通す実演はできない(読み物で式を示す)。
   XR01 だけ 1614 に上げると XR01–RT01 の IS-IS が Init に落ちた(MTU の食い違い= M4 の論点の再確認)。
7. **AC の MTU の食い違い**(XR01 の CE 向き IF を 9014)→ 疑似回線は両側で down。XR `Error: MTU mismatched`(MTU 9000 対 1500)・IOS `Last error: Pseudowire MTU mismatch with peer`。
8. **相手が IOS だと、VC タイプと control word の食い違いは故障にならない**= IOS は既定で autosense(XR をタイプ 4 にすると IOS も Eth VLAN に合わせ、
   control word を付けると IOS も on に合わせて up のまま・通信も可)(l2vpn-h.log)。
9. **XR 同士(XR01⇔XR02 の LDP の疑似回線)だと両方とも故障になる**= タイプ 4 を片側だけ → `Error: PW type mismatched`・control word を片側だけ →
   `Error: illegal control word`(どちらも down)(l2vpn-i.log)。★RFC 8077 の「片方が使わないなら使わない」と食い違う → 実機を正として記録(§24.4)。

**EVPN-VPWS XR01⇔XR02(RR= XR03)**(l2vpn-d.log・h)
10. BGP の l2vpn evpn(RR 経由)+ `neighbor evpn evi <EVI> target <相手の AC-ID> source <自分の AC-ID>`。RD/RT は自動(RD= ルータ ID:EVI・RT= AS:EVI)。
    BGP の経路は種類 1(`[1][ESI 0][AC-ID]/120`)。経路が届くまで 30 秒ほど DN。L2 属性の拡張コミュニティ `0x604:2:0`(P フラグ・MTU 0)。
11. **EVPN-VPWS は MTU の食い違いを既定で無視**(`Ignore MTU mismatch: Enabled`・`Transmit MTU zero: Enabled`。EVI に `enforce-mtu-match`・`transmit-l2-mtu`)→ MTU は故障の題材にならない。
12. **target の食い違い**(XR02 だけ target 9)→ XR02 は DN(`neighbor None … local ready`)、XR01 は **UP のまま**(XR02 の経路の AC-ID 4 は XR01 の target と合う)
    = 表示が非対称(TS 向き)。**RT の食い違い**(XR02 の EVI に 65000:999)→ 両側 DN。

**タグの操作**(l2vpn-f.log・EVPN-VPWS の上で)
13. 両端で VLAN が違う(110 と 111)→ 両端とも pop 1 なら通る(コアの中はタグなし= 付け替えはしなくてよい)。両端とも rewrite なし → 不通
    (タグ 110 のまま CE4 へ)。XR02 で `translate 1-to-1 dot1q 110 symmetric` → 通る(表示 `Rewrite Tags: [110]`)。片側だけ pop・片側 translate → 不通。
14. Q-in-Q= CE が 400/10 の二重タグ → XR01 `encapsulation dot1q 400 second-dot1q 10`+`pop 2` → 相手の VLAN 140(pop 1)へ通る。
15. `encapsulation dot1ad 401 dot1q 10`・`push dot1q 999`・`translate 1-to-2 dot1ad 500 dot1q 403` は構文としてコミットまで通る(0x88a8 を出す CE が無いので転送は未確認)。

**課題設計のための追加の測定**(判断の後・l2vpn-jk.log)
16. **LDP の疑似回線で XR の rewrite を付け忘れる → AC の MTU が 1504 になり `Error: MTU mismatched` で down**(IOS 側も `Pseudowire MTU mismatch with peer`。
    TAC 116453 のとおり)。ジャンボ MTU(9000)と同じエラー行で原因が 2 通り → M11-2 は「同じエラー・違う直し方」にできる。EVPN-VPWS は MTU を無視するので、
    rewrite の非対称は「up なのに不通」になる(§24.3-13)→ M11-4 の材料。
17. **Q-in-Q**: AC を `encapsulation dot1q 410`(外側だけ)+ pop 1 にすると内側 10・20 の二重タグをまとめて運ぶ。`exact` を付けると二重タグは落ちる。
    `second-dot1q 10` で内側を絞れる(20 は落ちる)。`second-dot1q any` は二重タグなら内側を問わず通す。

### 24.4 公式文書での裏どり(2026-11-01・サブエージェント。xrdocs.io は取得していない・問題集サイトは使っていない)

- **XRv 9000 のリリース ノート(7.7.1/7.11.1/24.1.1 の Table 6)**= 対応する L2 は「L2VPN VPWS」と LAG だけ(EVPN・VPLS・CFM・G.8032 の記載なし)→ §24.3-1・2 と一致。
  CML の参照ページ(IOS XRv 9000)= 「L2 MPLS VPN: PASS」(ポイント ツー ポイント)・転送は約 168 kbps。
- **XRd のデータ シート(2026-04)**= Control Plane は「minimal forwarding capabilities」・用途は vRR と PCE → §24.3-3 と一致(L2 の明記はなし)。
- **CML の参照ページ(IOL)**= 「Layer-2 switching is not supported, but layer-2 encapsulations, such as EoMPLS and L2TPv3, are supported」→ IOL の VPLS/E-LAN は転送しない見込み。
  IOS XE の EVPN-VPWS はルータ(C8000/ASR1000)の文書に無く ASR 920 だけ → §24.3-4 と矛盾しない。
- **TAC 116350/116453・RFC 8077**= 疑似回線の MTU は両側で一致が必要(§24.3-7 と一致)・XR の IF の MTU は L2 ヘッダ込み・タイプ 4 を片側だけ → PW type mismatched(§24.3-9 と一致)。
  ASR 9000 の EVPN-VPWS の制約= 7.3.2 以降は MTU 0 を広告し食い違いを既定で無視(§24.3-11 と一致)。
- **食い違い**: RFC 8077 は control word を「片方が使わないなら使わない」とするが、XR 同士では片側だけ有効にすると down(`illegal control word`)。
  IOS は autosense で合わせる。→ 実機を正とする(読み物は「XR 同士では合わせないと上がらない・IOS は合わせてくれる」と書く)。
- AToM の MTU の式(IOS XE 17 の MPLS ガイド)= コアの MTU ≧ お客さまの MTU + トランスポートのヘッダ + ラベルの数 × 4 → §24.3-6 の 1478 と一致。

### 24.5 ユーザ判断(2026-11-01 決定= 1〜3 とも案どおり。1= VPWS に絞る/2= XRT-10 の続き+XRv9000 をもう 1 台/3= §24.6 の 5 本)

1. **範囲**: XR で手を動かすのは VPWS(LDP の疑似回線・EVPN-VPWS・タグの操作・Q-in-Q)に絞り、E-LAN・E-Tree・マルチホーム・E-OAM・G.8032・802.1ah は読み物だけにするか。
2. **盤面**: XRT-10 を解き終えた状態(SR のコア・L3VPN のお客さま)に XRv9000 をもう 1 台(PE)足すか、PoC と同じ素の盤面(LDP のコア)で作り直すか。
   前者は「M10 で外した LDP を、疑似回線のシグナリング(targeted LDP)のためだけに戻す」筋が作れる。どちらも XRv9000 2 台(上限)。
3. **課題案**(§24.6)の本数と TS の仕込み。

### 24.5b 補足 PoC= IOS XE の仮想ルータなら(2026-11-01・ユーザの問い「IOS-XE(CSR1000v / Catalyst 8000V)だったらどうなのか」→「確かめ切る」)

盤面 `problems/_POC-XRL2XE`(P1= IOL を中心にした星形のコア・PE= **XE1/XE2/XE3= Catalyst 8000V 17.15.1a** と XR01= XRv9000 26.1.1・RR= XR02(XRd)・
CE1〜4= IOL・SW1= IOL-L2 を XE1+XE2 に束で二重に収容)。手順 `poc/xr/l2xe_poc.sh`・SW1 は telnet(`poc/xr/swsh.py`)・記録 `poc/xr/l2xe-*.log`。CSR1000v(17.3.8a)は試していない。

1. **8000V はライセンスの段階を上げるまで MPLS が無い**(既定は `License Level:` 空欄= `show mpls …` が構文ごと無い)。
   `license boot level network-advantage addon dna-advantage` → `write` → 再起動(確認に答える)で有効。登録は不要。1 台 4GB・転送の上限 20 Mbps。
2. **EVPN の E-LAN が動く**(vlan-based・EVI 200・`bridge-domain 200` に EFP と `member evpn-instance 200`)。3 拠点で ping/TCP 可。MAC は経路の種類 2
   (MAC と MAC/IP)・BUM の配り先は種類 3(IMET・`replication-type ingress`)。RR の XRd はそのまま反映する(l2xe-b.log)。
3. **VPLS(LDP・VFI・3 拠点の全メッシュ)が動く**(l2xe-cd.log)。公式の「Software-based data plane is not supported」(VPLS の制約)は古い世代の文書の持ち越しとみられ、
   8000V のデータ シートは VPLS を載せている(サブエージェントの文書調査)。
4. XR01⇔8000V の **LDP の疑似回線は通る**。**EVPN-VPWS は 8000V 同士なら通る**が、**XR⇔8000V は IOL と同じく XR→XE の向きを XE が捨てる**
   (制御は両側 up)= XR と IOS XE の EVPN-VPWS のデータ プレーンの相互接続の問題(l2xe-cd.log・l2xe-d3.log)。
5. **EVPN のマルチホーム(all-active)が動く**。ES は種類 0 か 3(`identifier type 3 system-mac …`)・冗長化は all-active だけ(single-active は構文に無い=
   公式の制約どおり)。SW1 に 1 本の束に見せるには両 PE の Port-channel に同じ `lacp device-id`。両 PE が種類 1(ES ごと・EVI ごとの A-D)と種類 4(ES 経路)を出し、
   遠い XE3 は SW1 の MAC を ESI 付き・次ホップ 2 つ(aliasing)で持つ。片側(XE1 の Gi3)を落とすと XE3 は数秒で XE1 を外す(ES 単位の取り消し)が、
   **IOL-L2 はリンク断を受け取らない**(CML の IOL の制約)ので SW1 は LACP の失効まで XE1 側へ振り続ける= 既定(slow)で 30 秒以上不通・`lacp rate fast` で断 約 18 秒(l2xe-e*.log)。
   ★IOL-L2 の初期設定の `vlan 200` が効かず VLAN が無かった(VTP サーバ)→ telnet で作り直して解決。
6. **CFM(802.1ag)と Y.1731 が動く**(LDP の疑似回線の E-Line・EVC 名付きの EFP に up MEP)。相手の MEP の学習・ループバック(`ping ethernet mpid …`)5/5・
   リンクトレース・DMM の双方向の遅延(0.69〜1.92 ms)・相手の EFP を落とすと `Lifetime Expired`。★xconnect の EVC の service は VLAN なし
   (`service <MA> evc <EVC>`)・VLAN 付きはブリッジ ドメイン用(取り違えると「already been configured with xconnect service」)。
   **EVPN-VPWS の EFP の MEP は成立せず**(片側が CCM を出さない)= 公式の「EVPN EFI does not support association into EVC」の範囲とみる(深追いしていない)(l2xe-f*.log)。
8. **ユーザ判断(2026-11-01)= 別のラボで追補**(「どれが一番実務的か」への答え= 今の SP の L2VPN の主役(EVPN の E-LAN+マルチホーム+CFM)は
   XR で動かせない側にあり、EVPN の仕組み(経路の種類・ESI・DF)は OS を問わず持ち込める/XRT-11 に混ぜると XR⇔XE の EVPN-VPWS が通らず作り物になる)。
   順序= **XRT-11(XR の VPWS・課題 5 本)を先に仕上げ → M11 追補= 8000V だけの小さなラボ(E-LAN・マルチホーム・CFM)**。読み物は XR の書き方を
   8000V の実測の設定と並べて示す。8000V の PoC 盤面は撤収(追補のときに組み直す)。
7. 示唆: E-LAN・マルチホーム・CFM は 8000V で手を動かせるが、**XR は加われない**(XRv9000 は VPWS だけ・XR⇔XE の EVPN-VPWS は通らない)。
   8000V は 1 台 4GB なので XRv9000 2 台の XRT-11 に何台も足すとメモリが足りない(PoC= XRv9000 1+8000V 3+XRd+IOL 7 で空き 約 15GB)。

### 24.6 課題案(PoC の結果から・ユーザ判断で確定する)

ラボは **`XRT-11`**。PE= XR01(XRv9000)・**XR03(XRv9000 を足す)**・RT02(IOL・据付)、RR= XR02(XRd)。

| 課題 | 中身(挙動で指定・値は課題文で渡す) | 主な XR の論点 | SPCOR |
|---|---|---|---|
| M11-1(構築) | お客さま C の拠点 1(XR01・VLAN 100)と拠点 2(RT02・据付・VLAN 200)を E-Line でつなぐ(LDP の疑似回線) | l2transport のサブインタフェース・rewrite pop(両端で VLAN が違ってよい理由)・xconnect と pw-id・(盤面 A なら)targeted LDP だけの `mpls ldp` | 4.2.a・4.2.d |
| M11-2(TS) | 「拠点間の E-Line が上がらない/上がっているのに通らない」。仕込み案= 前任者が AC の IF にジャンボ MTU(MTU mismatched)+ 別の E-Line で rewrite の付け忘れ(up なのに不通) | `show l2vpn xconnect detail` の Error 行・MTU の数え方(XR は L2 込み)・タグの対称性 | 4.2.a・4.2.d |
| M11-3(構築) | お客さま D の E-Line を EVPN-VPWS で(XR01⇔XR03・RR は XR02)。両端の VLAN が違う | BGP の l2vpn evpn・RR・`neighbor evpn evi … target … source`・経路の種類 1 の読み方・translate と pop | 4.1.a・4.2.a |
| M11-4(TS) | 「EVPN-VPWS の片側だけ down」(target の食い違い= 片側は UP に見える)または XR 同士の LDP の疑似回線の control word/タイプの食い違い | 非対称な表示の読み方・`illegal control word`/`PW type mismatched` | 4.1.a |
| M11-5(構築) | お客さま E の複数の VLAN を 1 本で運ぶ(Q-in-Q= 外側 400) | `encapsulation dot1q 400 second-dot1q …`・pop の枚数・dot1ad との違い(読み物) | 4.2.b・4.2.d |

- 読み物だけ= E-LAN(VPLS・EVPN E-LAN・MAC の学習と分割ホライズン)・E-Tree・EVPN のマルチホーム(ESI・DF・all-active/single-active)・E-OAM(CFM・Y.1731)・
  G.8032・802.1ah/PBB-EVPN・E-Access。設定例は公式文書の形で載せ、「この環境の XR では動かせない(PoC §24.3-1・2)」と明記する(CLAUDE.md §6 の「根拠は実機」の例外として扱う)。
- 「やってみる」の候補= 疑似回線の上の大きさの上限(1478)・IOS の autosense(タイプ 4 にしても上がる)・EVPN-VPWS の MTU の無視。

### 24.7 課題の確定案(2026-11-01・§24.5 の決定を受けて。値は課題文で渡す)

盤面= XRT-10 を解き終えた状態(SR のコア・XR01 に LDP なし・L3VPN・SR ポリシー・PCE)+ **XR03**(XRv9000・RT01 の先・IS-IS と SR の prefix-SID index 3 は据付・BGP なし)
+ **CEB3**(お客さま B の拠点 3・L2 だけ)。L2 の E-Line は L3VPN のポートにタグ付きのサブインタフェースで相乗りさせる(CE・XR01 の Gi0/0/0/2・3・RT02 の Et0/2・Et1/0)。
RT02 の相手側は据付のサブインタフェースの `xconnect`(LDP の疑似回線)。

| 課題 | お客さま・回線 | XR01 側 | 相手側 | 中身 |
|---|---|---|---|---|
| M11-1(構築) | A: CEA1 VLAN 100 ⇔ CEA2 VLAN 200(172.31.10.0/24) | Gi0/0/0/2.100 | RT02 Et0/2.200・pw-id 100(据付) | LDP の疑似回線。**XR01 には M10-2 で LDP が無い**→ シグナリング(targeted LDP)のためだけに LDP を戻す・コアのリンクで LDP を動かさない(採点= RT01/RT03 と隣接しない)。L3VPN が止まらないこと |
| M11-2(TS) | B: CEB1 300/310 ⇔ CEB2 300/310(172.31.30・31.0/24) | Gi0/0/0/3.300・.310(前任者 CHG-1401/1402) | RT02 Et1/0.300・.310・pw-id 300・310(据付) | 両方 `Error: MTU mismatched`。300= rewrite の付け忘れ(AC の MTU 1504)/310= サブインタフェースの MTU 9018(ジャンボ)→ 原因が別 |
| M11-3(構築) | B: CEB1 VLAN 400 ⇔ CEB3 VLAN 40(172.31.40.0/24) | Gi0/0/0/3.400 | XR03 Gi0/0/0/1.40 | EVPN-VPWS・EVI 400・AC-ID= 拠点の番号(1・3)。l2vpn evpn は RR(XR02)経由だけ(XR01⇔XR03 の直接のセッションは張らない)。XR02 の設定も |
| M11-4(TS) | B: CEB1 410/420 ⇔ CEB3 41/42(172.31.41・42.0/24) | Gi0/0/0/3.410・.420(前任者 CHG-1411・正しい) | XR03 Gi0/0/0/1.41・.42(前任者 CHG-1411) | 410= XR03 の target が 2(拠点 3 は DN・拠点 1 は UP に見える)/420= XR03 の rewrite の付け忘れ(両側 UP で不通) |
| M11-5(構築) | B: CEB1 ⇔ CEB3 の S-VLAN 500 の中の C-VLAN 10・20(172.31.51・52.0/24) | Gi0/0/0/3.500 | XR03 Gi0/0/0/1.500 | Q-in-Q の E-Line(EVPN-VPWS・EVI 500)。**外側 500 だけの単一タグ(172.31.50.0/24)は運ばない** → `second-dot1q any`(写しで終わらないひねり) |

- 拠点の番号(AC-ID の約束)= 拠点 1= 1・拠点 2= 2・拠点 3= 3。
- 採点= 状態(`show l2vpn xconnect`・BGP の要約)+ CE からの ping(`login_probe.py`)。M11-5 は 51/52 が通り 50 が通らないことを両方見る(全部止まっても「50 不通」は満たすため)。
- 仕込み= `XR01.commits.yml`(CHG-1401・1402・1411)・`XR03.commits.yml`(CHG-1411)。

### 24.8 実装の結果(2026-11-01・ラボ XRT-11)

- **作り方**: XR01・XR02 の初期設定は、XRT-10 の初期設定で一度組み、`PID=XRT-11 poc/xr/solve_xrt10.sh` で M10 を解いた実機の running-config から
  写した(SR-TE・PCC・カラーの入れ子は手で書かない)。XR03(XRv9000・IS-IS と SR の index 3 は据付・BGP なし)・CEB3・RT01 の CORE-C(RT01 側は LDP の同期を外す)・
  RT02 のサブインタフェースの `xconnect`(据付)・CE のサブインタフェースを足した。前任者の作業= `XR01.commits.yml`(CHG-1401・1402・1411)・`XR03.commits.yml`(CHG-1411)。
- **実測で設計を直した点**:
  1. **XR は `mpls ldp` の設定が無くても、疑似回線の相手と targeted LDP のセッションを張る**(起動時から LDP の設定が無い XR01 でも確認= `show running-config mpls` は
     `mpls oam` だけ・`Interfaces: 0 LDP configured`)→ M11-1 は「LDP を戻す」ひねりが成り立たない。要件は「コアのリンクで LDP を動かさない」のまま(入れると RT01 と隣接= 採点で落とす)、
     読み物 2.3 節の論点にした。`mpls ldp`(IF なし)を足す答えも通る(別解)。
  2. **サブインタフェースの `mtu` は AC を親のポートより大きくできない**(サブインタフェースに 9018 → AC は 1500 のまま)→ ジャンボの仕込みはポートの `mtu 9014` に変更
     (310 の AC が 9000・300 は 9004。ジャンボを外すと 300 は 1504 が残る= 原因が 2 つ重なる)。サブインタフェースの `mtu 1514` は AC が 1496(タグの分も引く)= 別解にならない。
  3. 新しい PE(XR03)との l2vpn evpn のセッションは、上がってから経路がそろうまで 1 分ほど(40 秒では `None`・1 分 45 秒で全部 UP)。課題文の待ち時間は「LDP と BGP」と書いた。
  4. Q-in-Q の拾う形の表(読み物 b4 §2.1)と、両端 rewrite なしで 2 枚のまま運ぶ形(別解・満点)。内側を列挙する形(`10,20`)は後から足す 30 を運ばない
     → CE に 500/30(172.31.53.0/24)を足して採点で見る。
- **E2E**: 白紙 0 → 模範解(`solve_xrt11.sh`・learn.yml の逐語= `verbatim.py`)で課題ごと 100・最終 100。M10 の状態(SR ポリシー 3 本 up・TI-LFA 全保護・L3VPN)も保たれる。
  誤答の判別(`poc/xr/wrong_xrt11.sh`・記録 `poc/xr/expM11-wrong.log`)= コアのリンクに LDP 75・`mpls ldp` だけ(別解)100・ジャンボだけ外す 0・
  XR01⇔XR03 の直接のセッション 65・識別子の入れ違い 75(両端が互いに矛盾しないので E-Line は通る= 約束の確認だけ落ちる)・420 の直し忘れ 65・
  外側 500 だけ 65・内側の列挙 55。別解= 両端 rewrite なしの Q-in-Q 100。reset 後に白紙 0(2 回)。読み物の「やってみる」(b0 の rewrite 外し・b2 の XR03 の
  rewrite 外し・b4 の second-dot1q なし)は解く側と同じ手順で測った。読み物= `courses/xr/{en,ja}/b0〜b6`(3 ページ+付録・実践 3 枚)。
  XRT-11 は白紙で稼働中(MGMT .11-.20/.31-.33・ユーザ未着手)。

## 25. M11 追補 — Catalyst 8000V で E-LAN・マルチホーム・CFM(SPCOR 4.2.a・4.2.c・4.1.a)(2026-11-01 実装中)

§24.5b-8 のユーザ判断(XRT-11 を先に仕上げ → 8000V だけの小さなラボで追補)を受けたもの。2026-11-01 にユーザが実装を指示
(「ラボは邪魔なら撤収してよい」→ XRT-11 は白紙のまま撤収)。**IOS XR は盤面に入らない**(XRv9000 はブリッジ ドメイン不可・CFM なし=
§24.3-1・2、XR⇔XE の EVPN-VPWS は不通= §24.5b-4)。読み物は 8000V の実測の設定を主に、IOS XR の書き方を公式文書の形で並べる。

### 25.1 盤面(ラボ `XRT-12`)

- コア= **P1(IOL 17.15)を中心にした星形**(§24.5b の PoC と同じ)。IS-IS CORE L2・wide・LDP。P1 は l2vpn evpn の **RR も兼ねる**(据付。PoC は XRd だった)。
- PE= **XE1・XE2・XE3(Catalyst 8000V 17.15.1a)**。Gi1= コア・Gi2= CE・Gi3= SW1(XE1・XE2)。データ IF は 3 本で足りる。
- お客さま C の拠点= 1(CE1・XE1)・2(CE2・XE2)・3(CE3・XE3)・4(**SW1= IOL-L2・XE1 と XE2 に LACP の束で二重に収容**)。
  CE は IOL ルータのサブインタフェースでサービスを出し分ける(拠点 3 の EVPN の E-LAN だけタグなし= ひねり)。
- 8000V は既定のライセンスの段階では MPLS が無い → 構築の最後に **`license boot level network-advantage addon dna-advantage`+保存+再起動**を
  自動化する(`topologies/xe_license.py`・problem.yml の `xe_license_boot`)。
- 資源= 8000V 3 台(各 4GB)+IOL 5 台。XRv9000 とは同居しない。

| サービス | 拠点 1(XE1 Gi2) | 拠点 2(XE2 Gi2) | 拠点 3(XE3 Gi2) | 拠点 4(SW1) | アドレス |
|---|---|---|---|---|---|
| E-LAN(VPLS・VPN 210)= 前任者の作り | VLAN 210 | VLAN 210 | VLAN 210 | — | 172.31.210.0/24(ホスト部= 拠点の番号) |
| E-LAN(EVPN・EVI 200)| VLAN 200 | VLAN 200 | **タグなし** | VLAN 200(束) | 172.31.200.0/24 |
| E-Line(LDP の疑似回線 130・据付)| VLAN 130 | — | VLAN 130 | — | 172.31.130.0/24 |

### 25.2 課題(案・値は課題文で渡す。番号は XRT-11 の続き)

| 課題 | 中身 | 主な論点 | SPCOR |
|---|---|---|---|
| M11-6(TS) | 前任者の VPLS(VPN 210)。拠点 1⇔3 だけ通じない(XE1・XE3 の VFI に互いの member が無い= ハブ アンド スポークのつもり。スプリット ホライズンで XE2 は中継しない)+もう 1 つ(PoC で決める) | VFI のフルメッシュ・スプリット ホライズン・`show l2vpn vfi`/`show bridge-domain` | 4.2.a |
| M11-7(構築) | EVPN の E-LAN(EVI 200)を拠点 1〜3 で。BGP は RR(P1)経由。拠点 3 はタグなし | EVI と BD・EFP・種類 2/3 の経路・`replication-type ingress`・`encapsulation untagged` | 4.1.a・4.2.a・4.2.d |
| M11-8(構築) | 拠点 4(SW1)を XE1・XE2 に all-active で二重に収容し、EVI 200 に加える。ESI は課題文で渡す | ES・ESI・`lacp device-id`・種類 1/4 の経路・エイリアシング・DF | 4.1.a |
| M11-9(構築) | 据付の E-Line 130 を CFM で監視(MD レベル 4・MEP ID= 拠点の番号)。切れたら 5 秒以内に両端で検知+Y.1731 で往復の遅延を測り続ける | MD/MA/MEP・CC の間隔と寿命(3.5 倍)・`ping ethernet`・IP SLA の y1731 | 4.2.c |

- 採点= 状態(BGP・`show l2vpn evpn mac`・`show bridge-domain`・`show ethernet cfm maintenance-points remote`・`show ip sla statistics`)+CE からの ping
  (`login_probe.py`)。M11-9 の「5 秒以内」は採点中だけ XE3⇔P1 のリンクに CML のリンク条件(loss 100= 黙った故障)を入れて確かめる
  (既定の CC 10 秒なら寿命 35 秒で残る・IS-IS/LDP もまだ切れない)。
- やり直し= IOS XE は `configure replace`(構築の最後に running-config を bootflash に控える。`xr_reset.py` を IOS XE にも広げる)。

### 25.3 構築して確かめること(PoC §24.5b で済んでいない点)

1. ライセンスの自動化(day0 に `license boot level` を入れておけば保存+再起動だけで済むか・再起動後に day0 の MPLS の行が効いているか)。
2. IOL の P1 が l2vpn evpn の RR になれるか(種類 1〜4 を反映するか)。
3. 拠点 3 のタグなしの EFP(同じポートに dot1q の EFP と同居)。
4. M11-6 の 2 つめの故障の候補(rewrite の付け忘れ= up なのに不通/VPN ID の打ち間違い= 疑似回線が上がらない)の症状。
5. ESI の種類 0 の書式・`lacp device-id` を片側だけにした時の SW1 の束(片方 suspended のはず)。
6. CFM の CC 1 秒と 10 秒で、黙った故障の検知の時間が採点で分かれるか。
7. `configure replace` で構築直後へ戻るか(l2vpn evpn・ES・CFM・IP SLA を含めて)。SW1(IOL-L2)に SSH で入れるか。

### 25.4 実測の結果(2026-11-01・ラボ XRT-12= Catalyst 8000V 17.15.1a+IOL 17.15。手順 `poc/xr/xrt12_poc.sh`・記録 `poc/xr/expM11b-*.log`)

1. **ライセンス**: day0 に `license boot level network-advantage addon dna-advantage` を入れておくと、8000V は初回の起動で自分で
   再起動し(uptime が数分)、`License Level: network-advantage` で上がった。day0 の MPLS・l2vpn の行も効いていた(LDP 隣接・VFI)→
   `xe_license.py` は確かめるだけで済んだ(段階がそろわない時だけ設定・保存・再起動し、MPLS の行が欠けていれば day0 を流し直す作り)。
   ★day0 の順序の罠= `service instance 130 ethernet E130` を `ethernet evc E130` より前に書くと EFP ごと捨てられ、その下の
   `description` がポートの説明に化けた(初回の構築で発覚→テンプレートを直した)。
2. **IOL の P1 が l2vpn evpn の RR になれる**(種類 1〜4 を反映)。PoC の XRd は不要になった。
3. **SW1(IOL-L2)は EEM が無く SSH の鍵が作られない**(applet ごと捨てる)→ `topologies/telnet_keygen.py`(problem.yml の `ssh_keygen_telnet`)。
   `vtp mode transparent` を先に書けば day0 の `vlan 200` は効いた(§24.5b-5 の対策)。
4. **M11-6(VPLS)**: 前任者の形(XE1・XE3 は XE2 だけ+XE3 の EFP に rewrite なし)で 1⇔2 は通り、3 は誰とも通じない。XE3 は CE2 の MAC を
   疑似回線で覚えるが CE3 の MAC を一度も覚えない(タグなしで CE3 へ出て CE3 が答えない)。rewrite を足すと 2⇔3 は通り 1⇔3 は通らない
   (XE2 は CE1・CE3 の MAC を両方の疑似回線で覚えているのに中継しない= スプリット ホライズン・`show l2vpn vfi` の S=Y)。member を足すと全部通る。
   候補だった VPN ID の打ち間違い(211)= その PE の疑似回線が DOWN(`local ready, LruRnd`・no remote binding)→ 読み物の表に回した。
   ★8000V 17.15.1a の VFI の `member <PE> [vc-id] encapsulation mpls` には **no-split-horizon の選択肢が無い**(ヘルプに出ない・付けると Invalid input)。
   公式(MPLS Configuration Guide 17.x の VPLS の章)は「The no-split-horizon keyword disables it」と書く → 公式と実機の食い違い。課題では使わない(M11-6 の
   誤答「XE2 でスプリット ホライズンを外す」は成り立たない)。読み物は「ラボの 8000V には外す選択肢が無かった」と注記。ユーザに報告する。
5. **M11-7(EVPN の E-LAN)**: `replication-type ingress` が無いと EVI が `State: Incomplete`・`Replication Type: Not set (global)`・
   `EVI Down, BD Up` で、BGP が上がっていても何も通らない(課題文の「コアにマルチキャストなし・PE ごとに 1 つずつコピー」が必須の行になる)。
   RD= ルータ ID:EVI・RT= AS:EVI(自動)。拠点 3 の `encapsulation untagged` は同じポートの dot1q の EFP と同居でき、XE3 を dot1q 200 にすると 0%。
6. **M11-8(マルチホーム)**: 種類 0 の入力は 9 オクテットを点で区切る(`00.00.00.00.00.00.00.04.01`)。表示の形(`0000.0000.0000.0000.0401`)は
   `Invalid input`。`lacp device-id` を XE1 だけにすると SW1 は Et0/1 を suspended(相手のシステム ID が 2 つ)・XE2 の Po1 は SD。
   両方にすると Po1(SU) Et0/0(P) Et0/1(P)・XE3 は SW1 の MAC を ESI 0401・次ホップ 2 つで持つ(エイリアシング)・Forwarder List に 2 台・
   序数 0/1・DF の待ち 3 秒・Split Horizon label。XE1 の Gi3 を落とすと 3 秒で XE3 の次ホップが XE2 だけになり、SW1(`lacp rate fast`)の ping は止まらない。
7. **M11-9(CFM)**: `ethernet cfm global` が無いと MEP の CC が `I` で相手を覚えない(`ethernet cfm ieee` は書かなくてよかった)。
   XE3⇔P1 にリンク条件 loss 100(黙った故障)→ 既定の CC(10 秒)は +10.2 秒でも相手の MEP が残る・1 秒は +3.2 秒で両端とも消える。
   その間 P1 の IS-IS・LDP は up のまま。`watch`(1.4 秒ごと)の 4 回目= +4.6 秒で採点する。
   ★**相手の MEP が消えると Y.1731(DMM)の操作は `Internal error` で止まったまま、MEP が戻っても再開しない**。`ip sla restart 130`(設定モード)で再開。
   予定の無い操作に restart しても Inactive のまま(予定の書き忘れは隠れない)→ IP SLA の確認は restart してから 15 秒後に読む。
   y1731 の下に `frequency` は無い(既定で毎秒 1 回の DMM)。
8. `configure replace bootflash:lab-baseline.cfg force` でのやり直し= §25.6。

### 25.5 公式文書での裏どり(2026-11-01・サブエージェント。cisco.com と RFC だけ・xrdocs.io は取得していない・問題集サイトは使っていない)

- VPLS(MPLS Configuration Guide 17.x「Configuring Virtual Private LAN Services」)= スプリット ホライズンが既定・フルメッシュ・VC ID= VPN ID → §25.4-4 と一致。
- EVPN(同「EVPN Single-Homing」「EVPN over MPLS with IRB」)= 「Only Ingress Replication is supported for EVPN MPLS」・RD/RT は自動。
  replication-type の既定や Incomplete の記述は無い(例は必ず書く)→ 実機を正(§25.4-5)。章が名指しするのは ASR 1000 だけ(C8000V の記載なし)。
- ★**ESI の種類が公式文書の中で割れる**: マルチホームの章(16.9 から持ち越しの文)は「Only type 3 ESI is supported」、IRB の章の設定例は
  「Support both type 3 and type 0」。17.15.1a の実機は種類 0 を受け付けて広告した(§25.4-6)。→ 新しい章と実機が一致するので種類 0 で作り、
  読み物に食い違いを注記。**ユーザに報告して判断を仰ぐ**(種類 3 に替える案あり)。
- all-active だけ・single-active なし(公式どおり)。`lacp device-id` は IRB の章の例にあるが「両 PE で同じ値に」の文は無い → 実機で必要と確認(§25.4-6)。
- CFM(Application Services Configuration Guide 17.x「Configuring Ethernet CFM for Cisco QFP-Based Platforms」= C8000v を名指し)= 既定の CCM 間隔 10 秒・
  loss-threshold 3・方向の既定は up・xconnect の service は VLAN なし。EVPN の制約「EVPN EFI does not support association into EVC」「only supports
  configuring down MEP on the EFP」「Up MEP cannot send CFM packet out from the EFI」→ §24.5b-6 の up MEP 不成立と一致。寿命 3.5 倍は NCS 520 の
  CFM の文書と 802.1ag。レベルの推奨範囲(5〜7/3〜4/0〜2)は Cisco の文書に無く 802.1ag による。
- Y.1731(IP Addressing Configuration Guide 17.x「Configuring IP SLAs Metro-Ethernet 3.0 (ITU-T Y.1731) Operations」)= 構文・Frame Interval 1000 が一致。
  「CFM over cross-connect … works only if the control-word is configured」とあるが、このラボの xconnect では特に設定せず動いた。
- IOS XR の形(ASR 9000/NCS 5500 の L2VPN ガイド・Ethernet OAM のガイドとコマンド リファレンス)= VPLS・EVPN の E-LAN・マルチホーム
  (`lacp system mac` を両 PE で同じに= NCS 5500 の例と TAC の技術文書 2026)・CFM(★XR の CC は既定で無効= IOS XE と違う)・`ethernet sla`。読み物に反映。
- RFC 7432(種類 1〜4・ESI の種類・DF のサービス カービング V mod N・エイリアシング・一括の取り消し・ESI ラベル)・RFC 4762(フルメッシュ・スプリット ホライズン)。

### 25.6 実装の結果(2026-11-01・ラボ XRT-12)

- 基盤に足したもの= `topologies/xe_license.py`(problem.yml の `xe_license_boot`)・`topologies/telnet_keygen.py`(`ssh_keygen_telnet`)・
  `xr_reset.py` の IOS XE 対応(`xe_reset_nodes`= 構築の最後に running-config を bootflash に写し、やり直しは `configure replace … force`)・
  `lab_up.yml` の 2 つの段・`poc/xr/verbatim.py` の見出し(`On XE1:`)と `configure terminal`。
- 課題= M11-6〜9(§25.2 のとおり。M11-6 の 2 つめの故障は rewrite の付け忘れに確定)。配点= 各 25。読み物= `courses/xr/{en,ja}/b7・b9・bb`
  (3 ページ)+実践 3 枚(b8・ba・bc)+付録 b6 を E-Tree・G.8032・802.1ah だけに縮めて追補の後ろへ・単元の入口 b0 の表を更新。
- **実測で直した点**: ①IOS XE は `service instance` の下にも `bridge-domain` がある→ 模範解・読み物の設定例は `exit` で抜けてから(`!` だけだと `member` が
  Invalid で EVI につながらない)。②MAC はフレームからしか覚えない→ MAC を読む確認(M11-7・M11-8)は ping の後に置き、確認の前にも CE から ping して 10 秒待つ。
  ③Y.1731 は相手の MEP を失うと止まる→ IP SLA の確認は restart してから読む(§25.4-7)。④XE2 でスプリット ホライズンを外す誤答は 8000V に構文が無く成り立たない。
- **E2E**(`poc/xr/e2e_xrt12.sh`・`wrong_xrt12.sh`・記録 `poc/xr/expM11b-verbatim.log`・`expM11b-wrong.log`・`expM11b-wrong2.log`)= 白紙 0 → 模範解 100(課題ごと・最終・逐語)・reset(configure replace)後に白紙 0(4 回)・誤答の判別(M11-6 rewrite だけ 35・メッシュだけ 30/M11-7 拠点 3 を dot1q 30・replication-type なし 0・PE どうしの直接のセッション 85/M11-8 lacp device-id が片側 0・ESI 違い 55/M11-9 CC の間隔が既定 60・ethernet cfm global なし 0)。
  ★全 PE から replication-type を外して戻すと 40 秒では E-LAN が戻らなかった(未追跡。XE3 だけなら 30 秒で戻る= やってみるの手順)。
- XRT-12 は E2E 後に撤収(2026-11-01・先に XRT-11 を解く・ユーザ指示)。provision 約 12 分(8000V は day0 のライセンスの行で 1 回自分で再起動)。
- ★ユーザ判断待ち 2 点(§25.5)= ①M11-8 の ESI の種類 0(公式の 2 つの章で割れる・実機と新しい章は種類 0 を認める。替えるなら種類 3)
  ②VPLS の no-split-horizon(公式にあるが 8000V の VFI の member に無い。課題では使っていない)。

## 26. MPLS サービスのまとめ直し(BL-261)(2026-11-03 起票・M12 の前に挟む)

### 26.1 経緯と見立て

2026-11-03 ユーザ申告「MPLS 関連が難しかった。何が何だか、どれがどう違うのか、どうやって設定するのか、あまり身についていない」。
重点としてユーザが選んだもの= **(b) サービスの違い(L3VPN・VPWS・VPLS・EVPN)** と **(c) 設定の組み立て方(何をどの順で入れるか)**。
(a) ラベルの配り方の違い(LDP・BGP ラベル付きユニキャスト・SR)と (d) 全体像は選ばなかった。

見立て(チャットでユーザに説明済み):
1. 10/24〜11/01 の 9 日で M8・M8 追補・M9・M10・M11(+追補)= 量と速さ。どれもラベルを使うので互いに似て見える。
2. 土台の読み物(M8・M8 追補・M9)は CLAUDE.md §6 の決まり(技術そのものから・設定例を常に)より前の書き方で、`:::config` が 0。
3. サービスを横に並べて比べるページがない(単元ごとに 1 つずつ説明しただけ)。
4. ラボは前の単元を解き終えた状態から始まり、課題は 1 か所の追加か故障 → 白紙から通して組んだことがない。
   記録= XRT-07 の 5 課題を約 40 分・XRT-08 の 3 課題を約 35 分で通過(足りない 1 か所を調べれば通れる作り)。
SPCOR の配点= 3.0 MPLS と SR 20%・4.0 サービス 20%。

### 26.2 方針

- M12 はこの後に回す。§5 の「先回りしない」の例外として、BL-257(2 周目)のうち **M9 L3VPN の読み物の書き直し**をここへ前倒しする
  (ユーザ了承 2026-11-03)。M8(運ぶ層)の書き直しは BL-257 に残す。
- 運ぶ層(IGP+LDP)は出来ている前提にし、サービスに絞る(ユーザの重点が (b)(c) のため)。

### 26.3 中身(案)

1. **地図のページ**(読み物・日英)= 4 つのサービスを同じ枠で並べる。
   - 枠= ①お客さまから見ると何か(ルータ/1 本の線/スイッチ) ②PE が覚えるもの ③内側のラベルの意味 ④PE 同士の話し方 ⑤お客さまをつなぐ所。
   - 組み立ての共通の順= 0 土台を確かめる → 1 PE 同士の話し合い → 2 サービスの入れ物 → 3 お客さまの収容 → 4 下から順に確かめる。
     4 つのサービスは同じ骨組みで、違うのは各段の中身、と見せる。
   - 1 つの盤面で 1 つのパケット/フレームを 1 ホップずつ追い、ラベルの積み方を比べる(根拠は実測)。
   - 同じ盤面の上の最小の設定例を `:::config` で並べる(IOS XR と IOS XE)。
2. **白紙から組むラボ**(XRT-13 の予定)= コアは出来ていてサービスは何もない状態から、4 つを順に組む。同じ CE の組に VLAN を分けて載せ、
   違いがサービスだけになるようにする。やり直しは `lab.sh reset`。値を変えてやり直せる生成器にするかは後で決める。
3. **M9 の読み物の書き直し**(何が嬉しいか → 仕組み → 設定例)。
4. **紙面**(ホップごとのラベルの積み方・`show` の読み方)。
- 順番= 1 → 2 → 3 → 4(地図で全体をつかみ、すぐ手で組む)。

### 26.4 盤面の案(2026-11-03 ユーザ決定= 案 1)

実測済みの制約= XRv9000 は VPWS だけ(ブリッジ ドメインなし・§24.3)/XRd は L2 を転送しない/XR⇔IOS XE の EVPN-VPWS は XR→XE が捨てられる
(§24.5b-4)/XR⇔8000V の LDP の疑似回線は通る/8000V は 4 つとも動く(§24.5b)/資源= XRv9000 1+8000V 3+XRd+IOL 7 で空き約 15GB。

- **案 1(推奨)**= 8000V×3(XE1〜3)が主役で 4 つとも組む+XRv9000×1(XR01)が L3VPN と LDP の VPWS に加わり、同じ枠の XR の書き方を並べる。
  P1= IOL(P 兼 RR)・CE= IOL。理由= 同じ PE の組・同じ CE の間で 4 つを順に組むと違いがサービスだけになる。XR の仮想機は E-LAN を
  転送できないので主役にできない。
- 案 2= XR だけ(XRv9000×2)。L3VPN と VPWS(LDP・EVPN-VPWS)だけ手で組み、VPLS・EVPN の E-LAN は読み物だけ。
- 案 3= IOS XE だけ(8000V×3)。XR は使わない。

### 26.5 PoC(2026-11-03 着手)

盤面 `problems/_POC-XRSVC`= P1(IOL・P 兼 RR= vpnv4 と l2vpn evpn・据付)を中心にした星形。PE= XE1〜3(8000V 17.15)・XR01(XRv9000 26.1.1)。
CE1〜4(IOL)は VLAN でサービスを出し分ける(CE 側は据付)。手順 `poc/xr/svc_poc.sh <段>`・記録 `poc/xr/expSVC-<段>.log`・pcap は `poc/xr/pcap/`。

| VLAN | サービス | 拠点(PE) | アドレス |
|---|---|---|---|
| 100 | L3VPN(VRF A・PE-CE は eBGP) | 1(XE1)・2(XE2)・4(XR01) | PE-CE 172.16.<拠点>.0/24(CE .1・PE .254)・CE の LAN= Loopback100 10.100.<拠点>.1/24・CE の AS 6500<拠点> |
| 130 | VPWS(LDP の疑似回線・pw-id 130) | 1(XE1)⇔ 4(XR01) | 192.168.130.0/24(ホスト部= 拠点) |
| 140 | VPWS(EVPN・EVI 140) | 2(XE2)⇔ 3(XE3) | 192.168.140.0/24 |
| 200 | EVPN の E-LAN(EVI 200・vlan-based) | 1・2・3(XE1〜3) | 192.168.200.0/24 |
| 210 | VPLS(VFI VPLS210・LDP) | 1・2・3(XE1〜3) | 192.168.210.0/24 |

確かめること:
1. 8000V の 1 本の IF に L3 のサブインタフェース(Gi2.100・VRF)と service instance(130/140/200/210)が同居できるか。
2. 4 つ(+EVPN-VPWS)が同じ盤面で同時に動くか。XR01 が L3VPN と LDP の VPWS に加われるか(XR⇔XE)。
3. 線の上のラベル= CML のリンクの捕獲(`poc/xr/cml_cap.py`)で、入口 PE→P1 の線は 2 枚(運ぶ+サービス)・P1→出口 PE の線は PHP で 1 枚か。
   サービスごとに内側のラベルが何を指すか(PE のラベル表 `show mpls forwarding-table` の行と突き合わせる)。
4. 「PE が覚えるもの」の表示= VRF の経路表/疑似回線だけ/ブリッジ ドメインの MAC(疑似回線から学ぶ)/EVPN の MAC(BGP の種類 2)。
5. CE からの traceroute に MPLS のラベルが出るか(L3VPN だけ)。
6. 設定例の元= 各 PE の running-config(段 `cfg`)。

### 26.6 実測の結果(2026-11-03・`_POC-XRSVC`・記録 `poc/xr/expSVC-*.log`・pcap は `poc/xr/pcap/`)

1. 8000V の Gi2 に L3 のサブインタフェース(Gi2.100・VRF A)と service instance 130/140/200/210 が**同居できた**(L3VPN と L2 が同時に通る)。
2. **5 つとも同時に稼働**= L3VPN(XE1・XE2・XR01)・VPWS LDP(XE1⇔XR01)・VPWS EVPN(XE2⇔XE3)・VPLS(XE1〜3)・EVPN の E-LAN(XE1〜3)。
   ping は初回の 1 つ落ち(ARP)以外すべて通過。XR⇔8000V の L3VPN と LDP の疑似回線は問題なし。
3. **線の上**(CML のリンクの捕獲)= 入口 PE→P1 は 2 枚・P1→出口 PE は 1 枚(PHP)。**外側はサービスによらず同じ**(XE2 行き= 17)。
   CE1→CE2: L3VPN `{17, 23}`+IP/VPLS `{17, 25}`+CW+フレーム/EVPN `{17, 28}`+フレーム。CE1→CE4 VPWS `{19, 24008}`+フレーム。
   CE2→CE3 EVPN-VPWS `{18, 23}`+CW+VLAN 0 のタグ+フレーム。L2 のフレームはタグなし(rewrite pop)。
   コントロール ワード= VPLS(8000V 同士の LDP)と EVPN-VPWS(8000V 同士)に有り・EVPN の E-LAN と XE⇔XR の LDP の VPWS に無し。
   ★EVPN-VPWS(8000V)は VLAN 0 のタグ(`8100 0000`)を付けて運ぶ(読み物は注記どまり。XR→XE の EVPN-VPWS が捨てられる件との関係は未確認)。
4. **内側のラベル= 受け取る PE が決めた入れ物の番号**。XE1 の `show mpls forwarding-table`= 23→VRF A の 10.100.1.0/24(Gi2.100)・
   24→l2ckt(1)(Gi2= VPWS)・25/26→l2ckt(2)(3)(VPLS の疑似回線→ブリッジ ドメイン)・27→evpn(mc:bd 200)(BUM)・28→evpn(uc:bd 200)。
   XR01= 24007→VRF A の 10.100.4.0/24・24008→PW(10.255.0.41:130)。★XE1 と XE2 がどちらも 23 を VPN のラベルにした= ラベルは PE ごとの意味。
5. CE の traceroute に MPLS のラベルが出る(L3VPN だけ)= CE1→CE4 の 2 ホップ目 P1 `[MPLS: Labels 19/24007]`・3 ホップ目 XR01 `[Label 24007]`。
6. EVPN の RT は書かなくても自動(E-LAN= 65000:200・EVPN-VPWS= 65000:140= AS:EVI)。VPLS の VFI は相手を `member` で名指し(BGP なし)。
7. ★`virl2_client` 2.10 の `download_capture` は CML 2.8.1 で 404(リンクの ID で取りに行く)→ `/pcap/<捕獲のキー>` で取る(`poc/xr/cml_cap.py`)。

見えた骨組み(読み物の軸にする)= **相手の見つけ方が 2 通り**: LDP で運ぶもの(VPWS・VPLS)は入れ物の中で相手の PE を名指しし、
targeted LDP が自動で張られる/BGP で運ぶもの(L3VPN・EVPN)は RR への iBGP のアドレス ファミリを足し、RT で仲間を見つける。
8. **故障の表れ方(読み物の「止まったときの見当」の根拠)**(`expSVC-fail.log`):
   - XE2 の VRF A の輸入 RT だけ 65000:101 に= XE2 の VRF には自分の経路だけ(`show bgp vpnv4 unicast all` も自分の RD だけ)・XE1 には 10.100.2.0/24 が残る→ CE2 から 0%。戻すと即 100%。
   - P1 の XR01 向き IF の `no mpls ip`= XR01 の 10.255.0.41/32 が `Unlabelled`・XE1 は 19 を付け続ける(P1 で道が切れる)→ L3VPN は経路が残ったまま 0%・
     LDP の疑似回線は XR01 が `DN`、XE1 は `VC status is down`(`Status received from network peer: DOWN(pw-tx-fault)`)。戻すと 40 秒以内に両方 100%。
   (PoC の盤面 `_POC-XRSVC` は 2026-11-03 に撤収済み。problems/_POC-XRSVC は再利用のため保持)

### 26.7 読み物(2026-11-03 完了・Drive 同期済み)

`courses/xr/{en,ja}/c0-svc-map.md`(サービスを並べて見る= 4 つの問い・CE の ARP・PE が覚えるもの・名指しか BGP か・
線の上のラベル(pcap)・受け取る PE のラベル表・まとめの表)と `c1-svc-assembly.md`(組み立て順= 段 0〜4・`:::config` 9 個・
下から確かめる表・止まったときの見当(実測 8 行)・IOS XE と IOS XR の対応)。章 "C0"(M 番号なし)・部「SP の中核とサービス」の末尾。
日英で見出し 14/15・段落 44/23 が一致。設定例は PoC の running-config から(XE1・XE2・XR01)。

### 26.8 ラボ XRT-13 の課題案(2026-11-03 ユーザ了承= 5 本)

- 盤面= `_POC-XRSVC` と同じ(PE= XE1〜3+XR01・P1= P 兼 RR を据付・CE を据付)。**初期状態= コア(IS-IS・LDP)と RR だけ**。PE には BGP もサービスも無い。
- 値は読み物の設定例と変える(別の顧客・VLAN 3xx・RT 65000:3xx)。拠点の組も変える(設定例の写しで終わらせない= §6)。
- 採点は課題ごとに段で分ける(段 1= RR との iBGP の AF/段 2= 入れ物/段 3= 収容/通し= CE 間の ping)→ 採点結果で「どの段で止まったか」が分かる。
  課題文には段の順を書かない(ヒント控えめの方針。順は読み物で学ぶ)。やり直しは固定値+`lab.sh reset`(生成器は後で検討)。

| 課題 | サービス | 拠点(PE) | ねらい |
|---|---|---|---|
| S-1 | L3VPN | 2(XE2)・3(XE3)・4(XR01) | 段 1〜3 を通して。XR の拠点は eBGP にポリシーが要る |
| S-2 | VPWS(LDP) | 3(XE3)⇔ 4(XR01) | 名指し。OS をまたぐ |
| S-3 | VPLS | 1・2・3 | 名指しの全メッシュ |
| S-4 | EVPN の E-LAN | 1・2・3 | BGP で見つけ合う。段 1 の l2vpn evpn と replication-type |
| S-5 | VPWS(EVPN) | 1(XE1)⇔ 2(XE2) | S-2 と同じ E-Line を BGP で |

読み物に足す「やってみる」の候補= CML の画面でリンクのキャプチャを取りラベルの枚数を数える/拠点を 1 つ足すとき VPLS と EVPN で既存の PE の何行が変わるか。

### 26.9 実装の結果(2026-11-03・ラボ XRT-13)

- 盤面= `_POC-XRSVC` と同じ(初期設定は PoC から・コメントだけ替え)。顧客 D・VLAN 3xx。provision 約 15 分(8000V はライセンスの行で 1 回自分で再起動)。
- 課題のひねり(設定例の写しで終わらせない)= S-1 拠点 3 の CE は BGP を話さない(XE3 に VRF の静的経路+再配送)/S-2 両端の VLAN が違う(320・321)/
  S-4 RT を 65000:3400 だけに(★下の実測)/S-3・S-5 は値と拠点の組だけ変える。
- 採点= 課題ごとに「段 1・段 2・段 3・通し」に分けた確認(`grading.svc1〜5.yml`)+最終(`grading.yml`= 各課題 20)。
  ★段 1(RR とのセッション)は**確立だけ**を見る。最初は「受けた経路の数が 0 でない」まで見ていて、段 3 の誤り(XR のポリシー忘れ・静的経路の渡し忘れ・
  replication-type の欠落)で段 1 まで落ちた → 確立だけに直した。S-1 の段 2 も「RR に届く経路」から「PE の VRF の RD と RT」(`show vrf detail`/`show vrf … detail`)へ。
  RR に届く経路は段 3 の確認にした(CE から受けて初めて出る)。
- 実践ページ= `courses/xr/*/c2-svc-practice.md`(課題文から切り出し)。★`scripts/course.sh` の切り出しが課題番号を「M11-6」の形だと決め打ちしていた →
  「S-1」の形も拾い、learn.yml の課題は title.en の頭で引くように広げた(既存の実践ページの出力は不変を確認)。
- ★**8000V 17.15.1a の EVPN の RT**(実測+公式で一致)= EVI に `route-target export/import` を書いても**自動の RT(AS:EVI= 65000:340)は消えず足されるだけ**
  (`Import-RTs: 65000:3400 65000:340`)。`no auto-route-target` で自動の分が消える。公式= MPLS Configuration Guide, IOS XE 17.x「EVPN Single-Homing」の例が
  `route-target both` と `no auto-route-target` の組、Catalyst 9400 の EVPN VXLAN ガイド(17.1)は「Removes the automatically generated route-targets」。
  ★さらに `no auto-route-target` のまま手の RT を最後の 1 つまで消すのは拒否(`% Cannot remove route-target because 'auto-route-target' is disabled.`)。
  → S-4 の「65000:3400 だけ」はこの 3 行で満たす(書かないと段 2 だけ落ちて 75 点)。読み物 c1 の 4.4 にはまだ書いていない(課題の答えになるため。解き終えた後に足すか判断)。
- E2E(`poc/xr/e2e_xrt13.sh`・`wrong_xrt13.sh`・記録 `poc/xr/expS13-*.log`)= 白紙 0(課題ごと・最終)→ 模範解を逐語で課題ごとに 100 → 最終 100。
  誤答(w1〜w7)= w1 XR のポリシー忘れ/w2 静的経路を BGP へ渡さない/w3 XR の AC の rewrite 忘れ(`Error: MTU mismatched`= XR 1504 対 XE 1500。8000V 相手でも同じ)/
  w4 VPLS のハブ アンド スポーク/w5 自動の RT を止めない/w6 replication-type なし/w7 EVPN-VPWS の target と source の取り違え。どれも落ちて、戻すと 100。

### 26.10 RR を P1 から専用の RR1 へ分ける(2026-11-04・ユーザ指摘→作り直し)

- 経緯= ユーザ「P1 に BGP の RR をさせたら、MPLS の醍醐味感が薄まりませんか？」→ 同意。転送は今も BGP を使わない(P1 は VRF なし・LFIB は
  PE のループバックだけ)が、制御面で P1 が全 VPN の経路を BGP の表に抱え、**BGP を持たないコア**が盤面で見えない。読み物も「P1 の BGP は RR のためで
  転送には使わない」と括弧書きで言い訳していた。M9〜M11(XRT-09〜11)は RR を別の XR02 にしていて、XRT-12・13 だけ台数を減らすため P1 に兼ねさせていた。
  XRT-13 はユーザが S-1〜S-3 を通過済みだったが「気にしなくていいので修正願います」で作り直し(その時点の PE の設定は scratchpad に控えた)。
- 盤面= RR1(IOL 17.15・Lo0 10.255.0.52)を P1 の脇に 1 本(P1 Ethernet1/1 ─ RR1 Ethernet0/0・10.0.52.0/24)。RR1 は IS-IS だけ(LDP なし= 経路を配るだけ)。
  P1 から `router bgp` を削除。`_POC-XRSVC` と XRT-13 の両方。★IOL の Ethernet0/3(a_if 3)は管理用= ここにつなぐと CML の取り込みが
  「interface P1-i3 is also connected to link l4」で失敗 → a_if 5(Et1/1)。
- 実測(PoC を全段取り直し・旧い出力は捨てた。`poc/xr/expSVC-*.log`)= P1 は `% BGP not active`・`show running-config | include ^router` は IS-IS だけ。
  P1 の LFIB の 16= RR1 の Lo `No Label`(RR1 に LDP が無い)・17〜20= PE。**ラベルは全部ずれた**(IOL の RR1 が 8000V より先に上がり 16 を取る)→ 読み物の
  出力(ARP・MAC・ラベルの表・キャプチャ・traceroute)を全部差し替え(CE の MAC も 8b00〜8e00 にずれた)。PE → RR1 の BGP は P1 までラベル 16 に載り、P1 が
  外して渡す(キャプチャで確認)。RR1= VRF なし・`show mpls interfaces` が空・VPNv4 の表に全拠点(no table)。XE1 の拠点 2 の経路= from 10.255.0.52・
  Originator 10.255.0.42・Cluster list 10.255.0.52・CEF は 18/25 で P1 へ(RR1 を通らない)。★IOS の RR は LDP なしでも VPNv4・EVPN を反射できる
  (ネクスト ホップは IGP で解決)。故障 2 種(RT の輸入違い・P1 の XR01 向きの `mpls ip` なし)の表れ方は前と同じ。PE の設定は RR の宛先(.51 → .52)だけが変わる。
- 裏どり= RFC 4364(コアのルータは VPN の経路を知らなくてよい)/Cisco IOS XRv 9000 Router Installation and Configuration Guide「Control Plane Specific
  Features」(vRR is not part of the forwarding path)・XRv 9000 Data Sheet(vRR)。「BGP-free core」という呼び名は公式文書では見つからず、コミュニティの用語
  (読み物では呼び名として紹介するだけ)。
- 読み物= c0 に 3.5 節「RR は道の外に置く: BGP を持たないコア」(P1 に BGP なし → 何が嬉しいか → RR1 はネクスト ホップを変えない → パケットは RR1 を通らない →
  RR1 を通るのは BGP だけ → RR1 は MPLS なし)・3.1 の P1 の説明と 16 の行・図に RR1・まとめに 1 文。c1 の段 1 に RR1 の設定例(running-config から)。
- ラボ= 課題文(日英: 据え付けに RR1・リンク表と機器表・「P1 と RR1 の間は IS-IS だけ・P1 は BGP なし」・S-1/S-4 の「ルート リフレクタ RR1」)・
  `grading.svc1`/`svc4`(RR1 で見る・PE の近隣は 10.255.0.52)・learn.yml(RR1・10.255.0.52)。
- E2E(2026-11-04・`poc/xr/expS13-*.log`)= 白紙 0(課題ごと・最終)→ 模範解を逐語で課題ごとに 100 → 最終 100。誤答 w1〜w7 は前回と同じ点で落ちて戻すと 100。
  **w8 を追加**= XE3 が RR1 でなく P1(10.255.0.51)に iBGP を張る(前の盤面の癖)→ P1 は BGP なしで Idle のまま → S-1・S-4 とも段 1 から落ちて 25 点・戻すと 100。
  reset 後は全部 0。ワークスペースの課題カードは再起動なしで新しい課題文(RR1)を出す(学習の記録は reset で退避)。

### 26.11 EVPN-VPWS は何が嬉しいか(2026-11-06〜07・ユーザ質問→読み物 1 ページ+PoC)

- 経緯= ユーザが XRT-13 全通過の後「EVPN-VPWS と普通の VPWS の嬉しさの違いがピンとこない」。1 本の線・片側 1 台の PE(S-2・S-5)では運ばれ方が同じなので
  差が見えない。差が出るのは ①拠点を 2 台の PE につなぐとき ②道を SR にして LDP をなくすとき(③相手の PE の住所を書かない)→ ユーザ「どちらも進めます」
  (読み物に足す+マルチホームの PoC)。
- 裏どり= ★IOS XE 17.x の MPLS のガイドの「EVPN Multihoming」の章は E-LAN 向けで、VPWS・point-to-point の記述が無い(制限= all-active のみ・
  single-active なし・type 3 ESI のみ等)。「EVPN Single-Homing」の章も VPWS は無し。IOS XE の EVPN-VPWS は ASR 900/NCS 4200 の「EVPN-VPWS
  Single Homed」の章だけ。IOS XR(ASR 9000 24.x)の L2VPN ガイドは EVPN-VPWS の single-homing と multi-homing を載せる。RFC 8214 の要約が
  「single-active / all-active redundancy with flow-based load-balancing」を嬉しさとして挙げる。PW の冗長の書き方= IOS XE の `member … encapsulation
  mpls group <名前> priority <n>`(Catalyst 9500 のコマンド リファレンス・ASR 900 の L2VPN Protocol-Based CLIs)。
- 盤面= `_POC-XRVPWS`(P1= P だけ・RR1= l2vpn evpn の RR・XE1〜3= 8000V 17.15.1a・SW1= IOL-L2 を XE1・XE2 に LACP の束・CE3)。手順
  `poc/xr/vpws_poc.sh`(a/bgp/mh/rate/mhf/mhf3/ldp/ldpf/sr/cfg)・記録 `poc/xr/expVPWS-*.log`。撤収済み。
- ★**実測(8000V の EVPN-VPWS のマルチホーム= 公式に記述なし・受け付けて動くが規格どおりではない)**= ES(type 0・all-active・`lacp device-id`)を束に付け、
  point-to-point の EVI の member に束を入れられる。SW1 の束は 2 本とも P・ping 通る・ES の Forwarder List に 2 台。ただし ①種類 1(EVI ごと)の経路の
  ESI が 0 のまま ②種類 1 の ES ごとの経路は出ない(XE3 で見えず) ③XE3 は 2 本の経路を multipath と表示するが VC の次の行き先は 1 台だけ ④PE が戻る
  たびに最後に届いた経路の PE へ乗り換える(RemDn→RemUp が一瞬・ping の連続した落ちなし)。束の両方の線から入るフレームは届く(SW1 の Et0/1= XE2 側へ
  100 発→ 100%)。切り替え= XE3 が使っている PE の線を落とすと最長 4 発(約 4 秒・CML は片側の shutdown が相手に伝わらず LACP の 3 秒待ちが大半)・
  落ちた PE の種類 1 の経路は取り下げ(0 available)。使っていない側を落とすと連続した落ちなし。平常時も 15000 発に 30 発前後 1 発ずつ落ちる(原因は未調査)。
- ★**実測(LDP の疑似回線の主と予備)**= XE3 に `group SITE4 priority 1/2` で XE1 を主・XE2 を予備 → UP/STANDBY。**SW1 の束が XE2 側へ流すと 0%**
  (XE2 は予備の線へ送る= Tx が増える・`Status sent to access circuit: DOWN(standby)`・XE3 が捨てる)。SW1 の XE2 側の線を止めると 100%。主の XE1 の線を
  落とすと XE3 は主を DN・予備を UP にして通る。XE1 が戻ると主へ戻り(revertive)、また 0%。= CE 側の束を予備に合わせる別の仕組み(MC-LAG など)が要る
  (この盤面では入れていない・mLACP/ICCP は未検証)。
- ★**実測(SR)**= IOL の P1 も IS-IS の SR(`connected-prefix-sid-map`・`router isis` の `segment-routing mpls`)が動く。コアのリンクの `mpls ip` を外すと
  P1 の LDP は 0 本・道は 16041 など。EVPN-VPWS は {16041 23} で通る。LDP の疑似回線も SR の道の上で UP だが、XE3 に XE1・XE2 との targeted の LDP が残る。
  疑似回線を消すと XE3 の LDP は 0 本。
- 読み物= `courses/xr/*/c3-evpn-vpws.md`(章 C0 の 4 ページ目・実践の後)。何が嬉しいか(困りごと→主と予備→ES)→仕組み(端の番号の種類 1・ES の種類 4)
  →同じ盤面で 2 つ(設定例・束・切り替え・主と予備で 0%)→SR で LDP を外す→まとめ。8000V が規格どおりでない点は :::note。c0 の冒頭の表と 2.3 節から案内。
  ラボ(課題)は作っていない= 2026-11-07 ユーザ判断で今度に見送り(BL-262。候補= この盤面で「拠点を 2 台にする」「LDP を外す」課題)。

### 26.12 M9 L3VPN の読み物の書き直し(2026-11-07 着手・BL-261 ③・ユーザ了承)

- 経緯= BL-261 の順番(地図 → XRT-13 → **M9 の書き直し** → 紙面)の 3 段目。旧 M9(1 ページ 39 KB・7 節)は CLAUDE.md §6 より前の書き方で、
  `:::config` が 0・「IOS XR の VRF」から入る XR 中心の構成・「何が嬉しいか」が無い・仕組みの図がトポロジ 1 枚だけ。
  章 C0(c0・c1)は 4 つのサービスを並べる入門で、L3VPN の細部(RR・as-override・共有サービス・インターネット)は M9 にしか無い
  → M9 を L3VPN 本体の単元として深め、c0/c1 から重ねて書かない(c0 の 3.1〜3.2 は案内でつなぐ)。
- **形(M10 にならう= 3 ページ+付録・実践も 3 枚)**:

  | ページ | 中身 | 課題 |
  |---|---|---|
  | `90-m9-l3vpn`(L3VPN の仕組み) | 何が嬉しいか(重なるアドレス・分離・オーバーレイ/ピア モデルの困りごと)→ VRF・RD・RT・VPNv4・2 枚のラベルを盤面で 1 ホップずつ → IOS XR の部品の置き場・PE-CE・RT のふるい | M9-1 |
  | `92-m9-rr-same-as`(RR と同じ AS のサイト) | フル メッシュの困りごと → VPNv4 の RR(全部持つ・AF ごとのクライアント・道の外)→ AS パスの検査と as-override・site-of-origin | M9-2 |
  | `94-m9-shared-internet`(共有サービスとインターネット) | RT の組み合わせでつながり方を決める(ハブとスポーク・非推移)→ 1 経路だけ荷札を足す(additive)→ 同じ PE の VRF どうし → VRF とグローバルの間 → パケットを追う | M9-3・M9-4 |
  | `96-m9-appendix`(付録) | VPN ラベルの割り当て方(per-prefix・per-vrf・per-ce)・Inter-AS A/B/C・CSC・IF の VRF を変えるとき(公式と実機の食い違い §22.6-1)・コマンドの対応 | — |

  実践= `91-m9-practice`(M9-1)・`93-m9-practice-2`(M9-2)・`95-m9-practice-3`(M9-3・M9-4)。旧「やってみる」6 つと測定値は該当ページへ移す。
- 設定例= `:::config`。課題の答えと同じ形のもの(M9-1 の VRF/IF/BGP・M9-2 の RR と as-override・M9-3 の輸出の方針・M9-4 のリーク)は `fold`。
  IOS XE の対比は RT02 の据え付けの設定(実機の running-config)。根拠= learn.yml の模範解(逐語で 100)と §26.12 の測り直し。
- 測り直し(2026-11-07)= XRT-09 を provision → `solve_xrt09.sh`(全課題)→ `poc/xr/m9rw_poc.sh out1 cap overlap soo perce out3 cfg`・
  記録 `poc/xr/expM9R-*.log`・pcap `poc/xr/pcap/m9-*.pcap` → reset → 撤収。測るもの= 両向きの traceroute と線の上のラベル(行き 16/22・帰りは
  XR01 の explicit-null で 0)/RT02 のラベルの表(内側のラベル= 受け取る PE の VRF の経路)/RR の VPNv4 表(両方の RD)/P が顧客の経路を持たない/
  **重なるアドレス**(CEB2 にも 10.101.2.0/24 を置いて RD で別の経路のまま・VRF ごとに正しい側へ)/site-of-origin(RT02 に届く・同じ値で送らない)/
  per-ce/設定例の元の running-config。
- ラボ・採点は変えない。learn.yml の read: と task.md/task.en.md の冒頭の案内・「コマンド例は示しません」(XRT-10 と同じ言い回しへ)を新しいページに合わせる。

**26.12 の結果(2026-11-07)**:
- 成果物= `courses/xr/{en,ja}/90-m9-l3vpn`(L3VPN の仕組み= 何が嬉しいか・VRF/RD/RT/VPNv4・2 枚のラベルを 1 ホップずつ(行きと帰りの 2 図)・
  重なるアドレスの実演・押さえどころ・XR の置き場と IOS XE の対比・確かめる順番)/`92-m9-rr-same-as`(RR は全部持つ・AF ごとのクライアント・道の外・
  as-override・site-of-origin)/`94-m9-shared-internet`(RT の組み合わせ・取り込みはつながらない・additive・同じ PE の VRF・VRF とグローバル・
  パケットを追う・スタティックでの受け渡し)/`96-m9-appendix`(ラベルの割り当て方 3 方式・Inter-AS・CSC・コマンドの対応)。
  実践= `91`(M9-1)・`93`(M9-2)・`95`(M9-3・M9-4)= practice.yml の `tasks:`。設定例 `:::config` 10 個(課題の答えと同じ形の 6 個は fold)。
  旧「やってみる」6 つは測定値ごと各ページへ移し、新しく 1 つ(同じアドレスを 2 つの顧客に)。日英の見出し・段落・表・囲みの並びは機械で一致を確認。
  learn.yml の read: と解説の節番号の参照・task.md/task.en.md の冒頭(ページの案内・「コマンド例」の言い回しを XRT-10 と同じに)を更新。ラボ・採点は不変。
- 測り直し= `poc/xr/m9rw_poc.sh`(out1・cap・overlap・soo・perce・out3・cfg・xevrf)・記録 `poc/xr/expM9R-*.log`・pcap `poc/xr/pcap/m9-{A,B}-*.pcap`。
  XRT-09 を provision → `solve_xrt09.sh` → 採点 100(★採点が学習ノルマに 1 行記録した→取り消し)→ 測定 → 撤収。
  1. 線の上= 行き XR01→RT01 `16|22`・RT01→RT02 `22`(PHP)/帰り RT02→RT01 `22|24004`・RT01→XR01 `0|24004`(XR01 の explicit-null= XRT-07 の M8-5)。
     行きの 22(RT02 の VPN ラベル)と帰りの 22(RT01 の LDP のラベル)は別物。顧客 B は `16|24`・帰り `22|24006`。ラベルの値は 10/27 の E2E と同じ。
  2. RT02 のラベルの表= 22→10.101.2.0/24[V]・23→198.51.100.128/25[V]・24→10.102.2.0/24[V](IOS XE も既定はプレフィックスごと)。P の RT01 は
     `% Subnet not in table`・`% BGP not active`。XR02 は全 RD を保持(10.99.2.0/24 も)・ラベルの表は空・`show route` に VPN の経路なし。RT02 は 10.99.2.0/24 を持たない。
  3. ★重なるアドレス= CEB2 に 10.101.2.0/24 を足す → 1 分以内に XR02 が RD 10.255.0.12:101 と :102 の 2 本・XR01 の CUST-A は {16 22}・CUST-B は {16 26}・
     traceroute の最後のホップが CEA2/CEB2 に分かれる。**SVC(両方の顧客を取り込む)の表で選ばれたのは 1 本(顧客 A)だけ**= 共有サービスは顧客の
     アドレスが重ならないことが前提(読み物 94 の 2.2 節)。消して 30 秒以内に戻る。採点への影響なし(該当チェックは肯定の ping だけ)。
  4. site-of-origin= XR01 の CEA1 に `site-of-origin 65101:1` → RT02 で `Extended Community: SoO:65101:1 RT:65000:101`。RT02 の CEA2 にも
     `neighbor 172.16.12.2 soo 65101:1` → RT02 は 10.101.1.0/24 を CEA2 に送らない(`Not advertised to any peer`)。★逆向き(RT02 が CEA2 の経路に印を付けて
     XR01 が CEA1 に送らない)は起きなかった= IOS XE は設定後に受け直していない経路に印を付けない(clear していない)。読み物は送らない側だけを書いた。
  5. per-ce= CEA1 の 2 経路が 24010 にまとまる・行き先は Gi0/0/0/2 の CEA1・2 行目に `Aggregate … (!)`(予備)。IOS XE の per-vrf=
     `mpls label mode vrf CUST-B protocol bgp-vpnv4 per-vrf`(グローバル)で `IPv4 VRF Aggr:27`・27→`aggregate/CUST-B`。
  6. IOS XE でアドレスの付いた IF に `vrf forwarding` → `% Interface Loopback99 IPv4 disabled and address(es) removed due to disabling VRF CUST-B`(アドレスが消える)。
- 本文の直し(裏づけの弱い言い切りを外した)= 旧 M9 の「IOS の PE は送って CE が捨てる」(未測定)を外し、XR が送る前に検査することだけを書いた。
  旧 M9 の「VPN-IPv4 は RFC 4364 の 4.2 節が定義」は誤り(4.1 節が VPN-IPv4・4.2 節は RD の符号化)→ 4.1 節に直した(RFC 4364 全文で確認・サブエージェント)。
  ラベルの割り当て方の per-ce の挙動は公式文書の明文が取れなかった(Cisco 8000 の L3VPN ガイド 26.x は per-CE が 26.3.1 から使えるとだけ)→ 実機のラベルの表で言える範囲だけを書いた。

### 26.13 紙面(BL-261 ④)— ラベルの積み方と表の読み(2026-11-07 着手・ユーザ決定)

- ユーザ決定(2026-11-07)= 範囲は ①〜③ を先に(故障の読み方は BL-263 へ見送り)・出し方は**毎日のパックに混ぜる**(units.yml の U-M9・U-M11 に載せ、
  単元ローテーションで回る)+ SP だけを解く日のために `--profile sp`。
- 器= `topologies/gen_paper_spvpn.py`(gen_paper_mcq の KB ファミリ・shape `spvpn`)。問題文は日本語で生成し、出題時に英訳する(紙面の英語出題の手順どおり)。
- 種類(kind):
  | kind | 枠 | 形 | 問うこと |
  |---|---|---|---|
  | `l3_stack` | 思考 | read(単一選択) | L3VPN の 1 つのパケットが、指定した 1 区間の上で運ぶラベルの積み方 |
  | `l2_stack` | 思考 | read(単一選択) | VPWS(LDP・EVPN)・VPLS・EVPN の E-LAN で、同じく 1 区間のラベル |
  | `owner` | 瞬発 | select・allthat | 線の上で捕まえた 2 枚のラベルを、それぞれ誰が決め、入口 PE がどうやって知ったか |
  | `lfib` | 瞬発 | match | 出口 PE のラベル表の行(サービスの行と運ぶ層の行)を、届いたパケットの扱いに対応づける |
- 盤面は 2 つ。どちらも実測だけを使う(図の出力は記録から行を抜き出して削るだけ・手で作らない。selftest が記録の中に同じ行があるかを照合する):
  - **5 サービスの盤面**(`_POC-XRSVC`・2026-11-04 の取り直し= RR1 を分けた後)= XE1・XE2・XE3(Catalyst 8000V)・XR01(XRv9000)・P1・RR1。
    記録 `poc/xr/expSVC-{l3,pw,vp,el,ev,lbl}.log`・キャプチャ `poc/xr/pcap/{l3,vpws,vpls,elan,evpws}-*.pcap`。
  - **M9 の盤面**(XRT-09・2026-11-07)= XR01・RT01・RT02・RT03・XR02(RR)。記録 `poc/xr/expM9R-out1.log`・キャプチャ `poc/xr/pcap/m9-{A,B}-*.pcap`。
- 場面(線の上の実測。左が外側):
  | 場面 | 通り道 | 入口→P | P→出口 | 入口 PE が内側を知る元 |
  |---|---|---|---|---|
  | L3VPN CE1→CE2 | XE1→P1→XE2 | 18 \| 25 | 25 | BGP(RR1 が反射)`show bgp vpnv4 unicast all labels` |
  | L3VPN CE2→CE1(応答) | XE2→P1→XE1 | 17 \| 25 | 25 | 出口 XE1 の In label 25 |
  | L3VPN CE1→CE4 | XE1→P1→XR01 | 20 \| 24009 | 24009 | 同上(1 区間目は XE1 の CEF でも実測・P1→XR01 の PHP は VPWS のキャプチャで実測) |
  | VPWS CE1→CE4 | XE1→P1→XR01 | 20 \| 24010 | 24010 | targeted LDP(`show l2vpn atom vc vcid 130 detail` の Bindings) |
  | VPWS CE4→CE1(応答) | XR01→P1→XE1 | 17 \| 26 | 26 | XR01 の `show l2vpn xconnect detail` の Remote 26 |
  | VPLS CE1→CE2 | XE1→P1→XE2 | 18 \| 27 | 27 | XE1 の `show bridge-domain 210` の MAC ごとの VC_LABEL(CE3 宛ては 26) |
  | E-LAN CE1→CE2 | XE1→P1→XE2 | 18 \| 30 | 30 | タイプ 2 の Label1 30(BUM はタイプ 3 の PMSI の 29) |
  | EVPN-VPWS CE2→CE3 | XE2→P1→XE3 | 19 \| 25 | 25 | `show l2vpn evpn vpws vc id 140 detail`(Local 26・Remote 25) |
  | EVPN-VPWS CE3→CE2(応答) | XE3→P1→XE2 | 18 \| 26 | 26 | 出口 XE2 の Local 26 |
  | L3VPN CEA1→CEA2 | XR01→RT01→RT02 | 16 \| 22 | 22 | `show bgp vrf CUST-A labels`(XR02 が反射) |
  | L3VPN CEA2→CEA1(応答) | RT02→RT01→XR01 | 22 \| 24004 | **0 \| 24004** | RT02 の `show ip bgp vpnv4 all labels`。XR01 が explicit null を広告(RT01 の表に `explicit-n`) |
  | L3VPN CEB1→CEB2 | XR01→RT01→RT02 | 16 \| 24 | 24 | 出口 RT02 の表の 24 |
  | L3VPN CEB2→CEB1(応答) | RT02→RT01→XR01 | 22 \| 24006 | **0 \| 24006** | RT02 の `show ip bgp vpnv4 all labels` |
- 誤りの選択肢の作り方(よくある取り違え)= 外側と内側を逆に書く/入口 PE の表の Local(自分が決めた番号。XE1 の 10.255.0.42 は 22)を外側に使う/
  逆向きの外側(P が入口 PE に割り当てた番号)を使う/P→出口の区間に外側を残す(PHP を忘れる)・逆に explicit null の区間で外側を外す/
  内側に入口 PE 自身が決めた番号を使う/VPLS で別の宛先(CE3)の VC_LABEL を使う/E-LAN で BUM のラベルを使う/ラベルなし。
  正解と同じ並びになった誤りは捨てる(XE1 と XE2 がどちらも 25 を VPN のラベルにしているため、L3VPN CE1→CE2 では「入口自身の番号」が正解と同じになる)。
- 裏どり= 線の上は CML のリンクの捕獲(上の表)。表の読み方は記録の出力そのもの。規定= RFC 3032 §2.1(ラベル 0 は IPv4 explicit null)・
  RFC 3031(PHP)・RFC 4364(VPN のラベルは出口 PE が割り当てて BGP で配る)・RFC 4447(疑似回線のラベルは targeted LDP で相手の PE が配る)・
  RFC 4762(VPLS)・RFC 7432(E-LAN: MAC/IP 広告ルートの Label1・Inclusive Multicast Ethernet Tag ルートの PMSI のラベル)・RFC 8214(EVPN-VPWS)。
- 対象外(BL-263 へ)= 故障の出力から原因を当てる問題。
- **実装の結果(2026-11-07)**= `topologies/gen_paper_spvpn.py`(KB ファミリ・`gen_paper_mcq` の KB_FAMILIES に登録)。場面 13(5 サービスの盤面 9・M9 の盤面 4)×区間 2・
  ラベル表 3 枚(XE1・M9 の XR01・M9 の RT02)。図の出力 20 個は記録の行番号から機械で写した(手で打たない)。selftest= 200 件+図の照合 20/20+場面ごとに
  「入口の表の Outgoing= 1 区間目の外側・Local= ing_local・P の表の Pop/explicit-n= 2 区間目」を図から導いて実測と照合(13 場面とも一致)+区間ごとの
  「必ず入れる誤り」(1 区間目= Local の列を外側に使う・2 区間目= PHP を忘れる/explicit null の区間で外側を外す)が肢に入るか。
  パックの解答欄の読み取り(選択・すべて選べ・組み合わせ)と HTML の描画を確認。units.yml= U-M9(`spvpn/l3_stack`・`owner`・`lfib`)・
  U-M11(`spvpn/l2_stack`・`owner`・`lfib`)・profile `sp`。単元ローテーションでは思考枠・瞬発枠とも U-M11 → U-M9 が次の先頭(未出題のため)。
  mixed(思考枠)は THINK_KINDS だけ、speed(瞬発枠)は SPEED_KINDS だけを引くことを確認。問題文は日本語で生成し、出題時に英訳する(他の紙面と同じ)。

