# BGPBEST-PAPER — 紙面ファミリ shape=bgpbest(BGP ベストパス読解・BL-112)

2026-08-12 起案。BL-111 第1群-1「BGP 紙面2系統」の①= **1.11.c Troubleshoot BGP path preference
(attributes and best-path)**。ユーザ要求= **ENARSI の範囲をできるだけ正確に**押さえること。
**多少 ENARSI より難しいのは可・簡単は不可**。

## 1. 器の判断(2026-08-12 調査報告で確定)

ラボ側は既に厚い(`gen_bgp_ring_ts` shape=path_select 故障6種・属性単体ラボ WEIGHT/MED/ORIGIN/
NHSELF/COMM・POLICY-01・complex 26故障)。空いているのは
**「show ip bgp の表を読み、決定順序を適用して、決め手の段まで言う」訓練**で、
ラボでは構造的に問えない(ラボは結果しか採点できない)。→ **紙面のみ作る。ラボ新造なし。**

## 2. 決定リスト(モデルの正典 — Cisco IOS の実装順)

`topologies/bgpbest_model.py` に純関数 `best(paths, opts)` として実装し、
**勝者だけでなく「決めた段」と消去の遍歴**を返す(why 形・解答解説の根拠)。

| 段 | 内容 | 備考(錯乱肢の種) |
|---|---|---|
| 0 | **next-hop 解決可**が前提 | 落ちた経路は候補にすら入らない(inaccessible) |
| 1 | weight 最大 | **ローカル専用・伝播しない**。local 起源は 32768 |
| 2 | LOCAL_PREF 最大 | AS 内で iBGP 伝播。**eBGP ピアには送られない** |
| 3 | 自機起源(network/aggregate/redistribute) | 実際は weight 32768 が先に拾うことが多い |
| 4 | AS-PATH 最短 | prepend も数える |
| 5 | origin 最小 (i < e < ?) | |
| 6 | MED 最小 | **同一隣接 AS 間のみ**(`bgp always-compare-med` で解除)。**欠落=0 扱い**(`bgp bestpath med missing-as-worst` で反転) |
| 7 | eBGP > iBGP | |
| 8 | next-hop への IGP メトリック最小 | detail の `(metric N)` がこの値 |
| 10 | (eBGP同士)最古の経路 | 非決定的。`bgp bestpath compare-routerid` があると飛ぶ |
| 11 | RID 最小 | RR 経由は ORIGINATOR_ID(RR は別 shape=bgprr) |
| 13 | 近隣アドレス最小 | 盤面では使わない(並行リンクのみで発生) |

- 段 10(oldest)は非決定 → **盤面は原則 compare-routerid ありで作る**か、受信順を明示する。
  (BL-093 実測= 対角タイは oldest 勝ち・compare-routerid+RID 操作で決定化)
- 段 9(multipath)・12(cluster list)は範囲外(multipath は出さない・RR は bgprr へ)。

## 3. 盤面

視点ルータ(vantage) 1 台 + 同一プレフィックスに 3〜5 経路。提示物=
- mermaid トポロジ(AS 雲・messy_mermaid 後処理)
- **`show ip bgp` の表**(合成。書式は PoC 実測の写し= マーカー `*>`/`* i`/無印、
  eBGP 受信行の **LocPrf 空欄**、MED 欠落の Metric 空欄、Weight 0/32768、桁揃え)
- 形により **`show ip bgp <prefix>` detail**(`(metric N)`= IGP メトリック、`(inaccessible)`、
  `best` 行、`from <ip> (<RID>)`)
- 必要なら関連 config 抜粋(route-map・neighbor 行)

## 4. kinds(故障種=決め手の段/誤認の種)

**DECIDE 系(read/why/fix)** — その盤面の決め手:
`k_weight` / `k_lp` / `k_localorig`(32768 行の読み) / `k_aspath` / `k_origin` /
`k_med`(同一隣接AS) / **`k_med_cross`**(MED はあるのに異ASで比較されず後段で決まる) /
`k_ebgp` / `k_igp`(detail の metric 読み) / `k_rid`(compare-routerid 前提)。

