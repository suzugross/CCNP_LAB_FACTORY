# BL-101 P0 追試3 — 紙面拡張候補の裏取り

自動生成: poc/aaa/ext_probe.py。対象= _POC-AAA の RT02。

## X7 — ★★実ログイン時の方式リスト層 debug(Method= の遍歴)  (102s)

### X7a 健全 / RADIUS 台帳の利用者 → **OK priv=15 (0.4s)**

```
*Aug  8 21:46:13.828: AAA/BIND(0000006E): Bind i/f
*Aug  8 21:46:13.828: AAA/AUTHEN/LOGIN (0000006E): Pick method list 'default'
*Aug  8 21:46:13.832: AAA/AUTHOR/EXEC(0000006E): processing AV priv-lvl=15
*Aug  8 21:46:13.832: AAA/AUTHOR/EXEC(0000006E): processing AV service-type=7
*Aug  8 21:46:13.832: AAA/AUTHOR/EXEC(0000006E): Authorization successful
*Aug  8 21:46:15.895: AAA/AUTHOR: auth_need : user= 'noc-taro' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 1 list= '' AUTHOR-TYPE= 'commands'
```

### X7b ★健全 / local のみの利用者(サーバは Reject を返す) → **AUTH_FAIL 3.3s**

```
*Aug  8 21:46:32.343: AAA/BIND(0000006F): Bind i/f
*Aug  8 21:46:32.343: AAA/AUTHEN/LOGIN (0000006F): Pick method list 'default'
```

### X7c ★全断 / local のみの利用者 → **OK priv=15 (12.6s)**

```
*Aug  8 21:46:53.059: AAA/BIND(00000070): Bind i/f
*Aug  8 21:46:53.059: AAA/AUTHEN/LOGIN (00000070): Pick method list 'default'
*Aug  8 21:47:05.215: AAA/AUTHOR (0x70): Pick method list 'default'
*Aug  8 21:47:05.215: AAA/AUTHOR/EXEC(00000070): processing AV cmd=
*Aug  8 21:47:05.215: AAA/AUTHOR/EXEC(00000070): processing AV priv-lvl=15
*Aug  8 21:47:05.215: AAA/AUTHOR/EXEC(00000070): Authorization successful
*Aug  8 21:47:07.265: AAA/AUTHOR: auth_need : user= 'emg-admin' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 1 list= '' AUTHOR-TYPE= 'commands'
```

### X7d 全断 / RADIUS のみの利用者 → **AUTH_FAIL 14.5s**

```
*Aug  8 21:47:23.944: AAA/BIND(00000071): Bind i/f
*Aug  8 21:47:23.944: AAA/AUTHEN/LOGIN (00000071): Pick method list 'default'
```

## X8 — ★★実 enable 時の方式リスト層 debug(3層目)  (137s)

### X8a 既定(enable secret)・正しいパスワード → **OK priv=15**

```
*Aug  8 21:52:56.863: AAA/BIND(00000072): Bind i/f
*Aug  8 21:52:56.863: AAA/AUTHEN/LOGIN (00000072): Pick method list 'default'
*Aug  8 21:52:56.866: AAA/AUTHOR/EXEC(00000072): processing AV priv-lvl=1
*Aug  8 21:52:56.866: AAA/AUTHOR/EXEC(00000072): processing AV service-type=7
*Aug  8 21:52:56.866: AAA/AUTHOR/EXEC(00000072): Authorization successful
*Aug  8 21:52:58.912: AAA/AUTHOR: auth_need : user= 'helpdesk' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 0 list= '' AUTHOR-TYPE= 'commands'
*Aug  8 21:52:58.912: AAA/MEMORY: create_user (0x76050079C7F8) user='helpdesk' ruser='NULL' ds0=0 port='tty3' rem_addr='10.1.10.6' authen_type=ASCII service=ENABLE priv=15 initial_task_id='0', vrf= (id=0)
*Aug  8 21:52:58.912: AAA/AUTHEN/START (2674557635): port='tty3' list='' action=LOGIN service=ENABLE
*Aug  8 21:52:58.912: AAA/AUTHEN/START (2674557635): non-console enable - default to enable password
*Aug  8 21:52:58.912: AAA/AUTHEN/START (2674557635): Method=ENABLE
*Aug  8 21:52:58.912: AAA/AUTHEN (2674557635): status = GETPASS
*Aug  8 21:53:00.871: AAA/AUTHEN/CONT (2674557635): continue_login (user='(undef)')
*Aug  8 21:53:00.871: AAA/AUTHEN (2674557635): status = GETPASS
*Aug  8 21:53:00.871: AAA/AUTHEN/CONT (2674557635): Method=ENABLE
*Aug  8 21:53:00.891: AAA/AUTHEN (2674557635): status = PASS
*Aug  8 21:53:00.891: AAA/MEMORY: free_user (0x76050079C7F8) user='NULL' ruser='NULL' port='tty3' rem_addr='10.1.10.6' authen_type=ASCII service=ENABLE priv=15 vrf= (id=0)
*Aug  8 21:53:03.894: AAA/AUTHOR: auth_need : user= 'helpdesk' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 1 list= '' AUTHOR-TYPE= 'commands'
```

