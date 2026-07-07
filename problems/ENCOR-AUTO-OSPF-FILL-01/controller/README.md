# 回答ワークスペース（ENCOR-AUTO-OSPF-FILL-01）

ルータには手で触らず、この Ansible 一式で OSPF を自動構成します。

## 手順
1. このフォルダごと自分の作業場所へコピー:
   ```bash
   cp -r problems/ENCOR-AUTO-OSPF-FILL-01/controller ~/lab && cd ~/lab
   ```
2. `hosts.ini` と `ospf.yml` の `__FILL_1__`〜`__FILL_4__`（計4か所）を埋める。
3. 実行:
   ```bash
   ansible-playbook -i hosts.ini ospf.yml
   ```
   - 3台すべて `changed` になれば設定が入っています。
   - もう一度実行して `changed=0`（=ok のみ）なら、冪等に書けている証拠です。

## つまずいたら
- `UNREACHABLE` … `hosts.ini` の `ansible_connection` / `ansible_user` / `ansible_password` を確認。
- `couldn't resolve module/action 'cisco.ios.__FILL_3__'` … `ospf.yml` のモジュール名（穴③）が未記入。
- 構成は入ったが採点が通らない … エリア番号（穴④）や OSPF プロセスIDを確認。

## ファイル
- `ansible.cfg` … 記入不要
- `hosts.ini`  … 穴①②
- `ospf.yml`   … 穴③④
