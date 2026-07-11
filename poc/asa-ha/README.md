# ASAv HA × ワンアーム構成 PoC (BL-041) — 結果 (2026-07-10)

ユーザ構想「トポロジーをワンアーム構成にしつつ FW を HA」の前提検証。
**全プローブ成功 → 出題化（構築問/TS/CAMPUS-TS 拡張）へ進める**。

## 検証環境（poc-asaha-lab.yaml・5台・console専用・リース不要）

```
        RT01(IOL, VLAN100 .1)      RT02(IOL, VLAN200 .1, telnetサーバ)
              \                      /
               [SW01 iosvl2 (vtp transparent)]
              trunk(100,200)   trunk(100,200)
               /                     \
   fw1 Gi0/0(ワンアーム)         fw2 Gi0/0(ワンアーム)
     Gi0/0.100 = outside .254 (standby .253)
     Gi0/0.200 = inside  .254 (standby .253)
   fw1 Gi0/1 ────────────────── fw2 Gi0/1   ← failover+state 共用リンク(FOLINK)
```

## プローブ結果（全✅・実機）

| # | 検証項目 | 結果 |
|---|----------|------|
| P1 | **unlicensed(デモ) で failover 有効化** | ✅ `Failover On`・エラー/ライセンス警告なし（最大の不確定要素を解消） |
| P2 | **ワンアーム転送**（1物理アームに dot1q サブIF ×2） | ✅ RT01→RT02 ICMP 100%・telnet 確立。iosvl2 トランク⇔ASA サブIF は素直に動作 |
| P3 | **config 自動複製** | ✅ セカンダリは **bootstrap 9行のみ**で hostname/サブIF/ACL 全て Active から複製・`Standby Ready` 到達 |
| P4a | 切替の断時間 | ✅ **ping 損失 0/60（1秒粒度で断ゼロ）**。`failover active` によるスイッチオーバー |
| P4b | **ステートフル引き継ぎ** | ✅ 張りっぱなし telnet セッションが切替を**生存**（resume 後に操作成功）。standby の `show conn` に複製 conn（flags UB）を事前確認 |
| P4c | virtual MAC / GARP | ✅ GW の ARP は virtual MAC のまま Active 側に追従（CML の L2 で問題なし） |

## ★実機知見（出題・自動化に直結）

1. **failover は unlicensed で完全動作**（Failover On / ペア形成 / 複製 / 切替 / ステート同期）。
   100Kbps スロットルは HA 機能自体には無関係
2. **セカンダリ投入は 9 行**（`failover lan unit secondary` + FOLINK 定義 + key + `failover`）。
   ASAv day0 不発問題の影響が最小になる構成 = HA はむしろ bootstrap 方式と相性が良い
3. **複製後は両ユニットとも hostname が同一**（例: fwha）→ コンソール自動化は
   ホスト名でユニットを識別できない。`show failover | grep This host` で判別するか、
   `prompt hostname priority state` の導入を検討
4. サブIFは既定で **Not-Monitored**（`show failover` に明示）→ `monitor-interface outside`
   を入れないとアーム断でも切り替わらない。**そのまま TS 故障ネタになる**
5. bootstrap 順序: ①primary へフル config＋`failover`（Active 化）→ ②secondary へ 9 行
   → 自動複製（リロード不要・1分弱で Standby Ready）
6. failover key も 8 字ポリシー対象（`CCNPccnp` で統一）
7. 切替履歴は `show failover history` が綺麗に残る（Just Active→Active Drain→…）＝採点/解説素材

## 出題ネタ（確定候補）

- **構築問**: ワンアーム HA ペアの組み立て（サブIF/standby IP/FOLINK/key/monitor-interface）
- **TS問**: ①failover key 不一致（ペア不成立） ②standby IP 欠落（切替後だけ通信断）
  ③monitor-interface 未設定（アーム断でも切り替わらない＝「冗長のはずが片系断で全断」）
  ④FOLINK 断のスプリットブレイン ⑤unit primary/secondary 旗の重複
- **CAMPUS-TS-01 拡張**: asa1→HA ペア化(+1ノード=15オブジェクトで20上限内)・F6 系故障追加

## 再現手順

1. `python3 poc/asa-ha/ha_tools.py up` → `wait`（5台・約4分）
2. `ha_tools.py bootstrap fw1`（フル config＋failover）→ `bootstrap fw2`（9行）
3. 検証: `ha_tools.py cmd fw1 "show failover"` / RT01→RT02 ping・telnet /
   fw2 で `failover active` → 断時間・セッション生存を観測
4. 片付け: `ha_tools.py down`
