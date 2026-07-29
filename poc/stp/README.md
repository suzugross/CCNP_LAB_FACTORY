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
