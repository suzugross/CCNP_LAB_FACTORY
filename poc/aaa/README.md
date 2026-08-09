# PoC 実測表 — IOS AAA (RADIUS) エッジ挙動 (BL-101 P0)

2026-08-08 実測。盤面= `problems/_POC-AAA`(SRV01/SRV02 FreeRADIUS ── RT01 ── RT02・IOL 17.15 /
Ubuntu 24.04 + FreeRADIUS 3.2.5)。生ログ= [results-raw.md](results-raw.md)・駆動= [sweep.py](sweep.py)。

**この表が紙面 `shape=aaa` の証拠の唯一の出所**であり、ラボ(GEN-AAAGRP / gen_aaa_ts)の
期待値もここに合わせる。設計= [../../problems/_drafts/AAA-BASE.design.md](../../problems/_drafts/AAA-BASE.design.md)。

## 盤面と台帳

| 要素 | 値 |
|---|---|
| RAD1 | SRV01 `10.99.1.2` auth-port **1812** / acct 1813 (標準) |
| RAD2 | SRV02 `10.99.2.2` auth-port **1912** / acct 1913 (★非標準) |
| 共有キー | 両サーバ共通 `Poc-Rad-1111` |
| clients 許可 | **ルータの Loopback0 のみ**(`10.0.0.1` / `10.0.0.2`) |
| 方式リスト | `aaa authentication login default group RADGRP local` / `aaa authorization exec default group RADGRP local` |
| タイマ | `radius-server timeout 3` / `retransmit 1` / group `deadtime 5` |
| SUZUKI | local **と** サーバ台帳の両方(priv 15・自動化/締め出し保険) |
| noc-taro | サーバのみ・`shell:priv-lvl=15` |
| helpdesk | サーバのみ・`shell:priv-lvl=1` |
| emg-admin | **local のみ**(priv 15)= 「RADIUS 台帳に無い」の観測用 |

## ★中核の実測表

| # | 故障種 | `test aaa` の応答 | 所要 | 実ログイン | サーバ側ログ(決め手) |
|---|---|---|---|---|---|
| B0 | (健全) | `User was successfully authenticated.` | **0.1s** | OK priv=15 / priv=1 | `Auth: Login OK: [noc-taro]` |
| E1 | `user_not_registered` | `User authentication request was rejected by server.` | **1.1s** | **AUTH_FAIL** | `Login incorrect (No Auth-Type found ...): [emg-admin/Emg-1234]` |
| E12 | 誤パスワード | 同上 (Reject) | 1.2s | AUTH_FAIL 3.4s | `Login incorrect (pap: ... does not match): [noc-taro/WrongPassword]` |
| E2 | `key_mismatch` | `No authoritative response from any server.` | **12.4s** | **local へ落ちる**(emg-admin OK priv=15 / 12.5s) | `Login incorrect (pap: ...)` ＋**パスワードが文字化け** |
| E3 | `src_iface_missing` | **同上・完全に同一文言** | **12.3s** | 同じく local へ落ちる (12.6s) | `Error: Ignoring request ... from unknown client 10.1.12.2` |
| E10 | `port_mismatch` | 同上 | 12.2s | local へ (12.6s) | (届かない) `show aaa servers` で当該サーバのみ **DEAD** |
| E9 | 全断 | 同上 | 12.1s | local へ (12.6s) / RADIUS のみのユーザは AUTH_FAIL | — |
| E8 | 片系断(RAD1 停止) | `User was successfully authenticated.` | **6.1s** | **OK priv=15** (6.5s) | RAD2 に `Login OK` |
| E4 | `no_authz_exec` | (認証は成功) | — | **OK だが priv=1 固着**(noc-taro も helpdesk も) | — |
| E5 | `authz_no_fallback` × 全断 | — | — | **EXEC_DENIED — SUZUKI も emg-admin も全員** | — |
| E6 | `list_not_applied` | — | — | RADIUS のみのユーザ AUTH_FAIL / **local ユーザは認証通過後 EXEC_DENIED** | — |
| E11 | (健全) | — | — | AVPair どおり priv=15 / priv=1 | — |
| E15 | `list_undefined`(authn) | — | — | **default と完全に同じ結果**(SUZUKI/noc-taro OK・emg-admin AUTH_FAIL) | — |
| E15B | `list_undefined`(authz) | — | — | 同上・**priv=15 が付く**(= default の認可が効いている) | — |
| E16a | enable(既定) | — | — | helpdesk priv1 → **enable secret で 15 へ昇格可** | — |
| E16b | enable を RADIUS 経由 | — | — | **ENABLE_FAIL `% Error in authentication.`**(priv 1→1) | `$enab15$` 不在で Reject |
| E17 | accounting exec | — | — | ログイン成功＋**Start/Stop が記録される** | `radacct/10.0.0.2/detail-20260808` |

