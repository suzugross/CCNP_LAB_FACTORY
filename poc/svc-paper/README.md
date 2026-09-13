# BL-170 紙面 Services 即答形ファミリ PoC 実測(iol-xe 17.15・2026-09-13)

紙面 `--shape svc` の exhibit と正誤判定の根拠。トポロジ `POC-SVC`(iol-xe ×2＋管理ブリッジ)を
provision し、ホスト(10.1.10.6)を SSH/SNMP/syslog/FTP/SCP の相手にして駆動(`sweep.py`)。
**採取後は撤収済み**(`sweep.py teardown`)。生ログは `results-raw.md`。

> ★**紙面は写像モデルが唯一の真実**(実機フルサイクルの安全網が無い・PAPER-BLUEPRINT-GAP §5-13)。
> 以下は対照付きで採った実測。**「定説と違う」結論は最も疑い、条件を1つずつ変えて確かめた**。

## 確定した挙動(正誤判定に使う)

### SSH(S1)
- 鍵なし= `SSH Disabled - version 2.0`。鍵生成で SSH Enabled。**ドメイン名(または hostname)が要る**
  (鍵名 `RT01.ccnp.local`)。既定 `Authentication timeout: 120 secs; Authentication retries: 3`。
- `transport input ssh` が無い vty(telnet のみ)へは SSH 不可(ポート拒否)。
- `login local` の vty はローカル・ユーザが要る。**access-class はセッションの発信元を絞る**。
- ★**この IOL イメージの癖(裏話に限定・正誤には使わない)**: `crypto key generate rsa modulus`
  は **512/768/1024 を拒否し 2048 が下限**(`% Invalid input`)。`show ip ssh` に
  `Minimum expected Diffie Hellman key size : 2048 bits`。`ip ssh version 1` も拒否。
  → 「v2 は 768 ビット以上」の定説と実機が食い違うので、**鍵長の数値を正解の弁別子にしない**
  (鍵の有無で判定する)。

### vty ログイン(S2/S2b・一部は console 同期の都合で S2c 再測予定)
- `transport input telnet` のとき SSH は拒否。`login local` は正ユーザで成功・誤/未定義ユーザで失敗。
- ★**注意(harness)**: 認証失敗の SSH セッションが vty を占有し 5 本埋まると以降 `Connection refused`
  になる(実発)。再測は毎回 `clear line vty 0-4` を挟む。

### logging(S3)
- **既定レベル**: Console / Monitor / Buffer = **debugging(7)**、**Trap = informational(6)**。
  (`show logging` の各行で確認)
- 宛先はそのレベル**以下(それ以上に深刻)**のみ表示。`logging trap warnings`(4)にすると
  シビアリティ 4 以下だけがサーバへ届く(syslog PRI `<188>`=local7.warning)。
- vty セッションにログを出すには `terminal monitor`(コンソールは既定で出る)。
- `send log <level> <text>` は `%SYS-<level>-USERLOG_<SEV>: Message from tty0(...): <text>` を作る。

### service timestamps(S4・クリーン)
| 構成 | ログ行の先頭 |
|---|---|
| `datetime`(msec なし) | `*Sep 13 09:18:37:` |
| `datetime msec` | `*Sep 13 09:18:39.349:` |
| `datetime msec localtime show-timezone`(clock timezone JST 9) | `*Sep 13 18:18:40.962 JST:` |
| `datetime localtime`(show-timezone なし) | `*Sep 13 18:18:44:` |
| `datetime year` | `*Sep 13 2026 09:18:42:` |
| `uptime` | `00:04:18:` |
| `no service timestamps log` | (タイムスタンプなし) |
| `service sequence-numbers`(＋datetime msec) | `000123: *Sep 13 ...` |
- **localtime を付けないと UTC**。clock timezone だけでは現地時刻にならない。

### debug condition interface(S5)
- `debug condition interface Et0/0` ＋ `debug ip packet/icmp` → **Et0/0 のトラフィックだけ**が全出力。
  他 IF(Et0/3)向けはほぼ抑止(自分宛の forus/echo reply だけ僅かに漏れる)。条件を外すと全 IF が出る。
