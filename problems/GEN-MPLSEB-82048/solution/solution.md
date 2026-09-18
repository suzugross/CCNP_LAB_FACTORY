# 解答 : GEN-MPLSEB-82048（自動生成）

## 故障1: l5e_infilter_overbroad (L5)

RT01 の prefix-list PL-CUST-LAN が le 23 (CE の LAN /24 を受信段階で破棄。★収容 PE の VRF にも LAN が無い = 再配布方式との差分指紋)

症状: 両顧客とも site1 の LAN が対向から見えない (セッションは全て正常)

修正:
```
  ['(global)'] -> ['no ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le 23', 'ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le 24']
  ['(global)'] -> ['clear ip bgp * soft']
```

## 故障2: l3_vpnv4_activate_missing (L3)

RT03 で RT02 が address-family vpnv4 で activate されていない

症状: 両顧客とも site3↔site2 のみ不通

修正:
```
  ['router bgp 65000', 'address-family vpnv4'] -> ['neighbor 38.38.38.38 activate']
  ['(global)'] -> ['clear ip bgp * soft']
```

## おとり（無害・修正不要）

- **decoy_rd_nonstandard** (RT03): RT03 の VRF CUST_A の RD が 65000:9100 (正規値 65000:100 と不揃い。だが RD は一意化の札であって所属判断に関与しない=無害)


復旧は `ansible-playbook playbooks/fix_generated.yml -e problem=GEN-MPLSEB-82048` でも投入可（自己検品用）。