## ★確定した知見(紙面・ラボの土台)

### 1. フォールバックの意味論 — Reject と timeout は別物(核心)

- **Reject では `local` に落ちない**(E1)。`emg-admin` は local に存在し、サーバも生きているのに
  **ログインできない**。`group RADGRP local` の `local` は**サーバ無応答(ERROR)時のみ**。
- **timeout では落ちる**(E2/E3/E9/E10)。同じ `emg-admin` が **12.5s 待たされて priv 15 で入れる**。
- → **「入れるか否か」より「何秒待たされたか」が原因を指す**。紙面の trace 形はこの 3 値
  (即 Accept 0.1s / 即 Reject 1.1s / 12s 待って local) で構成できる。

### 2. ★`key_mismatch` と `src_iface_missing` は機器側で区別できない

- `test aaa` の文言も所要秒数も **完全に同一**(`No authoritative response from any server.` / 12.3〜12.4s)。
- 決め手は**サーバ側ログだけ**:
  - キー不一致 → 要求は**届いている**。`Login incorrect (pap: ...)` で**パスワードが文字化け**して記録される
    (共有キーが違うので復号できない)。★さらにルータ側は Reject を受け取っても
    Response Authenticator を検証できず捨てるため、**サーバは「拒否した」のにルータは「無応答」と見る**。
  - 送信元誤り → 要求は**破棄される**。`Error: Ignoring request ... from unknown client <送信元IP>`。
- → 紙面の主題として成立する(「機器側の出力は同じ。どちらか判別せよ」)。**サーバ側ログを証拠として提示**するのが
  この shape の必須要素になる。

### 3. 送信元は拠点で変わる

`ip radius source-interface` を外すと、RT02(1ホップ先)は `10.1.12.2`、RT01(直結)は `10.99.1.1` で
到達する(E3/E3B)。clients が Lo0 のみ許可の設計だと**両方とも落ちる**が、ログに出る送信元が違うので
「どのルータの設定が抜けているか」を逆引きできる。

### 4. 認可(authorization)の 3 つの罠

- `aaa authorization exec` が無い → 認証は通るが **priv 1 固着**。AVPair の `shell:priv-lvl=15` は効かない(E4)。
- 認可にフォールバック節が無く全断 → **local ユーザも含め全員 exec 拒否**(E5)。
  **SUZUKI(自動化)すら入れない = 実運用の締め出し事故そのもの**。
- 認証は local で通っても、**認可が RADIUS を見に行って Reject されると exec 拒否**(E6)。
  §1 の「Reject は落ちない」が認可側にも同じく効く。

### 5. フェイルオーバーは 1 トランザクション内で成立する

RAD1 停止で **6.1s(= timeout 3s × 2 試行)後に RAD2 が応答**し、そのまま認証成功(E8)。
RAD1 は `show aaa servers` 上 **UP のまま**(DEAD 化しない)。所要は
`timeout × (retransmit+1) × 到達不能サーバ数` で説明できる(2 サーバ全滅なら 12s)。

