
## P8 (失敗)  (2026-09-19 00:50)

**P8 EXCEPTION**

```
Traceback (most recent call last):
  File "/home/suzuki/ansible/CCNP01/poc/fhs/p8_guards.py", line 145, in main
    P8(devs)
  File "/home/suzuki/ansible/CCNP01/poc/fhs/p8_guards.py", line 51, in P8
    conf(swb, ["ipv6 nd raguard policy HOST", "device-role host", "exit",
  File "/home/suzuki/ansible/CCNP01/poc/paper-kb/sweep.py", line 188, in conf
    out = dev.configure(lines, error_pattern=[], timeout=180, reply=DIALOG)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "src/unicon/bases/routers/services.py", line 259, in unicon.bases.routers.services.BaseService.__call__
  File "/home/suzuki/ansible/CCNP01/.venv/lib/python3.12/site-packages/unicon/plugins/ios/iosv/service_implementation.py", line 22, in call_service
    super().call_service(command, reply=reply,
  File "/home/suzuki/ansible/CCNP01/.venv/lib/python3.12/site-packages/unicon/plugins/generic/service_implementation.py", line 1021, in call_service
    self.process_dialog_on_handle(handle, dialog, timeout)
  File "/home/suzuki/ansible/CCNP01/.venv/lib/python3.12/site-packages/unicon/plugins/generic/service_implementation.py", line 1096, in process_dialog_on_handle
    cmd_result = dialog.process(
                 ^^^^^^^^^^^^^^^
  File "src/unicon/eal/dialogs.py", line 479, in unicon.eal.dialogs.Dialog.process
  File "src/unicon/eal/dialog_processor.py", line 353, in unicon.eal.dialog_processor.SimpleDialogProcessor.process
  File "src/unicon/eal/dialog_processor.py", line 254, in unicon.eal.dialog_processor.SimpleDialogProcessor.expect_eval_statements
  File "/home/suzuki/ansible/CCNP01/.venv/lib/python3.12/site-packages/unicon/plugins/generic/service_implementation.py", line 932, in config_state_change
    invalid_state_change_action(
  File "/home/suzuki/ansible/CCNP01/.venv/lib/python3.12/site-packages/unicon/plugins/generic/service_implementation.py", line 68, in invalid_state_change_action
    raise StateMachineError(msg)
unicon.core.errors.StateMachineError: Expected device to reach 'enable' state, but landed on 'enable' state.
```

## P8L source/prefix/destination guard(旧 CLI・POC-FHS-IOSV)  (2026-09-19 00:57)

**P8L-0 SWB show version**

```
Cisco IOS Software, vios_l2 Software (vios_l2-ADVENTERPRISEK9-M), Experimental Version 15.2(20200924:215240) [sweickge-sep24-2020-l2iol-release 135]
ROM: Bootstrap program is IOSv
Cisco IOSv () processor (revision 1.0) with 734445K/50176K bytes of memory.
```

**P8L-0 raguard policy HOST**

```
ipv6 nd raguard policy HOST
device-role host
---
(応答なし)
```

**P8L-0 raguard policy ROUTER**

```
ipv6 nd raguard policy ROUTER
device-role router
---
(応答なし)
```

**P8L-0 snooping policy SNOOP**

```
ipv6 snooping policy SNOOP
security-level guard
tracking enable
---
(応答なし)
```

**P8L-0 vlan 10 に snooping attach**

```
vlan configuration 10
ipv6 snooping attach-policy SNOOP
---
(応答なし)
```

**P8L-0 GigabitEthernet0/0 raguard ROUTER**

```
interface GigabitEthernet0/0
ipv6 nd raguard attach-policy ROUTER
---
% Invalid input detected at '^' marker.
```

**P8L-0 GigabitEthernet0/1 raguard HOST**

```
interface GigabitEthernet0/1
ipv6 nd raguard attach-policy HOST
---
% Invalid input detected at '^' marker.
```

**P8L-0 GigabitEthernet0/2 raguard HOST**

```
interface GigabitEthernet0/2
ipv6 nd raguard attach-policy HOST
---
% Invalid input detected at '^' marker.
```

**P8L-0 RT02 受信カウンタ ACL**

