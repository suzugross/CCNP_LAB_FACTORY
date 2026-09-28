# PoC: STP (rapid-pvst / MST / bpduguard) — BL-076 準備 (2026-07-29 実施・全項目クリア)

ラボ: `problems/_POC-STP`(ioll2×3 三角形+第2リンク・再利用可)。設計= [STP-SERIES.design.md](../../problems/_drafts/STP-SERIES.design.md)

## 結果サマリ(P1〜P6 全て ✅)

| # | 項目 | 結果 |
|---|------|------|
| P1 | rapid-pvst 動作 | ✅ `protocol rstp`・VLAN 毎 root 分離(sys-id-ext 込み priority 表示: 4096+10=4106) |
| P2 | ブロックポート決定性 | ✅ **priority 明示(4096/8192/既定)だけで机上予測と実機が完全一致**(VLAN10: SW03 Et0/1=Altn BLK / VLAN20: Et0/0=Altn BLK)。MAC 依存の tie-break は排除できる |
| P3 | bpduguard → err-disabled | ✅ boot 時に発火。検出= `show interfaces status err-disabled`(`Et0/2 err-disabled bpduguard`) |
| P4 | MST | ✅ region(name/revision/instance map)・`show spanning-tree mst configuration [digest]`・**不一致時の指紋= 境界ポート `P2p Bound(RSTP)` + `Regional Root this switch`**・是正で Bound 消滅+root 合流(`rem hops 19`) |
| P5 | Genie パーサ適合 | ✅ `show spanning-tree` が両モードでパース成功(rapid= `rapid_pvst.vlans.<id>...` / MST= `mstp.mst_instances.<n>...`) |
| P6 | portfast 構文 | ✅ **旧形 `spanning-tree portfast` のみ**(`edge` キーワードは % Invalid)。bpduguard は `spanning-tree bpduguard enable` |

## ★最重要の運用知見(作問の前提条件)

1. **mgmt VLAN(999) が演習 STP に巻き込まれる**: 各 SW の Et3/3 が MGMT-SW(unmanaged)経由で相互に BPDU を見るため、mgmt セグメントが冗長パスとして STP 計算に参加し、**Et3/3 が Altn BLK になり得る**(実測)。データ trunk が VLAN999 を運ぶ限り、STP 演習の再収束・故障で **mgmt 断が起きる**(モード変更時に実測 30〜60 秒断・自然復旧)。
   **→ 設計規則: 本番問題では全データ trunk に `switchport trunk allowed vlan <データVLANのみ>` を必須化**。999 の代替パスが消えれば MGMT-SW 星形は無ループ→Et3/3 は常時 FWD で完全隔離。
2. **コスト方式がモードで違う**: rapid-pvst= short(Ethernet=100) / MST= long(2000000)。採点 regex・コスト改変系故障の期待値はモード別に。
3. config 投入は collect_telnet では不可(exec プロンプト固定)→ **config モード対応プロンプト regex `SW\d+(\([\w-]+\))?#` の pexpect 直叩き**で安定(本 PoC で確立・生成器の fix 投入経路に流用)。
4. 検証残(作問時に確認): PVST⇄MST 混在の PVST simulation 系の細部(今回はモード遷移の過渡のみ観測)・root guard / loop guard の発火指紋。

## 採点素材(確定した指紋)

- root 確認: `Root ID Priority <4096+vlan>` + `Address`(または Genie の root 構造)
- ロール/状態: Genie `rapid_pvst.vlans.<id>` 配下 / raw `Et0/1 +Altn BLK`
- err-disabled: raw `err-disabled +bpduguard`
- MST 不一致: raw `Bound\(RSTP\)` / 是正後 not_regex + `rem hops`
- region 監査: `show spanning-tree mst configuration` の Name/Revision/instance 行 regex

---

# PoC 第2回: STP P2 の裏どり(BL-216・2026-09-22・ioll2-xe 17.15.1)

照合表 [curriculum/U-A3-stp.sources.md](../../curriculum/U-A3-stp.sources.md) の M1〜M15 を測った。
ツール= [stpcli.py](stpcli.py)(pexpect・手順 YAML)＋[run.yml](run.yml)(vault の認証情報を環境変数で渡す)。
手順= `steps/s1〜s5.yml`・生ログ= `logs/s1〜s5.log`。★最初に全 trunk を `allowed vlan 10,20(,30-37)` に絞った(mgmt 隔離・前回知見 1)。

