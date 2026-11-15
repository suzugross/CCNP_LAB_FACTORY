# J1 — Applying policy to BGP

## 1. Why policy is central to BGP

### 1.1 The problem: accepting too much, sending too little

By the previous page JUN02 can choose the routes it takes from the ISP. What is left is the other direction. Unless the ISP hears about
the inside networks, there is no way back from the ISP to the inside. And the fewer routes you send, the better: towards the ISP you want
to send just one route that covers the inside.

### 1.2 What came before

In IOS you put routes into the BGP table with `network` statements or `redistribute`, summarise with `aggregate-address`, and narrow
down with `neighbor … route-map … out`. In IOS XR, as M6 of the IOS XR track showed, nothing is sent to an eBGP neighbour that has no
policy; routes go out only once a `route-policy … out` is attached.

### 1.3 The Junos answer

Junos BGP has no `network` statement. What to advertise is chosen from the routing table by an **export policy**, written the same way
as an export into OSPF. A summary route is created in the routing table with `routing-options aggregate`, then chosen and sent out by
an export policy.

## 2. How it works

### 2.1 The minimal BGP configuration

JUN02 in JNT-02 starts with the following BGP configuration. The BGP unit comes later, so here we only take in what each line means.

:::config JUN02 — the eBGP session with the ISP (configured from the start)
set routing-options autonomous-system 65000        ## Your own AS number. Written outside BGP, under routing-options
set protocols bgp group ISP type external          ## Neighbours are put into groups. The neighbours in this group are eBGP
set protocols bgp group ISP peer-as 64500          ## The neighbour's AS number (applies to everyone in the group)
set protocols bgp group ISP neighbor 10.0.23.2     ## The neighbour's address, listed under the group
:::

It is IOS's `router bgp 65000` and `neighbor 10.0.23.2 remote-as 64500`, split into the AS number, a group and a neighbour.
As with OSPF, commit and `show bgp summary` print a `requires 'BGP' license` notice, and BGP works all the same (appendix).

### 2.2 BGP's default policies

Without any policy, JUN02 accepts every route from the ISP and advertises nothing (the output in section 2.1 of the overview page).
There are two reasons.

- **The default import accepts every route received.** `Default eBGP mode: advertise - accept, receive - accept` in `show bgp summary`
  shows it. Juniper does not turn on the behaviour of RFC 8212 (no route exchange with an eBGP neighbour that has no policy) by default,
  so as not to break existing configurations. To turn it on, choose it under `set protocols bgp defaults ebgp no-policy`.
- **The default export advertises only active BGP routes.** All of JUN02's BGP routes came from the ISP. Junos does not advertise a route
  learned from an eBGP neighbour to an eBGP neighbour in that same AS, so there is nothing to send. OSPF routes, direct networks and
  aggregate routes are not BGP routes, so they do not go out unless an export policy chooses them.

### 2.3 Routes rejected by import stay as hidden

A route that an import policy rejects is not thrown away; it stays in the routing table as **hidden**. It is not used, but you can still
see what arrived and why it is not used.

```console
admin@jun02> show bgp summary
Threading mode: BGP I/O
Default eBGP mode: advertise - accept, receive - accept
Groups: 1 Peers: 1 Down peers: 0
Table          Tot Paths  Act Paths Suppressed    History Damp State    Pending
inet.0
                      10          4          0          0          0          0
Peer                     AS      InPkt     OutPkt    OutQ   Flaps Last Up/Dwn State|#Active/Received/Accepted/Damped...
10.0.23.2             64500         47         47       0       0       20:12 Establ
  inet.0: 4/10/4/0

admin@jun02> show route 198.51.100.128/25 hidden extensive | match reason
                Hidden reason: Rejected by import policy
```

`4/10/4/0` means ten received, four accepted and in use. The six rejected ones are listed by
`show route receive-protocol bgp 10.0.23.2 hidden`.

### 2.4 The levels to write policy at: global, group, neighbor

In BGP you can write import and export at three levels: directly under `protocols bgp` (every neighbour), under a `group` (that group's
neighbours) and under a `neighbor` (that neighbour only). Juniper's documentation says that "a peer-level import or export statement
overrides a group import or export statement", and a group-level one overrides the global one. **They do not add up.**

With import `FILTER-IN` and export `SERVERS-OUT` on group ISP, adding `import TAG-198` under the neighbour left only TAG-198 on that
neighbour. FILTER-IN was gone, so all ten routes from the ISP were accepted. Only the direction you write is replaced: the export stayed
as the group's.

