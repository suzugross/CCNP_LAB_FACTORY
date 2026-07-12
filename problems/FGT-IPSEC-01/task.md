# FGT-IPSEC-01: マルチベンダ サイト間 VPN — Cisco と FortiGate を IKEv2 で対向させる

本社（FortiGate）と支社（Cisco ルータ）を **サイト間 IPsec VPN** で結びます。
実務で最も緊張するやつ — **メーカーが違う機器同士の VPN interop** です。
ゴールは、両側の設定思想の違いを理解し、**上がらない時に両側からデバッグして
原因を言い当てられる**ようになることです。

★本ラボは**体験型**です。📋観察チェックポイントで実際の出力を記録しながら
進めてください。🤔考察課題の答えは採点後レビューで解説します。
途中で「計画どおりに行かない」場面が仕込まれています — それも課題の一部です。

## トポロジ（あなたが触るのは FGT と RBR の2台）

```
 USER-PC ──[SW]── port3 ┌─────┐ port1          ┌──────┐        ┌─────┐ Gi0/0
 10.1.10.12   10.1.10.0/24│ FGT │───(インターネット: ISP1 ── INET)───│ RBR │
                          └─────┘ 203.0.113.2/30                └─────┘ 198.51.101.2/30
                                                                Gi0/1│ 192.168.20.0/24
                                                                    BR-SRV (192.168.20.10)
```

| 項目 | 値 |
|---|---|
| FGT port1 (WAN・**据付済み**) | 203.0.113.2/30・デフォルトルート設定済み |
| FGT port3 (LAN兼管理・**据付済み**) | 10.1.10.11/24（GUI: https://10.1.10.11） |
| RBR Gi0/0 (WAN・**据付済み**) | 198.51.101.2/30・デフォルトルート設定済み |
| RBR Gi0/1 (LAN・**据付済み**) | 192.168.20.1/24 |
| USER-PC / BR-SRV | 10.1.10.12 / 192.168.20.10（HTTP 応答あり）・console root |
| トンネル IF | FGT=172.16.255.1 ⇔ RBR=172.16.255.2（/30・Tunnel0） |
| 事前共有鍵 | **Ccnp2026Ipsec** |
| 社内セキュリティ標準 | **IKEv2・AES256-SHA256・DH group 14・PFS** |
| ログイン | FGT: admin/CCNPccnp（console/GUI）・RBR: SUZUKI/CCNPccnp（console） |

要件: 本社 LAN（10.1.10.0/24）⇔ 支社 LAN（192.168.20.0/24）を **route-based
IPsec**（FGT=トンネルIF / RBR=sVTI）で相互到達させること。NAT はしない。

## Phase 1: アンダーレイ確認（VPN の土台）

📋 **観察1**: FGT から `execute ping 198.51.101.2`、RBR から
`ping 203.0.113.1` が通ること（対向 FGT 自体への ping は返らない — それでよい）。

🤔 **考察1**: RBR から 203.0.113.2 への ping が返らないのに、この上に VPN を
組んで良いと判断できるのはなぜか（何が「土台の健全性」を保証している？）。

## Phase 2: 支社側（RBR）— IKEv2 sVTI を社内標準で構築

RBR に IKEv2 の一式（proposal / policy / keyring / profile / transform-set /
ipsec profile）と **Tunnel0**（sVTI: `tunnel mode ipsec ipv4`）、支社→本社 LAN
の静的経路を構築せよ。パラメータは**社内標準（上表）**に従うこと。

📋 **観察2**: `show crypto ikev2 proposal` で自分の proposal を確認。
Tunnel0 はまだ up/down のはず — なぜかも考えておく。

## Phase 3: 本社側（FGT）— 計画変更を強いられる

FGT で phase1-interface **TO-RBR** を作り、社内標準の proposal を設定せよ
（CLI: `config vpn ipsec phase1-interface`）。

📋 **観察3**: ここで**あなたの計画は崩れる**。何が起きたか記録し、
`set proposal ?` で**この機器が実際に提示する選択肢**を列挙せよ。

