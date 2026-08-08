# BGP-RING-TS design — 4台リング×AS配置抽選の統一BGP TS生成器（BL-093）

> **status: 全完了(2026-08-06)**。gen_bgp_ring_ts.py 実装済・5shape×解法軸×複合の
> 実機E2E 11サイクル全通過(broken 0〜75→fix→100)・CATALOG掲載済・出題可。
> 実装知見: ①netmodel は next-hop→所有者の直マップで **iBGP の Lo0 next-hop を
> 解決できない(unknown_nh)** → one_as は invariant を使わず対角 ping(source Lo1)採点
> ②grade.py の regex は MULTILINE 無し→行アンカーは `(?m)` 前置
> ③no_transit のトランジット発生・path_select の症状向きは compare-routerid＋RID
> 操作(swap_rid)で決定化(PoC知見の実装形)。

2026-08-05 ユーザ発案。4台リングトポロジー上で最大4AS（ときには全iBGP）を抽選し、
「ISP越し自社AS経路交換不能 / 非トランジット化 / 不要設定の残骸撤去 / 経路選択」
という**AS設計・ポリシー層のTS**を1つの生成器で出し分ける。
8/1以降の紙面問題(Cisco語・極度の曖昧さ)と同レベル・同文体を task.md に適用する初のラボ問。

## 1. 位置づけ・既存資産との棲み分け

| 既存 | 内容 | 本件との差 |
|------|------|-----------|
| gen_bgp_complex_ts | 7台4AS・26故障 | あちらは**到達性の配管**(session/activate/IGP連鎖)が主戦場。本件はセッション健全前提で**AS設計・ポリシー層**を主戦場にする(配管故障は複合時の脇役まで) |
| gen_bgp_pathts | 4台4ASダイヤモンド・LP/prepend 5故障 | 本件 shape=path_select はその**上位互換**(weight/MED/always-compare-med/残骸軸を追加・AS配置も抽選)。pathts は温存するが新規出題は本件へ移行 |
| gen_bgp_rrts | RRスター・iBGP伝播 | RR形はスターのまま存置。本件の全iBGP形は**フルメッシュ欠落**(スプリットホライズン)側を担当し RR は扱わない(重複回避) |
| ENARSI-BGP-SYNC-01 | sync残骸 | 「残骸撤去」の先行例。本件 shape=stale は as-override/allowas-in/weight の残骸で差別化 |

- 生成器: `topologies/gen_bgp_ring_ts.py` / 問題ID: **`GEN-BGPRING-<seed>`**
  （gen_redist_field 方式=IDから盤面・シナリオが割れない。リングであることだけは図で見える）
- 4 IOL・データIF 2本/台(+Lo0)で IOL 3本上限に余裕。lab_up 高速・常設4台で全shape共通。

## 2. 盤面（AS配置の抽選が最初のレイヤ）

物理は常に固定リング: RT01–RT02–RT03–RT04–RT01（/30×4区間・値はseed抽選）。
**AS配置 = layout を seed 抽選**し、layout が使える shape の集合を決める:

| layout | AS配置 | 使えるshape |
|--------|--------|-------------|
| `four_as` | 全台別AS(64512–65534抽選) | no_transit / stale / path_select |
| `split_company` | RT01・RT03=自社**同一AS**(対角・非隣接)、RT02/RT04=ISP-A/ISP-B | isp_exchange / path_select |
| `one_as` | 全台同一AS(全iBGP・Lo0ピア・OSPFアンダーレイ) | ibgp_ring / path_select(LP/weightのみ) |

- 各台 Lo0(ピア用・one_as/split_companyではIGPに載せる)＋Lo1(検証プレフィックス・BGPのみで広告)。
- BGP は AF 書式必須(規約)。`no bgp default ipv4-unicast`＋`address-family ipv4 unicast`。
- 解答者は最初に `show ip bgp summary` 等で **AS境界の地図を自分で描く**ところから始まる
  （task.md には AS 配置を書かない曖昧さ装置。→§6）。

## 3. shape カタログ（seed抽選・--shape で強制可）

### 3.1 `isp_exchange` — ISP越しの自社AS経路交換ができない（ユーザ例1）
- layout=split_company 固定。自社2拠点(RT01/RT03)が同一ASで、ISP-A(RT02)・ISP-B(RT04)の
  両方に接続。**ISP 2台は変更禁止**（曖昧表現で示す→§6）。
