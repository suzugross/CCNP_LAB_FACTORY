# CCNP 演習シミュレータ (CCNP01)

**Cisco CML（Cisco Modeling Labs）上に実機ネットワークを自動構築し、CCNP 相当の課題を出題 → 受験者が実コマンドで解答 → 自動採点する**、Ansible + pyATS/Genie ベースの学習システムです。

対象は Cisco 認定 **CCNP ENCOR (350-401)** / **ENARSI (300-410)** の技術領域。「問題を作る・投入する・採点する」を一気通貫で自動化しているので、**同じ技術を何度でも・少しずつ値を変えて**練習できます。

> 個人の学習・作問用に育てたリポジトリです。特定のCML環境で実機検証しながら作っていますが、環境依存の値（CML接続情報・管理IP）は差し替え可能にしてあります（後述の[セットアップ](#セットアップ)参照）。

```
  問題生成/作問 ──→ 初期投入 ──→ 受験者が CML で実コマンド解答 ──→ 自動採点
  (生成器 gen_*.py)  (Ansible)      (CML コンソール / SSH)          (pyATS Genie で構造化して判定)
```

<img width="949" height="654" alt="Image" src="https://github.com/user-attachments/assets/ac9b24c9-702e-4e60-be59-5adf3a563fc6" />
<img width="1485" height="721" alt="Image" src="https://github.com/user-attachments/assets/caa82c17-aed6-4300-9346-2d59c8320208" />

---

## 特徴

- **実機で学べる** — シミュレータの近似ではなく、本物の Cisco IOS-XE / IOSv / IOS-L2 を CML 上で動かして解く。
- **完全自動の採点** — `show` 出力を pyATS Genie で構造化し、フィールド単位でアサート。「隣接が FULL か」「この経路だけ消えているか」「ping が通るか」まで機械判定。合否は収束するまでリトライ。
- **問題の量産** — seed を渡すと生成器がトポロジ・故障・パラメータをランダム化して問題を丸ごと生成。**同じ seed なら同じ問題**（再現可能）。
- **自己完結の問題パック** — 1問 = 1ディレクトリ。問題文・初期config・採点基準・模範解答が揃っている。
- **トラブルシュート対応** — 正常構成に故障を注入して「直す」問題や、複数レイヤにまたがる連鎖故障も生成できる。
- **Ansible 自動化ラボ** — Cisco 機器を題材に Ansible そのものを学ぶ「道場」コースも同梱。

---

## 仕組み

4つの Ansible playbook が「描画 → 起動 → 解答 → 採点」を担います。

```
 build_topology.yml ──→ lab_up.yml ──────→ (受験者が解答) ──→ grade.yml
   day0 config を描画        CML へ import          実機 CLI で        show 出力を Genie で
   + gen_cml_lab.py で        して起動               設定を投入          構造化し、基準と照合
   ラボ YAML を生成                                                     して点数を返す
```

1. **build_topology.yml** — 問題定義（`problem.yml`）から day0 の「穴あき」config を描画し、`gen_cml_lab.py` が CML 用ラボ YAML（ノード・配線・管理IP）を生成する。
2. **lab_up.yml** — そのラボを CML に import して起動する。管理IPは共有プールから動的に貸与（`mgmt_alloc.py` の台帳が管理）。
3. **受験者の解答** — CML のコンソール、または管理IP経由の SSH で機器にログインし、実コマンドで設定する。自動化ラボの場合は付属の作業ディレクトリで Ansible を書く。
4. **grade.yml** — 各ノードへ `show` を送って出力を Genie で構造化し、採点基準（`grading.yml`）のチェックを1つずつ判定。全PASS になるまで一定間隔でリトライ（設定の収束待ち）。

採点の詳細は [採点の仕組み](#採点の仕組みgradepy--pyats-genie) を参照。

---

## 何ができる / どんな問題が出せるか

現在 **problems/ に 100 問超**（ENCOR 系 58・ENARSI 系 44・Ansible 自動化 5）。難易度は 1〜6 で、3〜4 が中心。加えて **生成器から無限にバリエーション**を作れます。

### ENCOR（350-401）系

| 分野 | 主な問題 |
|------|---------|
| **OSPF** | 単一エリア / マルチエリア / stub / NSSA / インターフェイスモード / 認証 / OSPFv3 |
| **EIGRP** | 基本構築 / variance による不等コストロードバランス / SIA トラブルシュート |
| **再配送** | OSPF ⇄ EIGRP など IGP 相互再配送 |
| **First-Hop 冗長** | HSRP（FHRP） |
| **トンネル / VPN** | GRE、DMVPN（Phase2 / Phase3）、IPsec sVTI（IKEv1 / IKEv2） |
| **経路制御** | PBR、IP SLA + Object Tracking、WAN 冗長・フェイルオーバ |
| **セグメンテーション** | VRF-Lite、VRF ルートリーク、VRF + NAT |
| **セキュリティ / L2** | 標準/拡張/名前付き ACL、VACL、SPAN / RSPAN、CoPP、エッジ機器ハードニング |
| **可視化 / 運用** | Flexible NetFlow、EEM |
| **QoS** | 分類・マーキング / ポリシング / 階層シェーピング + LLQ（効果を iperf3/ping で実測採点する体感シリーズ3問） |
| **その他** | LAG（EtherChannel）、IPv6 静的 / SLAAC、NAT/PAT 複合 |

### ENARSI（300-410）系

| 分野 | 主な問題 |
|------|---------|
| **BGP 属性 / 経路制御** | weight / local-preference / MED / community / AS-path / origin / next-hop-self |
| **BGP フィルタ / 集約** | prefix-list、route-map、AS-path 正規表現、経路集約、ルートリフレクタ |
| **BGP 複合** | 複数属性を組み合わせた総合ポリシー問題 |
| **再配送** | 相互再配送、再配送ループの発生と抑止 |
| **MPLS** | MPLS L3VPN 基礎構築（LDP / MP-BGP VPNv4 / VRF・マルチカスタマー） |
| **オーバーレイ複合** | DMVPN + BGP 再配送 |

### 生成問題（`GEN-*`）— seed で量産

| 種別 | 生成器 | 内容 |
|------|--------|------|
| 到達性 | `gen_topology.py` | ランダムなツリー型 OSPF。BFS で一意な next-hop を計算し採点 |
| ひねり | `gen_twist.py` / `gen_aggregate.py` / `gen_pathctrl.py` | ルートフィルタ / 経路集約・マルチエリア / 経路制御・冗長 |
| トラブルシュート | `gen_troubleshoot.py` | OSPF に故障を注入（多重故障・おとり・段差故障に対応） |
| BGP TS | `gen_bgp_troubleshoot.py` / `gen_bgp_pathts.py` / `gen_bgp_rrts.py` / `gen_bgp_complex_ts.py` | 到達性 / 経路選択 / RR 伝播 / 複合故障 |
| IGP 複合 TS | `gen_eigrp_complex_ts.py` / `gen_ospf_complex_ts.py` / `gen_ospfv3_complex_ts.py` / `gen_eigrpv6_complex_ts.py` | EIGRP / OSPF / OSPFv3 / EIGRPv6 の複合故障 |
| 再配送 TS | `gen_redist_mutual_ts.py` / `gen_redist_ripospf_ts.py` | 相互再配送 / RIP⇄OSPF 再配送ループ |
| 連鎖故障 | `gen_chain_ts.py` | 12台規模でレイヤをまたぐ連鎖故障を生成 |
| MPLS L3VPN TS | `gen_mpls_ts.py` | 12台 (3PE×Pリング×2顧客) の L3VPN に L1〜L5 の故障を注入 |
| L2 TS | `gen_l2_troubleshoot.py` | EtherChannel など L2 の故障 |
| セキュリティ TS | `gen_urpf_ts.py` | uRPF anti-spoofing の故障（strict過剰/ACL例外誤り/未設定/loose過緩の4種・非対称ルーティング題材） |
| サーバ / 監視 | `gen_dnsdhcp_*.py` / `gen_radius_build.py` / `gen_snmpv3_ts.py` / `gen_zbx*`(SNMP/Zabbix) | Linux サーバ（BIND/DHCP/FreeRADIUS）構築・TS、SNMPv3/Zabbix 監視 |

### Ansible 自動化ラボ（`ANSIBLE-01〜05`）

Cisco 機器を題材に **Ansible 自体**を段階学習するコース。トポロジは固定で「変わるのは Ansible 技術だけ」。
インベントリ → アドホック → Playbook → 変数優先順位 → 冪等性 の順に進む。ENCOR/ENARSI 側にも「OSPF/BGP を Ansible で自動構築する」自動化問題（`*-AUTO-*`）がある。

問題一覧は `ls problems/`、各問題の詳細は `problems/<ID>/task.md(.j2)` と `solution.md` を参照。

---

## 動作要件

| 必要なもの | 用途 |
|-----------|------|
| **Cisco CML 2.x** | ネットワーク機器を動かす基盤（API 有効・ログイン可能なこと） |
| CML ノードイメージ | ルータ/スイッチ用に IOL(iol-xe / ioll2-xe)、または IOSv/IOSvL2。Linux 問題用に Ubuntu クラウドイメージ |
| **Linux コントローラ**（Ubuntu 想定） | Ansible + pyATS を動かすホスト。CML と管理ネットワークで疎通できること |
| Python 仮想環境 | `.venv` に ansible-core、pyATS/Genie、`cisco.ios` / `cisco.cml` コレクション、`virl2_client` |

> 使用する CML イメージ ID は `group_vars/all/main.yml` の `device_profiles` で定義。手元の CML に登録済みの正確な ID に合わせて調整してください。

---

## セットアップ

```bash
git clone <this-repo> && cd CCNP01

# 1) Python 仮想環境（ansible-core / pyATS / cisco.ios / cisco.cml / virl2_client を導入）
python3 -m venv .venv && . .venv/bin/activate
pip install ansible-core pyats[full] && ansible-galaxy collection install cisco.ios cisco.cml

# 2) ★ローカル環境設定（CML接続情報・管理IPプール）を自分の値で作成
cp group_vars/all/local.yml.example group_vars/all/local.yml
$EDITOR group_vars/all/local.yml     # cml_host / cml_username / cml_password と mgmt_* を編集
```

`group_vars/all/local.yml` は **`.gitignore` 済み**（コミットされない）。CML の場所・ログイン・管理ネットワークといった各自の環境依存値はここだけに置きます。雛形は [`group_vars/all/local.yml.example`](group_vars/all/local.yml.example)。

**機器のログイン認証**は Ansible Vault（`group_vars/all/vault.yml`）に格納。学習用の固定値なので **vault パスワードは `CCNP`**、playbook 実行時に `--vault-password-file <(printf 'CCNP\n')` を付けます（各ノードの config テンプレートが同じ user/secret を焼き込む前提。変える場合はテンプレート側も合わせて変更）。

---

## クイックスタート

`scripts/lab.sh` がライフサイクル（build → up → 作業コピー配布 → 撤去）を一括管理します。

```bash
# 出題（build_topology → lab_up → lab/<ID>/ に問題.md と作業コピーを配置）
scripts/lab.sh provision ENCOR-OSPF-01           # variant 指定は第2引数: provision <ID> <variant>

# 受験者は CML コンソール / SSH で機器にログインして解答
#   - SSH 例: ssh <user>@<割当てられた管理IP>
#   - 自動化ラボ(ANSIBLE-*/AUTO-*)は lab/<ID>/ を編集して playbook を流す

# 採点
ansible-playbook playbooks/grade.yml -e problem=ENCOR-OSPF-01 \
  --vault-password-file <(printf 'CCNP\n')
# パラメータ化問題は -e variant=sXXXX も付ける

# 片付け（CMLラボを削除して管理IPを解放。problems/<ID> 自体は残る）
scripts/lab.sh teardown ENCOR-OSPF-01

scripts/lab.sh status                            # 稼働ラボ・管理IPの空き・作業コピー一覧
```

`lab.sh` を使わず手で回す場合:

```bash
V="--vault-password-file <(printf 'CCNP\n')"
ansible-playbook playbooks/build_topology.yml -e problem=<ID> [-e variant=<v>] [-e node_image=iosv] $V
ansible-playbook playbooks/lab_up.yml         -e problem=<ID> $V          # 停止/撤去: -e lab_state=stopped|absent
ansible-playbook playbooks/grade.yml          -e problem=<ID> $V          # -e max_attempts= -e settle_delay= で収束調整
```

> **複数ラボの同時稼働に対応**。管理IPは `topologies/mgmt_alloc.py` のリース台帳（`_state/mgmt_leases.json`）が first-fit で調停するため、旧ラボを撤去せずに新ラボを起動しても管理IP衝突は起きません。teardown 漏れは `mgmt_alloc.py gc` で回収できます。
>
> 同時稼働の上限は**環境依存**で、コードにハードコードした定数はありません。実質的には次の2つで決まります。
> 1. **管理IPプールのサイズ** = `group_vars/all/local.yml` の `mgmt_pool` の要素数（環境ごとに各自が設定・`.gitignore` 済。天井は管理セグメントのサブネット幅）。`mgmt_alloc.py` はプール不足のときだけ割当を停止する（要求ノード数 > 空きIP数 → rc=2、CML には触らない）。
> 2. **CML の同時起動ノード数** = CML ライセンスグレードの制約（例: Personal は 20 ノード）。プロジェクト側はこれを関知せず、超過分は CML が拒否する。Enterprise 等では実質プールサイズが律速。

---

## ディレクトリ構成

```
CCNP01/
├── ansible.cfg                  # network device 向け接続設定
├── inventory.yml                # 名前/グループのみ（管理IPは動的割当）
├── group_vars/ host_vars/       # 接続変数・device_profiles・vault(機器認証) / local.yml(環境依存・gitignore)
├── roles/baseline/              # day0 baseline テンプレート（baseline_router/switch/server.cfg.j2）
├── playbooks/
│   ├── build_topology.yml       # day0 描画 + gen_cml_lab.py → _generated/<ID>/lab.yaml
│   ├── lab_up.yml               # CML へ import + 起動（管理IP割当・プリフライト）
│   ├── grade.yml + _grade_attempt*.yml   # 採点（ssh / telnet / console の3収集パス）
│   ├── solve_generated.yml / fix_generated.yml   # 生成問題の模範解答/故障修正の自動投入
│   └── verify_failover*.yml     # フェイルオーバ（shut→疎通→復旧）の能動検証
├── topologies/
│   ├── conventions.md           # 採番・配線・命名規約
│   ├── gen_cml_lab.py           # problem.yml → CML ラボ YAML
│   ├── grade.py + netmodel.py   # 採点エンジン（Genie 構造化 / 大域不変条件）
│   ├── mgmt_alloc.py            # 管理IPリース台帳（複数ラボ同時稼働の調停）
│   ├── gen_*.py                 # 各種生成器
│   └── _generated/<ID>/         # build で出る中間物（mgmt_map / lab.yaml / 描画済 task.md 等・gitignore）
├── problems/<ID>/               # 問題パック（自己完結）
├── scripts/lab.sh               # 出題/片付けラッパ
└── lab/<ID>/                    # provision が作る使い捨て作業コピー（gitignore）
```

---

## 問題パック仕様

1問 = `problems/<ID>/` の自己完結ディレクトリ。

| ファイル | 役割 |
|---------|------|
| `problem.yml` | メタ（id/exam/topics/difficulty/target_nodes/points）＋ `lab.links`（配線。a_if/b_if は slot 番号） |
| `task.md` または `task.md.j2` | 受験者向け問題文（日本語）。`.j2` は params で数値が変わる |
| `initial/<NODE>.cfg.j2` | 出題時に重ねる「穴あき」config |
| `grading.yml` または `grading.yml.j2` | 採点基準（フィールドアサート型スキーマ） |
| `solution.md` | 模範解答 |
| `params/` | パラメータ化（`base.yml` 既定値 + `_gen.yml` ランダム化スキーマ） |
| `controller/` `controller_solution/` `blanks.yml` | 自動化ラボ用の穴あき workspace と完成形 |

### パラメータ化（値違い問題の量産）
`initial/grading/task` を `.j2` 化し `{{ params.xxx }}` を参照。`-e variant=<name>`（既定 `base`）で値を切替。
ランダム生成は `gen_params.py --problem <ID> --seed N` → `params/sN.yml`（同 seed = 同値 = 再現可能）。

---

## 採点の仕組み（`grade.py` / pyATS Genie）

- `show` 出力を Genie で**構造化** → `find`（glob でオブジェクト選択）+ `match`（同一オブジェクト上でフィールド相関）で判定。配点は all-or-nothing。
- `grade.yml` が **全PASS or max_attempts まで settle_delay 秒間隔でリトライ**（収束待ち）。
- Genie パーサが無い/壊れる箇所は **`raw:` 正規表現**（contains / not_contains / regex …）で判定。「特定経路だけ不在」「単一経路化（ECMP排除）」「能動 ping の成否」もこれで表現。
- `netmodel.py` = ネット全体の**大域不変条件**（ループ不在 / 最適性 / 到達性）を採点する別系統。
- 収集パスは `problem.yml` の `access:` で分岐: `ssh`（既定）/ `telnet`（IOL L2スイッチ）/ `console`（IOSv）。

`grading.yml` スキーマ例:
```yaml
defaults: { genie_os: iosxe }
checks:
  - name: "RT01-RT02 OSPF 隣接 FULL"
    node: RT01
    command: show ip ospf neighbor
    parser:  show ip ospf neighbor        # command=実機へ送る文字列 / parser=Genieキー（別物）
    find:    "interfaces.*.neighbors.*"
    match:   { state: { startswith: "FULL" } }
    points:  30
  - name: "特定経路だけ不在（raw で判定）"
    node: RT04
    command: show ip route 35.35.35.35
    raw: [ { regex: "not in table" } ]
    points: 10
```

---

## 規約（要点 / 詳細は [conventions.md](topologies/conventions.md)）

- **命名**: `RTxx`=router / `SWxx`=switch（接頭辞でロール自動判定）。CMLラボ名は `CCNP-LAB-<md5(id)[:8]>` で**不透明化**（画面に技術名が出て解法バレを防ぐ）。
- **採番**: Loopback0 = `x.x.x.x/32`（RT01→1.1.1.1）。ルータ間 = `10.1.<a><b>.0/30`（小番号側が .1）。
- **イメージ**: トポロジ単位で統一。優先 `CLI -e node_image` > `problem.yml` > group既定。物理IF名は device_profiles で論理↔物理を吸収。

---

## 運用上の落とし穴

- **複数ラボ同時稼働可**（管理IPは `mgmt_alloc.py` のリース台帳が調停）。上限は**環境依存**でコード定数はない：`mgmt_pool`（`local.yml`）の要素数と、CML グレードの同時起動ノード数（例: Personal 20）で決まる。teardown 漏れは `mgmt_alloc.py gc` で回収し、不要ラボは `scripts/lab.sh teardown <ID>` で撤去する。
- **baseline 末尾に `end` を置かない**（day0 は baseline+initial を連結。中間 `end` 以降が無視される）。
- **IOL はリンクダウンを対向に伝播しない**（片端 shutdown でも対向 line protocol は up）。フェイルオーバ設計は remote link-down 検知に依存しないこと。
- `raw` 採点は IOS のコマンド省略形・別表記に脆い → 各語を `<最短プレフィクス>[\w-]*` で緩める。
- `task.md.j2` にリテラル `{{ ____ }}` を書くと描画器が変数解釈して失敗 → `{% raw %}…{% endraw %}` で囲む。
- 採点チェックが多く**2分超**になる問題は、実行ツールの timeout を上げる。

---

## ライセンス / 免責

学習・作問目的の個人プロジェクトです。Cisco IOS 等のイメージは各自が正規に入手・ライセンスした CML 環境で使用してください（本リポジトリにイメージは含みません）。
