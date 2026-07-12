# FGT-FW-BASIC-01 模範解答・解説（受講者非公開）

模範 config 全文 = [poc/fortigate/golden-basic-fgt.cfg](../../poc/fortigate/golden-basic-fgt.cfg)
（fgtbasic_ops.py solve が投入するもの・実機 100/100 検証済 2026-07-12）。

## 設計の要点

| 要素 | 解 | 落とし穴 |
|---|---|---|
| port1 | 203.0.113.2/30・alias WAN・role wan・**allowaccess なし** | `set allowaccess ping` を付けると S1 減点（管理面の最小化が要件） |
| port2 | 172.16.10.1/24・alias DMZ・role dmz・allowaccess ping | — |
| オブジェクト | LAN-NET=10.1.10.0/24・DMZ-SRV=172.16.10.10/32 | 名前は採点対象（仕様書どおり） |
| ルート | 静的デフォルト → 203.0.113.1/port1 | SD-WAN 問と違い**単線**。ゾーン経路は使わない |
| policy 1 | LAN→WAN・src=LAN-NET・NAT有効 | NAT 忘れ→SRV まで届くが**戻りが来ない**（RFC1918 は外で捨てられる） |
| VIP | extip=**203.0.113.2**（port1自身）・portforward tcp80→172.16.10.10:80 | /30 なので余剰の公開 IP が無い＝**IF IP のポート公開**が定石 |
| policy 2 | WAN→DMZ・**dst=VIP オブジェクト**・service HTTP・NAT無効 | dst に実 IP や all を書くと VIP 変換後のマッチが仕様と異なる。★**VIP は変換の定義であって許可ではない**（本問最大の体験ポイント） |
| policy 3 | LAN→DMZ・dst=DMZ-SRV・HTTP+PING | `set service HTTP PING`（スペース区切り） |
| DMZ→LAN | **書かない**＝暗黙 deny | これ自体が要件（E1 は生存証明との複合チェック） |

## 暗黙 deny の実機指紋（Phase 5 の答え合わせ用・実機採取 2026-07-12）

```
msg="vd-root:0 received a packet(proto=1, 172.16.10.10:2257->10.1.10.12:2048) ... from port2."
msg="allocate a new session-000001b2"
msg="find a route: flag=00000000 gw-0.0.0.0 via port3"      ← ルート検索は成功
msg="Denied by forward policy check (policy 0)"             ← その後ポリシーで破棄
```

**評価順序= ①受信 ②セッション確保 ③ルート検索（出口 IF 決定）④ポリシー検索**。
出口 IF が決まらないと「srcintf→dstintf」のポリシー検索自体ができない、が理由。
policy 0 = 暗黙 deny（GUI のポリシー一覧最下段の Implicit Deny）。

## 考察課題の解説

- **考察1**: GUI に入れているのは port3（LAN）の allowaccess のおかげ。allowaccess は
  「**FGT 自身宛て**（管理面）の着信」だけを制御し、FGT 発の通信や転送通信には無関係。
- **考察2**: 直書きだとサーバ IP 変更時にポリシー全数を洗い出して修正。オブジェクト
  なら**定義1カ所**の変更で参照側は全て追従。監査（どこで使われているか）も一覧できる。
- **考察3**: NAT 無しでも SRV までは届く（宛先ルーティングは正しい）。しかし戻りの
  宛先が 10.1.10.12（プライベート）になり、インターネット側に経路が無く**戻りで破綻**。
- **考察4-1**: VIP を dst に置くと「この変換を通る通信」だけを正確に許可できる。
  実 IP を書くと VIP 以外の経路や別変換にもマッチし得て、意図が config から読めなくなる。
- **考察4-2**: SNAT を重ねると DMZ-SRV から見た送信元が全て FGT（172.16.10.1）になり、
  **アクセスログから真のクライアント IP が消える**。DNAT 公開では原則 SNAT しない。
- **考察5-1**: ルートが先・ポリシーが後（上記指紋）。policy 0=暗黙 deny。
- **考察5-2**: DMZ は「侵入される前提」の区画。DMZ→LAN 全遮断が**内部への横展開**を
  止める。開ける時は src=DMZ-SRV/32・dst=宛先ホスト/32・サービス最小の1本のみ。

## 採点上の注意（出題者向け）

- **ポリシー ID 依存**: S5/S6/S7 は `show firewall policy 1|2|3` で判定。受講者が
  作り直して ID がずれた場合は grade_input.json を目視し、内容が仕様どおりなら
  手動で合格扱いにする（task.md には ID どおりに作る指示あり）
- E1（DMZ→LAN 遮断）は dmz1→FGT ping 成功との**複合チェック**（負の要件を単独採点
  しない教訓 [[ccnp-qos-labs]] の適用）
- 採点は単段（劣化注入なし）約3分。`fgtbasic_ops.py grade`