### X8b 既定(enable secret)・誤ったパスワード → **ENABLE_FAIL priv=1**

```
*Aug  8 21:53:21.076: AAA/BIND(00000073): Bind i/f
*Aug  8 21:53:21.076: AAA/AUTHEN/LOGIN (00000073): Pick method list 'default'
*Aug  8 21:53:21.081: AAA/AUTHOR/EXEC(00000073): processing AV priv-lvl=1
*Aug  8 21:53:21.081: AAA/AUTHOR/EXEC(00000073): processing AV service-type=7
*Aug  8 21:53:21.081: AAA/AUTHOR/EXEC(00000073): Authorization successful
*Aug  8 21:53:23.094: AAA/AUTHOR: auth_need : user= 'helpdesk' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 0 list= '' AUTHOR-TYPE= 'commands'
*Aug  8 21:53:23.094: AAA/MEMORY: create_user (0x760501C346B8) user='helpdesk' ruser='NULL' ds0=0 port='tty3' rem_addr='10.1.10.6' authen_type=ASCII service=ENABLE priv=15 initial_task_id='0', vrf= (id=0)
*Aug  8 21:53:23.094: AAA/AUTHEN/START (1539495431): port='tty3' list='' action=LOGIN service=ENABLE
*Aug  8 21:53:23.094: AAA/AUTHEN/START (1539495431): non-console enable - default to enable password
*Aug  8 21:53:23.094: AAA/AUTHEN/START (1539495431): Method=ENABLE
*Aug  8 21:53:23.094: AAA/AUTHEN (1539495431): status = GETPASS
*Aug  8 21:53:25.130: AAA/AUTHEN/CONT (1539495431): continue_login (user='(undef)')
*Aug  8 21:53:25.130: AAA/AUTHEN (1539495431): status = GETPASS
*Aug  8 21:53:25.130: AAA/AUTHEN/CONT (1539495431): Method=ENABLE
*Aug  8 21:53:25.150: AAA/AUTHEN(1539495431): password incorrect
*Aug  8 21:53:25.150: AAA/AUTHEN (1539495431): status = FAIL
*Aug  8 21:53:25.150: AAA/MEMORY: free_user (0x760501C346B8) user='NULL' ruser='NULL' port='tty3' rem_addr='10.1.10.6' authen_type=ASCII service=ENABLE priv=15 vrf= (id=0)
*Aug  8 21:53:28.112: AAA/AUTHOR: auth_need : user= 'helpdesk' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 1 list= '' AUTHOR-TYPE= 'commands'
```

### X8c ★サーバ生存 / group→enable ・正しいパスワード → **ENABLE_FAIL priv=1**

