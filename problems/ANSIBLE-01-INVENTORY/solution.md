# 模範解答 : Ansible道場 01（インベントリと接続）

## 穴の答え
| 穴 | 答え | 意味 |
|----|------|------|
| connection | **network_cli** | ネットワーク機器に SSH で CLI 接続する接続プラグイン（`ansible.netcommon.network_cli` の短縮形）。server 用 `ssh` とは別物 |
| network_os | **ios** | `ansible_network_os=cisco.ios.ios`。CLIプロンプト解釈やコマンド整形に使う |

完成形は `controller_solution/hosts.ini`：
```ini
[routers]
RT01 ansible_host=10.1.10.11
RT02 ansible_host=10.1.10.12
RT03 ansible_host=10.1.10.13

[routers:vars]
ansible_user=SUZUKI
ansible_password=CCNP
ansible_connection=network_cli
ansible_network_os=cisco.ios.ios
```

## なぜ network_cli か（最重要ポイント）
- 既定の `ansible_connection=ssh` は「**リモート(機器)側で Python を実行**」する前提。
  ルータ/スイッチは任意の Python を実行できないので使えない。
- `network_cli` は「**制御機側から SSH してコマンド文字列を送り、出力を受け取る**」方式。
  `ansible_network_os` でその機器の CLI 作法（プロンプト・ページャ・整形）を解釈する。
- この2つが正しくないと、そもそも機器に到達できず何も設定できない（＝採点0）。

## 確認
```bash
cd lab/ANSIBLE-01-INVENTORY
ansible-playbook set_desc.yml
# 到達確認だけしたいとき（設定せず疎通だけ）:
ansible routers -m cisco.ios.ios_command -a "commands='show clock'"
```

## 補足（次回への布石）
- `ansible_user`/`ansible_password` も接続情報。実務では平文で置かず **ansible-vault**（道場 後半）で守る。
- グループ `[routers]` は playbook の `hosts: routers` と一致させる。グループ名が合わないと対象0台になる。
