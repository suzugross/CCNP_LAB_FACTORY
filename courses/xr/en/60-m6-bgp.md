# M6 — BGP

You know BGP: sessions, attributes, path selection. This unit is about how IOS XR lays BGP out, and about the places
where the IOS habits you bring lead you astray. It builds on M5: on IOS XR, most of what you do to BGP routes is done
with route policies.

The outputs in this unit were captured on IOS XRd 26.1.1 (lab XRT-03). The same BGP commands gave the same results on
IOS XRv 9000 26.1.1.

## 1. How the configuration is laid out

On IOS, a neighbour is created with `neighbor … remote-as` and then activated per address family with
`neighbor … activate`. On IOS XR the configuration is a tree:

```console
router bgp 65000
 bgp router-id 1.1.1.1
 address-family ipv4 unicast
  network 203.0.113.0/24
 !
 neighbor 10.0.11.2
  remote-as 65101
  description ISP-A
  address-family ipv4 unicast
   route-policy ISP-IN(200, 101) in
   route-policy ISP-OUT(1001, 0) out
  !
 !
```

- An address family must first be enabled for the process (`address-family ipv4 unicast` directly under
  `router bgp`). Only then can a neighbour use it.
- A neighbour is active in an address family because the address family appears under it. There is no `activate`.
- Session settings (remote AS, update source, timers, password) sit directly under the neighbour. Settings that
  concern routes (policies, next-hop-self, community sending, prefix limits) sit under the neighbour's address family.

## 2. iBGP between loopbacks

Internal peers usually peer between loopbacks, so that the session survives the loss of one link. Two things are
needed, and IOS XR treats them as IOS does:

- **The source address.** Without `update-source`, XR01 opens the session from the outgoing interface. A peer that
  knows XR01 only by its loopback refuses the connection, and the session stays in Active. `update-source Loopback0`
  under the neighbour fixes that.
- **The next hop.** iBGP does not change the next hop of routes learnt from eBGP. RT04 receives the provider routes
  with the provider's address as next hop, which it cannot reach:

```console
RT04#show ip bgp 11.0.0.0
BGP routing table entry for 11.0.0.0/8, version 0
Paths: (1 available, no best path)
  65101
    10.0.11.2 (inaccessible) from 1.1.1.1 (1.1.1.1)
      Origin IGP, metric 0, localpref 200, valid, internal
      Community: 65000:101
```

`next-hop-self` under the neighbour's address family makes XR01 announce itself as the next hop. Carrying the link
subnets in the IGP would work too, at the price of putting external addresses into the internal routing.

Two differences from eBGP are worth noticing in that output:

- The route arrived **without any route policy** on the iBGP neighbour. The default drop from M5 applies to eBGP only.
- It arrived with its **communities**. XR01 sends communities to iBGP neighbours by default; `send-community-ebgp` is
  needed for eBGP neighbours only.

## 3. Redistribution

Routes from another protocol enter BGP with `redistribute` under the process's address family. Like every attach
point, it takes a route policy, and without one every route of the source protocol is taken: loopbacks and link
subnets included.

```console
router bgp 65000
 address-family ipv4 unicast
  redistribute ospf 1 route-policy OSPF-TO-BGP
```

A redistributed route appears in the BGP table as locally originated, with origin incomplete and the IGP metric as MED:

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 203.0.113.128/26
...
  Local
    10.0.14.2 from 0.0.0.0 (1.1.1.1)
      Origin incomplete, metric 2, localpref 100, weight 32768, valid, redistributed, best, group-best
```

Where a redistributed route goes next is decided by the outbound policies. A prefix-set entry written without `ge`
or `le` matches that one prefix only, so an outbound filter for `203.0.113.0/24` does not let the /26 prefixes out.

## 4. Prepending, and a trap with apply

`prepend as-path own-as <n>` adds your own AS n times; `prepend as-path <AS> <n>` adds another number.
A count of 0 is accepted and does nothing, which makes the count usable as a parameter.

The trap lies in combining a change with a policy that filters. Suppose ISP-OUT decides what a provider may receive,
and you write a new policy for ISP-B:

```console
route-policy B-OUT
  apply ISP-OUT(1002)
  prepend as-path own-as 3
