# スーパーハードモード コンポーネント（BL-210 / BL-211）

起票 2026-09-21。発端= ユーザの ENARSI 本試験所感（2 回目受験）:
- 長大な ACL（ゲスト NW 用・インターネットに必要な通信だけ permit＋個別 deny の羅列）で、**in 側に udp 53 が無い**。out 側にも別の長大 ACL。
  ちゃんと読めば難しくないが、初見で「うんざり」する。
- 別問題: エントリが非常に多い ACL に「どこに何を挿入すべきか」。**長大 ACL を削除せず、要件どおりの通信ができるよう最小で変更する**。
- IPsec profile 名・isakmp key の名前が大文字小文字入り乱れで打ちづらい（コピペ不可）。

## 1. 枠組み

- **コンポーネント**= 既存のラボ生成器に後付けできる難化部品。生成器は `--hard <comp>[,<comp>]` を受け、共通モジュール
  `topologies/hardmode.py` を呼ぶ。1 問に最大 2 コンポーネント。難易度 = base + 個数（上限 6）。
- 各コンポーネントは seed 決定的に (a) initial cfg への追記 (b) task.md の仕様/遵守事項の追記 (c) grading checks の追記
  (d) solution/fix.json の追記 (e) solution/README への種明かし を返す。
- 生成器側は**接点**を宣言する（例: `HARD_HOOKS = {"edge": {"node": HUB, "iface": "links[0]", "dir": "in",
  "needs": [flows...], "forbid": [flows...]}}`）。needs= その問題の主題プロトコルが通すべきフロー。
- selftest で「コンポーネント × 生成器」の組合せごとに、正解が存在し・既存の一意性/不変条件が保たれることを検査。
- CATALOG の variant 列に `hard:<comp>` を記す。quiz スキルで「スーパーハード」指定時に `--hard` を付ける。

## 2. C1 うんざりACL（acl_wall）— BL-210

### 2.1 盤面
- 40〜80 行の拡張 ACL を接点 IF に適用。in / out / **両方**（本試験形= out 側は正しいが長い＝囮）を抽選。
- 骨格テーマ（抽選）:
  - `guest_internet`: ゲスト NW → インターネットに必要な通信だけ permit（dns/http/https/ntp/…）＋個別 deny（社内網・特定ホスト・特定ポート）＋ `deny ip any any log`
  - `edge_protect`: 外側 IF の in。IKE/IPsec/ICMP/管理/ルーティングを許可し、既知の攻撃元 deny を羅列（DMVPN・BGP 系）
  - `dc_service`: サーバ セグメントの out
- 生成規則: seq 10 刻みだが**所々詰まっている**（隙間なし区間= `ip access-list resequence` が必要な世界を抽選）／
  remark 行（running-config にだけ出る。解答者に remark を読ませる）／似た行を並べる（host が 1 違い・ポート違い・tcp/udp 違い）／
  established／icmp type／deny の羅列／末尾 `deny ip any any log`。
- 使う構文は `acl_model.py` が解釈できる範囲（ip/tcp/udp/icmp/gre/esp/ospf/eigrp・eq/neq/gt/lt/range・established・icmp type・PORT_NAMES）。
  object-group（間接参照）は第 2 弾（パーサ拡張が要る）。

### 2.2 欠陥（1 つ抽選・主題プロトコルに合わせる）
| id | 内容 | 正解の形 |
|---|---|---|
| `missing` | 必要な permit が無い（udp 53 / esp / udp 4500 / tcp 179 / 89 / 88 / udp 123 …） | 適切な seq に 1 行挿入 |
| `wrong_proto` | tcp 53 はあるが udp 53 が無い／`udp eq 500` はあるが esp が無い | 1 行挿入（既存行は残す） |
| `shadowed` | 必要な permit はあるが手前の広い deny に食われる（順序） | **deny より前の seq に挿入**（deny 削除は不可） |
| `wrong_side` | in 側に必要行が無く out 側にはある（方向） | in 側に挿入 |
| `narrow` | `host` が 1 つ違い／サブネットが狭い | 正しい 1 行を追加（誤行は残してよい） |
| `wrong_iface` | 適用点が別 IF | `ip access-group` の付け替え（ACL 本体は不変） |