| # | 論点 | 実測 |
|---|---|---|
| M1 | 既定モード | `no spanning-tree mode` でも running に `spanning-tree mode rapid-pvst` が残る= **既定は Rapid PVST+**(IOS XE の文書と一致) |
| M6 | summary 文言 | `Switch is in rapid-pvst mode` / `Portfast Default is disabled` / `PortFast BPDU Guard Default` / `Portfast BPDU Filter Default` / `Loopguard Default` / `Configured Pathcost method used is short`。`edge` の語は出ない |
| M2 | root primary | 現 root 32768→**24576** / 16384→**12288** / 24576(相手の MAC が小さい)→**20480** / 4096・0→**失敗** `% Failed to make the bridge root for vlan N` `% It may be possible to make the bridge root by setting the priority for some (or all) of these instances to zero.`(0 にはしない)。running には `spanning-tree vlan N priority <値>` の**数値だけ**が残り、後で root が変わっても**追従しない** |
| M3 | root secondary | 常に **28672**。★全員既定(32768)の VLAN で secondary を入れると**その SW が root になる**。現 root が 28672 なら同値で MAC 勝負(今回は root 維持) |
| M20 | priority 不正値 | 5000→ `% Bridge Priority must be in increments of 4096.` と許容値 16 個の一覧 / 65536→ `% Invalid input` |
| M4 | port-priority | **下流で変えても下流の RP は変わらない**(表示だけ `16.3`)/ **上流で 64 にすると下流の RP がそのリンクへ移る**。刻み 16(`% Port Priority in increments of 16 is required`)・256 は Invalid。VLAN 別 `spanning-tree vlan N port-priority` と全体 `spanning-tree port-priority` は併存する |
| — | 自側 cost | 下流で `spanning-tree vlan 20 cost 200` → 下流の RP が別リンクへ移る(cost は自分の RP 選択に効く) |
| M5 | pathcost long | 3 台そろえて `Configured Pathcost method used is long`・Et のコスト **2000000**・Root path cost も 2000000。short に戻すと 100 |
| M9 | root guard | 上位 BPDU で `Desg BKN*… *ROOT_Inc`・inconsistentports `Root Inconsistent`・detail `is broken (Root Inconsistent)`・ログ `%SPANTREE-2-ROOTGUARD_BLOCK: Received a superior STP BPDU from bridge … Root guard blocking port …`。★**ポート上の全 VLAN に効く**(相手が正当に root の VLAN20/36 も Root Inconsistent)。★上位 BPDU は別経路で回り込み、SW01 は結局 SW02 を root と認めた(root guard は「そのポートで」拒否するだけ)。上位 BPDU が止まると約 2 秒で `ROOTGUARD_UNBLOCK` |
| M10 | loop guard | 対向の BPDU を止めて約 5 秒で `Desg BKN*… *LOOP_Inc`・`Loop Inconsistent`・`%SPANTREE-2-LOOPGUARD_BLOCK`。そのポートが Altn/Root の VLAN だけ(Desg の VLAN は無影響)。BPDU 再開で即 `LOOPGUARD_UNBLOCK` |
| M10c | guard の併用 | IF の `spanning-tree guard loop` → `guard root` は**後勝ちで置き換わる**(同時に持てない)。global `loopguard default` があっても IF の `guard root` が効く(detail は `Root guard is enabled`) |
| M8 | bpduguard+bpdufilter 同一ポート | **filter が勝つ**(BPDU sent 0/received 0・err-disable しない)。filter を外すと即 `%SPANTREE-2-BLOCK_BPDUGUARD` `%PM-4-ERR_DISABLE` |
| M12 | errdisable recovery | 既定= 全 cause Disabled・`Timer interval: 300 seconds`。interval 最小 30(29 は Invalid)。★**既に err-disabled のポートは interval を後から縮めても旧 300 秒のタイマのまま**(40 秒後も復旧せず) |
| M7 | global bpdufilter | portfast trunk+global filter: リンクアップ後しばらく `Bpdu filter is enabled by default` のまま BPDU を送る(10 秒で 5 個)。相手から BPDU を受けると filter の表示が消え通常 STP に戻る(送信継続)。**送出数は確定できない**(スイッチ同士では相手が必ず BPDU を出す) |
| M17 | Edge 表示 | portfast(access・trunk とも)のポートは Type 列 `P2p Edge`。global `portfast default` で summary `Portfast Default is enabled`。trunk IF への `spanning-tree portfast` は警告 `will only have effect when the interface is in a non-trunking mode` |
| M11 | UDLD | ioll2 に存在。Et でも `udld port` / `udld port aggressive` で Bidirectional(`show udld` の `Message interval: 7000 ms`・TLV は 15 sec)。★**片方向は再現できず**: 受信側の MAC ACL(0100.0ccc.cccc deny)では UDLD フレームは落ちない(両モードとも Bidirectional のまま)。→ normal/aggressive の片方向時の挙動は**文書ベース**で扱う |
| M14 | pvst⇄rapid 混在 | rapid 側のポートに `P2p Peer(STP)`・detail `Peer is STP`。相手を rapid に戻すと自然に消えるポートと**残るポート**があった。`clear spanning-tree detected-protocols interface X` は**打った側だけ**消える(対向は残る) |
| M15 | MST⇄PVST+ 境界 | PVST 側に VLAN10 root(4096)がいる状態で 1 台を MST 化 → 境界 `Desg BKN*… Bound(PVST) *PVST_Inc`・`PVST Sim. Inconsistent`・`%SPANTREE-2-PVSTSIM_FAIL: Blocking designated port …: Inconsitent superior PVST BPDU received on VLAN …`(原文の綴りのまま)。MST 側の Et コストは 2000000 |
| M13 | RSTP 切替時間 | **自側の shut は 1 秒以内**に Altn→Root FWD。**対向の shut は約 5 秒**(IOL は対向のリンクダウンが伝わらず line protocol up のまま= hello 3 回失効) |

