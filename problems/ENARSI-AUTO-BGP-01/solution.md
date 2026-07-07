# 模範解答 : ENARSI-AUTO-BGP-01（自動化・技術拡張: BGP）

## 穴の答え
| 穴 | 答え | 意味 |
|----|------|------|
| ① | **ios_bgp_global** | AS番号・neighbor(remote-as) を宣言するグローバル設定モジュール |
| ② | **ios_bgp_address_family** | address-family ipv4 unicast の network/activate を扱うモジュール |
| ③ | **unicast** | `address-family ipv4 unicast` |
| ④ | **modified** | running≠startup のとき保存 |

完成形は `controller_solution/roles/bgp/{tasks,handlers}/main.yml`。

## ★ハマりどころ（実機検証で判明・重要）
- **AS番号は文字列**で渡す（int だと cisco.ios 11.x が `dictionary requested` エラー）。
- **router-id** は ios_bgp_global の `bgp.router_id` がこの版で不安定 → `ios_config` で補う。
- ios_bgp_global は **`no bgp default ipv4-unicast`** を入れるため、address-family で
  **neighbor を activate** しないと経路交換されない（`af_neighbors: activate:true`）。
  これは「リソースモジュールでも IOS の BGP 構造（global/AF/activate）を理解していないと動かない」良い教材。

## 要点：BGPは「グローバル」と「アドレスファミリ」で2モジュール
- `ios_bgp_global` … `router bgp <AS>` 直下（router-id、`neighbor … remote-as`）。
- `ios_bgp_address_family` … `address-family ipv4 unicast` 配下（`network`、redistribute、neighbor activate 等）。
- IOSの構造（グローバル／AF）がそのままモジュール分割に対応している、と理解すると迷わない。

## データ駆動のポイント
- host_vars をモジュール準拠キーで定義し、`neighbors`/`af_networks`/`af_neighbors` を
  **リストごとそのまま渡す**（変換不要）。ルータが増えても host_vars を足すだけ。

## 採点との関係（最終状態のみ）
- 両 `ios_bgp_global` でセッションが上がり（Established）、`ios_bgp_address_family` の network で
  Loopback が広告され、相手の RIB に `B 1.1.1.1/32` / `B 2.2.2.2/32` が入る。
- 手段は自由（`ios_config` 生 lines でも可）だが、リソースモジュールだと IOS の構造に沿って宣言でき冪等。

## 確認
```bash
cd lab/ENARSI-AUTO-BGP-01
ansible-playbook site.yml        # 1回目 changed / 2回目 changed=0（冪等）
# 目視:
ansible RT01 -i hosts.ini -m cisco.ios.ios_command -a "commands='show ip bgp summary'"
```

## 発展
- iBGP（同一AS・`update-source Loopback` ＋ next-hop-self）版。
- 経路制御（local-preference / MED / AS-path prepend）を route-map で。route-map は
  `ios_route_maps` リソースモジュール、neighbor への適用は ios_bgp_global/AF で。
