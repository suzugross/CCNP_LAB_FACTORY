# FGT-FW-BASIC-01: FW 基本設計体験ラボ — ポリシーと NAT で「通る/通らない」を設計する

あなたは小規模拠点に FortiGate を導入し、**インターネット接続・DMZ 公開サーバ・
社内 LAN** の3ゾーン構成を設計します。ゴールは「どの通信を・どの向きに・
どう変換して通すか」を自分で決めて実装し、**通らない通信が"どこで"落ちるのか**
まで自分の目で見届けることです。

★本ラボは**体験型**です。📋観察チェックポイントで実際の出力を記録しながら
進めてください。🤔考察課題の答えは採点後レビューで解説します。
GUI（https://10.1.10.11）と CLI のどちらで構築しても構いません
（おすすめ: GUI で作り、CLI の `show` で「何が生成されたか」を毎回確認）。

## トポロジ（あなたが触るのは FGT のみ・他は据付）

```
 あなたのPC ──┐(管理GUI/同一LAN)
              ├─[SW]── port3 ┌─────┐ port1 ──(WAN)── ISP1 ── INET ── SRV
 USER-PC ─────┘   10.1.10.0/24│ FGT │                            198.51.100.100
                              └─────┘ port2 ──(DMZ)── DMZ-SRV
                                                       172.16.10.10
```

| 項目 | 値 |
|---|---|
| FGT port1 (WAN) | 203.0.113.2/30・対向 ISP1=203.0.113.1・alias **WAN** |
| FGT port2 (DMZ) | 172.16.10.1/24・alias **DMZ** |
| FGT port3 (LAN兼管理・**設定済み**) | 10.1.10.11/24（GUI: https://10.1.10.11） |
| USER-PC | 10.1.10.12（GW=FGT）・console ログイン root |
| DMZ-SRV | **172.16.10.10**（HTTP 応答あり・据付） |
| SRV（インターネット上のサーバ） | **198.51.100.100**（HTTP 応答あり・据付） |
| 公開要件 | 外部から **http://203.0.113.2/** → DMZ-SRV へ転送 |
| FGT ログイン | console/GUI とも **admin / CCNPccnp** |

## Phase 1: インターフェース設計（ゾーンの入口を作る）

port1 / port2 に上表の IP と alias を設定せよ。加えて:

- port1（WAN）は **管理アクセスを一切開けない**（インターネットに管理面を晒さない）
- port2（DMZ）は **ping のみ許可**（疎通確認用）
- role も適切に（wan / dmz）— GUI のトポロジ表示が変わる

📋 **観察1**: FGT から `execute ping 203.0.113.1` と `execute ping 172.16.10.10`
が通ることを確認（対向設定は済んでいる — 通るかはあなたの IF 設定次第）。

🤔 **考察1**: port1 の allowaccess を空にしても、いま自分が GUI に入れて
いるのはなぜか。また FGT **発**の ping が port1 から出られるのはなぜか
（allowaccess は何の通信を制御している？）。

## Phase 2: アドレスオブジェクト（ポリシーの部品を先に作る）

以下の2つを定義せよ:

| オブジェクト名 | 内容 |
|---|---|
| **LAN-NET** | 10.1.10.0/24 |
| **DMZ-SRV** | 172.16.10.10/32 |

🤔 **考察2**: ポリシーに IP を直書きせずオブジェクトを挟む利点は？
「DMZ サーバの IP が変わる日」を想像して、変更箇所の数を比べよ。

## Phase 3: アウトバウンド（LAN からインターネットへ）

1. デフォルトルートを作成（gateway 203.0.113.1・device port1）
2. ファイアウォールポリシー **ID 1・名前 LAN-to-WAN** を作成:
   **port3 → port1・src=LAN-NET・dst=all・サービス ALL・accept・NAT 有効**
   （NAT は「発信 IF の IP を使う」= いわゆる IP マスカレード）

📋 **観察3-1**: USER-PC から `ping 198.51.100.100` と
`wget -q -O - http://198.51.100.100/` が通ることを確認。
📋 **観察3-2**: FGT で `diagnose sys session list | grep -A 3 198.51.100.100`
— セッションの `hook=post dir=org act=snat` の行を探し、**10.1.10.12 が
203.0.113.2 に変換されている**ことを自分の目で確認せよ。

