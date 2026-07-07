# 問題 ENCOR-WANHA-01 : デュアルGREトンネル + IP SLA/Track 自動フェイルオーバ

## シナリオ
本社(HQ)と支店(Branch)を、2つのトランジット（**Transit-A=primary / Transit-B=backup**）経由で
**GRE トンネル2本**で接続し、社内LAN同士を到達させます。さらに **IP SLA + Track** で
primary 経路を監視し、Transit-A 障害時に **自動で backup トンネルへ切り替わる**ようにします。

トランジット網（RT02/RT03）への到達性（underlay）は既設です。

## トポロジ
```
            RT02 (Transit-A / primary, 変更不可)
           /                              \
   10.0.12.0/30                      10.0.24.0/30
        /                                  \
   RT01 (HQ)                              RT04 (Branch)
        \                                  /
   10.0.13.0/30                      10.0.34.0/30
           \                              /
            RT03 (Transit-B / backup, 変更不可)
```

| ルータ | 役割 | Loopback0 | LAN(Lo10) | 管理IP(SSH) |
|--------|------|-----------|-----------|-------------|
| RT01 | HQ | 1.1.1.1/32 | 10.10.1.1/32 | `10.1.10.11` |
| RT02 | Transit-A / primary（**変更不可**） | 2.2.2.2/32 | — | `10.1.10.12` |
| RT03 | Transit-B / backup（**変更不可**） | 3.3.3.3/32 | — | `10.1.10.13` |
| RT04 | Branch | 4.4.4.4/32 | 10.10.4.1/32 | `10.1.10.14` |

- underlay（既設）: HQ↔Branch のトンネル終端アドレスへ、各トランジット経由で到達できます。
  - Transit-A 経由: HQ `10.0.12.1` ⇔ Branch `10.0.24.2`
  - Transit-B 経由: HQ `10.0.13.1` ⇔ Branch `10.0.34.2`

## 到達目標（HQ=RT01 と Branch=RT04 を構成）
1. **GRE トンネルを2本**作る。
   - **Tunnel1** … Transit-A 経由（HQ `10.0.12.1` ⇔ Branch `10.0.24.2`）。overlay = `172.16.1.0/30`
   - **Tunnel2** … Transit-B 経由（HQ `10.0.13.1` ⇔ Branch `10.0.34.2`）。overlay = `172.16.2.0/30`
2. **通常時は Tunnel1(primary) で HQ⇔Branch の LAN を到達**させる。
   - HQ から Branch LAN `10.10.4.1`、Branch から HQ LAN `10.10.1.1` へ到達できること。
3. **自動フェイルオーバ**を構成する。
   - 通常時は primary(Tunnel1) を使用し、Transit-A 障害時は自動的に backup(Tunnel2) へ切り替わること。
   - 切り替わった後も HQ⇔Branch の LAN 間通信が継続すること。

## 制約
- RT02 / RT03（トランジット）は変更不可。
- underlay の既設スタティックは変更しない（設定の追加で実現）。
- 「見せかけ」ではなく、実際に overlay 上で LAN 間が疎通すること。

## アクセス
SSH `SUZUKI / CCNP`（例: `ssh SUZUKI@10.1.10.11`）

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENCOR-WANHA-01 --vault-password-file <(printf 'CCNP\n')
```
