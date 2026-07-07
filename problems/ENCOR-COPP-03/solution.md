# 模範解答 : ENCOR-COPP-03

RT01 のみ設定する（base 値の例。variant では rate/IP が変わる）。

## RT01
```
! --- 分類用 ACL（守るもの / 制限するもの）---
ip access-list extended COPP-OSPF
 permit ospf any any
ip access-list extended COPP-SSH
 permit tcp any any eq 22
ip access-list extended COPP-ICMP
 permit icmp any any
ip access-list extended COPP-TELNET
 permit tcp any any eq 23
!
class-map match-any CM-OSPF
 match access-group name COPP-OSPF
class-map match-any CM-SSH
 match access-group name COPP-SSH
class-map match-any CM-ICMP
 match access-group name COPP-ICMP
class-map match-any CM-TELNET
 match access-group name COPP-TELNET
!
policy-map PM-COPP
 class CM-OSPF
  ! 無 police = transmit。ルーティングを保護（最優先で許可）
 class CM-SSH
  ! 無 police = transmit。管理 SSH を保護
 class CM-ICMP
  police 8000 conform-action transmit exceed-action drop
 class CM-TELNET
  police 8000 conform-action drop exceed-action drop
 class class-default
  police 32000 conform-action transmit exceed-action drop
!
control-plane
 service-policy input PM-COPP
```

## 確認
```
show policy-map control-plane
show ip access-lists
show ip ospf neighbor          ! FULL のままであること（壊していない証拠）
! RT02 から:
ping <RT01 のリンクIP>          ! 制限下でも疎通する（完全遮断ではない）
```

### 学習核心 / 落とし穴
- **CoPP は「守るもの」を先に明示許可する**。OSPF(proto 89) を transmit クラスに入れずに
  class-default で雑に police/drop すると、Hello/LSA が削られて**隣接が落ちる**。
  本問は隣接 FULL 維持を効果として採点する。
- **管理 (SSH) を必ず保護**する。class-default の police が管理 SSH に効いて
  操作不能になる事故を防ぐ。SSH を専用クラスで transmit に。
- **ICMP は止めずに制限**: `police <rate> conform-action transmit exceed-action drop`。
  適合は通し、超過だけ落とす（運用 ping は残す）。
- **Telnet は完全遮断**: `police <rate> conform-action drop exceed-action drop`。
  適合・超過とも drop ＝ レートに関係なく全廃棄（CoPP-02 と同じイディオム）。
- **class-default も忘れず police**: 未分類トラフィックを既定で制限し、想定外の
  CPU 圧迫を防ぐ。ただし適合 transmit にして管理・正常運用を巻き込まないレートにする。
- police の各クラスは **class-default より前**に並べる（具体クラス→default の順）。

> 採点: OSPF隣接FULL / ICMPクラス(police 指定rate・適合transmit・超過drop) /
> Telnetクラス(適合drop+超過drop) / class-default(police 指定rate・超過drop) /
> ACL(ICMP許可・OSPF許可・Telnet分類・SSH許可) / RT02→RT01 の ICMP 実疎通。
