# 回答ワークスペース（ENCOR-AUTO-OSPF-SCRATCH-01・レベル3＝ゼロから記述）

穴埋めではありません。**`roles/ospf/` の tasks/handlers を自分で書いて** OSPF を構成します。

## 与えられているもの
```
controller/
├── ansible.cfg / hosts.ini / site.yml   … 記入不要
├── host_vars/RT0X.yml                   … ★OSPF設計データ（process_id/router_id/interfaces）
└── roles/ospf/
    ├── tasks/main.yml                   … 空（ここに書く）
    ├── handlers/main.yml                … 空（ここに書く）
    └── defaults/main.yml                … 空
```

## やること
1. tasks: host_vars のデータを使い、OSPFプロセス(router-id)＋各IFのエリア参加を構成。
2. handlers: 変更時に running を保存。tasks から notify する。
3. 実行して採点が通ること。

## 手順
```bash
cd lab/ENCOR-AUTO-OSPF-SCRATCH-01
ansible-playbook site.yml          # 1回目 changed / 2回目 changed=0（冪等）
```

## 推奨（手段は自由・最終状態のみ採点）
- リソースモジュール `cisco.ios.ios_ospfv2` / `cisco.ios.ios_ospf_interfaces`（`state: merged`）
- `loop: "{{ interfaces }}"` で IF を回す
- handler は `cisco.ios.ios_config: { save_when: modified }`
（ROLE-01 を解いた人は、その tasks を思い出して“穴あき無し”で再現する練習）
