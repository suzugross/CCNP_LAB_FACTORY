# NETAUTO-03-RESTCONF ワークスペース

| ファイル | 内容 |
|----------|------|
| `01_get.sh` | STEP1: curl で RESTCONF に GET（疎通確認と全IF取得） |
| `02_get_interfaces.py` | STEP2: Python requests で GET → JSON を表に加工 |
| `03_create_loopback.py` | STEP3: PUT で Loopback100 を作成（採点対象） |

進め方・機器側の準備（RESTCONF 有効化）は `問題.md` を参照。
`__FILL_n__` の穴一覧とヒントは `穴.md` を参照。
