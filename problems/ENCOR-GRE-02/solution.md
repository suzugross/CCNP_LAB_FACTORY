# 模範解答 : ENCOR-GRE-02 (デュアル GRE + overlay OSPF)

設定するのは **RT01 (HQ) / RT03 (Branch1) / RT04 (Branch2)**。RT02 は変更しない。

## RT01 (HQ)
```
interface Tunnel100
 ip address 172.16.13.1 255.255.255.252
 tunnel source Loopback0
 tunnel destination 3.3.3.3
 tunnel mode gre ip
!
interface Tunnel200
 ip address 172.16.14.1 255.255.255.252
 tunnel source Loopback0
 tunnel destination 4.4.4.4
 tunnel mode gre ip
!
router ospf 2
 network 10.10.1.1 0.0.0.0 area 0
 network 172.16.13.0 0.0.0.3 area 0
 network 172.16.14.0 0.0.0.3 area 0
```

## RT03 (Branch1)
```
interface Tunnel100
 ip address 172.16.13.2 255.255.255.252
 tunnel source Loopback0
 tunnel destination 1.1.1.1
 tunnel mode gre ip
!
router ospf 2
 network 10.10.3.1 0.0.0.0 area 0
 network 172.16.13.0 0.0.0.3 area 0
```

## RT04 (Branch2)
```
interface Tunnel200
 ip address 172.16.14.2 255.255.255.252
 tunnel source Loopback0
 tunnel destination 1.1.1.1
 tunnel mode gre ip
!
router ospf 2
 network 10.10.4.1 0.0.0.0 area 0
 network 172.16.14.0 0.0.0.3 area 0
```

## 確認
```
show interfaces tunnel 100        ! up/up, Tunnel protocol/transport GRE
show ip route ospf                ! 10.10.x.1/32 が via 172.16.x.x, Tunnel1xx
```

## ポイント（落とし穴の解説）
- **トンネルの source/destination は Loopback0** を使う。Lo0 は underlay(OSPF proc1) で
  到達できるが、private Lo10 は underlay に無いのでエンドポイントには使えない。
- **overlay は別 OSPF プロセス(proc2)** にする。underlay(proc1) と分けることで、
  トンネルのエンドポイント(1.1.1.1 等)が overlay 経由で再学習されるのを防ぐ。
- ★**recursive routing（再帰ルーティング）の罠**: もし tunnel destination の
  ネットワーク(Lo0/32)を overlay OSPF に入れてしまうと、宛先がトンネル自身経由で
  解決され、トンネルが `%TUN-5-RECURDOWN` で落ちる（line protocol down）。
  → overlay には **private LAN(Lo10) とトンネル・サブネットだけ**を入れる。
- 2本のトンネルは同じ HQ Lo0 を source に共有してよい（destination が異なるため別トンネルとして成立）。
- 採点は効果ベース: トンネルが up/up & GRE であること、各 private LAN が
  **outgoing interface = Tunnel100/200** で学習されていること。
