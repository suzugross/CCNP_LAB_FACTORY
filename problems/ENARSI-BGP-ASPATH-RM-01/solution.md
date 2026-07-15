# 模範解答 : ENARSI-BGP-ASPATH-RM-01

## 考え方
「as-path で経路を識別し、`route-map` の各シーケンスで属性を `set` して、
neighbor に **inbound** 適用する」——これが BGP パス制御の基本形。
各課題は route-map の1シーケンスに対応し、条件が互いに素なので順序は問わない。

## RT01 の設定
```
! as-path で経路を識別（前回の道場と同じ書き方）
ip as-path access-list 1 permit _65210$      ! 起源 65210
ip as-path access-list 2 permit _65220$      ! 起源 65220
ip as-path access-list 3 permit _65230$      ! 起源 65230
ip as-path access-list 4 permit _65240$      ! 起源 65240
ip as-path access-list 5 permit _65250_      ! 65250 を含む（経由）
!
route-map RM_IN permit 10
 match as-path 1
 set local-preference 200
route-map RM_IN permit 20
 match as-path 2
 set weight 100
route-map RM_IN permit 30
 match as-path 3
 set local-preference 50
route-map RM_IN permit 40
 match as-path 4
 set community 65001:444
route-map RM_IN permit 50
 match as-path 5
 set as-path prepend 65001 65001
route-map RM_IN permit 100       ! ← 残り（制御対象外）を素通し。これが無いと暗黙 deny で全落ち
!
router bgp 65001
 neighbor 10.1.12.2 route-map RM_IN in
!
```
適用後、inbound を再処理：
```
clear ip bgp * in          ! （ルートリフレッシュ。効かなければ）
clear ip bgp *
```

## 確認
| 課題 | 確認コマンド | 期待 |
|---|---|---|
| 1 | `show ip bgp 172.16.1.0/24` | `localpref 200` |
| 2 | `show ip bgp 172.16.2.0/24` | `weight 100` |
| 3 | `show ip bgp 172.16.3.0/24` | `localpref 50` |
| 4 | `show ip bgp 172.16.4.0/24` | `Community: 65001:444` |
| 5 | `show ip bgp 172.16.5.0/24` | Path が `65001 65001 65099 65250 65260` |

## 要点・落とし穴
- **route-map 末尾の `permit 100`（match 無し＝全許可）を忘れない**。route-map も ACL 同様
  末尾は暗黙 deny なので、これが無いと制御対象外の経路（172.16.6/7）まで inbound で捨てられ、
  BGP テーブルから消える。
- **inbound 適用は即時反映されない**。`clear ip bgp * in`（ルートリフレッシュ）または
  `clear ip bgp *` で再処理する。
- `set weight` はローカル（RT01内）だけに効く非伝播属性。`local-preference` は AS 内伝播、
  `community` はタグ、`as-path prepend` は経路長操作——それぞれ効き方が違う点を意識する。
- 別解: 課題ごとに個別の route-map を作って `neighbor ... route-map X in` を…とはできない
  （**inbound route-map は neighbor につき1本**）。必ず1本にシーケンスでまとめる。
  各 `set` は `match as-path` の代わりに `match community` 等でも実現し得るが、本問は as-path 識別が主題。
