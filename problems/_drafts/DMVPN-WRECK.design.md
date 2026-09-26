# DMVPN TS「壊滅スタート」モード（BL-208）

起票 2026-09-21。発端= ユーザの ENARSI 本試験所感（DMVPN TS が極端に難しかった）。

## 1. 観察（本試験・言い回しでなく状況の型のみ）

- 初回から hub の `show dmvpn` にスポークが 1 台も出ていない。
- 欠落・誤りが hub と一部の spoke に散在:
  ipsec profile 未定義（→ tunnel protection も無い）／`ip nhrp network-id` なし／`tunnel key` なし／
  `tunnel destination` が設定されている／`ip nhrp map multicast dynamic` なし／一部 spoke に `crypto isakmp key` なし。
- 上記を全部潰すと ISAKMP SA は active になったが、hub の `show dmvpn` には依然 1 台も上がらない（最後の 1 層が残る）。
- spoke の `show dmvpn` には hub が static で見えていた（設定として見えていただけ）。
- 暗号は **IKEv1**（`crypto isakmp key` / `show crypto isakmp sa`）。

## 2. 方針

- 既存 `gen_dmvpn_ts.py`（IKEv2・IOSv・console 採点・最大 2 故障）は触らず、**新生成器 `gen_dmvpn_wreck.py`**（IKEv1・IOL・SSH 採点）。
- 初期状態= 欠落カタログから hub/spoke に散らして 6〜8 か所＋**最後の 1 層**（見える欠落を全部埋めても ISAKMP active・登録不成立が残る）を 1 つ。
- 盤面= IOL 5 台（HUB・SPOKE×3・ISP）。ISP は変更禁止。ISP の Lo に「インターネット」ホスト。
- 採点= hub の `show dmvpn` に全 spoke が UP／spoke 間 shortcut／暗号化カウンタ／EIGRP 経路／（オプション）フルトンネル。

## 3. PoC 項目（poc/dmvpn-wreck/sweep.py・結果は results-raw.md → README.md）

| ID | 内容 | 知りたいこと |
|---|---|---|
| P0 | 健全形（IKEv1・Phase 3・EIGRP）の基線 | 各 show の正常形 |
| P1 W* | 欠落カタログを 1 つずつ注入 | hub/spoke の `show dmvpn`・`show crypto isakmp sa`・`show crypto ipsec sa`・`show ip nhrp nhs detail`・ログの指紋 |
| P1 F* | 最後の 1 層の候補 | **ISAKMP は active なのに登録されない**が成立するもの（transform/PFS 不一致・ESP 遮断・NHRP 認証・NHS 誤り・nhs 無しの static map・mode gre ip 残り・protection 変更後の自動 shutdown） |
| P2 | 全部入りを day0 → 自然な順で是正 | 是正後に bounce/clear 無しで登録されるか（されないなら何が要るか） |
| P3 | フルトンネル（spoke → hub 折返し → NAT → インターネット） | IOL で成立するか。素朴な構成（spoke の既定経路をトンネルへ）と underlay の再帰の関係・FVRF 版 |

## 4. 結果(2026-09-21)

- PoC 全 22 ケース= [poc/dmvpn-wreck/README.md](../../poc/dmvpn-wreck/README.md)。
- 生成器 `topologies/gen_dmvpn_wreck.py` 完成。欠落 11 種(hub 6・spoke 5)を 6〜8 か所+最後の 1 層 6 種
  (f_nhs_static / f_tkey_typo / f_esp_acl / f_pfs / f_mode_tunnel / f_auth_typo)。hub 側 or 全 spoke に入れて「hub に 1 台も上がらない」を保証。
- 採点 13 チェック(hub 登録 25・ISAKMP 10・ESP 10・EIGRP 10(★Q Cnt 0 まで見る)・ping 15・shortcut 10・仕様 20)。
- E2E: 31701(最後= nhs 欠落)2 → 30 → 100 / 40021(最後= mode tunnel)5 → 30 → 100。どちらも最後の 1 層だけ残した状態で
  「ISAKMP QM_IDLE・hub 空」を再現。最後の 1 層の是正は bounce/clear なしで復旧。
- フルトンネル(IOL・DMVPN)は素朴構成でも成立 → crypto map 版は BL-209 へ。
