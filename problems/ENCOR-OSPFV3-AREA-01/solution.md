# 模範解答 ENCOR-OSPFV3-AREA-01

## 全ルータ：データIF有効化（IOL day0/再起動で admin-down のことがある）
各ルータの使用 Ethernet IF に `no shutdown`（RT02/RT03 は 2 本）。

## RT01（area0）
```
ipv6 router ospf 1
 router-id 1.1.1.1
interface Loopback0
 ipv6 ospf 1 area 0
interface Ethernet0/0
 ipv6 ospf 1 area 0
```

## RT02（ABR：集約 + Totally Stubby の no-summary）
```
ipv6 router ospf 1
 router-id 2.2.2.2
 area 1 stub no-summary
 area 1 range 2001:DB8:A1::/48
interface Loopback0
 ipv6 ospf 1 area 0
interface Ethernet0/0
 ipv6 ospf 1 area 0
interface Ethernet0/1
 ipv6 ospf 1 area 1
```

## RT03（area1 stub）
```
ipv6 router ospf 1
 router-id 3.3.3.3
 area 1 stub
interface Loopback0
 ipv6 ospf 1 area 1
interface Ethernet0/0
 ipv6 ospf 1 area 1
interface Ethernet0/1
 ipv6 ospf 1 area 1
```

## RT04（area1 stub）
```
ipv6 router ospf 1
 router-id 4.4.4.4
 area 1 stub
interface Loopback0
 ipv6 ospf 1 area 1
interface Ethernet0/0
 ipv6 ospf 1 area 1
```

## ポイント / 教育核心
- **OSPFv3 でも area 範囲集約は `area <id> range <ipv6-prefix>`**（ABR で type-3 を 1 本に）。
  area1 のアドレスを `2001:DB8:A1::/48` 配下に整列させておくと 1 本で集約できる。
  結果：backbone(RT01) は `OI 2001:DB8:A1::/48` のみ・個別 /128 は出ない。
- **Totally Stubby = `area 1 stub no-summary`（ABR のみ no-summary）+ `area 1 stub`（内部ルータ）**。
  area1 へ inter-area(type-3) を入れず、ABR が default(`::/0`) を注入。RT03/RT04 は `OI ::/0` だけで外へ。
  ※スタブフラグは **area1 全ルータで一致**が必須（不一致＝隣接不可）。
- **router-id 手動指定**：IPv6 only は IPv4 アドレスが無く router-id 自動選定不可（各プロセスで指定）。
- 確認：
  - RT01 `show ipv6 route ospf` → `OI 2001:DB8:A1::/48`（個別 /128 なし）
  - RT03/RT04 `show ipv6 route ospf` → `OI ::/0`（backbone 個別経路なし）
  - `ping 2001:DB8:A1:4::4`（RT01発・集約経由）/ `ping 2001:DB8:1::1`（RT04発・default経由）成功
```
