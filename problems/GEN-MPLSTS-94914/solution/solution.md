# 解答 : GEN-MPLSTS-94914（自動生成）

## 故障1: l5_routemap_leak (L5)

RT03 の PL-CUST-LAN に seq 10 permit 10.99.0.0/16 le 32 が混入 (機器管理 /32 が VPN をまたいで漏えい)

症状: 監査指摘: site3 収容 CE の管理アドレスが対向サイトから見える (疎通は全て正常)

修正:
```
  ['(global)'] -> ['no ip prefix-list PL-CUST-LAN seq 10 permit 10.99.0.0/16 le 32']
  ['(global)'] -> ['clear ip bgp * soft']
```

## 故障2: l1_ring_ospf_missing (L1)

RT06 のリングIF(10.25.97.0/30)が OSPF に入っていない (冗長で救済されユーザ影響なし = 片肺運転)

症状: 監視: RT05-RT06 間の OSPF 隣接ダウン警報 (ユーザ影響の報告なし)

修正:
```
  ['router ospf 1'] -> ['network 10.25.97.0 0.0.0.3 area 0']
```

## おとり（無害・修正不要）

- **decoy_ring_cost** (RT06): RT06 の Ethernet0/1 に ip ospf cost 100 (最適経路が迂回するだけで LDP は全リンクにあり無害)


復旧は `ansible-playbook playbooks/fix_generated.yml -e problem=GEN-MPLSTS-94914` でも投入可（自己検品用）。