### 6. deadtime の実効値

`deadtime 5` = **ちょうど 300s** で自然回復(`previous duration 300s` として記録)。
`clear aaa counters servers all` では **DEAD 状態は解除されない**(実測)。
→ ラボ採点・スイープでは **ケース間に「全サーバ UP」待ちを入れないと結果が壊れる**。

### 7. 非標準ポート(BL-001 の未検証リスク → 解消)

Ubuntu 24.04 / FreeRADIUS 3.2.5 で `sites-enabled/default` の `listen` ブロックを
**`type` ごとに** `port = 1912` / `1913` へ書き換えれば動作する(IPv4/IPv6 の 4 ブロック)。
`freeradius -XC` が `Configuration appears to be OK` を返し、`ss -lnup` に 1912/1913 が出る。
ルータ側は `address ipv4 <ip> auth-port 1912 acct-port 1913`、`show aaa servers` は
**`auth-port 1912`(コロン無し)** と表示する。

### 8. ★day0 の `!` はサブモードを抜けない(作問時の実装罠)

`aaa group server radius <名>` ブロックの直後に `!` を置いても config サブモードから出ない。
その後の `ip radius source-interface Loopback0` が**グループ配下**に入り、
グローバル側と**二重定義**になる。この状態でグローバル側だけ `no` しても
**送信元は Lo0 のまま**で「直したのに直らない」。
→ 生成器では `exit` を明示すること。なお `no ip radius source-interface` 単独は
**`% Incomplete command.`**(インタフェース名まで要る)。
※これは**故障種・錯乱肢として優秀**(「外したのに効かない」)なので P1 で `src_iface_group_level` として採用する。

### 9. ★未定義の方式リストを参照すると「default にフォールバック」= no-op

`line vty` に **存在しないリスト名**を指定しても拒否にはならず、**default 方式リストがそのまま効く**。
authentication(E15)・authorization(E15B) の**両方で同じ**。

- 結果は `login authentication` 行が**無い場合と完全に同一**
  (SUZUKI/noc-taro は入れる・emg-admin は入れない・priv 15 が付く)。
- → **`list_not_applied` と `list_undefined` は症状が区別できない**。
  切り分けは `show running-config | section line vty` を読むしかない。
- リポの蓄積との接続= prefix-list 未定義=全許可 / route-map 未定義=全拒否 に対し、
  **AAA の未定義参照は「default へ落ちる(no-op)」**。3つ目の類型として記録。

### 10. ★enable 認証 — Reject 非フォールバックが 3 層目でも成立

- 既定(`aaa authentication enable default` 未設定)では、priv 1 のユーザが
  **enable secret で priv 15 へ昇格できる**(E16a)。
- `aaa authentication enable default group RADGRP enable` にすると、
  RADIUS 側に `$enab15$` が無いため **Reject** → 後段の `enable`(= enable secret)へ**落ちず**、
  **`% Error in authentication.` で昇格不能**(E16b)。
- → **「Reject では後段メソッドへ落ちない」は authentication / authorization / enable の 3 層すべてで成立する
  統一原理**。紙面はこれを 1 本の軸として貫ける。
- 症状は「**入れるのに何もできない**」= `no_authz_exec`(priv 1 固着)と組み合わせると強い。

### 11. accounting — 動作する。ただし commands 課金は RADIUS では空振り

- `aaa accounting exec default start-stop group RADGRP` は動作し、
  **`/var/log/freeradius/radacct/<NAS-IP>/detail-YYYYMMDD`** に Start/Stop が記録される。
  記録には `Acct-Session-Id` / `NAS-Port-Id = "tty4"` / `Acct-Session-Time` /
  `Acct-Terminate-Cause = User-Request` などが載る。
- ★ **`NAS-IP-Address` は Loopback0 (`10.0.0.2`)** で、**ディレクトリ名がそのまま送信元の証拠**になる
  → §3(送信元)と直結する。「どのルータから来たか」を紙面で読ませられる。