```
*Aug  8 21:53:45.728: AAA/BIND(00000074): Bind i/f
*Aug  8 21:53:45.728: AAA/AUTHEN/LOGIN (00000074): Pick method list 'default'
*Aug  8 21:53:45.731: AAA/AUTHOR/EXEC(00000074): processing AV priv-lvl=1
*Aug  8 21:53:45.731: AAA/AUTHOR/EXEC(00000074): processing AV service-type=7
*Aug  8 21:53:45.731: AAA/AUTHOR/EXEC(00000074): Authorization successful
*Aug  8 21:53:47.751: AAA/AUTHOR: auth_need : user= 'helpdesk' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 0 list= '' AUTHOR-TYPE= 'commands'
*Aug  8 21:53:47.752: AAA/MEMORY: create_user (0x760501C8F400) user='helpdesk' ruser='NULL' ds0=0 port='tty3' rem_addr='10.1.10.6' authen_type=ASCII service=ENABLE priv=15 initial_task_id='0', vrf= (id=0)
*Aug  8 21:53:47.752: AAA/AUTHEN/START (1560798390): port='tty3' list='' action=LOGIN service=ENABLE
*Aug  8 21:53:47.752: AAA/AUTHEN/START (1560798390): using "default" list
*Aug  8 21:53:47.752: AAA/AUTHEN/START (1560798390): Method=RADGRP (radius)
*Aug  8 21:53:47.752: AAA/AUTHEN (1560798390): status = GETPASS
*Aug  8 21:53:49.751: AAA/AUTHEN/CONT (1560798390): continue_login (user='helpdesk')
*Aug  8 21:53:49.751: AAA/AUTHEN (1560798390): status = GETPASS
*Aug  8 21:53:49.751: AAA/AUTHEN (1560798390): Method=RADGRP (radius)
*Aug  8 21:53:50.753: AAA/AUTHEN (1560798390): status = FAIL
*Aug  8 21:53:50.753: AAA/MEMORY: free_user (0x760501C8F400) user='helpdesk' ruser='NULL' port='tty3' rem_addr='10.1.10.6' authen_type=ASCII service=ENABLE priv=15 vrf= (id=0)
*Aug  8 21:53:52.745: AAA/AUTHOR: auth_need : user= 'helpdesk' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 1 list= '' AUTHOR-TYPE= 'commands'
```

### X8d ★全断 / group→enable ・正しいパスワード → **LOGIN_FAIL AuthenticationException**

```
*Aug  8 21:54:13.006: AAA/BIND(00000075): Bind i/f
*Aug  8 21:54:13.006: AAA/AUTHEN/LOGIN (00000075): Pick method list 'default'
```

### X8e ★全断 / group→enable ・誤ったパスワード → **LOGIN_FAIL AuthenticationException**

```
*Aug  8 21:54:41.825: AAA/BIND(00000076): Bind i/f
*Aug  8 21:54:41.825: AAA/AUTHEN/LOGIN (00000076): Pick method list 'default'
```

## X10 — ★★到達不能→enable へ落ちる 3層目の全景  (236s)

### X10a 健全 / group→enable ・正しい enable secret(参考) → **LOGIN_FAIL AuthenticationException**

```
*Aug  8 21:56:45.797: AAA/BIND(00000078): Bind i/f
*Aug  8 21:56:45.797: AAA/AUTHEN/LOGIN (00000078): Pick method list 'default'
```

### X10b ★全断 / group→enable ・正しい enable secret → **OK priv=15**

