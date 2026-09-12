# 模範解答 : GEN-RDFIELD-3381

## 役割の種明かし
BR1=RT03, BR2=RT05, D0I1=RT01, D0I2=RT04, D2I1=RT02(ドメイン: EIGRP AS 136 / EIGRP AS 504 / EIGRP AS 193)

## 故障と是正
### RT03 / router eigrp 504 (wrong_id)
redistribute の参照 ID が誤り(存在しないプロセス/AS を参照=無言で経路ゼロ)。誤行を `no` で除去し `redistribute eigrp 136 metric 100000 100 255 1 1500` を投入。
### RT05 / router eigrp 193 (missing)
注入方向が丸ごと欠落。`redistribute eigrp 504 metric 100000 100 255 1 1500` を投入。

投入後 `clear ip route *`(対象 BR)。

## 教育核心
再配送の故障は「無い」「参照が違う」「seed が無い」「絞りすぎ」の4型がほとんど。
config の**見た目の完備**と**実効**(show ip route / show ip protocols の
Redistributing 節)を突き合わせるのが切り分けの型。
