# 解答 : GEN-MPLSTS-55847（自動生成）

## 故障1: l4_rt_export_wrong (L4)

RT03 の VRF CUST_B の route-target export が 65000:2001 (正: 65000:200。この site の経路がどの PE にも import されない)

症状: CUST_B の site3 だけ孤立 (他顧客は正常)

修正:
```
  ['vrf definition CUST_B', 'address-family ipv4'] -> ['no route-target export 65000:2001', 'route-target export 65000:200']
  ['(global)'] -> ['clear ip bgp * soft']
```

## 故障2: l3_wrong_neighbor_ip (L3)

RT01 の iBGP ピアが RT03 の Loopback でなく物理IP(10.79.59.1) を指す (双方向とも不一致でセッション不成立)

症状: 両顧客とも site1↔site3 のみ不通 (コア警報なし)

修正:
```
  ['router bgp 65000'] -> ['no neighbor 10.79.59.1', 'neighbor 88.88.88.88 remote-as 65000', 'neighbor 88.88.88.88 update-source Loopback0']
  ['router bgp 65000', 'address-family vpnv4'] -> ['neighbor 88.88.88.88 activate']
  ['(global)'] -> ['clear ip bgp * soft']
```

## おとり（無害・修正不要）

- **decoy_ring_cost** (RT06): RT06 の Ethernet0/1 に ip ospf cost 100 (最適経路が迂回するだけで LDP は全リンクにあり無害)


復旧は `ansible-playbook playbooks/fix_generated.yml -e problem=GEN-MPLSTS-55847` でも投入可（自己検品用）。
