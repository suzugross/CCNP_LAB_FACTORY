# FGT 作問シリーズ 構想メモ（BL-048 / BL-049 ほか）

FortiGate 基盤（BL-045 で確立・メモリ ccnp-fortigate）上の作問候補。
共通制約: **eval=IF総数3個上限 / wipe=ライセンス消失 / ライセンス済 fgt1 は1台のみ**
（2台構成の HA・FGT同士のVPN は不可）。ラボは共用ラボ "FGT-LAB"（BL-047 で改修）を使い回す。

## BL-048: FGT-IPSEC-01 — Cisco IOS ⇄ FGT サイト間 IPsec VPN（interop）

### ★完了（2026-07-12・実機フルサイクル 0/100→solve→100/100 一発）

**PoC 確定事項**（作問全般に効く）:
- **トンネル IF は eval「IF 3個上限」の対象外**（phase1-interface → type:tunnel 正常生成）
- **eval は LENC（低暗号）ビルド**: 暗号は DES 系のみ（des-md5/sha1/sha256/sha384/sha512・
  AES/3DES は parse error）→ interop は des-sha256/DH14 で統一（IOSv IKEv2 は des 対応）
- **eval はファイアウォールポリシー最大3本**（4本目= `-4 reached the maximum number of entries`）
- **FGT はトンネル IF 参照ポリシーが無いと IKE ネゴ自体を拒否**:
  指紋= `ignoring IKEv2 request, no policy configured` / 対向 Cisco には
  NO_PROPOSAL_CHOSEN が届く（proposal は合っているのに！）→ 両側デバッグ教材の核
- PFS: FGT phase2 既定有効 → IOS ipsec profile に `set pfs group14` 明示で整合
- **IOSv ノードへの IF 追加は物理構成ロックで拒否** → wipe + day0（旧 running-config
  吸い上げ＋追記）で再焼成する（INET Gi0/3 で実施済）

**ラボ増設（済）**: INET Gi0/3(198.51.101.1/30) — RBR(iosv・day0=WAN/LAN/デフォルト
ルート/login local) — pcC(alpine 192.168.20.10・httpd「BRANCH SERVER」)。
ISP1/ISP2 に 198.51.101.0/30 静的経路（wr mem 済）。12ノード。
console() は Username: プロンプト対応を追加（sdwan_ops.py）。

**成果物**: problems/FGT-IPSEC-01/・topologies/fgtipsec_ops.py・
poc/fortigate/golden-ipsec-{fgt,rbr}.cfg

### 当初設計（参考）

- **トポロジ**: fgt1（port1=WAN・port3=LAN）⇔ INET ⇔ Cisco IOS ルータ（sVTI）＋対向LAN。
  3IF中2本で足りる。IOS 側は既存 sVTI×IKEv2 資産（GREIPSEC 規約・golden）を流用
- **中身**: FGT の route-based VPN（`config vpn ipsec phase1-interface / phase2-interface`）
  と IOS sVTI を IKEv2 で対向。トンネルIFに static ルートを載せて LAN 間疎通
- **interop ならではの学習点**:
  - proposal/PFS 不一致を `diagnose vpn ike log-filter`＋`diagnose debug application ike -1`
    と IOS `debug crypto ikev2` の**両側から突き合わせて**デバッグ
  - Phase2 セレクタ: VTI の 0.0.0.0/0 と FGT quick mode selector の噛み合わせ（interop 最頻出罠）
- **リスク**: interop 自体が未PoC → 作問前に 1日 PoC（proposal組合せ・セレクタ・NAT-T 有無）
- 備考: FortiOS 7.6 は 2GB RAM 機で SSL-VPN 廃止 → リモートアクセス系をやるなら
  IPsec dial-up 一択（これも要PoC・優先度低）

## BL-049: FGT-REPLACE-01 — ASA→FortiGate リプレース体験

- **形式**: 「現行 ASA の running-config（紙面提供）を読み解き、同一要件を FGT で再実装せよ」
  ＝実務のリプレース案件そのもの。題材は UM2-BUILD-01 の ASA config を流用
- **概念対応を自力で作らせるのが肝**: security-level→ゾーン＋ポリシー / ACL→firewall policy /
  object network static NAT→VIP / global+nat→IPプール / inspection→セッションヘルパ
- **制約との折り合い**: ASA 側は読むだけなので IF 数自由。FGT 実装は 3IF に圧縮した縮小版仕様
- **位置づけ**: 実質2機種分の知識を要求 → BASIC-01・IPSEC-01 クリア後の「卒業試験」

## その他（登録のみ・小ネタ）

- **FGT-TS シリーズ**（将来の生成器候補）: ポリシー順序ミス / NAT欠落 / VIP作ったが
  ポリシー無し / RPF ドロップ（FGT strict RPF）。BASIC-01 の題材がそのまま故障カタログになる
- **VDOM 入門**: eval は VDOM 2個まで可。ただし 3IF 制約下では窮屈 → 優先度低
- 「未ライセンス＝スルー転送だけ死ぬ」現象: 意図的に作るとライセンスが戻せないため
  **出題不可**（座学解説ネタ止まり）
- ライセンス済ディスクの CML イメージ焼き込み（未検証・成功すれば複数FGT解禁）
