# 模範解答 : ENARSI-REDIST-BGP-LOOP-01

## なぜ壊れるか（3ドメイン再配送リングのループ）
被害プレフィクス `192.168.51.0/24` は RE が **BGP** で起点広告し、RC が **iBGP（AD 200）** で学習する。
再配送が **BGP → EIGRP → OSPF** の順に数珠つなぎ（リング）になっているため、この経路の「出自」が
ドメインを一周して RC に戻ってくる:

1. RC が `192.168.51.0/24`（iBGP）を **EIGRP** へ再配送（`bgp redistribute-internal` により iBGP も対象）。
2. RA が EIGRP で受け取り、**OSPF** へ再配送 → **O E2（AD 110）** として OSPF 域に広がる。
3. RC は OSPF にも参加しているので、この **O E2（110）** を受け取る。

ここで **戻ってきた経路の AD（OSPF 110）が、本来の iBGP（200）より低い**。RC は O E2 を優先し、
`192.168.51.0/24` 宛を **OSPF 側（RB 方向）** へ転送してしまう。すると:

```
RC ──O E2──> RB ──O E2──> RA ──EIGRP D EX──> RC ──> …（無限ループ）
```

起点 RE には決して届かず、`RC → RB → RA → RC` の **定常転送ループ**になる（TTL 超過）。
「一周して戻った経路の AD が iBGP より低い」——これが Ping-t #28776 と同じ核心。

## 解（RC）
BGP の管理距離を OSPF(110) 未満に下げ、RC が **iBGP（＝正しい起点 RE 方向）** を選ぶようにする。

```
router bgp 65000
 distance bgp 20 105 105
```

- 第2引数 **105 が iBGP（internal）の AD**。これを 110 未満にすると、RC は
  `192.168.51.0/24` を **iBGP（AD 105 < O E2 110）** で選び、次ホップ＝起点 RE になる。
- RC → RE へ直接転送 → ループ解消。RA は EIGRP(D EX)で RC 経由、RB は OSPF(O E2)で RA→RC 経由で
  最終的に RE に到達する。再配送リング（BGP→EIGRP→OSPF）自体はそのまま維持される。

### ★重要：変更後は経路の再計算が必要
`distance` は **既にインストール済みの経路には即時反映されない**。RC で

```
clear ip route *
```

を実行して初めて iBGP(105) が採用される（実行前は BGP エントリが `RIB-failure(17)` のまま残る）。
コンソールで解く場合、設定後に `show ip route 192.168.51.0` が `bgp` に変わらなければ clear すること。

## 確認
- RC: `show ip route 192.168.51.0` が **`Known via "bgp 65000", distance 105`**（O E2 ではない）。
- RC/RB/RA から `traceroute 192.168.51.1` が **RE に一直線で到達**（3台を回らない）。
- RB: 依然 `O E2 192.168.51.0/24`（リングの OSPF 注入は維持）。
- RE: `show ip route bgp` に OSPF/EIGRP 側 Loopback（戻り再配送 IGP→BGP の維持）。

## 別解（効果ベース採点なのでいずれも可）
- **`distance ospf external 205`**（RC の OSPF 外部 AD を iBGP 200 超へ）＝ RC が iBGP を優先。
  OSPF 内部経路に影響しないクリーンな別解。
- **経路タグ + フィルタ**: RC が BGP→EIGRP 再配送時に `set tag`、OSPF で戻ってきたその自ドメイン発を
  RC の OSPF 学習側（`distribute-list route-map in`）で遮断する。
- **不可**: いずれかの再配送を丸ごと削除して回避（リング設計が崩れる）、静的経路・デフォルトでの回避。

## 教育核心
- **多点再配送がドメインをまたいで「リング」を成すと、経路の出自が一周して戻る**。戻り経路の AD が
  元の学習元より低いと、そちらを優先してループ／振動する。
- 既定 AD（eBGP 20・EIGRP内部 90・OSPF 110・EIGRP外部 170・**iBGP 200**）の並びは必修。
  **iBGP は最も信用されない（200）**ため、iBGP 経路を IGP へ再配送するとこの種のループを招きやすい。
- 対策の定石は「AD 調整 / 経路タグ / メトリック調整 / フィルタリング」。本問は最小手＝
  **AD 調整（RC の BGP を OSPF 未満に）**。Ping-t #28776 と同型の思考を実機で体感する問題。
