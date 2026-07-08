# 解答 : GEN-MPLSTS-7100（自動生成）

## 故障1: l3_wrong_neighbor_ip (L3)

RT01 の iBGP ピアが RT03 の Loopback でなく物理IP(10.86.114.1) を指す (双方向とも不一致でセッション不成立)

症状: 両顧客とも site1↔site3 のみ不通 (コア警報なし)

修正:
```
  ['router bgp 65000'] -> ['no neighbor 10.86.114.1', 'neighbor 92.92.92.92 remote-as 65000', 'neighbor 92.92.92.92 update-source Loopback0']
  ['router bgp 65000', 'address-family vpnv4'] -> ['neighbor 92.92.92.92 activate']
  ['(global)'] -> ['clear ip bgp * soft']
```

## 故障2: l5_redist_bgp_missing (L5)

RT01 の OSPF 20(VRF CUST_B) に redistribute bgp が無い (対向経路が CE に届かない)

症状: CUST_B site1 の CE に対向サイトの経路が無い (隣接は FULL)

修正:
```
  ['router ospf 20 vrf CUST_B'] -> ['redistribute bgp 65000 subnets']
```

## おとり（無害・修正不要）

- **decoy_ring_cost** (RT05): RT05 の Ethernet0/2 に ip ospf cost 100 (最適経路が迂回するだけで LDP は全リンクにあり無害)


復旧は `ansible-playbook playbooks/fix_generated.yml -e problem=GEN-MPLSTS-7100` でも投入可（自己検品用）。