- 故障の核: eBGP ループ検知で対向拠点の経路が **`DENIED due to: AS-PATH contains our own AS`**
  （L3VPN-05 実機済指紋）。正解= 自社側 `neighbor <ISP> allowas-in`（両拠点×両ISP分）。
- 変種(seed抽選):
  - `allowas_full`: 両経路とも死んでいる(素の状態)。
  - `allowas_partial`: 片ISP経由だけ誰かが allowas-in 済→「片系のみ疎通・冗長性がない」チケット
    （症状が地味で切り分けが難しい上級形）。
  - `override_partial`(★PoC実証済): **ISP側の as-override 残骸**で片側だけ通る。受理側の
    パスは `65002 65002`(隣接重複指紋)・反対系は経路なし。fix方向(allowas-in統一 or 撤去)は
    監査要件で強制。「不要な as-override を消す」というユーザ例3を実害付きで回収する本命形。
  - `localas_alt`(後日変種): 監査要件で allowas-in 禁止→ `neighbor local-as ... no-prepend replace-as`
    解を強制(filter道場で replace-as 実機済)。v1 では見送り可。
- 採点: 両拠点で対向 Lo1 の BGP 経路有(regex)＋ping、**冗長性**=ISP片系 shutdown 後も疎通
  (これは採点しづらいので v1 は `show ip bgp` に2経路(paths)あることの regex で代替)。

### 3.2 `no_transit` — 非トランジットAS化（ユーザ例2）
- layout=four_as。RT01=自社(ISP-A/ISP-B にデュアルホーム)、RT02/RT04=ISP、RT03=遠方AS(起源)。
- broken 状態 = フィルタ無しで RT01 が ISP-A⇄ISP-B のトランジットに使われている
  （リングなので ISP から見て RT01 経由が最短になる区間が必ずある）。
- チケット: 「自社の回線に、他社間の通信が流入している、という報告」(帯域苦情の体裁)。
- **解法強制軸**(gen_redist_mp_ts 方式・seed抽選):
  - `--solution aspath` : 監査「プレフィックスの個別列挙は、許可されていません」
    → `ip as-path access-list N permit ^$` ＋ filter-list out 両ISP向け。
  - `--solution routemap`: 監査「filter-list の使用は、許可されていません」
    → route-map(match as-path or prefix-list)＋ neighbor out。
  - 他解法禁止は not_regex で担保(§7 の空出力PASS罠に注意)。
- 正の要件を必ず対で採点: 自社 Lo1 は両ISPに広告され続けること(絞りすぎ検出)。

### 3.3 `stale` — 全部別ASなのに不要設定が残っている→撤去（ユーザ例3）【PoCで再設計済】
- layout=four_as。「機器リプレース時に旧環境の設定が誤って restore された」体裁(DMVPN 31010 と同じ物語装置)。
- **★PoC結果(2026-08-05)による再設計**: as-override/allowas-in 残骸は素の4ASリングでは
  **完全不発**(受信側の AS-PATH＋**NEXTHOP is our own address** 二重チェックで直接折返しが
  入らず、一周パスは健全リングでは最短AS勝ちで伝播しない。poc/bgp-ring/README.md P2/P3)。
  → 主役を差し替え:
  - `stale_weight`(主役): 旧設計の `neighbor ... weight <大>` 残骸。**weightはLP/ASパスより
    先に評価**されるため、正しいLP/prepend設計が「設定はあるのに効かない」＋隣接prefixすら
    遠回り(3AS経路がベスト化)。(ユーザ例4の裏面もここで回収)
  - `stale_lp`(主役): inbound route-map の set local-preference 残骸。同上の実害系。
  - `stale_maxprefix`(候補): 小さすぎる maximum-prefix 残骸→セッションフラップ/Idle(PfxCt超過)。
  - `stale_as_override`/`stale_allowas_in`: **実害なしの残骸**として監査是正形の撤去対象 or
    紙面 cause 形(「この設定は何に影響しているか→実は不発。機構を説明させる」CCIE nuance)。
    実害を伴う形は split_company 変種(§3.1)で出す。
- 出題は**監査是正形**(L3VPN-05 形): 設計書に「ASパスは実際の経由ASを正しく反映していること」
  「近隣ごとの重み付けは使用されていないこと」等を書き、残骸の存在は明示しない。
