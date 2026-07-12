# FGT-FW-BASIC-01 設計メモ（BL-047）

FortiGate 作問シリーズ第2弾。SD-WAN 問（BL-046）が「回線品質」の話だったのに対し、
本問は **FWの本業（インターフェース設計・オブジェクト・ポリシー・NAT・暗黙deny）** を
初学者が体験しながら一周する構築ラボ。受験者は FGT ほぼ未経験の前提。

## ゴール（学習効果）

- FGT の設定モデル（config/edit/set/next/end・ポリシーは並び順評価）が体に入る
- 「オブジェクトを作ってからポリシーを書く」思考への切替（ACL直書き脳からの脱却）
- SNAT（IF出口NAT）と VIP（DNAT）の役割の違い＋「VIPを作っただけでは通らない」体験
- `diagnose debug flow` で暗黙denyの瞬間を観察・`diagnose sys session list` でステートフルの実感

## 共通制約（eval ライセンス・確定済）

- **設定可能IF 総数3個の絶対上限**（VLANサブIF/loopbackも不可）→ 3IF構成必須
- **wipe＝ライセンス消失** → 初期化は unbuild 方式（設定の逆順削除）。destroy verb は作らない
- 稼働中のCMLリンク抜去＝vNIC喪失 → **配線替えは必ずラボ停止後**

## 共用ラボ化（ラボ改修・one-time surgery）

既存 CML ラボ "FGT-SDWAN-01" を **"FGT-LAB"** に改名し、FGT問題シリーズの共用ラボとする
（fgt1 のライセンス保全のため、ラボは1個を使い回す）。

改修内容（全ノード停止後に実施）:

```
旧: fgt1.port2 ── ISP2.Gi0/1
新: fgt1.port2 ── SW2(無管理SW) ─┬─ ISP2.Gi0/1
                                  └─ dmz1(alpine)
```

- SW2 は L2 透過なので **SD-WAN 問は無改修でそのまま動く**（port2=203.0.114.2 ⇔ ISP2）
- BASIC 問では port2 を DMZ（172.16.10.1/24）に付け替え、ISP2 の Gi0/1 は別サブネットの
  同居人として無害（SD-WAN 設定は unbuild 済みなので経路も無し）
- dmz1 は console 専用（mgmt リース不要）。busybox httpd で Web サーバ役
- ノード数 8→10（20上限内・fgt-lab.yaml として再エクスポート済）
- sdwan_ops.py は PROBLEM("FGT-SDWAN-01") と TITLE("FGT-LAB") を分離

## アドレス計画（BASIC 問時・実装確定版）

| 場所 | プレフィクス | 主要ホスト |
|------|------------|-----------|
| WAN (port1) | 203.0.113.0/30（SD-WAN問と同一・変えない） | fgt1=.2 / ISP1=.1(GW) |
| DMZ (port2) | 172.16.10.0/24 | fgt1=.1 / dmz1=.10(httpd) |
| LAN (port3) | 10.1.10.0/24 | fgt1=.11 / pcA=.12（SD-WAN問と共通・mgmt兼用） |
| インターネット上のサーバ | 198.51.100.100 | pcB（SD-WAN問の SRV を流用・外部試験クライアント兼用） |

★VIP は当初案の「公開用 /24 内の別 IP（.100）」を廃し、**port1 自身の IP
（203.0.113.2）への port-forward tcp80** に変更。WAN が /30 のため余剰 IP が無く、
別 IP 案は ISP1/INET への経路追加（共用機材への設定債務）が要る。IF IP 公開は
小規模拠点の定石でもあり教材性も高い。ISP1/INET のルーティングは完全無改修。

## 体験フェーズ構成（task.md 骨子・📋観察/🤔考察スタイル踏襲）

1. **インターフェース設計**: port1/port2 の IP・alias(WAN/DMZ)・role・allowaccess 最小化
   （🤔 なぜ WAN に ping 応答を許すか/許さないか）
2. **オブジェクト**: address(LAN-NET/DMZ-SRV/SRV-EXT)・service(HTTP) を先に定義
   （🤔 直書きとの違い＝運用変更時の影響範囲）
3. **アウトバウンド**: 静的デフォルトルート（ISP1 のみ・SD-WAN 不使用）＋
   LAN→WAN ポリシー＋SNAT（📋 セッションテーブルで NAT 変換を観察）
4. **公開サーバ**: VIP 203.0.113.100→172.16.10.10 ＋ WAN→DMZ ポリシー
   （📋 VIP だけ作って curl→落ちる→ポリシー追加→通る、を体験）＋ LAN→DMZ ポリシー
5. **暗黙deny観察**: DMZ→LAN が落ちることを `diagnose debug flow` で確認
   （🤔 DMZ サーバが乗っ取られたら？）＋ポリシー順序の入替実験＋セッションテーブル

## 採点骨子（100点・console 採点・grade.py流用）

- G系（疎通）: pcA→198.51.100.100 ping/HTTP（SNAT 実証）・外部→VIP HTTP（pcB か INET から）
- S系（設定）: オブジェクト定義・ポリシー（srcintf/dstintf/NAT）・VIP・静的ルート・allowaccess
- E系（挙動）: DMZ→LAN 遮断（dmz1→pcA ping 失敗＝負の要件・複合チェック）・
  セッションテーブルに NAT 検証列
- ops: topologies/fgtbasic_ops.py（build=unbuild方式/grade/solve/status/stop・destroy無し）

## PoC 結果（2026-07-12・全項目実機✅）

- [x] ラボ改修（SW2 挿入・dmz1 追加・改名 FGT-LAB）→ ライセンス Valid 維持
- [x] SD-WAN 問が改修後も無傷 → **劣化採点込みフル回帰 100/100**（SW2 透過実証）
- [x] BASIC golden config 全構文検証 → solve 76行・注意0件
- [x] VIP: port1 IF IP への port-forward 方式に変更（上記）→ pcB からの DNAT HTTP 成功
- [x] debug flow 暗黙deny指紋採取 → `find a route ... via port3` の後に
      `Denied by forward policy check (policy 0)`（ルート先・ポリシー後の実証）
- [ ] eval の UTM 系挙動（本問では未使用・BL-048 以降の参考課題として持ち越し）

**フルサイクル: build 0/100 → solve → 100/100**（S3 のみ1回修正:
`show firewall address` は引数1個まで＝2オブジェクト同時指定不可→全リスト表示に変更）。

### ★改修時に発見・修正した SD-WAN 問の潜在バグ（重要知見）

pcA/pcB の **day0 config が旧PoC残骸（10.0.x.x）のまま**で、実IPは console 手打ちの
揮発状態だった → ラボ再起動で SD-WAN 問の採点が壊れる時限爆弾。今回 alpine 3台
（pcA/pcB/dmz1）を stop→wipe→day0焼き直し→start で恒久化（alpine の wipe は
ライセンス無関係で安全・**day0 は毎ブート実行**なので自己復旧する）。
教訓: **alpine を console 手打ちで構成したら必ず day0 にも焼き込む**。
