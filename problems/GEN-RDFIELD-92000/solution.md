# 模範解答 : GEN-RDFIELD-92000

## 役割の種明かし
BR1=RT02, BR2=RT06, D0I1=RT05, D0I2=RT01, D1I1=RT03, D2I1=RT04(ドメイン: EIGRP AS 589 / OSPF 90 / OSPF 84)

## 故障と是正
### RT02 / router ospf 90 (name_clash)
route-map RM-SVC の `match ip address SVC` が、**同名の standard ACL** (`permit 12.12.12.12`)に束縛されている(`prefix-list` キーワードが無い)。prefix-list SVC は参照されず、ACL の 1 本以外は暗黙 deny で全喪失。収容標準はフィルタ禁止なので `no redistribute ...` → `redistribute eigrp 589 subnets` で貼り替え、route-map/prefix-list/ACL も撤去。
### RT06 / router ospf 84 (wrong_id)
redistribute の参照 ID が誤り(存在しないプロセス/AS を参照=無言で経路ゼロ)。誤行を `no` で除去し `redistribute ospf 90 match internal external 1 external 2 subnets` を投入。

投入後 `clear ip route *`(対象 BR)。

## 教育核心
再配送の故障は「無い」「参照が違う」「seed が無い」「絞りすぎ」の4型がほとんど。
config の**見た目の完備**と**実効**(show ip route / show ip protocols の
Redistributing 節)を突き合わせるのが切り分けの型。
