# 模範解答 : ENCOR-AUTO-OSPF-FILL-01（自動化・レベル1 穴埋め）

## 穴の答え
| 穴 | ファイル | 答え | 意味 |
|----|----------|------|------|
| ① | hosts.ini `ansible_connection=` | **network_cli** | ネットワーク機器に SSH で CLI 接続する接続プラグイン。サーバ用 `ssh` とは別物 |
| ② | hosts.ini `ansible_network_os=cisco.ios.` | **ios** | 対象 OS。`cisco.ios.ios`。これで cli_parser/プロンプト解釈が IOS 用になる |
| ③ | ospf.yml モジュール `cisco.ios.` | **ios_config** | running-config に行を投入する設定モジュール。`parents`/`lines` で階層を表す |
| ④ | ospf.yml `... area` | **0** | 全インタフェースをエリア0に。`network 0.0.0.0 255.255.255.255` で全網羅 |

完成形は `controller_solution/hosts.ini` と `controller_solution/ospf.yml` を参照。

## なぜ動くか（自動化の要点）
- `ansible_connection=network_cli` … Ansible は対象に Python を置けないネットワーク機器へ、
  **制御マシン側から SSH してコマンドを送る**（persistent connection）。Linux サーバ向けの
  デフォルト `ssh`（リモートで Python 実行）とは仕組みが違う、というのが最初の勘所。
- `cisco.ios.ios_config` … `parents: router ospf 1` で `(config-router)` 階層に入り、
  `lines:` の各行を投入する。既に同じ行があれば**投入しない**ので、2 回流しても無害（冪等）。
- `network 0.0.0.0 255.255.255.255 area 0` … 全 IPv4 インタフェース（Loopback 含む）を
  area 0 に参加させる定番イディオム。リンクごとに network 文を分けても可。

## 採点との関係（手段非依存）
採点は `playbooks/grade.yml` が **最終状態だけ**を見る（ネイバー FULL / OSPF 経路の学習）。
このため、手打ち CLI で同じ設定を入れても満点になる。穴を間違えると：
- 穴①②を誤る → ルータに接続できず設定が入らない → 採点 FAIL（全経路未学習）
- 穴③を誤る → モジュールが見つからず Playbook がエラー
- 穴④を誤る（別エリア）→ ネイバーは上がるが area 設計が崩れ、隣接/経路が想定外
→ どの穴も「最終状態」に効くので、効果採点だけで正誤が判定できる。

## 確認コマンド（任意）
```bash
# Playbook 実行後、冪等性チェック（2回目は changed=0 になるのが理想）
ansible-playbook -i hosts.ini ospf.yml          # 1回目: changed
ansible-playbook -i hosts.ini ospf.yml          # 2回目: ok のみ（changed=0）

# 実機状態の目視
ansible RT01 -i hosts.ini -m cisco.ios.ios_command -a "commands='show ip ospf neighbor'"
```

## 発展（次のレベルへの布石）
- **レベル2**：`network_cli` や `ios_config` をヒント無しで書かせる／`loop` でリンク別 network 文。
- **冪等性を採点に追加**：grade 前に Playbook を2回流し、2回目 `changed=0` を必須化。
- **RESTCONF/NETCONF 版**：対象を cat8000v に替え、`ansible.netcommon.restconf_config`
  もしくは `cisco.ios` の netconf モジュールで同じ OSPF を構成する API 版に発展。
