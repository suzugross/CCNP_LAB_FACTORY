# 採点者専用 (GEN-DMVPNW-40021)

- RT01: `h_netid` — ip nhrp network-id 欠落(NHRP が有効にならない)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は decaps だけ増え encaps 0・spoke の State= NHRP・hub ログ %DMVPN-5-NHRP_NETID_UNCONFIGURED
- RT01: `h_p2p` — tunnel mode gre ip + tunnel destination(p2p GRE)
  - 見え方: hub の show dmvpn に tunnel destination の相手だけが UP(never)・他は上がらない
- RT01: `h_tkey` — tunnel key 欠落(spoke は key あり)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は decaps だけ増え encaps 0・spoke の State= NHRP・ログに痕跡なし
- RT02: `s_netid` — ip nhrp network-id 欠落
  - 見え方: その spoke の show dmvpn 自体が空・show ip nhrp nhs detail も空・ISAKMP SA も無い
- RT02: `s_tkey` — tunnel key 欠落
  - 見え方: その spoke だけ ISAKMP QM_IDLE・hub の該当 SA は decaps のみ・State= NHRP・痕跡なし
- RT03: `s_isakmp` — crypto isakmp key 欠落
  - 見え方: その spoke だけ ISAKMP SA が無い・State= IKE
- RT04: `s_netid` — ip nhrp network-id 欠落
  - 見え方: その spoke の show dmvpn 自体が空・show ip nhrp nhs detail も空・ISAKMP SA も無い
- RT04: `s_prof` — ipsec profile 未定義(→ tunnel protection も無い)
  - 見え方: hub ログ %CRYPTO-4-RECVD_PKT_NOT_IPSEC … src_addr=<その spoke> prot=47(約 1 分おき)・State= NHRP
- 最後の 1 層: `f_acl_wall` — hub 外側のうんざり ACL(40〜70 行)に ESP の欠陥(BL-210・hardmode.edge_wall)。既存行を消さず正しい位置に 1 行挿入するのが正解(spoke の State= NHRP)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は encaps も decaps も 0・spoke の State= NHRP・hub ログ %SEC-6-IPACCESSLOGNP: list EDGE-IN denied 50 <spoke> -> <hub>(欠陥の種類によらず同じ)
- 壁 `EDGE-IN`(in・48 エントリ): 欠陥= `wrong_proto`(必要な行の代わりに `udp eq 50`(ESP を UDP ポートと勘違いした行)がある) / seq= normal(seq 10 刻み(挿入できる)) / 世界= both(hub の外側 in(欠陥)＋全 spoke の外側 in(正しい＝囮。IOL は out 側 ACL が ARP を壊すので out 壁は使わない))
  - 正解= `permit esp any host 203.0.113.2` を anti-spoof(seq 90)の後・ルータ保護 deny(seq 550)の前に挿入(例: seq 545)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は encaps も decaps も 0・spoke の State= NHRP・hub ログ `%SEC-6-IPACCESSLOGNP: list EDGE-IN denied 50 <spoke> -> 203.0.113.2`
- 囮の壁 `EDGE-IN`(in・52 エントリ・正しい。触る必要なし)
- 囮の壁 `EDGE-IN`(in・49 エントリ・正しい。触る必要なし)
- 囮の壁 `EDGE-IN`(in・56 エントリ・正しい。触る必要なし)

## 切り分けの軸(解説用)

- spoke の State: IKE= Phase 1 未成立 / IPSEC= Phase 2 未成立 / NHRP= 暗号は通過・NHRP 段階
- NHRP 段階は hub の `show crypto ipsec sa`: decaps だけ増える= hub が受けて返事をしない(network-id・key・auth・nhs)/ 両方 0= ESP が届いていない(ACL)
- `show ip nhrp nhs detail` が空= spoke が登録要求を送っていない(nhs 行の欠落)
- ★IOL の罠(本問の初期状態では起きない): 稼働中の hub で network-id を外して付け直すと `ip nhrp redirect` が表示されたまま無効になり、Phase 3 の直接トンネルだけができない。`ip nhrp redirect` を再入力すれば直る

fix は solution/fix.json(最後の no shutdown + clear は保険。PoC P2= 是正だけで 41 秒で登録)。
