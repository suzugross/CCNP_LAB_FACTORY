# 採点者専用（受験者に見せないこと）

- 故障数: 3（積み重ねペア 1 組を含む）
  - mask_mismatch @ RT01 if=Ethernet0/0  [stack#1]
  - mtu_mismatch @ RT02 if=Ethernet0/0  [stack#1]
  - passive_interface @ RT05 if=Ethernet0/0
- おとり: 3 個（到達性に無害・修正不要）
  - ospf_cost @ RT02
  - description @ RT04
  - ospf_cost @ RT04
- fix.json   : 模範修正リスト（playbooks/fix_generated.yml が読む。おとりは含まない）
- impact.json: 申告症状と影響範囲（全失敗ペア）
- decoys.json: おとり一覧
