# Lab GEN-MPLSTS-94914 : MPLS L3VPN Troubleshooting, 12 Routers (auto-generated · Difficulty 5)

## Scenario
An SP core (3 PEs / 3 Ps in a triangular ring) provides L3VPN service to two customers (CUST_A / CUST_B).
Both customers **use the same private range, 172.16.0.0/16, with overlapping addresses**.
The CEs are customer-managed devices (**changes are not allowed**). You can operate only the core side (PE/P).

## Trouble Ticket

The NOC has received the following reports and alarms. **Identify the causes and restore the network to the design specification below.**

> - Audit finding: the management address of a CE attached at site3 is visible from the remote sites (all reachability is normal)
> - Monitoring: OSPF adjacency-down alarm between RT05 and RT06 (no user impact reported)

> Note: Multiple events may be occurring at the same time. A fault in a lower layer can hide symptoms in an upper layer, so always isolate from the lower layer upward.

```
 A-CE            +-------- SP core ---------+            A-CE
 RT07 --\        |         RT05(P2)         |        /-- RT09
         RT01(PE1)--RT04(P1)  |  \           RT02(PE2)
 RT08 --/        |     |  \  |   RT06(P3)---RT03(PE3)   \-- RT10
 B-CE            |     +---\-+--/    |      |            B-CE
                 +------------------ | -----+
                              RT11 --+-- RT12
                              (A-CE)     (B-CE)   * See the tables below for the exact cabling
```

## Design Specification (the intended state)
1. **Core IGP**: OSPF 1 / area 0 (core links and Lo0 only. Lo9 is not part of the IGP).
2. **MPLS**: LDP on all core links. LDP router ID = Loopback0 (force).
3. **MP-BGP**: AS 65000. **iBGP full mesh** between the Loopback0 addresses of the three PEs, VPNv4 AF only
   (address-family style). **The Ps (RT04-06) do not run BGP.**
4. **VRF** (common to all PEs): CUST_A = RD 65000:100 / RT 65000:100,
   CUST_B = RD 65000:200 / RT 65000:200.
5. **PE-CE**: OSPF (PE-side process CUST_A=10 / CUST_B=20,
   area 0, router-id=Lo0). Mutual redistribution between OSPF and BGP.
6. **Advertisement control**: Only the LANs (/24) in 172.16.0.0/16 are sent into VPNv4
   (prefix-list PL-CUST-LAN + route-map RM-OSPF2VPN). **Device management 10.99.0.0/16 must not be
   advertised across the VPN.**
7. **MSS**: ip tcp adjust-mss 1452 on the CE-facing interfaces of the PEs.
8. Static routes are not allowed. Changes to the CEs (RT07-12) are not allowed. Do not touch the MGMT VRF / Ethernet0/3.

## Addressing (values for this seed)
### Core Loopback0
| Node | Lo0 |
|------|-----|
| RT01 | 12.12.12.12/32 |
| RT02 | 72.72.72.72/32 |
| RT03 | 98.98.98.98/32 |
| RT04 | 90.90.90.90/32 |
| RT05 | 41.41.41.41/32 |
| RT06 | 14.14.14.14/32 |

### Core Links
| Link | Segment |
|------|---------|
| RT01–RT04 | 10.41.158.0/30 (RT01=.1 / RT04=.2) |
| RT02–RT05 | 10.116.69.0/30 (RT02=.1 / RT05=.2) |
| RT03–RT06 | 10.230.47.0/30 (RT03=.1 / RT06=.2) |
| RT04–RT05 | 10.205.28.0/30 (RT04=.1 / RT05=.2) |
| RT05–RT06 | 10.25.97.0/30 (RT05=.1 / RT06=.2) |
| RT04–RT06 | 10.164.180.0/30 (RT04=.1 / RT06=.2) |

### CE / Customers
| CE | Customer/Site | Attached PE | PE-CE link | Site LAN (Lo0) | Device management (Lo9) |
|----|---------------|-------------|------------|----------------|-------------------------|
| RT07 | CUST_A site1 | RT01 | 192.168.92.0/30 (CE=.1/PE=.2) | 172.16.234.1/24 | 10.99.203.1/32 |
| RT08 | CUST_B site1 | RT01 | 192.168.110.0/30 (CE=.1/PE=.2) | 172.16.234.9/24 | 10.99.1.1/32 |
| RT09 | CUST_A site2 | RT02 | 192.168.225.0/30 (CE=.1/PE=.2) | 172.16.240.1/24 | 10.99.233.1/32 |
| RT10 | CUST_B site2 | RT02 | 192.168.25.0/30 (CE=.1/PE=.2) | 172.16.240.9/24 | 10.99.101.1/32 |
| RT11 | CUST_A site3 | RT03 | 192.168.72.0/30 (CE=.1/PE=.2) | 172.16.144.1/24 | 10.99.189.1/32 |
| RT12 | CUST_B site3 | RT03 | 192.168.170.0/30 (CE=.1/PE=.2) | 172.16.144.9/24 | 10.99.241.1/32 |

## Objectives
- All site pairs of each customer (site1↔2↔3) have end-to-end reachability, and the customers are isolated from each other.
- The device management /32s stay within the attached PE (they do not cross the VPN).
- Core forwarding is label-switched.

## Scoring
```
ansible-playbook playbooks/grade.yml -e problem=GEN-MPLSTS-94914 \
  --vault-password-file <(printf 'CCNP\n')
```
