# JUNOS-BUILD-01 模範解答

`ssh admin@172.20.20.2` → `configure` の後、以下を投入。

```
set system host-name JUN01
set interfaces et-0/0/0 unit 0 family inet address 10.0.12.1/30
set interfaces lo0 unit 0 family inet address 192.168.0.1/32
set routing-options router-id 192.168.0.1
set protocols ospf area 0.0.0.0 interface et-0/0/0.0
set protocols ospf area 0.0.0.0 interface lo0.0 passive
set routing-options static route 172.16.10.0/24 discard
set policy-options policy-statement EXPORT-STATIC term T1 from protocol static
set policy-options policy-statement EXPORT-STATIC term T1 then accept
set protocols ospf export EXPORT-STATIC
```

要件7(安全なコミット作法)= **commit confirmed**:

```
show | compare          ← 投入前に差分確認(作法)
commit confirmed 5      ← 5分以内に確定しなければ自動ロールバック
commit                  ← 確定(confirmed の解除)
```

## 検証

```
show ospf neighbor                        ← 10.0.12.2 Full
show route protocol ospf                  ← 2.2.2.2/32 など学習
ping 2.2.2.2 source 192.168.0.1 count 5 rapid
show system commit                        ← "commit confirmed" の履歴
```

## 教育ポイント(採点後レビュー用)

- candidate config と commit モデル: 打った瞬間は何も起きない。`show | compare`→`commit confirmed`→確定、が Junos の安全作法の基本形
- **policy-statement = route-map 相当**。ただし Junos の再配送は「redistribute コマンド」ではなく **プロトコルへの export ポリシー適用**(`set protocols ospf export <名前>`)。「OSPF に入れたければ OSPF の export に書く」という向きの発想転換が最大の読み替えポイント
- Junos は lo0 のマスクに関係なく /32 で広告(今回ははじめから /32 で統一)
- router-id を明示しないと OSPF 起動時点の最良アドレスで RID が決まり、lo0 を後から足すと RID がズレる(Cisco と同じ罠が Junos にもある)
- discard ルート = Cisco の Null0 static 相当
