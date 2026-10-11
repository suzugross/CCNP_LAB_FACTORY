# 採点者専用 (GEN-DMVPNW-14320)

- RT01: `h_mcast` — ip nhrp map multicast dynamic 欠落
  - 見え方: 登録は成立する。EIGRP の隣接が spoke 側で張れない(ルーティング層の欠落)
- RT01: `h_p2p` — tunnel mode gre ip + tunnel destination(p2p GRE)
  - 見え方: hub の show dmvpn に tunnel destination の相手だけが UP(never)・他は上がらない
- RT01: `h_prof` — ipsec profile 未定義(→ tunnel protection も無い)
  - 見え方: hub に ISAKMP SA が 1 本も無い・spoke の State= IKE
- RT01: `h_tkey` — tunnel key 欠落(spoke は key あり)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は decaps だけ増え encaps 0・spoke の State= NHRP・ログに痕跡なし
- RT02: `s_isakmp` — crypto isakmp key 欠落
  - 見え方: その spoke だけ ISAKMP SA が無い・State= IKE
- RT02: `s_netid` — ip nhrp network-id 欠落
  - 見え方: その spoke の show dmvpn 自体が空・show ip nhrp nhs detail も空・ISAKMP SA も無い
- RT03: `s_isakmp` — crypto isakmp key 欠落
  - 見え方: その spoke だけ ISAKMP SA が無い・State= IKE
- RT04: `s_prof` — ipsec profile 未定義(→ tunnel protection も無い)
  - 見え方: hub ログ %CRYPTO-4-RECVD_PKT_NOT_IPSEC … src_addr=<その spoke> prot=47(約 1 分おき)・State= NHRP
- 最後の 1 層: `f_esp_acl` — hub の外側 ACL EDGE-IN に permit esp が無い(UDP 500/4500 は許可)。hub の encaps/decaps が両方 0(spoke の State= NHRP)
  - 見え方: ISAKMP QM_IDLE・hub の ESP は encaps も decaps も 0・spoke の State= NHRP・EDGE-IN の deny カウンタが増える

## 切り分けの軸(解説用)

- spoke の State: IKE= Phase 1 未成立 / IPSEC= Phase 2 未成立 / NHRP= 暗号は通過・NHRP 段階
- NHRP 段階は hub の `show crypto ipsec sa`: decaps だけ増える= hub が受けて返事をしない(network-id・key・auth・nhs)/ 両方 0= ESP が届いていない(ACL)
- `show ip nhrp nhs detail` が空= spoke が登録要求を送っていない(nhs 行の欠落)
- ★IOL の罠(本問の初期状態では起きない): 稼働中の hub で network-id を外して付け直すと `ip nhrp redirect` が表示されたまま無効になり、Phase 3 の直接トンネルだけができない。`ip nhrp redirect` を再入力すれば直る

fix は solution/fix.json(最後の no shutdown + clear は保険。PoC P2= 是正だけで 41 秒で登録)。
