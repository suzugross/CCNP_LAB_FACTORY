

# probe run 2026-08-22 05:21 (p0 p1 p2 p3 p4 p5 p6 p7 p8)

## p0
- golden 投入から track Up まで **11.1s**

`show track 1`(健全):
```
Track 1
  IP SLA 1 reachability
  Reachability is Up
    2 changes, last change 00:00:01
  Latest operation return code: OK
  Latest RTT (millisecs) 34
  Tracked by:
    Static IP Routing 0
```

`show ip sla configuration`:
```
IP SLAs Infrastructure Engine-III
Entry number: 1
Owner: 
Tag: 
Operation timeout (milliseconds): 5000
Type of operation to perform: icmp-echo
Target address/Source address: 100.64.0.1/10.0.12.1
Type Of Service parameter: 0x0
Request size (ARR data portion): 28
Data pattern: 0xABCDABCD
Verify data: No
Vrf Name: 
Do not fragment: No
Schedule:
   Operation frequency (seconds): 10  (not considered if randomly scheduled)
   Next Scheduled Start Time: Start Time already passed
   Group Scheduled : FALSE
   Randomly Scheduled : FALSE
   Life (seconds): Forever
   Entry Ageout (seconds): never
   Recurring (Starting Everyday): FALSE
   Status of entry (SNMP RowStatus): Active
Threshold (milliseconds): 5000
Distribution Statistics:
   Number of statistic hours kept: 2
   Number of statistic distribution buckets kept: 1
   Statistic distribution interval (milliseconds): 20
Enhanced History:
History Statistics:
   Number of history Lives kept: 0
   Number of history Buckets kept: 15
   History Filter Type: None
```

`show ip sla statistics`(健全):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: 34 milliseconds
Latest operation start time: 05:22:01 UTC Sat Aug 22 2026
Latest operation return code: OK
Number of successes: 1
Number of failures: 1
Operation time to live: Forever
```

`show ip route track-table`:
```
ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1 state is [up]
```

`show ip route 0.0.0.0`(健全):
```
Routing entry for 0.0.0.0/0, supernet
  Known via "static", distance 1, metric 0, candidate default path
  Routing Descriptor Blocks:
  * 10.0.12.2
      Route metric is 0, traffic share count is 1
```
- 健全時 ping 8.8.8.8 source Lo0: **100%**
- 奥障害から track Down まで **7.0s**(SLA frequency 10s・track delay 既定)

`show track 1`(奥障害):
```
Track 1
  IP SLA 1 reachability
  Reachability is Down
    3 changes, last change 00:00:01
  Latest operation return code: Timeout
  Tracked by:
    Static IP Routing 0
```

`show ip sla statistics`(奥障害・return code):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 05:22:11 UTC Sat Aug 22 2026
Latest operation return code: Timeout
Number of successes: 1
Number of failures: 2
Operation time to live: Forever
```

`show ip route 0.0.0.0`(切替後):
```
Routing entry for 0.0.0.0/0, supernet
  Known via "static", distance 200, metric 0, candidate default path
  Routing Descriptor Blocks:
  * 10.0.13.2
      Route metric is 0, traffic share count is 1
```
- 切替後 ping 8.8.8.8 source Lo0: **100%**(backup 経由)

切替後 ping:
```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 1.1.1.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/2 ms
```
- 復旧から track Up まで **7.0s**
- 復帰後 ping: **100%**

## p1

稼働中に `ip sla 1` 再入:
```
ip sla 1
Entry already running and cannot be modified
	(only can delete (no) and start over)
	(check to see if the probe has finished exiting)
```
- CLI応答: `% Invalid input detected at '^' marker.`

稼働中に定義変更を試行:
```
ip sla 1
Entry already running and cannot be modified
	(only can delete (no) and start over)
	(check to see if the probe has finished exiting)

icmp-echo 8.8.8.8
icmp-echo 8.8.8.8
 ^
% Invalid input detected at '^' marker.
```

unschedule 後に `frequency 20`:
```
ip sla 1
frequency 20
exit
```