### 2.3 採点
- `acl_vectors`（acl_model 意味評価）: 必要フロー= permit／**元の deny が全部生きている**／対象外フロー= deny（`permit ip any any` 等の過剰解を排除＝暗黙の最小変更原則）。
- 構造保全（raw）: `show ip access-lists <name>` のエントリ数 ≥ 元の数・canary 行（無害な特定 permit/deny）が contains。
- 最小変更: エントリ数 ≤ 元 + 2。
- 適用点: `show run interface` に `ip access-group <name> <dir>` が元のまま（wrong_iface 以外）。
- 機能: 主題プロトコルの効果（DMVPN= hub 登録・BGP= Established …）は既存 checks が兼ねる。
- 要件文: 「既存のフィルタは、削除または置き換えられてはならない」は**書く**（構造の制約）。「余計に開けるな」は**書かない**
  （暗黙の最小変更原則で担保・selftest で対象外プローブ不変を検査）。

### 2.4 対象生成器と接点
| 生成器 | 接点 IF | 必要フロー | 囮になる行 |
|---|---|---|---|
| gen_dmvpn_wreck / gen_dmvpn_ts | hub 外側 in | udp 500・udp 4500・esp | `permit gre`（protection 下では不要） |
| gen_bgp_ring_ts / bgp 系 | ピア リンク in | tcp 179（eq 179 / established の両向き） | `permit tcp … eq 179` が片向きだけ |
| gen_redist_field 等（OSPF/EIGRP） | ドメイン境界 | 89 → 224.0.0.5/6・unicast／88 → 224.0.0.10 | `permit ospf host A host B` だけ（マルチキャスト無し） |
| gen_dhcp_ts | リレー IF | udp 67/68 | bootps だけ／bootpc だけ |
| gen_fnf_ts / gen_snmpv3_ts / svc 系 | 管理セグメント | udp 2055／161-162／514／123 | tcp 版 |
| gen_aaa_ts | AAA サーバ側 | udp 1812/1813（PORT_NAMES に無い→数値） | 1645/1646 |
| gen_ipsla_ts | 監視 | icmp echo/echo-reply・udp jitter | echo だけ |

### 2.5 PoC 項目
- P1 seq 隙間なし区間への挿入（`resequence` の挙動・カウンタ保持= poc/acl §6 で既知）
- P2 60〜80 行 ACL の day0 投入（CVAC の時間・行数制限）と `show ip access-lists` 表示の acl_model パース（`log` は捨てる実装済）
- P3 remark の見え方（running-config のみ）→ 解答者の読み方
- P4 DMVPN: esp 欠落（今日の F2 で症状は確定= ISAKMP QM_IDLE・encaps/decaps 0）に加え udp 4500 欠落（NAT-T 不使用なら**非故障**= 囮候補）
- P5 object-group 版（第 2 弾）

### 2.6 実装状況（2026-09-21）
- `topologies/hardmode.py`: `edge_wall()`（in 側・edge_protect テーマ・欠陥 4 種= missing/wrong_proto/narrow/shadowed × seq 2 世界= normal/packed × 側 2 世界= in/both）、
  `egress_wall()`（out 側・正しい囮）、`wall_cfg/wall_apply/wall_fix/wall_check/wall_task_row/wall_readme`、selftest（300 seed × 4 × 2:
  欠陥は need_esp だけ落とす／正解挿入で全 PASS／`permit ip any any` の過剰解・anti-spoof より前への挿入・catch-all の削除は落ちる）。
- `acl_model.eval_acl_vectors` に `must_have`（元エントリの意味的生存）・`min_entries`・`max_entries` を追加。
- `gen_dmvpn_wreck.py --hard acl_wall`: FINAL= `f_acl_wall` 固定（他の最後の 1 層は使わない）・壁は別系列の乱数（同 seed の通常版と欠落配置が同じ）・
  難易度 6・配点= hub 登録 20・ESP 7・壁 8・適用 2。
