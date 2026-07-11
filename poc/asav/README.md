# ASAv 導入 PoC (BL-038) — 結果 (2026-07-10)

超大作3層キャンパスラボ問（IOSv+IOSvL2+ASAv・指示書待ち）の前提検証。
asav-9-22-1-1 を CML 2.8.1 で実戦投入できるかを実機確定した。
**結論: 出題可。ただし day0 注入は不発 → console bootstrap 方式を正式採用**。

## 検証環境（poc-asav-lab.yaml・3台・console+SSH）

```
RT01(inside 10.99.1.2) ── FW01(ASAv 9.22) ── RT02(outside 10.99.2.2)
  Lo0 192.168.1.1 ←static NAT→ 10.99.2.100      Lo0 198.51.100.1(疑似Internet)
  Lo1 192.168.2.1 ←dynamic PAT→ outside IF
MGMT: FW01=.11 RT01=.12 RT02=.13（mgmt_alloc リース・検証後解放済）
FW01: Management0/0(management-only) / Gi0/0=inside(100) / Gi0/1=outside(0)
```

## 検証マトリクス（全6テスト ✅・2026-07-10 実機）

| # | テスト | 結果 |
|---|--------|------|
| 1 | inside→outside: dynamic PAT ＋ icmp inspection | ✅ 100% (10/10) |
| 2 | inside→outside: static NAT 経由 | ✅ 90%（初発ARPのみ損・正常） |
| 3 | outside→マップIP 10.99.2.100 icmp（ACL許可） | ✅ 100%・hitcnt=10 |
| 4 | outside→10.99.2.100 telnet（static NAT 越し RT01 ログイン） | ✅ 確立 |
| 5 | outside→10.99.2.100:22（ACL 対象外） | ✅ 遮断 |
| 6 | outside→実IP 192.168.1.1 直撃 | ✅ 不達 |

採点シグネチャ: `show access-list`（hitcnt）/ `show xlate`（`flags s` = static、
`flags ri` 系 = PAT）/ `show conn` / `show nat detail`。**いずれも Genie パーサ無し
→ raw regex 判定**（本リポの確立手法）。

## ★罠カタログ（実機確定・作問/運用に直結）

1. **day0 config 注入は不発**。CML への保存・ISO 生成/マウント（boot log で
   `cdrom device /dev/hdb found`）までは正常だが ASAv が読まない。原因は
   ベース qcow2 が**イメージ作成時に一度ブート済み**（disk0 に `use_ttyS0`
   2024-10-12 付が存在＝シリアルコンソール化マーカー投入のため）で、ASAv の
   day0 読込条件「真の初回ブート」が消費済みのため。
   → **代替 = asav_bootstrap.py**（lab yaml の configuration を console 経由で投入）。
   なお カスタム node def（ISO 内ファイル名 day0-config 化）での検証は
   image def が dropfolder 制約で複製不能なため断念。
2. **パスワード最低8文字**（9.22 強制）。プロジェクト標準 `CCNP` は enable/
   username/初回ウィザード全てで拒否 → **ASA だけ `CCNPccnp` 規約**。
   初回 enable 時に対話ウィザード（Enter/Repeat Password）が出る点も自動化で処理要。
3. **ACL は実IP（8.3+ NAT との併用）**。outside ACL で static NAT 対象を許可する
   際は**マップIP(10.99.2.100)ではなく実IP(192.168.1.1)** を書く。マップIPで
   書くと無言で全落ち（本PoCで実測 0/10）。**そのまま難4-5 の出題ネタになる**。
4. **SSH は初回ブートでは上がらない**（CiscoSSH スタックが起動時 RSA 鍵不在で
   sshd 起動失敗 → Connection refused）。**復旧手順 = `crypto key generate rsa
   modulus 2048` → `write memory` → `reload`**。reload 後は正常 listen。
   レガシー版 `no ssh stack ciscossh` はこのイメージにファイルが無く ERROR。
