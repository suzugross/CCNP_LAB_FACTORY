# STP-P2 — 単元 U-A3 STP の P2(試験形式の選択問)設計

BL-216。前段= P1(BL-214・`cloze_kb_stp.py`・知識項目表 [curriculum/U-A3-stp.md](../../curriculum/U-A3-stp.md) 47 項目)。
ラボ(L1〜L3)は BL-076 で別途。状態: **完了・出題可**(2026-09-22)。実装= `topologies/gen_paper_stp.py`(9 kind)・`topologies/stp_model.py`。kind は §2 の 7 案に `s_basic`(802.1D 基礎の事実)と `s_mst`(リージョン比較を `s_modes` から分離)を足して 9 にした。

## 0. ゴール

- 知識項目表の各項目を、**本試験の形式**(単一選択・複数選択・数非明示・組合せ・show 読解・盤面計算)で少なくとも 1 kind が問えるようにする。
- 実装先= `topologies/gen_paper_stp.py`(`gen_paper_mcq --shape stp`・KB_FAMILIES 登録)。型は `gen_paper_eigrpkb.py`(kind×forms 表＋draw/build_choices_*＋selftest)に倣う。
- 恒久規約をそのまま適用: 複数選択と数非明示(ccnp-above-exam-cognition)・未提示前提×消去法・暗黙の最小変更原則・Cisco 語 v2(`--style`)・選択肢に因果を書かない。

## 1. 裏どり(CLAUDE.md「作問の裏どり」の初適用)

| ソース | 置き場 | 状態 |
|---|---|---|
| Cisco 公式 + ネットワークエンジニアとして | [curriculum/U-A3-stp.sources.md](../../curriculum/U-A3-stp.sources.md)(47 項目の照合表・食い違い D1〜D15・実測候補 M1〜M21) | 完了(2026-09-22) |
| 問題集(66 問) | 非公開側(`private/sources/` 配下・kind 対応表つき) | 抽出完了。29 問は図/show 出力が画像で欠落(信頼順 3 位のため論点の洗い出しにだけ使う) |
| 実機(ioll2-xe) | `problems/_POC-STP` を再利用・記録は [poc/stp/README.md](../../poc/stp/README.md) 第2回 | **完了**(2026-09-22・M1〜M17) |

照合で分かった前提(抜粋):
- 判定「確定」は 36 項目。「要実測」= #17・27・28・31・32・34・39・40。「要ユーザ判断」= #2・#20 と D9・#32(§5)。
- 知識項目表 #28 の文言「現 root がそれ以下なら」→ Cisco 原文は「24576 **未満**なら最小値から 4096 引く」。P1 KB の本文も合わせて直す(実測 M2 の後)。

## 2. kind 案(7 kind・P1 の 6 セクション＋TS)

| kind | 区分 | 形(forms) | 世界機構 / 盤面 | 主な被覆項目 |
|---|---|---|---|---|
| `s_elect` | 思考 | select / select2 / allthat / read | **3〜4 台の盤面を抽選**(priority・MAC・リンク速度・port-priority)→ STP 計算器で root / RP / DP / ブロックを算出。「ブロックになるポート」「PC-X→PC-Y の転送経路」「正しい記述をすべて」 | #3〜7・11・47 |
| `s_rstp` | 瞬発 | select / select2 / allthat / match | 事実ベース(役割 4 種・状態 3 種・転送する/しない・p2p/shared・edge・3 hello) | #12〜19 |
| `s_modes` | 瞬発＋思考 | select / select2 / allthat / read | 事実(PVST+/Rapid/MST・規格番号・IST)＋**MST リージョン設定 2 台分を並べて「同じリージョンか」「VLAN X はどのインスタンスか」** | #20〜27 |
| `s_tuning` | 思考 | select / select2 / fix / read | **要件「SWx を VLAN N の root に / secondary に」「VLAN N をリンク B へ寄せる」→ 最小変更の設定を選ぶ**(root primary の結果値計算・port-priority は上流側・cost は自側)。世界= 現 root の priority で正解の値が変わる | #28〜33 |
| `s_guard` | 思考 | select / select2 / allthat / cause | 要件駆動「既存 root を守る」「端末ポートに SW が挿されたら止める」「片方向リンク」→ 機能を選ぶ。global と interface の適用範囲の差(portfast ポートのみ)・併用不可・filter の危険 | #35〜43 |
| `s_read` | 思考 | read / select2 / allthat | `show spanning-tree vlan N` / `summary` / `interface … detail` / `mst` / `inconsistentports` / `show udld` を **計算器の盤面から描画**して読ませる(書式は ioll2 実測に合わせる) | #34・44〜47 |
| `s_ts` | 思考 | cause / fix / read | 症状→原因: err-disabled(bpduguard ログ)・root-inconsistent・loop-inconsistent・MST 境界 `Bound`・ループ(MAC フラップ・ストーム)・trunk⇔access 誤接続(型不一致の inconsistent) | #36〜41・#23・#1 |

