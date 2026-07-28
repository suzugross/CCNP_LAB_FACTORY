# CLAB-HYBRID — containerlab(szk-cl01)×CML 複合ラボ統合設計メモ

- 起点: 2026-07-28 ユーザが 10.1.10.9 に containerlab ホストを新設(vJunos EVO 稼働可)。
  CML⇔containerlab のノード間 L2 接続は確認済との申告。将来このプロジェクトから
  両基盤を制御し複合ラボ問題を出題するための、現地調査結果と必要作業の洗い出し。
- 関連: BL-061(マルチベンダ拡張)。vJunos は CML 内では3段ネストで起動不能(実測済)
  → containerlab 外出しは同 BL の「保留案」だったものが本命化した形。

## 1. 現地調査結果(2026-07-28 実機確認・全て確認済み事実)

### ホスト szk-cl01 (10.1.10.9)
- Ubuntu 24.04.3 LTS / 12 vCPU / RAM 23GiB(+swap 8GiB) / ディスク 73GB(空き49GB)
- VMware VM(MAC 00:50:56)・/dev/kvm あり=ネスト仮想化OK
- ログイン: suzuki / (ユーザ申告のパスワード)。**鍵認証は未設定**(paramikoパスワード接続で調査した)
- containerlab **0.77.0**。バイナリが SUID root(`-rwsr-xr-x /usr/bin/containerlab`)＋
  suzuki は clab_admins/docker グループ → **sudo 無しで deploy/inspect 可能**(自動化に好都合)
- docker 27.5.1。イメージは `vrnetlab/juniper_vjunosevolved:26.2R1.7-EVO`(2.56GB・~/vrnetlab でビルド)

### 稼働中ラボ(参照実装として貴重)
- `~/labs/ospf.clab.yml`: evo1—evo2 直結 + **evo1:eth2 を bridge kind ノード `br-cml` へ接続**
- `br-cml` = Linux ブリッジ。メンバは **ens160(CML方向の専用NIC・IPなし)** と evo1:eth2 の veth
  → これが CML への L2 出口の実装。ens33(10.1.10.9/26) は管理用で別。
- vJunos EVO は healthy 2台稼働中

### 管理アクセス経路(ここが統合の主戦場)
- ノード管理IPは docker ネットワーク `clab` = **172.20.20.0/24**(evo1=.2, evo2=.3)。
  CMLのMGMTプール(10.1.10.0/26)とは完全に別空間で衝突なし。
- ノード側ポート: **22(SSH)/830(NETCONF)/57400(gNMI) 全て開放確認済**
- 認証: **admin / admin@123**(vrnetlab既定。clab生成の ansible-inventory.yml に明記)
- szk-cl01 は `net.ipv4.ip_forward=1` 済＋containerlab が **DOCKER-USER チェーンに
  ACCEPT 2行を自動投入済**("set by containerlab" コメント付き)
  → **制御ホスト(10.1.10.6)に `ip route add 172.20.20.0/24 via 10.1.10.9` を1本足すだけで
  直接 SSH/NETCONF できる見込み**(未実施・要疎通確認)。代替は ProxyJump。
- containerlab はラボごとに `~/labs/clab-<name>/ansible-inventory.yml` を**自動生成**
  (ansible_host/ansible_user/ansible_password 入り) → 本プロジェクトの inventory に取り込める

### リソース実測(最重要制約)
- vJunos EVO 1ノード ≈ **RAM 7.2〜7.4GiB・CPU 0.6コア強**(docker stats 実測)
- 2ノードで 16GiB 消費・swap 2.4GiB 使用中 → **23GiBホストでは実質 2〜3 ノードが上限**
- ノード追加より「CML側に Cisco 多数 + clab側に Junos 1〜2台」の非対称設計が現実的

## 2. 統合に必要な作業(洗い出し・未実施)

