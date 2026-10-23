# M4 — Practice, second pass

These are the tasks of lab **XRT-05**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Ground rules

- You configure **XR01 only**. RT01, RT02 and RT03 are fixed; do not change them. You may log in to them to look.
- No command examples are given. Each task states the behaviour that is required. Use the CLI help (`?`),
  the `show` commands, and the Cisco IOS XR configuration guides and command references to find the commands.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. IS-IS needs a few seconds to flood a change and recompute routes;
  a broken adjacency takes up to 30 seconds to time out.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XR01 runs **IOS XRd**, the container form of IOS XR. For this unit it behaves as IOS XRv 9000 does.
  It forwards ping through itself, but not traceroute or TCP sessions; check your work with `show` commands and ping.

## Topology

| Link | XR01 | Peer | Addressing |
|---|---|---|---|
| ACCESS | GigabitEthernet0/0/0/0 | RT01 Ethernet0/0 | 10.0.11.0/24, 2001:db8:11::/64 (XR01 .1, RT01 .2) |
| CORE-A | GigabitEthernet0/0/0/1 | RT02 Ethernet0/0 | 10.0.12.0/24, 2001:db8:12::/64 (XR01 .1, RT02 .2) |
| CORE-B | GigabitEthernet0/0/0/2 | RT03 Ethernet0/0 | 10.0.13.0/24, 2001:db8:13::/64 (XR01 .1, RT03 .3) |
| SVC-LAN | GigabitEthernet0/0/0/3 | RT02 Ethernet0/2, RT03 Ethernet0/2 (one shared segment) | 10.0.100.0/24, 2001:db8:100::/64 (XR01 .1, RT02 .2, RT03 .3) |
| — | — | RT02 Ethernet0/1 ─ RT03 Ethernet0/1 | 10.0.23.0/24, 2001:db8:23::/64 (RT02 .2, RT03 .3) |

| Router | Loopback0 | Area | Level | Other networks in IS-IS |
|---|---|---|---|---|
| XR01 | 10.255.0.1/32, 2001:db8:255::1/128 | 49.0001 | 1 and 2 | — |
| RT01 | 10.255.0.11/32, 2001:db8:255::11/128 | 49.0001, 49.0010 | 1 only | access LANs 10.11.1.0/24 to 10.11.4.0/24, 2001:db8:1011:1::/64 to 2001:db8:1011:4::/64 |
| RT02 | 10.255.0.2/32, 2001:db8:255::2/128 | 49.0002 | 2 only | services 10.20.0.0/16, 2001:db8:1020::/64 |
| RT03 | 10.255.0.3/32, 2001:db8:255::3/128 | 49.0003 | 2 only | services 10.30.0.0/16, 2001:db8:1030::/64 |

- XR01 is configured as tasks M4-1 to M4-4 left it: IS-IS instance `CORE`, wide metrics at Level 2, single topology
  for IPv6, CORE-B at metric 1000, and the backbone loopbacks leaked into Level 1.
- RT02 and RT03 form the **backbone**: wide metrics, and a metric of 1000 in both directions on backup links. CORE-B is
  a backup link.
- RT01 is an older access router. It runs Level 1 only, with the original metric format, and it does not support
  IS-IS authentication.
- The three IOS routers carry IPv4 and IPv6 in IS-IS, in single topology. Their links to XR01 and to each other are
  point-to-point links. SVC-LAN is a broadcast segment.

## M4 — IS-IS, second pass

### Task M4-5
<p class="tolab"><a href="/_learn?id=XRT-05&amp;step=m4t5">Open in the lab workspace</a> — Read: <a href="42-m4-isis-deeper.html#s1-1">1.1 What is authenticated</a> · <a href="42-m4-isis-deeper.html#s1-2">1.2 Key chains on IOS XR</a> · <a href="42-m4-isis-deeper.html#s1-3">1.3 What a mismatch looks like</a> · <a href="42-m4-isis-deeper.html#s1-4">1.4 Keeping a level unauthenticated</a></p>


Last night the security team turned on IS-IS authentication in the backbone under work order SEC-0412. The work
covered RT02 and RT03 but left XR01 out. This morning XR01 has lost the backbone, and RT01 can no longer reach
anything outside its area.

| Work order SEC-0412 | |
|---|---|
| Scope | All Level 2 IS-IS packets |
| Key chain | `ISIS-L2` |
| Key | ID 1, key string `Bb0ne-2026` |
| Algorithm | HMAC-MD5 |
| Validity | From 00:00 on 1 January 2026, with no expiry |

- Bring XR01 in line with work order SEC-0412 on CORE-A and CORE-B. SVC-LAN is dealt with in task M4-6.
- Restore the exchange of IPv4 and IPv6 routes between area 49.0001 and the backbone, in both directions.
- Level 1 stays unauthenticated. Every change that RT01 makes to its prefixes must keep reaching XR01 and the backbone.

### Task M4-6
<p class="tolab"><a href="/_learn?id=XRT-05&amp;step=m4t6">Open in the lab workspace</a> — Read: <a href="42-m4-isis-deeper.html#s2-1">2.1 The pseudonode</a> · <a href="42-m4-isis-deeper.html#s2-2">2.2 The election</a> · <a href="42-m4-isis-deeper.html#s2-3">2.3 Point-to-point against broadcast</a></p>


SVC-LAN, a shared segment for the services platform, has been cabled to XR01. RT02 and RT03 already run IS-IS on it.

- XR01 must run IS-IS for IPv4 and IPv6 on SVC-LAN and form Level 2 adjacencies there with RT02 and RT03,
  in accordance with work order SEC-0412.
- SVC-LAN carries Level 2 only. XR01 must not send Level 1 hellos on it.
- XR01 must be the designated IS of SVC-LAN, and must keep that role when RT02 or RT03 restarts. RT02 and RT03 are not
  to be changed.

### Task M4-7
<p class="tolab"><a href="/_learn?id=XRT-05&amp;step=m4t7">Open in the lab workspace</a> — Read: <a href="42-m4-isis-deeper.html#s3-1">3.1 Where and how</a> · <a href="42-m4-isis-deeper.html#s3-2">3.2 What it costs</a></p>


The backbone team has asked area 49.0001 to advertise fewer prefixes.

- The backbone must receive RT01's access LANs as one IPv4 route, 10.11.0.0/16, and one IPv6 route,
  2001:db8:1011::/48, and must not receive the individual access LAN prefixes.
- Inside area 49.0001 every prefix keeps its own route. RT01's loopbacks keep their own routes in the backbone.

### Task M4-8
<p class="tolab"><a href="/_learn?id=XRT-05&amp;step=m4t8">Open in the lab workspace</a> — Read: <a href="42-m4-isis-deeper.html#s4-2">4.2 Renumbering an area</a> · <a href="42-m4-isis-deeper.html#s4-1">4.1 More than one NET</a></p>


Area 49.0001 is being renumbered to 49.0010. RT01 has already been given the new area address as a second NET, and
keeps the old one until the end of the work.

- Move XR01 to area 49.0010 and remove area 49.0001 from it. XR01 keeps its system ID.
- No adjacency of XR01 may go down while you do this: not the one with RT01, and not the ones with the backbone.
- The Check reads XR01's adjacency log from the moment that the new area is configured. If an adjacency goes down,
  make 49.0001 the only area of XR01 again and repeat the move.
