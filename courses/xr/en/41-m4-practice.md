# M4 — Practice

These are the tasks of lab **XRT-04**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Ground rules

- You configure **XR01 only**. RT01, RT02 and RT03 are fixed; do not change them. You may log in to them to look.
- No command examples are given. Each task states the behaviour that is required. Use the CLI help (`?`),
  the `show` commands, and the Cisco IOS XR configuration guides and command references to find the commands.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. IS-IS needs a few seconds to flood a change and recompute routes.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XR01 runs **IOS XRd**, the container form of IOS XR. For this unit it behaves as IOS XRv 9000 does.
  It forwards ping through itself, but not traceroute or TCP sessions; check your work with `show` commands and ping.

## Topology

| Link | XR01 | Peer | Addressing |
|---|---|---|---|
| ACCESS | GigabitEthernet0/0/0/0 | RT01 Ethernet0/0 | 10.0.11.0/24, 2001:db8:11::/64 (XR01 .1, RT01 .2) |
| CORE-A | GigabitEthernet0/0/0/1 | RT02 Ethernet0/0 | 10.0.12.0/24, 2001:db8:12::/64 (XR01 .1, RT02 .2) |
| CORE-B | GigabitEthernet0/0/0/2 | RT03 Ethernet0/0 | 10.0.13.0/24, 2001:db8:13::/64 (XR01 .1, RT03 .3) |
| — | — | RT02 Ethernet0/1 ─ RT03 Ethernet0/1 | 10.0.23.0/24, 2001:db8:23::/64 (RT02 .2, RT03 .3) |

| Router | Loopback0 | Area | Level | Other networks in IS-IS |
|---|---|---|---|---|
| XR01 | 10.255.0.1/32, 2001:db8:255::1/128 | 49.0001 | 1 and 2 | — |
| RT01 | 10.255.0.11/32, 2001:db8:255::11/128 | 49.0001 | 1 only | access LAN 10.11.0.0/16, 2001:db8:1011::/64 |
| RT02 | 10.255.0.2/32, 2001:db8:255::2/128 | 49.0002 | 2 only | services 10.20.0.0/16, 2001:db8:1020::/64 |
| RT03 | 10.255.0.3/32, 2001:db8:255::3/128 | 49.0003 | 2 only | services 10.30.0.0/16, 2001:db8:1030::/64 |

- **System IDs** are derived from the Loopback0 address: each octet is written with three digits and the twelve
  digits are grouped in fours. RT02 (10.255.0.2) has system ID `0102.5500.0002`.
- RT02 and RT03 form the **backbone**. It has been migrated to **wide metrics**. Its design rule gives every
  **backup link a metric of 1000 in both directions**. CORE-B is a backup link.
- RT01 is an older access router. It runs Level 1 only and has kept the original metric format.
- The three IOS routers carry IPv4 and IPv6 in IS-IS, with the IOS defaults. All their links are configured as
  point-to-point links.

## M4 — IS-IS

### Task M4-1
<p class="tolab"><a href="/_learn?id=XRT-04&amp;step=m4t1">Open in the lab workspace</a> — Read: <a href="40-m4-isis.html#s9">9. IS-IS on IOS XR</a> · <a href="40-m4-isis.html#s2">2. Addresses: the NET</a> · <a href="40-m4-isis.html#s3">3. Levels and adjacencies</a> · <a href="40-m4-isis.html#s4">4. Hellos, point-to-point links and the DIS</a></p>


A colleague has started the IS-IS configuration of XR01, instance `CORE`. No adjacency comes up.

- XR01 must be in area 49.0001, with a system ID that follows the convention.
- XR01 must form a Level 1 adjacency with RT01 and Level 2 adjacencies with RT02 and RT03.
- On each link, XR01 must send hellos only for the level that its neighbour runs.
- All three links are point-to-point links: no designated IS is elected on them.
- XR01 must run IS-IS for IPv4 and IPv6 on Loopback0 and on the three links, as the IOS routers do.

### Task M4-2
<p class="tolab"><a href="/_learn?id=XRT-04&amp;step=m4t2">Open in the lab workspace</a> — Read: <a href="40-m4-isis.html#s7">7. Metrics: narrow and wide</a> · <a href="40-m4-isis.html#s6">6. Between the levels: the ATT bit and route leaking</a></p>


The Level 2 adjacencies are up. Yet XR01 has no routes to the backbone, the backbone has none to area 49.0001,
and RT01 cannot reach anything outside its area.

- Restore the exchange of IPv4 routes between area 49.0001 and the backbone. RT01 must be able to reach the
  services networks of RT02 and RT03.
- RT01 is not to be changed. It must keep its routes.
- Apply the backbone's design rule for backup links on XR01's side of CORE-B. While CORE-A is up, XR01 must reach
  RT03 through RT02.

### Task M4-3
<p class="tolab"><a href="/_learn?id=XRT-04&amp;step=m4t3">Open in the lab workspace</a> — Read: <a href="40-m4-isis.html#s8">8. IPv6: one topology or several</a></p>


IPv6 is not exchanged yet, although every router runs IS-IS for it.

- XR01 must have IS-IS routes to the IPv6 loopbacks and networks of RT01, RT02 and RT03. RT02 and RT03 must have
  routes to the IPv6 loopbacks of XR01 and RT01 and to RT01's access LAN. RT01 must be able to reach the
  services networks over IPv6.
- IPv6 traffic must take the same paths as IPv4 traffic, to every destination including the link subnets.
  CORE-B stays a backup link for IPv6 as well.

### Task M4-4
<p class="tolab"><a href="/_learn?id=XRT-04&amp;step=m4t4">Open in the lab workspace</a> — Read: <a href="40-m4-isis.html#s10">10. Leaking with a route policy</a> · <a href="40-m4-isis.html#s6">6. Between the levels: the ATT bit and route leaking</a></p>


RT01 is going to become an MPLS edge router. It will need a route of its own to the loopback of every backbone router;
a default route will not do.

- RT01 must have an IS-IS route to the IPv4 and the IPv6 loopback of RT02 and of RT03.
- Nothing else from outside area 49.0001 may be added to RT01's routing tables. RT01 keeps reaching everything else
  through its default routes.
- Loopbacks are taken from 10.255.0.0/24 and 2001:db8:255::/64. When a new router joins the backbone, its
  loopbacks must reach RT01 with no change to XR01.
