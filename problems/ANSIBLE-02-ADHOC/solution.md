# 模範解答 : Ansible道場 02（アドホックコマンド）

## 穴の答え
| 穴 | 答え | 意味 |
|----|------|------|
| module | **ios_config** | 設定行を投入するモジュール（読みは ios_command） |
| value | **ANSIBLE-DOJO-02** | snmp location に入れる文字列（課題指定） |

完成形 `controller_solution/run.sh`：
```bash
ansible routers -i hosts.ini -m cisco.ios.ios_config \
  -a "lines='snmp-server location ANSIBLE-DOJO-02'"
```

## ポイント
- **モジュールが操作の単位**。アドホックでも Playbook でも、呼ぶモジュール（ios_command/ios_config）は同じ。
- `ios_command` は **読み取り専用**（show）。設定変更には使えない。設定は `ios_config`。
- `-a "lines='...'"` の中はシェルのクォートに注意（外を ", 内を ' にすると楽）。

## 確認
```bash
ansible routers -i hosts.ini -m cisco.ios.ios_command \
  -a "commands='show running-config | include snmp-server location'"
```