5. **ホスト鍵は ssh-rsa** → 現代 OpenSSH クライアントは
   `-o HostKeyAlgorithms=+ssh-rsa` が必要（IOS 同様の古い鍵問題）。
6. **`aaa authorization exec LOCAL auto-enable`** で privilege 15 ユーザの SSH が
   priv exec 直行 → SSH 採点はこれを前提にする（無いと `>` 止まりで show 系不可）。
7. **ICMP 通過には `inspect icmp` 必須**（global_policy へ追加。無いと inside→
   outside の echo-reply が戻らない）。class-map/policy-map/service-policy の
   投入は console 流し込みで問題なし（既定 policy にマージされる）。
8. **unlicensed = 100Kbps スロットル**（起動時 Warning 表示）。接続性・設定採点は
   問題なし。**スループット系採点（QoS 体感等）は不可**。
9. Genie ASA パーサは 24 コマンドのみ（`show nameif` / `show route` /
   `show interface ip brief` / `show service-policy` / `show failover` /
   `show crypto ikev2 sa` 等）。**NAT/xlate/conn/ACL 系は無い → raw 判定**。
   CML 自動生成 testbed は FW ノードに `os: asa` を付与（unicon asa プラグイン可）。
10. CML の config 抽出（`extract_configuration`）は動くが **パスワード類は
    `***** pbkdf2` にマスク**される（初期 config の往復再利用には使えない）。
11. リソース/挙動: 2GB/1vCPU・vmxnet3。**STARTED→BOOTED 約3.5分**・reload 約2分。
    IF は slot0=Management0/0、slot1〜=Gi0/0〜（最大8IF+Mgmt）。
12. `write memory` 済み config は**ノード再起動（reload/stop-start）で保持**
    される（wipe すると消える）。bootstrap は provision 時 1 回で済む。

## 出題タイプ別の適性（超大作への織り込み）

- **構築問**: inside/outside/dmz の nameif+security-level、object NAT（PAT/static）、
  outside ACL（実IP罠）、inspect icmp — いずれも採点シグネチャ明確で適性◎
- **TS問**: ACLマップIP故障 / inspect icmp 欠落 / nameif 未設定 / security-level
  同値+same-security 未許可 / NAT 順序 — day0 でなく bootstrap 投入なので
  故障焼き込みも同スクリプトで可
- **不適**: スループット体感系（ライセンス 100Kbps）・ASDM 系

## 再現手順

1. リース: `python3 topologies/mgmt_alloc.py allocate --repo . --problem POC-ASAV --nodes FW01,RT01,RT02`
2. 投入: virl2_client で poc-asav-lab.yaml を import + start（FW01 BOOTED まで約3.5分）
3. **ASA bootstrap**: `python3 poc/asav/asav_bootstrap.py`（yaml の configuration を
   console 投入・ERROR 行を報告）→ console で `crypto key generate rsa modulus 2048`
   → `write memory` → `reload noconfirm`（SSH 有効化）
4. 検証: SSH `ssh -o HostKeyAlgorithms=+ssh-rsa SUZUKI@10.1.10.11`（auto-enable で
   priv 直行）または console（asav_console.py）。IOS 側は従来通り
5. 片付け: ラボ stop/wipe/remove → `mgmt_alloc.py release --repo . --problem POC-ASAV`

## 本実装(問題化)時の宿題

- provision フロー統合: lab_up 後の ASA bootstrap ステップ（asav_bootstrap.py の
  汎用化: ラボ名/ノード名/config をパラメタ化、鍵生成+reload 込み・冪等化）
- collect_console.py の ASA 対応（`terminal pager 0`、enable ウィザード、
  unicon os=asa は testbed 済みなので流用可能見込み）
- device_profiles への asav family 追加（FW* 接頭辞 → 新 role、mgmt=Management0/0
  slot0、links=Gi0/0〜）と role_of() 拡張
- grade.py: ASA 用 raw 判定チェック種（hitcnt / xlate flags / conn 数）
