# CAMPUS-TS: 3層キャンパスLAN 障害演習ラボ（超大作・BL-040）

ユーザ提供の指示書（別セッションClaude作・2026-07-10受領, 原本: E:\cml-campus-lan-lab-prompt.md）
を一次ソースとし、本プロジェクトの実績・PoC結果との突き合わせ注記を付けたもの。

---

## A. 受領指示書の要点（原文の構成を保存）

### 目的・成果物 (DoD)
- 受講者は「症状だけ」渡され原因切り分け。運用者は1コマンドでフォールト注入/解除。
- `build.yml` → golden収束 / `inject_fault.yml -e fault=<name>` 注入 / `reset_golden.yml` 解除
- `verify.yml` が正常/異常を判定し落ちたチェックを出力
- README.md + ANSWER_KEY.md + faults/catalog.yml（機械可読の一次ソース）
- 冪等・再実行可能・vault管理

### トポロジ（golden）
```
                 [ WAN/外部 ]
                      |
                   [ asa1 ]  (asav)
                      |  outside:核へ / inside:サーバ網
        core1 ==== core2        (iosv, OSPF area0)
         |  \      /  |
       dist1 ==== dist2         (iosvl2: SVI/HSRP/STP root/OSPF)
        / \        / \
      acc1  \----/  acc2        (iosvl2: 純L2)
       |            |
      cli10        cli30        (ubuntu)
  svr1 (ubuntu) … サーバ網 (DHCP/DNS/Web)
```
- コア間/コア–ディストリ: /30 L3 p2p (OSPF area0)。アクセスは両ディストリへ冗長トランク。
  ディストリ間L2トランク（STP経路兼HSRP同期）。asa1はcore–サーバ網間でステートフル通過。

### VLAN/アドレッシング（例・確定後host_varsへ）
| 用途 | VLAN | サブネット | GW(HSRP VIP) | dist1 | dist2 |
|---|---|---|---|---|---|
| Users-A | 10 | 10.10.10.0/24 | .1 | .2 | .3 |
| Users-B | 20 | 10.10.20.0/24 | .1 | .2 | .3 |
| Guest | 30 | 10.10.30.0/24 | .1 | .2 | .3 |
| IoT | 40 | 10.10.40.0/24 | .1 | .2 | .3 |
| Server | – | 10.20.0.0/24 | asa inside .1 | – | – |
- Lo(RID): core1=1.1.1.1 core2=2.2.2.2 dist1=3.3.3.3 dist2=4.4.4.4 / p2p=10.254.x.x/30

### golden設計ルール（正解状態）
- **STPとHSRPの一致**: VLAN10/30→dist1がSTP root(4096)+HSRP active(110)、VLAN20/40→dist2。
  相手はsecondary root/standby・preempt有効
- OSPF全リンクarea0・p2p・コスト対称。ASAもOSPF参加（or対称スタティック）
- DHCPリレー: 両ディストリSVIに `ip helper-address <svr1>` を両系そろえて
- ASA: inside/outside・ステートフル許可・戻り経路がASAを通るようコスト調整
- MSS/MTU: goldenでは `ip tcp adjust-mss` クランプ済み

### フォールト5種（faults/catalog.yml に symptom/root_cause/where/detect_cmd/fix/grading_check）
| ID | 名称 | 仕込み | 症状の核 |
|----|------|--------|----------|
| F1 | trunk_allowed_mismatch | acc2→distトランクのallowed vlanからVLAN40除外(add忘れ) | VLAN40だけacc2配下でGW不達・acc1側は正常 |
| F2 | ospf_mtu_mismatch | core1–dist1の片側MTU変更 | 当該隣接だけEXSTART/EXCHANGE固着・冗長で何となく動く |
| F3 | dhcp_relay_gap | dist2のSVI30からhelper削除(dist1は有) | HSRPがdist2に振れた瞬間GuestだけAPIPA化 |
| F4 | asa_asymmetric_drop | OSPFコストで往路ASA経由/復路迂回の非対称 | ping/traceroute通るがTCPだけ確立不可(ステートフルdrop) |
| F5 | pmtud_blackhole | 経路MTU縮小+ICMP frag-needed drop+adjust-mss外し | 小さい通信OK・大きいHTTP/転送だけハング |