- 欠陥 `wrong_side` は「missing × both」に統合。`wrong_iface` は第 2 弾。
- ★**IOL の罠（E2E で発見）**: Ethernet の out 方向 IP ACL は ARP フレームまで（ずれた offset で）評価し catch-all で落とす → day0 から適用すると ARP 未解決で全断。
  よって **out 側の壁は使わない**。`both` 世界の囮は **全 spoke の外側 in の壁（正しい）** に変更。
- resequence は remark を消し、エントリだけ 10 刻みに振り直す（挿入位置の計算はエントリ位置）。表示のポート名 `msrpc` 等を acl_model に追加。
- E2E 2 周: 40021（wrong_proto・normal）5 → 30 → 100 ／ 50001（missing・packed・both= 全 spoke に囮壁）5 → 30 → resequence+挿入で 100。udp 4500 は NAT 無しでは非故障（Q2b）。

### 2.7 展開（2026-09-21）
- **DHCP TS** `gen_dhcp_ts.py --hard acl_wall`: `hardmode.lan_wall()`（guest_access テーマ・収容 IF in）。ACL 層の故障を壁の欠陥に置き換える（`wall_missing/narrow/shadowed/wrong_proto`）。
  ★本試験形の罠= anti-spoof `deny ip 0.0.0.0 0.255.255.255 any` が DISCOVER を食う → 正解は **anti-spoof より前** に挿入。
  E2E 9101（shadowed）55 → 100。deny カウンタ検査は hygiene 行/catch-all のどちらでも可に。
- **再配送フィールド** `gen_redist_field.py --wall`（chain 固定）: `hardmode.border_wall()`（境界ルータの 1 リンク in・target= `permit ospf|eigrp any any`・
  transit は tcp/udp/icmp だけ＝`permit ip` を書くと 89/88 まで通って欠陥が消える）。shadowed= hello は通るのに unicast が catch-all に落ちる（EXSTART 固着/EIGRP retry）。
  E2E 8801（missing・packed）35 → 50 → 100。reachability 40→32・壁 8。
- **BGP リング**は見送り（理由）: 片方向の tcp 179 permit だけでは接続衝突の解決で必ずどちらかの向きが成立し**単一行の欠陥が故障にならない**。
  両向きとも欠落＝2 行の是正が要る形にするか、`transport connection-mode passive` で向きを固定する必要があり、別設計（BL-210 残）。
- ★**IOS は同一 ACE を 2 つ持てない**（`% Duplicate entry`）: shadowed の正解は「同じ行を前に」ではなく**対向を絞った別の行**（`_cover(peers)`）。
- ★**ノイズの Loopback が EIGRP RID を奪う**（全拠点で同じ IP → RID 重複 → 経路が捨てられる）: 生成器は `eigrp router-id` を明示、ノイズ IP はノードごとに別。

## 3. C2 打ちづらい識別子（hostile_names）— BL-211
- 大文字小文字混在＋紛らわしい字（l/1/I・O/0）＋記号を profile 名・transform-set 名・ACL 名・route-map 名・PSK・NHRP 鍵に。
- IOS は名前を大小区別する → 参照のずれ（`DMVPN-Prof` を参照し `DMVPN-PROF` が定義）が自然な故障になる（gen_dmvpn_ts の i8 の一般化）。
- 既定は打ちやすい名前（大文字英数のみ）。2026-09-21 gen_dmvpn_wreck の PSK を `VPNKEY123` 形に変更済。
- 採点: 仕様書の名前で `show crypto ipsec profile <name>` / `show run | include`。
- **実装（2026-09-21）**: `hardmode.hostile_names()`（大小混在＋ l→1/O→0/S→5 ＋ `-_.#`・NHRP 鍵は 8 字）。`gen_dmvpn_wreck --hard names`。
  仕様書に名前を明記（通常モードも `名前` 行を追加）。Q3= 全部 IOS が受理。大小違いの参照は黙って無視されるので独立の故障種にはしない。

## 4. C3 囮の類似名オブジェクト（decoys）
- 使われていない似た名前のオブジェクト（profile/transform-set/ACL/route-map/prefix-list）を 2〜4 個残し、1 つだけが参照されている。
  BL-162（同名 ACL/prefix-list）・bgp ring の decoys の一般化。