- ★ **`aaa accounting commands 15 default start-stop group RADGRP` は CLI で受理されるが、
  RADIUS では記録がゼロ**(実測 `cmd=` 0 件。exec の Start/Stop は同時に記録されている)。
  コマンド課金は TACACS+ 前提の機能。→ **錯乱肢として最適**
  (「コマンド単位の記録が要る」要件に対し RADIUS で設定しても要件を満たさない)。
  なお削除時に `Accounting method list update failed!!` と表示されるが**実際には消える**。

### 12. ★コンソール(line con 0)の認証 — vty と同一規則。専用リストで分離できる

追試= [console_probe.py](console_probe.py) / 生ログ= [results-console.md](results-console.md)。
CML コンソールから実際にログインを試して測った(RT02)。

| # | 構成 | 利用者 | 結果 |
|---|---|---|---|
| C1 | console に専用リスト無し(= default `group local`)・サーバ生存 | local のみ | **入れない**(Reject は落ちない) |
| C1 | 同上 | RADIUS 台帳 | 入れる priv 15 |
| C2 | 同上・**サーバ全断** | local のみ | **入れる** priv 15(無応答→local) |
| C3 | `aaa authentication login CONSOLE local` を `line con 0` に適用・サーバ生存 | local のみ | **入れる** priv 15 |
| C3 | 同上 | RADIUS のみ | 入れない(local に居ない) |
| C4 | 同上・**サーバ全断** | local のみ | **入れる** priv 15 |
| C5 | console が**未定義リスト**を参照 | local のみ / RADIUS | **default と同じ結果**(vty の E15 と同一規則) |

→ 確定した規則:

- **console は vty と同じ規則で動く**(既定リストの解決・Reject 非フォールバック・
  未定義参照は default へ・priv は認可が与える)。console だから特別扱いという事実は無い。
- **要件「サーバ全断でも console からは入れること」の正解手段は、console 専用の方式リストを
  定義して `line con 0` に適用すること**(C3/C4)。専用リストが無ければ console は default と
  運命を共にし、**サーバが生きていて拒否を返す間は緊急用のローカル管理者すら入れない**(C1)。
- ★これは「サーバが落ちたときのため」ではなく「**サーバが生きているときのため**」の対策でもある、
  という点が直感に反する。紙面 `console_forgotten` の核心はここ。

### 13. ★★ルータ側 debug だけで全ての「無応答」を切り分けられる(サーバログ不要)

追試2= [debug_probe.py](debug_probe.py) / 生ログ= [results-debug.md](results-debug.md)。
`debug radius authentication` + `debug aaa authentication` + `debug aaa authorization`。

**発端(2026-08-08 ユーザ指摘)**: evidence 形の正解を「認証サーバの `radius.log`」に置いていたが、
**サーバログで何が読めるかは ENARSI の学習範囲に無い**ため、解答者は `show aaa servers` との差を
判断できず**設問として成立しない**。→ 機器側だけで切り分く道を測り直した。結果、**ある**。

| 状況 | debug の決定的な指紋 |
|---|---|
| 正常 | `Received from id ... Access-Accept` ＋ `Cisco AVpair [1] 19 "shell:priv-lvl=15"` |
| 台帳に無い / 誤パスワード | `Received from id ... Access-Reject`(復号は成功している) |
| **共有鍵の不一致** | `Received ... Access-Reject` **＋ `RADIUS: response-authenticator decrypt fail`** / `message-authenticator decrypt fail` / **`RADIUS: Response (nnn) failed decrypt`** → その後 `Request timed out!` |
| **送信元アドレスの誤り** | **`RADIUS: Pick NAS IP ... cfg_addr=0.0.0.0`** ＋ **`RADIUS/ENCODE: Best Local IP-Address <実送信元> for Radius-Server <サーバ>`** ＋ `NAS-IP-Address [4] 6 <実送信元>`。応答は一切無し |
| **待受ポートの取り違え** | 応答ゼロ。ただし **`Retransmit to (10.99.2.2:1812,1813)`** に**設定中のポート**が出るので仕様書と突き合わせられる |
| サーバ全断 | 応答ゼロ。ポート表記は正しい値のまま |

