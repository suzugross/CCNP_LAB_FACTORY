# GEN-IPSLA-TS.design.md — IP SLA/track TS 生成器（BL-134）

2026-08-22 起草。ユーザ指示=「ENARSI では TS 問題として出題される傾向なのでパックにも
含めたいし、様々な壊れ方の TS を行えるようにしておきたい。紙面は一旦置いておき、まずはラボ」。
＋「path-echo が必要なのか icmp-echo に差し替えるべきなのか分からずじまいだった。
そういった細かないやらしさも欲しい」（オペレーション種別の判別を故障レイヤに昇格）。

## 0. 位置づけ

- ENARSI 4.5（IP SLA / Object Tracking・Services 25% の 1/7）。
- 既存資産= ENCOR-IPSLA-01（隣接監視・難4・2026-07-25 消化）/ ENCOR-IPSLA-02
  （奥ビーコン監視・難5・2026-07-16 消化）。**両方とも固定問題で消化済＝再出題価値が枯れている**。
- 生成器化して seed で回す。ID= `GEN-IPSLATS-<seed>`・生成器= `topologies/gen_ipsla_ts.py`。
- 紙面転用（BL-100 第二群の shape=svc 系）は本件のスコープ外。ただし PoC の実測書式は
  紙面転用時にそのまま正典になるので、**return code・show 書式は byte で採取**しておく。

## 1. 盤面（IPSLA-02 流用・4 IOL）

```
RT01 ─10.0.12.0/30─ RT02(primary ISP) ─10.0.24.0/30─ RT04(Internet)
    ╲10.0.13.0/30─ RT03(backup ISP)  ─10.0.34.0/30─┘
                     （RT02↔RT03 inter-ISP 10.0.23.0/30）
RT04: Lo10=8.8.8.8/32(データ・両ISPから到達可) / Lo20=100.64.0.1/32(ビーコン・primary専用)
RT01: Lo0=1.1.1.1(データ送信元)
```

- ISP 側の実証済み設計（ENCOR-IPSLA-02 の initial をそのまま流用）:
  - RT02 は Internet/ビーコンへ **RT04 直結のみ**（奥障害が track に伝わる）。
  - RT03 はビーコンへの経路を持たない（プローブが backup へ逃げない）。
  - RT04 の「プローブ送信元 10.0.12.1 への戻り」は **primary 経由のみ**
    （応答も primary 限定＝対称）。データ送信元 1.1.1.1 への戻りは backup 優先
    ＋AD200 フォールバック（IOL リンクダウン非伝播対策）。
- 健全解（golden）= IPSLA-02 の解: icmp-echo でビーコン監視・source=10.0.12.1・
  ビーコン /32 を primary next-hop に固定・track 1 reachability・
  primary default track 連動＋backup AD200 フローティング。
- seed 抽選軸: アドレス面（10.0.x を含む3オクテット目群）・SLA/track 番号・
  ビーコンアドレス・ホスト名（BL-104 流儀）・primary/backup の IF 入れ替え・故障種。

## 2. 故障カタログ（レイヤ直交・`--faults 2` は別レイヤから）

症状クラス:
- **[固着]** primary 健全なのに backup 経由（track が不当に Down）
- **[不感]** 奥障害でも切り替わらない（サイレント・平常時は健全に見える）
- **[乱]** フラップ・部分断・ECMP 混走

| レイヤ | 故障種(案) | 症状 | 決め手 |
|---|---|---|---|
| sla | `sla_not_scheduled` schedule 未投入 | 固着 | `show ip sla statistics` に試行が出ない |
| sla | `sla_wrong_source` source が backup 側/Lo0 | 固着 | 戻り経路ポリシーで応答が返らない。statistics は Timeout |
| sla | `sla_wrong_target` 監視先がデータ宛(両ISP到達可) | ★機能症状なし(監査形) | ★p10 是正= プローブ送信元への戻りが primary 限定のため、default 追従でも backup で成功できず**フラップは起こらない**。構成監査指摘のチケットで出す |
| sla | `sla_threshold_only` react/threshold だけ設定した残骸 | 不感(効いていない) | threshold は reachability に効かない |
| track | `track_wrong_sla` 存在しない SLA 番号参照 | 固着 or 無条件 | `show track` の対象表示 |
| track | `track_route_mismatch` スタティック側の track 番号不一致 | 不感/無条件 | `show ip route track-table` |
| route | `pin_missing` ビーコン /32 固定漏れ | 乱(フラップ)〜固着 | ※盤面ではビーコン backup 不達なので固着。PoC で確定 |
| route | `pin_wrong_nh` /32 が backup 側 next-hop | 固着 | プローブ恒久失敗 |
| route | `ad_not_floating` backup の AD が primary と同値/小 | 乱(ECMP 混走)/常時 backup | `show ip route 0.0.0.0` |
| optype | `op_pathecho_blocked` icmp-path-echo×経路上 `no ip source-route` | 固着 | ping は通るのに SLA だけ落ちる。§3 |
| optype | `op_udp_no_responder` udp-jitter/udp-echo×responder 無し | 固着 | 同上。return code が異なる |
| optype | `op_tcp_wrong_port` tcp-connect が誰も listen しないポート | 固着 | 同上 |
| 上流 | `acl_probe_block` RT02/RT04 の ACL がプローブだけ遮断 | 固着 | 決め手は上流の ACL カウンタ(acl/aaa の型) |
| sla | ★`sla_life_finite`(PoC 知見5) unschedule→再 schedule 時に life 既定 3600 のまま | 時限で固着 | configuration の `Life (seconds): 3600` |
| sla | ★`sla_schedule_rejected`(PoC 知見8) timeout>frequency で schedule が day0 で落ちる | 固着(未稼働) | running-config に schedule 行が無い+return code Unknown |
| sla | ★`sla_wrong_source_lo`(PoC 知見14+p10) source=Lo0 で非対称往復成功 | ★**誤フェイルオーバ**(p10 是正) | 応答が backup 依存になり、**backup 側奥障害で誤 Down→健全な primary から死んだ backup へ切替→全断**(10.2s・ping 0% 実測)。primary 奥障害は普通に検知する(当初の「不感」予測は誤り) |

