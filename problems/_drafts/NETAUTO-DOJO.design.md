# NETAUTO 道場 設計メモ — NETCONF/RESTCONF/Python 自動化コース（初級から）

状態: **N3 完了・残り N1/N2/N4/N5 未着手**（BACKLOG BL-008〜BL-011）。開始 2026-07-08（ユーザ承認）。

## コース方針（Ansible道場と同思想）

- 題材は毎回ごく簡単な固定ゴール（Loopback 1本など）。**変わるのは自動化の技術だけ**。
- 出題形式は難度で柔軟: 穴埋め（`blanks.yml` でseedランダム化）→ 足場を減らす → ゼロ記述。
- 採点は従来どおり **機器の最終状態のみ**（手段非依存）＝ grade.yml 無改修で流用。
- ID規約: `NETAUTO-NN-<TECH>`（NNはカリキュラム番号で固定。作成順ではない）。

## カリキュラムと各レッスンの設計スケッチ

| # | ID(予定) | 技術 | 機器 | 状態 |
|---|----------|------|------|------|
| N1 | NETAUTO-01-NETMIKO | Python+netmiko で show収集→設定投入 | IOL 3台（軽い・既存 baseline-8rt 流用） | 未着手 |
| N2 | NETAUTO-02-DATA | JSON/YAML/Jinja2 の読み書き | **ラボ不要（オフライン）** | 未着手 |
| N3 | NETAUTO-03-RESTCONF | RESTCONF（curl→requests GET/PUT） | cat8000v ×1 | ✅完了(2026-07-08 実機100点) |
| N4 | NETAUTO-04-NETCONF | NETCONF（ncclient get-config/edit-config） | cat8000v ×1 | 未着手（次の作成候補） |
| N5 | NETAUTO-05-PYATS | pyATS/Genie で状態取得・差分検知 | 任意（IOLで可） | 未着手 |

### N1: NETAUTO-01-NETMIKO（難1-2）

- **前提作業: `.venv` に netmiko を pip 追加**（現状未導入。ncclient/requests/pyATSは導入済）。
- 内容: `ConnectHandler(device_type="cisco_xe", ...)` の接続パラメータ穴埋め →
  `send_command("show ip interface brief")` → `send_config_set` で Lo に description。
- 題材マーカー例: `description MANAGED-BY-NETMIKO`。採点は ANSIBLE-01 と同型（raw contains ×3台）。
- 教育核心: SSH自動化の最小形。network_cli(Ansible) との対応関係、show=文字列が返るだけ（構造化はN5への伏線）。

### N2: NETAUTO-02-DATA（難1-2・ラボ不要）

- 内容: 機器リスト(YAML) → Python で読み込み → Jinja2 テンプレートで config 断片生成 →
  JSON で保存。正解ファイルとの一致で自己採点（grade.yml 不使用 or shell採点）。
- Ansible道場 T2(08/09/10) のオフライン可レッスンと同ポジション。CMLノード0台なので隙間時間向け。
- 採点方式は要設計: 生成物ファイルの diff 判定（gen_blanks の「埋め戻し==solution」検証と同じ発想）。

### N4: NETAUTO-04-NETCONF（難2-3）— 次の作成候補

- 内容: STEP0 コンソールで `netconf-yang` 有効化 → ncclient で `get_config(source="running")` →
  subtree filter で ietf-interfaces を絞る → `edit_config` で Loopback 作成（N3と同じ題材で対比）。
- **N3 との対比が教育核心**: 同じ YANG モデル(ietf-interfaces)を XML+SSH(830) で操作。
  RESTCONF=HTTP動詞 / NETCONF=RPC(edit-config, candidate/running) の違い。
- 実機で要検証（N3 の RESTCONF 検証と同型の癖が想定される）:
  - `netconf-yang` 投入後のデーモン起動待ち（RESTCONF は約1分だった）
  - **MGMT VRF 越しの 830/TCP**（RESTCONF/443 は素通りだった。NETCONF も要確認）
  - ncclient 接続パラメータ: `device_params={"name": "csr"}` or `iosxe`、`hostkey_verify=False`
- 問題パックは NETAUTO-03 のコピーから作るのが最短（problem.yml の image_family: cat8000v、
  initial、grading の骨格を流用。マーカーは CONFIGURED-BY-NETCONF に変える）。

### N5: NETAUTO-05-PYATS（難3）

- 内容: 採点系で使っている pyATS/Genie を学習者側に降ろす。`device.parse("show ip route")` で
  構造化 → before/after の差分検知（例: 設定変更前後で Genie Diff）。
- testbed.yml の書き方（採点側の grade 入力と同じ流儀）＋ IOL で可（SSH+iosxe パーサ実証済）。
- 発展: 「意図した経路があるか」を assert する簡易ネットワークテスト＝大域不変条件グレーダ(netmodel)の入口。

## N3 で確立した基盤（再利用可・実機実証済）

- **device_profiles.cat8000v.router**（group_vars/all/main.yml）: node_definition=cat8000v /
  image=cat8000v-17-15-01a / RAM4096・1vCPU / slot0=Gi1 平置き命名 / mgmt=GigabitEthernet4(slot3)。
  problem.yml に `image_family: cat8000v` と書くだけで選択される。
- **baseline の SSH鍵EEM**: `image_family in ['iosv','cat8000v']` で watchdog(90s)型 → cat8000v 実機OK。
- **RESTCONF の癖**: 有効化(`restconf`+`ip http secure-server`+`ip http authentication local`)後、
  デーモン起動に約1分（その間 nginx の HTML エラーページ）。MGMT VRF 越し 443 は素通り。
  PUT は 201(新規)/204(更新)。採点で `ip http secure-server` を contains で見ると
  `no ip http secure-server` にも一致 → 行頭アンカー regex 必須。
- ブート時間: provision 完了(BOOTED)→ping→SSH まで数分。1台構成なら CML Personal 20ノード上限にも優しい。

## 関連

- メモリ: ccnp-netauto-dojo / ccnp-automation-lab-workflow / ccnp-cml-env
- 完成例: problems/NETAUTO-03-RESTCONF/（穴埋め・grading・task の雛形として流用可）
