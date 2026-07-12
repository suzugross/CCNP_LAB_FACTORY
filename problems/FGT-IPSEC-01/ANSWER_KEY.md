# FGT-IPSEC-01 模範解答・解説（受講者非公開）

模範 config = [golden-ipsec-fgt.cfg](../../poc/fortigate/golden-ipsec-fgt.cfg) /
[golden-ipsec-rbr.cfg](../../poc/fortigate/golden-ipsec-rbr.cfg)
（fgtipsec_ops.py solve が投入・実機検証済 2026-07-12）。

## 仕込んだ2つの「計画どおりに行かない」

| # | 事象 | 真相 | 実機指紋 |
|---|---|---|---|
| 1 | 社内標準 AES256 が FGT に入らない | **eval ライセンス = LENC（低暗号）ビルド**。使える暗号は DES 系のみ（`set proposal ?` = des-md5/sha1/sha256/sha384/sha512） | `command parse error before 'aes256-sha256'` |
| 2 | proposal を揃えてもネゴ拒否 | **FGT はトンネル IF を参照するポリシーが1本も無いと IKE ネゴ自体を拒否**（FW としての設計思想: 通す先の無い VPN は張らない）。VIP と同じ「定義しただけでは動かない」哲学 | FGT: `ignoring IKEv2 request, no policy configured` / `Negotiate SA Error: no policy configured for the gateway` → RBR には `NOTIFY(NO_PROPOSAL_CHOSEN)` が届く（**proposal は合っているのに**この NOTIFY が来る、が interop デバッグの醍醐味） |

★罠2の重要教訓: 対向 Cisco には NO_PROPOSAL_CHOSEN と**嘘のような理由**が届く。
片側のログだけ見ると「proposal 不一致」と誤診する — **両側デバッグの必然性**が本問の核。

## 設計の要点

- **FGT route-based**: phase1-interface 作成でトンネル IF が自動生成（★eval の
  「IF 3個上限」に**トンネル IF は数えられない** — PoC 実証済）。phase2 の
  セレクタは既定 0.0.0.0/0 のままにするのが正解 — IOS sVTI の any/any と一致
- **PFS**: FGT phase2 は既定 PFS 有効（dhgrp 14 指定）・IOS 側は既定無効 →
  `set pfs group14` を ipsec profile に明示して整合。PFS は **CHILD SA の
  リキー時**に効く（初回 IKE_AUTH の子 SA には KE 無し）→ 片側だけだと
  「最初は繋がるのに数時間後に切れる」時限断になる
- **eval 制約（本問で確定した2つ）**: ①暗号は DES 系のみ（LENC）
  ②**ファイアウォールポリシー最大3本**（4本目は `-4 reached the maximum number
  of entries`）— 本問は 2本で収まる
- IOS 側は既存 sVTI 規約どおり（proposal/policy/keyring/profile/transform/
  ipsec profile/Tunnel0）。keyring の peer address は**対向の実 IP**
  （203.0.113.2）で match identity も同じ

## 考察課題の解説

- **考察1**: 203.0.113.2 への ping 不達は FGT port1 の allowaccess（管理面）の
  問題であって転送面の障害ではない。土台の健全性は「FGT**発**の ping が RBR に
  届く」「経路が双方向に存在する」ことで保証済み。IKE は FGT 自身宛て UDP500 だが
  これは allowaccess ではなく IPsec エンジンが受ける
- **考察3**: eval ライセンスが輸出規制相当の LENC ビルドで動くため。実務では
  ①が正道（評価機のまま本番投入しない）。例外承認を取るなら期限と補償制御
  （経路暗号化の多層化など）をセットで
- **考察4**: 「このゲートウェイに policy が無い」。Cisco はルーティングが通信の
  意思決定者（トンネルが上がれば流れる）、FGT は**ポリシーが意思決定者**
  （通す相手が定義されるまで VPN すら張らない）
- **考察5-1**: NAT を入れると支社から見た送信元が全て 172.16.255.1（トンネル IP）
  になり、アクセス制御・ログ・逆向き通信（支社→本社の新規セッション）が壊れる。
  サイト間 VPN は「同一社内ネットワークの延伸」なので NAT しないのが原則
- **考察5-2**: 上記 PFS の項参照（リキー時・時限断）

## 実機検証ログ（PoC 2026-07-12）

- RBR: IKEv2 SA READY（Encr: DES, PRF: SHA256, DH Grp:14, Auth: PSK 両方向）・
  Tunnel0 up/up・encaps/decaps 10/10
- FGT: gateway established（direction: initiator になることも）・
  selectors(total,up): 1/1・rx/tx 10/10
- 端末間: pcA⇔pcC ping 5/5 双方向・HTTP「BRANCH SERVER」

## 採点上の注意（出題者向け）

- S5/S6 はポリシー ID 1/2 依存（task.md に ID 指定あり）。ずれたら grade_input.json を目視
- E4 の encaps/decaps は G1-G3 の採点トラフィックで進む（checks の順序が担保）
- 受講者がデバッグを enable したまま放置しがち → 採点前に `diagnose debug disable`
  を打つのが安全（grade は影響を受けないが console が荒れる）
