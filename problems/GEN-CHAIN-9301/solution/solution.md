# GEN-CHAIN-9301 解答（採点者用）

連鎖: L1:l1_mtu_mismatch → L1:l1_area_mismatch → L2:l2_rr_client_break → L2:l2_password_mismatch → L3:l3_redist_internal_missing → L3:l3_nh_passive_missing

## L1: l1_mtu_mismatch
RT01 側 West アクセスIF に ip mtu 1400 (EXSTART 固着)

## L1: l1_area_mismatch
RT01 の West アクセスIF が area 2 で設定されている(正: area 1)

## L2: l2_rr_client_break
両RRで RT01/RT07/RT09 の route-reflector-client が外されている(非client同士は反射されず West↔East の経路交換が途絶)

## L2: l2_password_mismatch
RT01 の急所ピア(RT03/RT04)にだけ MD5 パスワード(相手側は無し→セッション不成立)

## L3: l3_redist_internal_missing
両境界の BGP に bgp redistribute-internal が無い(IOS既定=iBGP経路はIGPへ再配送されない→East に West の戻り経路が皆無)

## L3: l3_nh_passive_missing
両境界の EIGRP側リンク(172.30.x)が OSPF に広告されていない(E2B経路の BGP next-hop が解決不能→RRで no best・East経路が配られない)

## おとり（無害・修正不要）
- RT05: dc_legacy_acl（未適用/無影響の残骸。削除しなくても減点なし）
- RT11: dc_snmp_note（未適用/無影響の残骸。削除しなくても減点なし）

修復は solution/fix.json（fix_generated.yml で投入可）。
下位レイヤから直すのが素直だが、順序は自由（採点は結果主義）。
