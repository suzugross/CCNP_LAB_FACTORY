# 問題 GEN-ZBXBUILD-200 : 監視一貫構築 — SNMPv3×Zabbix（難易度3）

## 状況
新設ルータ RT01〜RT03 を NOC の Zabbix 監視に組み込みます。監視サーバ ZBX01 は
構築済み（Web UI ログイン可・**ホスト未登録**）です。以下の**仕様書どおりの状態**を、
ルータ側・Zabbix 側の両方に構築してください。手順・画面操作は問いません。

## 環境
- Zabbix Web UI: `http://<ZBX01のMGMT IP>:8080/`（`Admin` / `zabbix`）
  - MGMT IP は provision 時の割当（既定 RT01=.11〜ZBX01=.14。並行ラボ運用時は
    オフセットされるため出題時の案内を参照）
- ZBX01 はインバンド 10.99.0.2 から各ルータへ到達可（経路設定済み）
- ルータの IP/OSPF は設定済み。**SNMP はどの機器にも未設定**。

## 仕様書 1: ルータ側 SNMPv3（RT01〜RT03 共通）
| 項目 | 値 |
|------|-----|
| view | `MONVIEW`（iso 配下すべて読み取り可） |
| group | `MONGRP`（v3 / **authPriv** / read view=MONVIEW） |
| user | `MONUSER`（認証 **SHA** `CCNP-Auth-2026` / 暗号化 **AES128** `CCNP-Priv-2026`） |
| アクセス制限 | **標準ACL 99** で SNMP 要求元を 10.99.0.2 のみに限定し group に適用 |
| その他 | location `CCNP-LAB` |

## 仕様書 2: Zabbix 側 監視登録（3 ホスト）
| 項目 | 値 |
|------|-----|
| ホスト名 | `RT01` / `RT02` / `RT03`（**大文字・完全一致**） |
| ホストグループ | `CCNP-LAB`（無ければ作成） |
| インターフェース | **SNMP**・対象 IP は下表の Loopback0・ポート 161 |
| SNMPv3 | 仕様書 1 のアカウント（authPriv / SHA / AES128） |
| テンプレート | `Cisco IOS by SNMP` |

| ルータ | 監視対象 (Loopback0) |
|--------|----------------------|
| RT01 | `6.6.6.6` |
| RT02 | `27.27.27.27` |
| RT03 | `95.95.95.95` |

## 到達目標（この状態になれば合格）
- ZBX01 から各 Loopback0 へ仕様のアカウントで SNMPv3 取得が成功する
- Zabbix の **Latest data で 3 ホストとも値が更新され続けている**（緑表示だけでは不十分）

## 注意
- ZBX01 の OS/Zabbix 本体はいじらない（登録操作のみ）。
- `snmp-server user` は running-config に表示されない仕様に注意。
- 登録直後の初回ポーリングまで最大 1 分待つこと。

## アクセス・採点
ルータ: SSH/コンソール `SUZUKI / CCNP`。採点は反映ラグがあるため attempts 多めで:
```
ansible-playbook playbooks/grade.yml -e problem=GEN-ZBXBUILD-200 -e max_attempts=20 \
  -e settle_delay=15 --vault-password-file <(printf 'CCNP\n')
```
