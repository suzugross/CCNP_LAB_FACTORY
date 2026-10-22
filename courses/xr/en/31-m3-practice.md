# M3 — Practice

These are the tasks of lab **XRT-02**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Topology

| Link | XR01 | Peer | Addressing |
|---|---|---|---|
| LINK1 | GigabitEthernet0/0/0/0 | RT01 Ethernet0/0 | 10.0.12.0/24 (XR01 .1, RT01 .2) |
| SERVERS | GigabitEthernet0/0/0/1 | SRV01 | 10.0.50.0/24 (XR01 .1, SRV01 .10) |
| LINK2 | GigabitEthernet0/0/0/2 | RT01 Ethernet0/1 | 10.0.21.0/24 (XR01 .1, RT01 .2) |
| LINK3 | GigabitEthernet0/0/0/3 | RT02 Ethernet0/0 | 10.0.23.0/24 (XR01 .1, RT02 .2) |

- XR01 Loopback0 1.1.1.1/32. RT01 Loopback0 2.2.2.2/32 (stands in for the NOC workstation).
  RT01 Loopback100 198.51.100.1/24 is the guest network.
- XR01 and RT01 run OSPF process 1, area 0, over LINK1. The addresses above are reachable from the start,
  except those behind LINK2 and LINK3 (subjects of M3).
- IPv6: LINK1 2001:DB8:12::/64 (XR01 ::1, RT01 ::2). XR01 Loopback0 2001:DB8::1/128, RT01 Loopback0 2001:DB8::2/128.
- LINK2 is a backup link to RT01. RT01 gives it OSPF cost 100.
- RT02 is the router of a branch in OSPF area 1, which RT02 runs as a stub area. Its LANs are 172.16.1.0/24,
  172.16.2.0/24 and 172.16.3.0/24 (RT02 .1); its Loopback0 is 3.3.3.3/32.
- SRV01 is a TACACS+ server. Its administrator reports that it is configured with XR01 as a client at **1.1.1.1**,
  with the key `XRT02-Tac-Key`, and that it holds these users:

  | User | Password | What the server grants |
  |---|---|---|
  | `ops1` | `Ops1-Pass` | network administration |
  | `view1` | `View1-Pass` | read-only |
  | the lab account | the lab password | full access |

## M3 — OSPF

### Task M3-1
<p class="tolab"><a href="/_learn?id=XRT-02&amp;step=m3t1">Open in the lab workspace</a> — Read: <a href="30-m3-ospf.html#s2">2. Inheritance</a></p>


LINK2 has been added to OSPF on XR01, but no adjacency forms over it.
Ensure that XR01 and RT01 form an OSPF adjacency over LINK2.
The design rule for XR01 stays in force: an interface added to OSPF must not send hellos unless it is explicitly
meant to form adjacencies. The SERVERS segment must remain without adjacencies.

### Task M3-2
<p class="tolab"><a href="/_learn?id=XRT-02&amp;step=m3t2">Open in the lab workspace</a> — Read: <a href="30-m3-ospf.html#s3">3. OSPFv3</a></p>


Ensure that XR01 and RT01 exchange their IPv6 loopback prefixes by OSPFv3 over LINK1.
XR01 must learn 2001:DB8::2/128 and RT01 must learn 2001:DB8::1/128.

### Task M3-3
<p class="tolab"><a href="/_learn?id=XRT-02&amp;step=m3t3">Open in the lab workspace</a> — Read: <a href="30-m3-ospf.html#s4">4. Areas</a></p>


XR01 is the area border router for area 1.

- Ensure that XR01 and RT02 form an adjacency over LINK3.
- RT02 must receive nothing from outside area 1 except a default route.
- Area 0 must learn the branch LANs as a single prefix, 172.16.0.0/22, and not as separate /24 prefixes.
