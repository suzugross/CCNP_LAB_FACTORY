# GEN-S2SVPN — 実務想定・複数拠点 IPsec VPN 設計構築問（生成器）design メモ

status: 提案(2026-07-24) / BL-063
問題ID案: `GEN-S2SVPN-<seed4桁>`（生成器 `topologies/gen_s2svpn.py`）
難易度想定: 4〜5 / 分野: ENARSI/VPN（+ENCOR NAT）

## 1. コンセプト

既存の IPsec 資産（sVTI IKEv1/IKEv2・crypto map・DMVPN+IPsec TS・FGT interop）は
すべて「技術を指定して作らせる/直させる」形。本問は逆に **要件書だけ渡して
技術選定から演習者に委ねる設計構築問**。BL-060(要件駆動グリーンフィールド)の
受入テスト方式採点を、VPN という限定ドメインで先行実証する位置づけでもある。

- 本社(HQ) + 支店2拠点(BR1/BR2) を拠点間 VPN で接続
- フル/スプリットトンネルは **seed でランダム**
- 支店間通信ポリシーも **seed でランダム**
- インターネットアクセスは NAPT 必須
- VPN 方式（DMVPN / sVTI フルメッシュ / crypto map / ハブ&スポーク）は **演習者が判断**
  → 採点は解法非依存の効果ベース

## 2. トポロジ（8ノード・20ノード上限に余裕）

```
 H-HQ(alpine) ─ HQ(IOSv) ─┐
 H-B1(alpine) ─ BR1(IOSv) ─┼─ INET(IOL・ISP役・変更禁止) ─ SRV(alpine・公開web)
 H-B2(alpine) ─ BR2(IOSv) ─┘
```

- エッジ3台は **IOSv**（DMVPN 選択肢を保証するため。mGRE/NHRP は gen_dmvpn_ts で IOSv 実績。console 採点）
- INET は IOL・変更禁止。各拠点へ公開 /30（203.0.113.x 等）、SRV セグメント 198.51.100.0/24
- LAN は RFC1918（seed で 10.x/172.16.x/192.168.x を出し分け）
- SRV は busybox httpd（curl 先＝NAPT 出口判定の的）

## 3. ランダム軸（seed 抽選）

| 軸 | 値域 | 出題文への現れ方 |
|---|---|---|
| A. トンネルポリシー | 両方split / 両方full / 混在(BR1のみfull等) | 「支店のWeb閲覧は本社セキュリティ装置経由で集約監査(=full)」vs「支店は自拠点で直接ブレイクアウト(=split)」等の業務要件文 |
| B. 支店間通信 | 全許可 / 全遮断 / 限定許可(ICMPのみ・特定セグメントのみ 等) | 「支店間で内線VoIPあり」「支店間直接業務なし・情報分離」等 |
| C. 公開サーバ | なし / HQ DMZ の静的NAT(port forward)公開 | 「本社のWebをインターネットへ公開」 |
| D. アドレス/番号 | LAN帯・公開IP・seed値 | 既存生成器の流儀どおり |

軸A×B×C で実質 3×3×2=18 パターン + アドレスランダム。

## 4. 教材の核（実務罠 — PoC で作り込む）

1. **NAT と crypto の順序**: split×NAPT 併存で、NAT ACL に VPN 対象トラフィックの
   deny を入れないと PAT が先に効いて crypto ACL 不一致 → VPN 片方向死。本問最大の実務論点。
2. **フルトンネルの再帰ルーティング**: default をトンネルに向けるとトンネル宛先まで
   飲み込む → ピア向け host route 必須（mGRE 再帰は RECURDOWN 非発出の既知指紋）。
3. **フルトンネル時の HQ ヘアピン NAT**: 支店LAN 発トラフィックを HQ の NAPT で出す
   → HQ の NAT inside 判定（Tunnel IF への ip nat inside）と NAT ACL への支店セグメント追加。★要PoC
4. **GREだけ張って暗号化なし**の手抜き検出（ipsec sa encaps 増分採点）。
5. ip mtu 1400 / ip tcp adjust-mss 1360（DMVPN/GRE 系規約 → 今回は採点要件に昇格）。

## 5. 採点設計（解法非依存・効果ベース）

