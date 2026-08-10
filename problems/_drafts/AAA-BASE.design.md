# AAA 両刀ベース設計 — 紙面 `shape=aaa` × ラボ(構築/TS) 共通基盤 (BL-101)

2026-08-08 作成。ユーザ指示「AAA について、ラボ問も同時に出題できることも踏まえたベース。
サーバは用意できるので、実際の挙動を再現しつつ紙面・ラボ両刀で理解を深めたい」。

上位= [PAPER-BLUEPRINT-GAP.design.md](PAPER-BLUEPRINT-GAP.design.md)(BL-100) の優先題材 P-D。
ラボ構築問の既存設計= [GEN-AAAGRP.design.md](GEN-AAAGRP.design.md)(BL-001)。本メモはその上位に立つ
**「紙面とラボで盤面・故障語彙・評価モデルを共有する」ためのベース設計**。

## ★確定事項(2026-08-08 ユーザ決定)

1. **TACACS+ は後回し** — 第1弾は **RADIUS 単独**。TACACS+(コマンド認可・RADIUS との対比)は P4 へ。
2. **サーバは 2 台** — FreeRADIUS × 2。**片系障害・フェイルオーバーの演出を優先**(1台同居案は不採用)。
3. **PoC 優先** — P0(実機実測)を先に回し、その実測表を紙面の証拠にする。

---

## 1. 中核方針 — 1つの正準盤面を共有する

このリポで確立した流れ(leakmap / ospfv3pl / v6redist)を AAA にも適用する:

> **実機PoCで全件実測 → `poc/aaa/README.md` に実測表 → 紙面はその写像として合成 →
> ラボは同じ故障種を実機で再現**

**不変条件= 紙面の故障種名 (kind) とラボの故障種名を一致させる。**
紙面で読んだ症状がそのまま実機で踏めるので、両刀が相互強化になる。

### 正準盤面(4ノード + MGMT)

```
SRV01 (FreeRADIUS #1) ──┐
                        RT01 ────── RT02
SRV02 (FreeRADIUS #2) ──┘   10.1.12.0/30
```

- **RT01= サーバ直結**(送信元は直結IF)、**RT02= 1ホップ先**(送信元が egress IF になる)
  → 既存 `gen_radius_build.py` で実証済みの「送信元が拠点ごとに違う」罠を盤面に内蔵する。
- IF/IGP は健全構成で投入済み。**論点は AAA だけに絞る**(1 shape = 1 レバー)。
- ノード予算 4 → CML 20 ノード上限に余裕。**BL-099 の問題パック(紙面3＋ラボ2)にも同居可**。
- サーバは `ubuntu` family(既存 GEN-RADIUS と同じ)。init.sh で FreeRADIUS を自動構成。

---

## 2. 教育核心 — 「考えさせる」7 軸

| # | 軸 | 核心 |
|---|---|---|
| A | method list の解決 | default と名前付き / line への適用忘れ。「このVTYに結局どれが効くか」 |
| B | **フォールバックの意味論** | ★`group RAD local` の `local` は**サーバ無応答(ERROR)時のみ**。**Reject では local に落ちない**(既存問で実証済み) |
| C | 認証と認可の分離 | 認証は通るのに exec 認可で即切断 / priv 1 固着。`if-authenticated` の有無 |
| D | priv-lvl の授受 | RADIUS は `Cisco-AVPair shell:priv-lvl=N`。`aaa authorization exec` が無ければ priv 1 のまま |
| E | (P4)RADIUS と TACACS+ の差 | ポート/暗号化範囲/AAA分離/コマンド認可。**第1弾では扱わない** |
| F | 送信元アドレス | `ip radius source-interface` 欠落 → サーバ側 clients 未登録の送信元 → **Reject でなく無言破棄→timeout** |
| G | 締め出し(lockout) | 適用の**順序**を誤ると自分が切れる。紙面 patch 形の一等地 |

★ **B と F が「Reject と timeout の読み分け」に収束する**のがこの題材の骨格。
v6redist の trace 形(ping 3値)と同じ構造を `test aaa` の応答で作れる。

---

## 3. 紙面ファミリ `shape=aaa`

### 紙面に出す事実(証拠)

- `show running-config | section aaa` 抜粋 ＋ `line con 0` / `line vty 0 4` 抜粋
- **サーバ仕様書**(GEN-AAAGRP 設計の形式を流用。IOS コマンドは出さない)
  = ユーザ台帳(名前/priv)・共有キー・**受理する送信元**・待受ポート・サーバ生死
- `show aaa servers` 抜粋 / `test aaa group ... legacy` 結果 / `debug aaa authentication` 抜粋
  → **書式は P0 実測に忠実**(合成表でも桁・列・語順を守る= BL-095 read 形の教訓)

### 故障種 (kind) 候補 8 ★ラボと共通語彙

| kind | 症状(P0 で確定させる) |
|---|---|
| `list_not_applied` | 名前付きリストを定義したが VTY 未適用 → default が効く |
| `no_authz_exec` | 認証は通るが **priv 1 固着** |
| `authz_no_fallback` | 認可にフォールバック節が無く、サーバ断で全員 exec 不可 |
| `src_iface_missing` | 送信元が想定外 → サーバ無言破棄 → **timeout** |
| `key_mismatch` | 共有キー不一致 → こちらも **timeout**(★`src_iface_missing` と同症状= 切り分けが本題) |
| `user_not_registered` | サーバ台帳に無い → **Reject → local に落ちない** |
| `console_forgotten` | `aaa new-model` で console も default に巻き込まれる |
| `port_mismatch` | SRV02 の非標準待受ポートに `auth-port` を合わせていない → timeout |
| `src_iface_group_level` ★ | `ip radius source-interface` が**グループ配下**にあり、グローバル側を消しても効かない(P0 ⑦) |
| `list_undefined` ★ | line が**未定義リスト**を参照 → default へ落ちる no-op(P0 E15)。`list_not_applied` と**症状が同一** |
| `enable_via_radius` ★ | `aaa authentication enable default group RADGRP enable` で `$enab15$` 不在 → **昇格不能**(P0 E16b) |
| `cmd_acct_on_radius` ★ | コマンド課金を RADIUS で設定 → **CLI は通るが記録ゼロ**(P0 ⑪)。要件不充足系の錯乱肢 |

→ P0 の追加実測で **8 → 12 種**。`proto_mix`(TACACS+ を `group radius` に登録)は P4 で追加。

