# M12 — Practice 1: trusting the marks

These are the tasks of lab **XRT-14**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Ground rules

- You configure **XR01**, and in Task M12-5 also **RR1**. All the other routers are fixed; do not change them. You may
  log in to them to look. CE1, CE2, CUST1, CUST2 and INET belong to the customers and the Internet.
- The tasks give no command examples. Each task states the behaviour that is required. The reading pages have
  configuration examples; the ones that have the same form as a task's answer are folded. To solve a task on your own
  first, use the CLI help (`?`), the `show` commands, and the Cisco IOS XR configuration guides and command references
  to find the commands.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. A check sends test traffic and counts it, so it takes one to three
  minutes.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- Each task also has a **How to verify** button: an example of checking your work in order (is it in → send traffic and count →
  count where it arrives → did anything else break). Open it whenever you like; it is not logged. Verify by hand before you press Check.
- XR01 runs **IOS XRv 9000** 26.1.1. Its QoS policy counters catch up some tens of seconds after the traffic.
  RR1 runs **IOS XRd** 26.1.1, the container form of IOS XR: it is the route reflector, outside the forwarding path.
- The inputs of CE1 and CE2, and the input of P1 on the XR01 side, have fixed QoS policies that only count the packets
  they receive by DSCP or by EXP (`COUNT-DSCP` on CE1 and CE2, `COUNT-EXP` on P1). The checks use them; do not change
  them.

## Topology

| Link | Ends | Addressing |
|---|---|---|
| CORE-1 | XR01 GigabitEthernet0/0/0/0 ─ P1 Ethernet0/0 | 10.0.1.0/24 (XR01 .1, P1 .51) |
| CORE-2 | P1 Ethernet0/1 ─ PE2 Ethernet0/0 | 10.0.2.0/24 (P1 .51, PE2 .2) |
| RR-LINK | P1 Ethernet0/2 ─ RR1 GigabitEthernet0/0/0/0 | 10.0.52.0/24 (P1 .51, RR1 .52) |
| SITE-1 | XR01 GigabitEthernet0/0/0/1 ─ CE1 Ethernet0/0 | 172.16.1.0/24 (CE1 .1, XR01 .254) |
| CUST-1 | XR01 GigabitEthernet0/0/0/2 ─ CUST1 Ethernet0/0 | 172.20.1.0/24 (CUST1 .1, XR01 .254) |
| PEERING | XR01 GigabitEthernet0/0/0/3 ─ INET Ethernet0/0 | 10.0.100.0/24 (XR01 .1, INET .100) |
| SITE-2 | PE2 Ethernet0/1 ─ CE2 Ethernet0/0 | 172.16.2.0/24 (CE2 .1, PE2 .254) |
| CUST-2 | PE2 Ethernet0/2 ─ CUST2 Ethernet0/0 | 172.20.2.0/24 (CUST2 .1, PE2 .254) |

| Router | Role | Platform | Loopback0 |
|---|---|---|---|
| XR01 | Provider edge, Internet border | IOS XRv 9000 26.1.1 | 10.255.0.1/32 |
| P1 | Core (no BGP) | IOS XE 17.15 | 10.255.0.51/32 |
| PE2 | Provider edge | IOS XE 17.15 | 10.255.0.2/32 |
| RR1 | Route reflector (IPv4 unicast and VPNv4), RTBH trigger | IOS XRd 26.1.1 | 10.255.0.52/32 |

| Customer | Attached to | Table | Addressing |
|---|---|---|---|
| Customer A site 1 (CE1, AS 65001) | XR01 GigabitEthernet0/0/0/1 (eBGP) | VRF A | LAN 10.100.1.0/24, phones 10.46.1.1, business system 10.21.1.1 |
| Customer A site 2 (CE2, AS 65002) | PE2 Ethernet0/1 (eBGP) | VRF A | LAN 10.100.2.0/24, voice server 10.46.2.1, business system 10.21.2.1 |
| Internet customer CUST1 | XR01 GigabitEthernet0/0/0/2 (static, single link) | Global | 198.51.100.0/25 |
| Internet customer CUST2 | PE2 Ethernet0/2 (static) | Global | 198.51.100.128/25 |
| INET (AS 64500) | XR01 GigabitEthernet0/0/0/3 (eBGP) | Global | Advertises 203.0.113.0/24 and a default route |

- In the core, all routers run the IS-IS instance `CORE` (level 2), and LDP runs on CORE-1 and CORE-2. P1 does not
  run BGP. RR1 reflects the IPv4 unicast and VPNv4 routes to XR01 and PE2. Internet traffic, too, is carried with LDP
  labels to its BGP next hop (the Loopback0 of a PE).
- XR01, PE2 and RR1 have a static route from the discard address 192.0.2.1/32 to Null0.
- The CEs of customer A send with the following DSCP, by destination (fixed):

  | Sending CE | Destination | DSCP |
  |---|---|---|
  | CE1 | Voice network 10.46.2.0/24 | EF |
  | CE1 | Business system 10.21.2.0/24 | AF21 |
  | CE1 | LAN 10.100.2.0/24 | EF (set by the PCs at site 1) |
  | CE2 | Voice network 10.46.1.0/24 | EF |
  | CE2 | Business system 10.21.1.0/24 | AF21 |
  | CE2 | LAN 10.100.1.0/24 | None |

- PE2 carries what it receives from CE2 with EXP 5 for EF, EXP 3 for AF21 and EXP 0 for the rest (fixed).

## M12 — Data-plane protection and QoS

### Task M12-1
<p class="tolab"><a href="/_learn?id=XRT-14&amp;step=m12t1">Open in the lab workspace</a> — Read: <a href="d0-m12-marking.html#s2-2">2.2 The trust boundary</a> · <a href="d0-m12-marking.html#s2-3">2.3 The mark on the label: EXP</a> · <a href="d0-m12-marking.html#s2-4">2.4 On the wire: with no policy at all</a> · <a href="d0-m12-marking.html#s3-1">3.1 The parts of MQC</a> · <a href="d0-m12-marking.html#s3-2">3.2 The ingress PE: classify and set the EXP</a> · <a href="d0-m12-marking.html#s3-5">3.5 Pitfalls</a></p>


Customer A's contract allows EF only on traffic to the voice network (10.46.0.0/16). The PCs at site 1 also mark
their traffic to the LAN with EF.

- Of the EF that XR01 receives from site 1, carry the traffic that is not to the voice network with DSCP 0. Do not
  change any other DSCP.
- In the core, carry EF to the voice network with EXP 5, AF21 with EXP 3, and everything else with EXP 0. Every label
  that is pushed carries the same EXP.
