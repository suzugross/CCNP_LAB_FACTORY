# 採点者専用 (GEN-DMVPNW-777)

- RT01: `h_mcast` — ip nhrp map multicast dynamic 欠落
  - 見え方: 登録は成立する。EIGRP の隣接が spoke 側で張れない(ルーティング層の欠落)
- RT01: `h_p2p` — tunnel mode gre ip + tunnel destination(p2p GRE)
  - 見え方: hub の show dmvpn に tunnel destination の相手だけが UP(never)・他は上がらない
- RT01: `h_tkey` — tunnel key 欠落(spoke は key あり)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は decaps だけ増え encaps 0・spoke の State= NHRP・ログに痕跡なし
- RT02: `s_isakmp` — crypto isakmp key 欠落
  - 見え方: その spoke だけ ISAKMP SA が無い・State= IKE
- RT02: `s_tkey` — tunnel key 欠落
  - 見え方: その spoke だけ ISAKMP QM_IDLE・hub の該当 SA は decaps のみ・State= NHRP・痕跡なし
- RT03: `s_prot` — tunnel protection 欠落(profile は定義済み)
  - 見え方: hub ログ %CRYPTO-4-RECVD_PKT_NOT_IPSEC … src_addr=<その spoke> prot=47(約 1 分おき)・State= NHRP
- RT04: `s_isakmp` — crypto isakmp key 欠落
  - 見え方: その spoke だけ ISAKMP SA が無い・State= IKE
- 最後の 1 層: `f_acl_wall` — hub 外側のうんざり ACL(40〜70 行)に ESP の欠陥(BL-210・hardmode.edge_wall)。既存行を消さず正しい位置に 1 行挿入するのが正解(spoke の State= NHRP)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は encaps も decaps も 0・spoke の State= NHRP・hub ログ %SEC-6-IPACCESSLOGNP: list EDGE-IN denied 50 <spoke> -> <hub>(欠陥の種類によらず同じ)
- 壁 `Sec_edge-In.v7`(in・46 エントリ): 欠陥= `missing`(必要な permit が無い(壁のどこにも無い)) / seq= normal(seq 10 刻み(挿入できる)) / 世界= in(hub の外側 in のみ)
  - 正解= `permit esp any host 203.0.113.2` を anti-spoof(seq 100)の後・ルータ保護 deny(seq 530)の前に挿入(例: seq 525)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は encaps も decaps も 0・spoke の State= NHRP・hub ログ `%SEC-6-IPACCESSLOGNP: list Sec_edge-In.v7 denied 50 <spoke> -> 203.0.113.2`
- C2 打ちづらい名前: profile `ip5Ec_PR0F_DMvpn4` / transform-set `Ts_aEs256_Sha2.v4` / ACL `Sec_edge-In.v7` / PSK `PReshAREd-KEY#80` / NHRP `nhRP-K42`(すべて仕様書に明記・大小区別あり)
- C3 囮: 似た名前の未使用 profile 2(1 つは mode tunnel+PFS・1 つは本物と等価)・transform-set 1・ACL 1(permit any)。参照を囮に付け替えると仕様の名前チェックで落ちる

## 切り分けの軸(解説用)

- spoke の State: IKE= Phase 1 未成立 / IPSEC= Phase 2 未成立 / NHRP= 暗号は通過・NHRP 段階
- NHRP 段階は hub の `show crypto ipsec sa`: decaps だけ増える= hub が受けて返事をしない(network-id・key・auth・nhs)/ 両方 0= ESP が届いていない(ACL)
- `show ip nhrp nhs detail` が空= spoke が登録要求を送っていない(nhs 行の欠落)
- ★IOL の罠(本問の初期状態では起きない): 稼働中の hub で network-id を外して付け直すと `ip nhrp redirect` が表示されたまま無効になり、Phase 3 の直接トンネルだけができない。`ip nhrp redirect` を再入力すれば直る

fix は solution/fix.json(最後の no shutdown + clear は保険。PoC P2= 是正だけで 41 秒で登録)。