| # | 作業 | 規模 | 備考 |
|---|------|------|------|
| A | ~~制御ホスト→172.20.20.0/24 の静的ルート~~ | — | **✅完了(2026-07-28)**: ユーザが netplan `60-clab-route.yaml` 追加・ping/SSH 直達実証済 |
| B | ~~szk-cl01 への鍵認証＋接続情報登録~~ | — | **✅完了(2026-07-28)**: id_ed25519.pub 登録・BatchMode SSH 確認済。接続情報は `group_vars/all/local.yml`(gitignored)の `clab_*` 変数に登録 |
| C | ~~Junos 制御ツール導入~~ | — | **✅完了(2026-07-28)**: .venv に ncclient 0.7.1 + jxmlease。★`junipernetworks.junos` 11.1.1 は **deprecated(2028-04撤去)→後継 `juniper.device` 2.0.2 も導入済み。playbook は juniper.device FQCN を使うこと** |
| D | ~~Junos 採点パス新設~~ | — | **✅完了(2026-07-28 実機100点)**: ①`grade.py` に `parser: json`(stdout を JSON として読み既存 find/match glob 機構で採点) ②`_grade_attempt.yml` に `exec: junos`(ansible.netcommon.cli_command / network_cli 収集) ③`grade.yml` に clab_nodes ホストマップ併合＋junos ノード専用 add_host(vault の IOS 接続変数をホスト変数で上書き)＋指紋照合は対象外化。grading.yml の書き方= `exec: junos` + `command: "show ... \| display json"` + `parser: json` + find/match |
| E | ラボ資材の二枚看板化: 問題生成器が CML yaml と `.clab.yml` を対で出力 → scp して `containerlab deploy -t` を SSH 実行するラッパを lab.sh/ops に追加 | 中 | clab は sudo 不要・startup-config 焼き込み対応(vrnetlab)なので day0 方式を踏襲可。**PoC では既設稼働ラボを再利用したため未実装(次の本実装対象)** |
| F | ~~CML 側トポロジの external connector 生成~~ | — | **✅完了(2026-07-28)**: `gen_cml_lab.py` に `lab.ext_links` 追加(`{node, if, connector, label}`)。**★罠(実証)= connector に書くのは ext-conn の「デバイス名」(bridge1)。ラベル("LAN-IX")だと import は通るが起動時に QUEUED→DEFINED_ON_CORE 無言差し戻し**(既知の invalid image ID と同型)。経路= ext-conn `bridge1`(ラベル LAN-IX・IF ens32) ↔ vSwitch ↔ szk-cl01 ens160 ↔ br-cml |
| G | クロスリンクの多重化設計: 現状はフラット1セグメント。プラットフォーム跨ぎ P2P リンクを複数張るなら VLAN トランク化(ESXi ポートグループ VLAN4095 + vlan-aware bridge or サブブリッジ複数) | 中 | 1本目の複合問は「境界リンク1本」設計にすれば先送り可能 |
| H | ノード認証の規約統一: EVO の startup-config で SUZUKI/CCNP を作りプロジェクト規約(vault)に合わせる | 小 | admin/admin@123 のままでも可だが inventory が二重規約になる |
| I | provision フローの起動待ち: clab の healthy 判定ポーリング＋EVO ブート時間の実測(未計測)を lab_up 相当に組み込む | 小 | |
| J | 出題規約の拡張: CATALOG/history/採点レビューのマルチベンダ問対応、ユーザの解答動線(EVO へは CML コンソールでなく SSH。VSCode ターミナルから直 SSH が自然) | 小 | ユーザは普段 CML コンソール解答([[ccnp-user-solving-via-console]])→Junos は SSH 動線の案内が必要 |

## 3. 推奨着手順(2026-07-28 更新)
1. ~~A+B(到達性と鍵)~~ ✅ / ~~C(ツール)~~ ✅ / ~~D(junos採点パス)~~ ✅ / ~~F(ext-conn生成)~~ ✅
2. ~~最小複合ラボのフルサイクル~~ ✅ → **§5 の PoC 実施結果参照(100/100 収束)**
3. 残= E(.clab.yml 出力+deploy ラッパ=clab側もコード管理する本実装) / G(境界VLAN多重化) /
   H(EVO 認証の規約統一) / I(EVO ブート時間実測・startup-config 焼き込み動作) / J(出題規約拡張)