unschedule 後の `show ip sla configuration`:
```
IP SLAs Infrastructure Engine-III
Entry number: 1
Owner: 
Tag: 
Operation timeout (milliseconds): 5000
Type of operation to perform: icmp-echo
Target address/Source address: 100.64.0.1/10.0.12.1
Type Of Service parameter: 0x0
Request size (ARR data portion): 28
Data pattern: 0xABCDABCD
Verify data: No
Vrf Name: 
Do not fragment: No
Schedule:
   Operation frequency (seconds): 20  (not considered if randomly scheduled)
   Next Scheduled Start Time: Pending trigger
   Group Scheduled : FALSE
   Randomly Scheduled : FALSE
   Life (seconds): 3600
   Entry Ageout (seconds): never
   Recurring (Starting Everyday): FALSE
   Status of entry (SNMP RowStatus): notInService
Threshold (milliseconds): 5000
Distribution Statistics:
   Number of statistic hours kept: 2
   Number of statistic distribution buckets kept: 1
   Statistic distribution interval (milliseconds): 20
Enhanced History:
History Statistics:
   Number of history Lives kept: 0
   Number of history Buckets kept: 15
   History Filter Type: None
```

再 schedule 後の `show ip sla statistics`:
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: 10 milliseconds
Latest operation start time: 05:22:46 UTC Sat Aug 22 2026
Latest operation return code: OK
Number of successes: 2
Number of failures: 0
Operation time to live: Forever
```

## p2
- 未 schedule での track 状態: **Down**

`show track 1`(未 schedule):
```
Track 1
  IP SLA 1 reachability
  Reachability is Down
    1 change, last change 00:00:45
  Latest operation return code: Unknown
  Tracked by:
    Static IP Routing 0
```

`show ip sla statistics`(未 schedule):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
Number of successes: Unknown
Number of failures: Unknown
Operation time to live: 0
```

`show ip route 0.0.0.0`(未 schedule):
```
Routing entry for 0.0.0.0/0, supernet
  Known via "static", distance 200, metric 0, candidate default path
  Routing Descriptor Blocks:
  * 10.0.13.2
      Route metric is 0, traffic share count is 1
```
- ping 8.8.8.8 source Lo0: **100%**(どちら経由かは上の RIB)

## p3
- 存在しない SLA 2 参照の track 状態: **Down**

`show track 1`(SLA 2 参照):
```
Track 1
  IP SLA 2 reachability
  Reachability is Down
    1 change, last change 00:00:46
  Latest operation return code: Unknown
  Tracked by:
    Static IP Routing 0
```

`show ip route 0.0.0.0`:
```
Routing entry for 0.0.0.0/0, supernet
  Known via "static", distance 200, metric 0, candidate default path
  Routing Descriptor Blocks:
  * 10.0.13.2
      Route metric is 0, traffic share count is 1
```

## p4

RT02 `show run all | include source-route`(既定値):
```
no ip source-route
```

`path-echo` 定義の CLI 応答:
```
ip sla 1
path-echo 100.64.0.1 source-ip 10.0.12.1
frequency 30
exit
```
- path-echo 健全時 track Up まで: **-1s**(-1=上がらず)

`show ip sla statistics`(path-echo 健全):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 05:26:43 UTC Sat Aug 22 2026
Latest operation return code: Timeout
Operation time to live: Forever
```

`show track 1`(path-echo 健全):
```
Track 1
  IP SLA 1 reachability
  Reachability is Down
    1 change, last change 00:02:36
  Latest operation return code: Timeout
  Tracked by:
    Static IP Routing 0
```
- RT02 `no ip source-route` 後の track: **Down**

`show track 1`(source-route 遮断):
```
Track 1
  IP SLA 1 reachability
  Reachability is Down
    1 change, last change 00:04:07
  Latest operation return code: Timeout
  Tracked by:
    Static IP Routing 0
```

`show ip sla statistics`(source-route 遮断・return code):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 05:28:13 UTC Sat Aug 22 2026
Latest operation return code: Timeout
Operation time to live: Forever
```
- 同時点の通常 ping ビーコン(source e0/0): **100%**(ping は通るのに SLA だけ落ちるかの実証)

## p5

`udp-jitter` 定義の CLI 応答:
```
ip sla 1
udp-jitter 100.64.0.1 17000 source-ip 10.0.12.1
frequency 10
exit
```
- responder 無しの track: **Down**

`show track 1`(responder 無し):
```
Track 1
  IP SLA 1 reachability
  Reachability is Down
    1 change, last change 00:00:45
  Latest operation return code: No connection
  Tracked by:
    Static IP Routing 0
```

