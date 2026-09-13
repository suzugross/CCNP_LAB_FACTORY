# 紙面 Services 即答形ファミリ（shape=svc・BL-170）設計（骨子）

起票 2026-09-13。状態= **完了・出題可（2026-09-13）**。BL-169（MPLS 紙面）の後に着手。
台帳= [BACKLOG.md](../../BACKLOG.md) BL-170。共通原則= [PAPER-3FAM-COPP-DMVPN-PREF.design.md](PAPER-3FAM-COPP-DMVPN-PREF.design.md) §0、
チェックリスト= [PAPER-BLUEPRINT-GAP.design.md](PAPER-BLUEPRINT-GAP.design.md) §5。
実測の正典= [poc/svc-paper/README.md](../../poc/svc-paper/README.md)。

## 11-b. 実装記録（2026-09-13・完了）

- **素材** `topologies/gen_paper_svc.py`（骨子の「小さな真偽関数」＋事実ベース）。kinds 9・形は
  下表（設計 §3 の 9 題材に対応）。`gen_paper_mcq.py --shape svc` に統合（mixed 暫定 3%＝再配送系/mpls から捻出・後日ユーザ再配分）。
  - `ssh`(select/allthat/fix) `snmp`(select/select2/read) `log`(select/allthat/read)
    `ntp`(select/cause) `archive`(select/select2/allthat) `cef`(select/read/match)
    `copy`(select/fix) `dnac`(select/cause) `light`(fix/cause)
  - 数非明示 allthat= ssh/log/archive。組合せ= cef。exhibit を読む分析形= snmp/cef/log(read)・
    ssh/copy/light(fix)・ntp/dnac/light(cause)。
- **PoC** `poc/svc-paper/`（iol-xe ×2＋管理ブリッジで S1〜S11 を実測・撤収済み）。実測を FACTS と
  真偽関数・exhibit に写像。★**「定説と違う」2 点**（`crypto key ... modulus` 2048 下限・
  **hidekeys 既定 ON**）は当初は裏話に限定していたが、ユーザ決定（下記）で出題から除外した。
- **検証**: `selftest` 920 件（9 kind × 形 × 40 seed）NG 0（一意性・決定性・因果なし・数非明示・
  組合せ全単射）。E2E= 7 形の生成・PYTHONHASHSEED 0/999 で byte 一致・パックの解答 UI（ラジオ/
  チェックボックス/組合せ行）と正解キー/組合せキーの読み取りを確認。genres.yml の `services` に `svc` を追加。
- **残**: (a)vty の未定義 access-class の許可/拒否（S2c・paramiko 版で再測予定・正誤には未使用）
  (b)`tftp-server`・`copy ... flash:`・`configure replace <file> force` は harness の console 同期問題で
  未確定（既知 valid コマンドまで同様に失敗＝IOS 非対応ではない・判定に未使用）
  (c)実パックでの初出題と講評（mixed に 3% で混ざる）。
- **深掘り（2026-09-13・poc/svc-paper/README.md「深掘り」節）**= ①鍵長 2048 下限と SSHv1 廃止は**版の仕様**（FN-72511: 17.11.1+ で拒否・RN「SSH Version 1 is not supported」・既定 `ip ssh version 2`/`ip ssh dh min size 2048`・EC 鍵だけでも SSH 可・回避策の shield disable は IOL で保存されず）。②hidekeys は**文書（既定=表示）と実機（既定=伏字）が食い違う**（無垢の対照で logger 自体は既定無効・有効化すると未設定でも `secret *`・`no hidekeys` で 12 種全部平文）。**★ユーザ決定（2026-09-13）= 不確かな問題は捨てる**（公式が誤っている／方針未定／不明瞭の可能性があるもの）。→ hidekeys、鍵長・SSHv1 の数値、「ドメイン名が必須」（label 指定なら不要）、v3 の暗号鍵誤り＝無応答とプロトコル不一致＝Unknown user、timestamps の「未設定でも既定で日時」、DNA Center の警告文（出典未検証）を**出題から除外**（裏話にも出さない・上記 2 案も不採用）。dnac は知識形のみ（cause 形を撤去）。selftest= 880 件 NG 0。
- **初出題（2026-09-13・PACK-TEST-SVC・紙面のみ 13 問＝9 種 7 形）**= 機械採点 8/13、所要 13 問で約 13 分。**出題側の欠陥 1 件**= copy/fix の FTP 枝で設問に「サーバが要求する認証」が無く、認証情報なしの URL（IOS の既定＝匿名 FTP）も成立し得た → Q10 は無効扱い。同じ枝の SCP 側は役割の取り違え（この装置がクライアントなのに ip scp server enable を正解に含めていた）。→ ftp 枝は盤面に「ユーザ/パスワードで認証・匿名拒否・ip ftp username 未構成」を明示、scp 枝は「この装置をサーバにする（aaa new-model 有効）」に改め、正解＝ ip scp server enable ＋ aaa authorization exec（実測 S10-4）。cef/read の各肢の反証も exhibit の flags/Adj source に即した文へ。selftest 880 NG 0 のまま。