★**核心**= 「鍵不一致」は**応答を受け取っているのに復号に失敗して捨てている**ことが
`failed decrypt` で見え、「送信元誤り」は**そもそも応答が返ってこない**うえに
`Best Local IP-Address` が**実際の送信元をそのまま表示する**。
→ **`show aaa servers` と `test aaa` では同一に見える 4 つの状況が、debug では全て割れる。**

★**debug は設定値も露出する**(= 「debug から構成を推測する」出題が作れる):

| debug の行 | 読み取れる構成 |
|---|---|
| `cfg_addr=<addr>` / `0.0.0.0` | `ip radius source-interface` の有無と、その IF のアドレス |
| `NAS-IP-Address [4] 6 <addr>` | 実際に使われた送信元 |
| `Send Access-Request to <ip>:<port>` | サーバのアドレスと `auth-port` |
| `Started <n> sec timeout` | `radius-server timeout` の値 |
| `Retransmit to (...)` の回数 | `radius-server retransmit` の値 |
| `Fail-over to (<ip>:<port>...)` | グループの 2 台目と**登録順** |
| `Cisco AVpair "shell:priv-lvl=N"` | サーバが返す権限レベル |
| `Access-Accept` / `Access-Reject` | 台帳の登録有無 |

### 14. ★★方式リストの遍歴が debug に出るのは **enable 認証だけ**

追試3= [ext_probe.py](ext_probe.py) / 生ログ= [results-ext.md](results-ext.md)。

`debug aaa authentication` を**実ログイン**と**実 `enable`** の下で採り直した(従来の採取は
`test aaa` だったため、**方式リストを通らず**遍歴が 1 行も出ていなかった)。

| 事象 | service | debug に出るもの |
|---|---|---|
| SSH ログイン (X7) | LOGIN | `AAA/AUTHEN/LOGIN (id): Pick method list 'default'` **だけ** |
| コンソールログイン (X9c) | LOGIN | **同上**。`Method=` も `status=` も出ない |
| `enable` (X8/X10) | **ENABLE** | ★`using "default" list` → `Method=<グループ> (radius)` → `status = GETPASS/PASS/FAIL/ERROR` の**全遍歴** |

→ **紙面で「方式リストの遍歴を読ませる」形は enable 認証でしか作れない。**
ログイン層では `Pick method list` までしか出ないため、どのメソッドで通ったかは debug から読めない。

### 15. ★★enable 認証の debug — `FAIL` と `ERROR` の分岐がそのまま字面に出る

| # | 構成 / 状態 | debug の骨格 | 結末 |
|---|---|---|---|
| X8a | 方式リスト無し(既定)・正パスワード | `non-console enable - default to enable password` → `Method=ENABLE` | `status = PASS` |
| X8b | 同上・誤パスワード | 同上 | `AAA/AUTHEN(id): password incorrect` → `status = FAIL` |
| X8c | `group→enable`・**サーバ生存** | `using "default" list` → `Method=<G> (radius)` | ★`status = FAIL`(**enable へ落ちない**) |
| X10b | `group→enable`・**全断** | `Method=<G> (radius)` → ★`status = ERROR` → `Restart` → `Method=ENABLE` | `status = PASS` |
| X10c | 同上・誤パスワード | 同上 | `password incorrect` → `status = FAIL` |

→ 確定した読み方:

- **`status = ERROR` は「応答が無い」= 次のメソッドへ進む。`status = FAIL` は「拒否された」= そこで終わる。**
  §1 の統一原理が、debug の**単語**として現れる唯一の層。