`show ip sla statistics`(responder 無し・return code):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
Type of operation: udp-jitter
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 05:29:18 UTC Sat Aug 22 2026
Latest operation return code: No connection
RTT Values:
	Number Of RTT: 0		RTT Min/Avg/Max: 0/0/0 milliseconds
Latency one-way time:
	Number of Latency one-way Samples: 0
	Source to Destination Latency one way Min/Avg/Max: 0/0/0 milliseconds
	Destination to Source Latency one way Min/Avg/Max: 0/0/0 milliseconds
Jitter Time:
	Number of SD Jitter Samples: 0
	Number of DS Jitter Samples: 0
	Source to Destination Jitter Min/Avg/Max: 0/0/0 milliseconds
	Destination to Source Jitter Min/Avg/Max: 0/0/0 milliseconds
Over Threshold:
	Number Of RTT Over Threshold: 0 (0%)
Packet Loss Values:
	Loss Source to Destination: 0
	Source to Destination Loss Periods Number: 0
	Source to Destination Loss Period Length Min/Max: 0/0
	Source to Destination Inter Loss Period Length Min/Max: 0/0
	Loss Destination to Source: 0
	Destination to Source Loss Periods Number: 0
	Destination to Source Loss Period Length Min/Max: 0/0
	Destination to Source Inter Loss Period Length Min/Max: 0/0
	Out Of Sequence: 0	Tail Drop: 0
	Packet Late Arrival: 0	Packet Skipped: 0
Voice Score Values:
	Calculated Planning Impairment Factor (ICPIF): 0
	Mean Opinion Score (MOS): 0
Number of successes: 0
Number of failures: 2
Operation time to live: Forever
```
- responder 投入から track Up まで: **11.1s**

`show ip sla statistics`(responder 有り・jitter 書式):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
Type of operation: udp-jitter
	Latest RTT: 4 milliseconds
Latest operation start time: 05:29:48 UTC Sat Aug 22 2026
Latest operation return code: OK
RTT Values:
	Number Of RTT: 10		RTT Min/Avg/Max: 1/4/16 milliseconds
Latency one-way time:
	Number of Latency one-way Samples: 8
	Source to Destination Latency one way Min/Avg/Max: 0/4/15 milliseconds
	Destination to Source Latency one way Min/Avg/Max: 0/0/3 milliseconds
Jitter Time:
	Number of SD Jitter Samples: 9
	Number of DS Jitter Samples: 9
	Source to Destination Jitter Min/Avg/Max: 0/4/14 milliseconds
	Destination to Source Jitter Min/Avg/Max: 0/2/3 milliseconds
Over Threshold:
	Number Of RTT Over Threshold: 0 (0%)
Packet Loss Values:
	Loss Source to Destination: 0
	Source to Destination Loss Periods Number: 0
	Source to Destination Loss Period Length Min/Max: 0/0
	Source to Destination Inter Loss Period Length Min/Max: 0/0
	Loss Destination to Source: 0
	Destination to Source Loss Periods Number: 0
	Destination to Source Loss Period Length Min/Max: 0/0
	Destination to Source Inter Loss Period Length Min/Max: 0/0
	Out Of Sequence: 0	Tail Drop: 0
	Packet Late Arrival: 0	Packet Skipped: 0
Voice Score Values:
	Calculated Planning Impairment Factor (ICPIF): 0
	Mean Opinion Score (MOS): 0
Number of successes: 1
Number of failures: 2
Operation time to live: Forever
```

## p6
- CLI応答: `%Scheduling a probe with timeout 60000 ms greater than frequency 10000 ms is not allowed.`
- CLI応答: `%Scheduling a probe with timeout 60000 ms greater than frequency 10000 ms is not allowed.`
- tcp-connect 23(実在): track **Down** / 8080(誰も listen せず): track **Down**

`show ip sla statistics 1`(port 23):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
Number of successes: Unknown
Number of failures: Unknown
Operation time to live: 0
```

`show ip sla statistics 2`(port 8080・return code):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 2
Number of successes: Unknown
Number of failures: Unknown
Operation time to live: 0
```

## p7
- source=10.0.13.1(backup側IF): track **Down** / source=1.1.1.1(Lo0): track **Up**
  (Lo0 は RT04 の戻りが backup 優先なので**非対称に成功**し、primary 監視になっていない不感形が成立するかの実証)

