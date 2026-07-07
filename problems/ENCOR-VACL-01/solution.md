# 模範解答 : ENCOR-VACL-01

設定するのは **SW01 のみ**。

```
ip access-list extended MATCH-TELNET
 permit tcp any any eq telnet
!
vlan access-map BLOCK-TELNET 10
 match ip address MATCH-TELNET
 action drop
vlan access-map BLOCK-TELNET 20
 action forward
!
vlan filter BLOCK-TELNET vlan-list 10
```

## 確認
```
show vlan access-map BLOCK-TELNET
show vlan filter
show ip access-lists MATCH-TELNET
```

## ポイント（落とし穴の解説）
- **VACL の論理**: `match ip address <ACL>` は「その ACL が **permit** したパケット」を
  この map エントリの対象にする、という意味。ACL の permit/deny は許可/拒否ではなく
  **分類（マッチするか否か）**として働く。だから「Telnet を落とす」には ACL で Telnet を
  **permit** し、map の action を **drop** にする。
- **暗黙の drop**: VLAN access-map にも最後に暗黙の drop がある。seq 20 の
  `action forward`（match 無し＝全マッチ）を置かないと、Telnet 以外も全部落ちて
  VLAN 内通信が止まる。
- **vlan filter で適用**: ルータ ACL の `ip access-group` とは違い、VACL は
  `vlan filter <map> vlan-list <vlans>` で VLAN に適用する。方向（in/out）の概念はない
  （VLAN 内/跨ぎの両方に効く）。
- **イメージ依存**: この VACL 構文は IOL L2(ioll2-xe) では非対応。IOSv-L2(iosvl2) で動く。
