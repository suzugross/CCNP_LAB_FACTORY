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
| M8 | MPLS LDP(隣接・同期・セッション保護・OAM・認証とラベルフィルタ) | 3.1 1.5.d | XR 1+IOL |
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
| M8〜M12(MPLS 転送・L3VPN・SR の転送・L2VPN・QoS・uRPF) | **XRv9000**(見込み) | Control Plane 版は転送が最小限。着手時に確認 |
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

## 18. M4 追補 — IS-IS の 2 周目(2026-10-22 設計・PoC中)

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
