# M11 — Appendix: E-LAN, multihoming and Ethernet OAM

This lab's IOS XRv 9000 runs only the E-Line (VPWS) among the L2VPN services, and it has no CFM commands. This appendix
looks at how the other services work. The configurations and outputs come from a PoC with Catalyst 8000V (IOS XE 17.15)
as the PEs. The IOS XR forms are shown as Cisco's documents give them (they cannot run on this lab's XR). A follow-up lab
with the 8000V, to practise these, will be added later.

At its default licence level, the 8000V has no MPLS commands at all. Set `license boot level network-advantage addon
dna-advantage`, save, and reload, and they are there (no registration was needed).

## 1. E-LAN: many sites in one LAN

### 1.1 What it is good for

When a customer wants three or more sites in one VLAN, joining every pair with E-Lines takes n(n−1)/2 of them for n
sites, and the CE has to choose which E-Line to send on. With an E-LAN, the provider's whole network behaves like one
switch: the PEs learn MAC addresses and send each frame only towards the site of its destination.

### 1.2 VPLS: a full mesh of pseudowires

In VPLS, each PE has a bridge domain and a pseudowire to every other PE of the same VPLS (a full mesh). A PE learns a
frame's source MAC on the AC or pseudowire it came from (learning in the data plane). Frames to unknown destinations
and broadcasts are copied to every pseudowire. A frame that came from a pseudowire is not sent to another pseudowire
(split horizon); with a full mesh, that leaves no loop.

:::config Catalyst 8000V (IOS XE 17.15) — VPLS on one PE (the form that worked as a full mesh of three in the PoC)
l2vpn vfi context VPLS210                          ## one VPLS instance
 vpn id 210                                        ## also the default VC ID of the pseudowires
 member 10.255.0.42 encapsulation mpls             ## one pseudowire per other PE (full mesh)
 member 10.255.0.43 encapsulation mpls
!
interface GigabitEthernet2
 service instance 210 ethernet                     ## AC = an EVC
  encapsulation dot1q 210
  rewrite ingress tag pop 1 symmetric
!
bridge-domain 210                                  ## the switch inside the PE; joins the AC and the VFI
 member GigabitEthernet2 service-instance 210
 member vfi VPLS210
!
:::

### 1.3 EVPN E-LAN: handing out MACs with BGP

In an EVPN E-LAN, the PE also learns MACs in the data plane. The difference is that it hands the learned MACs to the
other PEs in BGP **type 2** routes (MAC/IP advertisement). Another PE sends a frame for a MAC it got in BGP only to the
PE that advertised it. Which PEs get a copy of frames to unknown destinations and the like is told with **type 3** routes
(inclusive multicast, IMET). No full mesh of pseudowires between the PEs is needed.

```console
XE1#show l2vpn evpn mac
MAC Address    EVI   BD    ESI                      Ether Tag  Next Hop(s)
aabb.cc00.4f00 200   200   0000.0000.0000.0000.0000 0          Gi2:200
aabb.cc00.5000 200   200   0000.0000.0000.0000.0000 0          10.255.0.42
aabb.cc00.5100 200   200   0000.0000.0000.0000.0000 0          10.255.0.43
```

A MAC learned on the PE's own AC shows `Gi2:200`; a MAC received in BGP has the loopback of the PE that advertised it as
the next hop.

:::config Catalyst 8000V (IOS XE 17.15) — EVPN E-LAN on one PE (the form that worked with three in the PoC)
l2vpn evpn
 replication-type ingress                          ## BUM is copied once per receiving PE
 router-id Loopback0
!
l2vpn evpn instance 200 vlan-based                 ## EVI 200 (automatic RD and RT)
!
interface GigabitEthernet2
 service instance 200 ethernet
  encapsulation dot1q 200
  rewrite ingress tag pop 1 symmetric
!
bridge-domain 200
 member GigabitEthernet2 service-instance 200
 member evpn-instance 200                          ## join the bridge domain to the EVI
!
router bgp 65000
 address-family l2vpn evpn
  neighbor 10.255.0.21 activate                    ## the RR (IOS XRd reflected the routes in the PoC)
  neighbor 10.255.0.21 send-community both
