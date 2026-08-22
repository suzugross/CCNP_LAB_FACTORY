# 模範解答 : GEN-RDFIELD-53369

## 役割の種明かし
BR1=RT04, D0I1=RT03, D0I2=RT05, D1I1=RT01, D1I2=RT02(ドメイン: OSPF 14 / EIGRP AS 308)

## 故障と是正
### RT04 / router ospf 14 (wrong_id)
redistribute の参照 ID が誤り(存在しないプロセス/AS を参照=無言で経路ゼロ)。誤行を `no` で除去し `redistribute eigrp 308 subnets` を投入。

投入後 `clear ip route *`(対象 BR)。

## 教育核心
再配送の故障は「無い」「参照が違う」「seed が無い」「絞りすぎ」の4型がほとんど。
config の**見た目の完備**と**実効**(show ip route / show ip protocols の
Redistributing 節)を突き合わせるのが切り分けの型。