★ **常設の盤面要素にするもの**= **送信元アドレス**。AAA はトポロジ的思考がほぼ無い題材で、
放置すると「設定を読むだけ」に堕ちる。唯一ルーティングと交差するのが送信元で、
P0 で **RT01(直結)=`10.99.1.1` / RT02(1ホップ)=`10.1.12.2`** と拠点ごとに変わることを実測した。
→ **主症状を「片方の拠点だけ入れない」に置く**ことで、拠点差＝送信元差の推論を毎回要求する。
accounting の `radacct/<NAS-IP>/` もこの軸の証拠として使える(P0 ⑪)。

### 要件世界 (world) — ★4 種に絞る(2026-08-08 レビューで決定)

当初 6 種を挙げたが、**AAA では world 軸が leakmap/v6redist ほど効かない**と判断した。
あちらは world によって**採るべき技術手段そのものが反転**した(network+leak-map ↔ redistribute+leak-map)。
AAA の world の多くは「明らかな解を1つ禁止して残りを1つにする」=**反転ではなく消去**で、思考が一段浅い。
9 kind × 6 world = 54 のうち実際に成立するのは 20 前後で、しかも同工異曲になる見込み。

→ **本当に手段が変わる 4 種のみ採用**し、深さは **証拠軸(evidence 形)と認可の連鎖**で稼ぐ。

| world | 制約 | なぜ手段が変わるか |
|---|---|---|
| `default_frozen` | default 方式リストは変更禁止 | 名前付きリスト＋**line への適用**が必須解になる |
| `console_survives` | サーバ全断でも console からは入れること | console 用リストの分離が必須解になる |
| `server_frozen` | サーバ側台帳・clients は不可触 | 機器側だけで解く(送信元/local/リスト構成へ寄る) |
| `no_lockout` | ★切らずに移行する**順序**が要件 | 正解が「コマンド集合」でなく**順序**になる。patch 形専用 |

★ 非両立の組は `compatible_worlds()` で明示除外(BL-098 ⑤)。
例= `server_frozen` × `user_not_registered` は機器側だけでは解けない → 除外か「local へ寄せる」解に限定。

### 出題形 — ★evidence 形を新設(2026-08-08 決定)

- **read** — 「誰が・どこから・どの権限で入れるか」を表 4〜6 行で正誤判定
- **cause** — 「SSH は通るがすぐ切れる」「サーバ断で入れない」の原因(錯乱肢は claim を機械判定)
- **fix** — world に従った最小是正 **CLI**(散文にしない= BL-098 ②)
- **patch** ★ — 移行途中の状態から、**締め出さずに進める次の1コマンド**(AAA 固有の一等地)
- **trace** ★ — `Accept(0.1s)` / `Reject(1.1s)` / `無応答→12.5s 待って local` の 3 値読み分け
- **evidence** ★★**新設** — 「**次に取得すべき出力はどれか**」を問う

#### evidence 形を新設する理由(設計上の必然)

P0 で **機器側の出力が同一で原因が複数ありうるペア**が 2 組見つかった:

1. `key_mismatch` ↔ `src_iface_missing` — `test aaa` の文言も秒数も同一。
   **切り分けはサーバ側ログのみ**(届いて文字化け / `Ignoring request from unknown client`)
2. `list_not_applied` ↔ `list_undefined` — 未定義リスト参照は default へ落ちる no-op なので**症状が同一**。
   切り分けは `show running-config | section line vty` のみ

このとき、サーバ側ログを**常に出す**と「1行読むだけ」の浅い問題になり、**出さない**と正解が一意にならない。
→ 第3の道として **「この2つを切り分けるために次に何を見るか」を問う**。
これは ENARSI が測ろうとしている TS スキルそのもので、**既存 9 ファミリのどれにも無い形**。
**AAA 以外(BGP・OSPF・ACL)へも横展開できる**ので、紙面プラットフォーム全体への投資になる。

選択肢は「取得すべき出力」= `show running-config | section line vty` /
サーバの `radius.log` / `show aaa servers` / `debug aaa authentication` / accounting の
`radacct/<NAS-IP>/` など。**錯乱肢は「その出力では両者が同じ値になる」もの**を機械判定で選ぶ。

### 機械検証の要 — `topologies/aaa_model.py`(新規・★スコープ縮小版)

AAA には `acl_model.py` に相当する評価器が無いので新規に作る。ただし
**当初構想の「時間まで含む挙動モデル」は過剰かつ危険**と判断し縮小する(2026-08-08 レビュー)。
状態(DEAD 判定・deadtime・タイミング)まで持たせると、モデルが実機とずれた瞬間に問題が壊れる。

```
入力: 方式リスト定義(authn/authz/enable, default/named, メソッド列)
      line への適用(con/vty)  ※未定義リスト参照は default へ落ちる(P0 E15)
      サーバ台帳(user -> priv)・サーバ生死
      機器側サーバ定義(ip, key, auth-port)・サーバ側 clients(許可送信元, key)
      送信元設定(source-interface の有無 / ★グループ配下かグローバルか)
出力: (user, line) -> ok(priv) | reject | no_response(理由) | authz_fail
      ※★秒数はモデルに持たせない
```

- **秒数は式で後から出す**: `timeout × (retransmit+1) × 到達不能サーバ数`
  (P0 で 6.1s / 12.1〜12.4s として成立を確認済み)。
- これで `故障種9 × 世界4 × N seed` の**一意性 selftest**(直る候補≥2・要件適合=1)が回る。
- **ラボ側の採点期待値も同じモデルで出す** → 紙面とラボの判定一致を保証。
- ★ **機械検証は自モデルの誤りを検出できない**(BL-081)
  → 根拠は P0 実測表に一本化し、**各分岐に実測 E 番号をコメントで紐付ける**。
  **モデルは小さいほど安全**という判断でこの縮小を決めた。

---

## 4. ラボ側 — 2 段構え

1. **`GEN-AAAGRP`(既存 BL-001・設計済み)** = 構築問(難4)。
   FreeRADIUS 2台自動構築・named サーバグループ・**非標準ポート**・サーバ別キー・
   ローカルDBフォールバック・**3フェーズ挙動採点**(正常 / 片系断 / 全断)。
   本メモの決定(サーバ2台・RADIUS単独)と完全に一致するので**設計はそのまま使える**。
2. **`gen_aaa_ts.py`(新規)** = 故障注入 TS。**紙面と同一の kind** を実機で再現。
   `--faults 2` の複合は既存生成器の作法を踏襲(1ルータ1故障・非両立の組は除外)。

### 同時出題(両刀)の形

**紙面(shape=aaa の read/trace) → ラボ(同じ kind の TS)** をパックに並べる。
「紙面で読んだ症状を実機で踏む」構成。器は BL-099 の問題パックがそのまま使える。

---

## 5. ★運用制約(実装前に確定させる)

