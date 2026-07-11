# ENCOR-QOS-POLICE-01 模範解答

## 解法の考え方

CLASS-01 で覚えた MQC 3点セットの「アクション」を `set dscp` から `police` に
替えるだけ——ただし**分類を対象トラフィックに限定する**のが本問の核心。
class-default に丸ごと police を掛けると要件2（他に影響を与えない）を割る
（採点は「police クラスが match any でない」構造 + UDP 素通りの実測で検出する。
興味深いことに **ICMP は class-default 丸ごと police でもほぼ無傷**——TCP が
輻輳制御で CIR 付近に自制するため、小さな ping ぶんのトークンは大抵残っている。
巻き添えが数値に出るのは UDP のような「遠慮しない」トラフィック。実機検証済）。

- **policing**: 超過分をその場で破棄（バッファしない）。TCP はパケットロスを
  輻輳と解釈して自ら送信レートを下げるため、実測スループットは CIR 近辺
  （実測 0.9〜1.0Mbps）に落ち着く。
- **shaping との違い**（LLQ-01 で使う）: shaping は超過分をキューに溜めて平滑化
  =遅延が増える。policing は遅延を増やさない代わりにロスで抑える。

## 設定 (RT01)

```
ip access-list extended ACL-BACKUP
 permit tcp any any eq 5201
!
class-map match-all C-BACKUP
 match access-group name ACL-BACKUP
!
policy-map LIMIT-BACKUP
 class C-BACKUP
  police cir 1000000 conform-action transmit exceed-action drop
!
interface Ethernet0/1
 service-policy output LIMIT-BACKUP
```

※ 名前は任意。`police 1000000`（旧形式）でも同じ状態になる。
※ 適用場所は「WAN 出力」= E0/1 output（要件どおり）。E0/0 input でも
  「PC01発のバックアップ」には効くが、拠点1に端末が増えた場合や
  RT01 自身が発するトラフィックの扱いが変わる。WAN 帯域を守る目的なら
  WAN 出力に置くのが素直。

## 期待される測定値（実機 PoC 2026-07-08 の実測）

| 測定 | 実装前 | 実装後 |
|------|--------|--------|
| A: TCP スループット | 〜168 Mbps | **〜0.94 Mbps** |
| B: 転送中の ping | ほぼ無傷 | **無傷のまま** (loss 0% / avg 数ms) |
| C: UDP 5Mbps | 素通り | **素通りのまま** (制限対象外) |
| RT01 conformed/exceeded | - | 両方増加（exceeded = 破棄された超過分） |

## 補足（採点後レビュー用）

1. **なぜ TCP は 1Mbps に「落ち着く」のか**: ポリサはただ超過を破棄するだけ。
   レートを合わせているのは送信側 TCP の輻輳制御（ロス→ウィンドウ縮小）。
   つまりネットワークは「ロスというシグナル」で端末を躾けている。
2. **UDP に同じポリサを掛けたら**: 送信側は落ちたことを気にせず 5Mbps を
   送り続け、超過分 80% がただ捨てられ続ける（PoC 実測 67% loss）。
   リアルタイム系に policing が乱暴な理由。LLQ-01 で shaping+優先制御と比較する。
3. **bc (burst) の既定値**: `police cir 1000000` の bc 既定は cir/32 (31250 bytes)。
   バーストの許容量で瞬間的な超過の扱いが変わる。厳しすぎる bc は TCP の
   スループットを CIR よりだいぶ下に押し込むことがある。
4. police は**輻輳に関係なく常時**働く（LLQ の priority 内蔵ポリサが
   「輻輳時のみ」なのと対照的——LLQ-01 で再登場する論点）。
