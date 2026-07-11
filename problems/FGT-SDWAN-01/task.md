# FGT-SDWAN-01: SD-WAN 体感構築ラボ — 回線品質を見て自動で逃げるネットワーク

あなたは2本のインターネット回線（ISP1/ISP2）を契約した拠点に FortiGate を導入し、
**SD-WAN** を構築します。ゴールは「回線が*切れていないのに品質が悪い*とき、
ユーザ通信を止めずに自動で良い回線へ逃がす」仕組みを、自分の手で組んで・
数値で観察して・壊して（劣化させて）・治るまで見届けることです。

★本ラボは**体験型**です。各 Phase の 📋観察チェックポイントで実際の数値を
記録しながら進めてください。🤔考察課題の答えは採点後レビューで解説します。

## トポロジ（あなたが触るのは FGT のみ・他は据付）

```
 あなたのPC ──┐(管理GUI/同一LAN)
              ├─[SW]── port3 ┌─────┐ port1 ──(WAN1)── ISP1 ──┐
 USER-PC ─────┘   10.1.10.0/24│ FGT │                        ├── INET ── SRV
                              └─────┘ port2 ──(WAN2)── ISP2 ──┘   198.51.100.100
```

| 項目 | 値 |
|---|---|
| FGT port1 (WAN1) | 203.0.113.2/30・対向 ISP1=203.0.113.1 |
| FGT port2 (WAN2) | 203.0.114.2/30・対向 ISP2=203.0.114.1 |
| FGT port3 (LAN兼管理・**設定済み**) | 10.1.10.11/24（GUI: https://10.1.10.11） |
| USER-PC | 10.1.10.12（GW=FGT）・console ログイン root |
| SRV（宛先サーバ） | **198.51.100.100**（HTTP 応答あり・ISP1/ISP2 どちら経由でも到達可） |
| FGT ログイン | console/GUI とも **admin / CCNPccnp** |

## Phase 1: WAN インターフェース（配管をつなぐ）

port1 / port2 に上表の IP を設定せよ（`allowaccess ping` も付与）。

📋 **観察1**: FGT から両 ISP の対向 IP へ `execute ping` が通ることを確認。
さらに `execute ping-options source 203.0.113.2` → `execute ping 198.51.100.100`
で **WAN1 経由のサーバ到達**、source を 203.0.114.2 に変えて WAN2 経由も確認せよ
（ISP/INET には経路が用意済み — 使えるかはあなたの IF 設定次第）。

🤔 **考察1**: この時点で USER-PC からサーバへは通信できない。足りないものを
2つ挙げよ（ヒント: 経路と、FW としての許可）。

## Phase 2: SD-WAN ゾーン化（2本の回線を1つの仮想IFに束ねる）

1. SD-WAN を有効化し、**member 1 = port1（gateway 203.0.113.1）/
   member 2 = port2（gateway 203.0.114.1）**を既定ゾーン `virtual-wan-link` に収容
2. デフォルトルートを**個別 IF 宛てではなく SD-WAN ゾーン**に向ける
   （`config router static` で `set sdwan-zone virtual-wan-link`）
3. ファイアウォールポリシーを1本作成: **port3 → virtual-wan-link・
   accept・NAT 有効**

📋 **観察2**: `get router info routing-table all` — デフォルトルートが
**port1/port2 の2行**で載ることを確認（これがゾーン経路の正体）。
`diagnose sys sdwan member` でメンバー一覧と source IP を確認。
USER-PC から `ping 198.51.100.100` と `wget -q -O - http://198.51.100.100/`
が通ることを確認。

🤔 **考察2-1**: ポリシーの dstintf に port1/port2 を並べる代わりにゾーンを
指定する利点は？（回線を3本目に増やす日を想像せよ）
🤔 **考察2-2**: この時点で FGT は2回線をどう使い分けているか。「品質」を
見ているか？

## Phase 3: Performance SLA（回線に聴診器を当てる）

