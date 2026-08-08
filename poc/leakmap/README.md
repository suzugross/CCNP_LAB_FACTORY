# BL-095 PoC: EIGRP summary-address leak-map エッジ挙動 (2026-08-07 完了)

- 盤面: problems/_POC-LEAKMAP (2× iol-xe 17.15, RT01–RT02 直結, AS 6571)。
  ユーザ手組みラボ「EIGRP leak-map」の複製+全Lo network 投入版。**ユーザラボは不触**。
- 実行: `scripts/lab.sh provision _POC-LEAKMAP` → `.venv/bin/python3 poc/leakmap/sweep.py`
- 生ログ: [results-raw.md](results-raw.md) / 確定表: problems/_drafts/EIGRP-LEAKMAP-PAPER.design.md

## 確定した挙動(要旨)

| 状態 | RT02 の受信 |
|---|---|
| summary のみ | /30 のみ |
| + leak-map(PL permit 1.1.1.3/32) | /30 + 1.1.1.3/32 [90] |
| leak-map の route-map **未定義** | **リークなし** |
| route-map 在り・prefix-list **未定義** | **全リーク** |
| route-map 在り・match なし permit | **全リーク** |
| prefix-list が成分に不一致 | リークなし |
| 成分投入 = redistribute connected | 明細 **D EX [170]**・集約 D [90] |
| match が標準 ACL | prefix-list と同様に機能 |
| 集約成分1個=リーク対象(ユーザラボ状態) | 集約+明細の両方届く |
| static Null0+redistribute static(networkは対象のみ) | 集約 D EX [170/281600] + 明細 D [90] |
| 全Lo network+Null0 static 再配送(summaryなし) | 抑止なし(全明細素通り) |
| 成分が全て external の summary+leak | 集約 D [90] 内部のまま・明細 D EX |
| ★エコ形(V4): redistribute connected と leak-map が**同一 route-map を共用**(対象/32のみ投入) | 成立: D /30 [90] + 対象 D EX [170](ユーザ発案・BL-096③) |
| ★共用編集の副作用(V5): 共用マップのリストを別 Lo へ変更 | 旧対象は**投入ごと経路表から消失**・新 Lo が D EX で出現(リーク変更のつもりが再配布まで変わる) |

★核心の非対称: route-map ごと無い→漏れない / 器だけ在って中身空振り→全部漏れる。