★uRPF 知見: NAT/crypto はデータプレーン → RIB ベース netmodel では検出不能。
ping/curl の効果採点を主軸にする（0点発射チェックイディオム適用）。

- **P1 拠点間到達性** (25): HQ⇄BR1/BR2 の LAN 間 ping。支店間はポリシー軸Bどおり
  「通るべきは通る＋落ちるべきは落ちる」をセット採点（負の要件単独採点しない教訓）。
- **P2 暗号化保証** (20): 各エッジ `show crypto ipsec sa` encaps/decaps がテストトラフィックで
  増分すること＋INET の RFC1918 送信元/宛先 catch ACL カウンタ=0（平文漏れ・経路漏れ検出）。
- **P3 NAPT 出口検証** (25): 各ホストから SRV へ curl/ping → INET の SRV 向け IF に
  仕込んだ送信元公開IP別 ACL カウンタで「どの公開IPで出たか」判定。
  full=HQ公開IP / split=自拠点公開IP。軸C ありなら INET→HQ公開IP:80 の到達も。
- **P4 監査** (15): INET/SRV/ホスト変更禁止（config diff ゼロ）・静的経路ごまかし禁止等。
- **P5 MTU/MSS** (10): Tunnel IF の ip mtu / adjust-mss 存在（regex）＋ df-bit スイープ疎通。
- **P6 設計レポート** (5): report.yaml に VPN 方式と選定理由（将来拠点増の観点）→
  採点後 Claude 講評（既存レビュー方針に接続）。as-built 突合は遠期。

解法非依存の実証: 模範 solve は1系統（DMVPN or sVTI メッシュ）だが、
フルサイクル検証時に **別解（もう一方の方式）でも 100/100** を1回確認する
（gen_redist_mp の誤解法クロスチェックの逆向き＝正解多様性チェック）。

## 6. PoC 項目 — ★2026-07-24 実施済・主要項目すべて成立（[poc/s2svpn/README.md](../../poc/s2svpn/README.md)）

1. ✅ sVTI + NAT overload 同居 → **deny 不要**（Tunnel0 は nat outside でないため NAT 不発火）
2. ✅ crypto map + NAT overload → **古典罠が完全再現・deny 必須**。指紋= NAT テーブルに
   VPN 対象エントリ + encaps 0 + MM_NO_STATE。**罠の有無が技術選択で変わる**と判明
3. ✅ フルトンネル×HQ ヘアピン NAT **完全動作**（Tunnel0 に ip nat inside・IOSv 15.9・
   拠点間は inside→inside で NAT 非適用のまま）
4. ✅ INET JUDGE ACL 行別カウンタで出口公開IP機械判定成立（clear→テスト→読取）
5. ✅ alpine curl → busybox httpd（day0 焼込みで安定）
6. ✅ 再帰ルーティング指紋: sVTI は **RECURDOWN+ADJ-5-PARENT を明示発出**（mGRE 非発出と対照）・
   修正後復旧は自動 1〜2 分 → 採点に settle 時間
7. 残（本実装時に消化）: 軸B 限定許可の採点安定性 / DMVPN 解での採点中立性確認

## 7. 実装ステップ — ★2026-07-24 本実装完了（BL-063 完了アーカイブ参照）

1. ✅ PoC（poc/s2svpn/）
2. ✅ `topologies/gen_s2svpn.py`（軸A/B/C×LAN帯3種・task.md 依頼書体裁・svti/cmap 2系統模範解）
3. ✅ 採点は grade.py でなく **`topologies/s2svpn_ops.py` の自己完結逐次効果採点**を採用
   （clear→試験→カウンタ読取の順序制御が必要なため。evpn_ops/sda_ops 系）。
   0点発射ガード=負の要件は正の要件成立時のみ得点。
4. ✅ 実機4サイクル: 3303 svti 0→100 / 8808 cmap 0→84(★静的PAT罠発見)→修正→100 /
   9909 svti 100 / 1028 cmap 0→100（b2b全4種×解法2系統×トンネル全組合せ）
5. ✅ CATALOG/BACKLOG 更新。★新知見= crypto map×interface形静的PAT の先取り変換
   → route-map 条件付き静的NAT で解消（詳細は BL-063 アーカイブ行）

## 8. 遠期変種

