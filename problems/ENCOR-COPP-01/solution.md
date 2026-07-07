# 模範解答 : ENCOR-COPP-01

```
ip access-list extended COPP-ICMP
 permit icmp any any

class-map match-all CM-ICMP
 match access-group name COPP-ICMP

policy-map PM-COPP
 class CM-ICMP
  police 8000 conform-action transmit exceed-action drop

control-plane
 service-policy input PM-COPP
```

## 確認
```
show policy-map control-plane
show ip access-lists
```

### ポイント（落とし穴の解説）
- CoPP は通常インタフェースではなく **`control-plane`** に **`service-policy input`** で適用する。
- ポリシングは `police <bps> conform-action transmit exceed-action drop` の形。
  単位の既定は bps（`police 8000` = 8000 bps）。`bc`（バースト）は省略時に自動計算される。
- 対象を ICMP に限定するため、ACL で `permit icmp any any` を作り class-map で参照する。
  CoPP の class-default を触ると他の正当な制御トラフィックまで巻き込むので、専用クラスで絞る。

> 採点は最終状態（control-plane 入力ポリシーに ICMP を拾うクラスがあり、
> police 8000 / 超過 drop / 適合 transmit になっていること、および ICMP を許可する ACL の存在）で判定する。
> クラス名・ポリシー名・ACL 名は任意。
