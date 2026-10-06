# Problem GEN-REDISTMP-99505 : Routing Loop Caused by Multipoint Mutual Redistribution (Difficulty 5)

## Scenario
The internal network consists of three routing domains connected in a chain. **Two routers, RB and RC,** perform **mutual redistribution** between OSPF and EIGRP, and **RF** redistributes the customer site's RIPv2 network `192.168.233.0/24` into EIGRP (the seed metric for all redistribution is `1000000 1 255 1 1500`).

```
   [OSPF area0]        [EIGRP AS59]                          [RIPv2]
        RB ──── 172.16.49.0/24 ────┐
 172.16.89.0/24│                        │
        RA                          RD ── 172.16.19.0/24 ── RE ── 172.16.34.0/24 ── RF ═ 192.168.233.0/24
 172.16.186.0/24│                        │
        RC ──── 172.16.68.0/24 ────┘
```

## Trouble Ticket (representative symptoms)
> Traffic from the OSPF side (RA, etc.) to the customer network **`192.168.233.0/24` does not arrive**.
> Running `traceroute 192.168.233.6` shows the packets **circulating through the same four routers** until the TTL expires.
> All other destinations (such as each router's Loopback) are reachable normally.

## Routers / Roles
| Router | Role | Representative address |
|--------|------|------------------------|
| RA | OSPF internal | Lo0 `65.65.65.65/32` |
| RB | **OSPF⇄EIGRP border (mutual redistribution)** | Lo0 `61.61.61.61/32` |
| RC | **OSPF⇄EIGRP border (mutual redistribution)** | Lo0 `78.78.78.78/32` |
| RD | EIGRP internal (connected to both border routers and RE) | Lo0 `36.36.36.36/32` |
| RE | EIGRP internal | Lo0 `99.99.99.99/32` |
| RF | RIPv2 site; **RIP→EIGRP redistribution** | Lo0 `192.168.233.6/24` (customer LAN) |

## Objectives
1. Every router can reach **`192.168.233.6`** (reachability among all Loopbacks must also be maintained).
2. There is **no forwarding loop**.
3. The **redistribution design of each domain must be preserved** (removing or disabling any redistribution is not allowed).

## Restrictions (change-management and audit policy)
- Protocol placement (which routers and links run OSPF / EIGRP / RIP) must not be changed.
- **Configuration changes are allowed on RB and RC only.** RA / RD / RE / RF must not be modified.
- Implement the fix using the **route-tag method**: **set origin tag 211 on EIGRP→OSPF redistribution**, and **block routes carrying tag 211 on OSPF→EIGRP redistribution** (apply a route-map to the redistribution commands).
- **Changes to distribute-list / prefix-list / administrative distance (distance) are not allowed** (solve the problem by "origin marking", not by matching prefixes directly).
- Workarounds using static routes or default routes are not allowed.

## Hints (minimal)
Read the repeating pattern in the `traceroute 192.168.233.6` output. On each router in the loop, trace the **Known via (learning source) and metric** in `show ip route 192.168.233.0`, one router at a time.
RD should have **multiple** pieces of routing information for this destination. If you determine **where each one came from**, the place and direction in which to stop it will become clear.

## Access / Scoring
SSH `SUZUKI / CCNP` (mgmt addresses are assigned in order from 10.1.10.x).
```
ansible-playbook playbooks/grade.yml -e problem=GEN-REDISTMP-99505 --vault-password-file <(printf 'CCNP\n')
```
Scoring is **effect-based (reachability, absence of loops, shortest forwarding path) plus compliance with the audit policy**.
