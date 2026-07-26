# GEN-S2SVPN PoC (BL-063) — 結果 (2026-07-24)

複数拠点 S2S VPN 設計構築問（要件書形式・技術選定自由）の事前検証。
**主要6項目すべて成立 → 生成器実装に進める**。

## 検証環境（poc-s2svpn-lab.yaml・6ノード・コンソールのみ／MGMTリース不使用）

```
 H-HQ(alpine .101) ─ HQ(IOSv) ─ 203.0.113.0/30 ─┐
                     192.168.10.0/24            INET(IOL・変更禁止役) ─ SRV(alpine 198.51.100.80・busybox httpd)
 H-B1(alpine .101) ─ BR1(IOSv) ─ 203.0.113.4/30 ─┘
                     192.168.11.0/24
```

- HQ/BR1 = IOSv 15.9（DMVPN 選択肢保証のため）・INET = iol-xe 17.15
- day0 = NAPT(overload)+default のみのクリーン状態。crypto は全てコンソールから段階投入
- ドライバ = `poc_console.py`（pexpect・IOS/alpine 両対応。alpine は root ログイン）

## 検証結果

### 1. NAPT ベースライン＋出口公開IP判定（採点部品）✅

- 両ホストから SRV へ ping/wget 成功（`SRV-OK`）。busybox httpd は day0 焼込みで安定。
- **INET の `JUDGE-SRV` ACL（SRV向けIF out）で出口公開IPを機械判定できる**:
  `permit ip host 203.0.113.2 host 198.51.100.80` / `permit ip host 203.0.113.6 ...` の
  行別カウンタが送信元サイトごとに独立カウント。`clear access-list counters` → テスト →
  読取の手順で split/full の判定が成立（フルトンネル時は行10のみ増・行20=0 を実測）。
- RFC1918 平文漏れ検出用に `deny 10/172.16/192.168` 行 + `CATCH-LEAK-*`(WAN IF in) も設置済み。

### 2. sVTI × NAT overload 同居 — **deny 不要**（仮説どおり）✅

- Tunnel0(tunnel mode ipsec ipv4) + `ip nat inside source list <LANのみpermit> ... overload` の
  同居で、拠点間 5/5・**NAT テーブルに VPN トラフィックのエントリなし**・encaps/decaps=5/5。
- 理由: route-based では LAN間トラフィックが Tunnel0（nat outside でない）から出るため
  NAT が発火しない。**NAT ACL の deny は不要**。

### 3. crypto map × NAT overload — **古典罠が完全再現・deny 必須** ✅（教材の核）

- 同じ NAT のまま crypto map(Gi0/0) に組み替え → 拠点間 **100% loss**。
- ★診断指紋（実機採取）:
  - `show ip nat translations` に **`203.0.113.6 ← 192.168.11.101 → 192.168.10.101`**
    （VPN対象トラフィックが PAT に先取りされた動かぬ証拠）
  - `show crypto ipsec sa` **encaps: 0**（crypto ACL 不一致で一度も暗号化されない）
  - `show crypto isakmp sa` は **MM_NO_STATE (deleted)** 往復（トラフィック起動が空振り）
- 修正 = NAT ACL を extended 化し **`deny ip <自LAN> <相手LAN>`** を先頭に →
  ping 4/5（初弾は IKE ネゴで喪失・正常）・encaps 増・ブレイクアウト無傷。
- **罠の有無が技術選択で変わる**（sVTI=罠なし / crypto map=deny必須）→ 効果ベース採点なら
  どちらの解でも公平。task.md はどちらを選んでも成立する書き方にする。

### 4. フルトンネル × HQ ヘアピン NAT — **完全動作**（最重要項目）✅

- BR1: `ip route 0.0.0.0 0.0.0.0 Tunnel0` + **ピア向け host route**
  (`ip route 203.0.113.0 255.255.255.252 203.0.113.5`)・ローカル NAT は発火しなくなる（残置可）。