```
*Aug  8 21:57:08.561: AAA/BIND(00000079): Bind i/f
*Aug  8 21:57:08.561: AAA/AUTHEN/LOGIN (00000079): Pick method list 'default'
*Aug  8 21:57:20.701: AAA/AUTHOR (0x79): Pick method list 'default'
*Aug  8 21:57:20.701: AAA/AUTHOR/EXEC(00000079): processing AV cmd=
*Aug  8 21:57:20.701: AAA/AUTHOR/EXEC(00000079): processing AV priv-lvl=1
*Aug  8 21:57:20.701: AAA/AUTHOR/EXEC(00000079): Authorization successful
*Aug  8 21:57:22.744: AAA/AUTHOR: auth_need : user= 'lowlocal' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 0 list= '' AUTHOR-TYPE= 'commands'
*Aug  8 21:57:22.744: AAA/MEMORY: create_user (0x760501C3EFA8) user='lowlocal' ruser='NULL' ds0=0 port='tty4' rem_addr='10.1.10.6' authen_type=ASCII service=ENABLE priv=15 initial_task_id='0', vrf= (id=0)
*Aug  8 21:57:22.744: AAA/AUTHEN/START (519983022): port='tty4' list='' action=LOGIN service=ENABLE
*Aug  8 21:57:22.744: AAA/AUTHEN/START (519983022): using "default" list
*Aug  8 21:57:22.744: AAA/AUTHEN/START (519983022): Method=RADGRP (radius)
*Aug  8 21:57:22.744: AAA/AUTHEN (519983022): status = GETPASS
*Aug  8 21:57:24.722: AAA/AUTHEN/CONT (519983022): continue_login (user='lowlocal')
*Aug  8 21:57:24.722: AAA/AUTHEN (519983022): status = GETPASS
*Aug  8 21:57:24.722: AAA/AUTHEN (519983022): Method=RADGRP (radius)
*Aug  8 21:57:36.846: AAA/AUTHEN (519983022): status = ERROR
*Aug  8 21:57:36.846: AAA/AUTHEN/START (175242526): port='tty4' list='' action=LOGIN service=ENABLE
*Aug  8 21:57:36.846: AAA/AUTHEN/START (175242526): Restart
*Aug  8 21:57:36.846: AAA/AUTHEN/START (175242526): Method=ENABLE
*Aug  8 21:57:36.846: AAA/AUTHEN (175242526): status = GETPASS
*Aug  8 21:57:36.846: AAA/AUTHEN/CONT (175242526): continue_login (user='(undef)')
*Aug  8 21:57:36.846: AAA/AUTHEN (175242526): status = GETPASS
*Aug  8 21:57:36.846: AAA/AUTHEN/CONT (175242526): Method=ENABLE
*Aug  8 21:57:36.865: AAA/AUTHEN (175242526): status = PASS
*Aug  8 21:57:36.865: AAA/MEMORY: free_user (0x760501C3EFA8) user='NULL' ruser='NULL' port='tty4' rem_addr='10.1.10.6' authen_type=ASCII service=ENABLE priv=15 vrf= (id=0)
*Aug  8 21:57:36.922: AAA/AUTHOR: auth_need : user= 'lowlocal' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 1 list= '' AUTHOR-TYPE= 'commands'
```

### X10c ★★全断 / group→enable ・誤ったパスワード(他社題材と同型) → **ENABLE_FAIL priv=1**

```
*Aug  8 21:57:56.129: AAA/BIND(0000007A): Bind i/f
*Aug  8 21:57:56.129: AAA/AUTHEN/LOGIN (0000007A): Pick method list 'default'
*Aug  8 21:58:08.242: AAA/AUTHOR (0x7A): Pick method list 'default'
*Aug  8 21:58:08.242: AAA/AUTHOR/EXEC(0000007A): processing AV cmd=
*Aug  8 21:58:08.242: AAA/AUTHOR/EXEC(0000007A): processing AV priv-lvl=1
*Aug  8 21:58:08.242: AAA/AUTHOR/EXEC(0000007A): Authorization successful
*Aug  8 21:58:10.262: AAA/AUTHOR: auth_need : user= 'lowlocal' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 0 list= '' AUTHOR-TYPE= 'commands'
*Aug  8 21:58:10.262: AAA/MEMORY: create_user (0x760501EABDD8) user='lowlocal' ruser='NULL' ds0=0 port='tty4' rem_addr='10.1.10.6' authen_type=ASCII service=ENABLE priv=15 initial_task_id='0', vrf= (id=0)
*Aug  8 21:58:10.262: AAA/AUTHEN/START (1458250450): port='tty4' list='' action=LOGIN service=ENABLE
*Aug  8 21:58:10.262: AAA/AUTHEN/START (1458250450): using "default" list
*Aug  8 21:58:10.262: AAA/AUTHEN/START (1458250450): Method=RADGRP (radius)
*Aug  8 21:58:10.262: AAA/AUTHEN (1458250450): status = GETPASS
*Aug  8 21:58:12.258: AAA/AUTHEN/CONT (1458250450): continue_login (user='lowlocal')
*Aug  8 21:58:12.258: AAA/AUTHEN (1458250450): status = GETPASS
*Aug  8 21:58:12.258: AAA/AUTHEN (1458250450): Method=RADGRP (radius)
*Aug  8 21:58:18.333: AAA/AUTHEN (1458250450): status = ERROR
*Aug  8 21:58:18.333: AAA/AUTHEN/START (1192480936): port='tty4' list='' action=LOGIN service=ENABLE
*Aug  8 21:58:18.333: AAA/AUTHEN/START (1192480936): Restart
*Aug  8 21:58:18.333: AAA/AUTHEN/START (1192480936): Method=ENABLE
*Aug  8 21:58:18.333: AAA/AUTHEN (1192480936): status = GETPASS
*Aug  8 21:58:18.333: AAA/AUTHEN/CONT (1192480936): continue_login (user='(undef)')
*Aug  8 21:58:18.333: AAA/AUTHEN (1192480936): status = GETPASS
*Aug  8 21:58:18.333: AAA/AUTHEN/CONT (1192480936): Method=ENABLE
*Aug  8 21:58:18.352: AAA/AUTHEN(1192480936): password incorrect
*Aug  8 21:58:18.352: AAA/AUTHEN (1192480936): status = FAIL
*Aug  8 21:58:18.352: AAA/MEMORY: free_user (0x760501EABDD8) user='NULL' ruser='NULL' port='tty4' rem_addr='10.1.10.6' authen_type=ASCII service=ENABLE priv=15 vrf= (id=0)
*Aug  8 21:58:18.394: AAA/AUTHOR: auth_need : user= 'lowlocal' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 1 list= '' AUTHOR-TYPE= 'commands'
```

