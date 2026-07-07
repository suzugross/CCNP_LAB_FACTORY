# Zabbix 監視 × SNMPv3 TS — PoC 結果 (2026-07-03)

CML 上の Ubuntu ノードに Zabbix を自動構築し、IOL を SNMPv3 で監視して
「ダッシュボードで異常が見える → 逆引き TS」が成立するかの検証。**全項目成功**。

## 検証環境（poc-zbx-lab.yaml）

- CML ラボ `POC-ZBX-SNMPV3`
  - **UB01** (ubuntu-24-04, RAM 4096 に上書き): ens2=10.1.10.20/27(MGMT, gw .30) / ens3=10.99.0.2/30(インバンド)
  - **RT01** (iol-xe 17.15.1): E0/3=10.1.10.19(VRF MGMT) / E0/0=10.99.0.1(グローバル) + SNMPv3(day0投入)
  - MGMT-SW(unmanaged) + external_connector(System Bridge)

## 確認できたこと

| 項目 | 結果 |
|---|---|
| cloud-init 複数ファイル(user-data + network-config)を topology YAML の `configuration:` リストで投入 | OK（静的IP2面・GW・DNS 適用） |
| ラボ内から internet (repo.zabbix.com) | OK（GW 10.1.10.30 経由, HTTP 200） |
| cloud-init packages(snmp) 導入 | 起動→cloud-init 完了 約20秒 |
| IOL SNMPv3 (view/group/user を day0 で投入, SHA/AES128) | OK。`snmp-server user` は day0 で有効化される |
| SNMPv3 応答: インバンド / **VRF MGMT 経由** | 両方 OK（VRF 追加設定不要） |
| Zabbix 7.0.27 (PostgreSQL+nginx) インストール | **実質 ~2分**（apt 33秒 + DB/設定） |
| フロントエンド setup ウィザードのスキップ | `/etc/zabbix/web/zabbix.conf.php` を直接配置で OK |
| Zabbix API でホスト登録（SNMPv3 authPriv + "Cisco IOS by SNMP" テンプレ） | OK。IF-MIB 自動発見含む 20+ アイテム収集 |
| 障害検知（UDP/161 遮断 = ping は生きて SNMP だけ死ぬ） | IF利用不可(赤) **~90秒** / 障害イベント "No SNMP data collection" **~5.5分** / 復旧検知 30秒 |
| リソース | UB01 使用 RAM ~700MB / ディスク 2.4GB → **RAM 3GB で十分**（既定2GBでも動く見込み） |

## ハマりどころ（再実装時の注意）

1. **スキーマ投入は zabbix ロールで行う**: `zcat server.sql.gz | sudo -u zabbix psql zabbix`。
   postgres スーパーユーザで入れると所有者不一致で server が起動しない
   （復旧は `GRANT ALL ON ALL TABLES/SEQUENCES IN SCHEMA public TO zabbix;`）。
2. **`php8.3-pgsql` を明示インストール**（無いとフロントエンドが "Possible values MYSQL" エラー）。
3. テンプレは **"Cisco IOS by SNMP" 単独**で付ける（ICMP ping 内包。"ICMP Ping" テンプレ併用は icmpping キー重複で host.create が失敗）。
4. ラボ一括 start で ubuntu ノードだけ DEFINED_ON_CORE のまま取り残されることがある
   → lab_up 側で「全ノード BOOTED」確認と個別 start リトライを入れる。
   ★真因判明(2026-07-03 本実装時): **image_definition の ID 違い**。正しくは
   `ubuntu-24-04-20241004`（`ubuntu-24-04` は存在しない）。存在しない ID でも
   import は通り、起動時にスケジューラが**無言で** QUEUED→DEFINED_ON_CORE に
   差し戻す（イベントにもエラーが出ない）。この PoC が起動できたのは不安定な
   偶然だった。イメージ ID は `GET /api/v0/node_definitions/<id>`（または diagnostics
   の node_definitions[].images）で正確に確認すること。
5. 障害イベント化まで既定 ~5.5分（nodata トリガ）。出題で待たせたくない場合は
   トリガの評価窓を短縮 or「IFの利用不可(赤)表示」(~90秒) を見せる導線にする。

## 将来実装への示唆

- インストールが ~2分なので**ゴールデンイメージ化は必須ではない**。cloud-init 全自動
  （zbx_install.sh を runcmd 化 + zabbix.conf.php 配置）で provision 毎に組んでも現実的。
  さらに短縮したければイメージ化は後から検討。
- **拡張性（ユーザ要件）**: 「監視で異常が見える」を入口に、SNMPv3 故障に限らず
  経路断・ACL・IF障害等も同じ枠組みで出題可能。実装時は
  ①ホスト登録（zbx_register.py の一般化: mgmt_map/problem.yml 駆動）と
  ②故障注入（既存 gen_*_ts.py）と
  ③採点(Zabbix API problem.get / item lastvalue / snmpget) を疎結合に。
- 監視経路はインバンド推奨（ルーティング障害も監視断として見える）。MGMT VRF 経由も可。

## 使い方メモ

- ラボ投入: `curl -sk -X POST https://10.1.10.10/api/v0/import -H "Authorization: Bearer $TOKEN" --data-binary @poc-zbx-lab.yaml`
- Zabbix Web UI: `http://10.1.10.20:8080/` （Admin / zabbix）
- UB01 SSH: suzuki / CCNP
- RT01 SNMPv3: POCUSER / SHA AuthPass123 / AES PrivPass123