**MISCONF 系(cause)** — 「意図した経路にならない」の原因:
`c_weight_remote`(weight を別ルータに設定=伝播しない) /
`c_lp_ebgp`(LP を eBGP ピア向け out に設定=送られない) /
`c_nh_no_self`(境界の next-hop-self 欠落→inaccessible) /
`c_remote_lp`(こちらの MED/prepend より対向 AS の LP が上=MED は助言でしかない) /
`c_med_cross`(=k_med_cross の cause 面)。

## 5. worlds(要件世界 — fix 形の正解レバー反転)

| world | 要件 | 正解レバー | 罠 |
|---|---|---|---|
| w_one_router | 影響は当該ルータに限定・他ルータの選択を変えるな | **weight** | LP は iBGP で AS 全体に効く |
| w_whole_as | AS 内全ルータが同じ出口を使うこと | **LP** | weight は 1 台にしか効かない |
| w_inbound_only | 対向 AS の機器に触れられない(往路を変えたい) | LP/weight(in) | prepend/MED out は戻りにしか効かない |
| w_return | **戻り**のトラフィックを変えたい | **prepend/MED(out)** | 自側 in の属性は往路にしか効かない |
| w_no_prepend | AS-PATH の改変禁止(戻り) | **MED(out)** | 同一隣接 AS 世界でのみ成立(異ASなら不成立→世界非両立) |

fix 形の一意性= 被覆エンジン(works= モデルで経路が要求どおり反転する候補 ≥2・
complies= 世界の制約を満たすもの =1)。**戻り系は対向 AS 視点にも同じ best() を適用**して判定する。

## 6. forms(P1 = 4 形)

- **read** — 現在のベストパスはどれか(表+決定順序の適用)。
- **why** — 決め手となった段/属性はどれか(**用語理解を文脈内で問う**。選択肢= 属性名)。
- **fix** — 要件(世界)を満たして経路を X へ変える設定はどれか(CLI 提示・被覆エンジン)。
- **cause** — 操作したのに意図どおりにならない原因はどれか(MISCONF 系・claim 機械判定)。

P2 候補: aftermath(flap 後どうなるか=oldest の主題化 / acm・missing-as-worst 投入後) /
no_clear(ポリシー変更が反映されない=clear 忘れ。bgpdbg と重複しない範囲で)。

## 7. 難易度方針(「簡単は NG」への設計答)

- 決め手を**深い段**に置く(k_med_cross→eBGP/IGP/RID まで落ちる遍歴を読ませる)。
- 表に**読み違え要素を常設**: eBGP 行の LocPrf 空欄(=100 と誤読させない)・weight 32768 行・
  無印(inaccessible)行・MED 欠落行の混在。
- 錯乱肢の型= 「**一つ上の段で決まると誤読**」「比較されない MED で選ぶ」「inaccessible を候補に入れる」。
- 選択肢に因果を書かない(BL-080)・obfuscate_md/messy_mermaid 適用(BL-087/088)。

## 8. PoC(poc/bgpbest/ — 実測してから実装)

既存実測(流用): poc/bgp-ring P4= **MED 異AS比較不発・always-compare-med は clear 不要 15 秒で反転**/
P5= **AS長タイは oldest 勝ち**/ P2/P3= **local 起源 weight 32768 勝ち**・DENIED 指紋。
ラボ実績: WEIGHT/MED/ORIGIN/NHSELF/POLICY-01(weight 罠 81 点)。

要実測(_POC-BGPBEST・IOL 6台):

