# 問題 GEN-EIGRPV6-90761 : EIGRPv6(IPv6) 複合トラブルシュート — classic/named 混在（難易度5）

## 状況
**IPv6 のみ**・単一 AS **100** の EIGRPv6 網で到達性障害。全ルータが全 Loopback へ相互到達する
状態へ復旧してください。**有効化方式は classic（`ipv6 router eigrp`）と named
（`router eigrp CCNP6` + `address-family ipv6`）がルータ毎に混在**しています。

## トラブルチケット（代表症状・1件）
> **RT01 から RT04 の Loopback (`2001:DB8:40::40`) へ到達できない。** 原因は1か所とは限りません。

## ルータ / Loopback 台帳（mgmt は割当順）
| ルータ | Loopback0 | 方式 | mgmt(SSH) |
|--------|-----------|------|-----------|
| RT02 | `2001:DB8:32::32/128` | classic | 10.1.10.11 |
| RT07 | `2001:DB8:71::71/128` | classic | 10.1.10.12 |
| RT03 | `2001:DB8:23::23/128` | classic | 10.1.10.13 |
| RT01 | `2001:DB8:4::4/128` | classic | 10.1.10.14 |
| RT05 | `2001:DB8:52::52/128` | named | 10.1.10.15 |
| RT06 | `2001:DB8:46::46/128` | classic | 10.1.10.16 |
| RT04 | `2001:DB8:40::40/128` | named | 10.1.10.17 |

## 到達目標 / 切り分け
- 全ルータが全 Loopback を `show ipv6 route eigrp` で学習し相互到達。
- トポロジ・故障の種類・場所・件数は非公開。
- **EIGRPv6 の勘所**:
  - classic は **インタフェースで `ipv6 eigrp 100`** を打った所だけ参加。
  - named の IPv6 AF は **network 文が無く、IPv6 が付いた全IFが自動参加**。
    除外・停止は `af-interface <IF>` 配下の `shutdown`（＝ここが落とし穴になり得る）。
  - 認証は classic=IF直下 `ipv6 authentication ...`、named=af-interface 配下。
    named は **hmac-sha-256** も選べる（**両端で方式・鍵が一致しないと隣接不可**）。
  - hello/hold 不一致では隣接は落ちない。K値不一致は全隣接断。中継機の stub は下流丸ごと欠落。
- 切り分け: `show ipv6 eigrp neighbors` / `show ipv6 eigrp interfaces` / `show ipv6 protocols` /
  `show ipv6 route eigrp` / `show running-config | section eigrp`。

## アクセス・採点
SSH `SUZUKI / CCNP`。
```
ansible-playbook playbooks/grade.yml -e problem=GEN-EIGRPV6-90761 --vault-password-file <(printf 'CCNP\n')
```