🤔 **考察3**: NAT を切るとこの通信はどこまで行って、どこで破綻するか
（パケットは SRV に届く？届くなら何が返ってこない？）。

## Phase 4: DMZ 公開（VIP = 宛先 NAT）

**まず VIP だけ**を作成せよ（ポリシーはまだ作らない）:

- VIP 名 **DMZ-SRV-HTTP**: 外部 IF=port1・外部 IP **203.0.113.2**・
  **port-forward 有効 TCP 80 → 172.16.10.10:80**
  （WAN が /30 なので公開 IP は port1 自身の IP を使う — 小規模拠点の定石）

📋 **観察4-1**: SRV の console（root）から `wget -q -O - -T 5 http://203.0.113.2/`
→ **失敗する**ことを確認。VIP は「変換の定義」であって「許可」ではない。

続いてポリシーを2本作成せよ:

1. **ID 2・WAN-to-DMZ-HTTP**: port1 → port2・src=all・**dst=DMZ-SRV-HTTP（VIP を指定）**・
   サービス HTTP・accept（**NAT は無効**のまま）
2. **ID 3・LAN-to-DMZ**: port3 → port2・src=LAN-NET・dst=DMZ-SRV・
   サービス HTTP と PING・accept

📋 **観察4-2**: SRV から同じ wget → 今度は **DMZ SERVER** が返ることを確認。
USER-PC から `wget -q -O - http://172.16.10.10/` も確認。
📋 **観察4-3**: `diagnose sys session list | grep -B 2 -A 3 172.16.10.10` —
外部からのセッションで宛先 203.0.113.2 が 172.16.10.10 へ **DNAT** されている
行（`act=dnat`）を探せ。

🤔 **考察4-1**: ポリシー ID 2 の dstaddr には、なぜ実 IP（DMZ-SRV）ではなく
**VIP オブジェクト**を指定するのか。
🤔 **考察4-2**: ID 2 で NAT（SNAT）を有効にしなかったのはなぜか。有効にすると
DMZ-SRV のアクセスログから何が失われるか。

## Phase 5: 暗黙 deny を目撃する（FW の本性）

DMZ-SRV が乗っ取られた想定で、**DMZ → LAN** の通信を試す:

📋 **観察5-1**: DMZ-SRV の console（root）から `ping -c 3 10.1.10.12` →
**全滅**することを確認（あなたは DMZ→LAN のポリシーを1本も書いていない）。
📋 **観察5-2**: その瞬間を FGT で捕まえる:

```
diagnose debug flow filter saddr 172.16.10.10
diagnose debug enable
diagnose debug flow trace start 6
（DMZ-SRV から ping を再実行）
diagnose debug disable
diagnose debug flow filter clear
```

出力の中から **`find a route: ... via port3`** の行と、その直後の
**`Denied by forward policy check (policy 0)`** の行を書き留めよ。

🤔 **考察5-1**: ルート検索は**成功している**のに落ちた。FGT の転送処理では
経路とポリシーのどちらが先に評価されているか。「policy 0」とは何者か。
🤔 **考察5-2**: DMZ→LAN を全遮断のままにする設計は何を守っているか。
もし DMZ-SRV から LAN の特定サーバへだけ通したくなったら、どう書くのが最小か。

## 完成条件（この状態で採点します）

1. USER-PC → SRV の ping / HTTP が成功（SNAT アウトバウンド）
2. 外部（SRV 側）から http://203.0.113.2/ で DMZ-SRV の応答が返る（VIP 公開）
3. USER-PC → DMZ-SRV の HTTP が成功
4. **DMZ → LAN は遮断されている**（DMZ-SRV 自体は生きていること）
5. インターフェース / オブジェクト / ポリシー / ルートが本仕様書どおり
   （名前・ポリシー ID も仕様どおりに）

## ログイン・注意

- FGT: console / GUI（https://10.1.10.11）とも admin / CCNPccnp
- ★FGT で `execute factoryreset` 等の初期化コマンドは**絶対に打たないこと**
  （評価ライセンスが消えます）
- USER-PC / DMZ-SRV / SRV: console で root（プロンプトが出ない時は Enter）
- 据付機器（ISP1 / SRV / DMZ-SRV ほか）は変更禁止。DMZ 配線上に他ラボ用の
  据付ルータが同居しているが本問とは無関係・触らないこと
- 設定は自動保存されます（IOS と違い write memory 不要）
