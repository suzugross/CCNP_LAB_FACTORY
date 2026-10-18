# M3 — OSPF

You know OSPF. This unit is only about how IOS XR lets you write it down, and about three places where the
habits you bring from IOS lead you astray.

Everything shown here was captured on IOS XRv 9000 release 24.3.1.

## 1. One block, three levels

On IOS, OSPF lives in two places: the `router ospf` block and the interfaces (`ip ospf …` lines).
On IOS XR everything lives in the `router ospf` block, in three levels:

| Level | Holds |
|---|---|
| process | router ID, and defaults for every area |
| area | area type, summarisation, and defaults for every interface in the area |
| interface | an interface joins the area by being listed here; settings for that interface only |

There are no `network` statements and nothing OSPF-related under the interfaces themselves (M0).

## 2. Inheritance

Most interface settings — network type, cost, timers, authentication, passive — can be written at any of the three
levels. A setting at process level applies to every interface in every area; a setting at area level to every
interface in that area. The level closest to the interface wins.

That is convenient, and it is also how a link can be configured without a single line under it. Here passive is
set at process level, and only LINK1 turns it off:

```console
router ospf 1
 router-id 1.1.1.1
 passive enable
 area 0
  interface Loopback0
  !
  interface GigabitEthernet0/0/0/0
   network point-to-point
   passive disable
  !
  interface GigabitEthernet0/0/0/2
   network point-to-point
  !
```

LINK2 (Gi0/0/0/2) is in OSPF, has the right network type, and forms no adjacency. Its entry says nothing about
passive. The interface view does:

```console
RP/0/RP0/CPU0:XR01#show ospf interface GigabitEthernet0/0/0/2
GigabitEthernet0/0/0/2 is up, line protocol is up
  Internet Address 10.0.21.1/24, Area 0, SID 0, Strict-SPF SID 0
  Process ID 1, Router ID 1.1.1.1, Network Type POINT_TO_POINT, Cost: 1
  Timer intervals configured, Hello 10, Dead 40, Wait 40, Retransmit 5
    No Hellos (Passive interface)
```

`show running-config router ospf 1 inheritance detail` is meant to show inherited values. On this release it did
not mark the inherited passive at all. Read the effective state from `show ospf interface`.

A process-level `passive enable` with `passive disable` on the links that should form adjacencies is a common design:
a new interface stays silent until someone decides otherwise. Keep that in mind before you "fix" a silent link by
removing the process-level line.

`show ospf interface brief` gives the overview, one line per interface:

```console
Interface          PID   Area            IP Address/Mask    Cost  State Nbrs F/C
Lo0                1     0               1.1.1.1/32         1     LOOP  0/0
Gi0/0/0/0          1     0               10.0.12.1/24       1     P2P   1/1
Gi0/0/0/1          1     0               10.0.50.1/24       1     DR    0/0
Gi0/0/0/2          1     0               10.0.21.1/24       1     P2P   0/0
Gi0/0/0/3          1     1               10.0.23.1/24       1     P2P   0/0
```

## 3. OSPFv3

OSPFv3 is a separate process, `router ospfv3`, with the same three levels and the same inheritance.
The show commands follow the name: `show ospfv3 neighbor`, `show ospfv3 interface`, `show ospfv3 database`.

Two observations from the lab:

- The network-type trap from M0 works the same way. With XR01 on the default broadcast type and RT01 on
  point-to-point, the adjacency reaches FULL/DR and no route is installed.
- In the IPv6 routing table, OSPFv3 routes are labelled with the process as `ospf`:

```console
RP/0/RP0/CPU0:XR01#show route ipv6 2001:db8::2/128
Routing entry for 2001:db8::2/128
  Known via "ospf 1", distance 110, metric 1, type intra area
```

## 4. Areas

Area types and summarisation are written under the area, as on IOS they are written with `area N` keywords:
a stub area, a totally stubby area (no summary LSAs from the ABR), an NSSA, and `range` to summarise at an ABR.

The stub flag in the hello must match on both ends, as on IOS. With only one end calling the area a stub, no
adjacency forms. With both ends set to stub, the branch router receives the default route and every inter-area route:

```console
RT02#show ip route ospf
O*IA  0.0.0.0/0 [110/11] via 10.0.23.1, 00:00:31, Ethernet0/0
O IA     1.1.1.1 [110/11] via 10.0.23.1, 00:00:31, Ethernet0/0
O IA     2.2.2.2 [110/12] via 10.0.23.1, 00:00:31, Ethernet0/0
...
```

Making it totally stubby is a setting on the ABR only. The internal router keeps its plain stub setting.

The running configuration shows defaults in some places: a `range` you typed without options is displayed as
`range … advertise`.

## 5. Command names

| On IOS | On IOS XR |
|---|---|
| `show ip ospf neighbor` | `show ospf neighbor` |
| `show ip ospf interface brief` | `show ospf interface brief` |
| `show ip ospf database` | `show ospf database` |
| `show ipv6 ospf neighbor` | `show ospfv3 neighbor` |
| `show ip route ospf` | `show route ospf` |
| `show ipv6 route` | `show route ipv6` |

Redistribution into OSPF and filtering of routes are done with route policies on IOS XR. They are the subject of M5.

## Practice

Go to lab **XRT-02** and do the M3 tasks, after the M2 tasks.

<p class="tolab"><a href="/_learn?id=XRT-02">Open lab XRT-02 in the workspace</a> — <a href="31-m3-practice.html">The tasks</a></p>

:::note
Source: the IOS XR *Routing Configuration Guide* for the ASR 9000, *Implementing OSPF* (OSPF Hierarchical CLI and CLI
Inheritance), checked October 2026. The following come from measurement on 24.3.1: `inheritance detail` not marking
the inherited passive, and OSPFv3 routes shown as `ospf` in the IPv6 table.
:::
