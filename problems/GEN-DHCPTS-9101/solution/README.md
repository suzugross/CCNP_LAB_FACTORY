# 採点者専用 (GEN-DHCPTS-9101)

- faults: ['wall_shadowed'] / tgt: B
- 壁 `BRANCH-DHCP-ONLY`(in・43 エントリ): 欠陥= `shadowed`(必要な行はあるが、anti-spoof の deny の**後ろ**にあり食われている(同一 ACE は重複不可なので、対向を絞った別の行を前に入れる)) / seq= normal(seq 10 刻み(挿入できる)) / 世界= in(hub の外側 in のみ)
  - 正解= `permit udp host 0.0.0.0 eq bootpc host 255.255.255.255 eq bootps` を 先頭の remark(seq 20)の後・anti-spoof の先頭 `deny ip 0.0.0.0 0.255.255.255 any`(seq 40)の**前**に挿入(例: seq 35)
  - 見え方: CL の DISCOVER(src 0.0.0.0)だけが落ちる(更新は通る)。壁の `deny ip 0.0.0.0 0.255.255.255 any` のカウンタだけが増える(log 無しなのでログには出ない)
  - ★DHCP の壁は anti-spoof(`deny ip 0.0.0.0 0.255.255.255 any`)より**前**に入れる(DISCOVER の送信元は 0.0.0.0)。後ろに入れると DISCOVER だけ落ちる
