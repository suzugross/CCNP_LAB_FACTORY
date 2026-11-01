# XR Track 11 — L2VPN and Carrier Ethernet

This lab is the practice part of unit **M11 L2VPN and Carrier Ethernet** of the XR track. It continues where lab XRT-10
ended: the core, the VPN customers and segment routing are the same, and XR01 and XR02 start with the work of tasks
M10-1 to M10-5 done. A new provider edge, XR03, has joined the core. The unit has three pages: *E-Line and
pseudowires* (tasks M11-1 and M11-2), *EVPN-VPWS* (tasks M11-3 and M11-4) and *Q-in-Q* (task M11-5). Read each page
before its tasks, and work through the tasks here, in order. Each task builds on the previous one.

## Ground rules

- You configure **XR01** and **XR03**, and in Task M11-3 also **XR02**. All the other routers are fixed; do not change
  them. You may log in to them to look. The CEs, SVC and INET belong to the customers, the shared services and the
  Internet.
- The tasks give no command examples. Each task states the behaviour that is required. The reading pages have
  configuration examples; the ones that have the same form as a task's answer are folded. To solve a task on your own
  first, use the CLI help (`?`), the `show` commands, and the Cisco IOS XR configuration guides and command references
  to find the commands.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. Give LDP and BGP half a minute to settle after a commit.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XR01 and XR03 run **IOS XRv 9000** 26.1.1. On this platform, IOS XR runs only the point-to-point Layer 2 services
  (VPWS); it does not bridge. XR02 runs **IOS XRd** 26.1.1, the container form of IOS XR: it is the route reflector
  and the PCE, outside the forwarding path.

## Topology

| Link | Ends | Addressing | IS-IS metric |
|---|---|---|---|
| PRIMARY | XR01 GigabitEthernet0/0/0/0 ─ RT01 Ethernet0/0 | 10.0.1.0/24 (XR01 .1, RT01 .11) | 10 |
| BACKUP | XR01 GigabitEthernet0/0/0/1 ─ RT03 Ethernet0/0 | 10.0.3.0/24 (XR01 .1, RT03 .13) | 100 |
| CORE-A | RT01 Ethernet0/1 ─ RT02 Ethernet0/0 | 10.0.12.0/24 (RT01 .11, RT02 .12) | 10 |
| CORE-B | RT03 Ethernet0/1 ─ RT02 Ethernet0/1 | 10.0.23.0/24 (RT03 .13, RT02 .12) | 100 |
| RR-LINK | RT03 Ethernet0/2 ─ XR02 GigabitEthernet0/0/0/0 | 10.0.33.0/24 (RT03 .13, XR02 .21) | 10 |
| CORE-C | RT01 Ethernet0/2 ─ XR03 GigabitEthernet0/0/0/0 | 10.0.31.0/24 (RT01 .11, XR03 .3) | 10 |

| Router | Role | Platform | Loopback0 | Prefix-SID index |
|---|---|---|---|---|
| XR01 | Provider edge | IOS XRv 9000 26.1.1 | 10.255.0.1/32 | 1 |
| XR02 | VPNv4 route reflector, PCE | IOS XRd 26.1.1 | 10.255.0.21/32 | — |
| XR03 | Provider edge (new) | IOS XRv 9000 26.1.1 | 10.255.0.3/32 | 3 |
| RT01 | Core | IOS XE 17.15 | 10.255.0.11/32 | 11 |
| RT02 | Provider edge | IOS XE 17.15 | 10.255.0.12/32 | 12 |
| RT03 | Core | IOS XE 17.15 | 10.255.0.13/32 | 13 |

| Site | Attached to | Layer 3 VPN | Layer 2 sub-interfaces on the same port |
|---|---|---|---|
| Customer A, site 1 (CEA1) | XR01 GigabitEthernet0/0/0/2 | VRF CUST-A (untagged) | VLAN 100 |
| Customer A, site 2 (CEA2) | RT02 Ethernet0/2 | VRF CUST-A (untagged) | VLAN 200 |
| Customer B, site 1 (CEB1) | XR01 GigabitEthernet0/0/0/3 | VRF CUST-B (untagged) | VLANs 300, 310, 400, 410, 420; S-VLAN 500 |
| Customer B, site 2 (CEB2) | RT02 Ethernet1/0 | VRF CUST-B (untagged) | VLANs 300, 310 |
| Customer B, site 3 (CEB3) | XR03 GigabitEthernet0/0/0/1 | — | VLANs 40, 41, 42; S-VLAN 500 |