## X5 — ★コンソール認可 — グローバル無しでは効かないのか  (25s)

| 対象 | 条件 | 結果 |
|---|---|---|
| console: 認可= group のみ・全断・`aaa authorization console` **無し** | OK priv=15 |  |

## X6 — ★同上＋`aaa authorization console`  (37s)

| 対象 | 条件 | 結果 |
|---|---|---|
| console: 同じ状態＋`aaa authorization console` **有り** | LOGIN_FAIL CredentialsExhaustedError |  |

## X9 — ★コンソール login の方式リスト遍歴(SSH では出ない)  (129s)

### X9a 健全 / RADIUS 台帳の利用者 → **LOGIN_FAIL UniconAuthenticationError**

```
*Aug  8 22:05:00.035: AAA/AUTHEN/LOGIN (0000007E): Pick method list 'default'
```

### X9b ★健全 / local のみの利用者(サーバは Reject) → **LOGIN_FAIL UniconAuthenticationError**

```
*Aug  8 22:05:35.995: AAA/BIND(0000007F): Bind i/f
*Aug  8 22:05:35.995: AAA/AUTHEN/LOGIN (0000007F): Pick method list 'default'
*Aug  8 22:05:41.618: AAA/AUTHEN/LOGIN (0000007F): Pick method list 'default'
```

### X9c ★全断 / local のみの利用者 → **OK priv=15**

```
*Aug  8 22:06:15.042: AAA/BIND(00000080): Bind i/f
*Aug  8 22:06:15.042: AAA/AUTHEN/LOGIN (00000080): Pick method list 'default'
*Aug  8 22:06:27.995: AAA/MEMORY: create_user (0x76050079C7B0) user='emg-admin' ruser='NULL' ds0=0 port='tty0' rem_addr='async' authen_type=ASCII service=ENABLE priv=15 initial_task_id='0', vrf= (id=0)
*Aug  8 22:06:27.995: AAA/AUTHEN/START (3025344589): port='tty0' list='' action=LOGIN service=ENABLE
*Aug  8 22:06:27.995: AAA/AUTHEN/START (3025344589): console enable - default to enable password (if any)
*Aug  8 22:06:27.995: AAA/AUTHEN/START (3025344589): Method=ENABLE
*Aug  8 22:06:27.995: AAA/AUTHEN (3025344589): status = GETPASS
*Aug  8 22:06:28.096: AAA/AUTHEN/CONT (3025344589): continue_login (user='(undef)')
*Aug  8 22:06:28.096: AAA/AUTHEN (3025344589): status = GETPASS
*Aug  8 22:06:28.096: AAA/AUTHEN/CONT (3025344589): Method=ENABLE
*Aug  8 22:06:28.115: AAA/AUTHEN (3025344589): status = PASS
*Aug  8 22:06:28.115: AAA/MEMORY: free_user (0x76050079C7B0) user='NULL' ruser='NULL' port='tty0' rem_addr='async' authen_type=ASCII service=ENABLE priv=15 vrf= (id=0)
```

## X1 — if-authenticated / サーバ健全 — 属性は降ってくるか  (10s)

| 対象 | 条件 | 結果 |
|---|---|---|
| noc-taro (RADIUS priv-lvl=15) | サーバ健全 | OK priv=15 (0.5s) |
| helpdesk (RADIUS priv-lvl=1) | サーバ健全 | OK priv=1 (0.4s) |