- フォールトトグルは group_vars の `faults:` 辞書 → Jinja2分岐で壊れたconfigを描画。
  inject=1つtrue+該当ノード再注入 / reset=全false。golden⇔fault往復が冪等。

### スコープ外（README記載要）: デュプレックス不一致/late collision・片方向障害/UDLD・CRC等の物理層エラー（仮想リンクで再現不能）

### 実装順序: 前提確定→雛形→cml_lab(空config疎通)→goldenテンプレ→verify全green→F1..F5を1つずつ(inject→verify→reset)→docs→クリーン環境で全往復

---

## B. 本プロジェクト実績との突き合わせ（§9前提質問への回答・確定済事項）

1. **CML接続**: 10.1.10.10 (2.8.1)・認証=group_vars vault/local.yml・OOB=10.1.10.0/26
   (mgmt_alloc.pyリース制・GW .30・Ansibleホスト .6)。→確定済・質問不要
2. **node_definition実名**: iosv(iosv-159-3-m9) / iosvl2(iosvl2-2020) / asav(asav-9-22-1-1) /
   ubuntu(ubuntu-24-04-20241004) / 補助 unmanaged_switch+external_connector。→全て導入済
   - ★ASAv制約(BL-038 PoC実機確定): day0注入不発→**console bootstrap方式**(asav_bootstrap.py)。
     パスワード8字以上(`CCNPccnp`)・ACLは実IP(8.3+)・SSHは鍵生成+write mem+reload後有効
     (+`HostKeyAlgorithms=+ssh-rsa`)・auto-enableでpriv直行・unlicensed=100Kbps
     (→F5の「大サイズ転送」はスロットル前提で判定サイズ設計要, iperf系は不可)・
     NAT/conn/xlate/ACLはGenie無→raw判定。詳細= poc/asav/README.md
   - ★ASAvのOSPF参加は未検証→Phase 0でプローブ(不可なら対称スタティック代替が指示書にも明記)
3. **IOSvL2のOSPF**: 本リポ未実績→Phase 0でプローブ。不安定なら指示書の代替案
   (コア側スタブ化/p2p network固定)。SVI/HSRP/STP/トランクは実績あり
   (★ブート後mgmt SVI down固着→shut/no shut必須は既知)
4. **機器の管理経路(実績)**: IOSv=SSH不可→console採点(collect_console.py) /
   IOSvL2=SVI bounce後SSH可 / ASAv=bootstrap後SSH可 / ubuntu=SSH。
   指示書の「network_cli前提」はIOSvで成立しない→収集層は既存の混成方式
5. **リソース**: 10 VM(iosv×2+iosvl2×4+asav+ubuntu×3)+unmanaged SW+extconn。
   CML Personal 20ノード上限内・RAM約11GB(50GB中)。→成立。他ラボ全停止が前提
6. **DHCP/DNS/Web**: リポ実績=BIND9+ISC DHCP(組立/TS問)・cloud-init方式確立。
   dnsmasq(1本で完結)への置換も可 →ユーザ選択
7. **症状の与え方/採点**: リポ規約=task.md全文チャット貼付+ヒント控えめ+grade.py100点+
   採点後解法レビュー。指示書のverify.yml(green/red)とどう統合するか→ユーザ選択

## C. 実装方針（2026-07-10 ユーザ確定）

- **Q1 リポ構成 = 既存CCNP01パイプライン統合**: problems/CAMPUS-TS-01 として実装。
  cisco.cml/cisco.ios/cisco.asa コレクションは使わず virl2_client+既存roles+lab.sh。
  build/inject_fault/reset_golden/verify の指示書コマンド体系は lab.sh サブコマンド
  or 専用スクリプトとして被せる（DoD の1コマンド往復は維持）
- **Q2 採点系 = grade.py 100点方式**: 受講者採点は本リポ規約（100点+チェック別内訳+
  採点後解法レビュー）。faults/catalog.yml の grading_check を grade.yml 形式へ展開。
  運用者向け golden 検証（全隣接full/HSRP/STP/DHCP/TCP/大転送）も同 grade 資産で実装
- **Q3 注入方式 = day0差し替え+該当ノードのみ wipe+再起動**: fault トグル→config再生成
  →当該ノードだけ差し替え。ASAv が対象の fault は bootstrap 再投入。往復は冪等
- **Q4 svr1 = BIND9 + ISC DHCP**: 既存 Linux サーバラボ（GEN-DNSTS/DNSDHCP系）の
  実績テンプレを流用。Web は nginx。cloud-init 方式