## 0. 位置づけ

- 4.0 Services（25%）は、ラボ（SNMPv3/DHCP/IP SLA/NetFlow）と debug 読解（bgpdbg）で「深い」側は埋まっているが、
  **構成 1 画面を見て 60〜90 秒で即答する軽い形**が無い。4.1 機器管理（SSH/scp/tftp）・4.3 ログ/timestamps/条件付き debug・
  4.7 DNA Center は紙面ゼロ。
- 狙いは **BL-145 速筋レーン（時限スプリント）の弾**。難 2〜3・1 問 60〜90 秒。深い形は既存ラボに任せ、本ファミリは
  「既定値の罠」と「1 行の欠落」を主題にする。
- 想定される問われ方: SSH が繋がらない原因／必須構成 3 つ、SNMP の読み書き拒否・v3 のエラー文字列・通知の信頼性、
  ログのレベルと表示の差、タイムスタンプと時刻同期のずれ、archive のパスワード露出、CEF のテーブル、copy の書式、
  DNA Center の時刻ずれ警告、IP SLA の schedule / track 欠落、NetFlow のエクスポータ欠落、DHCP の除外・リース。

## 1. 器

- `gen_paper_mcq.py --shape svc`（紙面専用）。素材= `topologies/gen_paper_svc.py`。モデルは題材ごとの**小さな真偽関数**
  （下記 §4）と事実ベース。作法は copp/pref に揃える。
- `records/genres.yml` の `services` に shape 名 `svc` を追加（集計のため）。種別行= `svc/<kind>`。
- 時限（自動打ち切り）は BL-145 のパック UI 拡張で行い、本ファミリは問題を供給するだけ。

## 2. 知識境界

| 扱う | 裏話のみ | 扱わない |
|---|---|---|
| SSH（domain-name・RSA 鍵長と v2 の 768 ビット条件・`ip ssh version`・`transport input`・vty の ACL/login・`ip ssh time-out/authentication-retries`）、SNMP v2c/v3（community＋ACL・host/traps/informs の違い・v3 の group/user/security level・view）、ログ（レベル 0〜7・console/monitor/buffered/trap の既定・`service timestamps` の datetime/msec/localtime/show-timezone・`logging synchronous`・条件付き debug）、時刻（`ntp server/source/authenticate/trusted-key`・`ntp master` の既定 stratum・`show ntp status/associations`）、archive（path/time-period/write-memory・`log config`/`hidekeys`・`configure replace`/rollback）、CEF（FIB/隣接テーブル・`show ip cef` の receive/attached/glean/drop・process switching への退避）、copy（tftp/ftp/scp の URL 書式・`ip ftp username`・`tftp-server`）、DNA Center assurance（時刻ずれ・アシュアランスが示す典型症状） | SNMPv3 のエンジンID・informs の再送回数・`logging discriminator`・NTP の access-group | SNMP の MIB 設計、syslog サーバ側の実装、TACACS+（BL-101 の後回し分） |

## 3. kinds（題材 9・各 3 形）

| kind | 主題 | 既定値の罠（錯乱肢の種） |
|---|---|---|
| `ssh` | 接続できない原因／必須構成／vty の ACL | v2 には 768 ビット以上の鍵・`transport input ssh` の既定は telnet/ssh 両方ではない機種差・`login local` と `aaa new-model` の関係 |
| `snmp` | 読み書き拒否（community/ACL/RW）・v3 のエラー文字列・trap と inform | 未定義 ACL は全許可（実測済）・`snmp-server host` の既定版は 1・`enable traps` 無指定は全種 |
| `log` | 表示されるメッセージの範囲・宛先ごとのレベル・timestamps の差 | console/monitor/buffered の既定は debugging・trap は informational・`localtime` 無しは UTC |
| `ntp` | 同期しない原因・クロックとログの不一致 | `ntp authenticate` だけでは同期しない（trusted-key 必要）・`ntp master` の既定 stratum 8・source IF |
| `archive` | 変更ログのパスワード露出・自動保存・rollback | `hidekeys` の階層・`configure replace` は archive 無しでも可・`time-period` の単位 |
| `cef` | どのテーブルか・`show ip cef` の各エントリの意味・CEF 無効時の挙動 | FIB と RIB の対応・glean=未解決の隣接・receive=自分宛 |
| `copy` | URL 書式・認証の与え方・ルータの TFTP サーバ化 | `ftp://user:pass@host/path` と `ip ftp username`・`tftp-server flash:` |
| `dnac` | アシュアランスの警告から原因を選ぶ（時刻ずれ・到達性・OSPF Exstart など） | 警告文は DNA Center の英文をそのまま提示 |
| `light` | IP SLA / NetFlow / DHCP の 1 行欠落（schedule・track・exporter 参照・excluded-address・lease） | 既存ラボ生成器の故障カタログから「1 行で直る」ものだけ転用 |

