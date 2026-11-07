# M9 — Practice 1: the first sites

These are the tasks of lab **XRT-09**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Ground rules

- You configure **XR01**, and from Task M9-2 also **XR02**. All the other routers are fixed; do not change them. You
  may log in to them to look. The CEs, SVC and INET belong to the customers, the shared services and the Internet.
- The tasks give no command examples. Each task states the behaviour that is required. The reading pages have
  configuration examples; the ones that have the same form as a task's answer are folded. To solve a task on your own
  first, use the CLI help (`?`), the `show` commands, and the Cisco IOS XR configuration guides and command references
  to find the commands.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. A BGP session with an IOS router can take up to a minute to come up,
  and an IOS router up to a minute more to pass on a route it has just learned.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XR01 runs **IOS XRv 9000** 26.1.1. XR02 runs **IOS XRd** 26.1.1, the container form of IOS XR: it is the route
  reflector, outside the forwarding path.
- The customer-facing interfaces of XR01 (GigabitEthernet0/0/0/2 to 0/0/0/5) have a description and no address.

## Topology

| Link | Ends | Addressing | IS-IS metric |
|---|---|---|---|
| PRIMARY | XR01 GigabitEthernet0/0/0/0 ─ RT01 Ethernet0/0 | 10.0.1.0/24 (XR01 .1, RT01 .11) | 10 |
| BACKUP | XR01 GigabitEthernet0/0/0/1 ─ RT03 Ethernet0/0 | 10.0.3.0/24 (XR01 .1, RT03 .13) | 100 |
| CORE-A | RT01 Ethernet0/1 ─ RT02 Ethernet0/0 | 10.0.12.0/24 (RT01 .11, RT02 .12) | 10 |
| CORE-B | RT03 Ethernet0/1 ─ RT02 Ethernet0/1 | 10.0.23.0/24 (RT03 .13, RT02 .12) | 100 |
| RR-LINK | RT03 Ethernet0/2 ─ XR02 GigabitEthernet0/0/0/0 | 10.0.33.0/24 (RT03 .13, XR02 .21) | 10 |

| Router | Role | Platform | Loopback0 |
|---|---|---|---|
| XR01 | Provider edge | IOS XRv 9000 26.1.1 | 10.255.0.1/32 |
| XR02 | VPNv4 route reflector | IOS XRd 26.1.1 | 10.255.0.21/32 |
| RT01 | Core | IOS XE 17.15 | 10.255.0.11/32 |
| RT02 | Provider edge | IOS XE 17.15 | 10.255.0.12/32 |
| RT03 | Core | IOS XE 17.15 | 10.255.0.13/32 |

| Site | Attached to | Addressing | CE AS | Networks |
|---|---|---|---|---|
| Customer A, site 1 (CEA1) | XR01 GigabitEthernet0/0/0/2 | 172.16.11.0/24 (XR01 .1, CEA1 .2) | 65101 | 10.101.1.0/24, public 198.51.100.0/25 |
| Customer A, site 2 (CEA2) | RT02 Ethernet0/2 | 172.16.12.0/24 (RT02 .1, CEA2 .2) | 65101 | 10.101.2.0/24, public 198.51.100.128/25 |
| Customer B, site 1 (CEB1) | XR01 GigabitEthernet0/0/0/3 | 172.16.21.0/24 (XR01 .1, CEB1 .2) | 65201 | 10.102.1.0/24 |
| Customer B, site 2 (CEB2) | RT02 Ethernet1/0 | 172.16.22.0/24 (RT02 .1, CEB2 .2) | 65202 | 10.102.2.0/24 |
| Shared services (SVC) | XR01 GigabitEthernet0/0/0/4 | 172.16.91.0/24 (XR01 .1, SVC .2) | — | 10.99.1.0/24, 10.99.2.0/24 |
| Internet (INET) | XR01 GigabitEthernet0/0/0/5 | 192.0.2.0/24 (XR01 .1, INET .2) | 64500 | default route, 203.0.113.0/24 |

| VRF on XR01 | Route distinguisher | Imported route targets | Exported route targets |
|---|---|---|---|
| CUST-A | 10.255.0.1:101 | 65000:101, 65000:900 | 65000:101 |
| CUST-B | 10.255.0.1:102 | 65000:102, 65000:900 | 65000:102 |
| SVC | 10.255.0.1:900 | 65000:101, 65000:102 | see Task M9-3 |

- The core runs the IPv4 IS-IS instance `CORE` between XR01, XR02, RT01, RT02 and RT03 (area 49.0001, Level 2 only,
  wide metrics, point-to-point circuits) and LDP on every core link as in lab XRT-07. The RR-LINK has no LDP.
  RT01 and RT03 do not run BGP.
- All provider routers are in AS 65000. RT02 has the VRFs CUST-A and CUST-B with the same route targets as XR01 and
  route distinguishers 10.255.0.12:101 and 10.255.0.12:102. It exchanges VPNv4 routes with XR02 only, and uses
  `as-override` towards CEA2.
- Customer A has one AS, 65101, at both sites. The CEs advertise their networks in eBGP and accept what the provider
  sends. SVC runs no routing protocol: it has a static default route to XR01.

## M9 — L3VPN

### Task M9-1
<p class="tolab"><a href="/_learn?id=XRT-09&amp;step=m9t1">Open in the lab workspace</a> — Read: <a href="90-m9-l3vpn.html#s2-1">2.1 A separate table in the PE: the VRF</a> · <a href="90-m9-l3vpn.html#s2-2">2.2 A number on the route: the RD</a> · <a href="90-m9-l3vpn.html#s2-3">2.3 A tag on the route: the RT</a> · <a href="90-m9-l3vpn.html#s2-4">2.4 Between the PEs: VPNv4 and the VPN label</a> · <a href="90-m9-l3vpn.html#s3-1">3.1 Where each part goes</a> · <a href="90-m9-l3vpn.html#s3-3">3.3 The session with the CE</a> · <a href="90-m9-l3vpn.html#s3-5">3.5 The order to check in</a></p>


Customers A and B are new VPN customers. Their second sites are already in service on RT02; their first sites are
connected to XR01.

- Connect site 1 of customer A (CEA1) and site 1 of customer B (CEB1) to XR01, in the VRFs and with the route
  distinguishers and route targets of the table. Address the interfaces as in the table.
- Exchange routes with CEA1 and CEB1 in eBGP. XR01 must accept every route that they advertise, and advertise the
  routes of their VPN to them.
- XR01 must exchange VPN routes with the route reflector XR02 only, over a session from its Loopback0. Do not create a
  VPNv4 session between XR01 and RT02.
- Do not change XR02 in this task.
