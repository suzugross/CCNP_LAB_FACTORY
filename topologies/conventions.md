# トポロジ採番・配線規約 (conventions)

問題ごとにトポロジを生成する際の共通ルール。問題はこの規約に沿って
必要なノード/リンクだけを `problem.yml` で宣言する（巨大な常設ラボは作らない）。

## 1. ノード命名とロール
- `RTxx` … **router**（iol-xe / iosv）
- `SWxx` … **switch**（ioll2-xe / iosvl2）
- ロールは**名前の接頭辞**で自動判定（RT→router, SW→switch）。
- イメージは `image_family`（`iol` | `iosv`）で**トポロジ単位に統一**。
  family 内で router/switch は各々のイメージを使う（[[ccnp-image-policy]] の発展）。

## 2. 管理アクセス (MGMT) — 10.1.10.0/26
Ansible 実行ホスト=10.1.10.6、CML=10.1.10.10。各ノードは管理スイッチ→
External Connector(System Bridge) 経由でこのセグメントに載る。

mgmt IP は固定でなく **動的プール**（`target_nodes` 順に割当。group_vars の
`mgmt_pool` = 10.1.10.11-20, .31-.50 の計30個。.21-.29 予約 / .30 GW）。

| ノード | mgmt 物理IF (iol) | 方式 |
|--------|-------------------|------|
| RTxx | Ethernet0/3 (slot3) | VRF MGMT のルーテッドIF |
| SWxx | Ethernet3/3 (slot15) | mgmt VLAN(999) の SVI |

- ルータ: `Gi0/3 or Eth0/3` を VRF MGMT に入れて直接IP。
- スイッチ: L2 のため **VLAN 999(MGMT) の SVI** に IP。物理 mgmt ポートは
  VLAN999 アクセス。管理SWは untagged 単一ブロードキャストドメイン。

## 3. インタフェース割当（slot 採番）
物理IF名 = `prefix + (slot//4) + "/" + (slot%4)`（iol=Ethernet, iosv=GigabitEthernet）。

| ロール | データリンク slot | mgmt slot |
|--------|------------------|-----------|
| router | 0,1,2 (最大3、必要なら拡張) | 3 |
| switch | 0..14 | 15 |

- `problem.yml` の `lab.links` の `a_if/b_if` = **slot 番号**。

## 4. アドレス採番
- **Loopback0**: `RTxx → x.x.x.x/32`（RT01=1.1.1.1, RT02=2.2.2.2, ...）
- **ルータ間 /30**: `10.1.<a><b>.0/30`（例 RT01-RT02 = 10.1.12.0/30、小番号側が .1）
- **クライアント/ユーザ VLAN**: `192.168.<vlan>.0/24`（例 VLAN10 = 192.168.10.0/24）
- **FHRP 仮想IP**: 当該セグメントの `.1`（例 192.168.10.1）

## 5. VLAN 番号
- `999` … MGMT（スイッチ管理 SVI 専用、データには使わない）
- `10,20,30...` … 問題で使うユーザ VLAN
- `1` … 使用しない（既定VLANは触らない）

## 6. 認証・SSH（全ノード共通）
- user `SUZUKI` / pass `CCNP` / enable `CCNP`（Ansible のログイン情報と一致）
- SSH鍵は **EEM applet GEN-SSH-KEY** が起動約30秒後に自動生成。
- baseline テンプレート末尾に `end` を置かない（day0 連結時に以降が無視されるため）。

## 7. Linux サーバノード（ZBX*/SRV*/PC* → role=server, 2026-07-03〜）
- `ZBXxx`=Zabbix監視 / `SRVxx`=汎用 / `PCxx`=クライアント端末（DHCPクライアント等。
  実体は ubuntu＝server と同じ扱い）。ロールは名前接頭辞で自動判定（他と同様）。
- イメージは `node_image_families: {ZBX01: ubuntu}` で**ノード単位指定**（ubuntu-24-04,
  cloud-init）。RAM は `node_ram: {ZBX01: 3072}` で上書き可（既定 2048）。
- **IF/slot**: `ens2`=slot0=**mgmt**（netplan で静的IP・GW 10.1.10.30 経由で apt 可）、
  データリンクは `ens3`(slot1) 以降 → `lab.links` の `a_if/b_if >= 1`。
