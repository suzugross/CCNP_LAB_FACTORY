# 模範解答 : Ansible道場 05（冪等性と --check/--diff）

## 穴の答え
| 穴 | 答え |
|----|------|
| ntp | **10.123.45.6** |

```yaml
    - name: set ntp server
      cisco.ios.ios_config:
        lines:
          - "ntp server 10.123.45.6"
```

## 学習の核心（手を動かして確認すること）
```bash
ansible-playbook pb.yml --check --diff   # 流す前: +ntp server ... の差分が見える
ansible-playbook pb.yml                  # 1回目: changed=1
ansible-playbook pb.yml                  # 2回目: changed=0 ← 冪等！
```
- **冪等**＝何度流しても同じ。`ios_config` は既存行を入れ直さないので2回目は changed=0。
- 毎回 changed になるなら、その task は冪等でない（例: ios_command で show を“設定のつもり”で使う等）。設計を見直すサイン。
- 本番前は `--check --diff` でリハーサル。事故を防ぐ実務の基本。

## 補足
- `--check` は「変更しないモード」。一部モジュールは check 非対応のこともある。
- 差分を綺麗に出すには、投入する行を running-config の表記に合わせるとよい（警告が出る場合あり）。