```console
admin@jun02> show bgp neighbor 10.0.23.2 | match "Import|Export"
  Export: [ SERVERS-OUT ] Import: [ TAG-198 ]

admin@jun02> show bgp summary
...
10.0.23.2             64500         50         50       0       0       21:07 Establ
  inet.0: 10/10/10/0
```

The `Import:` and `Export:` lines of `show bgp neighbor neighbour` show the policies actually in effect for that neighbour, in the order
of evaluation.

### 2.5 Changing attributes: local preference, community, AS path, MED

BGP attributes are rewritten in a policy's `then`. None of these actions ends the evaluation.

| Action | What it rewrites | Where to use it |
|---|---|---|
| `local-preference 150` | LOCAL_PREF (higher is preferred; used only inside the AS) | On import, to set how much a received route is preferred |
| `community add name` | Adds a community (`set` replaces, `delete` removes) | To mark routes and choose them in a later policy |
| `as-path-prepend "65000 65000"` | Adds AS numbers to the front of the AS path | On export, to make your path look longer to the neighbour |
| `metric 50` | In BGP, the MED | On export, to tell the neighbouring AS which way in you prefer |

A community is named under `policy-options` before use (`set policy-options community CUST members 65000:200`). You can see the result
of a rewrite in `show route … detail`. The number after `Preference: 170/` is derived from the local preference: it reads `-101` for a
local preference of 100, `-151` for 150 and `-201` for 200.

```console
admin@jun02> show route 198.51.100.0/24 exact detail table inet.0

inet.0: 19 destinations, 19 routes (13 active, 0 holddown, 6 hidden)
198.51.100.0/24 (1 entry, 1 announced)
        *BGP    Preference: 170/-151
                Next hop: 10.0.23.2 via et-0/0/1.0, selected
                State: <Active Ext>
                Local AS: 65000 Peer AS: 64500
                Age: 7 	Metric: 0
                AS path: 64500 I
                Communities: 65000:200
                Accepted
                Localpref: 150
```

(Lines not used here are left out of the output.)

### 2.6 Sending an aggregate route

A summary route is created in the routing table with `routing-options aggregate route 172.16.0.0/16`. The aggregate route is used only
while at least one **contributing route** exists within its range.

```console
admin@jun02> show route 172.16.0.0/16 exact detail

inet.0: 20 destinations, 20 routes (14 active, 0 holddown, 6 hidden)
172.16.0.0/16 (1 entry, 1 announced)
        *Aggregate Preference: 130
                Next hop type: Reject, Next hop index: 0
                State: <Active Int Ext>
                Local AS: 65000
                AS path: I  (LocalAgg)
                Contributing Routes (2):
                	172.16.10.0/24 proto OSPF
                	172.16.20.0/24 proto OSPF
```

(Lines not used here are left out of the output.)

- The preference is 130.
- The next hop is `Reject`. Packets to destinations within the aggregate that have no more specific route are dropped here. It is the
  counterpart of the route to Null0 that IOS's `aggregate-address` creates.
- When no contributing route is left, the aggregate route becomes hidden (`State: <Hidden Int Ext>`). That is what happened when the
  export into OSPF on JUN01 was removed.

An aggregate route is not a BGP route either, so it does not go out until an export policy chooses `from protocol aggregate`. Once sent,
its AS path is shown like `65000 65000 [65000] I`. The bracketed number is your own AS, which goes to the front when the route is sent to
an eBGP neighbour. On the ISP's FRR1 it shows as `65000 65000 65000`, and the router that aggregated it as
`aggregated by 65000 192.168.0.2`.

## 3. Configuration examples

### 3.1 Sending the inside networks to the ISP as /24s, with a MED

JUN02 sends the inside /24s that it learned through OSPF to the ISP, with a MED of 50 (no aggregation).

:::config JUN02 — the inside networks learned through OSPF, to the ISP
set policy-options policy-statement SERVERS-OUT term SERVERS from protocol ospf                   ## Routes whose source is OSPF
set policy-options policy-statement SERVERS-OUT term SERVERS from route-filter 172.16.0.0/16 longer ## The finer routes within 172.16.0.0/16
set policy-options policy-statement SERVERS-OUT term SERVERS then metric 50                       ## In BGP, the MED
set policy-options policy-statement SERVERS-OUT term SERVERS then accept                          ## 
set policy-options policy-statement SERVERS-OUT term REST then reject                             ## Send nothing else (do not leave it to BGP's default export)
set protocols bgp group ISP export SERVERS-OUT                                                    ## Apply at the way out of the ISP group
:::

