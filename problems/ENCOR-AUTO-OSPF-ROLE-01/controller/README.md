# 回答ワークスペース（ENCOR-AUTO-OSPF-ROLE-01・モダン記法）

FILL-01 の `ios_config` 生 lines とは違い、**リソースモジュール＋データ駆動＋role** で書く。

## 構成
```
controller/
├── ansible.cfg            … 記入不要
├── hosts.ini             … 記入不要（接続情報入り）
├── site.yml              … routers に role 'ospf' を適用
├── host_vars/RT0X.yml    … OSPF 設計データ（process_id/router_id/interfaces）★記入済み
└── roles/ospf/
    ├── tasks/main.yml    … 穴①〜④（リソースモジュール/state/loop/notify）
    ├── handlers/main.yml … 穴⑤（save_when）
    └── defaults/main.yml … 空
```

## 穴一覧（計5）
| 穴 | ファイル | 何を入れるか |
|----|----------|--------------|
| ① | tasks `cisco.ios.____` | OSPFv2 プロセス用リソースモジュール名 |
| ② | tasks `state: ____` | 既存を消さず足し込む宣言的ステート |
| ③ | tasks `loop: "{{ ____ }}"` | host_vars のインタフェース一覧の変数名 |
| ④ | tasks `notify: ____` | 発火させるハンドラ名（handlers の name と一致） |
| ⑤ | handlers `save_when: ____` | running≠startup のとき保存するモード |

## 手順
```bash
cp -r problems/ENCOR-AUTO-OSPF-ROLE-01/controller ~/lab-role && cd ~/lab-role
# tasks/main.yml と handlers/main.yml の __FILL_n__ を埋める
ansible-playbook site.yml
# 2回目実行で changed=0・"save ospf config" が走らない＝冪等＆handler理解OK
ansible-playbook site.yml
```

## ポイント
- **データ（host_vars）とロジック（tasks）が分離**されている。ルータが増えても host_vars を足すだけ。
- **リソースモジュール**は「あるべき状態」を宣言する（`state: merged`）。生 CLI を書かない。
- **handler は notify された回だけ**動く。毎回 save しないのが綺麗な作法。