★設計への反映: [STP-P2.design.md](../../problems/_drafts/STP-P2.design.md) §5。

---

# PoC 第3回: 4 台盤面(gen_stp.py 用・BL-076・2026-09-22・ioll2-xe 17.15.1)

ラボ `problems/_POC-STP4`(SW01=DS1 / SW02=DS2 / SW03=AS1 / SW04=AS2・DS 間 2 本・AS は 2 系統・SW03-SW04 に監査ポート)。
手順= `steps/s6〜s9.yml`・ホスト= `steps/hosts4.json`・生ログ= `logs/s6〜s9.log`。day0 で全 trunk `allowed vlan 10,20`＋Et3/3 に `bpdufilter enable`。

| # | 論点 | 実測 |
|---|---|---|
| T1 | 4 台盤面の決定性 | priority(VLAN10: SW01 4096/SW02 8192・VLAN20 逆)だけで **2 VLAN×12 ポートの role/state が stp_model.py の予測と全一致**。Et3/3 は `Bpdu filter is enabled`・`BPDU: sent 0, received 0`・STP 表に出ない(mgmt 隔離成立) |
| T2 | 転送経路の効果採点 | SVI ping 後の `show mac address-table dynamic vlan N` で経路が読める(VLAN10: SW01 が SW03/SW04 の SVI MAC を Et0/2/Et0/3 で学習= SW01 経由)。SVI の MAC は `aabb.cc8X.XX00` 形。初回 ping は ARP で 1 発落ちる(repeat 3 以上) |
| T3 | native 不一致 | **allowed vlan を絞った盤面では `PVID_Inc` もログも出ない**(untagged が VLAN1=非許可で捨てられる)。症状は片側 `Desg BLK` と root port の迂回だけ・ping は通る → **故障として不採用** |
| T4 | allowed の片側欠落 | SW02 Et0/2 から VLAN20 を外す → SW03 の VLAN20 root port が Et0/0(cost 200・SW01 経由)へ移り Et0/1 は `Desg BLK`。疎通は保たれる= **経路の故障(遠回り)として採用可**(U-A1 と複合) |
| T5a | 監査ポート(bpduguard) | SW03 Et0/2(access10+portfast+bpduguard)と SW04 Et0/2(access99=PARK・trunk に載らない)を no shut → **1 秒以内に `err-disabled bpduguard`**・`%SPANTREE-2-BLOCK_BPDUGUARD` |
| T5b | 監査ポート(filter 併用) | 同ポートに bpdufilter を足すと err-disable せず `Bpdu guard is enabled`+`Bpdu filter is enabled`・`sent 0, received 0`。**PARK VLAN で行き止まりなのでループしない**(CPU 0%) → filter_beats_guard の効果採点に使える |
| T5c | 両端 bpduguard | **先に BPDU を受けた側だけ**が落ちる(競合・今回は SW04 側)。→ 監査ポートの対向は要件の対象外にして guard を付けない |
| T6 | loop guard | 対向 SW01 Et0/1 に bpdufilter → SW02 Et0/1 は VLAN10 で `Desg BKN* *LOOP_Inc`(約 5 秒)。**VLAN20 は filter 側(SW01 Et0/1 が Altn だった側)に loop guard が無いので約 30 秒で `Desg FWD`= 実ループ** |
| T6b | 実ループの影響 | IOL では**嵐にならない**(CPU 0%・ping は宛先によって 100% / 0% に割れる= MAC の学習位置が狂う)。mgmt は無事。→ 誤解法(loop guard 撤去)は**構造チェック(期待 Altn が FWD)**で検出する。疎通だけでは決まらない |
| T6c | 復旧 | filter 撤去で即 `Altn BLK` に戻る |
| 注 | baseline への bpdufilter | **全スイッチ問題の baseline には入れない**: データ trunk に VLAN999 を通す既存ラボでは、MGMT ブリッジ経由の VLAN999 ループを作る。STP 盤面の initial に allowed vlan とセットで入れる(BL-135 はこの条件付きで解決) |

