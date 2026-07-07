# 模範解答 : ENCOR-OSPF-IF-01

インタフェースモード（各インタフェース配下で `ip ospf 1 area 0`）で構成する。
※ インタフェース名はイメージにより異なる（IOL: Ethernet0/0.. / IOSv: GigabitEthernet0/0..）。

## RT01
```
interface Loopback0
 ip ospf 1 area 0
interface Ethernet0/0
 ip ospf 1 area 0
interface Ethernet0/1
 ip ospf 1 area 0
```

## RT02
```
interface Loopback0
 ip ospf 1 area 0
interface Ethernet0/0
 ip ospf 1 area 0
```

## RT03
```
interface Loopback0
 ip ospf 1 area 0
interface Ethernet0/0
 ip ospf 1 area 0
```

## 確認
```
show ip ospf interface brief     ! インタフェースが OSPF に参加しているか
show ip ospf neighbor
show ip route ospf
```

### ポイント
- インタフェースモードは各インタフェース配下に **`ip ospf <pid> area <area>`** を書く方式。
  `router ospf 1` プロセスは最初の `ip ospf` で暗黙生成される（network 文は書かない）。
- network 文方式と最終的なネイバー／経路は同じになるが、本問は方式をインタフェースモードに限定。
  採点は `show running-config` にインタフェース配下の `ip ospf 1 area 0` があることも確認する。
- Loopback も忘れず参加させること（参加しないと 1.1.1.1 等が広告されない）。
