# REDISTMP Task2 オプション — タグ是正後も残る境界 RIB 次善の是正 (OSPF distribute-list in)

- 起票: 2026-08-18(ユーザ持ち込み設計の取り込み。原案は外部 Claude 作)
- 対象: `topologies/gen_redist_mp_ts.py`(GEN-REDISTMP・BL-058 完成形)への**追加要件オプション**
- BL: BL-129
- 状態: ★★**全完了・出題可(2026-08-18)**= PoC(実機全項目成立)＋本実装
  (`gen_redist_mp_ts.py --task2 auto|on|off`)＋実機 E2E フルサイクル
  (broken 10 → 模範解答 100 → **Task1のみ 69**(部分解実証) → 再投入 100)。
  実測記録= [poc/redistmp-task2/README.md](../../poc/redistmp-task2/README.md)

## 0. 主題(1行)

**「タグによる再配送フィルタはループの伝播を止めるが、境界ルータ自身の RIB の
経路選択には一切作用しない」** — この残存事象を、`distribute-list route-map <名> in`
(OSPF 配下・match tag)による **RIB 挿入抑止**で是正させる。

## 1. 形態 = 「時々つくオプション」(ユーザ指示 2026-08-18)

独立問題ではなく、GEN-REDISTMP の生成時に **seed 抽選で時々付く追加要件**とする。
問われる時と問われない時がある、という揺らぎ自体が出題価値
(「この盤面ではどこまで要求されているか」を要件から読む訓練)。

### 発現条件

- **routemap モード限定**。理由:
  - acl / prefix モードにはタグが存在せず、match tag による将来プレフィックス
    自動追従の想定解が構成できない。
  - distance モードは AD 操作で経路選好そのものを是正する解法であり、
    「AD 変更禁止」を核とする本オプションと定義上両立しない。
- 抽選: mode==routemap 確定後に `rnd.random() < 0.5`(routemap 自体が 1/4 なので
  全体では約 12.5%=「時々」)。
- CLI: `--task2 {auto,on,off}`(既定 auto=抽選)。`on` は solution=routemap を強制
  (他モード明示指定との併用はエラー)。
- **★byte 再現性**: task2 の乱数消費は既存の全 draw(mode 抽選→rand_values)の
  **最後**に置く。off に倒れた場合を含め、既存 seed の生成物がバイト一致で
  変わらないことを回帰で保証する(GEN-MPLSEB の「既存seedバイト再現性維持」と同じ規律)。

## 2. ベース選定の根拠(記録)

- **gen_redist_mp_ts が原案の Task 1 そのもの**: RIPv2(RF)→EIGRP→OSPF の3ドメイン・
  AD 無操作・victim(192.168.x.0/24)一周再注入・`--solution routemap` = 出自タグ解
  (E→O set tag / O→E match tag deny)。
- **BL-058 採点仕様が本オプションの空白を明文化済**:「netmodel optimal は
  **RB/RC→RF を除外**=フィルタ系解法では片境界の O E2 遠回りが正常残留」。
  Task2 はこの除外を**再包含**する形で実装できる(採点設計が最初から噛み合う)。
- **twoborder(gen_redist_field)は不適**: EIGRP external AD=95 固定(会社ポリシー)が
  決定性キーのため D EX 95 < O E2 110 となり、「O E2 が D EX 170 に勝つ」という
  本オプションの現象自体が発生しない。

## 3. 事象の正確な記述(問題文・解説の前提)

Task1(タグ)完了状態では、victim について:

- 片方の境界(起点側)が D EX 170 を保持し Type-5 を生成(ASBR)。victim の Type-5 は
  **ドメイン全体で1枚**(実測確認)。
- **もう片方の境界は O E2 110 が D EX 170 に勝ち**、RIP 宛転送が
  OSPF 迂回→対向境界→EIGRP 復帰の次善パスになる(実測: 5ホップ vs 直行3ホップ)。
- ★どちらの境界が次善側になるかは**タイミング依存で非決定**(BL-058「鏡像の向きは
  非保証」)。問題文・採点は向きを断定しない。**After は両境界 D EX で決定的**。
