# XR Track 10 — Segment Routing

This lab is the practice part of unit **M10 Segment Routing** of the XR track. It continues where lab XRT-09 ended:
the core and the VPN customers are the same, and XR01 and XR02 start with the work of tasks M9-1 to M9-4 done. The unit
has three pages: *How segment routing works* (tasks M10-1 and M10-2), *TI-LFA* (task M10-3) and *SR policies and the
PCE* (tasks M10-4 and M10-5). Read each page before its tasks, and work through the tasks here, in order. Each task
builds on the previous one.

## Ground rules

- You configure **XR01**, and in Task M10-5 also **XR02**. All the other routers are fixed; do not change them. You
  may log in to them to look. The CEs, SVC and INET belong to the customers, the shared services and the Internet.
- No command examples are given. Each task states the behaviour that is required. Use the CLI help (`?`),
  the `show` commands, and the Cisco IOS XR configuration guides and command references to find the commands.
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

XR01 is the last router to join SR. A colleague prepared it under change CHG-1301 and left before finishing.

- Make XR01 take part in SR in the IS-IS instance `CORE`, following the convention: the global block of the
  convention and prefix-SID index 1 on Loopback0.
- XR01 must send its labelled traffic (to RT02, and the VPN traffic of the customers) on SR labels, and the other
  routers must reach XR01 on SR labels.
- Keep LDP running on XR01 for now: it is the fallback until the change window closes (Task M10-2).

### Task M10-2

The change window is over. LDP goes away on XR01.

- Stop LDP on XR01. The IOS routers keep it among themselves.
- The VPN traffic of both customers must keep flowing in both directions, and IS-IS must keep using the links of
  XR01 as before: XR01 must advertise its core links with their usual metrics.

### Task M10-3

Losing PRIMARY or BACKUP must not wait for IS-IS to compute a new path.

- On both core links of XR01, make XR01 compute, ahead of time, a backup path for every IS-IS prefix that it reaches
  over the link, so that it can switch to it as soon as the link fails (link protection).
- RT01's loopback has no loop-free alternate in the plain sense: the backup must use segment routing to reach it.
- While the network converges after a link goes up or down, XR01 must avoid the temporary loops that the routers'
  different update times can cause, using segment routing.

### Task M10-4

RT01 is due for maintenance. Customer A has asked that its traffic from site 1 to site 2 stop crossing the link
between XR01 and RT01 now. Nothing changes for customer B.

- Steer the traffic of customer A from XR01 towards site 2 onto a path that avoids the link PRIMARY. The traffic of
  customer B keeps the shortest path.
- Use the provider's convention: the routes of a service that needs a special path carry the **color 100**.
- The path must be computed by XR01 from the topology. Do not write the hops of the path into the configuration.
- Do not change RT02 or the route reflector.

### Task M10-5

The provider plans a redundant service that needs two paths from XR01 to RT02 that never share a link. Paths of
this kind are to be computed by a central path computation element.

- Make XR02 a path computation element at its Loopback0 address, using the topology that it learns in IS-IS. XR02
  stays outside the forwarding path.
- On XR01, create two SR policies to RT02 with the colors **201** and **202**. Their paths must be computed by XR02,
  not by XR01, and the two paths must not share any link.