!
:::

On IOS XR, the AC and `evi <EVI>` go under `l2vpn` → `bridge group` → `bridge-domain`, and `advertise-mac` under
`evpn` → `evi <EVI>` (as Cisco's documents give it). This lab's IOS XRv 9000 rejected a commit of a bridge domain with
`VPLS Bridge domains not supported on this platform`.

## 2. EVPN multihoming

### 2.1 What it is good for

Attaching a site's switch to two PEs protects it from a PE or link failure. With plain Layer 2, though, spanning tree
blocks one of the two links. With EVPN multihoming, the two PEs share one **Ethernet segment** (ES) and look like one
partner to the CE. The CE bundles its two links into one with LACP and uses both at once (all-active).

### 2.2 How it works

- **ESI**: the identifier of the ES. The two PEs set the same value.
- **Type 4 routes** (ES routes): the PEs of the same ES find each other and choose one of them to send BUM to the CE
  (the DF), since two copies would reach the CE if both sent.
- **Type 1 routes** (per ES): with these, a far PE learns that the ES has two PEs. It can send to both even for a MAC
  learned behind only one of them (**aliasing**). When a PE's link fails, it withdraws its type 1 route, and the far PE
  drops it as a next hop for every MAC of that ES at once.

In the PoC, the far PE, XE3, held the MAC of SW1 (bundled to two PEs) with the ESI and two next hops. When XE1's link to
SW1 went down, XE3 removed XE1 as a next hop within seconds.

```console
XE3#show l2vpn evpn mac
MAC Address    EVI   BD    ESI                      Ether Tag  Next Hop(s)
aabb.cc80.4e00 200   200   0300.0000.0000.0100.0001 0          10.255.0.41
                                                               10.255.0.42
```

The IOL-L2 acting as the CE, however, does not learn that a link went down (a limit of IOL on CML). SW1 kept sending
towards XE1 until LACP timed out, and traffic stopped for more than 30 seconds at the default rate, and for about 18
seconds with `lacp rate fast`. On real equipment, the link failure reaches the CE at once.

:::config Catalyst 8000V (IOS XE 17.15) — all-active multihoming on one PE (the form that bundled to two PEs in the PoC)
l2vpn evpn ethernet-segment 1
 identifier type 3 system-mac 0000.0000.0001       ## ESI (type 3 = made from a MAC); the same value on both PEs
 redundancy all-active                             ## the 8000V has all-active only (single-active is not in the syntax)
!
interface Port-channel1
 lacp device-id 0000.0000.0001                     ## both PEs show the CE the same LACP ID, so the CE forms one bundle
 evpn ethernet-segment 1
 service instance 200 ethernet
  encapsulation dot1q 200
  rewrite ingress tag pop 1 symmetric
!
interface GigabitEthernet3
 channel-group 1 mode active                       ## the link to the CE
!
bridge-domain 200
 member Port-channel1 service-instance 200
!
:::

On IOS XR, `identifier type 0 <ESI>`, and `load-balancing-mode single-active` if wanted, go under `evpn` →
`interface Bundle-Ether1` → `ethernet-segment` (as Cisco's documents give it).

## 3. E-Tree

An E-Tree is an E-LAN with roots and leaves. Leaves cannot reach each other; a leaf talks with the roots only. A video
source as the root and each site as a leaf is a typical use. EVPN marks frames that come from a leaf AC and does not send
them out of leaf ACs (RFC 8317). On IOS XR, `etree leaf` on an EVI or a bridge domain makes it a leaf, and one without it
is a root (as Cisco's documents give it). The PoC did not try it.

## 4. Ethernet OAM: CFM and Y.1731

### 4.1 What it is good for

From the CE, an E-Line shows only whether a ping gets through. The provider wants to check, apart from the customer's
traffic, that the section it sold is not broken and that its delay is within the agreement. IEEE 802.1ag **CFM** puts
monitoring points at both ends of an Ethernet section to watch that it is alive, and isolates faults with loopback and
linktrace. ITU-T **Y.1731** measures delay and loss on top of it.

### 4.2 How it works

- **Maintenance domain** (MD) and level (0 to 7): the customer, the provider and the operators each monitor at their own
  level.
- **Maintenance association** (MA): one service (here, one E-Line).
- **MEP**: a monitoring point at an end of the section. It sends **CCMs** at regular intervals and declares a fault when
  the other end's CCMs stop.
- **Loopback** (LBM/LBR) and **linktrace** (LTM/LTR): Ethernet versions of ping and traceroute.

In the PoC, MEPs went on both ends of an E-Line on an LDP pseudowire between two 8000Vs. Each learned the other's MEP,
the loopback got 5/5, the linktrace reached the other MEP, and the Y.1731 delay measurement (DMM) gave 0.69 to 1.92 ms
two-way. With the other end's AC down, the other MEP left the table and `show ethernet cfm errors` showed `Lifetime
Expired`.

:::config Catalyst 8000V (IOS XE 17.15) — a MEP at an E-Line end, and Y.1731 delay (the form that worked in the PoC)
ethernet cfm ieee
ethernet cfm global
ethernet evc E130                                  ## the name of the service (EVC)
!
ethernet cfm domain CUST level 5                   ## the customer's MD at level 5
 service E-LINE-130 evc E130                       ## the MA; no VLAN for an xconnect's EVC (the VLAN form is for bridge domains)
  continuity-check
  continuity-check interval 1s                     ## send a CCM every second
!
interface GigabitEthernet2
 service instance 130 ethernet E130                ## tie the AC to EVC E130
  encapsulation dot1q 130
  rewrite ingress tag pop 1 symmetric
  cfm mep domain CUST mpid 41                      ## this end's MEP (the other end is 43)
!
l2vpn xconnect context E130
 member GigabitEthernet2 service-instance 130
 member 10.255.0.43 130 encapsulation mpls
!
ip sla 10
 ethernet y1731 delay DMM domain CUST evc E130 mpid 43 cos 0 source mpid 41   ## send DMM to MEP 43 and measure the round-trip delay
 frequency 10
ip sla schedule 10 start-time now life forever
:::

MEPs at the ends of an EVPN-VPWS E-Line did not work in the PoC: one side sent no CCMs. The CFM chapter of Cisco's
documents has a restriction that an EVPN EFI cannot be associated with an EVC.

This lab's IOS XRv 9000 26.1.1 has no `ethernet cfm` command at all (it is not in its packages). The IOS XR form is
`ethernet cfm` → `domain <name> level <n>` → `service <name> xconnect group <G> p2p <name>`, and `ethernet cfm` →
`mep domain … service … mep-id <n>` on the AC sub-interface (as Cisco's documents give it). Y.1731 is `ethernet sla`.

## 5. G.8032 and 802.1ah

- **G.8032** (ITU-T Ethernet ring protection): on switches joined in a ring, one link (the RPL) is blocked to prevent a
  loop, and opened to go around when another link fails. It aims at switching within 50 ms. A ring needs three switches
  or more, so this lab does not cover it.
- **IEEE 802.1ah** (PBB, provider backbone bridges): wraps the customer's whole frame in a frame with the provider's MAC
  addresses (B-MAC), MAC-in-MAC. Services are told apart by a 24-bit I-SID, past the wall of 4094 VLANs, and the core
  switches need not learn the customers' MACs. Combined with EVPN, it is PBB-EVPN (RFC 7623).
- **E-Access**: an E-Line between a customer and the boundary to another operator's network (the ENNI).

:::note
Sources: L2VPN and Ethernet Services Configuration Guides for the ASR 9000 and NCS 5500, IOS XR 25.x (2025; VPLS, EVPN,
multihoming, E-Tree). Interface and Hardware Component Configuration Guide for the ASR 9000, 25.x (Ethernet OAM). IOS XE 17
MPLS Configuration Guide (VPLS, EVPN single-homing and multihoming) and Application Services Configuration Guide (CFM on
QFP platforms, which include the C8000v). Catalyst 8000V data sheet (2025). RFC 4762, 7432, 7623, 8317. IEEE 802.1ag,
802.1ah. ITU-T G.8013/Y.1731, G.8032. All checked in November 2026. The 8000V configurations, outputs and times come from
measurements in the PoC.
:::
