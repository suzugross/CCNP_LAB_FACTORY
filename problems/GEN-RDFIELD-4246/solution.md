# 模範解答 : GEN-RDFIELD-4246

## 役割の種明かし
BR1=RT02, D0I1=RT01, D1I1=RT03(ドメイン: EIGRP AS 891 / EIGRP AS 629)

## 故障と是正
### RT02 / router eigrp 629 (missing)
注入方向が丸ごと欠落。`redistribute eigrp 891 metric 100000 100 255 1 1500` を投入。

投入後 `clear ip route *`(対象 BR)。

## 教育核心
再配送の故障は「無い」「参照が違う」「seed が無い」「絞りすぎ」の4型がほとんど。
config の**見た目の完備**と**実効**(show ip route / show ip protocols の
Redistributing 節)を突き合わせるのが切り分けの型。
