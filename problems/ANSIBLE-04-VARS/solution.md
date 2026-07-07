# 模範解答 : Ansible道場 04（変数の優先順位）

## 穴の答え
| ファイル | 値 | 効果 |
|----------|----|----|
| `group_vars/routers.yml` | **TOKYO-NOC** | routers 全台で all(DEFAULT) を上書き |
| `host_vars/RT03.yml` | **OSAKA-NOC** | RT03 だけ group_vars を上書き（host_vars が勝つ） |

結果: RT01/RT02 = TOKYO-NOC、RT03 = OSAKA-NOC。

## ポイント（優先順位）
```
group_vars/all (DEFAULT-NOC)  ← 最弱
   ↓ 上書き
group_vars/routers (TOKYO-NOC)
   ↓ 上書き（RT03のみ）
host_vars/RT03 (OSAKA-NOC)    ← 最強（今回の範囲で）
```
- **より具体的な場所が勝つ**。「全体はTOKYO、RT03だけOSAKA」が、if 文なしで宣言的に書ける。
- 実務では `-e key=val`（extra-vars）が最強。一時的な上書きやCI連携で使う。

## 確認
```bash
ansible RT03 -i hosts.ini -m ansible.builtin.debug -a "var=dojo_team"   # => OSAKA-NOC
ansible RT01 -i hosts.ini -m ansible.builtin.debug -a "var=dojo_team"   # => TOKYO-NOC
```

## よくある誤解
- group_vars/host_vars は **インベントリ（hosts.ini）と同じ場所**に置く（このワークスペース直下）。
- ファイル名はグループ名/ホスト名と一致させる（`routers.yml` / `RT03.yml`）。
