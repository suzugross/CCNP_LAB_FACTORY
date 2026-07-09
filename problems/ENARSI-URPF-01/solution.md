# ENARSI-URPF-01 模範解答

## 解法の考え方

要件2「可能な限り厳格」だけを見て両アップリンクに strict (`reachable-via rx`) を
入れると、**要件3 の顧客B フロー（192.168.100.1 発）が断する**。これが本問の核心。

理由 = **非対称ルーティング**:

- RT01 の 192.168.100.0/24 への経路は **OSPF E2 で Uplink-A (E0/0) 向き**
  （広告しているのは ISP-A。`show ip route 192.168.100.0` で ASBR=2.2.2.2 を確認できる）。
- しかし顧客B はデュアルホームで、**出口には ISP-B を使う**ため、実際のパケットは
  **Uplink-B (E0/1) に着信**する。
- strict uRPF は「送信元への経路が**着信IFを向いている**こと」を要求するため、
  E0/1 着信の 192.168.100.1 発パケットは RPF 不一致でドロップされる。

切り分けの決め手は per-IF の uRPF 統計:

```
RT01# show ip interface Ethernet0/1 | include verif|drops
  IP verify source reachable-via RX
   10 verification drops          ← 正規フローを落としている
```

したがって「技術的に可能な限り厳格」の解釈は:

- **E0/0 (Uplink-A)**: 着信する正規フローは対称のみ → **strict が可能**
- **E0/1 (Uplink-B)**: 正規の非対称着信がある → strict は不可、**loose が上限**

## 設定 (RT01)

```
interface Ethernet0/0
 ip verify unicast source reachable-via rx
!
interface Ethernet0/1
 ip verify unicast source reachable-via any
```

## 別解（満点扱い）: strict + ACL 例外

E0/1 を strict のまま、非対称プレフィックスだけ ACL で救済する構成も
要件をすべて満たす（むしろより厳格。ただし **ACL は番号付き限定**・named は
IOL 17.15 で不受理）:

```
access-list 10 permit 192.168.100.0 0.0.0.255
interface Ethernet0/1
 ip verify unicast source reachable-via rx 10
```

ACL 救済分は `suppressed verification drops` に計上され、通常ドロップと区別できる。

## 検証

```
RT02# ping 1.1.1.1 source 2.2.2.2 repeat 10        → 100%（対称・strict通過）
RT03# ping 1.1.1.1 source 192.168.100.1 repeat 10  → 100%（非対称・loose通過）
RT03# ping 1.1.1.1 source 203.0.113.1 repeat 10    → 0%（経路なし→looseでも drop）
RT01# show ip interface Ethernet0/1 | include verification drops
   10 verification drops                            ← 増分を確認
```

## よくある誤答と配点の挙動（実機検証済み）

| 解答 | 結果 | 点 |
|------|------|----|
| 未解答 | 正規フローは全部通るが uRPF の証拠ゼロ | 35 |
| 両IF strict | 顧客B断（★25点の要件3違反）。ドロップ実証は満点 | 75 |
| 両IF loose | 正規維持は満点だが E0/0 の strict 構成・strict 実証が取れない | 65 |
| RT01 に静的経路を足して対称化 | 要件4違反（前提ガードで検出） | 95 |
| 模範解答 / ACL別解 | 全チェック PASS | 100 |

## 補足（uRPF の実務知識）

- **strict (rx)**: 送信元への best path が着信IFを向いている時のみ通す。
  シングルホーム顧客収容・スタブ側で使う。
- **loose (any)**: 経路表に送信元への経路が「存在」すれば通す（IF は不問）。
  非対称が前提のマルチホーム/コア側で使う。bogon/未割当だけを落とす。
- `allow-default`: default route を RPF の根拠として認めるオプション。
  default がある環境の loose は事実上ザルになるので通常は付けない（本問は
  default 無し設計なので論点外）。
- uRPF は CEF の入力機能（CEF 必須）。自宛（コントロールプレーン宛）パケットにも
  効く（実機実証済み）。
- カウンタは `show ip interface <IF>` の `verification drops`（per-IF）と
  `show ip traffic` の `unicast RPF`（全体）。`clear counters <IF>` でリセット可。
