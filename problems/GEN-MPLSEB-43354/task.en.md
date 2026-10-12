# Problem GEN-MPLSEB-43354 : MPLS L3VPN Troubleshooting, 12 Routers (auto-generated, difficulty 5)

## Scenario
The SP core (3 PEs / 3 Ps in a triangular ring) provides L3VPN service to two customers (CUST_A / CUST_B).
Both customers **use the same private range 172.16.0.0/16, and the ranges overlap**.
The CEs are customer-managed devices (**changes are not allowed**). You can operate only the core side (PE/P).

## Trouble Tickets

The NOC has received the following reports and alarms. **Identify the causes and restore the network to the design specification below.**

> - Only site1 of CUST_A is isolated (the other customer is normal)
> - Only site3 of CUST_B cannot reach the remote sites (CUST_A is entirely normal; the PE-CE session is Established)

> Note: Multiple events may be occurring at the same time. Because a fault at a lower layer can hide symptoms at an upper layer, always isolate from the lower layer upward.

## Topology

```
 A-CE            +--------- SP core --------+            A-CE
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
3. **MP-BGP**: AS 65000. **iBGP full mesh** between the Loopback0 interfaces of the 3 PEs, VPNv4 AF only
   (AF style). **The Ps (RT04-06) do not run BGP**.
4. **VRF** (common to all PEs): CUST_A = RD 65000:100 / RT 65000:100,
   CUST_B = RD 65000:200 / RT 65000:200.
5. **PE-CE**: eBGP (address-family ipv4 vrf. The CE AS numbers are in the table below. Because CUST_B uses **the same AS 65200 at all sites**,
   **as-override** is applied on the PE side to accommodate it). **Redistribution and static routes are not used** (eBGP routes go directly into VPNv4).
6. **Advertisement control**: Only the LANs (/24) in 172.16.0.0/16 may be received from a CE
   (route-map RM-CE-IN, which references prefix-list PL-CUST-LAN, is applied **per neighbor in the in direction**).
   **Device management 10.99.0.0/16 is discarded at reception** (it is not installed even in the VRF of the attached PE).
7. **MSS**: ip tcp adjust-mss 1452 on the CE-facing interfaces of the PEs.
8. Static routes are not allowed. Do not change the CEs (RT07-12). Do not touch the MGMT VRF / Ethernet0/3.

## Addressing (values for this seed)
### Core Loopback0
| Node | Lo0 |
|--------|-----|
| RT01 | 76.76.76.76/32 |
| RT02 | 32.32.32.32/32 |
| RT03 | 49.49.49.49/32 |
| RT04 | 33.33.33.33/32 |
| RT05 | 52.52.52.52/32 |
| RT06 | 93.93.93.93/32 |

### Core Links
| Link | Segment |
|--------|-----------|
| RT01–RT04 | 10.106.250.0/30 (RT01=.1 / RT04=.2) |
| RT02–RT05 | 10.89.217.0/30 (RT02=.1 / RT05=.2) |
| RT03–RT06 | 10.207.175.0/30 (RT03=.1 / RT06=.2) |
| RT04–RT05 | 10.174.247.0/30 (RT04=.1 / RT05=.2) |
| RT05–RT06 | 10.113.67.0/30 (RT05=.1 / RT06=.2) |
| RT04–RT06 | 10.144.110.0/30 (RT04=.1 / RT06=.2) |

### CEs / Customers
| CE | Customer/Site | AS | Attached PE | PE-CE link | Site LAN (Lo0) | Device management (Lo9) |
|----|------------|-----|--------|--------------|------------------|----------------|
| RT07 | CUST_A site1 | 65101 | RT01 | 192.168.134.0/30 (CE=.1/PE=.2) | 172.16.127.1/24 | 10.99.211.1/32 |
| RT08 | CUST_B site1 | 65200 | RT01 | 192.168.163.0/30 (CE=.1/PE=.2) | 172.16.127.9/24 | 10.99.201.1/32 |
| RT09 | CUST_A site2 | 65102 | RT02 | 192.168.36.0/30 (CE=.1/PE=.2) | 172.16.167.1/24 | 10.99.176.1/32 |
| RT10 | CUST_B site2 | 65200 | RT02 | 192.168.41.0/30 (CE=.1/PE=.2) | 172.16.167.9/24 | 10.99.33.1/32 |
| RT11 | CUST_A site3 | 65103 | RT03 | 192.168.171.0/30 (CE=.1/PE=.2) | 172.16.60.1/24 | 10.99.175.1/32 |
| RT12 | CUST_B site3 | 65200 | RT03 | 192.168.222.0/30 (CE=.1/PE=.2) | 172.16.60.9/24 | 10.99.189.1/32 |

## Goals
- All site pairs of each customer (site1↔2↔3) have end-to-end reachability, and the customers are isolated from each other.
- The device management /32s reach only the attached PE (they do not cross the VPN).
- Core forwarding is label switched.

## Scoring
```
ansible-playbook playbooks/grade.yml -e problem=GEN-MPLSEB-43354 \
  --vault-password-file <(printf 'CCNP\n')
```
