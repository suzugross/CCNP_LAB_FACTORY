# 解答 : GEN-MPLSEB-74980（自動生成）

## 故障1: l5e_activate_missing (L5)

RT02 の RT10 向けネイバーが activate されていない (経路交換なし)

症状: CUST_B の site2 が全断 (リンク/ping は正常)

修正:
```
  ['router bgp 65000', 'address-family ipv4 vrf CUST_B'] -> ['neighbor 192.168.168.1 activate']
  ['(global)'] -> ['clear ip bgp * soft']
```

## 故障2: l3_wrong_neighbor_ip (L3)

RT02 の iBGP ピアが RT01 の Loopback でなく物理IP(10.185.118.1) を指す (双方向とも不一致でセッション不成立)

症状: 両顧客とも site2↔site1 のみ不通 (コア警報なし)

修正:
```
  ['router bgp 65000'] -> ['no neighbor 10.185.118.1', 'neighbor 4.4.4.4 remote-as 65000', 'neighbor 4.4.4.4 update-source Loopback0']
  ['router bgp 65000', 'address-family vpnv4'] -> ['neighbor 4.4.4.4 activate']
  ['(global)'] -> ['clear ip bgp * soft']
```

## おとり（無害・修正不要）

- **decoy_ring_cost** (RT06): RT06 の Ethernet0/2 に ip ospf cost 100 (最適経路が迂回するだけで LDP は全リンクにあり無害)


復旧は `ansible-playbook playbooks/fix_generated.yml -e problem=GEN-MPLSEB-74980` でも投入可（自己検品用）。
