# BL-101 P2 追試2 — dead-criteria と deadtime (2026-08-09 08:34)

片系断(SRV01 停止)のまま連続 3 回ログイン。`deadtime 1` は共通。

| dead-criteria | 1回目 | 2回目 | 3回目 | 1回目の後の show aaa servers |
|---|---|---|---|---|
| dead-criteria 無し | ✅6.3s | ✅6.3s | ✅6.4s | `10.99.1.2:1812=current UP, duration 147 / 10.99.2.2:1912=current UP, duration 147` |
| time 5 tries 1 | ✅6.4s | ✅3.3s | ✅0.3s | `10.99.1.2:1812=current UP, duration 149 / 10.99.2.2:1912=current UP, duration 149` |
| time 5 tries 2 | ✅6.4s | ✅3.3s | ✅0.3s | `10.99.1.2:1812=current UP, duration 7s, / 10.99.2.2:1912=current UP, duration 151` |