```
ipv6 access-list CNT
sequence 10 permit icmp 2001:DB8:98::/64 any
sequence 20 permit icmp 2001:DB8:99::/64 any
sequence 30 permit icmp 2001:DB8:33:B::/64 any
sequence 40 permit icmp any any
sequence 50 permit ipv6 any any
exit
interface Ethernet0/0
ipv6 traffic-filter CNT in
exit
---
(応答なし)
```

**P8L-0 CLB show ipv6 interface brief (GUA after 15.617999792098999s)**

```
Ethernet0/0            [up/up]
    FE80::A8BB:CCFF:FE01:7000
    2001:DB8:33:B:A8BB:CCFF:FE01:7000
    2001:DB8:33:BAD:A8BB:CCFF:FE01:7000
```

**P8L-0 CLB show ipv6 routers**

```
Router FE80::A8BB:CCFF:FE01:7100 on Ethernet0/0, last update 0 min
  Hops 64, Lifetime 1800 sec, AddrFlag=0, OtherFlag=1, MTU=1500
  HomeAgentFlag=0, Preference=High
  Reachable time 0 (unspecified), Retransmit time 0 (unspecified)
  Prefix 2001:DB8:33:BAD::/64 onlink autoconfig
    Valid lifetime 2592000, preferred lifetime 604800
Router FE80::A8BB:CCFF:FE01:6F00 on Ethernet0/0, last update 0 min
  Hops 64, Lifetime 1800 sec, AddrFlag=0, OtherFlag=1, MTU=1500
  HomeAgentFlag=0, Preference=Medium
  Reachable time 0 (unspecified), Retransmit time 0 (unspecified)
  Prefix 2001:DB8:33:B::/64 onlink autoconfig
    Valid lifetime 2592000, preferred lifetime 604800
```

**P8L-0 CLB 範囲外アドレス追加(Et0/0=98::1 / Lo0=99::1)**

```
interface Loopback0
ipv6 address 2001:DB8:99::1/64
exit
interface Ethernet0/0
ipv6 address 2001:DB8:98::1/64
exit
---
(応答なし)
```

**P8L-0 SWB show ipv6 snooping policies**

```
Target               Type  Policy               Feature        Target range
vlan 10              VLAN  SNOOP                Snooping       vlan all
```

**P8L-0 SWB show ipv6 neighbors binding**

```

```

**P8L-0 SWB show ipv6 snooping features**

```
Feature name   priority state
RA guard          192   READY
Snooping          128   READY
```

**P8L-0 SWB show ipv6 snooping counters interface GigabitEthernet0/1**

```
% no ipv6 snooping policy attached on Gi0/1
```

**P8L-0 SWB show ipv6 nd raguard policy HOST**

```
Policy HOST configuration: 
  device-role host
Policy HOST is applied on the following targets: 
Target               Type  Policy               Feature        Target range
```

**P8L-0 ガード無し (a) CLB 既定送信元(SLAAC GUA)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/6 ms
```

**P8L-0 ガード無し (b) CLB 送信元 2001:DB8:98::1(Et0/0 追加・表に載る・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:98::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:98::1
.....
Success rate is 0 percent (0/5)
```