`show ip sla statistics 1`(backup側IF source):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 05:31:37 UTC Sat Aug 22 2026
Latest operation return code: Timeout
Number of successes: 0
Number of failures: 5
Operation time to live: Forever
```

`show ip sla statistics 2`(Lo0 source):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 2
	Latest RTT: 20 milliseconds
Latest operation start time: 05:31:38 UTC Sat Aug 22 2026
Latest operation return code: OK
Number of successes: 4
Number of failures: 1
Operation time to live: Forever
```

`show track 1`:
```
Track 1
  IP SLA 1 reachability
  Reachability is Down
    1 change, last change 00:00:45
  Latest operation return code: Timeout
  Tracked by:
    Static IP Routing 0
```

`show track 2`:
```
Track 2
  IP SLA 2 reachability
  Reachability is Up
    2 changes, last change 00:00:36
  Latest operation return code: OK
  Latest RTT (millisecs) 20
```

## p8

`timeout 20000`×`frequency 5` の CLI 応答:
```
ip sla 1
icmp-echo 100.64.0.1 source-ip 10.0.12.1
frequency 5
timeout 20000
exit
```

`threshold 30000`(> timeout) の CLI 応答:
```
ip sla 1
threshold 30000
exit
```

定義後の `show ip sla configuration`:
```
IP SLAs Infrastructure Engine-III
Entry number: 1
Owner: 
Tag: 
Operation timeout (milliseconds): 20000
Type of operation to perform: icmp-echo
Target address/Source address: 100.64.0.1/10.0.12.1
Type Of Service parameter: 0x0
Request size (ARR data portion): 28
Data pattern: 0xABCDABCD
Verify data: No
Vrf Name: 
Do not fragment: No
Schedule:
   Operation frequency (seconds): 5  (not considered if randomly scheduled)
   Next Scheduled Start Time: Pending trigger
   Group Scheduled : FALSE
   Randomly Scheduled : FALSE
   Life (seconds): 3600
   Entry Ageout (seconds): never
   Recurring (Starting Everyday): FALSE
   Status of entry (SNMP RowStatus): notInService
Threshold (milliseconds): 30000
Distribution Statistics:
   Number of statistic hours kept: 2
   Number of statistic distribution buckets kept: 1
   Statistic distribution interval (milliseconds): 20
Enhanced History:
History Statistics:
   Number of history Lives kept: 0
   Number of history Buckets kept: 15
   History Filter Type: None
```

`show ip route 0.0.0.0`(backup AD1 並置=ECMP?):
```
Routing entry for 0.0.0.0/0, supernet
  Known via "static", distance 1, metric 0, candidate default path
  Routing Descriptor Blocks:
    10.0.13.2
      Route metric is 0, traffic share count is 1
  * 10.0.12.2
      Route metric is 0, traffic share count is 1
```
- ECMP 状態の ping 8.8.8.8: **100%**


# probe run 2026-08-22 05:35 (p4b p6b p8b p9)

## p4b
- 全機 `ip source-route` 有効化での path-echo track Up: **-1s**(-1=上がらず)

`show ip sla statistics`(path-echo・source-route 有効):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 05:37:50 UTC Sat Aug 22 2026
Latest operation return code: Timeout
Operation time to live: Forever
```

`show ip sla statistics 1 details`(per-hop が出るか):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 05:37:50 UTC Sat Aug 22 2026
Latest operation return code: Timeout
Over thresholds occurred: FALSE
Operation time to live: Forever
Operational state of entry: Active
Last time this entry was reset: Never
```

`show track 1`:
```
Track 1
  IP SLA 1 reachability
  Reachability is Down
    1 change, last change 00:03:04
  Latest operation return code: Timeout
  Tracked by:
    Static IP Routing 0
```

## p6b
- tcp-connect 23(vty telnet): track **Down** / 8080(listen なし): track **Down**

`show ip sla statistics 1`(port 23):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 05:39:13 UTC Sat Aug 22 2026
Latest operation return code: Timeout
Number of successes: 0
Number of failures: 5
Operation time to live: Forever
```

`show ip sla statistics 2`(port 8080・return code):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 2
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 05:39:14 UTC Sat Aug 22 2026
Latest operation return code: Timeout
Number of successes: 0
Number of failures: 5
Operation time to live: Forever
```

## p8b
- CLI応答: `%Scheduling a probe with timeout 20000 ms greater than frequency 5000 ms is not allowed.`