- ★★**片側適用は「次善の引っ越し」(PoC P5 実測)**: dl-in を片境界だけに入れると、
  その境界が D EX 化+Type-5 自己生成 → **対向境界(未適用)が O E2 側に反転**して
  自分の Type-5 を取り下げる。固定的な非対称状態は存在せず、
  **次善経路が対向へ移動するだけ**。到達性は全過程で無断絶。
- 対称適用後は両境界が Type-5 を生成(**ASBR 2台化・Type-5 2枚**)。RA は O E2 のまま
  **ECMP 2経路化**(metric 同値)・到達性不変。つまり想定解は他ルータの LSDB/RDB を
  「増やす」= 採点・制約は**不変ではなく喪失禁止**で書く(§4)。
- 収束は**適用・撤去・再適用とも約1秒・clear 不要**(LSDB→RIB 再調停のみのため。
  distance の16秒より速い)。task.md の「clear ip route \*」備考はそのまま無害。

## 4. task.md への提示形

Task1/Task2 の**二段構成**にする(原案の意図を保存):

- Task1 = 既存のループ是正チケット(routemap モードの現行文面)。
- Task2 = 「Task1 の是正が**収容標準どおり正しく完了していることを前提に**、
  それでもなお残る下記事象への対応」として追記。
  Cisco語(逐語訳調)。Task1 の設定ミス扱いにしない文面を明示:
  > 「タグによる再注入対策は、当社標準に完全に準拠しているものとします。
  > その上で、境界ルータから RIP 由来プレフィックスへの転送が
  > EIGRP 隣接経由の最短パスであることを保証してください。」

### 制約(別解排除・原案4点+穴1点)

| 制約文(収容標準・Cisco語で整形) | 排除対象 |
|---|---|
| AD の変更を伴う手法を用いないこと | distance ospf external / ACL付き distance |
| Task1 で投入した再注入対策の設定は変更・削除しないこと | タグ設定の改変 |
| OSPF ドメイン内の他ルータから、当該プレフィックスの **Type-5 LSA および O E2 経路が失われない**こと(喪失禁止) | distribute-list out / 再配送点の追加フィルタ(LSA 生成抑止と RIB 挿入抑止の差異を問う仕掛け)。★原案の「変化を生じさせない」は**想定解自体が違反**(ASBR 2台化で LSDB 1→2枚・RA の RIB が ECMP 化する実測)ため喪失禁止形に是正(2026-08-18 PoC) |
| RIP ドメインへ**後日追加されるプレフィックスにも追加設定なしに**同一動作が保証されること | 静的・集約・プレフィックス単位 match |
| **経路の判定は Task1 で付与した出自タグに基づいて行う**こと(特定ルータのアドレスに依存しないこと) | ★一意性監査で発見した穴= `distribute-list prefix <全deny> gateway <対向指し> in`(プレフィックス列挙なしで将来分にも効くため原案4制約をすり抜ける) |

## 5. 想定解(唯一解)

両境界(RB/RC 相当)で対称に:

```
route-map DENY_TAG_RIB deny 10
 match tag <tag>
route-map DENY_TAG_RIB permit 20
!
router ospf <pid>
 distribute-list route-map DENY_TAG_RIB in
```

(route-map 名は自由。採点は名前を固定しない)

- 副作用の整理: SET_TAG は E→O 再配送の全経路に付くため、dl-in は境界の
  タグ付き O E2 を全て RIB 非掲載にする。EIGRP 内部発プレフィックスは
  境界では D 90 が勝っており実質 no-op(これ自体が「タグ単位の包括制御」の教材点)。

## 6. 採点設計(task2=on の時の追加分)

1. **optimal 再包含**: BL-058 で除外していた RB/RC→RF ペアを pairs に戻す(+10 相当。
   task2=off 時は現行のまま除外維持)。
2. **効果**: RB・RC 両方で `show ip route <victim>` が `Known via "eigrp <asn>"`
   (D EX)。O E2 の not_regex 併用。★このチェックだけで**対称性が機械的に強制**される
   (片側適用では反転により対向が必ず O E2 になる=PoC P5 実測)。
3. **★LSDB 保持の明示確認**: RB(または RC)で `show ip ospf database external`
   に victim の Type-5 が**タグ付きで残存**(実機表示形= `External Route Tag: <tag>`)。
   「RIB からだけ消えている」ことの直接証拠。
