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
