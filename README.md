# CCNP 演習シミュレータ (CCNP01)

**Cisco CML（Cisco Modeling Labs）と containerlab の上に本物のネットワーク OS を自動で組み、課題を出題 → 実コマンドで解答 → 自動採点する**学習システムです。土台は Ansible と pyATS/Genie。出題から採点・撤収までを Claude Code で回す前提で作っています（手順は [CLAUDE.md](CLAUDE.md) と [`/quiz` スキル](.claude/skills/quiz/SKILL.md)）。

学び方は 4 つあります。

| 学び方 | 中身 |
|---|---|
| **ラボ** | CML / containerlab の実機で構築・トラブルシュート。`show` 出力を構造化して自動採点 |
| **紙面パック** | 選択式・穴埋めの問題用紙（HTML）。1 日 3 パック。採点と同時に解説ページが出る |
| **教材コース** | 日英を 1 冊で切り替える読み物と、課題ごとに確認・ヒントが付く学習ラボ（IOS XR トラック・Junos トラック） |
| **学習ゲーム** | STP とルーティングの盤面をブラウザで解く |

範囲は CCNP ENCOR (350-401)・ENARSI (300-410) を中心に、CCNA の基礎、SP 系（IOS XR・SPCOR 350-501 寄り）、マルチベンダ（FortiGate・Junos・Arista EOS・FRRouting）まで広げています。