## 4. モデル層（一意性の機械検証）

- 各 kind に**真偽関数**を持つ: 例 `ssh_ready(cfg)`= domain-name ∧ 鍵あり ∧ (v2 なら鍵 ≥ 768) ∧ vty に ssh ∧ 認証手段あり ∧ ACL が発信元を許可。
  `log_shown(level, dest_cfg)`= メッセージ severity ≤ 宛先のレベル。`ntp_synced(cfg)`= server 到達 ∧ (認証なら鍵一致 ∧ trusted)。
  `snmp_access(cfg, mgr, op)`= community 一致 ∧ (ACL 未定義 ∨ ACL が mgr を許可) ∧ (op=write なら RW)。
- fix 形= 候補 CLI を状態に適用して真偽関数が真になる候補が **ちょうど 1**（他は偽か要件違反）。
- cause 形= claim と反証の事実ベース＋排他表（copp 方式）。read 形= 真偽関数の帰結を 1 つ。select/select2/allthat= 事実ベース。
- selftest= kinds×forms× N seed で一意性、byte 決定性、`render_html --selftest`。

## 5. 盤面と exhibit

- 1 台（`Router1`）＋管理端末／サーバの最小構成。図は省略できる（`figure` 無し）。exhibit は `show running-config | section` と
  `show ip ssh` / `show snmp` / `show logging` / `show ntp status` / `show archive` / `show ip cef` の **IOL byte 写し**。
- 値の抽選: ホスト名・アドレス・community 名・鍵長（512/768/1024/2048）・ログレベル・stratum・ACL 番号・URL。

## 6. PoC（`poc/svc-paper/README.md`）

IOL 1 台＋Ubuntu 1 台（syslog/NTP/TFTP/SNMP マネージャ。`poc/zabbix-monitoring` の ZBX01 の cloud-init を流用可）。CML の空きが要る。

| # | 項目 |
|---|---|
| S1 | `crypto key generate rsa` の鍵長と `ip ssh version 2` の受理／拒否（768 未満のとき）・`show ip ssh` の表示 |
| S2 | `transport input` の既定と `login local` 無し vty へ SSH したときの応答 |
| S3 | logging の既定レベル（console/monitor/buffered/trap）と `show logging` の表示・`logging trap` 変更時の差 |
| S4 | `service timestamps log datetime` の各オプションと表示（msec/localtime/show-timezone・`clock timezone`） |
| S5 | `debug condition interface` の効き方（対象外 IF のメッセージが出ないこと） |
| S6 | `ntp authenticate` のみ／trusted-key あり／鍵不一致の `show ntp status`・`associations` |
| S7 | `ntp master` 既定 stratum・`ntp source` の効果 |
| S8 | `archive` `log config` のパスワード露出と `hidekeys`・`configure replace` の前提 |
| S9 | `show ip cef` の receive/attached/glean/drop・`no ip route-cache cef` 後の `show ip cef` |
| S10 | `copy` の URL 書式と失敗時のメッセージ（tftp/ftp/scp）・`tftp-server flash:` |
| S11 | SNMP: community の ACL 未定義＝全許可（再確認）・RO への set の応答・`snmp-server host` の既定版・v3 の `UNKNOWNUSERNAME`/`WRONGDIGEST` の出方（gen_snmpv3_ts の指紋を流用） |

## 7. 段階と工数

| 段 | 内容 | 目安 |
|---|---|---|
| P0 | PoC S1〜S11 | 0.5 日 |
| P1 | ssh / snmp / log / ntp（select/select2/allthat/fix/cause/read）＋ selftest | 1 日 |
| P2 | archive / cef / copy / dnac / light | 1 日 |
| E2E・合流 | パックで試行・mixed 暫定 3%（捻出元は再配送系）・BL-145 の時限 UI と接続 | 0.5 日 |

## 8. リスク

- 知識問は摩耗が早い → 題材 9×3 形×既定値の罠で組合せを稼ぎ、極性反転と数非明示で延命。
- 機種差（IOL と物理 IOS-XE の既定値の違い）→ PoC の実測を正典にし、解説に「IOL 17.15 の既定」と明記。
- 「定説と違う」結論はまず疑う（S3・S6・S9 は既定値の思い込みが混ざりやすい）。

## 9. 参照

- 既存ラボ生成器: `gen_snmpv3_ts.py`（v3 の指紋）・`gen_ipsla_ts.py`・`gen_fnf_ts.py`・`gen_dhcp_ts.py`（`light` の種）
- 手本: `gen_paper_copp.py`・`gen_paper_pref.py`、[PAPER-MPLS.design.md](PAPER-MPLS.design.md)（同日起票の姉妹ファミリ）
- 速筋レーン: BACKLOG BL-145
