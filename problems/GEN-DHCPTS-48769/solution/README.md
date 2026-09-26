# 採点者専用 (GEN-DHCPTS-48769)

- faults: ['wall_missing'] / tgt: A
- 壁 `OPS-DHCP-ONLY`(in・46 エントリ): 欠陥= `missing`(必要な permit が無い(壁のどこにも無い)) / seq= normal(seq 10 刻み(挿入できる)) / 世界= in(hub の外側 in のみ)
  - 正解= `permit udp any eq bootpc any eq bootps` を 先頭の remark(seq 20)の後・anti-spoof の先頭 `deny ip 0.0.0.0 0.255.255.255 any`(seq 40)の**前**に挿入(例: seq 35)
  - 見え方: CL の DISCOVER(src 0.0.0.0)だけが落ちる(更新は通る)。壁の `deny ip 0.0.0.0 0.255.255.255 any` のカウンタだけが増える(log 無しなのでログには出ない)
  - ★DHCP の壁は anti-spoof(`deny ip 0.0.0.0 0.255.255.255 any`)より**前**に入れる(DISCOVER の送信元は 0.0.0.0)。後ろに入れると DISCOVER だけ落ちる