4. 初弾問題候補: OSPF or eBGP のマルチベンダ interop(難3)。EVO 台数制約(2〜3)に合う
   「CML側が主戦場・Junos は対向/審判役」構成。BL-060 合併シナリオの B社機材役にも合流可能

## 5. PoC 実施結果(2026-07-28・POC-CLABHYB-01・実機フルサイクル済)
- **構成**: RT02—RT01(IOL/CML) —[ext-conn bridge1]—L2—[br-cml]— JUN01(vJunos EVO/clab・既設稼働ノード無改変)。
  全て OSPF area 0。境界 10.0.12.0/30・CML内 10.77.12.0/30・JUN01 lo0 192.168.0.1/24
- **結果**: provision(lab.sh)→境界越し FULL 隣接→採点4チェック→**100/100 収束→teardown 完走**。
  junos JSON チェック(30点)は初回から PASS
- **問題パック**: `problems/POC-CLABHYB-01/`(保持・複合問の雛形。CATALOG には載せない)
- **知見**:
  1. ★ext-conn の configuration は**デバイス名**(bridge1)。ラベルは無言差し戻し(F欄参照)
  2. ★**Junos は lo0 をマスクに関係なく /32 ホストルートで OSPF 広告**(RIB 期待値は
     192.168.0.1/32。Cisco 側の常識で /24 を期待すると採点を踏み外す)
  3. Junos 収集は network_cli(cli_command)が楽(netconf 版 junos_command の display json
     対応より確実・`\| no-more` 不要=terminal plugin が screen-length 0 を設定)
  4. 採点中の JUN01 は labid 指紋なし扱いで素通し(構造上 clab ノードに指紋を焼く手段が
     未整備。J の宿題= clab 側 labid 相当(例: system login message)の検討)
  5. 手動テストラボ(iol-0=10.0.12.2)と PoC の IP 衝突が起きた→**複合ラボは境界サブネットの
     台帳管理が必要**(当面は 10.0.12.0/30 を BL-061 専用に予約)

## 6. 再開手順(2026-07-28 中断時点のスナップショット)
- **現在地**: A〜D・F 完了(PoC 100/100 フルサイクル済・§5)。**次= E(.clab.yml 出力+deploy ラッパ)→初弾 interop 問**
- **残置状態**:
  - CML: PoC ラボ撤収済・リース解放済(クリーン)
  - clab(szk-cl01): **ospf ラボ(evo1=JUN01/evo2)は稼働のまま残置**(ユーザ資産のため)。
    RAM 16GiB 消費中。落とす場合= `containerlab destroy -t ~/labs/ospf.clab.yml`
  - 復元資材(ラボを落としても再現可能): `problems/POC-CLABHYB-01/clab/ospf.clab.yml`(トポロジ)
    ＋ `clab/jun01.set.cfg`(JUN01 config・load set terminal で復元)
- **PoC 再現(いつでも)**: clab側 ospf ラボ稼働中なら
  `scripts/lab.sh provision POC-CLABHYB-01` → `ansible-playbook playbooks/grade.yml -e problem=POC-CLABHYB-01 --vault-password-file <(echo CCNP)` → `scripts/lab.sh teardown POC-CLABHYB-01` だけで回る
- **接続情報**: group_vars/all/local.yml の `clab_*` / szk-cl01 は鍵認証済 / EVO は admin/admin@123

## 4. 未確認事項(次回確認)
- 制御ホストからのルート追加後の実疎通(iptables は通る想定だが未実証)
- vJunos EVO のブート所要時間・startup-config 焼き込みの実動作
- ~~CML 側 ext-conn がどのブリッジ/NIC か~~ → **解決済(2026-07-28)**: `bridge1`(ラベル LAN-IX・ens32)。
  ユーザ提示の `ip link`(ens32 master bridge1)＋CML API `/system/external_connectors` 実照会で確定
- ens32/ens160 両側の ESXi ポートグループの VLAN/セキュリティ設定(多重リンク化 G の前提)
- `containerlab version` は 0.77.0 だが vJunos EVO kind の startup-config 対応詳細