★PoC 実測(2026-08-22・poc/ipsla/README.md)による確定:
- `pin_missing` の実症状= **フェイルバック不能ラッチ**(平常時 Up の潜在故障→障害後、
  復旧しても backup 固着。fix 3.7s で復帰)。フラップ形ではない。
- return code 指紋 5種(OK/Timeout/**Unknown=不稼働**/No connection/Socket connect
  error)が診断の決め手として機械採点・解説の両方に使える(README の一覧表)。
- 編集ロックの fix 手順= **unschedule→編集→再 schedule で成立**(delete 必須ではない。
  ただし life が 3600 に戻る=知見5 の故障種と表裏)。

- 「不感」系はそのまま出すと診断の取っ掛かりが無い →
  (a) **事後是正シナリオ**（Cisco語: 「先週の奥障害時に切替が行われず全断した。
  原因を特定し再発しないよう是正せよ」）で出す、
  (b) 採点で**破壊→観測→復旧を1本の shell に閉じ込め**実証する（gen_aaa P2 の型）。
  故障種ごとに (a)(b) を併用。
- 修理の摩擦（いやらしさの通奏低音）= **スケジュール済み SLA は編集ロック**
  （実機挙動を PoC P1 で確定）。fix 手順は「unschedule→編集→再 schedule」または
  「no ip sla N→再作成」で、これを知らないと %エラーで詰まる。

## 3. オペレーション種別層（ユーザ発案の主軸）

核= **データプレーンは健全（ping は通る）のにプローブだけ死ぬ**。「このオペは要件上
必要なのか、icmp-echo に差し替えてよいのか」を要件書が一意に決める。

| 現況 | 壊れ方(★=PoC 実測済) | 要件世界A(到達性のみが根拠) | 要件世界B(計測が監査要件) |
|---|---|---|---|
| path-echo | ★**IOL では何をしても上がらない**(source-route 有効化でも Timeout・per-hop 統計も出ない=PoC 知見10) | **icmp-echo へ差し替えが唯一解** | **廃止**(IOL で成立しないため作らない。実機HWでの挙動未確認と解説に記す) |
| udp-jitter | ★対向に `ip sla responder` 無し= `No connection` | 差し替えが正解 | responder 追加が正解(対向が自社機の変種盤面。responder は1行で PoC 済) |
| tcp-connect | ★listen なしポート= `Socket connect error` | 差し替え or 正ポート | サービス監視が要件なら正ポート修正のみ |

- 診断の決め手= `show ip sla statistics` の **return code の読み分け**(5種の指紋
  一覧を PoC で byte 採取済= poc/ipsla/README.md)。
- ★tcp-connect は既定 timeout 60000ms → frequency と衝突して schedule 拒否になる
  ので、盤面が tcp-connect を使う時は timeout 明示が必須(逆にこれ自体を
  `sla_schedule_rejected` の題材にもできる)。

## 4. 提示・シナリオ

- task.md は Cisco語（恒久規約）。論理構成は提示、故障箇所はヒント無し（hint policy）。
- 要件書形式: 「切替判定は宛先到達性のみを根拠とする」「ホップ毎の遅延計測が監査要件」
  「ISP 機器(RT02/03/04)は変更不可」等の条項で解を一意化。
  未提示前提×消去法の恒久規約（2026-08-12）に沿い、盤面は完備にしない。
- 上流故障種(`acl_probe_block`)のみ「ISP 機器の**閲覧は可・変更は要申請**」等の
  文言で観測経路を開ける（変更不可のままだと fix 不能）。→ fix は「申請」を模して
  該当行の特定を解答させる形か、RT01 側回避策か、PoC 後に決める。

## 5. 採点

- SSH 採点（IOL・4台・mgmt リース 4本）。grade.yml= 設定 regex＋状態＋実疎通。
- フェイルオーバ実証= verify_failover(_deep).yml の型を採点へ内蔵:
  **破壊(奥 or 手前)→track 遷移確認→backup 疎通→復旧→primary 復帰確認**を
  1本の shell タスクに閉じ込める（ios→shell 順序問題の回避・gen_aaa P2 教訓）。
