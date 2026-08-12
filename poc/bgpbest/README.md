# PoC: BGP ベストパス決定リスト (BL-112) — 2026-08-12

環境: CML ラボ `POC-BGPBEST`(IOL iol-xe 17.15 ×6・console 直駆動・mgmt/SSH 不使用)。
測定= `probe.py`(B1〜B15) + `probe2.py`(再測定 B7b/B13b/B13c・新規 B17)。
生ログ= `results-raw.md`。紙面への写像= `topologies/bgpbest_model.py`(決定リスト) +
`topologies/gen_paper_bgpbest.py`(表・detail レンダラ。**実測行と byte 一致**を selftest で保証)。

トポロジ: RT01=視点(AS65100) / RT02・RT03=AS65200(同一隣接AS×2) / RT04=AS65300 /
RT05・RT06=AS65100 境界(iBGP・Lo ピア・next-hop-self・OSPF cost 10/100)。
全員が 198.51.100.0/24 を起源広告。

## 結論サマリ

| # | 項目 | 結果 |
|---|------|------|
| B1/B2 | 表・detail・summary の byte 書式 | ✅ 採取(下の「表示規則」) |
| B3 | weight 40000 が全段に先行 | ✅ AS長最短・他条件同でも weight 側が best |
| B4 | LP 200 > AS-PATH 長 | ✅ prepend×3 の最長経路が LP で best。**iBGP ピアへ LP 200 のまま伝播**も確認 |
| B5 | 自機起源 = weight 32768 | ✅ 表= `0.0.0.0`/`32768`/Path列 `i` のみ。detail= `valid, sourced, local` |
| B7b | origin i < ? | ✅ 全条件同で Origin IGP 側が best(detail= `Origin incomplete`) |
| B8 | MED 同一隣接AS 比較 | ✅ 50 vs 200 → 50。値入替で反転 |
| B9 | MED 異AS 不比較 | (bgp-ring P4 で実測済み: 比較されず・acm 投入で clear 不要 15 秒反転) |
| B10 | MED 欠落=0 / missing-as-worst | ⚠️ **測定不能**(下の失敗録②)。盤面から排除(モデルが strict で拒否) |
| B11 | eBGP > iBGP | ✅ AS長・origin 同で eBGP 側。eBGP 断で iBGP へフォールバック |
| B12 | next-hop への IGP メトリック | ✅ `(metric 11)` vs `(metric 101)`。**OSPF cost 入替だけで clear 無しで反転** |
| B13b | ★oldest の持続 | ✅ **best 側を flap → 対抗が best を取り、戻ってきた旧 best(新しい)は奪還できない** |
| B13c | ★compare-routerid > oldest | ✅ older=RID大 の状態で投入 → **clear 無し・11 秒で RID 小へ反転**。detail 冒頭に `BGP Bestpath: compare-routerid` |
| B15 | next-hop 解決不能 | ✅ **表では `* i` のまま(見分け不可)**。detail の `(inaccessible)` が唯一の証拠。best は他方へ |
| B16 | LP を eBGP ピアへ set out | ✅ **送られない**(受信側 localpref 100 のまま)。設定は無警告で受理される |
| B17 | ★真の MED 欠落(2 AS ホップ) | ✅ 表= **Metric 列が完全空欄**・detail= **`metric N,` 句ごと消える**。隣接 AS までは MED 到達(非遷移の実証) |

## 表示規則(紙面レンダラの正典・全て実測写し)

1. **表の桁**: Metric 右端= 49 桁目 / LocPrf 右端= 56 / Weight 右端= 63 / Path は 65 桁目から。
   ネットワーク列は先頭行のみ・継続行は空欄 17 桁。
2. **マーカー**: 2 文字目 `*`(valid)・3 文字目 `>`(best)・4 文字目 `i`(internal)。
   ★**inaccessible でも `*` が付く**(B15)= 表からは見分けられない。
3. **LocPrf 列**: iBGP 受信行= `100`(既定値も表示) / eBGP 受信行= **空欄**(既定 100 は出ない) /
   in 方向 route-map で set した eBGP 行= その値が出る(B4) / **自機起源行= 空欄**(B5)。
4. **Metric(MED) 列**: 有値(0 含む)= その数字。**欠落= 完全空欄**(B17)。
   network/redistribute 起源は必ず MED を付ける(=0)ので、空欄は「AS を 2 つ以上
   跨いだ経路」でだけ自然発生する(MED は非遷移・B17 で RT03 まで届き RT01 で消えるのを確認)。
5. **detail の属性行**: `Origin <IGP|EGP|incomplete>, [metric N, ]localpref N,
   [weight N, ]valid, <external|internal|sourced, local>[, best]`。
   ★MED 欠落時は `metric N,` 句ごと出ない(B17)。localpref は常に出る(表と非対称)。