- **採点自身が締め出される**。AAA の故障は SSH 採点を殺し得る。
  → **TS の採点は console 経由を既定**とする(既存 `collect_console` 資産)。
  P0 で「どの kind が SSH 採点を殺すか」を実測し、console 必須の範囲を確定する。
- **自動化ユーザ SUZUKI は local とサーバ台帳の両方に置く**(既存問で確立済みの約束)。
- サーバ停止を伴う採点フェーズは **always 節で必ず復旧**させる(BL-001 設計を踏襲)。

---

## 6. P0 PoC 計画(最優先・これから実施)

- PoC パック= `problems/_POC-AAA/`(`_POC-V6REDIST` / `_POC-BGPDBG` と同じ保持方式)
- 実測表= `poc/aaa/README.md`
- 盤面= §1 の 4 ノード。SRV01/SRV02 とも FreeRADIUS を init.sh で自動構成。

### 測るもの(各ケースで共通に採取)

`test aaa group RAD <user> <pass> legacy` の**出力文言**と**所要秒数** /
実 SSH ログインの可否と `show privilege` / `debug aaa authentication` の行 /
`show aaa servers` の該当行 / **サーバ側ログ** `/var/log/freeradius/radius.log`

### ケース一覧

| # | 内容 | 確認したい核心 |
|---|---|---|
| B0 | 基線(正常・両サーバ生存・source-interface あり) | 全出力の基準形を採取 |
| E1 | `user_not_registered` | ★**Reject では local に落ちない**の再実証と文言採取 |
| E2 | `key_mismatch` | Reject でなく **timeout** になること・秒数 |
| E3 | `src_iface_missing` | ★**E2 と機器側で区別できるか**(紙面の主題の成否がここで決まる)。サーバ側ログの `Ignoring request from unknown client` の有無で差が出るか |
| E4 | `no_authz_exec` | ログイン可・**priv 1 固着**の見え方 |
| E5 | `authz_no_fallback` × 全断 | exec 拒否の実挙動(即切断か・文言) |
| E6 | `list_not_applied` | default が効いてしまう事の観測 |
| E7 | `console_forgotten` | `aaa new-model` 後の console 挙動(締め出し境界) |
| E8 | 片系断(SRV01 停止) | SRV02 での継続・**切替遅延の実測**(timeout × retransmit × deadtime) |
| E9 | 全断 | local フォールバック成功・遅延 |
| E10 | `port_mismatch`(SRV02 非標準ポート) | ★**FreeRADIUS 非標準ポート待受の設定手順**(BL-001 の未検証リスク)＋`show aaa servers` の実効値表記 |
| E11 | priv-lvl AVPair(1 と 15) | `aaa authorization exec` との組合せ表 |
| E12 | Reject 時の VTY 挙動 | 再プロンプト回数・`% Authentication failed` の出方 |
| E13 | `deadtime` の効き | 死んだサーバをスキップする時間 |
| E14 | `test aaa` と実ログインの乖離 | test は通るがログインは落ちる組があるか(**採点の妥当性に直結**) |

### PoC の成果物

1. `poc/aaa/README.md` の実測表(上記全ケース) — **紙面の証拠の唯一の出所**
2. 「どの kind が SSH 採点を殺すか」の一覧 → §5 の console 必須範囲の確定
3. 非標準ポート待受の手順(BL-001 のリスク解消)
4. `aaa_model.py` の分岐設計に必要な事実(失敗理由の判別可能性)

### ★P0 実施結果(2026-08-08 完了) — 実測表= [poc/aaa/README.md](../../poc/aaa/README.md)

B0+E1〜E12 を全件実測。設計に反映すべき確定事項:

1. **Reject と timeout の非対称が実証された**(核心)。
   Reject= 即時(1.1s)・**local へ落ちない**(local に居る emg-admin がサーバ生存下でログイン不可)。
   timeout= **12.5s 待って local へ落ちる**。→ **trace 形は「0.1s Accept / 1.1s Reject / 12.5s 待って local」の 3 値**で構成する。
2. ★**`key_mismatch` と `src_iface_missing` は機器側で完全に同一**(文言も秒数も)。
   決め手は**サーバ側ログのみ**= キー不一致は「届いて**パスワードが文字化け**」、
   送信元誤りは「`Ignoring request ... from unknown client <IP>`」。
   → **サーバ側ログを証拠として紙面に出すことがこの shape の必須要素**(当初案には無かった)。
   さらに**キー不一致ではサーバは Reject を返しているのにルータは「無応答」と見る**
   (Response Authenticator を検証できず破棄)= 紙面 cause 形の一等地。
3. 認可の罠が 3 つに整理された= `no_authz_exec`→**priv 1 固着** / `authz_no_fallback`×全断→**SUZUKI 含め全員 exec 拒否** /
   **認証 local 成功でも認可 RADIUS Reject で exec 拒否**(§1 が認可側にも効く)。
4. フェイルオーバーは**1 トランザクション内で成立**(6.1s= timeout×試行数)。所要は
   `timeout × (retransmit+1) × 到達不能サーバ数` で説明でき、**紙面の秒数を計算で出せる**。
5. `deadtime 5` = **ちょうど 300s**・`clear aaa counters servers all` では解除されない
   → ラボ採点/スイープは**ケース間に全サーバ UP 待ちが必須**。
6. **非標準ポートは動作(BL-001 のリスク解消)**。`listen` を type ごとに書き換え。
7. ★**day0 の `!` はサブモードを抜けない**= `aaa group server` 直後の `ip radius source-interface` が
   グループ配下に入り二重定義になる。「外したのに効かない」→ **故障種 `src_iface_group_level` として P1 で採用**
   (故障種は 8→9 種)。生成器では `exit` を明示すること。`no ip radius source-interface` 単独は `% Incomplete command.`
8. **console 必須範囲が確定**= `authz_no_fallback` × サーバ断 の族のみ SSH 採点不可。
   それ以外は SSH 可(ただし timeout 系はログイン毎に約 12.5s の遅延を採点設計に織り込む)。
   ※**解答者は普段 CML コンソールで解く**ので締め出し故障でも困らない。困るのは自動採点だけ
   → **E5 系を TS の故障種から外す必要は無い**(採点経路を console にすれば済む)。
9. ★**未定義の方式リスト参照 = default へフォールバック(no-op)**。authentication/authorization 共通。
   → `list_not_applied` と **症状が完全に同一**(2 組目の「区別不能ペア」= evidence 形の材料)。
   リポの類型に追加: prefix-list 未定義=全許可 / route-map 未定義=全拒否 / **AAA 未定義=default へ落ちる**。