- The core runs the IPv4 IS-IS instance `CORE` with segment routing on every router. XR01 has no LDP since Task M10-2;
  the IOS routers still run LDP among themselves. XR03 runs IS-IS and SR (prefix-SID index 3) and nothing else.
- The Layer 3 VPNs, the SR policies and the PCE are those of lab XRT-10. They must keep working.
- A customer's Ethernet service between two sites is an **E-Line**. On each port, the Layer 3 VPN stays untagged and
  the E-Lines use tagged sub-interfaces of the same port. The two ends of an E-Line may use different VLANs.
- The provider's site numbers: site 1 = **1**, site 2 = **2**, site 3 = **3**. Where an E-Line needs an identifier
  for each end, the identifier of an end is the number of its site.

## M11 — L2VPN and Carrier Ethernet

### Task M11-1

Customer A has bought an E-Line between site 1 and site 2, apart from its Layer 3 VPN. The site 2 end (RT02) is
already in place.

- Carry the frames that CEA1 sends on VLAN 100 to CEA2 on VLAN 200, and back. The CEs use 172.31.10.0/24 on this
  E-Line.
- The E-Line is a pseudowire signalled with LDP, with the ID **100**, between XR01 and RT02.
- Use LDP only to signal the pseudowire. LDP must not run on XR01's core links; the transport labels keep coming from
  segment routing.
- Customer A's Layer 3 VPN must keep working.

### Task M11-2

A colleague built two E-Lines for customer B between site 1 and site 2 (VLANs 300 and 310), with changes CHG-1401 and
CHG-1402. Neither of them has ever worked. The site 2 end (RT02) is in place and correct.

- Make both E-Lines work. The CEs use 172.31.30.0/24 on VLAN 300 and 172.31.31.0/24 on VLAN 310.
- Do not change RT02.

### Task M11-3

Customer B has opened site 3, attached to the new provider edge XR03. XR03 has joined the core and has no other
configuration.

- Build an E-Line between CEB1 on VLAN 400 and CEB3 on VLAN 40. The CEs use 172.31.40.0/24 on it.
- Build it with EVPN (EVPN-VPWS), in EVPN instance **400**. The identifier of each end follows the site numbers.
- XR01 and XR03 exchange their EVPN routes only through the route reflector XR02. There must be no BGP session between
  XR01 and XR03. The BGP router ID of XR03 is its Loopback0 address.

### Task M11-4

With change CHG-1411, the colleague also built two more E-Lines between site 1 and site 3 with EVPN-VPWS, in EVPN
instances 410 and 420. The customer says that neither of them carries any traffic.

- Make both E-Lines work. The CEs use 172.31.41.0/24 (VLAN 410 at site 1, VLAN 41 at site 3) and 172.31.42.0/24
  (VLAN 420 at site 1, VLAN 42 at site 3).
- Where the configuration does not follow the provider's conventions, bring it in line with them.

### Task M11-5

Customer B wants to carry its own VLANs 10 and 20 between site 1 and site 3, as they are. The customer's equipment
sends them with an outer tag of **500**, the tag agreed with the provider, outside its own VLAN tag (Q-in-Q).

- Carry the frames of VLANs 10 and 20 inside outer tag 500 between site 1 and site 3 on one E-Line, in EVPN instance
  **500**. The CEs use 172.31.51.0/24 on VLAN 10 and 172.31.52.0/24 on VLAN 20.
- When the customer adds more of its own VLANs inside outer tag 500 later, the E-Line must carry them without any
  change on the provider side.
- Frames that have only the outer tag 500 (no inner tag) must not be carried on this E-Line. The CEs have the
  addresses 172.31.50.0/24 for checking this.