- fix: 残骸削除＋ clear(inbound 系の付け外しは **`clear ip bgp <nbr> in` ハード**が確実。
  soft in はポリシー付替え直後に不発の実測あり)。task.md には書かない(切り分け技能の一部)。
- 定常性リスクは解消: 観測した全状態で**安定・振動なし**(PoC実測)。

### 3.4 `path_select` — 経路選択（ユーザ例4）
- 全layoutで成立(one_asではLP/weightのみ)。リングは常に「時計回り/反時計回り」の2経路を持つ
  ので、設計書で向きを指定→壊す、が自然に組める。
- 故障軸(欠落と誤適用の両方・seed抽選):
  - `lp_missing / lp_wrong_nbr / lp_wrong_dir`(inで設定すべきをoutに等)
  - `prepend_missing / prepend_wrong_nbr`
  - `weight_missing / weight_on_wrong_rtr`(★weightは非伝播=ローカル限り、を突く定番)
  - `med_missing`: 設計書「MEDで着信経路を制御」だが MED 未設定。
  - `med_cross_as`(★PoC実証済): **MEDは設定済みなのに効かない**。★盤面はPoCで修正:
    MEDは非推移属性で起源ASの値は非隣接に届かないため、「対角prefixの2経路に両ISPが
    各自MEDを付ける」形で構成する。異AS間は既定で比較されず MED小側が負ける症状を実測。
    正解= `bgp always-compare-med`(**clear不要・15秒以内に自動再計算**を実測)。
    AS長が違う組はMED以前にAS長で決まる=錯乱肢素材。
- pathts と違い PRIMARY/BACKUP のラベルは付けず、設計書の記述(Cisco語)から向きを読み取らせる。

### 3.5 `ibgp_ring` — 全iBGP（ユーザ例の「ときにはすべてIBGP」）
- layout=one_as。物理リング＋OSPFアンダーレイ、iBGPはLo0ピア。
- 故障軸: `mesh_session_missing`(フルメッシュ欠落→**スプリットホライズンで対角の経路だけ来ない**。
  全セッションEstablishedなのに、という指紋)/ `nexthop_self_missing`(eBGP注入点を将来外部付きに
  拡張したときの軸・v1では外部相当をRT03のstatic+redistで模擬) / `update_source_missing`。
- gen_bgp_complex_ts と被る軸だが、4台リングでは「どの2台間のメッシュが欠けたか」を
  経路の欠け方(どの対角が見えないか)から逆算する切り分けが主題になり、7台版より純度が高い。

## 4. 故障数・複合規則

- 既定 `--faults 1`(shape の主故障のみ)。`--faults 2` で **1ルータ1故障**(DMVPN 16故障の規則を踏襲)、
  shape 主故障＋別レイヤ(stale残骸 or 配管系1種)の複合。難易度: 単発=難4 / 複合=難5。
- decoy(無害な囮設定・gen_bgp_pathts 方式)を全shapeで1〜2個注入
  (例: 使われていない route-map 定義・prefix-list 残骸。20260805-002 の RM-STG1 と同じ趣向)。

## 5. 採点設計

- 収集は SSH(IOL)。grade.yml regex/not_regex ＋ ping 実効。
- ASパス検証は `show ip bgp <prefix>` の Path 行 regex(例: stale では `65002 65002` が**消えている**こと
  ＋正しい経由ASの並びが**在る**こと、を対で)。
- not_regex 単独は空出力でPASSする罠(DHCPリレー知見)→ 必ず同一コマンドの正 regex とペアにする。
- 負の要件(トランジット遮断)は「ISP側で経路が消えた」regex＋「自社経路は残っている」regex の対。
- 経路選択は gen_pathctrl 型 raw(向き=next-hop IP の有無)。ECMP 化も FAIL にする(prepend欠落の検出)。
- clear が必要な故障(stale系・LP変更)があるため、採点前の温め(P2a 方式)は不要だが
  **fix.json の適用後に clear ip bgp \* を含める**(fix_generated.yml 互換の match:none パススルー)。

## 6. task.md の文体（本件の要件の半分はここ）

8/1以降の紙面問題(20260802-004〜20260805-002)と同じ **Cisco語**(恒久規約 2026-08-02)を
ラボ問 task.md に初適用する。装置:

