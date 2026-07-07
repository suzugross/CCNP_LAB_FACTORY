# 問題 ENCOR-IPSLA-01 : IP SLA + Track で primary/backup ISP 自動切替

## シナリオ
RT01 はデュアルホームで 2つの ISP（RT02 = primary / RT03 = backup）に接続している。
両 ISP の先には Internet コア (RT04) があり、そこで `8.8.8.8` が提供されている。
普段は **primary ISP (RT02) 経由でインターネット (8.8.8.8) に出る**が、
primary 区間で障害が起きた場合は **backup ISP (RT03) 経由に自動で切り替える**よう
RT01 を構成せよ。手動オペレーションを介さず、ルータが能動的に primary の到達性を
監視し、切替を実行できること。

## トポロジ
```
                            10.0.24.0/30
        RT02 (primary ISP) ───────────────┐
       / 10.0.12.0/30                      │
RT01 ─┤                                RT04 (Internet)  [Lo10] 8.8.8.8/32
       \ 10.0.13.0/30                      │
        RT03 (backup ISP) ────────────────┘
                            10.0.34.0/30
              （RT02 ↔ RT03 間にも inter-ISP リンク 10.0.23.0/30 あり）
```

- RT01 ↔ RT02: `10.0.12.0/30` (RT01=.1 / RT02=.2)  ← primary access
- RT01 ↔ RT03: `10.0.13.0/30` (RT01=.1 / RT03=.2)  ← backup access
- RT02 ↔ RT03: `10.0.23.0/30` (RT02=.1 / RT03=.2)  ← inter-ISP
- RT02 ↔ RT04: `10.0.24.0/30` (RT02=.1 / RT04=.2)
- RT03 ↔ RT04: `10.0.34.0/30` (RT03=.1 / RT04=.2)
- 目的地: `8.8.8.8/32` (RT04 = Internet コア上。**primary / backup どちらの ISP からも到達可**)
- RT01 の社内アドレス: `Loopback0 = 1.1.1.1`（疎通確認はこれを送信元にする）

## 到達目標
- RT01 はデフォルトルート (`0.0.0.0/0`) で `8.8.8.8` に到達する。
- 通常時は **primary (10.0.12.2 = RT02) 経由**を使う。
- primary の到達性が失われた瞬間に、**backup (10.0.13.2 = RT03) 経由**へ自動で切替わる。
- 切替後も `8.8.8.8` への通信（往復）が成立すること。

## 制約
- RT02 / RT03 / RT04 は変更不可（ISP / Internet 機器）。設定するのは RT01 のみ。
- 動的ルーティングプロトコルは使わない。スタティック + 到達性監視で実現する。
- 監視機構の指定値（採点が固定値で判定する）:
  - IP SLA のインスタンス番号は **1**
  - Track のオブジェクト番号は **1**
  - SLA は **ICMP echo**、ターゲットは **10.0.12.2**（RT02 の primary 側 IF）
- ルーティングの指定値:
  - primary default route は **next-hop 10.0.12.2**、Track 1 で監視
  - backup default route は **next-hop 10.0.13.2**、AD = **200**（フローティングスタティック）

## アクセス
- RT01: `10.1.10.11` / RT02: `10.1.10.12` / RT03: `10.1.10.13` / RT04: `10.1.10.14`（SSH, admin/CCNP）

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENCOR-IPSLA-01 --vault-password-file <(printf 'CCNP\n')
```
採点では設定・状態に加え、`8.8.8.8` への **実疎通**（RT01 からの往復）も確認する。

## フェイルオーバー実証（任意）
primary を実際に落として切替後も 8.8.8.8 に届くことを自動確認するには:
```
ansible-playbook playbooks/verify_failover.yml -e problem=ENCOR-IPSLA-01 --vault-password-file <(printf 'CCNP\n')
```