10. ★**Reject 非フォールバックは authentication / authorization / enable の 3 層すべてで成立**。
    `aaa authentication enable default group RADGRP enable` は `$enab15$` 不在の Reject で
    `enable`(secret)へ落ちず `% Error in authentication.`。
    → **紙面はこの 1 本の統一原理で貫ける**(症状は層ごとに違うが原因は同じ)。
11. **accounting は動作**(`radacct/<NAS-IP>/detail-YYYYMMDD` に Start/Stop)。
    ★`NAS-IP-Address` が Loopback0 なので**ディレクトリ名が送信元の証拠**になる。
    ★**`aaa accounting commands 15` は RADIUS でも CLI 受理されるが記録ゼロ**(TACACS+ 前提)
    → 「コマンド単位の記録が要る」要件への**錯乱肢に最適**。

### ★レビューで決めた設計変更(2026-08-08)

| 項目 | 変更 | 理由 |
|---|---|---|
| 出題形 | **evidence 形を新設**(5→6 形) | 区別不能ペアが 2 組見つかり、ログを常に出すと浅く・出さないと非一意になるため |
| 要件世界 | **6 → 4 種**(`default_frozen`/`console_survives`/`server_frozen`/`no_lockout`) | AAA では world が「反転」でなく「消去」にしかならず、組合せが同工異曲になるため |
| `aaa_model.py` | **時間を持たせない**(4 値＋理由のみ・秒数は式) | モデルが実機とずれると問題が壊れる。小さいほど安全 |
| 故障種 | **8 → 12 種**(group_level / list_undefined / enable_via_radius / cmd_acct_on_radius) | 追加 PoC で 4 種が実測確認できたため |
| 盤面 | **送信元を常設要素**にし主症状を「片方の拠点だけ入れない」に | AAA 唯一のトポロジ性。放置すると「設定を読むだけ」に堕ちる |
| 段階 | **P1 を P1a/P1b に分割** | 一息では大きすぎる。目玉(evidence/trace)を先に出す |

---

## 7. 段階

★ P1 は一息では大きすぎるため **2 段に割る**(2026-08-08 決定)。

| 段 | 内容 | 実機 | 状態 |
|---|---|---|---|
| P0 | PoC — B0+E1〜E18 全件実測 | 要 | **完了 2026-08-08** |
| P1a | `aaa_model.py`(縮小版) ＋ **read / cause / trace / evidence** | 不要 | **完了 2026-08-08・出題可** |
| P1b | **fix / patch**(CLI 生成・一意性検証・`no_lockout` の順序問題) | 不要 | **完了 2026-08-08** |
| P2 | ラボ構築問 `GEN-AAAGRP`(BL-001 の設計を実装) | 要 | **完了 2026-08-09・出題可** |
| P3 | ラボTS `gen_aaa_ts.py`(紙面と同一 kind) | 要 | 未 |
| P4 | TACACS+ 拡張(コマンド認可・RADIUS との対比) | 要 | 後回し(ユーザ決定) |

P1a を先にするのは、**CLI 生成が不要で軽い**うえ、本ファミリの目玉である
**evidence 形と 3 値 trace がここに入る**ため。P1b は CLI の状態収束形(BL-095 の教訓)と
順序判定が要るので分ける。

## 7.5 ★P1a 実装結果(2026-08-08 完了・出題可)

成果物= [`topologies/aaa_model.py`](../../topologies/aaa_model.py) ＋
[`topologies/gen_paper_aaa.py`](../../topologies/gen_paper_aaa.py) ＋
`gen_paper_mcq.py --shape aaa`(mixed ルーレット合流済)。

検証:

- `aaa_model.py --selftest` = **PoC 実測 B0/E1〜E18 と全件一致**(各分岐に E 番号を紐付け)
- `gen_paper_aaa.py --selftest` = **4 形 2040/2040 成立** /
  **evidence 成立 240/540**(= 区別不能ペアに属する 4 種の全盤面) /
  **区別不能ペアは実測どおり 2 組のみ**
- E2E **36 問**を機械検分(4 形すべて出現・全 9 種・正解一意・漏えい 0・空節 0)
- 既存 9 shape ＋ mixed の回帰 OK

### ★実装で判明した知見(次のファミリにも効く)

1. **潜在故障の罠** — 故障には「観測集合に載らないと現れない」型がある。
   `port_mismatch` / `authz_no_fallback` は **1 台目が応答している限り健全に見え**、
   `enable_via_radius` は **特権昇格を観測しないと現れない**。
   → 盤面に「SRV01 計画停止」を持たせ、観測表に**特権昇格の行**を足して顕在化させた。
   これを怠ると「健全と同じ指紋」の種別が量産され、**evidence 形の対立仮説が偽物になる**
   (自己検査が実際に検出した。偽ペアが 8 組 → 修正後は実測どおりの 2 組)。
2. `src_iface_group_level` は **現在状態としては健全**(是正が効かない罠)。
   現在状態の種別ではなく **P1b の fix/patch 対象**として扱う。
3. **evidence の一意性は「提示した選択肢の中で一意」で担保する**。
   区別できる観測が複数あるときは、そのうち 1 つだけを正解として出し、
   他方は**選択肢に出さない**(出すと 2 正解になる)。
4. ★**BL-088 の不親切化(`obfuscate_md`)と evidence 形は衝突する**。
   設問の統一(`GENERIC_ASK`)と症状の抽象化(`VAGUE_SYMPTOM`)により、
   **対立する 2 仮説と「何を問うているか」が消えて解答不能**になった。
   → `keep_ask=True` を追加して設問文と症状本文を温存する。
   **「設問文そのものが情報の担い手である出題形が存在する」**は BL-088 側にも効く一般知見。
5. `obfuscate_md` が **空の `## 設定抜粋` 見出しを常に出していた**のを修正(全 shape に効く)。

### ★P1a 追加拡張(2026-08-08・初回出題 2/3 の所見を受けて)

**(1) console 観測の追加** — 追試 [console_probe.py](../../poc/aaa/console_probe.py)(実測 C1〜C5)。
`console_survives` を要件に出しながら **観測表が vty しか無く判定できない**状態だったのを是正。

- **console は vty と完全に同じ規則**で動く(既定リストの解決・Reject 非フォールバック・
  未定義参照は default へ・priv は認可が与える)。console 固有の特別扱いは無い。
- ★核心= 要件「サーバ全断でも console から入れること」の正解手段は
  **console 専用の方式リストを `line con 0` に適用すること**。専用リストが無いと、
  **サーバが生きていて拒否を返している間は緊急用のローカル管理者すら入れない**。
  「サーバが落ちたときのため」ではなく「**サーバが生きているときのため**」でもある、
  という点が直感に反する。