1. **逐語訳調**: 「〜であるところの」「〜という理由により」「示されているところの」を要件文に散らす。
2. **変更禁止対象を名指ししない**: 「お客様に対して事前に通知が行われていないという理由により、
   **貴社の管理下にないデバイス**に対する構成の変更は、許可されていません」
   → どれが管理下かは AS 配置を自分で読んで確定させる(ISP=管理外、が読み)。
3. **AS配置・ピア一覧を表で与えない**: リンク一覧(物理)だけ与える。論理(AS/ピア)は実機で調べる。
4. **要件は結果でしか書かない**: 「他の組織の間のトラフィックが、貴社のASを、経由してはなりません」
   (filter-list とも as-path とも書かない。解法指定は監査文の禁止形でのみ行う)。
5. チケット文は申告の体裁(「〜という報告が、複数の拠点から、寄せられています」)。
   原因数は「1か所とは限らない」定型で伏せる。
6. ヒント抑制規約([[ccnp-problem-hint-policy]])どおり、show コマンド例の提示は最小限
   (DMVPN 31010 より絞る方向)。

## 7. 出力パック構成

problems/GEN-BGPRING-<seed>/
- task.md（上記文体・図は物理リングのみ・messy化は紙面転用時のみ）
- topology.yml / initial/（broken day0）/ grading/grade.yml
- solution/（正解config断片・fix.json＝fix_generated.yml 互換・解説.md に shape/layout 種明かし）
- params/base.yml（紙面転用・再現用の盤面パラメータ）

## 8. PoC 結果（2026-08-05 実施・全6項目消化。詳細= [poc/bgp-ring/README.md](../../poc/bgp-ring/README.md)）

| # | 確認事項 | 結果 |
|---|----------|------|
| P1 | split_company: DENIED指紋→allowas-in復旧＋ISP側as-override残骸の非対称変種 | ✅ 成立(変種込み)。DENIED句の読み分け(対角=ASパスのみ/折返し=+NEXTHOP)も採取 |
| P2 | stale_as_override の定常性・指紋 | ⚠️ **素の4ASリングでは不発**(NEXTHOPチェック機構を解明)。主役を weight/LP 残骸へ差替え(§3.3)。全状態で安定・振動なし |
| P3 | stale_allowas_in 一周戻り | ⚠️ 受理・テーブル汚染は成立するが実害なし(自prefixはlocal勝ち)。§3.3の扱いへ |
| P4 | med_cross_as | ✅ 成立。盤面は「両ISPが各自MED」形へ修正。always-compare-med は clear不要 |
| P5 | no_transit 両解 | ✅ 成立。基線タイのoldest勝ちで自然にトランジット発生。soft out 即時 |
| P6 | ibgp_ring 対角欠け | ✅ 成立。全Established・対角のみ相互欠落・中継は保持しても反射しない |

★実装で必ず守る運用知見: ①対角タイは oldest 勝ちで非決定的→**生成器はポリシー固定 or
`bgp bestpath compare-routerid` を焼く** ②BGPプロセス作り直し直後は read-only(update-delay
120s)で PfxRcd 0 が続く→採点は2分待ち or update-delay 短縮 ③inbound ポリシー付替えの
fix 手順は `clear ip bgp <nbr> in`(ハード)標準 ④advertised-routes は as-override
書き換え前表示(wire と食い違う=罠素材)。

## 9. フェーズと規模

1. **PoC**(半日): §8。P2 の結果で stale の出題形を確定。
2. **実装**(1日): gen_bgp_complex_ts の3層構造(build_model/FAULTS/render)を流用。
   v1 shape= isp_exchange / no_transit / path_select / ibgp_ring（stale は P2 の結果次第で v1 か v1.1）。
3. **実機検証**(1日): shape×主故障の全スイープ(broken→fix→100)＋複合1本。CATALOG追記。
4. **紙面転用**(後日・BL-082①と合流): cause 形(「最も適切な説明はどれか」)は本件の盤面が
   そのまま gen_paper_mcq の新 shape になる(med_cross_as / stale_weight / スプリットホライズン
   は紙面向きの好素材)。params/base.yml を紙面パイプラインに渡す(mploop 方式)。

## 10. 未決事項（着手時にユーザ確認）

- stale が P2 で振動した場合: 紙面送りにするか、症状を「フラップの証跡読解」としてラボに残すか。
- isp_exchange の冗長性採点(片系断テスト)を v1 でやるか(採点が重い)。
- 難易度既定: 単発を難4に置いたが、no_transit 単発は難3寄り。--hard 相当(複合既定化)を作るか。
