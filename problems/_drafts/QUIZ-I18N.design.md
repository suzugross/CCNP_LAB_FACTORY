# QUIZ-I18N — 出題の日英バイリンガル化（オンデマンド翻訳方式）

- 起案: 2026-07-27（ユーザ要望「全問題を日本語/英語どちらでも選べるように」）
- 状態: **完了（2026-07-27）** — SKILL.md 改修＋試訳1本(`problems/ENARSI-EIGRP-VRF-01/task.en.md`)＋初回実運用1周
  (ENARSI-OSPF-MADJ-01 を英語出題→採点→英語レビューまでフルサイクル・ユーザ一発100点・翻訳起因の問題なし)
  - 試訳対象は当初候補 ENARSI-REDIST-POLICY-01 から変更: params 問題で展開済み task.md が無かったため、静的 task.md を持つ完成問題 ENARSI-EIGRP-VRF-01 を採用
- 対象: quiz スキルの出題フローのみ。**採点系(grading.yml/grade.py)・生成器・既存 task.md には一切手を入れない**

## 決定事項

- **方式 = 案A: 出題時オンデマンド翻訳**
  - 事前一括翻訳(案B)は不採用: 再出題されない問題の翻訳が無駄・GEN 系は seed ごとに文面が変わるため事前翻訳が意味を持たず、生成器55本への `--lang` 実装が最重量になる
  - 新規問題のみ両言語(案C)は不採用: 既存165問を英語で解きたい要望を満たせない
- **英語の文体 = Cisco 公式に寄せる**(ユーザ明示要望)
  - Cisco 技術解説文(Config Guide / ENARSI・ENCOR OCG)・試験問題文の言い回しに揃える
  - 例: 「〜を設定しなさい」→ "Configure ...", 「〜であることを確認」→ "Verify that ...", 「〜してはならない」→ "Do not ... / must not ...", 「要件」→ "Requirements", 「制約」→ "Restrictions"(シム問の定番見出し)

## 実装内容（着手時）

1. `.claude/skills/quiz/SKILL.md` 改修:
   - **選定**: 出題言語の指定を受け付ける(既定=日本語。「英語で」「in English」等で英語)
   - **提示**: 英語指定時は task.md を翻訳して同ディレクトリに `task.en.md` として保存し、その全文をチャットに貼る＋プレビューリンクも英語版を指す。静的問題は既存 `task.en.md` があれば再利用(キャッシュ)。GEN 系は新 seed 生成直後に毎回翻訳
   - **採点後レビュー・降参時解説**: 英語出題回は solution.md ベースの解説も英語で(solution.md 自体の翻訳保存は任意)
2. 翻訳規約(SKILL.md に明記):
   - ホスト名・IP・プレフィックス・コマンド・インターフェース名・VRF名等の識別子は**原文のまま逐語保持**(採点 regex と食い違わせない)
   - 要件の数値・条件・禁止事項は**1対1対応**で欠落/追加禁止
   - 用語は Cisco 試験英語に統一: 再配送=redistribution / 集約=summarization(BGP は aggregation) / 経路=route / 隣接=adjacency(EIGRP は neighbor) / 認証=authentication / 検証=verify / 疎通=reachability / 拠点=branch(site) / 本社=HQ(headquarters)
   - 見出し構成(シナリオ/要件/制約/採点)は Cisco シム問の "Scenario / Requirements / Restrictions / Scoring" 体裁に寄せる
3. 品質確認: 既存問題1本(候補: ENARSI-REDIST-POLICY-01 など要件密度の高いもの)で試訳→ユーザレビュー→規約に反映

## 注意

- 採点は実機 config への regex 照合なので問題文の言語と完全に独立(検証不要)
- `_history.md` には出題言語を記録する(en 出題の再出題判断・キャッシュ有無の把握用)

## 追補(2026-07-27 実運用2回目での学び)

- **CML Lab Notes は build_topology が日本語 task.md を埋め込む**(当初設計の見落とし・ユーザ指摘)。
  → `scripts/set_lab_notes.py` を新設し、英語出題の提示手順に「Notes を task.en.md へ差し替え」を追加(SKILL 反映済)。
  notes のみの PATCH なので config 無変更・出題中でも安全。
- day0/initial の config 内コメント・description の日本語混在は構築時焼込のためオンデマンドでは直せない → **BL-072** として分離(新規問題は英語規約・既存は再出題時に順次)。