- `no debug condition interface X` は削除の確認 `Proceed with removal? [yes/no]` を出す。

### NTP(S6・全同期は待たず認証フラグで判定)
- `ntp master`(引数なし)= **stratum 8**(既定)。`ntp master 5` = stratum 5。外部源なしでサーバ化。
- **認証は 鍵定義＋`ntp authenticate`＋`ntp trusted-key` の 3 点が揃って初めて成立**:
  - 鍵＋server key のみ(authenticate なし)= `show ntp associations` の ref clock 欄 **`.INIT.`**
  - ＋`ntp authenticate`(trusted-key なし)= **`.AUTH.`**(認証が要求されるが未完成)
  - ＋`ntp trusted-key`(完全)= `.AUTH.` のまま短時間はポーリング→(十分待てば)同期
  - reach は未同期の間 0。→ **exhibit は `.AUTH.`・reach 0 で描き、trusted-key 行の有無で原因を割る**。

### archive(S8/S8b)
- 未構成= `show archive` は `Archive feature not enabled`、`show archive log config all` は
  `% Config Logger disabled.`。
- `path`/`write-memory`/`time-period`(単位=**分**)/`maximum` が archive の下位コマンド。
- `configure replace` は **reload なしで差分ロールバック**。`show archive config differences` は
  `!Contextual Config Diffs:` に `-interface LoopbackNN` の形で差分を出す。`rollback timer` あり。
- `log config`＋`logging enable` で構成変更ログ。`notify syslog` で `%PARSER-5-CFGLOG_LOGGEDCMD`。
- ★**この IOL の癖(裏話に限定)**: **hidekeys が既定 ON**(既定で `secret *`/`community * ro` と伏字)、
  `no hidekeys` で初めて平文(`secret S3cretPW4`)。定説(hidekeys を明示して隠す)と既定の向きが逆なので、
  **「hidekeys が無いと平文で漏れる」を正解の弁別子にしない**(hidekeys が「伏字にする機能」であることだけ使う)。

### CEF(S9/S9b・クリーン)
- `show ip cef` の種別: **receive**=自分宛 / **attached**=直結解決 / **drop**=破棄
  (`0.0.0.0/8`・`127.0.0.0/8`・`224.0.0.0/4`・`240.0.0.0/4`)/ `no route`=既定経路なし。
- `... detail` の flags: `[receive, local, source eligible]`(自分宛)/
  `[attached, connected, cover dependents, need deagg]`(直結サブネット)/`[attached]`＋
  `Adj source: IP adj out of EtX`(解決済み隣接)。
- 静的経路: next-hop 未解決だが到達可能= `recursive via <nh> → recursive via <subnet> → attached to EtX`。
  Null0 宛= `attached to Null0`。IF 指定のみ= `attached to EtX`＋`show ip cef adjacency glean` に載る。
- **`no ip cef`** → `show ip cef` = `%IPv4 CEF not running`、`show ip interface` に
  `IP CEF switching is disabled`。**ping は 100% のまま**(プロセス・スイッチングが継続)。
- IF 単位 `no ip route-cache cef` → その IF だけ `IP route-cache flags are Fast, No CEF`。

### ファイル転送(S10)
- **FTP**: `copy running-config ftp://user:pass@host:port/file` 成功。`ip ftp username`/`ip ftp password`
  ＋`copy ... ftp://host:port/file` 成功。`ip ftp passive` で受動。パスワード誤りは失敗。
- **SCP サーバ**: `ip scp server enable` が要る。`aaa new-model` を有効にすると
  **`aaa authorization exec` が無いと `Sink: Privilege denied.`**(authentication だけでは不足)、
  authorization exec を足すと取得成功。aaa なし(`login local`＋priv15 ユーザ)なら取得成功。
- ★**harness の限界**: `copy running-config flash:X`・`dir flash: | include`・`tftp-server flash:X` が
  いずれも同じ `% Invalid input at ^` を返した(**既知の valid コマンドまで同様に失敗**)= unicon の
  コンソール同期の副作用であって IOS の非対応ではない。→ **tftp-server の可否は判定に使わない**。