- → 観測表に console 行を追加し、**故障種 `console_forgotten` を復活**(9→10 種)。

**(2) evidence 形の 3 つ巴化** — 初回出題で **「消去法でも解ける」**弱点が出たため。

- 仮説は **提示物だけで見分けがつかない候補**から採る(`shown_signature` = 結果表 + `test aaa` のみ。
  evidence 形は構成も `show aaa servers` も出さないので、`signature()` より粗い指紋が正しい)。
- **`srv1_down` を独立に抽選**するようにし、「1 台目が停止している」状況を作れるようにした。
  この状況では **鍵不一致 / 送信元誤り / ポート取り違えが同じ症状に化ける** → 3 つ巴が成立。
- 設問は **「最も多くの候補を除外できる出力はどれか」**。各観測を
  **「仮説ごとに何通りに割れるか」で機械採点**する:
  サーバログ = 3 分割 / 送信元設定・`show aaa servers` = 2 分割 / `line vty`・`line con`・`test aaa` = 1 分割。
- ★**錯乱肢に「2 分割までしかできない惜しい選択肢」が入る**ため、消去法が効かなくなった。

検証= 家族 selftest **4 形 2280/2280** / **evidence 300/600**(3 つ巴は evidence 可能盤面の約 4 割) /
E2E **50 問**機械検分(10 種・console 行・`line con` 2 拠点分・3 つ巴の設問文・漏えい 0) /
全 9 shape ＋ mixed の回帰 OK。

### ★総監査の結果と規約(2026-08-08)

9 観点の機械検査で 6 件検出・5 件修正(詳細= BACKLOG BL-101)。ここには**規約として残すもの**だけ書く:

1. **決定性**: 生成経路で Python の `hash()` を使わない(起動ごとに塩が変わる)。
   識別子から乱数種を作るときは `zlib.crc32` を使う。検証は
   `PYTHONHASHSEED` を変えた 2 回の生成の diff で行う。
2. **「読み取れる」形(dbgread 等)の正解は、出力に実際に現れる事実に限る**。
   設定値が正しくても、その値が出力に現れない盤面では正解にできない。
3. **観測表の行は「観測できる状況」でのみ出す**: 昇格行は priv1 でログインできた
   利用者のみ・ログイン不可/priv15 の利用者の昇格行は出さない(行ごと省く)。
4. **仕様書と show の認識論**: サーバ仕様書は**意図(申告値)**であり、`show`/`debug` は**事実**。
   サーバ側故障(user_not_registered 等)では仕様書と観測が食い違うが、それは
   TS の標準的な前提(文書より実機)として成立させる。問題文に注記は入れない。
5. **錯乱肢の理由文(解説)も機械導出する**。手書きの一律文は「症状は直るが要件に反する」
   候補を誤説明する。

### P1b への申し送り

- `fix` は **CLI の状態収束形**で出す(BL-095 の教訓)。AAA は `no` の構文が素直でないものがある
  (`no ip radius source-interface` 単独は `% Incomplete command.`)。
- `patch`(= `no_lockout` 世界)は **順序**が正解になる唯一の形。
  「先に local 管理者を作ってから default を切り替える」等を候補にする。
- `src_iface_group_level` と `cmd_acct_on_radius` は **「やっても直らない/要件を満たさない」錯乱肢**として投入。

## 9. 拡張(BL-103・2026-08-08 ユーザ指示の優先順)

ユーザ指定の順序で **1件ずつ実装・検証**する。以下が正準の順序表。

| # | 項目 | 実測要否 | 状態 |
|---|---|---|---|
| ① | **dbgconf 形**(debug の逆問題) | 不要 | **完了** |
| ② | **コンソール認可**(`aaa authorization console`) | 済(X5/X6/X11/X12) | **完了** |
| ③ | **`if-authenticated`** | 済(X1/X2/X2b) | **完了** |
| ④ | **ACL による RADIUS 遮断** | 済(X4/X4b) | **完了** |
| ⑤ | **vty 範囲違い**(`0 4` と `5 15` で方式リストが違う) | 不要 | **完了** |
| ⑥ | **authread 形**(enable 認証の方式リスト遍歴を読ませる・ユーザ提示題材と同型) | 済(X7〜X12) | **完了**(複数選択= BL-082 も実装) |

### 統合実測(2026-08-08)の結論 — 実測表 [poc/aaa/README.md](../../poc/aaa/README.md) §14〜§18

②〜④＋⑥の裏取りを 1 セッションで実施([poc/aaa/ext_probe.py](../../poc/aaa/ext_probe.py))。
確定した事実と、それが作問に与える制約は以下。

- **②確定**= コンソールの認可は `aaa authorization console` が無ければ**実行されない**
  (X5=入れる / X6=入れない。差はこのグローバル 1 行だけ)。
  → 故障種 `authz_console_disabled` が作れる(構成は正しく見えるのに有効化だけ無い)。
  → **`aaa_model.py` はコンソールにも認可を無条件適用しており実機とずれている**。
    現行出力に誤りは無い(該当盤面 0/1600)が、②の実装前にモデルを直す必要がある。
- **③確定**= `if-authenticated` は exec を許すが**属性を与えない**。
  グループが応答する限り `local` と見分けがつかず、**全断でフォールバックしたときだけ**
  priv が 1 に留まる(`local` なら `username ... privilege 15` が適用され 15)。
  → `no_authz_exec`(常に priv 1)との判別は**平常時の priv** でしか付かない。
    観測表が「平常時」「全断時」の 2 条件を持つ設計がそのまま効く。
- **④確定**= ACL で落としても `test aaa` の文言・秒数・`show aaa servers` の DEAD 表示は
  サーバ停止と**完全に同一**。決め手は `show ip access-lists` のカウンタのみ。
  out 方向(要求を落とす)と in 方向(応答だけを落とす)も機器側では同じに見える。
  → evidence 形に**第3の正解クラス**が入り、「debug が一番情報量が多い」で 5 割取れる
    現状(debug 50.7% / 構成 49.3%)が崩れる。
- **⑥確定(最重要の制約)**= **方式リストの遍歴(`Method=` / `status=`)が debug に出るのは
  `service=ENABLE` だけ**。ログイン認証は SSH でもコンソールでも
  `Pick method list 'default'` の 1 行しか出ない。
  → **authread 形は enable 認証で作る**。ユーザ提示題材が `Router>enable` から始まるのも同じ理由。
  → 読み取れる語彙= `using "default" list`(方式リストが効いている) /
    `non-console enable - default to enable password`(構成されていない) /
    `Method=<G> (radius)` / `status = ERROR`(応答なし→次へ) / `status = FAIL`(拒否→終了) /
    `Restart`(次メソッドへの移行) / `password incorrect` /
    `console enable - ...` と `non-console enable - ...`(回線種別)。

