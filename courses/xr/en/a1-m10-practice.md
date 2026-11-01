# M10 — Practice 1: from LDP to SR

These are the tasks of lab **XRT-10**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Ground rules

- You configure **XR01**, and in Task M10-5 also **XR02**. All the other routers are fixed; do not change them. You
  may log in to them to look. The CEs, SVC and INET belong to the customers, the shared services and the Internet.
- The tasks give no command examples. Each task states the behaviour that is required. The reading pages have
  configuration examples; the ones that have the same form as a task's answer are folded. To solve a task on your own
  first, use the CLI help (`?`), the `show` commands, and the Cisco IOS XR configuration guides and command references
  to find the commands.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. Give IS-IS and BGP half a minute to settle after a commit.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XR01 runs **IOS XRv 9000** 26.1.1. XR02 runs **IOS XRd** 26.1.1, the container form of IOS XR: it is the route
  reflector, outside the forwarding path.

## Topology

| Link | Ends | Addressing | IS-IS metric |
|---|---|---|---|
| PRIMARY | XR01 GigabitEthernet0/0/0/0 ─ RT01 Ethernet0/0 | 10.0.1.0/24 (XR01 .1, RT01 .11) | 10 |
| BACKUP | XR01 GigabitEthernet0/0/0/1 ─ RT03 Ethernet0/0 | 10.0.3.0/24 (XR01 .1, RT03 .13) | 100 |
| CORE-A | RT01 Ethernet0/1 ─ RT02 Ethernet0/0 | 10.0.12.0/24 (RT01 .11, RT02 .12) | 10 |
| CORE-B | RT03 Ethernet0/1 ─ RT02 Ethernet0/1 | 10.0.23.0/24 (RT03 .13, RT02 .12) | 100 |
| RR-LINK | RT03 Ethernet0/2 ─ XR02 GigabitEthernet0/0/0/0 | 10.0.33.0/24 (RT03 .13, XR02 .21) | 10 |

| Router | Role | Platform | Loopback0 | Prefix-SID index |
|---|---|---|---|---|
| XR01 | Provider edge | IOS XRv 9000 26.1.1 | 10.255.0.1/32 | 1 (Task M10-1) |
| XR02 | VPNv4 route reflector | IOS XRd 26.1.1 | 10.255.0.21/32 | — |
| RT01 | Core | IOS XE 17.15 | 10.255.0.11/32 | 11 |
| RT02 | Provider edge | IOS XE 17.15 | 10.255.0.12/32 | 12 |
| RT03 | Core | IOS XE 17.15 | 10.255.0.13/32 | 13 |

| Site | Attached to | CE AS | Networks |
|---|---|---|---|
| Customer A, site 1 (CEA1) | XR01 GigabitEthernet0/0/0/2, VRF CUST-A | 65101 | 10.101.1.0/24 |
| Customer A, site 2 (CEA2) | RT02 Ethernet0/2, VRF CUST-A | 65101 | 10.101.2.0/24 |
| Customer B, site 1 (CEB1) | XR01 GigabitEthernet0/0/0/3, VRF CUST-B | 65201 | 10.102.1.0/24 |
| Customer B, site 2 (CEB2) | RT02 Ethernet1/0, VRF CUST-B | 65202 | 10.102.2.0/24 |

- The core runs the IPv4 IS-IS instance `CORE` between XR01, XR02, RT01, RT02 and RT03 (area 49.0001, Level 2 only,
  wide metrics, point-to-point circuits). BFD (100 ms × 3) runs on PRIMARY and BACKUP. RT01 and RT03 do not run BGP.
- The VPNs are those of lab XRT-09: route targets 65000:101 (customer A) and 65000:102 (customer B), VPNv4 sessions
  with the route reflector XR02 only, shared services and Internet access on XR01. Their traffic crosses the core on
  labels, and today those labels come from LDP.
- The provider is moving the core from LDP to **segment routing (SR-MPLS)**. The IOS routers are ready: they run SR in
  IS-IS with the prefix-SID indexes of the table, prefer SR labels over LDP labels, and protect their prefixes with
  TI-LFA. They still run LDP among themselves. On their links to XR01, LDP is still on, but they no longer tie their
  IS-IS metric to it (LDP-IGP synchronisation is off on those links).
- The provider's SR convention: one global block, **16000–23999**, on every router (the platform default); the
  prefix-SID index of a router is the last octet of its Loopback0 address.

## M10 — Segment Routing

### Task M10-1
<p class="tolab"><a href="/_learn?id=XRT-10&amp;step=m10t1">Open in the lab workspace</a> — Read: <a href="a0-m10-segment-routing.html#s2-1">2.1 Giving each router a number</a> · <a href="a0-m10-segment-routing.html#s2-7">2.7 Details of the block</a> · <a href="a0-m10-segment-routing.html#s3-1">3.1 Where the configuration goes</a> · <a href="a0-m10-segment-routing.html#s3-2">3.2 What the routers advertise</a> · <a href="a0-m10-segment-routing.html#s3-3">3.3 A block too small</a> · <a href="a0-m10-segment-routing.html#s4-1">4.1 Two labels for one prefix</a></p>


XR01 is the last router to join SR. A colleague prepared it under change CHG-1301 and left before finishing.

- Make XR01 take part in SR in the IS-IS instance `CORE`, following the convention: the global block of the
  convention and prefix-SID index 1 on Loopback0.
- XR01 must send its labelled traffic (to RT02, and the VPN traffic of the customers) on SR labels, and the other
  routers must reach XR01 on SR labels.
- Keep LDP running on XR01 for now: it is the fallback until the change window closes (Task M10-2).

### Task M10-2
<p class="tolab"><a href="/_learn?id=XRT-10&amp;step=m10t2">Open in the lab workspace</a> — Read: <a href="a0-m10-segment-routing.html#s4-2">4.2 Switching LDP off</a></p>


The change window is over. LDP goes away on XR01.

- Stop LDP on XR01. The IOS routers keep it among themselves.
- The VPN traffic of both customers must keep flowing in both directions, and IS-IS must keep using the links of
  XR01 as before: XR01 must advertise its core links with their usual metrics.