### SNMP(S11・クリーン)
- コミュニティ: **RO は GET のみ・SET は `noAccess`**。RW は GET/SET 両方。
- **ACL が未定義**のコミュニティ= 全許可(GET 成功)。**ACL が発信元を許可しない**= 無応答(タイムアウト)。
- `show snmp` カウンタ: 誤コミュニティ= `Unknown community name`、RO への SET= `Illegal operation`。
- **v3 の指紋**(pysnmp から観測):
  | 事象 | 応答 |
  |---|---|
  | authPriv 正常 | 値が返る |
  | 認証パスワード誤り | **Wrong SNMP PDU digest**(認証失敗) |
  | 暗号パスワード誤り | **無応答**(復号失敗で黙って破棄) |
  | priv グループへ authNoPriv 要求 | **authorizationError** |
  | 未定義ユーザ / プロトコル不一致 | **Unknown USM user** |
  - `show snmp user` は Engine ID・Auth/Privacy Protocol・Group を表示(**鍵は出ない・running-config にも出ない**)。
- 通知: `snmp-server host X <comm>`(version 省略)= **v1 の trap・udp-port 162**。
  `informs version 1` = `%Informs not supported in SNMPv1`(**inform は v2c 以上**)。
  `snmp-server enable traps`(引数なし)= running-config に **91 行**展開(全種)。
  `show snmp host` は trap/inform と udp-port と security model を表示。

## 生成器への反映
- 実測を `gen_paper_svc.py` の `FACTS`(タグ排他)と分析形の真偽関数・exhibit に写像。
  「定説と違う」2 点(鍵長 2048 下限・hidekeys 既定 ON)は**解説の裏話に限定**し、正誤の弁別子にしない。
- `selftest` = 9 kind × 形 × 40 seed = **920 件 / NG 0**(一意性・決定性・因果なし・数非明示・組合せ全単射)。
- `gen_paper_mcq.py --shape svc` に統合(mixed 暫定 3%)。E2E: 7 形の生成・PYTHONHASHSEED 0/999 byte 一致・
  パックの解答 UI(ラジオ/チェックボックス/組合せ行)と正解キー/組合せキーの読み取りを確認。

## 未計測・保留
- SNMP の view(system excluded)は view 作成が console 同期で不完全だったため保留(設計上「裏話」扱い)。
- `tftp-server` の可否・`copy ... flash:`・`configure replace <file> force` は harness の同期問題で未確定
  (いずれも既知 valid コマンドまで同様に失敗するため、次回は file prompt / dialog を見直して再測)。
- vty の未定義 access-class の許可/拒否は S2c(paramiko 版)で確定予定。

## 深掘り: 「定説と違う」2 点の裏取り(S12 系・2026-09-13・Cisco 文書との突合)

> **ユーザ決定(2026-09-13)**: 公式が誤っている／方針未定／不明瞭の可能性があるものは**出題から捨てる**。以下の 2 点に加え、「ドメイン名が必須」(label で不要)・v3 の暗号鍵誤り=無応答／プロトコル不一致=Unknown user・timestamps の既定有無・DNA Center の警告文も`gen_paper_svc.py` から除外した(この節は研究記録として残す)。

対象イメージ= `Cisco IOS Software [IOSXE], Linux Software (X86_64BI_LINUX-ADVENTERPRISEK9-M), Version 17.15.1`。
`?` ヘルプの採取は unicon の状態機械を壊すため断念(`show running-config all` で既定値を直読みする方式に切替)。