**P8L-0 ガード無し (c) CLB 送信元 2001:DB8:99::1(Lo0・表に無い・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:99::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:99::1
.....
Success rate is 0 percent (0/5)
```

**P8L-0 ガード無し RT02 show ipv6 access-list CNT (受信カウンタ: 10=98::/64 20=99::/64 30=33:B::/64)**

```
IPv6 access list CNT
    permit icmp 2001:DB8:98::/64 any (5 matches) sequence 10
    permit icmp 2001:DB8:99::/64 any (5 matches) sequence 20
    permit icmp 2001:DB8:33:B::/64 any (7 matches) sequence 30
    permit icmp any any (1 match) sequence 40
    permit ipv6 any any sequence 50
```

- P8L-0 ガード無し ping 成功率 a=100% b=0% c=0%

**P8L-1 source-guard policy SG**

```
ipv6 source-guard policy SG
---
(応答なし)
```

**P8L-1 GigabitEthernet0/1 に SG attach**

```
interface GigabitEthernet0/1
ipv6 source-guard attach-policy SG
---
% A Snooping policy should be attached to target Box for this feature to operate properly
```

**P8L-1 SWB show ipv6 source-guard policy SG**

```
Policy SG configuration: 
  validate address
Policy SG is applied on the following targets: 
Target               Type  Policy               Feature        Target range
Box                  BOX   SG                   Source guard   vlan all
```

**P8L-1 SWB show ipv6 snooping policies**

```
Target               Type  Policy               Feature        Target range
vlan 10              VLAN  SNOOP                Snooping       vlan all
Box                  BOX   SG                   Source guard   vlan all
```

**P8L-1 SWB show running-config interface GigabitEthernet0/1**

```
Building configuration...

Current configuration : 140 bytes
!
interface GigabitEthernet0/1
 description === to CLB (host) ===
 switchport access vlan 10
 switchport mode access
 negotiation auto
end
```

**P8L-1 source-guard(address) (a) CLB 既定送信元(SLAAC GUA)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P8L-1 source-guard(address) (b) CLB 送信元 2001:DB8:98::1(Et0/0 追加・表に載る・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:98::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:98::1
.....
Success rate is 0 percent (0/5)
```

**P8L-1 source-guard(address) (c) CLB 送信元 2001:DB8:99::1(Lo0・表に無い・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:99::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:99::1
.....
Success rate is 0 percent (0/5)
```

**P8L-1 source-guard(address) RT02 show ipv6 access-list CNT (受信カウンタ: 10=98::/64 20=99::/64 30=33:B::/64)**

```
IPv6 access list CNT
    permit icmp 2001:DB8:98::/64 any (5 matches) sequence 10
    permit icmp 2001:DB8:99::/64 any (5 matches) sequence 20
    permit icmp 2001:DB8:33:B::/64 any (5 matches) sequence 30
    permit icmp any any sequence 40
    permit ipv6 any any sequence 50
```

- P8L-1 source-guard(address) ping 成功率 a=100% b=0% c=0%

**P8L-1 SWB show ipv6 snooping counters interface GigabitEthernet0/1**

```
% no ipv6 snooping policy attached on Gi0/1
```

**P8L-1 SWB show ipv6 neighbors binding**

```

```

**P8L-1 SWB — SWB show logging**

```

```

**P8L-2 GigabitEthernet0/1 SG detach**

```
interface GigabitEthernet0/1
no ipv6 source-guard attach-policy SG
---
(応答なし)
```

**P8L-2 source-guard policy PG(validate prefix)**

```
ipv6 source-guard policy PG
validate prefix
---
(応答なし)
```

**P8L-2 GigabitEthernet0/1 に PG attach**

```
interface GigabitEthernet0/1
ipv6 source-guard attach-policy PG
---
% A Snooping policy should be attached to target Box for this feature to operate properly
```

**P8L-2 SWB show ipv6 source-guard policy PG**

```
Policy PG configuration: 
  validate prefix
  validate address
Policy PG is applied on the following targets: 
Target               Type  Policy               Feature        Target range
Box                  BOX   PG                   Source guard   vlan all
```

**P8L-2 prefix-guard(validate prefix) (a) CLB 既定送信元(SLAAC GUA)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P8L-2 prefix-guard(validate prefix) (b) CLB 送信元 2001:DB8:98::1(Et0/0 追加・表に載る・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:98::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:98::1
.....
Success rate is 0 percent (0/5)
```

**P8L-2 prefix-guard(validate prefix) (c) CLB 送信元 2001:DB8:99::1(Lo0・表に無い・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:99::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:99::1
.....
Success rate is 0 percent (0/5)
```

**P8L-2 prefix-guard(validate prefix) RT02 show ipv6 access-list CNT (受信カウンタ: 10=98::/64 20=99::/64 30=33:B::/64)**

```
IPv6 access list CNT
    permit icmp 2001:DB8:98::/64 any (5 matches) sequence 10
    permit icmp 2001:DB8:99::/64 any (5 matches) sequence 20
    permit icmp 2001:DB8:33:B::/64 any (6 matches) sequence 30
    permit icmp any any (2 matches) sequence 40
    permit ipv6 any any sequence 50
```

- P8L-2 prefix-guard(validate prefix) ping 成功率 a=100% b=0% c=0%

**P8L-2 SWB show ipv6 snooping counters interface GigabitEthernet0/1**

```
% no ipv6 snooping policy attached on Gi0/1
```

**P8L-2b PG に validate address 追加**

```
ipv6 source-guard policy PG
validate address
---
(応答なし)
```

**P8L-2b prefix+address (a) CLB 既定送信元(SLAAC GUA)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/1 ms
```

**P8L-2b prefix+address (b) CLB 送信元 2001:DB8:98::1(Et0/0 追加・表に載る・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:98::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:98::1
.....
Success rate is 0 percent (0/5)
```

**P8L-2b prefix+address (c) CLB 送信元 2001:DB8:99::1(Lo0・表に無い・範囲外)→GW — CLB# ping 2001:DB8:33:B::1 repeat 5 source 2001:DB8:99::1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B::1, timeout is 2 seconds:
Packet sent with a source address of 2001:DB8:99::1
.....
Success rate is 0 percent (0/5)
```

**P8L-2b prefix+address RT02 show ipv6 access-list CNT (受信カウンタ: 10=98::/64 20=99::/64 30=33:B::/64)**

```
IPv6 access list CNT
    permit icmp 2001:DB8:98::/64 any (5 matches) sequence 10
    permit icmp 2001:DB8:99::/64 any (5 matches) sequence 20
    permit icmp 2001:DB8:33:B::/64 any (5 matches) sequence 30
    permit icmp any any sequence 40
    permit ipv6 any any sequence 50
```

- P8L-2b prefix+address ping 成功率 a=100% b=0% c=0%

**P8L-2 GigabitEthernet0/1 PG detach**

```
interface GigabitEthernet0/1
no ipv6 source-guard attach-policy PG
---
(応答なし)
```

**P8L-3 destination-guard policy DG**

```
ipv6 destination-guard policy DG
enforcement always
---
(応答なし)
```

**P8L-3 RT02 未知宛先の静的 ND**

```
ipv6 neighbor 2001:DB8:33:B::DEAD Ethernet0/0 aabb.cc00.0dea
---
(応答なし)
```

**P8L-3 DG 無し RT02→CLB 2001:DB8:33:B:A8BB:CCFF:FE01:7000 — RT02# ping 2001:DB8:33:B:A8BB:CCFF:FE01:7000 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B:A8BB:CCFF:FE01:7000, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P8L-3 DG 無し RT02→::DEAD — RT02# ping 2001:DB8:33:B::DEAD repeat 3 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 2001:DB8:33:B::DEAD, timeout is 2 seconds:
...
Success rate is 0 percent (0/3)
```

**P8L-3 GigabitEthernet0/0 に DG attach**

```
interface GigabitEthernet0/0
ipv6 destination-guard attach-policy DG
---
% Invalid input detected at '^' marker.
```

**P8L-3 vlan 10 に DG attach(代替)**

```
vlan configuration 10
ipv6 destination-guard attach-policy DG
---
(応答なし)
```

**P8L-3 SWB show ipv6 destination-guard policy DG**

```
Destination guard policy DG: 
  enforcement always
	Target: vlan 10
```

**P8L-3 DG あり RT02→CLB 2001:DB8:33:B:A8BB:CCFF:FE01:7000 — RT02# ping 2001:DB8:33:B:A8BB:CCFF:FE01:7000 repeat 5 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 2001:DB8:33:B:A8BB:CCFF:FE01:7000, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P8L-3 DG あり RT02→::DEAD — RT02# ping 2001:DB8:33:B::DEAD repeat 3 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 2001:DB8:33:B::DEAD, timeout is 2 seconds:
...
Success rate is 0 percent (0/3)
```

**P8L-3 SWB show ipv6 snooping counters interface GigabitEthernet0/0**

```
% no ipv6 snooping policy attached on Gi0/0
```

**P8L-3 SWB show ipv6 snooping counters vlan 10**

```
Received messages on vlan 10   :
Protocol        Protocol message
NDP             
DHCPv6          

Bridged messages from vlan 10   :
Protocol        Protocol message
NDP             
DHCPv6          

Dropped messages on vlan 10   :
Feature         Protocol Msg [Total dropped]
```

**P8L-3 SWB — SWB show logging**

```

```
