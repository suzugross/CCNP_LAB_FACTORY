# 解答 : GEN-MPLSEB-40718（自動生成）

## 故障1: l3_wrong_neighbor_ip (L3)

RT01 の iBGP ピアが RT03 の Loopback でなく物理IP(10.72.249.1) を指す (双方向とも不一致でセッション不成立)

症状: 両顧客とも site1↔site3 のみ不通 (コア警報なし)

修正:
```
  ['router bgp 65000'] -> ['no neighbor 10.72.249.1', 'neighbor 58.58.58.58 remote-as 65000', 'neighbor 58.58.58.58 update-source Loopback0']
  ['router bgp 65000', 'address-family vpnv4'] -> ['neighbor 58.58.58.58 activate']
  ['(global)'] -> ['clear ip bgp * soft']
```

## 故障2: l1_ring_ospf_missing (L1)

RT05 のリングIF(10.0.119.0/30)が OSPF に入っていない (冗長で救済されユーザ影響なし = 片肺運転)

症状: 監視: RT05-RT06 間の OSPF 隣接ダウン警報 (ユーザ影響の報告なし)

修正:
```
  ['router ospf 1'] -> ['network 10.0.119.0 0.0.0.3 area 0']
```

## おとり（無害・修正不要）

- **decoy_ring_cost** (RT05): RT05 の Ethernet0/2 に ip ospf cost 100 (最適経路が迂回するだけで LDP は全リンクにあり無害)


復旧は `ansible-playbook playbooks/fix_generated.yml -e problem=GEN-MPLSEB-40718` でも投入可（自己検品用）。