- **day0**: `roles/baseline/templates/baseline_server.cfg.j2` が user-data と
  network-config を `---CCNP-NETWORK-CONFIG---` 区切りで描画し、gen_cml_lab.py が
  CML の複数 config ファイルに分割。問題固有の構築は `initial/<node>.sh.j2`
  （/opt/ccnp/init.sh として実行）。`initial/<node>.cfg.j2` は**空スタブ必須**。
- **接続**: group_vars/servers.yml（paramiko / become無効）。ログインは共通の
  SUZUKI/CCNP（cloud-init が作成）。
- **監視問題**: problem.yml の `monitoring:` を lab_up.yml→topologies/zbx_setup.py が
  解釈し Zabbix へ SNMPv3 ホスト登録。採点は grading checks の `exec: shell`
  （ZBX ノード上で snmpget / zbx_check.py / ping を実測）。
- **ポーラ用インバンド**: ZBX01-RT01 は `10.99.0.0/30`（.1=RT側, .2=ZBX側）。
  監視対象への経路は init.sh が static route で持つ（監視経路はインバンド
  ＝経路障害も「監視断」としてダッシュボードに現れる設計）。

関連: [[ccnp-phase1-pipeline]] [[ccnp-cml-env]] [[ccnp-zabbix-monitoring-ts]]

## BGP 設定スタイル規約（2026-07-05〜）
新規の BGP を含む問題は **AF方式（MP-BGPスタイル）を標準**とする:
- initial/模範解答とも `no bgp default ipv4-unicast` ＋ `address-family ipv4` 配下に
  activate / network / aggregate / redistribute / neighbor ポリシーを置く
- セッションパラメータ（remote-as / update-source / ebgp-multihop / password）は
  `router bgp` 直下（IOS の正規配置）
- 採点は状態ベースなので受験者の記法自体は縛らないが、task.md に「AF方式が社内標準」と
  明記し、レビューで講評する
- 既存 BGP 問題（ENARSI-BGP-01系ドリル・DMVPN+BGP・gen_bgp_complex_ts.py 等）は
  順次 AF 化（変更時は実機1サイクル検証を必須とする）

## BFD 規約（2026-07-08〜, SPIKE-BFD-01 実機スパイクで確立）
ルーティングプロトコル問題に「BFD 設定」要件を載せる際の標準。**bfd 変種（variant）として
追加**し、既存の検証済ベースライン（base 等）は変更しない。

### タイマ・設定スタイル
- 標準タイマ: `bfd interval 500 min_rx 500 multiplier 3`（対象IFに設定）。
  IOL/IOSv とも echo モード 500ms で安定動作（フラップなし・実機検証済）。
  仮想環境のため 500ms 未満は使わない（タイマ値は params の bfd_interval/bfd_multiplier）。
- プロトコル連動（受験者はどちらの方式でも可・採点は効果ベース）:
  - OSPF: IF `ip ospf bfd` または `router ospf` 配下 `bfd all-interfaces`（相互運用も実証済）
  - EIGRP classic: `router eigrp <AS>` 配下 `bfd all-interfaces` / named: `af-interface <IF>` 配下 `bfd`
  - BGP: `neighbor <ip> fall-over bfd`（直結 eBGP。マルチホップ/Loopbackピアは対象外＝BFD不適）
- IOL は片端 shutdown の link-down が対向へ伝播しないが、**BFD なら ECHO FAILURE で
  約1.5秒検知**し OSPF/EIGRP/BGP を即断できる（フェイルオーバ問題の改善にも利用可）。

### 採点チェック雛形（Genie 実証済・IOL/IOSv 共通）
`show bfd neighbors details` は iosxe パーサで IOL/IOSv とも構造化可。ネイバーIP は
dict キーなので **find はリスト形式**で書く（ドット入りキー対応）:
```yaml
- name: "RTxx: BFD セッション (<peer_ip>) Up・OSPFクライアント登録"
  node: RTxx
  command: "show bfd neighbors details"
  parser: "show bfd neighbors details"
  find: ["our_address", "*", "neighbor_address", "<peer_ip>"]
  match:
    state: "Up"
    registered_protocols.*: "OSPF"     # EIGRP / BGP も同様
    multiplier: 3                       # 乗数は構造化採点可
  points: 5
```
- interval の厳密採点はしない（echo モード時に MinTxInt が 1s へ退避し、echo/制御どちらの
  値かが構成依存のため）。要求値は task.md に明記し、乗数＋セッションUp＋クライアント登録で判定。
