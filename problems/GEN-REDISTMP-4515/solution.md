# 模範解答 : GEN-REDISTMP-4515(solution=routemap)

## なぜ壊れるか(多点相互再配送×seed metric の定常ループ・Ping-t #26308 型)
`192.168.94.0/24` は RIP 発。RF が EIGRP へ再配送し(D EX・AD 170)、境界 RB/RC が
EIGRP→OSPF へ再配送(O E2・AD 110)、それが**もう一方の境界で OSPF→EIGRP に再注入**される。

- 境界では **O E2(110) が D EX(170) に勝つ**ため、片方の境界(鏡像はどちらでも)が
  「OSPF 勝ち=再注入源」、他方が「EIGRP 勝ち=Type-5 起点」に**役割分担して固定**される。
- RD から見ると候補は 2 つとも D EX(170) だが、**再注入点の方が 1 ホップ近い**ため
  seed metric 起算の合成メトリックが小さく、RD は誤った方(境界向き)を選ぶ。
- 結果、`RA→(境界)→RD→(逆側境界)→RA` の **4 台定常転送ループ**。AD は一切
  操作していないのに成立するのが本問の核心(教科書的な AD 逆転とは別物)。

### 診断の決定打
- RD `show ip eigrp topology 192.168.94.0/24` : 候補が 2 つ見え、External data の
  **External protocol が片方 OSPF・片方 RIP**。「EIGRP の外部経路なのに出自が OSPF」
  =どこかで一周して戻ってきた再注入の動かぬ証拠。
- 境界の `show ip route 192.168.94.0` : 片方が `Known via "ospf 91"` で
  `Advertised by eigrp 15 ...` 表示(=OSPF 勝ち側が EIGRP へ再注入している)。

## 解(RB・RC の**両方**に投入)
```
route-map SET-TAG permit 10
 set tag 894
!
route-map DENY-TAG deny 10
 match tag 894
route-map DENY-TAG permit 20
!
router ospf 91
 redistribute eigrp 15 subnets route-map SET-TAG
router eigrp 15
 redistribute ospf 91 metric 1000000 1 255 1 1500 route-map DENY-TAG
```
**出自マーキング**: EIGRP→OSPF で入った経路すべてにタグ 894 を焼き、OSPF→EIGRP の
再配送でタグ 894 を弾く。被害プレフィクスを名指ししないので、**将来 RIP 側に別の
プレフィクスが増えても自動で守られる**(実務のベストプラクティス形)。
`DENY-TAG permit 20`(素通し)を忘れると OSPF 発の正常経路まで全滅する(暗黙 deny)。

**片側だけ**直すと、逆向きの再注入が残って**鏡像のループが継続**する(2 点相互再配送の
定石: 対策は必ず両境界に対で入れる)。

## 確認
- RD: `show ip route 192.168.94.0` が `via 172.16.87.5`(RE 方向)へ復帰。
- RA: `traceroute 192.168.94.6` が RA→(境界)→RD→RE→RF で完走(巡回しない)。
- フィルタ系解法では、片側境界の `192.168.94.0` が O E2(遠回りだが到達可)のまま残るのは
  **正常**(O→E 再注入だけを止めたため。距離調整版では両境界とも EIGRP 直行になる)。

## 教育核心
- **多点(2 点以上)相互再配送**は、出自が一周して戻る**フィードバック経路**を必ず作る。
  防御は①再配送点フィルタ(distribute-list out)②出自タグ③AD 調整④メトリック劣化の
  4 家系 — 本問は監査ポリシーで routemap 家系を指定して解かせる形。
- `distribute-list <list> out <protocol>` の **out+プロトコル引数**は「再配送の入口で
  絞る」ための構文(ネイバー向け out とは別物)。ENARSI 頻出。
