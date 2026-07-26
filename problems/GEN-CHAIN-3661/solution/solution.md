# GEN-CHAIN-3661 解答（採点者用）

連鎖: L1:l1_ospf_auth → L2:l2_wrong_neighbor_ip → L3:l3_nh_passive_missing

## L1: l1_ospf_auth
RT11 側 West アクセスIF のみ OSPF MD5 認証が有効(RT01側は無し)

## L2: l2_wrong_neighbor_ip
RT01 のRRピアが Loopback でなく物理リンクIPを指している(双方向とも neighbor 不一致でセッション不成立)

## L3: l3_nh_passive_missing
両境界の EIGRP側リンク(172.30.x)が OSPF に広告されていない(E2B経路の BGP next-hop が解決不能→RRで no best・East経路が配られない)

## おとり（無害・修正不要）
- RT05: dc_legacy_acl（未適用/無影響の残骸。削除しなくても減点なし）

修復は solution/fix.json（fix_generated.yml で投入可）。
下位レイヤから直すのが素直だが、順序は自由（採点は結果主義）。
