# PoC: BGP ループバック・ピアリングの debug 実出力 (BL-085) — 2026-08-02

記述式紙面問題（debug を読んで両側の config を推定し、修正案を書く）の素材採取。
環境: IOL iol-xe 17.15 ×4（problems/_POC-BGPDBG）。

## ★結論: 形式は成立する。ただし「片側だけ update-source 欠け」は故障にならない

### 発見1: iBGP で片側だけ `update-source` が無くてもセッションは **UP する**

- RT01: `neighbor 2.2.2.2` + `update-source Lo0` / RT02: `neighbor 1.1.1.1`（update-source 無し）
- 結果: **`%BGP-5-ADJCHANGE: neighbor 2.2.2.2 Up`（両側 Established）**
- 理由: RT02 発の接続（src=10.0.12.2）は RT01 に拒否されるが、**RT01 発の接続
  （src=1.1.1.1）は RT02 の `neighbor 1.1.1.1` に一致して受理**される。
  接続レースで「update-source を持つ側が開いた接続」が生き残る。
- → **出題では「片側 update-source 欠け」単独を故障として使わない**こと（症状が出ない）。

### 発見2: 「neighbor 文の指す先が食い違う」= 両側 Idle・debug に両側の実像が出る

構成: RT01 `neighbor 2.2.2.2` + `update-source Lo0` / RT02 `neighbor 10.0.12.1`（物理宛・
update-source 無し）。**これが記述式問題の本命素材**。

RT01 側:
```
BGP: 2.2.2.2 active went from Idle to Active
BGP: 2.2.2.2 open active, local address 1.1.1.1
BGP: 2.2.2.2 open failed: Connection refused by remote host
BGP: 2.2.2.2 Active open failed - tcb is not available, open active delayed ...
BGP: ses global 2.2.2.2 (...) act Reset (Active open failed).
BGP: 2.2.2.2 active went from Active to Idle
```
RT02 側:
```
BGP: 10.0.12.1 active went from Idle to Active
BGP: 10.0.12.1 open active, local address 10.0.12.2
BGP: 10.0.12.1 open failed: Connection refused by remote host
...
```
**読み取れること（＝設問の答えの骨格）**
- `open active, local address <X>` … その機が **どの送信元で開きに行ったか**。
  RT01=1.1.1.1（Lo）→ update-source Lo0 あり / RT02=10.0.12.2（物理）→ update-source 無し。
- 宛先（行頭の `<peer>`）… その機の **neighbor 文の宛先**。RT01→2.2.2.2（Lo宛）/
  RT02→10.0.12.1（**物理宛**）。両者が非対称であることが確定する。
- `Connection refused by remote host` … 相手が **その送信元を neighbor として持っていない**
  （TCP RST）。到達性の問題ではない（＝経路・IF は生きている）。

### 発見3: eBGP ループバック・ピア × `ebgp-multihop` 無し の signature

構成: RT03/RT04 とも Lo ピア＋`update-source Lo0`＋対向 Lo への static あり。multihop 無し。
```
BGP: 4.4.4.4 Active open failed - no route to peer, open active delayed 12288ms (35000ms max, 60% jitter)
```
- **`no route to peer`** ＝ eBGP のシングルホップ検査（connected check）に落ちている。
  static で経路はあるのに出る点が肝（「経路が無い」の字面に釣られると誤診する）。
- `show ip bgp summary` は **Idle**・`Connections established 0`。
- 修正= 両側に `neighbor <peer> ebgp-multihop 2`（または `disable-connected-check`）。

## 出題への反映

- 記述式の主素材は **発見2**（両側の debug から両側の config を再構成できる）。
- 変種として **発見3**（multihop 欠け・`no route to peer` の誤読を誘う）。
- 発見1 は「**なぜ片側欠けでも UP するのか**」を問う上級変種（または赤ニシン）に使える。
- 収集は console（`show logging | include BGP:`）。`debug ip bgp` を有効化してから
  再試行を待って採る（本番の紙面問題では PoC で採った実出力を素材として使う）。

---

# PoC 続編: 変種追加の実測 (BL-136(b)・2026-08-23) — probe2.py

盤面= `_POC-BGPDBG2`(IOL 2台・Lo/物理 back-to-back)。生ログ= results-probe2.md。
bgpdbg の変種3→7への拡張素材。★採取の教訓= `clear logging` の [confirm] は
コンソールを1コマンドずらす→ **`logging buffered` のサイズ付け直しで無プロンプト
クリア**が安全。

## 確定した指紋(4点)

1. **password 不一致(b1)**: 両側に `%TCP-6-BADAUTH: Invalid MD5 digest from <peer>(<port>)
   to <own>(179)` が再送間隔で並び、約30秒で `open failed: Connection timed out;
   remote host not responding` → Idle。
2. **★片側だけ password(b1b)**: `No MD5 digest`(Invalid ではない)が**両方向**
   ((179)発と(eph)発)で出る。★**BADAUTH を記録するのは password を持つ側だけ**
   — 持たない側のログは静かに Active open failed するのみ。Invalid/No の読み分け
   +出る側の非対称、の2軸が読解の決め手。
3. **remote-as 誤り(b2)**: 誤設定側= `bad OPEN, remote AS is <actual>, expected
   <wrong>` → `%BGP-3-NOTIFICATION: sent ... 2/2 (peer in wrong AS) 2 bytes <hex>`
   (hex= 相手 AS の16進・実測 FDEA=65002)。健全側= OpenConfirm まで進んで
   `NOTIFICATION: received`。**sent/received で犯人の側が割れる**。summary の
   AS 列には誤設定値がそのまま出る(状態 Closing/Idle)。
4. **neighbor shutdown(b3)**: 残骸側= debug を有効にしても**一切の行が出ない**
   (FSM 不動作)+ summary `Idle (Admin)`。対向= `Connection refused` の周期。
   ★debug だけでは「neighbor 文が無い」と区別できないため、**この変種のみ
   summary を紙面に提示する**(設計判断・gen_paper_bgpdbg 参照)。

> ★CML の `_POC-BGPDBG2` は 2026-09-05 に削除済(BL-136 完了・実測は results-probe2.md に保存済。盤面は IOL 2台 back-to-back で手組み再現可)。