実測は [poc/aaa/ext_probe.py](../../poc/aaa/ext_probe.py)(X1〜X6)。結果は
`poc/aaa/results-ext.md` へ書き出し、README §14 以降に確定知見として畳む。

### ① dbgconf — 完了(2026-08-08)

**形**: `debug radius authentication` の出力だけを見せ、**それを生じさせる構成**を
4つの構成抜粋から選ばせる。既存 `dbgread`(出力から値を1つ読む)の逆で、
**出力全体と構成の対応**を取らせる。

**実装の要点**:

- `debug_block()` を `debug_render(d, dev, srv, site)` に分離した。**dev の純関数**に
  なったので、候補構成それぞれから debug を描き直せる。被覆エンジン方式の debug 版。
- 選択肢は `transport_cfg()` = **debug が明かす範囲の構成だけ**を描く
  (方式リスト・line・鍵の値は debug から読めないので全候補で同一にする)。
  読めない値を動かした候補は**解答者が反証できない**ため、軸から外している。
- 候補の軸= 送信元指定の有無 / timeout / retransmit / RAD1・RAD2 のポート /
  RAD2 のアドレス / **グループ内のサーバ順序**。描き直して出力が変わらないものは自動的に落ちる
  (例: 1台目が即応答する盤面では retransmit を変えても出力が同じ→使わない)。
- ★**仕様表照合の抜け道を塞いだ**。ポート/アドレスを動かした候補だけで選択肢を埋めると
  「**サーバ仕様表と一致する構成を選ぶ**」だけで解けてしまう。しかし
  *構成が仕様表と食い違うこと自体が `port_mismatch` の正体*なので、その照合は
  本来この設問の根拠にならない。→ 仕様食い違い型の錯乱肢は **1本まで**に制限。
  検証: この抜け道で正解できる盤面 **0/1000**。
- ★**BL-088 との衝突(3例目)**= 選択肢が構成そのものなので、設問文を汎用文
  「次のうち、正しいものは、どれですか」に均すと**「要件に適合する構成はどれか」という
  別の設問に化ける**。→ `keep_ask` の対象に追加(evidence / patch に続く)。
- ★**解説の機械導出で踏んだ罠**= 差分行として候補側の行だけを引用すると、
  再送回数のような**出現回数の違い**では「示された出力にも在る行」を根拠に挙げてしまい
  解説が意味を成さない。→ **同じ位置の両者の行を並べて**示す形に変更。

**検証**: 選択肢テキストを構成へ**読み戻して**独立に debug を描き直し、
「出力を再現する選択肢がちょうど1つ・かつそれが正解」を **1200 盤面で 0 違反**。
E2E 60 問(構成非提示・設問保全・選択肢4本・漏えい0)、決定性(PYTHONHASHSEED 1 vs 999 で全文一致)、
全 shape + mixed 回帰 OK。出題形は **8種**になった(read/cause/trace/evidence/dbgread/**dbgconf**/fix/patch)。

**併せて修正**: 解答の「最重要知見」欄が **「鍵不一致と送信元誤りを区別できるのはサーバ側の記録だけ」**
と書いたままだった(追試2 §13 で **debug で切り分けられる**と確定済み)。
`test aaa` / `show aaa servers` では区別できないが `debug radius authentication` では区別できる、
という現在の事実に書き換えた。


### ② コンソール認可 — 完了(2026-08-08)

**実測**: X5/X6 で「グローバルの `aaa authorization console` が無ければ `line con 0` の
`authorization exec` は実行されない」を確定。さらに **X11/X12(追試4 `console_raw.py`)** で
**そのときの権限レベルは 1** と確定した(RADIUS の AVPair `priv-lvl=15` も
`username ... privilege 15` も適用されない)。既存のコンソール測定は pyATS の自動 enable 昇格で
priv が汚染されていたため、CML 端末サーバへ直接 SSH して**素のコンソール**で測り直した。

**★これは既存出力の誤りでもあった**: 生成器は `aaa authorization console` を描いていないのに
観測表のコンソール行を priv 15 としており、**提示した構成では提示した表を再現できない**状態だった。
生成済み 22 件が該当(うち read 形は正解の表そのものが実機と食い違う)。

**実装**:

- `aaa_model.py`= `dev["authz_console"]` を追加。`line == "con"` かつ未設定なら
  **認可を実行せず priv 1** を返す。selftest に X5/X6/X11a/X11c/X12a/X12b を追加。
- `gen_paper_aaa.py`= 健全な盤面は `aaa authorization console` を持つ(持たないと
  要件「コンソールから操作できること」を満たせない)。config 抜粋にもこの行を描画。
- **新しい故障種 `authz_console_missing`**(10→11 種)= グローバルの有効化だけが無い。
  症状は**故障拠点のコンソールだけ priv 1**。構成は一見正しく見える(回線には
  `authorization exec` が書かれている)ので、**グローバル 1 行の有無を見に行けるか**が問われる。
- fix 候補 `enable_authz_console` を追加。ただし**この故障を直す候補は1本しかない**ため、
  被覆エンジンの条件(直る候補≥2)を満たさず **fix 形からは除外**される
  (`user_not_registered` / `console_forgotten` と同じ扱い)。

**検証**: `aaa_model` selftest OK / 家族 selftest **2520/2520**・
**区別不能ペアは実測どおり2組のまま**(新故障種は独自の指紋を持つ)/
E2E 70 問で「コンソール行が priv 15 なのにグローバル行が無い」不整合 **0 件**・
新故障種は必ず priv 1 の行を持つ/決定性 OK(PYTHONHASHSEED 1 vs 999)/
全 10 shape ＋ mixed 回帰 OK。


### ③ `if-authenticated` — 完了(2026-08-08)

**実測(X1/X2/X2b)**: グループが応答する限り `local` と見分けがつかない(AVPair の priv がそのまま乗る)。
**全断でフォールバックしたときだけ** priv 1 に留まる(`local` なら `username ... privilege 15` が適用され 15)。

**実装**:

- `aaa_model.py`= メソッド `if-authenticated` を追加。認証済みなら必ず通り、
  **属性を返さない**(`val=None`)ので呼び出し側で priv 1 になる。selftest に X1/X2/X2b を追加。
- **新しい故障種 `authz_if_authenticated`**(11→12 種)= 認可の代替手段が `local` でなく
  `if-authenticated`。`no_authz_exec`(常に priv 1)との判別は**サーバが応答するときの priv**でしか付かない。

**★併せて直した構造的な欠陥 — 観測が平常時しか無かった**:

フォールバック側の故障は平常時の観測に一切現れない。実際 `authz_no_fallback` は
**60/60 の盤面で健全と同じ表**になっており、「一部の利用者が操作できない」という
**設問文と観測が矛盾**していた(この故障種は `NEEDS_OUTAGE` で SRV01 だけを止めていたが、
SRV02 が応答するので症状が出ない)。

→ 観測に **「認証サーバがすべて停止した場合」の表を常設**した(`outage_table()` / `render_obs()`)。
全故障種で一律に出すので、この表の有無が道標にならない。
載せるのは全断でも認証が通りうる利用者(緊急用ローカル・自動化)とコンソールに限る
(RADIUS 台帳のみの利用者はどの故障種でもログイン不可になり識別に寄与しない)。

効果:

- **12 故障種すべてが観測に症状を出すようになった**(症状なしの盤面 0/60)。
- `authz_no_fallback`(全断で **SUZUKI 含め exec 拒否** = 実運用の締め出し事故)と
  `authz_if_authenticated`(全断で **priv 1**)がここで初めて区別できる。
- ★**fix 形の要件文とモデルの合格条件の乖離**(以前から未解決だった項目)も実質的に解消。
  `fix_works()` は「平常時と全断時の両方で健全と一致」を要求しているが、
  従来は全断時の観測が**解答者に見えていなかった**ため問題が不完全だった。

**検証**: `aaa_model` selftest OK / 家族 selftest **2760/2760**・区別不能ペアは実測どおり2組のまま /
E2E 80 問(8形式・12故障種・全断観測の常設・**観測に異常が1つも無い問題 0 件**・漏えい0) /
決定性 OK / 全 10 shape ＋ mixed 回帰 OK。


### ④ ACL による RADIUS 遮断 — 完了(2026-08-08)

**実装**:

- `aaa_model.py`= `dev["acl_block"]`(`"out"` / `"in"`)。立っていれば全サーバが到達不能になり、
  理由は `acl_out` / `acl_in`。判定順は ACL が最優先(要求が出て行かない/応答が返らないため)。
- **新しい故障種 2 つ**(12→14 種)= `acl_block_request`(要求を落とす)と
  `acl_block_reply`(応答だけを落とす)。
- 描画= `acl_lines()`(構成に載る ACL 定義)/ `acl_iface_block()`(適用行)/
  `acl_block()`(`show ip access-lists` の出力。カウンタは `retransmit + 1`)。
  遮断していない機器では**何も出さない**(実機どおり・説明文は書かない)。
- 観測カタログ `OBSERVATIONS` に `show ip access-lists` を追加。

**★evidence 形の偏りが解消**: 導入直後は正解が **debug 71.4% / 構成 28.6%** と、
かえって debug に偏った。原因は**対立仮説を KINDS の並び順で先頭 2 つ取っていた**ことで、
「同じ観測でしか割れない組」(ACL の要求遮断/応答遮断)が同じ盤面に揃わなかった。
→ 盤面から導いた**決定的な乱数**(crc32 由来。選択肢生成と設問文で同じ順になる必要がある)で
対立仮説を並べ替えた。結果= **debug 44.3% / 構成 28.6% / ACL 27.1%** の 3 クラスになり、
「debug が一番情報量が多い」で取れる率が 71% → 44% に落ちた。

**区別不能ペアが 2 組 → 7 組に増えた**(これは正しい)。
`key_mismatch` / `src_iface_missing` / `acl_block_request` / `acl_block_reply` の 4 つは
**機器側の観測(結果表・`test aaa`・`show aaa servers`)では相互に区別できない**。
debug は前 2 つを割れるが ACL の 2 つは割れず、`show ip access-lists` だけが割れる。

**★併せて直した描画の不具合(全 shape に効く)**: `_fenced_blocks()` が
**表以外の行から空行をすべて捨てて**いたため、「表 → 見出し行 → 表」が 1 つの塊に潰れ、
**2 つ目の表が表として描画されない**状態だった(全断の観測表を足して発覚)。
前後の空行だけを落とし内部の空行は残すよう修正。

**★併せて直した既存バグ(v6redist・BL-098)**: `build_choices_fix()` が
**集合をそのままたどって**候補を間引いており、文字列の hash に PYTHONHASHSEED が効くため
**同じ seed でも選択肢が変わる**非決定性があった。安定順の `keys` 側をたどるよう修正。
mixed の決定性検査で検出(aaa 単体の検査では出なかった)。

**検証**: `aaa_model` selftest OK / 家族 selftest **3240/3240** /
E2E 90 問(14 故障種・8 形式・ACL 盤面は構成に ACL 定義と適用行が載る・evidence は構成非提示・漏えい0) /
表描画の不整合 **0 件**(全 shape) / 決定性 OK(aaa / v6redist / **mixed 25 問**) /
全 10 shape ＋ mixed 回帰 OK / v6redist selftest OK。


### ⑤ vty 範囲違い — 完了(2026-08-08)

**実装**:

- `aaa_model.py`= 回線に `vty_hi`(= `line vty 5 15`)を追加。`resolve_list()` は
  回線キーで引くだけなので変更不要。
- **新しい故障種 `vty_range_partial`**(14→15 種)= 名前付きリストを作ったが
  **`line vty 0 4` にしか当てていない**。`5 15` は既定リストに従うため、
  **6 セッション目以降だけ認証経路が変わる**。
- `line_vty_block()` は **2 レンジとも常に描く**(片方だけ出すとその有無が道標になる)。
  patch 形の構成表示も同じ形に揃えた。
- 観測に `<管理者>(6 セッション目以降)` の行を**全故障種で一律に**追加。
- fix 候補 `apply_list_all_vty`(`line vty 0 15` に適用)を追加。
  直る候補は `apply_list_all_vty` と `default_to_group` の 2 つで、
  `default_frozen` 世界が後者を落として正解を一意にする(被覆エンジンが素直に効く)。

**★併せて直した設計上の欠陥 — 提示と判定で観測の定義が別々だった**:

`fix_works()` が見る観測(`_obs_sig`)は手書きの別実装で、新しい行(6 セッション目・
全断)が入っていなかった。そのため **`vty_range_partial` が判定側から見えず、
19 候補すべてが「直る」と判定**されていた(`authz_no_fallback` でも同じ事故を起こしている)。

→ **1 拠点ぶんの観測を `site_rows()` に集約**し、紙面の表も `_obs_sig` も
**同じ関数から出す**ようにした。これで「提示された観測に現れない故障を、
判定側だけが知っている」という状態が構造的に起こらない。
副作用として判定が厳しくなり、これまで通っていた見かけだけの是正候補が落ちるようになった。

