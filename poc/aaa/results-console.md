# BL-101 P0 追試 — コンソール(line con 0)の認証挙動

自動生成: poc/aaa/console_probe.py。対象= _POC-AAA の RT02。

| ケース | 結果 | 詳細 |
|---|---|---|
| C1 console: default(group+local) / サーバ生存 / local のみの利用者 | **LOGIN_FAIL** | UniconAuthenticationError |
| C1 console: 同上 / RADIUS 台帳の利用者 | **OK** | priv=15 |
| C2 console: default(group+local) / **サーバ全断** / local のみ | **OK** | priv=15 |
| C3 console: 専用リスト CONSOLE=local / サーバ生存 / local のみ | **OK** | priv=15 |
| C3 console: 同上 / RADIUS のみの利用者 | **LOGIN_FAIL** | UniconAuthenticationError |
| C4 console: 専用リスト CONSOLE=local / **サーバ全断** / local のみ | **OK** | priv=15 |
| C5 console: **未定義リスト**参照 / サーバ生存 / local のみ | **LOGIN_FAIL** | UniconAuthenticationError |
| C5 console: 同上 / RADIUS 台帳の利用者 | **OK** | priv=15 |

最終の `line con` 構成(後始末後):
```
line con 0
 exec-timeout 0 0
 logging synchronous
 login authentication NOEXIST
```