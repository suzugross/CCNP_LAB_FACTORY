# ENCOR-QOS-LLQ-01 模範解答

## 解法の考え方

要件1「全トラフィック合計で 2Mbps に収める」と要件2「EF を優先」を同時に満たすには
**階層型ポリシー（Hierarchical QoS / parent-child）**が必要。

- 親: `class-default` に `shape average 2000000` — 全トラフィックを 2Mbps の
  ソフトウェアキューへ落とす（＝キャリアに破棄させず自分の管理下で輻輳を作る）。
- 子: シェーパのキュー内で EF を `priority 256` (LLQ) — 輻輳時も EF は
  待ち行列を追い越して送出される。

**フラット1段のポリシー（EF に priority + class-default に shape）は誤答**。
class-default の shape はそのクラスの通過分しか絞らないため、EF がシェーパの外を
素通りし「合計 2Mbps」の契約を守れない（実網ではキャリアが EF ごと破棄する）。
採点でも階層（child_policy_name 配下）を判定しており、フラット構成は
カウンタ系 2 チェックが FAIL する。

## 設定 (RT01)

```
class-map match-all VOICE
 match dscp ef
!
policy-map QOS-CHILD
 class VOICE
  priority 256
!
policy-map QOS-WAN
 class class-default
  shape average 2000000
  service-policy QOS-CHILD
!
interface Ethernet0/1
 service-policy output QOS-WAN
```

※ 名前 (VOICE / QOS-CHILD / QOS-WAN) は任意。
※ 子の class-default に `fair-queue` は**あえて入れない**（下記「補足」参照）。

## 期待される測定値（実機 PoC 2026-07-08 の実測）

| 測定 | 実装前 | 実装後 |
|------|--------|--------|
| A: TCP スループット | 〜168 Mbps | **〜1.8 Mbps**（shape 2M の 91%） |
| B: 輻輳中の EF ping | RTT 〜327ms / loss 〜68% | **RTT 〜1ms / loss 0%** |
| B: 輻輳中の 普通 ping | （実装前は輻輳自体が起きない※） | RTT 〜330ms / loss 〜60% |

※実装前は物理リンクが高速なため 5Mbps 程度では輻輳しない（＝「キャリア破棄」を
自分の shaper で管理下に置いて初めて、ルータ上に観測可能な輻輳が現れる）。

確認: `show policy-map interface Ethernet0/1`
- 親 class-default: `shape (average) cir 2000000` と total drops の増加
- `queue stats for all priority classes`: pkts output 増加・drops 0
- 音声クラス: `Priority: 256 kbps`

## 補足（採点後レビュー用）

1. **fair-queue を子 class-default に入れると何が変わるか**: WFQ が小さいフロー
   （普通の ping）も別キューに隔離して保護するため、「EF だけが助かる」対比が消え、
   普通の ping まで RTT 数 ms になる（それ自体は改善であり実務では有効な選択。
   本問は対比を見るため FIFO のまま）。
2. **priority 256 の内蔵ポリサ**: 輻輳中、EF クラス自身が 256kbps を超えると
   超過分は破棄される（`b/w exceed drops`）。音声本数の見積もりを誤ると
   「LLQ にしたのに音声が死ぬ」障害になる（PoC 実測: EF に 1Mbps を流すと 76% loss）。
3. **shape average の bc/be 既定**: IOS が cir から自動算出（2M → bc/be 8000bit)。
   音声の遅延要件が厳しい場合は bc を小さくして Tc を詰める余地がある。
4. GRE/IPsec 併用時は `qos pre-classify`、帯域見積りには L2 ヘッダ扱いの差
   （shape はデフォルトで L2 長）も実務上の論点。
