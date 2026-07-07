# 模範解答 : ENCOR-OSPF-STUB-01

要件「area 1 の外を見る経路はデフォルトルート 1 本のみ。inter-area の個別経路も
external も入れない」は、area の性質として **Totally Stubby Area** に
すれば達成できる。ABR が type 5 (external) と type 3 (inter-area summary) の
両方を area 1 へ漏らさず、代わりに O*IA のデフォルトを 1 本だけ自動注入する。

## RT02 (ABR)
```
router ospf 1
 area 1 stub no-summary
!
```
- `stub` で type 5 (LSA 5 = external) を遮断、
- `no-summary` で type 3 (LSA 3 = inter-area summary) も遮断、
- ABR は area 1 へ O*IA 0.0.0.0/0 を自動注入する。

## RT03 (area 1 内部)
```
router ospf 1
 area 1 stub
!
```
- 内部ルータ側は `stub` のみ (`no-summary` は ABR 側だけ書く)。
- ただし **両端で area タイプが一致していないと隣接が確立しない**ため、
  RT03 側も `area 1 stub` の設定が必須。

## 確認
```
show ip ospf neighbor                   ! RT02 と FULL になっているか
show ip route ospf                      ! O*IA 0.0.0.0/0 のみが見えるか
show ip route 1.1.1.1                   ! ★ "Network not in table"
show ip route 192.0.2.0                 ! ★ "Network not in table"
show ip ospf | section "It is a stub"   ! 自身が stub area メンバである表示
```

### ポイント（落とし穴の解説）
- **両側で area タイプを揃える**: 一方だけ `area 1 stub` にすると Hello の E-bit
  ミスマッチで OSPF 隣接が確立しない。グレーディング C3 (neighbor FULL) が落ちる。
- **`no-summary` は ABR 側だけに書く**: 内部ルータに `no-summary` を書いても
  パラメータエラーになるか無効。役割が「summary を生成するかどうか」なので
  ABR でのみ意味を持つ。
- **デフォルトルートの注入は自動**: stub area を構成すると、ABR が `O*IA 0.0.0.0/0`
  を自動的に注入してくれる。受験者が `default-information originate` 等を書く
  必要は無い (むしろ書くと別の意図が混ざる)。
- **なぜ distribute-list ではダメか**: 制約で「area の性質そのもの」で解決と
  指定されている。distribute-list in は ABR/RT03 個別の RIB install を止める
  だけで LSA フラッディングは止まらず、area 1 全体に対する自然な拡張性が無い。
- **NSSA との違い**: NSSA は area 1 内に ASBR が存在する場合 (type 7 を扱う)。
  本問は area 1 内に ASBR が無いので素直に stub / totally-stub で良い。

> 採点: 両側の `area 1 stub[ no-summary]` 設定 / OSPF 隣接 FULL / O*IA デフォルト
> ルートが RT03 RIB に存在 / RT03 RIB から個別の inter-area / external が消えている
> ことを判定。