- 支店 NAT 越え(NAT-T)版・IKEv2 指定版・バックアップISP×IP SLA フェイルオーバー版
- FGT 拠点混在 interop（FGT-LAB 資産流用）
- 拠点3以上に増やして DMVPN の優位性を体感させる版（20ノード上限内で+1拠点は可）

## 9. Day2 運用シナリオパック（BL-064・ユーザ発案 2026-07-24）— ★2026-07-25 実装完了

実装は `gen_s2svpn.py --day2`＋`s2svpn_ops.py grade --ticket t1/t2/t3`。
3チケットとも実機 broken 0/100→模範解答 100/100 済(BL-064 完了アーカイブ参照)。
下記原案からの主な確定差分: BR3(#1)と BR4(#3)を**別ノード**にして3チケットを1ラボ逐次処理化/
#3 の吸収拠点は**既存支店と重複**(HQ とではない)＝戻りが正規保持者のトンネルへ吸われる指紋/
解法はホスト単位 static NAT+route-map(network 形は route-map 非対応・PoC README 追記参照)。

本編（BL-063）で構築済みの環境を「稼働中の本番」と見立て、運用チケットを順次投入する続編。
ベーストポロジに **BR3 + H-B3 を配線済み・未設定で最初から置いておく**（8→10ノード、上限内）。
チケット文はどれも実務どおり情報不足・曖昧にする（ヒント控えめ方針・既存チケットTSの流儀）。

### シナリオ1: 支店追加（実機×仕様書の食い違いあり・ブラウンフィールド構築）

- 「BR3 を既存仕様書どおりに追加してほしい」＋仕様書(ドキュメント)を渡す。
  **仕様書は実機と食い違う箇所を seed で仕込む**（例: 事前共有鍵が現行と違う/HQ側の
  受け入れ設定が仕様書と別インターフェース/トランスフォームセットの世代ずれ/LAN帯の記載ミス）。
- 学習点= as-built 調査（show run/crypto/cdp で現物を正とする判断）＋食い違いの報告。
- 採点= BR3 全要件疎通（P1-P3 を BR3 に拡張）＋ report.yaml に発見した食い違い列挙
  （seed 由来の答えと照合＝BL-062 の「答えが現場にしかない」採点様式の流用）。

### シナリオ2: 「支店のインターネットが遅い」→ フル→スプリット変更

- チケット=体感報告のみ（「BR1 のネットが遅いと苦情」）。原因= full tunnel の
  ヘアピン集約。対応= 経営判断でローカルブレイクアウト許可→ split へ移行、という筋書き。
- 学習点= §4 の罠1（NAT ACL への VPN 対象 deny 追加）と罠2の**解除**（default の戻し）を
  稼働中に、拠点間通信を切らさず実施する変更作業。
- 採点= P3 の出口公開IP判定が HQ→BR1 自拠点IPへ**変化**したこと＋P1/P2 が劣化していないこと
  （before/after の2回採点 or 変更後1回で全項目）。

### シナリオ3: 吸収拠点のサブネット完全重複（曖昧チケット×NAT overlapping）

- 「吸収した拠点を担当者が見様見真似で本社と VPN 接続→『よくわからないがうまくいかない』」。
  実態= 新拠点 LAN が既存拠点と**完全同一サブネット**。トンネルは Phase1/2 とも UP、
  SA もできるのに通信不成立（or 片方向）という診断が紛らわしい状態を作る。
- 解法= NAT overlapping（トンネル対象の twice/policy NAT で相互に別の見かけ帯へ変換）
  or リナンバ提案（チケット制約で「拠点側は変更凍結」としリナンバ封じ→NAT 強制、が本命）。
- ★要PoC: IOSv での NAT overlapping × IPsec の順序（inside→outside 変換後の crypto ACL 一致）。
- BL-060 合併シナリオの「NAT overlapping」要素の単体先行実証になる。
- 採点= 変換後アドレスでの相互疎通＋既存拠点無影響＋（リナンバ封じの）config diff 監査。

実装形= 生成器に `--scenario add_branch/split_migrate/overlap` を持たせ、ベース seed の
成果物ラボへ差分投入する ops 方式（evpn_ops/sda_ops の phase 投入と同系）。3本連番で
1つの「運用週間」ストーリーにもできる（追加→苦情→吸収合併の時系列）。