> 個人の学習・作問用に育てたリポジトリです。特定のラボ環境で実機検証しながら作っていますが、環境に依存する値（CML と containerlab ホストの接続情報・管理 IP）は `group_vars/all/local.yml` に分けてあります（[セットアップ](#セットアップ)参照）。

```
  生成器 gen_*.py（seed で再現可能）／固定の問題 problems/<ID>/
        │
        ├─ ラボ:  build_topology → lab_up ─────→ 実機で解答 ─────────→ grade
        │          (Ansible)       (CML / containerlab)  (ワークスペース / SSH)    (pyATS Genie で判定)
        │
        ├─ 紙面:  pack.sh new ──→ HTML の問題用紙 ──→ ブラウザで解答 ──→ pack.sh grade → 解説ページ
        │
        └─ 教材:  course.sh build ──→ ポータルで読む ──→ lab.sh learn（課題ごとの確認・ヒント）
```

<img width="949" height="654" alt="Image" src="https://github.com/user-attachments/assets/ac9b24c9-702e-4e60-be59-5adf3a563fc6" />
<img width="1485" height="721" alt="Image" src="https://github.com/user-attachments/assets/caa82c17-aed6-4300-9346-2d59c8320208" />

---

## 特徴

- **実機で学べる** — シミュレータの近似ではなく、本物の OS を動かして解く。IOL（IOS XE / L2）・IOSv / IOSvL2・Catalyst 8000V・IOS XRv 9000・IOS XRd・NX-OS・ASAv・FortiGate-VM（CML）、vJunos-Evolved・Arista cEOS・FRRouting（containerlab）、Ubuntu（サーバ・監視）。
- **完全自動の採点** — `show` 出力を pyATS Genie で構造化し、フィールド単位で判定する。「隣接が FULL か」「この経路だけ消えているか」「ping が通るか」まで機械で判定し、設定が収束するまでリトライする。
- **問題の量産** — seed を渡すと生成器がトポロジ・故障・パラメータをランダムに決めて問題を丸ごと作る。**同じ seed なら同じ問題**（再現できる）。
- **紙面にも実機の裏づけ** — `gen_paper_mcq.py` の一部の shape は、使い捨てのラボを CML に組んで `show` を集めてから問題用紙にする。ほかのファミリも、正誤の根拠を公式文書と実機で確かめてから出す。
- **英語で出題** — 問題文は英語が基本。英訳がある問はページの中のボタンで日本語に切り替えられる（解説は日本語）。
- **1 問 = 1 ディレクトリ** — 問題文・初期 config・採点基準・模範解答が揃っている。
- **単元で管理** — [`CURRICULUM.md`](CURRICULUM.md) が単元ごとの紙面とラボの到達度の台帳。毎日のパックは単元を順に回して出す。
- **Ansible 自動化ラボ** — Cisco 機器を題材に Ansible そのものを学ぶコースも同梱。

---

## 4 つの学び方

### ラボ（`scripts/lab.sh`）

1 問ずつ CML / containerlab に組んで解きます。解くのはブラウザのワークスペース（左に課題とトポロジ、右に機器のコンソール）か、CML のコンソール・SSH。

| コマンド | 内容 |
|---|---|
| `lab.sh provision <ID> [variant]` | 構築して起動し、`lab/<ID>/` に課題文と作業コピーを置く |
| `lab.sh grade <ID> [variant]` | 採点（得点を学習記録 `records/` にも残す） |
| `lab.sh checkpoint <ID> <名前>` | 途中の状態を `grading.<名前>.yml` で確認（記録に残さない） |
| `lab.sh reset <ID> [--rebuild]` | 構築直後へ戻してやり直す（IOS XR はコミットの巻き戻し、Junos は `load override`） |
| `lab.sh learn <ID> [PORT]` | 学習モードのワークスペースを開く（`learn.yml` を持つ問題） |
| `lab.sh connect <ID> <NODE>` | containerlab のノードに入る（FRR は vtysh、Junos・EOS は SSH） |
| `lab.sh rma <ID> <NODE>` | 機器交換の演習（保存した設定で MAC の違う機体に入れ替える。CML のみ） |
| `lab.sh teardown <ID>` | ラボを消して管理 IP を返す（`problems/<ID>` は残る） |
| `lab.sh status` | 稼働中のラボ・管理 IP の空き・作業コピーの一覧 |

出題可の問題の一覧は [`problems/CATALOG.md`](problems/CATALOG.md)（実機で通しの検証が済んだものだけ）。

### 紙面パック（`scripts/pack.sh`）

1 回の `pack.sh new` で、その日の 3 パックを `packs/<PACK-ID>/` に作ります。

- 1 パック = 思考系 2 問・瞬発力 3 問・解説の穴埋め 2 問。ラボ 3 本は 1 本目のパックに付く。
- 出す単元は、最後に出した日が古い順に回す（`topologies/units.yml`・`paper_rotation.py`・`lab_rotation.py`）。`--profile ccna|encor|enarsi|ccie|sp|vendor` や単元 ID で範囲を絞れる。
- `pack.sh serve` で配信すると、ページの解答欄がそのまま `解答.md` に保存される。
- `pack.sh grade` が採点して、解説ページ `report.html` を作る（解答の並置・なぜこの答えか・選択肢ごとの理由・実機での確かめ方）。
- 英訳は `questions/en/<ID>.md` に置く。原文との照合（`pack.sh en`）を通った訳だけが使われる。

### 教材コース（`courses/`・`scripts/course.sh`）

公開文書と実機での確認をもとに書き下ろした教材です。英語が原文で、1 冊の中のボタンで日本語に切り替わります。単元を読んでから、その単元の学習ラボで手を動かします。

| コース | 単元 | 学習ラボ |
|---|---|---|
| IOS XR トラック（`courses/xr/`） | M0 入り方と調べ方 〜 M13 自動化とアシュアランス（設定の管理・OSPF・IS-IS・RPL・BGP・MPLS/LDP・L3VPN・SR・L2VPN・QoS など） | `XRT-01`〜`XRT-15`（XRv 9000 / XRd・一部 Catalyst 8000V） |
| Junos トラック（`courses/junos/`） | J0 IOS・IOS XR から Junos へ、J1 ルーティング ポリシー | `JNT-01`〜（containerlab の vJunos-Evolved） |

- **学習モード**（`lab.sh learn`）は、ワークスペースに Steps タブが増える。課題ごとに確認（途中の採点）・段階式のヒント・確かめ方の例が見られる。
- 本文の専門用語は [`glossary/`](glossary/) の辞書から拾い、カーソルを置くと説明が出る。
- `course.sh <名前> sync` で言語ごとに 1 枚の HTML へ束ね、rclone でクラウドに置く（スマホで通信なしに読める）。
- 同じ基盤（`topologies/gen_reading.py`・`scripts/read.sh`）で、技術文書の訳文を読み物にすることもできる（訳文そのものはリポに含めていない）。

### 学習ゲーム（`games/`）

ポータルから遊べる、盤面を読み解くゲームです。進み具合はサーバに残ります。

| ゲーム | 内容 |
|---|---|
| STP パズル（`/_stp/`） | 図のポートに役割と状態を書き込む |
| STP 経路づくり（`/_stp_path/`） | priority・速度・cost・port-priority を変えて、お題の経路にする |
| ルーティング経路づくり（`/_route_path/`） | インターフェースと static route を変えて、お題の道にパケットを通す |

計算はサーバ側のモデル（`stp_model.py`・`route_model.py`）が行い、実機と照らし合わせてあります。

### ポータルとワークスペース

`scripts/pack.sh serve` で次の 2 つが上がります。

- **ポータル**（既定 8899）: 教材の棚・パックの一覧（採点状態つき）・ゲーム。
- **ワークスペース**（既定 8897・`topologies/lab_console.py`）: ラボを 1 画面で解く。ブラウザ（xterm.js）から WebSocket で中継し、CML のコンソールサーバか containerlab のノードへつなぐ。

---

## 仕組み

4 つの Ansible playbook が「描画 → 起動 → 解答 → 採点」を担います。

```
 build_topology.yml ──→ lab_up.yml ──────→ (受験者が解答) ──→ grade.yml
   day0 config を描画        CML へ import          実機 CLI で        show 出力を Genie で
   + gen_cml_lab.py で        して起動               設定を投入          構造化し、基準と照合
   ラボ YAML を生成                                                     して点数を返す
```

1. **build_topology.yml** — 問題定義（`problem.yml`）から day0 の「穴あき」config を描画し、`gen_cml_lab.py` が CML 用ラボ YAML（ノード・配線・管理 IP）を作る。
2. **lab_up.yml** — そのラボを CML に import して起動する。管理 IP は共有プールから動的に貸す（`mgmt_alloc.py` の台帳が管理）。
3. **受験者の解答** — ワークスペース・CML のコンソール・管理 IP への SSH で機器に入り、実コマンドで設定する。自動化ラボは付属の作業ディレクトリで Ansible を書く。
4. **grade.yml** — 各ノードへ `show` を送って出力を Genie で構造化し、採点基準（`grading.yml`）のチェックを 1 つずつ判定する。全 PASS になるまで一定間隔でリトライ（設定の収束待ち）。

**containerlab の問題**（`problem.yml` に `platform: clab`）は CML を使いません。`topologies/clab_ops.py` が `problems/<ID>/clab/` の資材を containerlab ホストへ送って deploy / destroy し、採点は Junos・EOS へ SSH、FRR へは `docker exec` で `show` を集めます。CML と containerlab をまたぐ複合ラボも組めます。

採点の詳細は [採点の仕組み](#採点の仕組みgradepy--pyats-genie) を参照。

---

## 扱う範囲

単元の区分は [`CURRICULUM.md`](CURRICULUM.md) に合わせています。各単元の紙面・ラボの有無と問題 ID はそちらと [`problems/CATALOG.md`](problems/CATALOG.md) が正本です。

| 区分 | 主な題材 |
|---|---|
| A. L2 / キャンパス | VLAN・STP（PVST+ / MST・3 層盤面）・EtherChannel・FHRP・SPAN / RSPAN・VACL |
| B. ルーティング基礎・経路制御 | static・PBR・IP SLA + track・WAN 冗長・VRF-Lite とルートリーク・再配送（相互・ループと抑止・仕様書駆動の選択的再配送） |
| C〜E. IGP / BGP | EIGRP（variance・SIA・VRF）・OSPF（マルチエリア・stub / NSSA・認証・OSPFv3）・BGP（属性・フィルタ・集約・RR・IPv6・レガシー synchronization） |
| F. マルチキャスト | IGMP・PIM・RP（紙面の穴埋めのみ） |
| G. VPN / オーバーレイ | GRE・DMVPN（Phase 2 / 3・IPsec）・IPsec（sVTI・crypto map）・MPLS L3VPN・SD-Access の土台（LISP / VXLAN）・EVPN-VXLAN |
| H. セキュリティ | ACL・CoPP・uRPF・AAA（RADIUS）・IPv6 FHS・エッジ機器のハードニング |
| I. インフラサービス / 運用 | DHCP / DHCPv6・NAT・Flexible NetFlow・EEM・SNMPv3 と Zabbix・DNS / DHCP / FreeRADIUS サーバ |
| J. IPv6 基礎 | アドレッシング・SLAAC・RA |
| K. 自動化 | Ansible 自動化ラボ・RESTCONF |
| L. 基礎概念 | CCNA 範囲の知識（紙面のみ） |
| M. IOS XR | XR トラックの単元（上の教材コース） |
| マルチベンダ | FortiGate（SD-WAN・FW ポリシー・Cisco との IPsec・ASA からの置き換え）・Junos トラック |

規模（2026-11 時点）: `problems/` に 441 個（固定の問題 117・生成済みの GEN インスタンス 319・containerlab の試験台 5）、ラボの生成器 約 50 本、紙面の生成器 27 本、紙面の問題 約 1,000 問。

### 生成器（`topologies/gen_*.py`）

seed で問題を量産します。主な系統は次のとおりです（全体の一覧は [`problems/CATALOG.md`](problems/CATALOG.md) の「生成器一覧」）。

| 系統 | 例 |
|---|---|
| IGP・経路制御 | `gen_topology.py`（ランダムなツリー型 OSPF）・`gen_troubleshoot.py`・`gen_ospf_complex_ts.py`・`gen_eigrp_complex_ts.py`・`gen_route_ctrl.py` |
| BGP | `gen_bgp_troubleshoot.py`・`gen_bgp_pathts.py`・`gen_bgp_rrts.py`・`gen_bgp_complex_ts.py`・`gen_bgp_ring_ts.py` |
| 再配送 | `gen_redist_field.py`・`gen_redist_mutual_ts.py`・`gen_redist_loop_ts.py`・`gen_redist_mp_ts.py` |
| 複数レイヤの連鎖故障 | `gen_chain_ts.py`（12 台規模）・`gen_enterprise.py`（拠点構築） |
| VPN・MPLS | `gen_dmvpn_ts.py`・`gen_dmvpn_wreck.py`・`gen_mpls_ts.py`・`gen_s2svpn.py`（要件書から設計して組む） |
| L2 | `gen_stp.py`・`gen_stp_3tier.py`・`gen_stp_mst.py`・`gen_l2_troubleshoot.py` |
| サービス・セキュリティ | `gen_dhcp_ts.py`・`gen_fnf_ts.py`・`gen_ipsla_ts.py`・`gen_urpf_ts.py`・`gen_v6addr_ts.py`・`gen_snmpv3_ts.py` |
| フィルタの道場 | `gen_list_dojo.py`（prefix-list / AS-path / ACL）・`gen_dojo_dlist.py`（distribute-list） |
| 紙面 | `gen_paper_mcq.py`（多くの shape の入口）・`gen_paper_cloze.py`（解説の穴埋め）ほか `gen_paper_*.py` |

---

## 動作要件

| 必要なもの | 用途 |
|---|---|
| **Cisco CML 2.x**（2.10 で検証） | ネットワーク機器を動かす基盤（API が有効でログインできること） |
| CML のノードイメージ | IOL（iol-xe / ioll2-xe）・IOSv / IOSvL2・Catalyst 8000V・IOS XRv 9000・IOS XRd・Ubuntu など。問題ごとに要るものが違う |
| containerlab ホスト（任意） | `platform: clab` の問題用。Linux + Docker + containerlab（0.83 で検証）。vJunos-Evolved・cEOS・FRR のイメージを入れておく |
| **制御ホスト** | Ansible と pyATS を動かすホスト（Linux・Python 3.12 で検証）。CML・containerlab ホストと管理ネットワークで通じること |
| Python と Ansible の依存 | [`.devcontainer/requirements.txt`](.devcontainer/requirements.txt)（ansible-core・pyATS/Genie・virl2_client ほか）と [`.devcontainer/requirements.yml`](.devcontainer/requirements.yml)（cisco.cml・juniper.device・junipernetworks.junos） |
| rclone（任意） | 教材をクラウドへ持ち出す時だけ |

> 使う CML のイメージ ID は `group_vars/all/main.yml` の `device_profiles` で定義しています。手元の CML に登録済みの ID に合わせてください。

---

## セットアップ

```bash
git clone <this-repo> && cd CCNP01

# 1) Python の仮想環境と Ansible のコレクション
python3 -m venv .venv && . .venv/bin/activate
pip install -r .devcontainer/requirements.txt
ansible-galaxy collection install -r .devcontainer/requirements.yml

# 2) ★ローカルの環境設定（CML・管理 IP のプール・containerlab ホスト）を自分の値で作る
cp group_vars/all/local.yml.example group_vars/all/local.yml
$EDITOR group_vars/all/local.yml
```

- `group_vars/all/local.yml` は **`.gitignore` 済み**（コミットされない）。環境に依存する値はここだけに置きます。雛形は [`group_vars/all/local.yml.example`](group_vars/all/local.yml.example)。containerlab の項目は、`platform: clab` の問題を使う時だけ要ります。
- **機器のログイン認証**は Ansible Vault（`group_vars/all/vault.yml`）に入っています。学習用の固定値なので **vault パスワードは `CCNP`**。playbook を直接流す時は `--vault-password-file <(printf 'CCNP\n')` を付けます（`lab.sh`・`pack.sh` は自分で付ける）。各ノードの config テンプレートが同じ user / secret を焼き込む前提なので、変える時はテンプレートも合わせます。
- 制御ホストを VS Code の開発コンテナで作る定義も [`.devcontainer/`](.devcontainer/) にあります。ユーザ名・パス・公開するポートは作者の環境に合わせてあるので、使う時は書き換えてください。

---

## クイックスタート

```bash
# ラボを 1 問
scripts/lab.sh provision ENCOR-OSPF-01      # 構築・起動・lab/ENCOR-OSPF-01/ に課題文
#   → ワークスペース / CML コンソール / SSH で解く
scripts/lab.sh grade ENCOR-OSPF-01          # 採点
scripts/lab.sh teardown ENCOR-OSPF-01       # 片付け

# 紙面パック
scripts/pack.sh new                         # 今日の 3 パックを作る（ラボの構築も含むので時間がかかる）
scripts/pack.sh serve                       # http://<制御ホスト>:8899/ で解く
scripts/pack.sh grade --today --no-lab      # 紙面を採点して解説ページを出す
scripts/pack.sh close --today               # ラボを片付ける

# 教材コース
scripts/course.sh xr build                  # ポータルの棚に載せる
scripts/lab.sh provision XRT-01 && scripts/lab.sh learn XRT-01   # 学習ラボ
```

`lab.sh` を使わずに手で回す場合:

```bash
V="--vault-password-file <(printf 'CCNP\n')"
ansible-playbook playbooks/build_topology.yml -e problem=<ID> [-e variant=<v>] [-e node_image=iosv] $V
ansible-playbook playbooks/lab_up.yml         -e problem=<ID> $V          # 停止/撤去: -e lab_state=stopped|absent
ansible-playbook playbooks/grade.yml          -e problem=<ID> $V          # -e max_attempts= -e settle_delay= で収束調整
```

> **複数ラボの同時稼働に対応**しています。管理 IP は `topologies/mgmt_alloc.py` のリース台帳（`_state/mgmt_leases.json`）が first-fit で割り当てるので、旧ラボを撤去せずに新ラボを起動しても管理 IP は衝突しません。teardown 漏れは `mgmt_alloc.py gc` で回収できます。
>
> 同時稼働の上限は**環境に依存**し、コードに定数はありません。実質は次の 2 つで決まります。
> 1. **管理 IP プールの大きさ** = `local.yml` の `mgmt_pool` の要素数。足りない時だけ割り当てを止める（要求ノード数 > 空き IP 数 → rc=2、CML には触らない）。
> 2. **CML の同時起動ノード数** = CML のライセンスの制約（例: Personal は 20 ノード）。超えた分は CML が拒否する。

---

## ディレクトリ構成

```
CCNP01/
├── CLAUDE.md                    # Claude Code で回す時の運用ルール
├── .claude/skills/quiz/         # 出題フロー（/quiz スキル）
├── .devcontainer/               # 制御ホストの開発コンテナと依存の一覧
├── ansible.cfg / inventory.yml  # 接続設定・名前とグループだけ（管理 IP は動的に割り当て）
├── group_vars/ host_vars/       # 接続変数・device_profiles・vault / local.yml（環境依存・gitignore）
├── roles/baseline/              # day0 の baseline テンプレート
├── playbooks/                   # build_topology / lab_up / grade（+ _grade_attempt*）ほか
├── topologies/
│   ├── gen_cml_lab.py           # problem.yml → CML ラボ YAML
│   ├── grade.py + netmodel.py   # 採点エンジン（Genie で構造化 / ネット全体の不変条件）
│   ├── gen_*.py                 # 生成器（ラボ・紙面・パック・読み物）
│   ├── *_model.py               # 意味の評価器（ACL・BGP 最良経路・STP・経路表など。採点・紙面・ゲームが使う）
│   ├── clab_ops.py              # containerlab の deploy / destroy / exec
│   ├── lab_console.py           # ラボのワークスペース
│   ├── pack_server.py           # ポータルと配信サーバ
│   ├── units.yml / lab_modes.yml   # 単元とローテーションの定義
│   ├── *_ops.py                 # 大型シナリオの構築・運用ヘルパ
│   ├── conventions.md           # 採番・配線・命名の規約
│   └── _generated/ _state/      # build の中間物・台帳（gitignore）
├── problems/<ID>/               # 1 問 = 1 ディレクトリ
│   ├── CATALOG.md / _history.md # 出題可の一覧 / 出題の記録
│   └── _drafts/                 # 設計メモ（BACKLOG.md からリンク）
├── questions/ answers/          # 紙面の問題と答え（questions/en/ は英訳）
├── courses/                     # 書き下ろしの教材（xr/・junos/）
├── glossary/                    # 教材の用語集の辞書
├── games/                       # 学習ゲームの画面とステージ定義
├── curriculum/                  # 単元の補足と参照ソース
├── records/                     # 学習の記録（attempts.jsonl・学習モードの記録）
├── poc/<テーマ>/                # 作問前の PoC（実機検証のログ・試行スクリプト）
├── scripts/                     # lab.sh / pack.sh / course.sh / read.sh / quota.sh
├── BACKLOG.md / CURRICULUM.md   # 課題の台帳 / 単元ごとの到達度の台帳
└── lab/ packs/ reading/         # provision・パック・読み物の出力（gitignore）
```

---

## 問題ディレクトリの仕様

1 問 = `problems/<ID>/` の自己完結したディレクトリです。

| ファイル | 役割 |
|---|---|
| `problem.yml` | メタ（id / exam / topics / difficulty / target_nodes / points）＋ `lab.links`（配線。a_if / b_if は slot 番号） |
| `task.md` または `task.md.j2` | 受験者向けの問題文（日本語）。`.j2` は params で数値が変わる |
| `task.en.md` | 英語の問題文（教材コースの学習ラボなど） |
| `initial/<NODE>.cfg.j2` | 出題時に重ねる「穴あき」config |
| `grading.yml` または `grading.yml.j2` | 採点基準（フィールドを判定する形式） |
| `grading.<名前>.yml` | 途中の確認用の採点基準（`lab.sh checkpoint`・学習モードの「確認」） |
| `learn.yml` | 学習モードの中身（課題ごとの確認・段階式ヒント・確かめ方の例） |
| `solution.md` | 模範解答 |
| `params/` | パラメータ化（`base.yml` 既定値 + `_gen.yml` ランダム化スキーマ） |
| `controller/` `controller_solution/` `blanks.yml` | 自動化ラボ用の穴あき workspace と完成形 |
| `clab/` | containerlab のトポロジ（`*.clab.yml`）と初期設定。`problem.yml` の `platform: clab`・`clab_nodes`・`clab_topology` と組で使う |

### パラメータ化（値違いの問題の量産）

`initial/grading/task` を `.j2` にして `{{ params.xxx }}` を参照します。`-e variant=<name>`（既定 `base`）で値を切り替えます。
ランダムな生成は `gen_params.py --problem <ID> --seed N` → `params/sN.yml`（同じ seed = 同じ値 = 再現できる）。

---

## 採点の仕組み（`grade.py` / pyATS Genie）

- `show` 出力を Genie で**構造化** → `find`（glob でオブジェクトを選ぶ）+ `match`（同じオブジェクトの上でフィールドを照合）で判定。配点は all-or-nothing。
- `grade.yml` が **全 PASS か max_attempts まで、settle_delay 秒おきにリトライ**（収束待ち）。
- Genie のパーサが無い・壊れる箇所は **`raw:` の正規表現**（contains / not_contains / regex …）で判定。「特定の経路だけ無い」「単一経路化（ECMP の排除）」「能動 ping の成否」もこれで表す。
- `netmodel.py` = ネット全体の**大域不変条件**（ループが無い / 最適 / 到達できる）を採点する別系統。
- 集め方は `problem.yml` の `access:` で分かれる: `ssh`（既定）/ `telnet`（IOL の L2 スイッチ）/ `console`（IOSv など）。containerlab のノードは SSH（Junos・EOS）か `docker exec`（FRR）。

`grading.yml` の例:
```yaml
defaults: { genie_os: iosxe }
checks:
  - name: "RT01-RT02 OSPF 隣接 FULL"
    node: RT01
    command: show ip ospf neighbor
    parser:  show ip ospf neighbor        # command=実機へ送る文字列 / parser=Genie のキー（別物）
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

## 規約（要点。詳細は [conventions.md](topologies/conventions.md)）

- **命名**: `RTxx` = router / `SWxx` = switch（接頭辞で役割を判定）。CML のラボ名は `CCNP-LAB-<md5(id)[:8]>` で**中身が分からない名前**にする（画面に技術名が出て解き方が割れるのを防ぐ）。
- **採番**: Loopback0 = `x.x.x.x/32`（RT01 → 1.1.1.1）。ルータ間 = `10.1.<a><b>.0/30`（小さい番号の側が .1）。
- **イメージ**: トポロジ単位でそろえる。優先は `CLI -e node_image` > `problem.yml` > グループの既定。物理 IF 名は device_profiles で論理と物理の違いを吸収する。

---

## 運用上の落とし穴

- **baseline の末尾に `end` を置かない**（day0 は baseline と initial をつなげたもの。途中の `end` から後ろが無視される）。
- **IOL はリンクダウンを対向に伝えない**（片端を shutdown しても対向の line protocol は up のまま）。フェイルオーバの設計は、対向のリンクダウンの検知に頼らないこと。
- **VLAN の多い L2 の盤面は IOSvL2 で組む**（ioll2 では BPDU が欠けることがある）。
- `raw` の採点は IOS のコマンドの省略形・別表記に弱い → 各語を `<最短プレフィクス>[\w-]*` で緩める。
- `task.md.j2` にリテラルの `{{ ____ }}` を書くと、描画器が変数とみなして失敗する → `{% raw %}…{% endraw %}` で囲む。
- 採点のチェックが多く **2 分を超える**問題は、実行ツールの timeout を上げる。

---

## ライセンス / 免責

学習・作問目的の個人プロジェクトです。Cisco・Juniper・Arista・Fortinet などのイメージは、各自が正規に入手し、ライセンスに従って使ってください（本リポジトリにイメージは含みません）。
