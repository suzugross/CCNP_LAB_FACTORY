# 模範解答 : ENCOR-GRE-01

## RT01 (HQ)
```
interface Tunnel100
 ip address 172.16.13.1 255.255.255.252
 tunnel source Loopback0
 tunnel destination 3.3.3.3
 tunnel mode gre ip
!
router eigrp 100
 network 10.10.1.1 0.0.0.0
 network 172.16.13.0 0.0.0.3
!
```

## RT03 (Branch)
```
interface Tunnel100
 ip address 172.16.13.2 255.255.255.252
 tunnel source Loopback0
 tunnel destination 1.1.1.1
 tunnel mode gre ip
!
router eigrp 100
 network 10.10.3.1 0.0.0.0
 network 172.16.13.0 0.0.0.3
!
```

## 確認
```
show interfaces tunnel 100
show ip eigrp neighbors
show ip route eigrp
ping 10.10.3.1 source Loopback10           ! RT01 から
ping 10.10.1.1 source Loopback10           ! RT03 から
```

### ポイント（落とし穴の解説）
- **tunnel source/destination は Loopback0 (underlay 上で到達可能なアドレス) を使う**:
  物理 IF にすると、その IF が落ちただけでトンネル全体が落ちる。Lo0 ならどのリンクが
  生きていれば underlay 経路で到達可能 → トンネル可用性が上がる。
- **tunnel destination は underlay (OSPF) で解決できる必要がある**:
  この問題では 1.1.1.1 / 3.3.3.3 が underlay の OSPF で交換されているので、
  ルックアップ→OSPF経路 で到達可。Lo10 (10.10.x.1) は OSPF に載せていないので
  tunnel destination には使えない (使ったらリカーシブで up しない)。
- **EIGRP は overlay (Tunnel100) と private LAN (Lo10) のみ network 文に入れる**:
  underlay の OSPF はそのまま残し、EIGRP は overlay 上だけで回す＝
  プライベートが事業者網に漏れない（要件「underlay に広告しない」を満たす）。
- **再帰ルーティング (recursive routing) に注意**:
  Lo10 を OSPF にも入れてしまうと、EIGRP が学んだ overlay 経路と OSPF underlay 経路が
  競合 ＋ tunnel destination のリカーシブが壊れるケースがある。OSPF と EIGRP の責務を
  分けるのが核心。
- **Tunnel100 / EIGRP AS 100 / overlay 172.16.13.0/30 は task の指定値に従う**
  (採点が固定値で判定)。tunnel mode は既定が `gre ip` なので明示しなくても可。

> 採点: 両端 Tunnel100 が up/up かつ GRE、両端で対向 Lo10 を EIGRP 経由で学習し
> outgoing が Tunnel100 になっていることを判定。RT02 (transit) は採点対象外。