---

# 追記: build モード E2E で見つかった IOL 固有挙動(2026-09-22・BL-076・gen_stp.py)

| # | 事象 | 実測 |
|---|---|---|
| B1 | 実行中の pvst→rapid 移行 | 移行後、提案/合意が成立せず `Desg BLK` のまま 15 分以上(`clear spanning-tree detected-protocols` で解ける)・約 40 秒周期のトポロジ変更・**IOL プロセス停止 2 回**(`Segmentation fault(11), Process = VMATM Callback`・crashinfo 出力・CML iol-runner も panic)。起動時から rapid の盤面では起きない |
| B2 | 持ち込み機器の root 情報の固着 | データ VLAN で持ち込み機器(priority 0)が root の状態から一括設定(DS に root guard・AS に bpduguard)すると、AS が `Root ID Priority 1` / `Port 0 ()` を保持し続け DS 側は ROOT_Inc のまま。clear・shut/no shut・priority 再投入では解けず、`no spanning-tree vlan N` → `spanning-tree vlan N` で解消。一括設定で 2/2 再現・手動の単発操作(4 回)では再現せず |
| B3 | 弱い持ち込み機器 | priority 61440 にすると root port 側になり定期 BPDU を出さない → 後から入れた bpduguard は発動しない(RSTP の規定どおり) |
| B4 | ioll2 の EEM | `event manager applet ...` が `% Invalid input`= **ioll2 に EEM は無い**(baseline の SSH 鍵生成 EEM も ioll2 では効かない) |
| B5 | root primary の失敗 | 持ち込み機器が VLAN27 の root(priority 1)の状態で DS に `spanning-tree vlan 27 root primary` → `% Failed to make the bridge root for vlan 27`(M2 と一致) |
| 注 | 出力エラー | IOL は未接続ポートにも output errors / `%AMDP2_FE-6-EXCESSCOLL` を約 30 秒おきに出す。障害の指紋にはならない |

---

# PoC 第4回: MST 世界(L4・BL-076・2026-09-22・ioll2-xe 17.15.1)

ラボ `problems/_POC-STP-MST`(gen_stp の盤面を流用・SW01〜03 を稼働中に MST 化・SW04 は Rapid PVST+ のまま境界)。手順= `steps/s10〜s12.yml`・ホスト= `steps/hosts5.json`・生ログ= `logs/s10〜s12.log`。