## X2 — ★if-authenticated / サーバ全断 — 権限レベルは何になるか  (40s)

| 対象 | 条件 | 結果 |
|---|---|---|
| emg-admin (local priv 15) | サーバ全断 | OK priv=1 (12.6s) |
| SUZUKI (local priv 15) | サーバ全断 | OK priv=1 (12.6s) |

## X2b — 対照: 認可= group local / サーバ全断  (23s)

| 対象 | 条件 | 結果 |
|---|---|---|
| emg-admin (local priv 15) | サーバ全断・認可= group local | OK priv=15 (12.5s) |

## X4 — ★ACL で要求を落とす(out) — 症状はサーバ停止と同じか  (31s)

| 対象 | 条件 | 結果 |
|---|---|---|
| test aaa | Attempting authentication test to server-group RADGRP using radius / *Aug  8 22:14:51.720: %SYS-5-CONFIG_I: Configured from console by SUZUKI on vty0 (10.1.10.6)No authoritative response from any server. | 12.3s |
| emg-admin 実ログイン | OK priv=15 (12.6s) |  |

`acl`:

```
*Aug  8 22:15:04.281: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 1) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Aug  8 22:15:10.552: %RADIUS-4-RADIUS_DEAD: RADIUS server 10.99.1.2:1812,1813 is not responding.
*Aug  8 22:15:16.651: %SEC_LOGIN-5-LOGIN_SUCCESS: Login Success [user: emg-admin] [Source: 10.1.10.6] [localport: 22] at 22:15:16 UTC Sat Aug 8 2026
*Aug  8 22:15:16.651: %SSH-5-SSH2_USERAUTH: User 'emg-admin' authentication for SSH2 Session from 10.1.10.6 (tty = 1) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeededshow ip access-lists BLOCK-RAD
Extended IP access list BLOCK-RAD
    10 deny udp any any eq 1812 (4 matches)
    20 deny udp any any eq 1912 (4 matches)
    30 permit ip any any (7 matches)
```

`aaa_servers`:

```
RADIUS: id 1, priority 1, host 10.99.1.2, auth-port 1812, acct-port 1813, hostname RAD1
     State: current DEAD, duration 10s, previous duration 31866s
RADIUS: id 2, priority 2, host 10.99.2.2, auth-port 1912, acct-port 1913, hostname RAD2
     State: current UP, duration 53s, previous duration 300s
```

## X4b — ★ACL で応答だけ落とす(in) — 要求は届いている  (14s)

| 対象 | 条件 | 結果 |
|---|---|---|
| test aaa | Attempting authentication test to server-group RADGRP using radius / *Aug  8 22:20:38.735: %SYS-5-CONFIG_I: Configured from console by SUZUKI on vty0 (10.1.10.6)No authoritative response from any server. | 12.3s |

`acl`:

```
Extended IP access list BLOCK-RAD-IN
    10 deny udp any eq 1812 any (2 matches)
    20 deny udp any eq 1912 any (2 matches)
    30 permit ip any any (2 matches)
```

## X11 — ★コンソールの権限レベル(自動昇格なしで実測)  

pyATS を使わず CML 端末サーバ経由の素のコンソールで測る(unicon の自動 enable 昇格を排除)。対象= RT02。

| 対象 | 結果 |
|---|---|
| X11a ★RADIUS 台帳の利用者(AVPair priv-lvl=15) | OK priv=1 (プロンプト=>) |
| X11b local の利用者(username privilege 15) | AUTH_FAIL  |
| X11c ★RADIUS 台帳の利用者(AVPair priv-lvl=15) | OK priv=15 (プロンプト=#) |
| X11d local の利用者(username privilege 15) | AUTH_FAIL  |


## X12 — ★コンソール専用リストでの権限レベル(認可の実行有無)

pyATS を使わず CML 端末サーバ経由の素のコンソールで測る(unicon の自動 enable 昇格を排除)。対象= RT02。

| 対象 | 結果 |
|---|---|
| X12a ★local の利用者(username privilege 15)・認可は不実行 | OK priv=1 (プロンプト=>) |
| X12b local の利用者(username privilege 15)・認可が実行される | OK priv=15 (プロンプト=#) |

