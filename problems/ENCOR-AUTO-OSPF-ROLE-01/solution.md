# 模範解答 : ENCOR-AUTO-OSPF-ROLE-01（自動化・レベル2 モダン記法）

## 穴の答え
| 穴 | ファイル | 答え | 意味 |
|----|----------|------|------|
| ① | tasks `cisco.ios.____` | **ios_ospfv2** | OSPFv2 プロセスを宣言的に構成するリソースモジュール |
| ② | tasks `state: ____` | **merged** | 既存を消さず「あるべき状態」を足し込む（冪等） |
| ③ | tasks `loop: "{{ ____ }}"` | **interfaces** | host_vars の `interfaces:` リストを回す |
| ④ | tasks `notify: ____` | **save ospf config** | handlers/main.yml の `- name:` と一致させる |
| ⑤ | handlers `save_when: ____` | **modified** | running と startup が異なるとき保存 |

完成形は `controller_solution/roles/ospf/{tasks,handlers}/main.yml` を参照。

## 3つのモダン要素の要点
### ① リソースモジュール（宣言的）
`cisco.ios.ios_ospfv2` / `cisco.ios.ios_ospf_interfaces` は **生 CLI を書かず**「あるべき状態」を
構造（dict/list）で宣言する。`state: merged` は既存設定を尊重しつつ差分だけ投入するので、
**何度流しても同じ結果（冪等）**。`replaced`/`overridden`/`deleted` 等で状態管理の粒度を変えられる。

### ② データ駆動（host_vars + loop）
**設定値**（process_id / router_id / interfaces）は `host_vars/<host>.yml` に置き、**処理**（tasks）は
それを `loop` で回すだけ。ルータが増えても **host_vars を 1 枚足すだけ**で拡張できる。
`loop_control.label` でループ出力を読みやすくしている。

### ③ role 化 + handlers/notify
設定タスクが **changed** を返した回だけ `notify` で handler `save ospf config` が発火し、
`save_when: modified` で running→startup を保存する。**毎回 save しない**のが綺麗な作法。
2 回目の実行では changed=0 となり handler も走らない（=冪等＋handler の理解確認）。

## FILL-01 との対比（同じ課題・別の書き方）
| | FILL-01（クラシック） | ROLE-01（モダン） |
|---|---|---|
| 設定方法 | `ios_config` に生 lines | リソースモジュール `state: merged` |
| データ | playbook 直書き | host_vars に分離＋loop |
| 構造 | 単一 playbook | role（tasks/handlers/defaults） |
| 保存 | （なし） | handler + notify で変更時のみ |

採点（`grade.yml`）は**両者とも同一**（最終状態のみ）。つまり「書き方が違っても結果が同じなら同点」。

## 確認
```bash
ansible-playbook site.yml          # 1回目: changed + handler 実行
ansible-playbook site.yml          # 2回目: changed=0・handler スキップ（冪等）
# 機器に触れず状態だけ生成して確認したいとき（発展）:
#   tasks の state を 'rendered' にすると CLI を生成だけして流さない
#   state を 'gathered' にすると現状を構造化して取得できる
```

## 発展（次の一歩）
- `state: replaced` で「宣言した状態に厳密に一致させる（余計な設定は消す）」挙動を体験。
- `cisco.ios.ios_facts`（`gather_network_resources`）で現状を facts 化 → 差分管理。
- `meta/argument_specs.yml` で role 入力（ospf/interfaces）の型バリデーション。
- molecule で role 単体テスト（ansible04 の `tests/` 雛形を実装）。