- 瞬発枠(speed)には `s_rstp`・`s_modes` の事実形だけを入れる。残りは思考枠。
- **問題集に出てきたが知識項目表に無い論点** → 項目表に追記してから被覆する(#48〜): ①EtherChannel は STP 上 1 本の論理リンク(コスト・役割)②起動時は自分を root とみなして BPDU を出す ③802.1D/w/s の規格番号 ④trunk⇔access 誤接続時の STP の反応(PVID/型の不一致による inconsistent 表示)⑤PortFast は trunk にも設定できる(`portfast trunk`)。
- 盤面の計算器(`s_elect`/`s_read` 共通)は P1 の `t_read` 世界と共用できる形で `topologies/stp_model.py` に切り出す(ラボ L1 の期待値計算にも使う)。

## 3. 数値・表記の規約(案)

| 論点 | 案 | 根拠 |
|---|---|---|
| 盤面のリンク速度とコスト | 紙面の盤面は **Gi/Fa インタフェースと Cisco 公式の short 値(Gi=4・Fa=19・10G=2)** で描く。long は `s_tuning` の方式変更の文脈でだけ出す | 公式の既定表。IOL の Et=100 は試験の典型と違う(D2) |
| show 出力の書式 | 行の並び・列名・略号は **ioll2 実測**に合わせ、値だけ計算器から入れる(IF 名は Gi に置き換え) | 盤面と実機の書式の不一致を避ける(紙面 show は実機と行一致の既存方針) |
| PortFast 構文 | 本文は旧形 `spanning-tree portfast` を正とし、`edge` 形は「IOS のバージョンによって」の文脈に限って出す | ioll2 は旧形のみ(P6)・15.2(4)E 以降の文書は edge 形(D3) |
| 数値そのものを問わない論点 | global BPDU filter の送出数・MST 最大インスタンス数・cost の範囲・PVST+ 最大インスタンス数 | 資料間で割れる(D5・D7・D8・D12) |

## 4. 実機 PoC(ioll2-xe・`problems/_POC-STP` 再利用)

照合表 M1〜M21 のうち、出題の正誤に直結する **A 群(M1〜M5)** と、`s_guard`/`s_read`/`s_ts` の指紋に要る **B 群(M6〜M15)** を 1 回の PoC で測る。C 群は任意。

| 順 | 測るもの | 決まること |
|---|---|---|
| 1 | M1 既定モード・M6 summary の文言 | D1 の実機側・`s_read` summary の書式 |
| 2 | M2/M3 root primary/secondary の境界(32768/16384/4096/0・同値 MAC 負け) | `s_tuning` の正解値の算法 |
| 3 | M4 port-priority(上流/下流どちらで効くか・刻み)・M5 pathcost long | `s_tuning`/`s_elect` のひっかけの正しさ |
| 4 | M9 root guard・M10 loop guard・M12 errdisable recovery・M8 guard+filter 併用 | `s_guard`/`s_ts` の指紋とログ |
| 5 | M11 UDLD の有無・M13 RSTP 切替時間・M14 pvst⇄rapid 混在・M15 PVST simulation | 出題可否の判定(ioll2 に無い機能は文書ベースで出す) |

## 5. ユーザ判断が要る論点

| # | 論点 | 選択肢 |
|---|---|---|
| U1 | 「Cisco の既定モード」(#20・D1) | (a) 現行 Catalyst/IOS XE = Rapid PVST+ を正にする (b) 試験の定番 = PVST+ を正にする (c) 既定モードは出題しない/機種・版を問題文で固定する |
| U2 | BPDU 宛先 MAC(#2・D6) | PVST+ の 0100.0CCC.CCCD まで出すか、IEEE の 0180.C200.0000 だけにするか |
| U3 | UDLD normal モードは err-disable しないか(D9) | 断定形は避ける案(「片方向を検出しても normal はポートを無効化しない」まで)か、実測結果で決めるか |
| U4 | `pathcost method long` は全スイッチで揃えるべきか(#32) | 公式に明文なし。出題しないか、「揃えないと計算が食い違う」を理由付きで出すか |

**決定(2026-09-22 ユーザ)**:
- U1= **版で答えが変わる**。15.2(4)E より前の IOS= PVST+・15.2(4)E 以降と Catalyst 9000(IOS XE)= Rapid PVST+(Cisco 文書と一致)。
  既定モードを問う時は、問題文で機種/版を示して正解を一意にする。版を示さずに「既定は？」とは聞かない。ioll2 の実測値(M1)は参考として記録する。
- U2= **IEEE の 0180.C200.0000 のみ**。PVST+ の SSTP 宛先(0100.0CCC.CCCD)は出題しない。
- U3= 実機で確認を試みた(M11)。ioll2 に UDLD はあるが**片方向リンクを再現できない**(受信側 MAC ACL では UDLD フレームが落ちない)。
  → Cisco 公式(信頼順 1)の範囲で出す案: 「近隣情報がタイムアウトしても normal はポートを無効化しない(undetermined)/ aggressive は再確立を試みて失敗すると err-disable」。
  光の誤配線(misconnect)を normal が検出したときの扱いは出題しない。**決定(2026-09-22 ユーザ)= Cisco 公式の見解どおり(上記の案)で一旦確定**。
- U4= short も long も出題する。ただし**1 問の中では全スイッチをどちらか一方にそろえる。混在は出題しない**(混在の食い違いを題材にしない)。
  盤面・show 出力・選択肢の数値は、その問題の方式で一貫させる(selftest で検査)。

## 5b. PoC で見つかった出題素材(ひっかけの種)

- root primary は**一度きりの計算**(running には数値だけ・後で root が変わっても追従しない)/ 現 root が 4096 以下だと**失敗**する(0 にはしない)
- root secondary を全員既定の VLAN に入れると**その SW が root になる**
- port-priority は**上流側**で効く(下流で変えても表示が変わるだけ)
- root guard は**ポート上の全 VLAN**に効く(別 VLAN の正当な root まで止める)・上位 BPDU が別経路で回り込めば root は結局変わる
- 同一ポートの bpduguard+bpdufilter は **filter が勝つ**
- errdisable recovery の interval 変更は**既に err-disabled のポートのタイマに効かない**
- `clear spanning-tree detected-protocols` は**打った側だけ**
- IF の `spanning-tree guard` は後勝ちで置換(loop と root を同時に持てない)

## 6. 実装順

1. PoC(§4)→ 照合表の「実機」欄と poc/stp/README.md を更新 → U1〜U4 の決定を反映
2. 知識項目表に #48〜 を追記・#28 の文言修正(P1 KB も同期)
3. `stp_model.py`(計算器・selftest= 手計算の定番盤面 10 本と一致)
4. 瞬発 2 kind(`s_rstp`・`s_modes` の事実形)→ 思考 5 kind
5. selftest(一意性・正解が 1 通り・選択肢重複なし)→ scratch パックで試走 → CATALOG/CURRICULUM(U-A3 の P2 列)/units.yml/genres.yml を更新
