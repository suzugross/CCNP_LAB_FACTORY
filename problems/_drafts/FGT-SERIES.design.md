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

### ★完了（2026-07-12・実機フルサイクル build 0/100 → solve → 100/100 一発）

成果物= problems/FGT-REPLACE-01/（task.md・running-config.txt・grading.yml・
ANSWER_KEY.md）・topologies/fgtreplace_ops.py・poc/fortigate/golden-replace-fgt.cfg。
UNBUILD（sdwan_ops.py 共用）に SRV-VIP / SNAT-POOL の冪等 delete を追加済み。
採点の検出器設計: G4(ping 2.2.2.1)=port-forward 解を弾く / S6(poolname)=nat enable
素通し解を弾く / G5=SL 暗黙許可の移行漏れを弾く。以下は設計記録。

- **形式**: 「現行 ASA の running-config（**紙面提供・ノード起動しない**）を読み解き、
  同一要件を FGT で再実装せよ」＝実務のリプレース案件の再現。
  題材= UM2-BUILD-01 FW1 の day0 config（原本= poc/um2/poc-um2-onearm-lab.yaml →
  問題パックに running-config.txt として同梱）
- **ASA を立てない理由**: ①config がワンアームで UM2 世界（VLAN243/244/254・LB VIP・
  L3SW HSRP）を参照→生かすには UM2 の半分が必要で20ノード上限と衝突（それは
  UM2-BUILD-01 として既存） ②学習目標は config 読解と概念変換であって ASA 操作ではない。
  ライブカットオーバー型は反響を見て変種（+asav 1台=13ノードで枠内）
- **位置づけ**: 実質2機種分の知識を要求 → BASIC-01・IPSEC-01 クリア後の「卒業試験」

### 概念対応（受講者に自力で作らせる移行設計表＝問題の核）

| ASA（読む） | FGT（作る） | 教材ポイント |
|---|---|---|
| security-level 100/50/0 | ゾーン＋**明示ポリシー** | inside→dmz の SL 暗黙許可が FGT では消える（明示ポリシー忘れ＝移行漏れの定番） |
| ACL OUTSIDE-IN（実IP宛 icmp+www） | WAN→DMZ ポリシー（dst=**VIPオブジェクト**・PING+HTTP） | ASA 8.3実IP規約 vs FGT のVIP参照 |
| object NAT static 172.16.250.1⇔2.2.2.1 | VIP（extip=2.2.2.1 **オフサブネット**） | グローバルIPは移行で「持っていく」 |
| global+nat dynamic PAT→2.2.2.10 | IPプール 2.2.2.10 ＋ LAN→WAN ポリシーで参照 | |
| ワンアーム dot1q ×3 | **3物理IF へ再設計**（eval=VLANサブIF不可） | 制約を逆手に取る設計判断 |
| route 4本 | static は default 1本のみ（他は connected 化） | eval=ルート3本上限とも整合 |
| inspect icmp | 設定不要（FGT は既定ステートフル） | 考察課題 |
| failover/monitor-interface/standby IP | **移行対象外**と判断させる | 考察課題（FGT なら FGCP。eval 制約で不可も解説） |

### アドレス読替表（task.md に添付・FGT-LAB 現行アドレスは不変更）

outside 172.16.243.0/24→port1 203.0.113.0/30(自IP.2/GW.1) / inside 172.16.100.0/24
（Trust）→port3 10.1.10.0/24(LAN兼管理) / dmz 172.16.254.0/24→port2 172.16.10.0/24 /
サーバ実IP 172.16.250.1(LB VIP)→dmz1 172.16.10.10 / **マップIP 2.2.2.1・PAT IP 2.2.2.10
は原文どおり継続使用**（ISP1 に /32 静的経路×2 を fgt1 向けに追加・wr mem。
BL-048 の RBR 経路追加と同じ前例・他問題に無害）

### 教材構成（体験型 Phase1-5・FGT シリーズの型）

1. **現行構成の読み解き**: running-config.txt から要件表を起こす（📋各行の意味）
2. **移行設計**: 概念対応表＋アドレス読替を自分で埋める（🤔SL暗黙許可はどこへ？）
3. **FGT 実装**: IF→オブジェクト→VIP/IPプール→ポリシー3本（eval 上限ぴったり）
4. **挙動検証**: PAT 送信元の確認（session list）/ pcB→2.2.2.1 HTTP・ping /
   LAN→dmz / 移行漏れを debug flow で自己診断
5. **考察**: inspect icmp の行方・移行対象外項目の一覧化（実務の移行判断表）

### 採点スケッチ（fgtreplace_ops.py = fgtbasic_ops.py 骨格流用・0点発射→100点）

S1 IF設計(port1/2/3 IP+role) / S2 オブジェクト / S3 default route 1本 /
S4 pcA→pcB 疎通＋**送信元が 2.2.2.10**（diagnose sys session list） /
S5 pcB→2.2.2.1 の HTTP 200＋ping（オフサブネットVIP） / S6 pcA→dmz1 HTTP
（明示ポリシー＝SL暗黙許可の移行漏れ検出） / S7 負の要件: pcB→pcA 直宛 deny
（暗黙deny生存確認）。ポリシーID 1/2/3 は task.md で指定（BASIC-01 と同じ運用）

### PoC 結果（2026-07-12 全✅・実装可）

- [x] **fgt1 eval 再アクティベーション**（新 S/N **FGVMEVSVGQCAU4C8**・確立手順どおり
      一発成功。★FGT-LAB はラボごと削除されていたため fgt-lab.yaml から再インポートで
      復旧。★day0 罠を2件修復: ISP1/ISP2 の 198.51.101.0/30 経路が NVRAM のみで
      エクスポート未反映→焼き込み＋BL-049 用 2.2.2.0/28 経路も day0 化）
- [x] **オフサブネット VIP**: extip 2.2.2.1（port1 /30 サブネット外）＋ISP1 静的経路
      `2.2.2.0/28 → 203.0.113.2` で **DNAT 完全動作**（pcB→2.2.2.1 の HTTP 200
      "DMZ SERVER"＋ping 3/3。session: `act=dnat 198.51.100.100→2.2.2.1(172.16.10.10)`）
      → BASIC-01 の「/30 だから自IP port-forward」制約を超えて ASA 忠実形が成立
- [x] **オフサブネット ippool** 2.2.2.10 の SNAT 動作
      （session: `act=snat 10.1.10.12→198.51.100.100(2.2.2.10)`）
- [x] eval 上限内: IF 3（port1/2/3）・policy 3本・static route 1本 — 全て投入エラーゼロ
- ★実機知見: **eval ライセンス反映（warm reboot）で4本目 vNIC(port4) が QEMU から消える**
      （アクティベーション用 NAT 経路は未ライセンス時のみ有効＝一時 nat-tmp ノード方式で
      正解。撤去済・ラボは正準12ノード）

## その他（登録のみ・小ネタ）

- **FGT-TS シリーズ**（将来の生成器候補）: ポリシー順序ミス / NAT欠落 / VIP作ったが
  ポリシー無し / RPF ドロップ（FGT strict RPF）。BASIC-01 の題材がそのまま故障カタログになる
- **VDOM 入門**: eval は VDOM 2個まで可。ただし 3IF 制約下では窮屈 → 優先度低
- 「未ライセンス＝スルー転送だけ死ぬ」現象: 意図的に作るとライセンスが戻せないため
  **出題不可**（座学解説ネタ止まり）
- ライセンス済ディスクの CML イメージ焼き込み（未検証・成功すれば複数FGT解禁）
