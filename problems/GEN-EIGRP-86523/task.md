# 問題 GEN-EIGRP-86523 : EIGRP 複合トラブルシュート（難易度5）

## 状況
単一 AS **100** の EIGRP 網（IPv4）で到達性障害。全ルータが全 Loopback へ
相互到達する状態へ復旧してください。

## トラブルチケット（代表症状・1件）
> **RT01 から RT02 の Loopback (`10.98.98.98`) へ到達できない。** 原因は1か所とは限りません。

## ルータ / Loopback 台帳（mgmt は割当順）
| ルータ | Loopback0 | mgmt(SSH) |
|--------|-----------|-----------|
| RT03 | `10.1.1.1/32` | 10.1.10.11 |
| RT02 | `10.98.98.98/32` | 10.1.10.12 |
| RT04 | `10.36.36.36/32` | 10.1.10.13 |
| RT06 | `10.34.34.34/32` | 10.1.10.14 |
| RT05 | `10.66.66.66/32` | 10.1.10.15 |
| RT01 | `10.78.78.78/32` | 10.1.10.16 |
| RT07 | `10.60.60.60/32` | 10.1.10.17 |

## 到達目標 / 切り分け
- 全ルータが全 Loopback を `show ip route eigrp` で学習し相互到達。
- トポロジ・故障の種類・場所・件数は非公開。有効化方式: 全機 **named mode**（`router eigrp CCNP` / `address-family ipv4 unicast autonomous-system 100`）。
- 切り分け: `show ip eigrp neighbors` / `show ip eigrp interfaces` / `show ip protocols` /
  `show ip route eigrp` / `show running-config | section eigrp`。
- ヒント（EIGRP の勘所）: **hello/hold の不一致では隣接は落ちない**。隣接不形成は
  K値・認証・passive・ACL・network 欠落など。設定変更後に隣接が戻らない時は
  `clear ip eigrp neighbors`。中継機が **stub** だと下流が丸ごと落ちる。

## アクセス・採点
SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜）。
```
ansible-playbook playbooks/grade.yml -e problem=GEN-EIGRP-86523 --vault-password-file <(printf 'CCNP\n')
```
