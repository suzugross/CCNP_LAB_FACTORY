# GEN-RADIUS-100 模範解答（採点者用）

## サーバ側: SRV01_solve.sh（clients.conf 2台分＋authorize 3ユーザ＋restart）
## NW側: fix.json（aaa new-model → radius server ブロック → 方式リスト）

## レビュー観点
- SUZUKI を RADIUS に登録したか（**Reject では local へフォールバックしない**。
  登録漏れ＝自動化/採点の締め出し。これが本問最大の学び）
- clients.conf が 2 台分あるか（RT02 の送信元は 10.1.12.2）
- priv-lvl を AVPair で返しているか（monitor-op は priv1 = show 系のみ）
- 機器側は `test aaa` で検証してからセッションを切ったか
