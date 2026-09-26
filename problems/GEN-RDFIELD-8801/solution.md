# 模範解答 : GEN-RDFIELD-8801

## 役割の種明かし
BR1=RT04, D0I1=RT03, D0I2=RT02, D1I1=RT01(ドメイン: EIGRP AS 820 / OSPF 82)

## 故障と是正
### RT04 / router eigrp 820 (missing)
注入方向が丸ごと欠落。`redistribute ospf 82 match internal external 1 external 2 metric 100000 100 255 1 1500` を投入。
### RT04 / うんざり ACL BORDER-IN(--wall・BL-210)
- 壁 `BORDER-IN`(in・39 エントリ): 欠陥= `missing`(必要な permit が無い(壁のどこにも無い)) / seq= packed(挿入すべき区間の seq が詰まっている(`ip access-list resequence` が要る)) / 世界= in(hub の外側 in のみ)
  - 正解= `permit eigrp any any` を anti-spoof(seq 80)の後・ルータ保護 deny(seq 113)の前に挿入(seq が詰まっているので `ip access-list resequence BORDER-IN 10 10` → seq 345。★IOL では resequence で remark が消える)
  - 見え方: missing/wrong_proto/narrow= 隣接が立たない(hello 224.0.0.x が落ちる・narrow は unicast 行だけ)/ shadowed= hello は通るのに unicast(DBD/Update)が catch-all に落ちる= OSPF EXSTART 固着・EIGRP retry limit。ログ `%SEC-6-IPACCESSLOGNP: list BORDER-IN denied 89|88 <peer> -> 10.139.232.1`
  - 見え方(border): missing/wrong_proto= 隣接が立たない(hello が落ちる)/ narrow= hello(224.0.0.x)が落ちて隣接が立たない / shadowed= hello は通るのに unicast(DBD/Update)が落ちる= OSPF EXSTART 固着・EIGRP retry limit

投入後 `clear ip route *`(対象 BR)。

## 教育核心
再配送の故障は「無い」「参照が違う」「seed が無い」「絞りすぎ」の4型がほとんど。
config の**見た目の完備**と**実効**(show ip route / show ip protocols の
Redistributing 節)を突き合わせるのが切り分けの型。
