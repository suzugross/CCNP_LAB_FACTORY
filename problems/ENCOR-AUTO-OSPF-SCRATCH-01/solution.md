# 模範解答 : ENCOR-AUTO-OSPF-SCRATCH-01（レベル3＝ゼロから記述）

ROLE-01 と同じ完成形を、穴あき無しで自分で書ければ正解。完成形は `controller_solution/` 参照。

## roles/ospf/tasks/main.yml
```yaml
---
- name: OSPF プロセス（router-id）を構成
  cisco.ios.ios_ospfv2:
    config:
      processes:
        - process_id: "{{ ospf.process_id }}"
          router_id: "{{ ospf.router_id }}"
    state: merged
  notify: save ospf config

- name: 各インタフェースを OSPF エリアに参加させる
  cisco.ios.ios_ospf_interfaces:
    config:
      - name: "{{ item.name }}"
        address_family:
          - afi: ipv4
            process:
              id: "{{ ospf.process_id }}"
              area_id: "{{ item.area }}"
    state: merged
  loop: "{{ interfaces }}"
  loop_control:
    label: "{{ inventory_hostname }} {{ item.name }} area {{ item.area }}"
  notify: save ospf config
```

## roles/ospf/handlers/main.yml
```yaml
---
- name: save ospf config
  cisco.ios.ios_config:
    save_when: modified
```

## 採点との関係
最終状態のみ採点（ネイバー FULL / 経路学習）。`ios_config` 生 lines で書いても、
リンク別 `network` 文で書いても、結果が同じなら満点。リソースモジュールを選ぶと
**列挙したIFだけ精密に有効化**でき、catch-all より安全（ROLE-01レビュー参照）。

## レベルの位置づけ
- L1(FILL) 穴埋め生lines → L2(ROLE) 穴埋めモダン → **L3(SCRATCH) ゼロから記述**。
- 次(L4)は「host_vars すら与えず、要件からデータモデルを設計」、L5は「壊れたplaybookを直す」。