| # | 論点 | 実測 |
|---|---|---|
| N0 | 持ち込み機器 | **MST では駐車 VLAN(99)の BPDU も CIST に入り**、priority 0 の持ち込み機器がリージョン全体の CIST root になった(SW03 が CIST regional root)。per-VLAN の隔離は MST では効かない |
| N1 | bpduguard 投入 | 持ち込み機器ポートに bpduguard → 即 err-disabled・CIST root は SW01 にきれいに戻った(B2 の固着は起きず) |
| N2 | PVST シミュレーション | SW04 の VLAN218 だけ 4096 → DS の境界 `Desg BKN* Bound(PVST) *PVST_Inc`・`PVST Sim. Inconsistent`(MST0/1/2 全部)・`%SPANTREE-2-PVSTSIM_FAIL: … Inconsitent superior PVST BPDU received on VLAN 218`。戻すと解消 |
| N3 | PVST 側を全 VLAN 優位 | `spanning-tree vlan 1-4094 priority 4096` でも不整合のまま(VLAN2 以降は sys-id 分だけ VLAN1 より劣位)= 公式「root が PVST 側なら VLAN2 以降は VLAN1 より優位」と一致 |
| N4 | revision 不一致 | SW03 が別リージョン= 上り `Bound(RSTP)`・MSTI の root 側ポートは `Mstr`・SW03 は regional root。**digest は同じ**(VLAN 対応だけを反映) |
| N5 | instance 対応の不一致 | SW02 が別リージョン(`Bound(RSTP)`)・MST2 の root を SW01・SW02 の両方が名乗る |
| — | MSTI の port-priority | `spanning-tree mst 2 port-priority 64` を上流(inst2 root)に → 下流の inst2 の root port がリンク2 へ |
| R | 移行の向き | **rapid→MST は 3/3 安定**。**MST→rapid は Dispute / Desg BLK が出て乱れる**。IOS がモード変更時に `Changing STP mode can disrupt the traffic and make system unstable / Recommend to change STP mode only during maintenance window` を出す |
| — | 旧機側の表示 | SW04(rapid-pvst)の上りは常に `Peer(STP)`(clear でも消えない)。公式に記述が無いので論点・採点に使わない |
| — | allowed の穴(gen_stp E2E で追加測定) | inst1 の転送経路の trunk から VLAN を 1 つ外すと、STP は正常(Root FWD / Altn BLK)のまま、その VLAN だけ 0%= 公式「同じインスタンスの VLAN は一緒に外せ」と一致 |

---

# PoC 第5回: IOL と IOSvL2 の BPDU 欠落比較(BL-219・2026-09-25)

きっかけ= PACK-20260922-Z のラボ採点中、**稼働 2 日の ioll2 ラボで SW01→SW04 の VLAN30 の BPDU だけが落ちた**
(送信 140 / 受信 16・同リンクの他 VLAN は全到達・逆向き正常・送信側 `output errors` が 2 秒に 1 回増加)。
対向ポートが Altn⇄Desg を往復し、採点のたびに 88〜95 点で揺れた。ポート bounce では直らず、ノード再起動で解消。

| 盤面 | 条件 | 結果 |
|---|---|---|
| `_POC-STP4`(ioll2・新規) | 起動直後・5 分測定 | 6 リンク×2 VLAN すべて送受信一致(欠落ゼロ) |
| `_POC-STP-L2V`(IOSvL2・新規) | 起動直後・5 分測定 | 6 リンク×3 VLAN すべて一致(欠落ゼロ) |
| 両方 | ポート上げ下げ+priority 変更 10 周の後・5 分測定 | どちらも一致(`sent=6` の非対称は合意 BPDU で正常) |

→ **新規・中負荷では IOL でも再現しない**。長時間稼働が条件と見られる(次は半日〜1 日放置して再測定)。

測定手順(そのまま実務の切り分けに使える):
```
clear spanning-tree counters [interface X]        ! 両端で
! 20〜300 秒待つ
show spanning-tree interface X detail | include of VLAN|BPDU:    ! 両端で突合
show interfaces X | include packets output|output errors         ! 送信側の落ち方
```
IOSvL2 の注意= 起動後に Vlan999 SVI が down で固着する(コンソールから SVI を shut/no shut で復旧)。
IOSvL2 のポートは Gi(コスト short=4)・IOL は Et(short=100)。役割の期待値は方式を揃えれば同じ。