**検証**: `aaa_model` selftest OK / 家族 selftest **3480/3480** /
`vty_range_partial` の fix= 直る候補 2・要件適合 1 /
E2E 90 問(15 故障種・`line vty 5 15` の描画・6 セッション目の観測・漏えい0)で NG 0 /
決定性 OK(aaa / mixed) / 全 10 shape ＋ mixed 回帰 OK。


### ⑥ authread — 完了(2026-08-09)

**形**: `debug aaa authentication` の **enable 認証**の遍歴(`Method=` → `status = PASS|FAIL|ERROR`)
を読ませる。このリポで初の**複数選択(2つを選択)**。

**実装**:

- `aaa_model.py`= 遍歴を返す `walk_methods()` を追加し、`run_methods()` を**その薄いラッパ**にした。
  ⑤で立てた「提示と判定は同じ関数から出す」原則を最初から適用している。
- `gen_paper_aaa.py`= `enable_walk` / `enable_debug_block` / `enable_cfg_block` /
  `authread_facts`(11 文の真偽をすべて遍歴から機械導出) / `build_choices_authread`。
- 複数選択の器(BL-082)= 正解表記 `**B・C**` / `rebalance_position` は複数正解でスキップ /
  `gen_pack.py` の `choice_of` と `key_of` を複数記号対応(`BD` / `B,D` / `B・D` / `B と D`)。

**★多エージェント監査で見つかった欠陥(すべて修正済み)**:

このリポで初めて、実装後に **4 観点 × 独立エージェント**で監査し、各指摘を別のエージェントが
**反証にかけて再現できたものだけ**採用する形を採った。機械検証(独立再導出)は通っていたのに、
以下が残っていた。

1. **正解が 3 本になる盤面**(一意性の破綻)= 「method2 は試行されていない。」の述語を
   `has_list and second is None` としていたが、**方式リストが無い盤面でも真**。
   → `second is None` に修正。
2. **実機が出さない占位文字列** `(user='<利用者>')` を出力ブロックに書いていた
   → 実際の利用者名に。**規約「出力ブロックには実機が出す文字列以外を入れない」の再違反**。
3. **`port='con 0'` は捏造**(実測は コンソール= `tty0` / SSH= `tty3`) → 実測値に。
4. **2 本目の `Method=` 行の facility が実測と非対称**
   (グループ側は `AAA/AUTHEN (id):`、ENABLE 側は `AAA/AUTHEN/CONT (id):`) → 実測どおりに。
5. **トランザクション ID が +1 の連番**(実測は無関係な値) → 盤面から crc32 で導出。
6. **未実測の組合せ「コンソール × 方式リスト有り」**を描いていた
   → コンソールは方式リスト無しの枝に限定。
7. **軸ラベルが違うだけで恒等的に同値な文**が同居し消去法で解けた
   (「method1 は enable パスワード」≡「方式リストが構成されていない」) → 同一軸に統合。
   修正後、軸をまたぐ恒等同値は **0 組**(2160 観測 × 11 文で全ペア走査)。
8. **正解 2 本が回線軸＋結果軸だけ**になり遍歴を読まずに解ける盤面があった
   → **正解の 1 本は必ず遍歴の軸**(m1/m2/list)から採る。
9. `show running-config | section aaa` を名乗りながら `radius-server ...` 等
   section に入らない行を出していた → aaa の塊だけに。
10. **問題パックの採点系が複数選択を扱えず無言で採点不能**だった → `choice_of`/`key_of` を対応。
11. `rebalance_position` が複数正解の解答ファイルを読めず、直後の単一正解問題で
    3 連続防止が効かなくなっていた → 正規表現を複数記号対応に。
12. **authread の selftest が無かった** → `_authread_selftest()` を追加(一意性・軸の相異・
    遍歴軸の包含・出力に実機以外の文字列が無いこと・未実測の組合せが出ないことを検査)。

**棄却された指摘**: 「仕様表が稼働中なのに `status = ERROR`」は**欠陥ではない**
(稼働中でも鍵不一致・送信元誤り・ACL 遮断で到達不能。このファミリが意図して教えている区別)。

**検証**: `aaa_model` selftest OK / 家族 selftest 3480/3480 ＋ **authread selftest 600/600** /
生成物の debug テキストだけから 11 文の真偽を再導出して正解表と照合 → **不一致 0 件** /
決定性 OK(aaa / mixed) / 全 10 shape ＋ mixed 回帰 OK / パックの `key_of` が全形式で一致 30/30。

## 8. 参照

- 台帳= [BACKLOG.md](../../BACKLOG.md) BL-101(本メモ)・BL-001(ラボ構築問)・BL-100(紙面突合せ台帳)
- 既存実機知見= `topologies/gen_radius_build.py` 冒頭(FreeRADIUS 3.2.5 / Cisco-AVPair /
  **Reject はフォールバックしない** / RT02 の送信元は egress IF)
- 既存問= `problems/GEN-RADIUS-100`(構築・実機済)・`problems/ENCOR-EDGE-HARDEN-01`
- 共通チェックリスト= PAPER-BLUEPRINT-GAP.design.md §5(11 項)


---

## 10. ★P2 実装結果(2026-08-09 完了・出題可)

成果物= [`topologies/gen_aaa_build.py`](../../topologies/gen_aaa_build.py) →
`problems/GEN-AAAGRP-<seed>/`。詳細= [GEN-AAAGRP.design.md](GEN-AAAGRP.design.md) の
「実装結果」節、採点機構の実測= [poc/aaa/README.md](../../poc/aaa/README.md) §19。

**両刀が成立した**: 紙面 `shape=aaa` と同じ 4 ノード盤面・同じ語彙(送信元 / 鍵 /
非標準ポート / フォールバック / 締め出し)を、今度は自分の手で組む側から扱う。

このファミリで新しく確定した実測は 2 つ。どちらも次のラボ(P3 の `gen_aaa_ts.py`)に
そのまま効く。

1. **3 フェーズ挙動採点の作り方**。`grade.yml` は ios を全件集めてから shell を回すので、
   「壊してから見る」はチェックの並びでは作れない。**破壊も観測も 1 本の shell に閉じ込め、
   そこからルータへ実ログインする**(Ubuntu → IOL は素の ssh で通る)。
   採点は最大 10 回再試行されるので、そのスクリプトは trap で自己復旧させ、
   かつ**前回の残り(DEAD 記録)を待ってから**測る。
2. ★**`deadtime` は単独では無効**。`radius-server dead-criteria` を満たして初めて
   サーバが DEAD になり、そこで初めて `deadtime` が効く。
   紙面側の故障種にも `deadtime_only`(書いたのに効かない)を追加できる。→ BL-105。
