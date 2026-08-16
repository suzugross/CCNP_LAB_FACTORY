# BGPDBG-MCQ — shape=bgpdbg の選択式化(パック合流) 設計 (BL-124)

> **★実装完了(2026-08-16)**。本設計どおり+実装時の差分2点:
> ①asym_up に fix 形(単一選択)を追加(§2 の追記どおり) ②要件行は素の文で渡す
> (obfuscate の構造化モードが番号を付けるため「- 」を付けると二重装飾)。
> 検証結果は BACKLOG 完了アーカイブ BL-124 の行を参照。

2026-08-16 ユーザ指示: 「bgpdbg(記述式)を、難易度を可能な限り落とさずに
選択形式(2〜3選択の複数選択あるいは単一選択)の通常紙面問題へ改修し、パックに載せたい」。

前提の現状(調査結果):

- `mixed` ルーレット([gen_paper_mcq.py](../../topologies/gen_paper_mcq.py) 6659行付近)に
  bgpdbg の枝が無い= パック(gen_pack)から構造的に漏れている唯一の shape。
- パック側の器は記述式にも対応済みだが、記述式は Claude 手採点になり夜間バッチの
  自動採点フロー(`key_of()` のキー突合)に乗らない。→ 選択式化が本筋。
- 素材の実機根拠= poc/bgpdbg/README.md(IOL 17.15・発見1〜3)。variant 3種
  (addr_mismatch 難4 / ebgp_multihop 難4 / asym_up 難5)、値は seed 抽選済み。

## 1. 難易度を保つための方針

記述式の難しさの核は3つ。選択式でもこの3つを**そのまま仕事として残す**:

1. **debug → 構成の再構成**(`open active, local address <X>` と行頭ピアから
   両側の neighbor 宛先/update-source を確定する)
   → 逆問題 **dbgconf 形**で保存(aaa BL-103① の前例)。選択肢= 両ルータの構成ペア。
   構成を選ぶには結局 debug から写像を自分で組むしかない。
2. **字面の罠**(`no route to peer`=シングルホップ検査 / `Connection refused`=到達性でない)
   → 罠を**錯乱肢そのもの**にする(経路追加・update-source 追加)。否定材料
   (経路表・ping)は現行どおり提示し続ける= 提示物で錯乱肢を殺せる構造。
3. **asym_up の「なぜ UP か」**(接続レースの理解・配点40点の主役)
   → **read 形(複数選択・正解2)**で保存。事実文の真偽は d から機械導出
   (authread 方式)。「拒否ログと ADJCHANGE Up の共存」を説明できないと選べない。

追加の締め: 6択×複数選択(Choose two)・keep_ask(下記)・恒久規約
「選択肢に因果を書かない」(why は解答側)・未提示前提×消去法(BL-113)の活用。
DIFF 表(4/4/5)は変えない。

## 2. 出題形(Tier1 = 3形)

### A. dbgconf — 逆問題・単一選択・5択(全 variant)

「示されている出力を生じさせている、両ルータの BGP ネイバー構成は、どれですか。」
選択肢= `router bgp` 抜粋の**ペア**(A側+B側を1肢に併記・CLI ブロック)。

- 正解= 実像。錯乱肢= **描き直すと出力が変わる**近傍構成だけを置く(aaa dbgconf 前例)。
  軸: 各側 {neighbor 宛先: Lo/物理} × {update-source: 有/無}(ebgp では ± multihop)。
- 一意性は §4 の指紋モデルで機械検証(錯乱肢の指紋 ≠ 実像の指紋)。

### B. fix — select2・6択・正解2(addr_mismatch / ebgp_multihop)