### ① RSA 鍵長 2048 下限・SSHv1 廃止 = **版の仕様(文書あり)**であってイメージの癖ではない
| 実測(S12/S12e) | 結果 |
|---|---|
| `crypto key generate rsa modulus` 512/768/1024/1536 | すべて `% Invalid input`(パーサで拒否) |
| 同 2048/3072/4096・`general-keys modulus 2048 label X` | 受理 |
| `show running-config all` の既定 | **`ip ssh version 2`・`ip ssh dh min size 2048`**・`ip ssh time-out 120`・`authentication-retries 3`・kex に group14-sha1 なし |
| `ip ssh dh min size 1024`・`ip ssh version 1` | `% Invalid input` |
| `crypto engine compliance shield disable`(FN-72511 の回避策) | 受理され「take effect after reboot」と出るが **`write memory` しても startup-config に残らず、再起動後は `no ... disable`(既定=有効)に戻る**→ IOL では回避策を再現できない |
| RSA 鍵を消して **EC 鍵(`crypto key generate ec keysize 256`)だけ** | `show ip ssh`= Enabled(`ecdsa-sha2-nistp256` の hostkey)・ホストから SSH ログイン成功 |
- 文書: Field Notice **FN-72511**= 「IOS XE **17.11.1 以降**、2048 ビット未満の RSA 鍵は SSH で拒否される(17.6.1 から警告)。アップグレード時に SSH サーバが無効化される。回避= 2048 鍵の再生成、または `crypto engine compliance shield disable`(非推奨)」。
  Catalyst 9300/9600 の 17.6/17.12/17.15 リリースノート= 「**Use SSH Version 2. SSH Version 1 is not supported.**」、17.10 から group14-sha1/hmac-sha1 等が既定リストから除外。
- 結論: **「SSHv2 は 768 ビット以上」は旧 IOS/古い OCG の記述**。17.11 以降の実機では 2048 が下限で、しかも RSA 必須ですらない(EC 鍵で可)。
  出題は「鍵が要る」「v2 の既定」「dh min 2048」までを事実とし、**768/2048 の数値は版依存として裏話**に置く。
  「機器の画面に書いてある要件を読む」形(`%Please create EC or RSA keys ... (and of atleast 2048 bits for SSH v2 in case of RSA)`)なら版依存なしに出題できる。

### ② hidekeys = **文書は「既定で表示」だが 17.15.1 は既定で伏字**(文書との食い違い・出典未発見)
| 実測(S12d・**無垢の RT02** を対照) | 結果 |
|---|---|
| 無垢の `show archive log config all` / `show running-config all \| section archive` | `% Config Logger disabled.` / (空)= **構成変更ログは既定で無効(文書どおり)** |
| `archive / log config / logging enable` だけ入れて `username x secret y` | 記録は **`username x secret *`**= hidekeys 未設定でも伏字 |
| `show running-config all` の archive 節(RT01) | **`hidekeys` が既定として並ぶ**(明示しないと `show running-config` には出ない・`no hidekeys` は出る) |
| `no hidekeys` にして 12 種を再投入 | **全部平文**: `username password 0`・`username secret`・`enable password`・`enable secret`・`snmp-server community`・`ntp authentication-key`・`key-string`・`crypto isakmp key`・`ip ftp password`・line `password`・`ip ospf message-digest-key`・`neighbor password`(tacacs/radius の `key` は投入自体が harness で通らず未確認) |
| 起動ログ | `WARNING: Configured enable password CLI with weak encryption type 0 will be deprecated in future`(type 0 の enable password は起動時に警告) |
- 文書: Config Fundamentals コマンドリファレンスの `hidekeys`= **Command Default「Password information is displayed.」**(12.3(4)T 導入)、IOS XE 17.x のシステム管理ガイドも「hidekeys を有効にするとパスワードが表示されなくなる」= 明示で隠す前提。既定が変わったことを示すリリースノートは見つからず。
- 結論: 定説(明示して隠す)と実機(既定で隠す)が食い違う。**「hidekeys が無いと平文で漏れる」を正解にしない**方針は維持。
  版依存なしに出せる形= **`no hidekeys` が明示された構成 + 平文の記録**を見せて「伏字にするには」→ `hidekeys`(実測どおり no→平文/あり→伏字)。

### 教訓(BL-106 と同じ)
- 「定説と違う」は ①文書で版の境界を確認 ②無垢の対照で既定を直読み(`show running-config all`) ③回避策で逆向きに動かす、の 3 点を揃えてから採用/不採用を決める。今回 ①②は揃い、③は IOL の制約で不成立。
