# DMVPN Phase3 + IKEv2 完全版 PoC (BL-006) — 結果 (2026-07-09)

DMVPN-IPSEC.design.md の Phase 1。IOSv (iosv-159-3-m9) 上で
**mGRE + tunnel protection + IKEv2 wildcard PSK** のベースライン成立と、
故障カタログの「成立性が疑わしい故障」の症状を実機確定した。
**baseline は day0 一発で全項目成立 → 実装(構築問＋gen_dmvpn_ts.py)へ進める**。

## 検証環境（poc-dmvpn-ipsec-iosv-lab.yaml・4台 IOSv・console）

```
RT01(Hub 1.1.1.1) ─┐
RT02(Sp1 2.2.2.2) ─┼─ RT04(WAN transit・/30×3)   overlay: Tunnel0 10.255.0.0/24
RT03(Sp2 3.3.3.3) ─┘                              EIGRP AS100 / NHRP id1 / tunnel key 100
IKEv2: AES-GCM-256/PRF SHA384/DH19・wildcard keyring・ESP transport・PSK共通1本
MGMT: .18/.19/.20/.31 (mgmt_alloc リース・検証後解放済)
```

day0 = 模範解答ベースライン（本 yaml がそのまま構築問の解答仕様＝生成器の正解 config）。

## baseline 結果（起動一発 ✅ 全成立）

- Hub `show dmvpn`: 2 spokes UP(D) / IKEv2 SA ×2 READY（**Encr: AES-GCM, keysize: 256,
  PRF: SHA384, DH Grp:19** が `show crypto ikev2 sa` の素の出力に出る → raw 採点容易）
- Phase 3 動作: spoke の対向スポーク経路 next-hop = ハブ（10.255.0.1）のまま、
  ping 誘発で **spoke-spoke 動的トンネル + 動的 IKEv2 SA が双方向に成立**
  （`DT1/DT2` エントリ・`show ip nhrp shortcut` に rib nho・IPsec SA encaps/decaps 増加）
- ESP transport mode: `show crypto ipsec sa` の `in use settings ={Transport, }` で判定可

## 故障カタログの実機確定（★=設計から変更あり）

| 故障 | 結果 | 実機症状（採点シグネチャ） |
|------|------|--------------------------|
| per-peer keyring（wildcard潰し） | ✅採用・難5本命 | hub-spoke 完全正常・**spoke間 ping も 100%通る**（永久ハブ折返し）。traceroute 2ホップ・shortcut 空・`show dmvpn` に **`IX` + `DX`(No Socket)** ペア・spoke間 IKEv2 SA 無し |
| spoke p2p GRE 化 | ✅採用・難4 | 全到達OK・当該 spoke は shortcut 永久不成立。**対向スポーク側に `UNKNOWN <IP> IKE never IX` の残骸**が出る（切り分けの手がかり） |
| tunnel key 不一致 | ✅採用・難4 | **IKEv2 SA は READY のまま** `show dmvpn` State **`NHRP`** 固着・`show ip nhrp nhs detail` に `Registration Request ... expired`。IKE/GRE の層切り分けを強制 |
| NHRP 認証不一致 | ✅採用・難4-5 | **完全サイレント**: hub は Registration Request を受信して黙殺（`debug nhrp error` にも何も出ない・`debug nhrp packet` で受信だけ見える）。spoke State `NHRP`・hub に `IX`。★稼働中注入だと**旧キャッシュで暫く動き続ける**（初回検証で誤って「非故障」判定しかけた）→ **day0 注入なら決定的** |
| tunnel protection 片側欠落 | ✅採用・難3 | hub が平文 GRE を破棄 → 当該 spoke のみ登録不可・EIGRP 消失・IKEv2 SA `DELETE`。もう片方の spoke は正常（対比が効く） |
| ★network-id 不一致 | ❌**非故障確定** | hub=1 vs spoke=99 で登録・shortcut・全通信が正常動作（ローカル有意でワイヤに乗らない）。**故障には使えない** → 「疑わしく見えるが正常」のデコイ/解説ネタに |
| ★mode transport/tunnel 齟齬 | ⚠️動くが仕様違反型 | 不一致時は**両端 Tunnel mode に合意して通信継続**（hub の sa も `{Tunnel,}` に変わる）。不通にはならない → 効果採点（`={Transport,` 判定）でのみ出題可 |
| ★ip mtu 1400 欠落 | ❌**TS故障不成立** | 実効境界は 1472（=1500-28）。1401〜1472 の DF ping が**通ってしまう**（外側 GRE が断片化・DF は外側に複製されない）。「大きいパケットだけ落ちる」は再現しない → **構築問の要件**（run 判定＋ df-bit ping ペア: 正常時 1400 通過/1401 破棄が決定的）に格下げ |

## 生成器設計に効く実機知見

1. **故障は day0 注入が原則**。特に NHRP 系は稼働中注入だと hub の旧キャッシュで
   「動いて見える」偽の非故障になる（本 PoC で実証）。生成器は initial cfg に
   故障を焼き込む方式（既存 gen と同じ）なので問題なし。
2. `show dmvpn` の **State 列と Attrb 列が故障シグネチャの主役**:
   正常 `UP/S,D,DT1,DT2` / GRE・NHRP 不達 `NHRP` / IPsec 不成立 `IKE`+`IX` /
   socket 無し `DX`。raw regex で判定しやすい。
3. IKEv2 スイートは `show crypto ikev2 sa`（detailed 不要）の素の出力に
   Encr/PRF/DH が出る。transport 判定は `show crypto ipsec sa | include settings`。
4. クリア後の再収束は数秒〜十数秒（ping 1回目が落ちることがある）→
   採点は誘発 ping を判定より前に置く（0点発射イディオム踏襲）。
5. 修復判定 ping の直後に `show dmvpn` を取ると動的エントリ形成まで拾える
   （PHASE3-01 の能動 ping 方式がそのまま使える）。
6. `ip nhrp nhs 10.255.0.1 nbma 10.0.14.1 multicast` の現代構文は IOSv 15.9 で有効
   （map 3行構文を書かせる必要なし。故障注入は nbma 値の書き換えで n1 になる）。

## 再現手順

1. リース: `python3 topologies/mgmt_alloc.py allocate --repo . --problem POC-DMVPN-IPSEC --nodes RT01,RT02,RT03,RT04`
   （yaml の mgmt IP/description 内リースを割当に合わせて書き換え）
2. 投入: virl2_client で poc-dmvpn-ipsec-iosv-lab.yaml を import+start（プリフライト ping 込み）
3. 検証: pyATS console (via='a') で show/config 投入（scratchpad/cml_poc.py 相当）
4. 後片付け: ラボ delete → `mgmt_alloc.py release --repo . --problem POC-DMVPN-IPSEC`