要件文(reqs)が一意性の担い手。select2 の前例(BL-120 #8)に従う。

- **addr_mismatch**: 要件=「ループバック間でピアリングする設計を維持したまま確立させる」。
  正解2= ①B の neighbor を lo_a 宛へ是正(no neighbor 物理宛 + remote-as 再設定) 
  ②B に `neighbor lo_a update-source Loopback0`。
  錯乱肢= A を物理宛へ揃える(**直るが要件違反**・why で説明)/A に ebgp-multihop
  (iBGP に無関係)/対向 Lo への経路追加(ping 成功が否定)/`clear ip bgp *`。
  ★「A を物理宛へ」の**対になる2肢目は置かない**(組で直る二重正解の防止)。
- **ebgp_multihop**: 正解2= ①A に `ebgp-multihop 2` ②B に `ebgp-multihop 2`
  (**片側だけでは確立しない**= PoC 発見3・Choose two が最も自然)。
  錯乱肢= 静的経路の追加(字面の罠・両側の経路表提示が否定)/update-source 追加
  (`local address` 行が「既にある」ことを示す)/network 文/clear。
  ★`disable-connected-check` は**選択肢に出さない**: multihop との混成組でも確立し
  二重正解化するため。解説で別解として言及するに留める。

### C. read — 複数選択・6択・正解2(asym_up 専用)

「示されているところの出力および状態に関する記述として、正しいものは、
どれとどれですか。(2つを選択してください)」

- 真の候補(機械導出): 「確立している接続は {A} が開いたもの(送信元 lo_a)」
  「{B} 発の接続(送信元 ip_b)は {A} に拒否されている」「{B} に update-source が無い」
  「構成の非対称が残ったまま Established になっている」等から2つ抽選。
- 偽の候補: 「両側の構成は対称」「経路の障害により {B} 発の接続が失敗」
  「{A} 側の update-source が欠けている」「lo_a 宛の経路が {B} に無い」等。
- fix(単手= B へ update-source)は select2 に馴染まないため asym_up は read/dbgconf で出す。

### variant × form 抽選(mixed / --shape bgpdbg 共通)

★2026-08-16 コミット ff9afd8(BL-122)のユーザ方針「config で解決させる形を ~70% へ」を反映:

| variant | 抽選 |
|---|---|
| addr_mismatch | fix-select2 65% / dbgconf 35% |
| ebgp_multihop | fix-select2 70% / dbgconf 30% |
| asym_up | read 45% / fix(単一選択) 30% / dbgconf 25% |

- **asym_up の fix(単一選択・新設)**: 要件=「ピアの確立を維持しつつ非対称を解消」。
  正解= B に `update-source Loopback0`。決定的錯乱肢= 「A の update-source を
  **外して**対称化」(両側欠け= Idle 化・PoC 発見1(c) が根拠。対称化はするが要件
  「確立の維持」に反して切断される)。他= 物理宛への両側付け替え(要件違反)・clear。
- **鏡像錯乱肢(BL-122 の方向反転パターン)**: fix 形に「直す側を逆にした」肢を
  **1肢だけ**置く(2肢置くと組で直る二重正解が生まれるため対を成立させない)。
- **前提文常設(BL-123 パターン)**: dbgconf / read には「構成に関して判断できる
  ことは、示されている出力が全てである」旨の前提文を置き、未提示前提の
  補完余地を封じて一意性を担保する。

**essay 形の温存**: `--forms essay` 指定時のみ従来の記述式を出す(mixed には出さない)。
BL-111 で MPLS L3VPN 記述式が essay 方式を流用予定のため、機構は削除しない。

## 3. 配線(gen_paper_mcq.py)

1. **mixed ルーレット**: bgpdbg に 5% を配分。捻出= pbr 10→9 / urpf 10→9 /
   leakmap 10→9 / ospfv3pl 10→9 / chain 6→5(BGP 合計 8→13%。BL-100/111 の
   「BGP 最優先・再配送系は飽和」方針に整合)。コメントの配分表も更新。
   ※ mixed の同一 seed の出力は変わる(過去問は questions/ に生成済みで凍結・許容)。
2. **dispatch**: choices 構築(6805行付近)・form 抽選・reqs(fix 用 `bgpdbg_requirements`)
   を他 shape と同型で追加。`--kinds` プール(6602行)は既に `gpb.VARIANTS` 登録済み。
3. **question_md_bgpdbg 改修**: 選択式レイアウト(## 選択肢・A.〜・複数選択は
   「(2つを選択してください)」= render_html の `pick_count()` が拾う書式)。
   essay 分岐は従来文面を温存。文体= Cisco語規約は現行を踏襲。
4. **answer_md_bgpdbg 改修**: `## 正解\n\n**B・D**` 形式(gen_pack `key_of()` 互換)。
   ★選択式の解答 md に**「ルーブリック」の語を書かない**(key_of がこの語で
   記述式と判定し自動採点から外れる)。essay 形のみ従来のルーブリックを出す。
5. **keep_ask**: shape 全形で登録(bgpbest 前例)。理由= asym_up は「壊れていない」
   (汎用の症状文が存在しない障害を参照してしまう)・select2 は選ぶ個数が設問文の担い手。
   BL-120 の教訓「新形式は必ず keep_ask 登録」。
   `essay=(shape_i=="bgpdbg")` は `essay=(shape_i=="bgpdbg" and form=="essay")` へ。
6. **leak_lint トークン**: `addr_mismatch` / `ebgp_multihop` / `asym_up` / `variant=`。
7. `rebalance_position` は複数正解を自動スキップ(対応済み・変更不要)。

## 4. 一意性の機械検証(selftest)

gen_paper_bgpdbg.py に selftest を新設(他 shape の慣行に合わせる):

- **指紋モデル**: `signature(構成ペア) → 両側 debug 指紋`(宛先・送信元・
  refused/no-route/Up の別)を小さく実装。
  - dbgconf: 全錯乱肢の指紋 ≠ 実像の指紋 を全 seed で検証。
  - fix: 「直る判定」(各側の open が相手の neighbor 文に受理されるか+eBGP の
    connected check)で、6択から2つ選ぶ全15組合せ中、**要件を満たして直る組が
    正解の組だけ**であることを検証(混成解・二重正解の検出)。
  - read: 事実文の真偽を d から導出している時点で機械保証(authread 方式)。
- seed スイープ(600 目安)× variant × form で: 正解数(1 or 2)・選択肢の重複なし・
  記号 A-J 範囲・leak_lint。

## 5. パック側(gen_pack.py)

- `PAPER_GENRES` に `"bgp": ["bgpbest", "bgpdbg"]` を追加。
- `--require-shape` 既定を `redist,aaa,acl` → `redist,aaa,acl,bgp` へ
  (パック毎に BGP 紙面1問を保証。mixed 5% だけでは BGP ゼロのパックが出るため)。
  ★既定変更はユーザ確認の上で適用。

## 6. 検証計画(E2E)

1. selftest NG=0(全 variant × 全 form)。
2. `--shape bgpdbg --count 30 --exam`: leak_lint 通過・`choice_letters()` /
   `pick_count()` が全問で選択肢と個数を正しく拾う・`key_of()` が正解記号を読める。
3. mixed スイープ(200問規模): bgpdbg 出現率 ≈5%・他 shape の回帰(生成成功率)。
4. `gen_pack --dry-run` で bgp 必須枠の確保を確認。
5. 初出題数問(quiz フロー)で難易度の体感を確認し、抽選比・錯乱肢を調整。

## 7. 決定済み/確認事項

- 決定済み(本設計): 形式3本(dbgconf/fix-select2/read)・DIFF 維持・essay 温存・
  keep_ask 全形・disable-connected-check を選択肢に出さない。
- ユーザ確認: ①mixed の配分(bgpdbg 5%・捻出元) ②`--require-shape` 既定への bgp 追加
  ③essay を `--forms essay` で残す扱いで良いか。
