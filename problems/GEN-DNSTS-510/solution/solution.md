# GEN-DNSTS-510 解答（採点者用）

## 注入故障
- **allow_query_narrow** (server): allow-query の acl から 192.168.0.0/16 が漏れ → PC01 だけ REFUSED
- **acl_udp53** (nw): RT01 の RT02 側受信 ACL が UDP/53 だけ deny（ping/DHCP は通る）

## 修復
- サーバ側: `SRV01_fix.sh`（健全設定へ全量復元・受験者は差分修正でよい）
- NW側: `fix.json`（fix_generated.yml で投入可）

## 受験者に期待する切り分け
症状（PC01 の名前解決/リース/ルータの解決）→ サーバか経路かの二分 →
dig の status(REFUSED/SERVFAIL/timeout) と journalctl / show access-lists で確定。
