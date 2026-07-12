# FGT-REPLACE-01 模範解答・解説（受講者非公開）

模範 config 全文 = [poc/fortigate/golden-replace-fgt.cfg](../../poc/fortigate/golden-replace-fgt.cfg)
（fgtreplace_ops.py solve が投入するもの）。

## Phase 1 の答え（現行 ASA の要件表）

| # | 通信 | 根拠 |
|---|---|---|
| 1 | inside→outside 全サービス（送信元は 2.2.2.10 に PAT） | SL 100→0 暗黙許可 + OBJ-TRUST-NET の nat dynamic |
| 2 | outside→公開サーバ の ICMP と HTTP のみ | ACL OUTSIDE-IN 2行（宛先は**実 IP** 172.16.250.1 = 8.3+ 仕様・NAT が ACL より先に評価される） |
| 3 | inside→dmz 全サービス | SL 100→50 暗黙許可（**ACL には現れない**＝移行漏れの罠） |
| 4 | dmz→outside 全サービス | SL 50→0 暗黙許可（新環境では要件外とし移行しない — 縮小仕様） |
| 5 | dmz→inside 遮断 | SL 50→100 は暗黙 deny |

- NAT: ①172.16.250.1⇔2.2.2.1 の 1:1 static ②172.16.100.0/24→2.2.2.10 の PAT
- route: default 以外の3本は L3SW/LB 向け → 新環境は connected 化で **default 1本**
- failover ブロック・standby IP・monitor-interface: **移行対象外**（FGT 1台構成。
  FGT で実現するなら FGCP HA — 本ラボの eval ライセンスでは組めない）

## 概念対応表（Phase 2 の答え）

| ASA | FortiGate |
|---|---|
| security-level 暗黙許可 | **存在しない** → ゾーン間ごとに明示ポリシー |
| access-list + access-group | firewall policy（IF ペア + src/dst/service） |
| object network + nat static | **VIP（1:1・port-forward にしない）** |
| object network + nat dynamic（PAT アドレス） | **ippool** ＋ policy で `set ippool enable` |
| inspect icmp | 不要（FGT は既定で ICMP もステートフル管理） |
| failover | FGCP HA（本環境では移行対象外と判断するのが正） |
| ワンアーム dot1q ×3 | 3物理ポート（eval は VLAN サブ IF 不可・新環境仕様） |

## 設計の要点と落とし穴

| 要素 | 解 | 落とし穴 |
|---|---|---|
| VIP SRV-VIP | extip **2.2.2.1**（オフサブネット）・mappedip 172.16.10.10・**1:1** | port-forward tcp80 で作ると **G4（ping 2.2.2.1）が落ちる**（ACL permit icmp の移行漏れ）。オフサブネット extip は ISP1 の `2.2.2.0/28 → 203.0.113.2` 静的経路で成立（据付・day0 済） |
| ippool SNAT-POOL | 2.2.2.10 単一・policy 1 で `set ippool enable` + poolname | `set nat enable` だけだと送信元が port1 IP（203.0.113.2）になり**現行 PAT 仕様と不一致**（S6 で検出。G1/G2 は通ってしまう — 設定チェックで拾う設計） |
| policy 3 LAN→DMZ | 明示的に作る | **最頻出の移行漏れ**: ASA では SL 暗黙許可で通っていたため config 上に痕跡が無い。観察3-1 で体験させる |
| dmz→outside | 作らない（縮小仕様） | ASA では SL50→0 で通っていたが、DMZ-SRV に外向き要件が無いため「開けない」が正（要件5・考察5-3 の種） |
| route | default 1本 | ASA の route inside/dmz 3本を写経すると無意味な静的ルートが残る（S9 の思想。eval は route 3本上限もある） |

## session テーブルの実機指紋（Phase 4 の答え合わせ用・2026-07-12 採取）

```
hook=post dir=org  act=snat 10.1.10.12:2254->198.51.100.100:8(2.2.2.10:7371)   ← 観察4-2
hook=pre  dir=org  act=dnat 198.51.100.100:2254->2.2.2.1:8(172.16.10.10:2254)  ← 観察4-3
```

## 考察課題の解説

- **考察1**: No。inside→dmz を許可する ACL は無い**が通る**（SL 100→50）。
  「ACL が無い＝通らない」ではないのが ASA。この Yes/No を Phase 3 で覆される
  （FGT では No になる）体験が本問の背骨。
- **考察2-1**: failover 系（FGCP は別途設計が必要・本環境は1台）と inspect icmp
  （FGT は既定ステートフル）。standby IP も HA 前提なので対象外。
- **考察2-2**: 1本（default のみ）。inside/dmz が FGT の connected になるため。
- **考察3**: ACL に `permit icmp any host 172.16.250.1` がある＝ICMP も公開要件。
  port-forward は指定 L4 ポートしか変換しない → 1:1 VIP が正。
- **考察5-1**: 入れていない。FGT はセッションテーブルで ICMP echo/reply を対で
  管理するのが既定動作（ASA は inspect icmp を入れて初めて同等になる）。
- **考察5-2**: 安全になった点=暗黙許可が消え、許可が全てポリシーに明文化された
  （監査可能性）。後退した点=HA が無くなり FW が単一障害点になった。
- **考察5-3**: 「開けていないはずの通信が通らないこと」の試験。例: 外部→2.2.2.1 の
  HTTP/ICMP **以外**（ssh 等）が落ちること、DMZ→外部が落ちること（要件5 の検収）。

## 採点上の注意（出題者向け）

- ポリシー ID 依存（S6/S7/S8）・ID ずれ時は grade_input.json を目視
- G4 が port-forward 解の検出器 / S6 poolname が nat enable 素通し解の検出器
- E1 は複合チェック（負の要件を単独採点しない）
- 採点は単段・約3分。`fgtreplace_ops.py grade`