# PoC 第6回: 3 層盤面の TS 論点とグローバル既定(BL-221 TS / BL-222・2026-09-27・IOSvL2 iosvl2-2020)
盤面= `GEN-STP-94002`(gen_stp.py --world 3tier・build を模範解で設計どおりにした状態)。
設計= VLAN14/147 root SW01・予備 SW02・36864 は SW03 / VLAN32 root SW02・予備 SW01・36864 は SW04 / 持ち込み機器= SW06 Gi1/3。
ログ= 実験スクリプトの出力(セッションの scratchpad・要点はここに転記)。

## G. グローバル既定(BL-222)
- **G1 summary の書式**: 既定は `Portfast Default is disabled` / `Portfast Edge BPDU Guard Default is disabled` /
  `Loopguard Default is disabled`。`portfast edge default` で **`Portfast Default is edge`**、
  `portfast edge bpduguard default` で `... BPDU Guard Default is enabled`、`loopguard default` で `Loopguard Default is enabled`。
- **G2 ポートごとの実効**(`show spanning-tree vlan N detail` / `show spanning-tree detail` / `... interface X detail` 共通):
  明示= **`Loop guard is enabled on the port`**・既定由来= **`Loop guard is enabled by default on the port`**・
  **`Root guard is enabled on the port`**。行は各 ` Port N (IF 名) of VLAN00NN is <役割> <状態>` ブロックの
  `Link type` と `BPDU:` の間に出る → ブロック内に限定した regex で実効を採点できる。
- **G3 優先関係**: `loopguard default` + IF の `spanning-tree guard root` → そのポートは **Root guard の行だけ**
  (loop guard は出ない)・不整合 0。= 「既定で loop guard・下向きだけ root guard を明示」は成立する。
- **G4 BPDU ガード既定**: IF の bpduguard を外し `portfast edge default` + `portfast edge bpduguard default` にして
  持ち込み機器のポートを shut/no shut → **`err-disabled bpduguard` で再び遮断**。
  ★未確認= bounce しない場合(既に BPDU を受けて edge でなくなったポートに既定が効くか)→ E2E で確認する。
- G5 `portfast edge default` は `%Warning: this command enables portfast by default on all interfaces.` を出す(確認プロンプトは無い)。
- 副次: IOSvL2 は**未接続のポートも up 扱い**で `show spanning-tree` に出る(VLAN1 の全ポート・アクセスの未接続エッジは
  `Desg FWD ... P2p Edge`)。採点は期待行の存在で見るので影響しない。

## T. TS 故障の実測(BL-221)
- **T1 コア間の loopguard_trip**(片側に bpdufilter): **両コアとも「自分が root でない VLAN」で孤立**。
  非 root 側コアのコア間ポート= `LOOP_Inc`、さらに下向き 2 本= `ROOT_Inc`(root へ分配経由で届こうとして
  root guard に当たる)→ そのコアは当該 VLAN で `This bridge is the root` を名乗り全ポート BKN。
  bpdufilter は送受とも止めるので**どちら側に付けても対称**(SW01 側・SW02 側とも同じ 3+6 本)。
  外すと自動復旧(不整合 0)。アクセス間の疎通は root 側コア経由で保たれる(症状は不整合の報告だけ)。
- **T2 1 台だけ pathcost short**(SW04): SW04 が `Cost 4` を広告し比較で全勝 → **VLAN32(SW04 が 36864 の VLAN)で
  分配間のブロック側とアクセスの上りが逆転**(アクセスの root cost が 20004 になる)。SW04 は予備コア側の
  リンクでも Desg を取る。指紋= Cost 列の 4 と 20000 の混在。long に戻すと設計どおりに戻る。
- **T3 アクセスに低い priority**: root(24576)より優位な値(4096・20480)→ **分配 2 台のそのアクセス向きポートが
  当該 VLAN で `Root Inconsistent`** → アクセスが孤立(SVI 間 ping 0%)。**28672(予備と同値・root に届かない)
  → 不整合も役割の変化も無し**= 監査(アクセスは priority 既定)でしか分からない「要件違反型」。