- **`using "default" list` があれば方式リストが効いている。**
  無い場合は `non-console enable - default to enable password` となり、
  **`aaa authentication enable` が構成されていない**ことが読み取れる。
- 回線種別も文言に出る: コンソールは `console enable - default to enable password (if any)`、
  それ以外は `non-console enable - ...`。
- `Restart` は**次のメソッドへ移る際のマーカー**(トランザクション ID も振り直される)。

★測定の落とし穴: 「全断で enable」を測るには **local かつ priv 1** の利用者が要る。
RADIUS 専用の priv 1 利用者では**全断時にログインすらできず** enable に到達しない(X8d/X8e が空振り)。

### 16. ★★コンソールの認可は `aaa authorization console` が無ければ実行されない

同一条件(認可リスト= `group <G>` のみ・フォールバック無し・サーバ全断・
`line con 0` に `authorization exec` 適用済み)でグローバルコマンドの有無だけを変えた。

| # | `aaa authorization console` | コンソールログイン |
|---|---|---|
| X5 | **無し** | **入れる**(priv 15) = 認可が**実行されていない** |
| X6 | **有り** | **入れない** = 認可が実行され、フォールバック無し×全断で拒否 |

vty で同じ構成は EXEC 拒否になる(E5)。→ **コンソールだけは既定で認可が無効**。
`line con 0` に `authorization exec` を書いても、**グローバルの有効化が無ければ効かない**。

さらに、**そのとき権限レベルが何になるか**を昇格なしで測り直した
(追試4= [console_raw.py](console_raw.py)。既存の `console_probe.py` は pyATS が
**自動で enable へ昇格する**ため priv 値が信用できず、C1〜C5 の priv は無効)。

| # | コンソールの構成 | `aaa authorization console` | 利用者 | 結果 |
|---|---|---|---|---|
| X11a | 既定リスト(`group local`) | **無し** | RADIUS 台帳(AVPair `priv-lvl=15`) | ★OK **priv 1**(プロンプト `>`) |
| X11c | 同上 | **有り** | 同上 | OK **priv 15**(`#`) |
| X12a | 専用リスト(authn/authz とも local) | **無し** | local `username ... privilege 15` | ★OK **priv 1** |
| X12b | 同上 | **有り** | 同上 | OK **priv 15** |

→ ★**認可が実行されないと、権限レベルは 1 になる**。
RADIUS の AVPair も `username ... privilege 15` も**適用されない**。
「認可が走らなければ認証で通った素性の priv がそのまま出る」ではない。

★これは**紙面の既存出力の誤り**でもあった。生成器は `aaa authorization console` を
描いていないのに観測表のコンソール行を **priv 15** と書いており、
**提示した構成では提示した表を再現できない**状態だった(2026-08-08 修正)。

→ 作問への含意: 「構成は正しく見えるのにグローバルの有効化だけが無い」という
**故障種 `authz_console_disabled`** が作れる。また `aaa_model.py` は現在
コンソールにも認可を無条件で適用しており、**この点でモデルが実機とずれている**
(ただし現行の紙面出力に誤りは無い= コンソール行が認可で拒否になる盤面 0/1600 を検算済み)。

### 17. ★`if-authenticated` は exec を許すが **属性を与えない**

| # | 認可の方式列 | 状態 | 利用者 | 結果 |
|---|---|---|---|---|
| X1 | `group <G> if-authenticated` | 健全 | RADIUS 台帳 priv-lvl=15 | OK **priv=15** |
| X1 | 同上 | 健全 | RADIUS 台帳 priv-lvl=1 | OK **priv=1** |
| X2 | 同上 | **全断** | local `privilege 15` の利用者 | ★OK **priv=1** |
| X2b | `group <G> local`(対照) | **全断** | 同じ利用者 | OK **priv=15** |

→ 確定:

- グループが**応答する限り** `if-authenticated` は `local` と見分けがつかない(AVPair の priv がそのまま乗る)。
- **全断でフォールバックしたときに差が出る**。`local` は `username ... privilege 15` を適用するが、
  **`if-authenticated` は「認証済みか」しか見ないので権限レベルは 1 のまま**。
