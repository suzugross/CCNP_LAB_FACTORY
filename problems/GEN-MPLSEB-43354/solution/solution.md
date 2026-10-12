# 解答 : GEN-MPLSEB-43354（自動生成）

## 故障1: l4_rt_export_wrong (L4)

RT01 の VRF CUST_A の route-target export が 65000:1001 (正: 65000:100。この site の経路がどの PE にも import されない)

症状: CUST_A の site1 だけ孤立 (他顧客は正常)

修正:
```
  ['vrf definition CUST_A', 'address-family ipv4'] -> ['no route-target export 65000:1001', 'route-target export 65000:100']
  ['(global)'] -> ['clear ip bgp * soft']
```

## 故障2: l5e_asoverride_missing (L5)

RT03 の RT12 向けネイバーに as-override が無い (CUST_B は全サイト同一 AS 65200 → CE の AS_PATH ループ検知で対向経路が破棄される。PE の advertised-routes には在るのに CE の table に無い)

症状: CUST_B の site3 だけ対向サイトと不通 (CUST_A は全て正常・PE-CE セッションは Established)

修正:
```
  ['router bgp 65000', 'address-family ipv4 vrf CUST_B'] -> ['neighbor 192.168.222.1 as-override']
  ['(global)'] -> ['clear ip bgp * soft']
```

## おとり（無害・修正不要）

- **decoy_ring_cost** (RT04): RT04 の Ethernet0/2 に ip ospf cost 100 (最適経路が迂回するだけで LDP は全リンクにあり無害)


復旧は `ansible-playbook playbooks/fix_generated.yml -e problem=GEN-MPLSEB-43354` でも投入可（自己検品用）。