Without `REST`, BGP routes learned from anywhere other than this ISP (there are none in this topology, but there would be from another
ISP or over IBGP) would go out under BGP's default export. It is safer to close a way-out policy with a term that rejects.

Result (at this point JUN01 was sending only 172.16.20.0/24 into OSPF):

```console
admin@jun02> show route advertising-protocol bgp 10.0.23.2

inet.0: 19 destinations, 19 routes (13 active, 0 holddown, 6 hidden)
  Prefix                  Nexthop              MED     Lclpref    AS path
* 172.16.20.0/24          Self                 50                 I
```

```console
frr1# show bgp ipv4 unicast 172.16.20.0/24
BGP routing table entry for 172.16.20.0/24, version 12
Paths: (1 available, best #1, table default)
  Advertised to peers:
  10.0.23.1
  65000
    10.0.23.1 from 10.0.23.1 (192.168.0.2)
      Origin IGP, metric 50, valid, external, best (First path received)
```

### 3.2 Marking received routes: inserting a term into a policy

In section 2.2 of the overview page, the policy that marks routes was put in front in the chain. You can do the same by inserting a term
into one policy. Into JUN02's FILTER-IN, add a term that gives 192.0.2.0/24 a local preference of 120 and community 65000:200, in front of
the term that accepts.

:::config JUN02 — mark one route inside FILTER-IN
set policy-options community CUST members 65000:200                                    ## Name the community to add
set policy-options policy-statement FILTER-IN term MARK from route-filter 192.0.2.0/24 exact ## Only 192.0.2.0/24 itself
set policy-options policy-statement FILTER-IN term MARK then local-preference 120      ## Only change attributes. No accept
set policy-options policy-statement FILTER-IN term MARK then community add CUST        ## 
insert policy-options policy-statement FILTER-IN term MARK before term LEN             ## In front of the accepting term (LEN). Left at the end, it is never reached
:::

```console
admin@jun02> show route community 65000:200 detail | match "^[0-9]|Localpref|Communities"
192.0.2.0/24 (1 entry, 1 announced)
                Communities: 65000:200
                Localpref: 120
```

### 3.3 From IOS and IOS XR to Junos

| In IOS | In IOS XR | In Junos |
|---|---|---|
| `router bgp 65000` | `router bgp 65000` | `set routing-options autonomous-system 65000` |
| `neighbor 10.0.23.2 remote-as 64500` | `neighbor 10.0.23.2 remote-as 64500` | `group ISP type external`, `peer-as 64500`, `neighbor 10.0.23.2` |
| Put routes into the BGP table with `network` or `redistribute` | The same | An export policy chooses from the routing table |
| `aggregate-address 172.16.0.0 255.255.0.0 summary-only` | `aggregate-address 172.16.0.0/16 summary-only` | `routing-options aggregate route 172.16.0.0/16` and an export policy |
| `neighbor … route-map name in`, `out` | `route-policy name in`, `out` | `import name`, `export name` (global, group, neighbor) |
| No policy on eBGP: everything passes | No policy on eBGP: nothing passes | No policy: accept everything, advertise only BGP routes |
| `set local-preference 150` | `set local-preference 150` | `then local-preference 150` |
| `set as-path prepend 65000 65000` | `prepend as-path 65000 2` | `then as-path-prepend "65000 65000"` |
| `set community 65000:200 additive` | `set community … additive` | `then community add name` |

## Practice

Move to lab **JNT-02** and work on tasks J1-4 and J1-5.

<p class="tolab"><a href="/_learn?id=JNT-02">Open lab JNT-02 in the workspace</a> — <a href="16-j1-practice-3.html">Tasks</a></p>

:::note
Sources: Juniper Networks, *BGP User Guide* (2026-07-09), the exception noted for RFC 8212 and "Implicit filter for Default EBGP Route
Propagation Behavior without Policies", and the rule that a route is not advertised back to an eBGP neighbour in the same AS
(advertise-peer-as). *Routing Policies, Firewall Filters, and Traffic Policers User Guide* (2026-06-23), "Example: Applying Routing
Policies at Different Levels of the BGP Hierarchy" (peer overrides group, group overrides global) and the table of actions that change
attributes. IOS XR behaviour is from M5 and M6 of the IOS XR track. The output was captured on vJunos-Evolved (Junos OS Evolved
26.2R1.7) and FRRouting 10.7.1 in containerlab.
:::