4. **他ルータの喪失禁止**: RA の `O E2 <victim>` 維持(既存チェック流用可)＋到達性。
   ★next-hop・RDB 数・LSDB 枚数は固定しない(想定解で ECMP 2経路・Type-5 2枚に増える)。
5. **監査(指紋+禁止)**:
   - regex: `router ospf <pid>` 配下の `distribute-list route-map \S+ in`
   - regex: 当該 route-map に `match tag <tag>`(deny 節)
   - not_regex: `(?m)^\s*distance `(既存)・`distribute-list (\d+|prefix|gateway)`
     の in 形(gateway 逃げ・ACL/prefix 直指定の遮断)・静的 ban(既存)
   - 対称性: RB・RC **両方**に指紋があること(片側のみ→降格)

## 7. Before / After 期待出力(実機採取済 2026-08-18)

全出力と regex 化に使う表示形は [poc/redistmp-task2/README.md](../../poc/redistmp-task2/README.md) に収録。要点:

- Before: 次善側境界= O E2 110(`Tag <tag>, type extern 2` / `Route tag <tag>`)・
  traceroute 5ホップ迂回・LSDB は対向発 Type-5 1枚。
- After: 両境界 D EX 170 via EIGRP 直行(3ホップ)・**LSDB の Type-5 残存**
  (`External Route Tag: <tag>`・最終状態は両境界発の2枚)・RA は O E2 維持で ECMP 化。
- 非対称(片側のみ適用): ★固定状態にならず**次善が対向境界へ移動**(役割反転)。
  解説素材として README P5 の観測列(自己 Type-5 生成→対向反転→対向 LSA 取り下げ)を使う。

## 8. 解説方針(原案の補足を強制事項として採用)

**「タグ運用は誤りで dl-in に置き換えるべき」という結論に誘導しない。**

- タグ + match tag deny(再配送点)= **ドメイン間の伝播制御**(ループ防止)。
- distribute-list route-map in(OSPF 配下)= **ローカル RIB の選択制御**。
- 担当領域が異なるため**併用**が正しい。タグを「ループ防止のため」に付けた
  はずが「経路選択のため」にも再利用できる、という一本の線で締める。
- なぜ OSPF の dl-in が LSDB に作用しないか(リンクステートの LSDB 一貫性要件)。
- 運用上の注意: dl-in は自ルータの転送にしか効かない/タグ体系の変更が
  両方の仕組みを同時に壊す単一依存点になる。
- 非対称の帰結(実測): 片側だけの適用は**次善経路を対向境界へ引っ越させるだけ**
  (適用側の ASBR 化→対向の RIB 反転→対向の LSA 取り下げ、の連鎖)。
  「直したつもりが問題が隣に移った」形として解説する。

## 9. PoC チェックリスト — **1〜6 完了(2026-08-18・POC-BL129-TASK2・撤収済)**

1. ✅ iol-xe 17.15 で受理・動作(RIB 非掲載+LSDB 保持)。
2. ✅ **clear 不要・約1秒で即時収束**(適用・撤去・再適用の3方向とも。distance の
   16秒より速い= LSDB→RIB 再調停のみ)。task.md 備考の clear 文言は無害でそのまま。
3. ✅ D EX 昇格は瞬時(EIGRP topology に候補既在)。
4. ✅ ASBR 2台化で RA の経路種別・到達性不変(ping 20/20)。★ただし LSDB 1→2枚・
   RIB は ECMP 化=「増える」→制約・採点は喪失禁止形へ是正(§3/§4/§6 反映済)。
5. ✅ 非対称= ★役割反転の発見(§3)。
6. ✅ 表示形採取済(README の表)。★`show ip protocols` の `Incoming update filter list`
   行は eigrp 節にも `not set` 同型行が出るため section 絞りか route-map 名込みで regex。
7. ✅ 回帰(2026-08-18 実装時)= --task2 off で全4モード14seed バイト一致・auto の
   非 routemap seed もバイト一致(抽選は最後尾)・採点 regex の模範解答自己整合 14/14。

## 10. 残課題・派生

- 紙面化: BL-086 ④a の shape=mploop(同盤面の紙面流用)に「dl-in の read/fix 形」を
  足せるか。錯乱肢「distribute-list out で LSDB から消える」が自然に作れる。
  → 実装完了後に別 BL として起票判断。