## D. Phase 0 プローブ結果（2026-07-10 実機・全✅ → golden実装へ）

1. ✅ IOSvL2 OSPF p2p: routed port(`no switchport`)+p2p で FULL 安定（懸念の癖は未発現）
2. ✅ ASAv OSPF 参加: unlicensed でも FULL/BDR・inside網広告・end-to-end 100%
3. ✅ F5 成立: `ip mtu`縮小で DF大パケット落ち+frag-needed(M)。**ingress側**
   `no ip unreachables` で無言ブラックホール化（★IOSはingress IFの設定で抑止判定）
4. F4 は golden トポロジで実施（コスト操作のみ・低リスク・ASAシグネチャはBL-038確立済）
★注入知見: IOSvL2 は物理 `mtu` 拒否 → 仕込みは `ip mtu` で統一（iosv/iosvl2両対応）
全記録= [poc/campus/README.md](../../poc/campus/README.md)

## E. golden 詳細設計（2026-07-10 確定・CAMPUS-TS-01）

### ノード（11 VM + MGMTSW/SRVSW/EXTC = CML 14オブジェクト ≤ 20上限）

cli40 を指示書から追加（F1 の VLAN40 被害者が居ないと症状を体感できないため）。

| node | 種別 | 役割 |
|------|------|------|
| core1/core2 | iosv | OSPF area0 コア |
| dist1/dist2 | iosvl2 | SVI/HSRP/STP root/OSPF(routed port uplink) |
| acc1/acc2 | iosvl2 | 純L2 |
| asa1 | asav | outside=コア側/inside=サーバ網・OSPF参加 |
| svr1 | ubuntu | BIND9+ISC DHCP+nginx (10.20.0.10) |
| cli10/cli30/cli40 | ubuntu | VLAN10@acc1 / VLAN30@acc2 / VLAN40@acc2・DHCP |

### リンク/IF 割当

- core1: Gi0/0=core2(10.254.0.1/30) Gi0/1=dist1(10.254.1.1/30) Gi0/2=dist2(10.254.2.1/30)
  Gi0/3=asa1 outside(10.254.3.1/30・★golden: `ip mtu 1400`+`ip tcp adjust-mss 1360`)
  Gi0/4=MGMT(vrf)
- core2: Gi0/0=core1(.2) Gi0/1=dist1(10.254.4.1/30) Gi0/2=dist2(10.254.5.1/30)
  Gi0/3=**サーバ網バックドア 10.20.0.3/24**(★golden: `ip ospf cost 1000`+passive)
  Gi0/4=MGMT(vrf)
- dist1: Gi0/0=core1(10.254.1.2) Gi0/1=core2(10.254.4.2) ともに routed p2p /
  Gi0/2=dist2トランク / Gi1/0=acc1 / Gi1/1=acc2 / Gi3/3=MGMT(routed port)
- dist2: 対称 (10.254.2.2 / 10.254.5.2)
- acc1: Gi0/0=dist1 Gi0/1=dist2 (トランク) / Gi1/0=cli10(VLAN10) / Gi3/3=MGMT
- acc2: Gi0/0=dist1 Gi0/1=dist2 / Gi1/0=cli30(VLAN30) / Gi1/1=cli40(VLAN40) / Gi3/3=MGMT
- asa1: Mgmt0/0(slot0)=MGMT / Gi0/0(slot1)=outside / Gi0/1(slot2)=inside(10.20.0.1/24)
- サーバ網 10.20.0.0/24 は SRVSW(unmanaged) に asa1-inside / core2-Gi0/3 / svr1-ens3 を収容
- OSPF コストは全 p2p 明示 `ip ospf cost 10`（ASA 側も `ospf cost 10`）

### golden 正解状態（採点＝全green）

- OSPF: core1⇔core2/dist1/dist2/asa1・core2⇔dist1/dist2 全て FULL（7隣接）
- HSRP/STP: VLAN10/30=dist1 active+root(4096)・VLAN20/40=dist2。preempt 有効
- DHCP: cli10/30/40 が svr1 からリース取得（helper=10.20.0.10 両dist×4SVI）
- DNS/HTTP: cli→ svr1 名前解決+`curl http://10.20.0.10/big.bin`(≒100KB) 完走
  （★ASAv unlicensed 100Kbps スロットル→大転送判定は 100KB 級・タイムアウト60s）