| # | 項目 | 目的 |
|---|---|---|
| B1 | `show ip bgp` 表の byte 書式(eBGP LocPrf 空欄/MED 空欄/Weight/マーカー/桁) | 合成表の忠実性 |
| B2 | `show ip bgp <prefix>` detail 書式(best 行に理由が付くか/from 行/RID) | 同上 |
| B7 | origin i vs ? の決着 | 段5 |
| B8 | MED 同一隣接 AS で比較・小さい方が勝つ | 段6 |
| B10 | MED 欠落=0 扱い/missing-as-worst で反転 | 段6の既定値 |
| B11 | eBGP > iBGP(AS長・origin・MED を揃えて隔離) | 段7 |
| B12 | IGP メトリックで決着+detail の `(metric N)` 表示 | 段8 |
| B13 | compare-routerid で RID 決着(oldest の飛び) | 段10/11 |
| B15 | next-hop-self 欠落→ **inaccessible の実表示**(表のマーカー/detail) | 段0 |
| B16 | LP を eBGP ピア向け out に set したときの実挙動(送られない/警告有無) | c_lp_ebgp |

PoC トポロジ: RT01=AS65100(視点)・RT02/RT03=AS65200(同一隣接AS×2)・RT04=AS65300・
RT05/RT06=AS65100 境界(iBGP+OSPF アンダーレイ・eBGP は RT02/RT03 へ)。
全員が同一プレフィックスを起源広告。実験は neighbor shutdown と route-map 差し替えで切替。

## 9. 検証(selftest)

- `bgpbest_model.py` の selftest= PoC 実測表(B7〜B16)との一致を機械検証(aaa_model 方式)。
- 生成器 selftest= kinds×worlds×forms 全組合せ × N seed で「read/why= 正解一意」
  「fix= works≥2・complies=1」「cause= 真 claim 一意」を機械保証。
- `PYTHONHASHSEED` 1/999 で byte 同一(zlib.crc32 のみ使用)。

## 10. 参照

- 台帳= BL-112(本件)・BL-111(ロードマップ)・BL-100(ブループリント突合せ)
- 器の判断= [PAPER-BLUEPRINT-GAP.design.md](PAPER-BLUEPRINT-GAP.design.md) §8
- 実測= poc/bgp-ring/README.md(P2〜P5)・poc/bgpbest/README.md(本件・これから)

## 11. ★実装記録(2026-08-12 完了・出題可)

- 成果物= `topologies/bgpbest_model.py`(決定リスト・17 checks) /
  `topologies/gen_paper_bgpbest.py`(盤面・レンダラ・被覆・selftest 24組合せ NG=0) /
  `gen_paper_mcq.py` 統合(--shape bgpbest・--forms/--worlds・mixed 配分再調整)。
- PoC= §8 の B 全項目消化(B10 のみ**測定不能と判明**→盤面から排除)。
  実測表の正典= poc/bgpbest/README.md。PoC ラボ POC-BGPBEST は STOPPED 温存。
- §2 からの変更点:
  - 段10(oldest)= 「持続」の規則として実証(B13b)。**盤面で使う時は
    「クリア/リフレッシュ未実施」を明記**(Updated on は soft refresh でも動く)。
  - MED 欠落= 0 扱いの**比較**は未実測のまま(B10 失敗録)。モデルが strict で拒否。
  - worlds は §5 の5種から**7種**へ(nh_invalid 用に igp_frozen/bgp_frozen を追加=
    「BGP 凍結だと IGP 広告が正解」の反転が成立)。respect_med を追加し、
    return は return_med/return_prepend の対に分離。
- ★E2E(--exam 14問+mixed)で検出した欠陥と修正:
  1. **read 形は表の `*>` に答えが書いてある** → 「取り下げ直後の no best path
     過渡」(B1 実測形= `*` のみ・detail `no best path`)で提示し
     「この後選出される経路はどれか」と問う形に変更。
  2. **cause 形は不親切化(設問の汎用化)で二重正解になる**(錯乱肢に
     「一般則としては真」の記述= MED は異AS間で比較されない等を含むため。
     原因を問う文でのみ一意)→ bgpbest は**全形 keep_ask**。
  3. why 形の反証文が「差が付かない」と「絞られたが決着せず」を混同 → 区別。
- 難易度実装= 全盤面にデコイ(早い段で負ける第3経路)・eBGP 行 LocPrf 空欄・
  weight 32768 行・inaccessible 行(表では健常に見える)・MED 見せて比較させない、
  の読み違え要素を常設。