timeout 20000×frequency 5 の schedule 試行:
```
ip sla schedule 1 life forever start-time now
%Scheduling a probe with timeout 20000 ms greater than frequency 5000 ms is not allowed.
```

直後の `show ip sla statistics`(未稼働の指紋確認):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
Number of successes: Unknown
Number of failures: Unknown
Operation time to live: 0
```
- CLI応答: `%Scheduling a probe with threshold 30000 ms greater than timeout 4000 ms is not allowed.`

threshold 30000×timeout 4000 の schedule 試行:
```
ip sla schedule 1 life forever start-time now
%Scheduling a probe with threshold 30000 ms greater than timeout 4000 ms is not allowed.
```
- threshold 4000(=timeout・RTT よりはるか上)で稼働: track **Up**(threshold は reachability 判定に効かないことの傍証は紙面用に別途)

## p9
- /32 固定なしでも平常時は track Up(**-1s**)=プローブは default(primary) を追って成功=潜在故障
- 奥障害→track Down: **0.4s**(切替自体は機能する)
- ★★復旧後 150s 経っても track Down のまま= **フェイルバック不能ラッチの成立**(プローブが backup 側 default を追ってビーコンに届かない)

復旧後の `show track 1`:
```
Track 1
  IP SLA 1 reachability
  Reachability is Down
    1 change, last change 00:04:37
  Latest operation return code: Timeout
  Tracked by:
    Static IP Routing 0
```

復旧後の `show ip route 0.0.0.0`:
```
Routing entry for 0.0.0.0/0, supernet
  Known via "static", distance 200, metric 0, candidate default path
  Routing Descriptor Blocks:
  * 10.0.13.2
      Route metric is 0, traffic share count is 1
```

復旧後の `show ip sla statistics`:
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 05:44:37 UTC Sat Aug 22 2026
Latest operation return code: Timeout
Number of successes: 0
Number of failures: 28
Operation time to live: Forever
```
- fix(/32 固定投入)から track Up まで: **3.7s**
- fix 後 ping 8.8.8.8: **100%**(primary 復帰)


# probe run 2026-08-22 05:46 (p6c)

## p6c

素の telnet 8.8.8.8(ベースライン):
```
Trying 8.8.8.8 ... Open


User Access Verification

Password: 
% Password:  timeout expired!
Password: 
% Password:  timeout expired!
Password: 
% Password:  timeout expired!
% Bad passwords

[Connection to 8.8.8.8 closed by foreign host]
```
- tcp-connect 23(vty telnet): track **Up** / 8080(listen なし): track **Down**

`show ip sla statistics 1`(port 23):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: 1 milliseconds
Latest operation start time: 05:48:57 UTC Sat Aug 22 2026
Latest operation return code: OK
Number of successes: 5
Number of failures: 0
Operation time to live: Forever
```

`show ip sla statistics 2`(port 8080・return code):
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 2
	Latest RTT: 0 milliseconds
Latest operation start time: 05:48:58 UTC Sat Aug 22 2026
Latest operation return code: Socket connect error
Number of successes: 0
Number of failures: 5
Operation time to live: Forever
```


# probe run 2026-08-22 10:17 (p10)

## p10
- Lo0 source の定常: track Up まで 10.9s(非対称往復で成立)
- ①primary 奥障害の検知: track Down まで **10.2s**(-1=検知せず。検知するなら『切替されず』の症状文は誤り)
- ②backup 奥障害での track: Down まで **10.2s**(-1=影響なし。Down なら誤フェイルオーバ)

②の `show ip route 0.0.0.0`:
```
Routing entry for 0.0.0.0/0, supernet
  Known via "static", distance 200, metric 0, candidate default path
  Routing Descriptor Blocks:
  * 10.0.13.2
      Route metric is 0, traffic share count is 1
```
- ②の ping 8.8.8.8 source Lo0: **0%**(0% なら健全な primary があるのに全断)

②の `show ip sla statistics`:
```
IPSLAs Latest Operation Statistics

IPSLA operation id: 1
	Latest RTT: NoConnection/Busy/Timeout
Latest operation start time: 10:18:05 UTC Sat Aug 22 2026
Latest operation return code: Timeout
Number of successes: 2
Number of failures: 4
Operation time to live: Forever
```
- 対照(golden source・backup 奥障害継続中): track **Up** / ping **0%**(Up・100% なら backup 側障害に不感=正しい設計)