🤔 **考察3**: なぜこの FortiGate は社内標準の暗号を受け付けないのか
（ヒント: ライセンス）。実務でこの状況に遭遇したら、①機器/ライセンスを変える
②標準の例外承認を取る、のどちらをどう進めるか。

**設計変更**: 本ラボでは例外承認が下りたものとして、両側を
**des-sha256 / DH group 14 / PFS group14** に統一して続行せよ
（RBR 側の修正も忘れずに。★実務では DES は使わないこと）。

## Phase 4: FGT 残りの構築 — そして上がらない

FGT 側の残りを構築せよ:

1. phase2-interface **TO-RBR-P2**（セレクタは既定のまま）
2. トンネル IF **TO-RBR** に IP（172.16.255.1/32・remote-ip 172.16.255.2/30）
3. アドレスオブジェクト **LAN-NET**（10.1.10.0/24）/ **BR-NET**（192.168.20.0/24）
4. 支社 LAN への静的経路（device=TO-RBR）

ここで RBR の Tunnel0 を `shutdown` → `no shutdown` してネゴを蹴れ。

📋 **観察4**: トンネルは**まだ上がらない**。両側からデバッグして原因を特定せよ:

- RBR: `debug crypto ikev2`（見終わったら `undebug all`）
- FGT: `diagnose vpn ike log-filter rem-addr4 198.51.101.2` →
  `diagnose debug application ike -1` → `diagnose debug enable`
  （見終わったら disable + reset）

RBR 側に届く NOTIFY の名前と、FGT 側デバッグが吐く**拒否理由の一文**を書き留めよ。

🤔 **考察4**: proposal は両側揃っているのに FGT がネゴを拒否した。FGT は
「何が存在しない」と言っているか。この設計思想（FW としての VPN の扱い）を、
Cisco ルータとの違いとして説明せよ。

## Phase 5: ポリシーで完成 — 確立を見届ける

ファイアウォールポリシーを2本作成せよ（**NAT は有効にしない**）:

1. **ID 1・LAN-to-VPN**: port3 → TO-RBR・src=LAN-NET・dst=BR-NET・accept
2. **ID 2・VPN-to-LAN**: TO-RBR → port3・src=BR-NET・dst=LAN-NET・accept

📋 **観察5-1**: RBR Tunnel0 を再度バウンス → 今度は確立する:
`show crypto ikev2 sa`（READY・Encr/PRF/DH を記録）/ FGT
`diagnose vpn ike gateway list`（established・proposal を記録）
📋 **観察5-2**: USER-PC ⇔ BR-SRV の ping / `wget -q -O - http://192.168.20.10/`
を確認し、RBR `show crypto ipsec sa` の **encaps/decaps カウンタが進む**こと、
FGT `get vpn ipsec tunnel summary` の rx/tx を確認せよ。

🤔 **考察5-1**: ポリシーで NAT を有効にしなかったのはなぜか。有効にすると
支社側から見た通信はどう見え、何が壊れ得るか。
🤔 **考察5-2**: 両側で PFS（group14）を明示的に揃えた。PFS が効くのは
**いつの・何の**ネゴシエーションか。片側だけ PFS 有効だと、いつ・どう壊れるか。

## 完成条件（この状態で採点します）

1. USER-PC ⇔ BR-SRV の ping / HTTP が双方向で成功（VPN 経由・NAT なし）
2. IKEv2 SA が確立（RBR=READY / FGT=established・des-sha256/DH14/PSK）
3. RBR の IPsec SA で encaps/decaps が実際に進んでいる・Tunnel0 up/up
4. 両側の設定が本仕様書どおり（名前・ポリシー ID・トンネル IP も仕様どおり）

## ログイン・注意

- ★FGT で `execute factoryreset` 等の初期化コマンドは**絶対に打たないこと**
  （評価ライセンスが消えます）
- RBR の WAN/LAN/デフォルトルートは据付済み — **VPN 関連の追加のみ**行うこと
- 据付機器（ISP1 / ISP2 / INET / USER-PC / BR-SRV ほか）は変更禁止
- FGT の設定は自動保存。RBR は最後に `write memory` を忘れずに
