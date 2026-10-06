# 解答 : GEN-MPLSEB-32578（自動生成）

## 故障1: l5e_infilter_leak (L5)

RT03 の PL-CUST-LAN に seq 10 permit 10.99.0.0/16 le 32 が混入 (機器管理 /32 を受信してしまい VPN をまたいで漏えい)

症状: 監査指摘: site3 収容 CE の管理アドレスが対向サイトから見える (疎通は全て正常)

修正:
```
  ['(global)'] -> ['no ip prefix-list PL-CUST-LAN seq 10 permit 10.99.0.0/16 le 32']
  ['(global)'] -> ['clear ip bgp * soft']
```

## 故障2: l3_vpnv4_activate_missing (L3)

RT03 で RT01 が address-family vpnv4 で activate されていない

症状: 両顧客とも site3↔site1 のみ不通

修正:
```
  ['router bgp 65000', 'address-family vpnv4'] -> ['neighbor 3.3.3.3 activate']
  ['(global)'] -> ['clear ip bgp * soft']
```

## おとり（無害・修正不要）

- **decoy_ring_cost** (RT05): RT05 の Ethernet0/2 に ip ospf cost 100 (最適経路が迂回するだけで LDP は全リンクにあり無害)


復旧は `ansible-playbook playbooks/fix_generated.yml -e problem=GEN-MPLSEB-32578` でも投入可（自己検品用）。
