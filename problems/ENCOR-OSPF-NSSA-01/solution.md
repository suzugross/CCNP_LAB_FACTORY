# 模範解答 : ENCOR-OSPF-NSSA-01

## 考え方
2 つの要件が同時に成り立つ area の性質は **NSSA**（さらに RIB を絞るなら **Totally NSSA**）。

- 要件1「支店ローカル外部 `198.51.100.0/24` を HQ へ配る」
  → 支店(area 1)の内部に **ASBR(RT03)** を置いて再配送したい。
  しかし **stub / totally-stub は area 内に ASBR を置けない**（Type-5 external を遮断するため
  ASBR が外部を流し込めない）。**NSSA なら Type-7 LSA で外部をエリア内に持ち込め**、
  ABR がそれを **Type-5 に変換**して backbone(area 0) へ伝える。
- 要件2「RT03 の RIB は外向きデフォルト 1 本だけ」
  → ABR 側を **`nssa no-summary`（Totally NSSA）** にすると、Type-3(inter-area summary) を
  area 1 へ漏らさず、代わりに `O*IA 0.0.0.0/0` を 1 本だけ自動注入する。

## RT02 (ABR)
```
router ospf 1
 area 1 nssa no-summary
```
- `nssa` で Type-5 を遮断しつつ Type-7→Type-5 変換を担う。
- `no-summary` で Type-3(inter-area) も遮断し、O*IA デフォルトを自動注入する。

## RT03 (支店 area 1 内部 = ASBR)
```
router ospf 1
 area 1 nssa
 redistribute static subnets
```
- `area 1 nssa`：両端で area タイプを一致させる（不一致だと隣接が確立しない）。
  内部ルータ側に `no-summary` は書かない（ABR 側だけ）。
- `redistribute static subnets`：保有する `198.51.100.0/24` を OSPF(Type-7)へ注入＝ASBR 化。

## 確認
```
! RT03
show ip ospf neighbor                 ! RT02 と FULL
show ip route ospf                    ! O*IA 0.0.0.0/0 のみ（1.1.1.1 / 2.2.2.2 は無い）
show ip ospf | include NSSA|stub      ! 自身が NSSA メンバである表示

! RT01 (HQ)
show ip route ospf                    ! ★ O E2 198.51.100.0/24 を学習（NSSA が外部を運んだ証拠）
show ip route 198.51.100.0
```

## ポイント / 落とし穴
- **stub では解けない**：area 1 内の RT03 を ASBR にしたいので Type-5 を完全遮断する stub /
  totally-stub は不可。Type-7 を扱える **NSSA** が必須。これが本問の核心。
- **両端で area タイプを揃える**：RT02 が `nssa`、RT03 も `nssa`。片側だけだと OSPF の
  オプションビット(N-bit)不一致で隣接が確立しない（C4 隣接 FULL が落ちる）。
- **`no-summary` は ABR 側だけ**：Totally NSSA にして Type-3 を止め、デフォルト 1 本に絞る。
  これで RT03 の `1.1.1.1/32` `2.2.2.2/32` が消え、`O*IA 0.0.0.0/0` だけが残る。
- **外部は ABR で Type-5 化**：RT03 の Type-7 を RT02 が Type-5 に変換するので、
  HQ(area0, RT01)では `O E2`（外部）として見える（`O N2` は NSSA 内部だけ）。
- **default-information originate は不要**：Totally NSSA の ABR がデフォルトを自動注入する。

> 採点: RT02 `area 1 nssa no-summary` / RT03 `area 1 nssa` + `redistribute static` /
> RT02-RT03 隣接 FULL / RT01 が `O E2 198.51.100.0/24` を学習 / RT03 が O*IA デフォルトを保持 /
> RT03 RIB から個別 inter-area が消えている、ことを判定。
