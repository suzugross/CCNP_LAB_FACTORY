# 採点者専用 (GEN-DMVPNW-4242)

- RT01: `h_mcast` — ip nhrp map multicast dynamic 欠落
  - 見え方: 登録は成立する。EIGRP の隣接が spoke 側で張れない(ルーティング層の欠落)
- RT01: `h_netid` — ip nhrp network-id 欠落(NHRP が有効にならない)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は decaps だけ増え encaps 0・spoke の State= NHRP・hub ログ %DMVPN-5-NHRP_NETID_UNCONFIGURED
- RT01: `h_tkey` — tunnel key 欠落(spoke は key あり)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は decaps だけ増え encaps 0・spoke の State= NHRP・ログに痕跡なし
- RT02: `s_mtu` — ip mtu 1400 / ip tcp adjust-mss 1360 欠落(症状なし・仕様との差分)
  - 見え方: 症状なし(1400B DF の ping も外側の断片化で通る)。`show run interface Tunnel0` の仕様突き合わせだけで見つける
- RT02: `s_tkey` — tunnel key 欠落
  - 見え方: その spoke だけ ISAKMP QM_IDLE・hub の該当 SA は decaps のみ・State= NHRP・痕跡なし
- RT03: `s_mtu` — ip mtu 1400 / ip tcp adjust-mss 1360 欠落(症状なし・仕様との差分)
  - 見え方: 症状なし(1400B DF の ping も外側の断片化で通る)。`show run interface Tunnel0` の仕様突き合わせだけで見つける
- RT03: `s_prot` — tunnel protection 欠落(profile は定義済み)
  - 見え方: hub ログ %CRYPTO-4-RECVD_PKT_NOT_IPSEC … src_addr=<その spoke> prot=47(約 1 分おき)・State= NHRP
- RT04: `s_isakmp` — crypto isakmp key 欠落
  - 見え方: その spoke だけ ISAKMP SA が無い・State= IKE
- RT04: `s_prot` — tunnel protection 欠落(profile は定義済み)
  - 見え方: hub ログ %CRYPTO-4-RECVD_PKT_NOT_IPSEC … src_addr=<その spoke> prot=47(約 1 分おき)・State= NHRP
- 最後の 1 層: `f_acl_wall` — hub 外側のうんざり ACL(40〜70 行)に ESP の欠陥(BL-210・hardmode.edge_wall)。既存行を消さず正しい位置に 1 行挿入するのが正解(spoke の State= NHRP)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は encaps も decaps も 0・spoke の State= NHRP・hub ログ %SEC-6-IPACCESSLOGNP: list EDGE-IN denied 50 <spoke> -> <hub>(欠陥の種類によらず同じ)
- 壁 `seC_eDGe-1n.v3`(in・46 エントリ): 欠陥= `missing`(必要な permit が無い(壁のどこにも無い)) / seq= packed(挿入すべき区間の seq が詰まっている(`ip access-list resequence` が要る)) / 世界= both(hub の外側 in(欠陥)＋全 spoke の外側 in(正しい＝囮。IOL は out 側 ACL が ARP を壊すので out 壁は使わない))
  - 正解= `permit esp any host 203.0.113.2` を anti-spoof(seq 100)の後・ルータ保護 deny(seq 143)の前に挿入(seq が詰まっているので `ip access-list resequence seC_eDGe-1n.v3 10 10` → seq 445。★IOL では resequence で remark が消える)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は encaps も decaps も 0・spoke の State= NHRP・hub ログ `%SEC-6-IPACCESSLOGNP: list seC_eDGe-1n.v3 denied 50 <spoke> -> 203.0.113.2`
- 囮の壁 `seC_eDGe-1n.v3`(in・47 エントリ・正しい。触る必要なし)
- 囮の壁 `seC_eDGe-1n.v3`(in・54 エントリ・正しい。触る必要なし)
- 囮の壁 `seC_eDGe-1n.v3`(in・50 エントリ・正しい。触る必要なし)
- C2 打ちづらい名前: profile `ipSEc_pr0f_DMVpn3` / transform-set `ts_aes256_SHa2.v3` / ACL `seC_eDGe-1n.v3` / PSK `PrEsHARed-key#87` / NHRP `NHRP-k57`(すべて仕様書に明記・大小区別あり)
- C3 囮: 似た名前の未使用 profile 2(1 つは mode tunnel+PFS・1 つは本物と等価)・transform-set 1・ACL 1(permit any)。参照を囮に付け替えると仕様の名前チェックで落ちる
- C5 ノイズ: 各拠点に無害な設定 120 行前後(LEGACY Loopback・QoS・Null0 静的・未使用 ACL/route-map/IP SLA)
- C6 メモ: 偽の項目= 1 番目「支店2(RT03)の Tunnel0 と暗号の設定は、完了して確認済み」(RT03 には欠落 ['s_mtu', 's_prot'] がある)
- C7 df: MTU/MSS 欠落の spoke= RT02, RT03(症状なし・仕様監査)

## 切り分けの軸(解説用)

- spoke の State: IKE= Phase 1 未成立 / IPSEC= Phase 2 未成立 / NHRP= 暗号は通過・NHRP 段階
- NHRP 段階は hub の `show crypto ipsec sa`: decaps だけ増える= hub が受けて返事をしない(network-id・key・auth・nhs)/ 両方 0= ESP が届いていない(ACL)
- `show ip nhrp nhs detail` が空= spoke が登録要求を送っていない(nhs 行の欠落)
- ★IOL の罠(本問の初期状態では起きない): 稼働中の hub で network-id を外して付け直すと `ip nhrp redirect` が表示されたまま無効になり、Phase 3 の直接トンネルだけができない。`ip nhrp redirect` を再入力すれば直る

fix は solution/fix.json(最後の no shutdown + clear は保険。PoC P2= 是正だけで 41 秒で登録)。