ヘルスチェック **SLASRV** を作成せよ（★名前にハイフンは使えない）:
宛先 **198.51.100.100**・protocol ping・**interval 1000**(ms)・members 1 2。

📋 **観察3（重要・基準値の記録）**: 30秒待ってから
`diagnose sys sdwan health-check status` を実行し、**両メンバーの
latency / jitter / packet-loss / MOS を書き留めよ**（後で劣化時と比べる）。
GUI でも Network > SD-WAN > Performance SLAs のグラフを開いておくこと。

🤔 **考察3**: プローブは何秒間隔で・どの IF から・何本飛んでいるか。
プローブ宛先を「回線の先の実サーバ」にする意味は？（ISP の GW 宛てとの違い）

## Phase 4: SLA 閾値と SD-WAN ルール（「悪い」の定義と逃げ方）

1. SLASRV に **sla 1** を定義: `latency-threshold 100`（ms）・
   `packetloss-threshold 5`（%）・link-cost-factor latency packet-loss
2. SD-WAN ルール **TOSRV** を作成: `mode sla`・sla=SLASRV id 1・
   **priority-members 1 2**（= 平常時 port1 優先、SLA 違反で port2）

📋 **観察4**: `diagnose sys sdwan service4` — ルールに **1: port1 / 2: port2**
の順で載り、両方 `sla(0x1)`（SLA 充足）であること。今の第一選択は？

🤔 **考察4**: latency-threshold 100ms は観察3の基準値の何倍か。閾値を
基準値ギリギリ（例: 5ms）にすると何が起きるか。

## Phase 5: 体感 — 劣化・自動迂回・復帰を見届ける

構築が終わったら出題者に伝えること。出題者が **WAN1 に遅延250ms＋loss3%**
を注入します（実回線の「輻輳した安い回線」の再現）。以下を**リアルタイムで**
観察せよ:

📋 **観察5-1**: USER-PC で `ping 198.51.100.100` を流しっぱなしにしておく
📋 **観察5-2**: `diagnose sys sdwan health-check status` を数秒おきに実行 —
port1 の latency/loss が悪化し、`state(dead)` → `sla_map=0x0` になる瞬間を捉えよ
📋 **観察5-3**: `diagnose sys sdwan service4` — 第一選択が **port2 に入れ替わる**
ことを確認。USER-PC の ping は何発落ちたか？
📋 **観察5-4**: 出題者が劣化を解除した後 — port1 の latency はすぐ 1ms 台に
戻るのに、**しばらく port2 のまま**であることを確認。`packet-loss(%)` の
表示に注目しながら、port1 に戻る瞬間まで見届けよ

🤔 **考察5-1**: 切替時、なぜユーザの ping はほぼ落ちないのか（ルーティング
プロトコルの収束と何が違う？）
🤔 **考察5-2**: 回復後すぐフェイルバックしないのはなぜか。この「慎重さ」は
実運用で何を防いでいるか（ヒント: フラッピング）

## 完成条件（この状態で採点します・採点中に出題者が劣化→復旧を再実行します）

1. USER-PC → 198.51.100.100 の ping / HTTP が成功（SD-WAN 経由・SNAT）
2. Performance SLA が両メンバー alive・SLA 閾値どおり
3. SD-WAN ルールが仕様どおり（mode sla・port1 優先）
4. **WAN1 劣化時に port2 へ自動切替し、ユーザ通信が継続すること**
5. **回復後に port1 へ自動フェイルバックすること**

## ログイン・注意

- FGT: console / GUI（https://10.1.10.11）とも admin / CCNPccnp
- ★FGT で `execute factoryreset` 等の初期化コマンドは**絶対に打たないこと**
  （評価ライセンスが消えます）
- USER-PC: console で root（プロンプトが出ない時は Enter）
- 据付機器（ISP1 / ISP2 / INET / SRV）は変更禁止
- 設定は自動保存されます（IOS と違い write memory 不要）
