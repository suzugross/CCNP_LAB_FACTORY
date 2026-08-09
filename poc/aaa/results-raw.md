# BL-101 P0 PoC 生ログ — IOS AAA(RADIUS) エッジ挙動

自動生成: poc/aaa/sweep.py。盤面= _POC-AAA。delta は原則 RT02 に適用。

## E15 — ★list_undefined — 未定義リストを line に指定  (22s)

- **login SUZUKI (local+RADIUS)**
  - login: OK priv=15 (0.4s)
- **login noc-taro (RADIUS のみ)**
  - login: OK priv=15 (0.4s)
- **login emg-admin (local のみ)**
  - login: AUTH_FAIL 3.4s
- **(revert 後) login noc-taro**
  - login: OK priv=15 (0.3s)

**line vty**
```
line vty 0 4
 exec-timeout 0 0
 login authentication NOEXIST
 transport input ssh
```

## E15B — authorization 側の未定義リスト参照  (12s)

- **login noc-taro (RADIUS のみ)**
  - login: OK priv=15 (0.4s)
- **login SUZUKI (local+RADIUS)**
  - login: OK priv=15 (0.4s)

**line vty**
```
line vty 0 4
 exec-timeout 0 0
 authorization exec NOEXIST2
 transport input ssh
```

## E16 — ★enable 認証(既定 / RADIUS 経由)  (27s)

- **(a) 既定: helpdesk(priv1) → enable secret**
  - login: ENABLE_OK priv 1→15 (6.0s) 
- **(b) enable 認証を RADIUS 経由に: 同上**
  - login: ENABLE_FAIL priv 1→1 (6.0s) % Error in authentication.

## E17 — ★accounting exec start-stop  (12s)

- **login noc-taro(accounting 有効)**
  - login: OK priv=15 (0.4s)
- **radacct 配下(前)**
  - test aaa: `(なし)`
    ```
    (なし)
    ```
- **radacct 配下(後)**
  - test aaa: `/var/log/freeradius/radacct/10.0.0.2/detail-20260808`
    ```
    /var/log/freeradius/radacct/10.0.0.2/detail-20260808
    ```

**show aaa servers**
```
RADIUS: id 1, priority 1, host 10.99.1.2, auth-port 1812, acct-port 1813, hostname RAD1
     Estimated Outstanding Accounting Transactions: 0
     Estimated Throttled Accounting Transactions: 0
RADIUS: id 2, priority 2, host 10.99.2.2, auth-port 1912, acct-port 1913, hostname RAD2
     Estimated Outstanding Accounting Transactions: 0
     Estimated Throttled Accounting Transactions: 0
```