6. **detail の nh 行**: `<nh>[ (metric N)][ (inaccessible)] from <peer> (<RID>)`。
   `(metric N)`= next-hop への IGP メトリック(段8 の唯一の観測点・B12)。
   next-hop-self 欠落時の nh は**外部区間のアドレスのまま**・from はピア(B15)。
7. **detail 冒頭**: bestpath ノブ設定時のみ `BGP Bestpath: compare-routerid` /
   `BGP Bestpath: med`(missing-as-worst) の状態行(B13c/B10)。
8. **並び順**: 表・detail とも**新しい経路が上**(B13b の flap で逐次確認)。
   `best #N` は detail の並びの 1-based 位置。
9. **Network 列の表記**: classful 一致(例 198.51.100.0=クラスC /24)は長さ無し・
   非一致(172.20.77.0/24)は `/24` 付き(B17)。
10. `show run | section router bgp`: neighbor は **IP 昇順**・neighbor 配下は
    remote-as→(shutdown)→update-source・AF 配下は activate→next-hop-self→
    route-map→weight(語のアルファベット順)。
11. おまけ: `r>`(RIB-failure)の実物を採取(redistribute connected が自機の
    connected と衝突した行・probe2 B7b の表)。将来の錯乱肢素材。

## 挙動規則(モデルの正典)

- 決定順序の実証: weight(B3) → LP(B4) → 自機起源32768(B5・bgp-ring P2/P3) →
  AS長(B4 の対照) → origin(B7b) → MED 同一隣接AS(B8) → eBGP>iBGP(B11) →
  IGP メトリック(B12) → oldest(B13b) → RID(B13c)。
- **oldest は「持続」の規則**: 新しい等価経路は既存 best を奪えない。flap した旧 best は
  戻っても新参なので奪還できない(B13b・判別方向で実証)。
- **compare-routerid は oldest を飛ばす**: 投入は clear 不要(11 秒・B13c)。
  同様に missing-as-worst 投入も再計算を誘発した(B10 の残骸で確認)。
- **LP は eBGP セッションへ送られない**(B16)。route-map の設定は無警告で受理される
  =「設定はあるのに効かない」型の罠として成立。
- OSPF cost 変更→BGP ベスト再計算は自動(clear 不要・B12。反応時間の実測は
  パーサ不備で取れず。60 秒スキャナ以内とだけ言える)。
- ★**NHT の過渡**: 新着経路は検証前の数秒間 `(inaccessible)`+`no best path` になる
  (B1 初回採取)。また b1 基線で「セッション確立順と oldest が食い違う」事例を観測
  = oldest の実体は**有効化(検証完了)の順**であり受信順とは限らない。
  → **紙面で oldest を使う盤面は、受信順を本文で明示する**(Updated on だけに頼らせない。
  Updated on は soft refresh でも更新されてしまう・B16 で確認)。

## 失敗録(測定設計の誤り・チェックリスト規則 12)

1. **B7 初回= Null0 静的が connected に負けた**: `ip route 198.51.100.0 ... Null0` は
   Lo100 の connected(AD 0)に負けて RIB に入らず、`redistribute static` が空振り
   =経路が消えただけの盤面を「origin の測定」と誤認しかけた。
   対照(経路数)で気づいた。redistribute connected でやり直し(B7b)。
2. **B10= 「route-map を外せば MED 欠落」は誤り**: network 起源は常に MED=0 を
   **付けて**広告する。欠落は 2 AS ホップでしか作れない(B17 で作った)。
   「欠落 vs 有値」の比較そのものは**未実測のまま**なので、モデルは strict で
   その盤面を拒否する(`med_default_exercised`)。
3. **probe.py の best 検出**: `", best" in line` が `Paths: (5 available, best #4...`
   の見出しに先に一致し全 wait が空振り(採取は長い timeout に救われた)。
   probe2 で修正(`Origin` 行に限定)。**flap 対象の選定がこれに依存していた**ため
   B13 初回は非 best を flap してしまい判別力が無かった(B13b で是正)。

## 紙面(shape=bgpbest)への反映

- kinds= 決め手 11 種(weight/lp/localorig/aspath/origin/med/med_cross/ebgp/igp/rid/
  nh_invalid)+誤認 3 種(weight_remote/lp_ebgp/remote_lp)。
- worlds= one_router(→weight)/whole_as(→LP)/return_med(→MED out)/return_prepend
  (→prepend)/respect_med(→acm)/igp_frozen(→next-hop-self)/bgp_frozen(→IGP 広告)。
- モデルの strict 拒否= MED 順序依存盤面・MED 欠落 vs 有値の比較盤面。
- 表・detail は上の表示規則の写し。selftest が実測行との byte 一致を毎回検査する。
