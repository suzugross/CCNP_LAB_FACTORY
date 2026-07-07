# 模範解答 : Ansible道場 03（Playbookの構造）

## 穴の答え
| 穴 | 答え | 意味 |
|----|------|------|
| hosts | **routers** | 対象グループ（インベントリの [routers] と一致） |
| module | **ios_config** | 設定を投入するモジュール |
| parents | **interface Loopback3** | lines を入れる設定階層 |

完成形 `controller_solution/pb.yml`：
```yaml
- name: Loopback3 を作る Playbook
  hosts: routers
  gather_facts: false
  tasks:
    - name: Loopback3 に IP と description を設定
      cisco.ios.ios_config:
        parents: interface Loopback3
        lines:
          - ip address 3.3.3.3 255.255.255.255
          - description DOJO-03
```

## ポイント
- `hosts:` がインベントリのグループ名と合っていないと **対象0台**（何も起きない）。
- `ios_config` は **`parents` で階層に入り `lines` を流す**。`interface Loopback3` 配下に2行入る。
- task の `name:` は実行ログに出る。後から読む人（自分含む）のために必ず付ける。

## 補足
- 同じ playbook を2回流すと2回目は `changed=0`（冪等）。これは Lesson05 で扱う。
