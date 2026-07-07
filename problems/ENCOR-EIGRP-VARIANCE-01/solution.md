# ENCOR-EIGRP-VARIANCE-01 解説（IOL 実機で 100/100 確認済み）

RT01 で **variance** と **prefix 個別のメトリック調整（offset-list 等）** を行う。設定は RT01 のみ。

## 1. RT01 上のトポロジを読む（`show ip eigrp topology 10.44.44.44/32` / `... all-links`）
実測値（wide metric）:
| 経路 | next-hop | 合計メトリック | RD | 判定 |
|------|----------|----------------|-----|------|
| via RT02 | 10.12.12.2 | **78,725,120（=FD）** | 72,171,520 | successor |
| via RT03 | 10.13.13.2 | 2,038,251,520 | **72,171,520 < FD** | **FS**（導入可） |
| via RT05 | 10.15.15.2 | 88,555,520 | **82,001,920 ≧ FD** | **非FS**（導入不可） |

- **FS 条件**：RD < 現FD。RT03 は 72,171,520 < 78,725,120 → FS。RT05 は 82,001,920 ≧ 78,725,120 → **非FS**。
- ★**罠**：RT05 の合計メトリック（88,555,520）は FD の 1.1 倍程度で「variance を上げれば入りそう」に
  見えるが、**RD ≧ FD ＝ FC 不成立**なので **variance をいくつにしても絶対に入らない**（ループ防止）。
  無理に使うには RT05 側のメトリックを下げるしかなく、offset-list（加算のみ）では下げられない＝
  「非FS は安全に使えない」が EIGRP の結論。

## 2. 最小 variance の算出
FS（RT03）を導入する最小の variance =
`⌈ FS合計 / FD ⌉ = ⌈ 2,038,251,520 / 78,725,120 ⌉ = ⌈ 25.89 ⌉ = 26`。

```
router eigrp VAR
 address-family ipv4 unicast autonomous-system 100
  topology base
   variance 26
```
→ D は via RT02（successor）と via RT03（FS）の**2 next-hop**でロードバランス。RT05 は非FSなので不参加。
（トラフィック配分はメトリック逆比＝不等分散。`traffic-share min across-interfaces` で
バックアップ扱い＝主経路のみ使用にもできる／今回は既定のまま）

## 3. E だけを単一経路に保つ（variance はグローバル）
`variance 26` は **アドレスファミリ全体**に効くため、同じ構造の E も RT03 経由で2経路化してしまう。
**E の prefix だけ** RT03 経由を variance 範囲外へ押し出す（または学習させない）。

**解1: offset-list（メトリックを底上げして範囲外へ）**
```
access-list 66 permit 10.66.66.66
router eigrp VAR
 address-family ipv4 unicast autonomous-system 100
  topology base
   offset-list 66 in 100000000 Ethernet0/1
```
RT03（Ethernet0/1）から受信する E の metric に大きな offset を加算 → `E via RT03` が `26 × FD` を
超え、RIB に入らない。D は対象外、E の successor（via RT02）も無影響。

**解2: distribute-list（E の RT03 経由を学習しない）**
```
ip prefix-list E-ONLY seq 5 deny 10.66.66.66/32
ip prefix-list E-ONLY seq 10 permit 0.0.0.0/0 le 32
router eigrp VAR
 address-family ipv4 unicast autonomous-system 100
  topology base
   distribute-list prefix E-ONLY in Ethernet0/1
```
どちらでも可（採点は「E が via RT03 を含まない・via RT02 は在る」結果で判定）。

## 検証
```
show ip route 10.44.44.44   ! via 10.12.12.2 と 10.13.13.2 の2本・10.15.15.2 は無い
show ip route 10.66.66.66   ! via 10.12.12.2 のみ
show ip eigrp topology 10.44.44.44/32   ! FD/RD と FS の確認
```

## 学びの要点
- variance は **FS しか導入しない**（非FS はループ防止で不可）。RT05 がその教材。
- 最小 variance は FD と FS 合計メトリックから**計算**する（勘で 2 などとしない）。
- variance は **AF 全体**に効くグローバル設定。**prefix 単位の制御は offset-list / distribute-list** で行う。
