# BL-105 前提の裏取り — show aaa servers の DEAD 条件 (2026-08-10 23:05)

## C. 既定の構成に `dead-criteria` は入っているか

- `show running-config | include dead-criteria` → `(出力なし)`
- → **既定では入らない**。健全な盤面に持たせるには明示設定が要る。

## A/B. 片系断(SRV01 停止)で連続ログインしたときの State 推移

| dead-criteria | 直前 | 1回目 | 2回目 | 3回目 | 4回目 | RADIUS_DEAD ログ |
|---|---|---|---|---|---|---|
| dead-criteria 無し | (取得できず) | ✅6.4s<br/>10.99.1.2=current UP / 10.99.2.2=current UP | ✅6.3s<br/>10.99.1.2=current UP / 10.99.2.2=current UP | ✅6.3s<br/>10.99.1.2=current UP / 10.99.2.2=current UP | ✅6.3s<br/>10.99.1.2=current UP / 10.99.2.2=current UP | (出ず) |
| dead-criteria time 5 tries 1 | (取得できず) | ✅6.4s<br/>10.99.1.2=current UP / 10.99.2.2=current UP | ✅3.3s<br/>10.99.1.2=current DEAD / 10.99.2.2=current UP | ✅0.3s<br/>10.99.1.2=current DEAD / 10.99.2.2=current UP | ✅0.3s<br/>10.99.1.2=current DEAD / 10.99.2.2=current UP | `*Aug 10 23:09:16.492: %RADIUS-4-RADIUS_DEAD: RADIUS server 1` |

