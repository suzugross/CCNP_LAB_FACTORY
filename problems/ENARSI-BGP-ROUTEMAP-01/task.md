# 問題 ENARSI-BGP-ROUTEMAP-01 : route-map で prefix-list / as-path を合成した inbound 制御

## シナリオ
RT01 (AS65001) は隣接 RT02 (AS65002) から複数のプレフィックスを受信している。
RT02 は自社 (AS65002) の経路に加え、さらに先の RT03 (AS65003) からの経路も
中継してくる。新ポリシーで以下の inbound 制御を **1 つの route-map に合成**して
RT01 に実装したい:

1. **`10.10.0.0/16` の中の /24 単位の経路**（社内優先サービス） → 受信し、
   **local-preference を 200** に引き上げる。
2. **AS65003 を経由した経路**（外部AS 経由） → 受信を拒否する。
3. 上記以外の経路 → そのまま受信（デフォルト local-pref 100）。

## トポロジ
```
[Lo10  = 10.10.0.0/24]    [Lo172 = 172.16.0.0/24]
[Lo20  = 10.20.0.0/24]
       │
RT01 ─ eBGP ─ RT02 ──── eBGP ──── RT03
AS65001       AS65002 (transit)    AS65003
```

初期状態で RT01 の BGP テーブルには `10.10.0.0/24`、`10.20.0.0/24`、`172.16.0.0/24`
の 3 つが見える。

## 到達目標
- RT01 ↔ RT02 eBGP は Established で維持。
- RT01 BGP テーブル:
  - `10.10.0.0/24` が残り、best path の **local-pref = 200** であること。
  - `10.20.0.0/24` が残り、local-pref はデフォルト (100)。
  - `172.16.0.0/24` は **消えている** こと。

## 制約
- 変更は **RT01 のみ**。RT02 / RT03 は変更不可。
- inbound 制御は **1 つの route-map** に **複数 sequence** を並べて合成する。
  個別 prefix-list だけ / 個別 filter-list だけの解は不可。
- 中で使う部品 (受験者の自由):
  - 優先サービス系の prefix を見るには **prefix-list (`ge` 表記)** を使う。
  - AS65003 を見るには **as-path access-list** を使う。
- route-map は **inbound** で適用する。

## アクセス
- RT01: `10.1.10.11` / RT02: `10.1.10.12` / RT03: `10.1.10.13`（SSH, admin/CCNP）

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-BGP-ROUTEMAP-01 --vault-password-file <(printf 'CCNP\n')
```
