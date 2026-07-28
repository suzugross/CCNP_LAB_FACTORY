# 模範解答 (ENARSI-EIGRP-VRF-01)

## RT02 に投入する設定(全量)

```
key chain KC-A
 key 1
  key-string Suzu2026A
!
vrf definition TENANT-A
 rd 65000:100
 address-family ipv4
 exit-address-family
!
vrf definition TENANT-B
 rd 65000:200
 address-family ipv4
 exit-address-family
!
interface Ethernet0/0
 vrf forwarding TENANT-A
 ip address 10.10.1.2 255.255.255.252
!
interface Ethernet0/1
 vrf forwarding TENANT-A
 ip address 10.10.2.2 255.255.255.252
!
interface Ethernet0/2
 vrf forwarding TENANT-B
 ip address 10.20.1.2 255.255.255.252
!
router eigrp SUZUNET
 address-family ipv4 unicast vrf TENANT-A autonomous-system 100
  af-interface Ethernet0/0
   authentication mode md5
   authentication key-chain KC-A
  exit-af-interface
  af-interface Ethernet0/1
   authentication mode md5
   authentication key-chain KC-A
   summary-address 172.16.10.0 255.255.254.0
  exit-af-interface
  network 10.10.1.0 0.0.0.3
  network 10.10.2.0 0.0.0.3
 exit-address-family
 address-family ipv4 unicast vrf TENANT-B autonomous-system 200
  network 10.20.1.0 0.0.0.3
 exit-address-family
```

## 落とし穴(採点対象の理解ポイント)

1. **`vrf forwarding` 投入で IF の IP アドレスが剥がれる**
   (`% Interface X IPv4 disabled and address(es) removed due to enabling VRF`)。
   IP を再投入しないと隣接が上がらない。本問最大の罠。
2. **`vrf definition` には `address-family ipv4` が必須**。忘れると
   `vrf forwarding` が `% IPv4 ... not enabled` で拒否される
   (旧 `ip vrf` 構文との違い。ENARSI 頻出)。
3. **named mode の VRF 収容は `address-family ipv4 unicast vrf <名> autonomous-system <AS>`**。
   AS はAF行で宣言する(classic の `router eigrp <AS>` と違いインスタンス名は自由文字列)。
4. **named mode の認証は af-interface 配下** (`authentication mode md5` +
   `authentication key-chain`)。classic の `ip authentication ...` はIFに打てない
   (named 管理下では無効)。CE側(classic MD5)との相互運用は key id/key-string
   の一致だけが条件で、key chain 名は一致不要。
5. **集約は af-interface 配下の `summary-address`**。RT04 向け(E0/1)にだけ設定
   すれば site1 の明細/24 が抑止され /23 のみ広告される(RT02 の VRF-A RIB には
   AD5 の Null0 サマリが立つ)。
6. AS 100/200 の分離+VRF 分離の二重構造なので、IF の VRF 収容を間違えると
   AS 不一致で隣接自体が上がらない(症状から切り分け可能)。

## 検証コマンド

```
show vrf detail TENANT-A
show ip eigrp vrf TENANT-A neighbors
show ip eigrp vrf TENANT-A interfaces detail
show ip route vrf TENANT-A 172.16.10.0 255.255.255.0
show ip route vrf TENANT-B 172.16.10.0 255.255.255.0
ping vrf TENANT-B 172.16.30.1
```