- ネガティブ実証済: 片側の連動設定を外すと両側 Down/セッション消滅 → 両側 FAIL（偽陽性なし）。

### 変種の作り方（ENCOR-OSPF-01 がパイロット）
- `params/bfd.yml` = base のコピー ＋ `bfd: true`（＋ bfd_interval/bfd_multiplier）。
- `task.md.j2` に `{% if params.bfd | default(false) %}` で要件を1項追加
  （ヒント控えめ: 対象リンク・タイマ値・「プロトコルと連動」のみ。コマンドは書かない）。
- `grading.yml.j2` は既存チェックの配点を bfd 時のみ圧縮し、BFD チェックを追加して**合計100点を維持**。
- 模範解答は solution.md に BFD 節を追記。実機検証は bfd 変種で1サイクル（base は再検証不要）。

## QoS 効果採点規約（2026-07-09〜, ENCOR-QOS-LLQ-01 で確立）
QoS 問題は「構成（Genie）＋効果（実測）」の2層で採点する。実測は PC*（ubuntu +
iperf3。サーバ側は init.sh で systemd 常駐化）から `exec: shell` チェックで行う。

- **パーサ**: `show policy-map interface` は dev.parse だと rv1 版が選ばれ IOL/IOSv の
  IF 名にマッチしない → grading.yml に `parser: "class:iosxe.show_policy_map.ShowPolicyMapInterface"`
  と書く（grade.py の class: 直指定拡張）。`Priority: N kbps` 行は構造化されないため raw regex で。
- **カウンタ系チェック**は採点器自身のトラフィックで加算される設計にする
  （試行1: ios 収集→shell でトラフィック発生 → 試行2で counter チェック PASS。
  ＝2試行で収束が正常。clear counters 前提の「>0」「==0」型のみ使い、絶対レート判定はしない）。
- **★EF保護は単独で採点しない**: QoS 未設定だと輻輳自体が起きず EF ping が綺麗に
  通ってしまう（実機で 20点 の偽陽性を確認済）。「同一輻輳ウィンドウ内で
  EF 無傷 AND BE 劣化」を1チェックに統合して判定する。
- **体感問の子 class-default は FIFO**（fair-queue を入れると WFQ が BE の小フローも
  救って対比が消える）。閾値は比率で: スループット CIR×0.7〜1.1 / EF avg<60ms /
  BE loss≥20% or avg≥150ms（実測: shape 2M で TCP 1.75-1.82M, EF 0.9-3.8ms, BE 322-334ms/60-75%loss）。
- 輻輳源は `iperf3 -u -b 5M -l 1200 -t 18`（バックグラウンド）× shape 2M。
  複数チェックが連続しても前チェックの残フラッド(数秒)は次の輻輳チェックには無害だが、
  **スループット測定チェックは輻輳チェックより前に置く**こと。
- **★policing の「限定性」は ICMP 巻き添えで検出できない**（POLICE-01 実機教訓:
  class-default 丸ごと police の誤答でも、TCP が輻輳制御で CIR 付近に自制するため
  ping はほぼ無傷 = 90点通過してしまった）。検出は
  ①構造: police クラスの `match.*: {ne: "any"}`（class-default 除外）＋
  ②効果: **UDP（遠慮しないトラフィック）の素通り確認** の2本柱で行う。
- マーキング実績（`QoS Set / dscp X / Packets marked N`）は Genie 非構造化
  → 複数行 raw regex `'dscp ef\s*\n\s*Packets marked [1-9]'` で対採点（CLASS-01 実証）。
  下流伝搬は受け側 RT の観測ポリシー（initial 焼き込み・クラス名固定）のカウンタを
  Genie 構造化採点（match dscp のカウンタ専用 policy はアクション無しで良い）。