- HQ: **Tunnel0 に `ip nat inside`**＋NAT ACL に支店LAN (`permit ip 192.168.11.0 0.0.0.255 any`) 追加。
- 実測: H-B1→SRV の ping/HTTP 成功・**HQ の NAT テーブルに
  `203.0.113.2 ← 192.168.11.101 → 198.51.100.80`**・JUDGE 行10(HQ IP)のみカウント。
- 拠点間通信は inside→inside になるため **NAT 非適用のまま**（deny 不要・実測 3/3）。

### 5. 再帰ルーティング指紋（フルトンネルの定番事故）✅

- host route を撤去（default via Tunnel0 だけにする）→
  **`%ADJ-5-PARENT: ... looped chain attempting to stack`** →
  **`%TUN-5-RECURDOWN: Tunnel0 temporarily disabled due to recursive routing`** → up/down フラップ。
- ★sVTI(p2p) は RECURDOWN を**明示発出する**（mGRE は非発出の既知知見と対照的・出題時の
  切り分け素材として優秀）。
- 修正（host route 再投入）後の復旧は**自動だが 1〜2 分**（RECURDOWN ホールドダウン＋IKE 再確立）
  → 採点は修正後に settle 時間を置くこと。

### 6. コンソール運用の注意

- `clear crypto ipsec counters` は IOSv に**存在しない**（正= `clear crypto sa counters`）。
- alpine は day0 スクリプト焼込みで IP/route/httpd 全て安定。root ログイン（パスワード無し）。
- IOSv の `no ip nat inside source list ...` は動的エントリ残存時に失敗し得る →
  先に exec で `clear ip nat translation *`。

## 残項目（本実装時に消化・リスク低）

- 支店間「限定許可」ポリシーの採点安定性（支店2つ必要 → 本実装トポロジで確認）
- DMVPN 解での採点中立性（JUDGE/encaps 判定は方式非依存のはず・既存 gen_dmvpn 資産で確認容易）
- MTU/MSS 要件の regex ＋ df-bit スイープ採点（既存 DMVPN 問の流用）

## 追加 PoC (2026-07-25・BL-064 シナリオ③): NAT overlapping × IPsec

同ラボ再起動で検証。**吸収拠点のサブネット完全重複を単側 NAT で解消するレシピを確立**。

1. **`ip nat inside source static network <real> <alias> /24`**(ネットワーク形):
   VTI(Tunnel を `ip nat outside`)越しに双方向動作するが、**無条件のため
   インターネット向けトラフィックまで先取り変換**して NAPT 併存を破壊(実測 100% loss)。
   **route-map 後置は IOSv 15.9 で構文非対応**(% Invalid)。
2. **正解=ホスト単位 static + route-map**: `ip nat inside source static <real> <alias>
   route-map RM-OVL`(RM は VPN 宛のみ permit)。外部発(HQ→エイリアス)のコールド開始も
   逆変換が動く・PAT と完全併存(実測: 実→実 4/4・HQ→alias 4/4・SRV-OK)。
3. ★**Tunnel を nat outside にした時点で、動的 PAT がトンネル出口にも適用される**→
   sVTI でも NAT ACL の VPN 宛 deny が必須になる(BL-063 では sVTI=deny 不要だった罠が
   overlap 文脈で再登場する教材的連続性)。
4. 壊れ方の指紋(D2 チケット#3 broken 実測): SA UP・吸収拠点発 encaps 増加・
   HQ の戻りが「重複プレフィックスを正規に持つ既存支店のトンネル」へ吸われて消える／
   INET CATCH-LEAK に private-src(行30)と alias宛ルート無し(行50)のヒット。

## 再現手順

1. 投入: `import_lab(poc/s2svpn/poc-s2svpn-lab.yaml)` → `lab.start(wait=True)`（起動後 約2分待ち）
2. 操作: `poc_console.py --node <名> --exec/--config/--sh ...`（区切り `;;`）
3. **ラボは POC-S2SVPN として STOPPED 退避中**（day0=クリーン NAPT ベースライン・
   crypto 投入分は write mem していないので stop/start で初期状態に戻る）。
   BL-064 シナリオ③（NAT overlapping × IPsec）の PoC に再利用予定。
