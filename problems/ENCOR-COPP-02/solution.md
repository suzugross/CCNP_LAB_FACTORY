# 模範解答 : ENCOR-COPP-02

```
ip access-list extended COPP-ICMP
 permit icmp any any
!
ip access-list extended COPP-TELNET
 permit tcp any any eq 23
!
class-map match-all CM-ICMP
 match access-group name COPP-ICMP
!
class-map match-all CM-TELNET
 match access-group name COPP-TELNET
!
policy-map PM-COPP
 class CM-TELNET
  police 8000 conform-action drop exceed-action drop
 class CM-ICMP
  police 8000 conform-action transmit exceed-action drop
!
control-plane
 service-policy input PM-COPP
```

## 確認
```
show policy-map control-plane
show ip access-lists
```

### ポイント（落とし穴の解説）
- **Telnet の "全廃棄" を policer で表現する**:
  `police <rate> conform-action drop exceed-action drop` とすると、適合トラフィックも
  policer によって drop される ＝ そのクラスにマッチしたトラフィックは全て破棄される。
  rate (8000) は何でもよい (全部 drop なので意味を持たない) が、`police` 文には rate 必須。
- **policy-map のクラス順序に注意**: ポリシーは記述順に評価され、最初にマッチしたクラスで終了。
  `class-default` を先に置くと後続クラスへ届かない。本問では ICMP / Telnet 専用クラスを
  明示しているので順序の影響は出ないが、追加分類を入れる際は注意。
- **class-default を触らない**: そこを police すると、OSPF/SSH 等の正常な制御トラフィックも
  巻き込んで CPU 到達を遅延させてしまう。専用クラスで対象を絞ることが CoPP の基本。
- **CoPP は `control-plane` モードに `service-policy input` で適用**する。通常のインタフェース
  には付けない。

> 採点は「ICMP クラスが police 8000/適合transmit/超過drop」「Telnet クラスが police の
> 適合・超過とも drop」「ICMP/Telnet をそれぞれ識別する ACE が存在」の4効果で判定する。
> クラス/ポリシー/ACL の名前は任意。
