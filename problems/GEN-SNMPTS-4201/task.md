# 問題 GEN-SNMPTS-4201 : 監視サービス復旧 — SNMPv3×Zabbix（難易度4）

## 状況
NOC の Zabbix で一部ルータの監視に異常が出ています。ダッシュボードの
「見え方」から障害を切り分け、**全ルータの監視が正常（SNMP 取得成功・緑）**に
戻るよう復旧してください。原因は 1 台・1 種類とは限りません。

## 監視環境
- Zabbix Web UI: `http://<ZBX01のMGMT IP>:8080/`（`Admin` / `zabbix`）
  - MGMT IP は provision 時の割当（既定 RT01=.11〜ZBX01=.14。並行ラボ運用時は
    オフセットされるため出題時の案内を参照）
  - Monitoring → Hosts / Latest data / Problems を活用
- 監視サーバ ZBX01 はインバンド（10.99.0.2）から各ルータの **Loopback0** を
  SNMPv3 でポーリングしている:

| ルータ | 監視対象 (Loopback0) |
|--------|----------------------|
| RT01 | `63.63.63.63` |
| RT02 | `91.91.91.91` |
| RT03 | `92.92.92.92` |

## NOC 標準の監視アカウント（機器側はこの仕様に合致していること）
- SNMPv3 user `MONUSER` / group `MONGRP`（**authPriv**）
- 認証: **SHA** / `CCNP-Auth-2026`、暗号化: **AES128** / `CCNP-Priv-2026`
- view `MONVIEW`（システム情報・IF 情報が取得できること）

## 到達目標
- Zabbix 上で RT01〜RT03 の SNMP 監視がすべて正常（緑・エラーなし）
- ZBX01 から各 Loopback0 への SNMPv3 取得と ping が成功

## 注意
- ZBX01（監視サーバ）の設定は正しい。**触るのはルータ側のみ**。
- `snmp-server user` は running-config に表示されない仕様に注意。
- 修正後、Zabbix の表示が緑に戻るまでポーリング周期ぶん（〜1分）待つこと。

## アクセス・採点
ルータ: SSH `SUZUKI / CCNP`。採点は修正反映のラグがあるため attempts 多めで:
```
ansible-playbook playbooks/grade.yml -e problem=GEN-SNMPTS-4201 -e max_attempts=20 \
  --vault-password-file <(printf 'CCNP\n')
```