- 経路対称: cli→svr は core1→asa1 経由（バックドアはコスト1000で不使用）・復路 svr GW=asa

### F1〜F5 注入設計（全て単一ノードの day0 差し替え）

| F | 対象ノード | golden→fault の差分 | 主症状 |
|---|-----------|---------------------|--------|
| F1 trunk_allowed_mismatch | acc2 | 両アップリンクの `switchport trunk allowed vlan 10,20,30,40`→`10,20,30` | cli40 だけ DHCP/GW 不達・`show int trunk` 差 |
| F2 ospf_mtu_mismatch | core1 | Gi0/1(dist1向け) に `ip mtu 1300` 追加 | core1⇔dist1 のみ EXSTART 固着・冗長で稼働継続 |
| F3 dhcp_relay_gap | dist2 | SVI30 の `ip helper-address` 削除 | VLAN30 が dist2 active 時のみ APIPA 化 |
| F4 asa_asymmetric_drop | core2 | バックドア Gi0/3 `ip ospf cost 1000`→`5` | ping可・TCPだけ不成立(ASA tcp-not-syn drop) |
| F5 pmtud_blackhole | core1 | Gi0/3 の `ip tcp adjust-mss 1360` 削除 + Gi0/1,0/2,0/0 に `no ip unreachables` | 小通信OK・大転送のみハング(frag-needed 無言化) |

注入方式: faults トグル→gen が day0 再生成→**該当ノードのみ** CML config 差し替え
+wipe+再起動（他ノードは無停止）。reset は全 false で同じ経路。

### 実装物

1. `topologies/gen_campus_lab.py`: faults 辞書→ラボ YAML(全day0込み)+_generated 出力。
   ASA config は yaml 内正準（bootstrap が投入）。svr1/cli は cloud-init
2. `problems/CAMPUS-TS-01/`: problem.yml/task.md/grading.yml/catalog.yml/ANSWER_KEY.md/README.md
3. `topologies/campus_ops.py`: build/inject/reset/grade/status/destroy（DoDの1コマンド往復）
4. grading.yml: 19チェック=100点（IOS=collect_console / ASA=pexpect専用収集 / linux=SSH）

## F. 実機検証結果（2026-07-10・全サイクル完走）

**golden 100/100 → F1 91 → F2 80 → F3 95 → F4 79 → F5 92 → reset → 100/100 回帰**。
全フォールトで「カタログ期待チェックだけ落ち、他は green」を達成（副作用ゼロ）。

### 実装中に確定した実機知見（★重要）

1. **IOSvL2 の day0 では `vlan` 定義が VTP server モードだと無言で消える**
   （手動投入は成功するので気づきにくい）→ day0 冒頭に `vtp mode transparent` が必須
2. 生成器の SVI ブロック結合バグに注意: `!` と `interface VlanX` が同一行に融合すると
   コメント化され、後続設定が前の SVI に合流（HSRP 4グループが Vlan10 に集約される
   派手な症状で発覚）
3. **F4 のバックドアは golden で `shutdown` が正解**。connected のまま cost 1000 に
   しても、core2 を transit する通信（例: F2 で dist1 が core2 経由に迂回した時）が
   connected 経路で ASA を短絡してしまい、F2 に非対称の副作用が出る（実測で発覚）。
   F4 注入 = `no shutdown`+`cost 5`（「閉塞予備線の開通ミス」という自然な物語になる）
4. **DHCP リレーは HSRP と無関係**: helper を持つ全 SVI が中継するため、F3 の発症
   条件は「HSRP フェイルオーバー」ではなく「dist1 SVI down（メンテ等）」（実測確認）
5. ASA console 収集は unicon だと `Decode failures exceeded limit`（非UTF8バイト）
   → campus_ops 内の pexpect(codec_errors=replace) 専用収集で対応
6. F4 の ASA 決定的シグネチャ: `show asp drop frame tcp-not-syn`（curl 1回で+7）

### 残作業/メモ

- クリーン環境フル再現（destroy→build→各fault→reset）は未実施。次回出題時の
  provision で自然に検証される（現ラボは全ノードが修正版 day0 で再デプロイ済み）
- BL-039（ASA汎用統合）は campus_ops 内で実質消化。collect_console.py 本体への
  ASA 対応マージは将来の任意課題
