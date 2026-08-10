# GEN-AAAGRP-51201 模範解答（採点者用）

投入は `solution/fix.json`（両ルータ同一）。要点だけ:

```
aaa new-model
radius server RAD1
 address ipv4 10.99.5.2 auth-port 1812 acct-port 1813
 key Srv1-5730
radius server RAD2
 address ipv4 10.99.6.2 auth-port 1912 acct-port 1913
 key Srv2-4893
aaa group server radius AAA-SRV
 server name RAD1
 server name RAD2
 deadtime 1
ip radius source-interface Loopback0
radius-server timeout 2
radius-server retransmit 1
radius-server dead-criteria time 5 tries 1
aaa authentication login default group AAA-SRV local
aaa authorization exec default group AAA-SRV local
aaa accounting exec default start-stop group AAA-SRV
```

## レビュー観点

- **送信元**: サーバの `clients.conf` は各ルータの **Loopback0 のみ**許可。
  `ip radius source-interface Loopback0` が無いと RT01 は直結 IF、RT02 は
  出口 IF の IP で送るため**不明クライアントとして無言破棄**され、
  Reject ではなく**タイムアウト**になる。「拒否されている」と読み違えやすい所。
- **サーバ毎の鍵**: SRV01=Srv1-5730 / SRV02=Srv2-4893。`radius server` ブロック内の
  `key` で個別に持つ。旧来の `radius-server host` 形は非推奨。
- **遅延**: 片系断のログイン遅延は `timeout × (retransmit+1)` で決まる
  (実測= timeout 3・retransmit 1 で 6.3 秒)。要件の 5 秒以内には
  `timeout 2 / retransmit 1`(4 秒)などが要る。
- ★**`deadtime` だけでは何も起きない**(実測 poc/aaa/results-deadcrit.md)。
  サーバが「応答不能」と判定されて初めて `deadtime` の出番になり、その判定条件は
  `radius-server dead-criteria` が決める。既定のままだと片系断で連続ログインしても
  **毎回 6.3 秒**待たされ続ける(DEAD 化しない)。`dead-criteria time 5 tries 1` を
  入れると 6.4 → 3.3 → **0.3 秒**と落ちる。挙動③はこの 3 回目で見ている。
  「書いたのに効かない」典型で、本問の主眼のひとつ。
- **ローカル予備の意味**: `group AAA-SRV local` の `local` が使われるのは
  **サーバ無応答のときだけ**。サーバが Reject を返した場合はローカルへ落ちない。
  だから RADIUS 台帳の SUZUKI 登録が必須(生成器が投入済み)。
- **やってはいけない解**: RADIUS 利用者を `username` でローカルにも作ると挙動④は
  通るが**挙動⑤で落ちる**(全断時に RADIUS 利用者が入れてしまうため)。