- → `no_authz_exec`(常に priv 1)との違いは **「サーバが応答するときの priv」**でしか判別できない。

★作問への反映(2026-08-08): 紙面の観測は**平常時しか出していなかった**ため、
フォールバック側の故障が**観測に一切現れていなかった**。
実際 `authz_no_fallback` は **60/60 の盤面で健全と同じ表**で、
「一部の利用者が操作できない」という設問文と矛盾していた。
→ 観測に **「認証サーバがすべて停止した場合」** の表を常設した(全故障種で一律に出す)。
これで 12 故障種すべてが観測に症状を出すようになった(0/60 = 症状なしの盤面は消滅)。
`authz_no_fallback`(全断で **SUZUKI 含め exec 拒否**)と
`authz_if_authenticated`(全断で **priv 1**)がここで初めて区別できる。

### 18. ★ACL で RADIUS を落とすと、機器側の症状はサーバ停止と**完全に同じ**

| # | ACL | `test aaa` | 所要 | 実ログイン | ACL カウンタ |
|---|---|---|---|---|---|
| X4 | out: `deny udp any any eq <auth-port>` | `No authoritative response from any server.` | 12.3s | local へ (12.6s) | ★`(4 matches)` = 2台×(初回+再送) |
| X4b | in: `deny udp any eq <auth-port> any` | **同一文言** | 12.3s | — | ★`(2 matches)` = 応答だけを落としている |

→ 確定:

- `test aaa` の文言・所要時間・`show aaa servers` の DEAD 表示は**サーバ停止/ポート違い/鍵不一致と区別できない**
  (`%RADIUS-4-RADIUS_DEAD` も同じく出る)。**唯一の決め手は `show ip access-lists` のカウンタ**。
- **out 方向(要求を落とす)と in 方向(応答だけを落とす)は、機器側では同じに見える**が、
  カウンタの向きと数で区別できる。in 方向は「要求はサーバに届いており、サーバ側では認証が成立している」。
- → evidence 形の正解クラスに `show ip access-lists` が加わる。
  ★**要求遮断(out)と応答遮断(in)は `debug radius authentication` でも完全に同一**なので、
  この 2 つを対立仮説にすると **`show ip access-lists` だけが唯一の決め手**になる。
  作問への反映後の実測= 正解の分布は **debug 44.3% / 構成 28.6% / ACL 27.1%**
  (導入前は debug 50.7% / 構成 49.3% の二択で、当てずっぽうで 5 割取れていた)。

## ラボ採点への含意(§5 の確定)

| 故障種 | SSH 採点 |
|---|---|
| E1 / E12(Reject 系) | **可**。ただし SUZUKI をサーバ台帳から外す故障は作らないこと |
| E2 / E3 / E9 / E10(timeout 系) | **可**。ただし**ログイン毎に約 12.5s** 遅延する(採点タイムアウト設計に反映) |
| E4 / E6 | 可(priv 1 固着・exec 拒否はユーザによる) |
| **E5(authz にフォールバック無し × サーバ断)** | **不可 — 全員 exec 拒否**。★**console 経由必須** |

→ `gen_aaa_ts.py` は **E5 系を含む場合のみ console 採点**に切り替える(既存 `collect_console` を使用)。

## 測定上の教訓(自分向け)

初回スイープは `test aaa` の完了検出を**固定 sleep + 不完全な正規表現**で行っており、
`No authoritative response from any server.` に一致せず 60s 待ち切って**全タイムアウト系の秒数が偽値**になり、
さらに次コマンドとバッファが混線して **E8 を「フェイルオーバー失敗」と誤記録**した。
→ **プロンプト(`#`)待ちの expect に作り直して再測**したのが本表。
**紙面の証拠にする値は、必ずプロンプト待ちで取ること。**