- 採点: 囮は消しても消さなくてもよい（減点なし）。参照が正しいこと。
- **実装（2026-09-21）**: `hardmode.similar_names()`＋`gen_dmvpn_wreck.decoy_lines()`（`--hard decoys`）= 似た名前の profile 2（1 つは mode tunnel+PFS・1 つは本物と等価）・transform-set 1・ACL 1（permit any）。
  仕様の名前チェック（`tunnel protection ipsec profile <本物>` を hub/spoke で contains）で囮への付け替えを落とす。

## 5. C4 無停止制約（no_disruption）
- 「正常な拠点の隣接/セッションを落としてはならない」を **uptime で採点**（`show ip eigrp neighbors` Uptime・`show bgp summary` Up/Down・
  `show dmvpn` UpDn Tm ≥ 提供からの経過時間）。
- Tunnel bounce / `clear crypto session` / `clear ip bgp *` が使えない → 局所的な是正（per-peer clear・`clear ip nhrp <ip>`・soft reconfig）の知識が要る。
- 実装: provision 時刻を `_generated/<id>/` に記録し、grade 時に `show clock` と併用して比較。
- **未着手（2026-09-21）**: 壊滅スタートには「正常な拠点」が無いので対象外。gen_dmvpn_ts（一部 spoke 正常）向けに、provision 時刻の記録と uptime 比較の採点種が要る。

## 6. C5 設定ノイズ（config_noise）
- 無関係な設定 100〜300 行（未使用 VLAN/Loopback/QoS policy/バナー/class-map/未使用 ACL/静的経路）を day0 に足し `show run` を 3 倍にする。
  `| section` `| include` `| begin` の運用技能。囮（C3）と相性がよい。
- 採点: 影響なし（触らなくてよい）。
- **実装（2026-09-21）**: `hardmode.noise_lines(rnd, node_idx)`（`--hard noise`）= LEGACY Loopback 6〜10（192.0.2.x・ノード別）・QoS class/policy-map・Null0 静的 8〜14・
  未使用 ACL/prefix-list/route-map・IP SLA/track・domain list。約 120 行。★RID 事故（§2.7）を踏んだので `eigrp router-id` 明示とセット。

## 7. C6 不正確なチケット（noisy_ticket）
- 申告に 1 点だけ事実と違う記述（報告者の勘違い）を混ぜ、task に「申告は正確とは限らない」と明記。
  一意性: 申告の誤りが盤面から確定できること（未決定にしない）。既存の教訓「症状文も実測対象」の武器化。
- **実装（2026-09-21）**: `gen_dmvpn_wreck.false_memo()`（`--hard ticket`）= 「前任者の引き継ぎメモ」3 項目（真 2＋偽 1）。偽は実際の欠落から作る
  （「支店 X は完了・確認済み」「hub は mGRE 投入済み」「protection 投入済み」）。task に「正確とは限らない」を明記。README に偽の項目と根拠。

## 8. C7 DF 通信（df_traffic）
- VPN 系: 1400B DF の業務通信が通ること（`ping size 1400 df-bit`）。ip mtu / adjust-mss の欠落を故障に
  （TS では外側 GRE の断片化で救済されて不成立＝**構築要件として**成立。gen_dmvpn_ts の知見）。
- **実装（2026-09-21）**: `gen_dmvpn_wreck --hard df`= 1〜2 spoke の `ip mtu 1400`/`ip tcp adjust-mss 1360` 欠落（`s_mtu`・症状なし）＋ Tunnel0 仕様チェックに MTU/MSS の contains を追加
  （df ping は外側断片化で通るので効果採点には使わない＝仕様監査の項目）。

## 9. 段取り（2026-09-21 時点）
1. ✅ `hardmode.py` ＋ C1 を gen_dmvpn_wreck に接続 → PoC → E2E 2 周
2. ✅ C2 / C3
3. ✅ C1 を dhcp / redist field へ展開（bgp ring は見送り・§2.7）
4. ⏸ C4（gen_dmvpn_ts 向け・採点基盤が要る）
5. ✅ C5 / C6 / C7（gen_dmvpn_wreck `--hard all` E2E= 2 → 30 → 100）
6. 残= quiz スキルで「スーパーハード」指定時の `--hard` 付与ルール（CATALOG の記載で運用）
