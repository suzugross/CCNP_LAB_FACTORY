# PoC: PBR×ワイルドカードACL (BL-081) — 2026-08-02 実機検証記録

環境: IOL iol-xe 17.15 ×4 (problems/_POC-PBR・ユーザ手組み「CCNPラボPBR」と同形)。
HUB は 172.16.x への経路を持たない=PBR 不一致なら不達、という判定装置構成。

## 検証結果(全て実機・1周)

1. **★match ip address prefix-list は PBR では「match 節が無視され全トラフィック一致」**
   - MAP-B: `match ip address prefix-list PL-B`(PL-B=172.16.0.0/21 le 24)
   - クライアント発 ping: 172.16.0.1 / 7.1 / **16.1(PL範囲外)** すべて成功
   - `show route-map` MAP-B: Policy routing matches: **20 packets**(=全 ping 数)
   - → 故障種別 match_plist の症状は「対象が通らない」でなく
     **「除外対象まで policy 転送されてしまう」**(rm_no_match と同型の全吸引)
2. **カウンタは ping で温まり、発数どおり計上される**
   - ACL-A `(10 matches)` / MAP-A `Policy routing matches: 10 packets, 1140 bytes`
   - 収集順はクライアント ping → HUB show の順(collect_console は同一ノード内
     アルファベット順・ノード間は checks 出現順。"ping..."<"show..." で自然に成立)
3. **不一致時の ping 表示**: `U.U.U` / `.U.U.`(HUB が unreachable 応答) +
   `Success rate is 0 percent`。成功は `!!!!!` + 100 percent。紙面証拠として明瞭。
4. ワイルドカード動作確認: `0.0.3.255`={0..3} → 172.16.0.1 成功 / 7.1・8.1 不達 ✓
5. `show running-config | section route-map|access-list|policy` の regex 交互は動作する
   (ただし interface 配下の `ip policy` 行が文脈なしで出る→出題では
   `section interface` を別掲する方が読みやすい)

## 設計への反映

- match_plist は「全吸引」系(要件『除外対象へポリシー転送しない』違反)として出題。
- fix 形の選択肢に prefix-list 置換案を常設ハズレとして混ぜられる
  (到達性は直るが除外要件に違反=機械検証でも fixer 不成立)。
- 正典: problems/_drafts/PAPER-PBR-WILDCARD.design.md
