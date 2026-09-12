# 模範解答 : GEN-REDISTMP-20461(solution=routemap+task2)

## なぜ壊れるか(多点相互再配送×seed metric の定常ループ 型)
`192.168.27.0/24` は RIP 発。RF が EIGRP へ再配送し(D EX・AD 170)、境界 RB/RC が
EIGRP→OSPF へ再配送(O E2・AD 110)、それが**もう一方の境界で OSPF→EIGRP に再注入**される。

- 境界では **O E2(110) が D EX(170) に勝つ**ため、片方の境界(鏡像はどちらでも)が
  「OSPF 勝ち=再注入源」、他方が「EIGRP 勝ち=Type-5 起点」に**役割分担して固定**される。
- RD から見ると候補は 2 つとも D EX(170) だが、**再注入点の方が 1 ホップ近い**ため
  seed metric 起算の合成メトリックが小さく、RD は誤った方(境界向き)を選ぶ。
- 結果、`RA→(境界)→RD→(逆側境界)→RA` の **4 台定常転送ループ**。AD は一切
  操作していないのに成立するのが本問の核心(教科書的な AD 逆転とは別物)。

### 診断の決定打
- RD `show ip eigrp topology 192.168.27.0/24` : 候補が 2 つ見え、External data の
  **External protocol が片方 OSPF・片方 RIP**。「EIGRP の外部経路なのに出自が OSPF」
  =どこかで一周して戻ってきた再注入の動かぬ証拠。
- 境界の `show ip route 192.168.27.0` : 片方が `Known via "ospf 31"` で
  `Advertised by eigrp 61 ...` 表示(=OSPF 勝ち側が EIGRP へ再注入している)。

## 解(RB・RC の**両方**に投入)
```
route-map SET-TAG permit 10
 set tag 347
!
route-map DENY-TAG deny 10
 match tag 347
route-map DENY-TAG permit 20
!
router ospf 31
 redistribute eigrp 61 subnets route-map SET-TAG
router eigrp 61
 redistribute ospf 31 metric 1000000 1 255 1 1500 route-map DENY-TAG
```
**出自マーキング**: EIGRP→OSPF で入った経路すべてにタグ 347 を焼き、OSPF→EIGRP の
再配送でタグ 347 を弾く。被害プレフィクスを名指ししないので、**将来 RIP 側に別の
プレフィクスが増えても自動で守られる**(実務のベストプラクティス形)。
`DENY-TAG permit 20`(素通し)を忘れると OSPF 発の正常経路まで全滅する(暗黙 deny)。

**片側だけ**直すと、逆向きの再注入が残って**鏡像のループが継続**する(2 点相互再配送の
定石: 対策は必ず両境界に対で入れる)。

## 確認
- RD: `show ip route 192.168.27.0` が `via 172.16.27.5`(RE 方向)へ復帰。
- RA: `traceroute 192.168.27.6` が RA→(境界)→RD→RE→RF で完走(巡回しない)。
- フィルタ系解法では、片側境界の `192.168.27.0` が O E2(遠回りだが到達可)のまま残るのは
  **正常**(O→E 再注入だけを止めたため。距離調整版では両境界とも EIGRP 直行になる)。
  ※ ただし本問は **Task 2 でこの残存を是正する**(下記)。
## 教育核心
- **多点(2 点以上)相互再配送**は、出自が一周して戻る**フィードバック経路**を必ず作る。
  防御は①再配送点フィルタ(distribute-list out)②出自タグ③AD 調整④メトリック劣化の
  4 家系 — 本問は監査ポリシーで routemap 家系を指定して解かせる形。
- `distribute-list <list> out <protocol>` の **out+プロトコル引数**は「再配送の入口で
  絞る」ための構文(ネイバー向け out とは別物)。ENARSI 頻出。

## Task 2 : タグ是正後も残る境界の次善経路

### なぜタグだけでは残るのか(伝播制御と経路選択の分離)
DENY-TAG が止めるのは **O→E 再配送(=ドメイン間の伝播)** だけで、境界ルータ自身の
RIB の勝敗(O E2 110 vs D EX 170)には一切作用しない。Task 1 完了時点では
victim の Type-5 を生成できるのは片方の境界だけ — もう片方は対向発の O E2 が勝ち、
`redistribute eigrp` の拾う対象(EIGRP の RIB 経路)を失って LSA を生成しない。
この「OSPF 勝ち側」境界の転送が、OSPF 迂回(5 ホップ)の次善パスになる。
**これは Task 1 の設定ミスではなく、タグ運用が構造的にカバーしない領域**である。

### 解(RB・RC の**両方**に投入)
```
route-map DENY-TAG-RIB deny 10
 match tag 347
route-map DENY-TAG-RIB permit 20
!
router ospf 31
 distribute-list route-map DENY-TAG-RIB in
```

OSPF の `distribute-list ... in` は **LSA/LSDB には一切作用せず、LSDB→RIB の
挿入だけを抑止**する(リンクステートは LSDB の一貫性を壊せないため、ディスタンス
ベクタの distribute-list とは根本的に別物)。タグ 347 の O E2 が RIB に入らなく
なった結果、D EX 170 が昇格して EIGRP 隣接直行(3 ホップ)へ切り替わる。
実測では適用・撤去とも**約 1 秒で収束・`clear ip route *` 不要**。

### 片側だけ入れると何が起きるか(実測)
適用側が D EX 化して Type-5 を自己生成した瞬間、**未適用側が O E2 に反転**して
自分の Type-5 を取り下げる — 次善経路は消えず**対向境界へ引っ越すだけ**。
固定的な非対称状態は存在しない。対策は必ず両境界に対で入れる(Task 1 と同じ定石)。

### 確認(Before/After)
- 両境界: `show ip route 192.168.27.0` が `Known via "eigrp 61"`(D EX・直行)。
- 両境界: `show ip ospf database external 192.168.27.0` に Type-5 が**残存**
  (`External Route Tag: 347`)。**RIB からだけ消えている**ことが本問の核心の証拠。
  最終状態では両境界が ASBR 化し LSA は 2 枚(正常)。
- RA: O E2 のまま維持(ECMP 2 経路化は正常)・到達性不変。

### 教育核心(Task 1 との関係=置換ではなく併用)
- タグ＋DENY-TAG(再配送点) = **ドメイン間の伝播制御**(ループ防止)。
- DENY-TAG-RIB(distribute-list in) = **ローカル RIB の選択制御**(次善排除)。
- 担当する問題が異なるため**両者は併用する** — Task 1 で焼いた出自タグが
  Task 2 の判定材料にそのまま再利用できるのが、出自マーキング方式の配当。
- 運用上の注意: dl-in は設定したルータ自身の転送にしか効かない。また、
  タグ体系の変更は伝播制御と選択制御の**両方を同時に壊す単一依存点**になる。
