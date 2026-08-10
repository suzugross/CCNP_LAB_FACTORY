# BL-108 決着 — グループ配下の timeout/retransmit (2026-08-10 23:20)

## H. `config-sg-radius` のヘルプに出るか

```
?
RADIUS Server-group commands:
  accounting        Specify a RADIUS attribute filter for accounting
  attribute         Customize selected radius attributes
  authorization     Specify a RADIUS attribute filter for authorization
  backoff           Retry backoff pattern (Default is retransmits with constant delay)
  cache             cached DB profile configuration
  deadtime          Specify time in minutes to ignore an unresponsive server
  default           Set a command to its defaults
  domain-stripping  Strip the domain from the username
  dscp              Set Radius dscp marking value
  exit              Exit from RADIUS server-group configuration mode
  host              Specify a RADIUS server
  ip                Internet Protocol config commands
  ipv6              IPv6 config commands
  key-wrap          Configure RADIUS key-wrap feature
  load-balance      Server group load-balancing options.
  mac-delimiter     MAC Delimiter for Radius Compatibility Mode
  no                Negate a command or set its defaults
  pick-method       Method by which the next host will be picked
  retransmit        Specify the number of retries to active server
  server            Specify a RADIUS server
  server-private    Define a private RADIUS server (per group)
  subscriber        Configures MAC Filtering RADIUS Compatibility mode
  throttle          Throttle requests to radius server
  timeout           Time to wait for a RADIUS server to reply
RT02(config-sg-radius)#
```

- `timeout` / `retransmit` の行: **出る** → retransmit        Specify the number of retries to active server / timeout           Time to wait for a RADIUS server to reply
- `timeout ?` → `timeout ? <1-1000> Wait time (default 5 seconds) RT02(config-sg-radius)#timeout`
- `retransmit ?` → `retransmit ? <1-100> Number of retries for a transaction (default is 3) RT02(config-sg-radius)#retransmit`

## F. グループ配下だけに置いたときの実所要(片系断)

| 置き場所 | 構成 | 1回目 | 2回目 | 期待 |
|---|---|---|---|---|
| グローバル | `RT02#how running-config | include ^radius-server (timeout|retransmit) /       ^ / % Invalid input detected at '^' marker.` | 4.4s | 4.4s | 2×2=**4 秒** |
| グループ配下のみ | `RT02#how running-config | include ^radius-server (timeout|retransmit) /       ^ / % Invalid input detected at '^' marker.` | 40.2s | 40.2s | 効けば 4 秒 / 効かなければ既定 5×4=**20 秒** |


## F2. グループ配下の値を変えても所要が動かない（決め手）

グローバルを消し、**グループ配下だけ**に値を置いて片系断でログインした。

| グループの値 | 実測 | 効いていれば |
|---|---|---|
| `timeout 2` / `retransmit 1` | **40.2s** | 4s |
| `timeout 10` / `retransmit 1` | **40.2s** | 20s |
| `timeout 2` / `retransmit 3` | **40.2s** | 8s |

**3 通りとも 40.2 秒で一致。値を 5 倍にしても所要は 1 秒も動かない。**
→ `server name` で参照する名前付きサーバに対して、**グループ配下の値は使われていない**。

★未解明: 40.2s の内訳。IOS 既定は `timeout 5 × (retransmit 3 + 1) = 20s` なので
その 2 倍にあたるが、2 台ぶんなのか 2 トランザクションぶんなのかは切り分けていない
（グローバルに `timeout 2 / retransmit 1` を置いた場合は 4.4s で、こちらは 1 回ぶん）。