end-policy
```

It reads as "what ISP-OUT allows, prepended". It is not. A route that ISP-OUT drops is dropped. But a route that
ISP-OUT does not pass simply reaches the end of ISP-OUT, undecided, and returns to B-OUT. There `prepend` changes it,
and a changed route is accepted (M5). Measured in the lab, ISP-B received every route learnt from ISP-A, and the
customer route marked "do not announce to ISP-B", all of them prepended.

Two correct forms:

- Use the applied policy as a condition: `if apply ISP-OUT(1002) then prepend as-path own-as 3 endif`.
  The condition is true for the routes the applied policy passes.
- Make the prepend part of the filtering policy itself, with the count as a parameter.

## 5. Templates

IOS XR has three kinds of templates for neighbours:

| Template | Holds |
|---|---|
| `session-group` | session settings only (remote AS, update source, timers, password…) |
| `af-group NAME address-family …` | settings of one address family only (policies, community sending, prefix limit…) |
| `neighbor-group` | both; its address families can also use an af-group |

A neighbour takes a neighbor-group with `use neighbor-group NAME`; an address family takes an af-group with
`use af-group NAME`. A neighbour inherits every value it does not set itself, and a value it sets itself wins.
So moving a setting into a template means removing it from the neighbours too.

The running configuration does not show inherited values, not even with `inheritance` (the same behaviour as OSPF in
M3). This command does, and tags each value with where it came from — `n:` a neighbor-group, `a:` an af-group,
`[]` the neighbour itself:

```console
RP/0/RP0/CPU0:XR01#show bgp neighbor 10.0.11.2 configuration
neighbor 10.0.11.2
 remote-as 65101              []
 description ISP-A            []
 address-family IPv4 Unicast  []
  maximum-prefix 1000 80      [n:ISP     a:ISP-AF]
  policy ISP-IN(200, 101) in  []
  policy ISP-OUT(1001, 0) out []
  send-community-ebgp         [n:ISP     a:ISP-AF]
```

`show bgp neighbor-group NAME configuration` and `show bgp af-group NAME configuration` show a template the same way.
Parameterised policies (M5) and templates work together: the template holds what every provider shares, and each
neighbour holds its policies with its own values.

## 6. Looking at paths, and command names

Path selection follows the steps you know (weight, local preference, locally originated, AS path length, origin, MED,
eBGP over iBGP, IGP metric to the next hop, and the tie-breakers). To see why a path won, ask for the comparison:

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 11.0.0.0/8 bestpath-compare
...
  Path #1: Received by speaker 0
    10.0.11.2 from 10.0.11.2 (101.101.101.101), if-handle 0x00000000
      Origin IGP, metric 0, localpref 200, valid, external, best, group-best
      best of AS 65101, Overall best
  Path #2: Received by speaker 0
    10.0.12.2 from 10.0.12.2 (102.102.102.102), if-handle 0x00000000
      Origin IGP, metric 0, localpref 100, valid, external, group-best
      best of AS 65102
      Lower local preference than best path (path #1)
```

Each losing path ends with the step at which it lost.

| On IOS | On IOS XR |
|---|---|
| `show ip bgp summary` | `show bgp ipv4 unicast summary` (or `show bgp summary`) |
| `show ip bgp` | `show bgp ipv4 unicast` |
| `show ip bgp neighbors X routes` | `show bgp ipv4 unicast neighbors X routes` |
| `show ip bgp neighbors X advertised-routes` | `show bgp ipv4 unicast neighbors X advertised-routes` |
| `show ip bgp neighbors X` | `show bgp neighbor X` |
| — | `show bgp neighbor X configuration` (with the source of each value) |
| `clear ip bgp X soft in` | `clear bgp ipv4 unicast X soft in` |
| `neighbor X route-map M in` | `route-policy P in` under the neighbour's address family |
| `neighbor X activate` | the address family under the neighbour |
| `neighbor X maximum-prefix 1000 80` | `maximum-prefix 1000 80` under the neighbour's address family |
| `neighbor X peer-group G` | `use neighbor-group G` |

## Practice

Go to lab **XRT-03** and do the M6 tasks, after the M5 tasks.

<p class="tolab"><a href="/_learn?id=XRT-03">Open lab XRT-03 in the workspace</a> — <a href="61-m6-practice.html">The tasks</a></p>

:::note
Source: the IOS XR *Routing Configuration Guide* for the ASR 9000, *Implementing BGP* and *Implementing Routing Policy*,
checked October 2026. The following come from measurement on IOS XRd 26.1.1: the `apply` trap in section 4, a prepend
count of 0, communities sent to iBGP without `send-community-ebgp`, and the running configuration not showing
inherited values.
:::