- 収束待ち: track の up/down delay と SLA frequency に依存。PoC で既定値の遷移時間を
  実測し、採点の待ち時間を決める。
- 監査 regex は表示形で書く（実測書式から起こす・恒久教訓）。

## 6. パック合流

1. CATALOG「生成器一覧」に1行（台数=4 を明記・予算計算が拾う）。
2. `gen_pack.py` の `LAB_GENRES` に
   `"ipsla": {"label": "IP SLA/track TS", "prefixes": ["GEN-IPSLATS"], "tags": ["ip-sla", "track"]}`。
3. ジャンル判定= `records/genres.yml` の services に `ip-sla`/`track` タグ登録済み・手当不要。

## 7. PoC 計画（poc/ipsla/・_POC-IPSLA・4 IOL・console 直駆動）

pref/bgpbest の型（virl2_client＋pyats console・mgmt 不使用）。probe.py のチェック:

- **P0 基線**: golden 解投入 → track Up・8.8.8.8 疎通・書式採取
  (`show ip sla configuration/statistics`・`show track`・`show ip route track-table`)。
  奥破壊→切替→復旧のタイミング実測（採点待ち時間の根拠）。
- **P1 編集ロック**: schedule 済み SLA の `ip sla 1` 再入の挙動（%エラー文言）・
  unschedule 手順の要否。
- **P2 未 schedule**: track の状態と statistics の見え方。
- **P3 存在しない SLA 参照**: track の状態（Down か・対象表示）。
- **P4 path-echo**: IOL で icmp-path-echo が動くか。`ip source-route` の既定値。
  経路上 `no ip source-route` で path-echo だけ落ちるか・return code。
  ★不発なら optype 層は udp/tcp 系のみで成立させ、path-echo は紙面転用へ回す。
- **P5 udp-jitter/udp-echo**: responder 無しの return code / 有りで成立。
- **P6 tcp-connect**: 実在ポート(RT04 vty telnet) vs 誤ポートの return code。
- **P7 source 誤り**: backup 側 source での失敗形（P0 盤面の戻り経路ポリシーで実証）。
- **P8 こまごま**: timeout>frequency の受理・threshold の reachability 非関与・
  AD 同値スタティックの RIB（ECMP 2エントリ）。

結果= results-raw.md（生ログ）→ README.md（確定挙動）。

## 8. 未決 → PoC で解決した分(2026-08-22)と残り

★PoC は全探針完了(p0〜p9・poc/ipsla/README.md が正典・盤面ラボ `_POC-IPSLA` は
CML に STOPPED で温存)。

- ~~path-echo 不発時の optype 層の構成~~ → **不発が確定・「差し替え唯一解」形で採用**(§3)。
- ~~`pin_missing` の実症状~~ → **フェイルバック不能ラッチ**(§2)。フラップ形は不要
  (ラッチの方が TS として上質: 「復旧したのに戻らない」)。
- 収束タイミング確定: frequency 10 で track 遷移 7〜11s・fix 後 4s。採点待ち 30s。
- ~~`acl_probe_block` の fix の形~~ → **ACL を RT01(顧客エッジ)側に置く**ことで解決
  (ISP 変更不可の建前と両立・fix は deny 行の撤去)。
- 実装完了(2026-08-22)= `gen_ipsla_ts.py` 故障13種5レイヤ+`--faults 2`。
  「不感系の見せ方」は事後是正チケット+任意の破壊実証
  `playbooks/verify_ipsla_generated.yml`(fault.json 駆動)に確定(採点内破壊は
  Linux ノードが無く exec:shell が使えないため見送り。config 固定判定+効果3種で
  全故障種が判別できることを E2E で確認)。
- ★**実機 E2E 14 サイクル全通過(2026-08-22)**= 全13種 broken 50〜90→fix 後 100、
  複合1本(wrong_source_lo×route_track_missing) 70→100、不感系4種+複合の
  破壊実証 PASS。結果表= poc/ipsla/README.md §E2E。CATALOG/gen_pack 合流済み。

## 9. ★症状文の事後是正(2026-08-22・出題初日にユーザが発見)

- PACK-20260822-D Q1(sla_wrong_target)で、チケットの「フラップ」がユーザの
  破壊実験で再現されず、**症状文が盤面と矛盾**していることが発覚。原因=
  wrong_source_lo / wrong_target の2種だけ症状文を**机上予測**で書いており、
  E2E は「fix で満点」「切替・復帰」だけを見て**症状文と実挙動の一致を検証して
  いなかった**。p10 実測で両種を是正(§2 の表・実測= poc/ipsla/README.md p10)。
- ★恒久教訓= **症状文(チケット)も実測対象**。故障種を追加するときは
  「そのチケットの出来事を実機で再現できること」を PoC/E2E の検証項目に含める。
- 盤面特性の副記録(p10 対照)= backup 側奥障害では golden でもデータが全断する
  (RT04 の Lo0 宛戻りが backup 優先+IOL リンクダウン非伝播で AD200 フォール
  バックが発動しないため)。チケットには使わないこと。
