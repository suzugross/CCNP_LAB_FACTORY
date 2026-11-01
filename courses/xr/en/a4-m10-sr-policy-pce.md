# M10 — SR policies and the PCE

This page covers how to send only some of the traffic along a path that is not the shortest, and how to compute that
path centrally. It is sections 3.3.c (traffic engineering with SR) and 3.3.e (the path computation element) of the
blueprint, and you use it in Tasks M10-4 and M10-5. Read section 2 of the previous page, How segment routing works (writing waypoints by stacking labels), first.

## 1. What it is good for

### 1.1 Same next hop, different paths

In Task M10-4, only customer A goes through RT03, and customer B stays as it is. The difficulty is that customer A's
route 10.101.2.0/24 and customer B's route 10.102.2.0/24 have the same next hop, RT02's loopback (10.255.0.12). XR01 has
only one path to that next hop (16012, to RT01), so changing "the path to RT02" moves both.

What you want is to choose, route by route, a different path to the same next hop. An **SR policy** is a way of
stacking labels (a path) with a name such as "to RT02 with color 100". Mark a route with color 100, and that route alone
uses the path. Routes without the mark keep the ordinary shortest path.

What this gives you:

- Only the head end, XR01, is configured. RT01, RT02, RT03 and the route reflector stay unchanged, and no tunnel is signalled.
- The choice of path is expressed as the intent of a service ("low delay", "avoid this link"). The color is a BGP extended
  community, so if the advertising side sets it, the receiving PE picks a path that fits the intent.
- You do not even have to write the policy in advance. When a route with a color arrives, the head end can build the
  path from a template (section 2.3).

### 1.2 What one router cannot see

A head end sees the topology of its own IGP area. It does not see the paths that other head ends have chosen, nor the
topology beyond its area. To place two paths from two PEs to the same destination so that they share no link, for
example, someone has to see both paths. That is the **path computation element** (PCE): it sees the whole network, computes the path and hands it to the head end (section 3).

## 2. SR policies

### 2.1 Color, end point, candidate paths

RFC 9256 identifies an SR policy by three things: the head end, a **color** (a number that stands for an intent) and the
**end point** (where the path ends). A policy has one or more **candidate paths**, each with a preference; of the valid
ones, the one with the highest preference is used. A candidate path is explicit (a list of labels written in the
configuration) or dynamic (computed by the head end or by a PCE from constraints). Each policy gets a **binding SID**: a packet that arrives with this label goes into the policy.

IOS XR keeps the policies under `segment-routing` → `traffic-eng`. An explicit path writes the order of the labels (or
of next hops) in a `segment-list`, and the policy refers to it. This policy writes the path of section 2.3 of the previous page as it is:

```console
RP/0/RP0/CPU0:XR01#show segment-routing traffic-eng policy color 100
Color: 100, End-point: 10.255.0.12
  Name: srte_c_100_ep_10.255.0.12
  Status:
    Admin: up  Operational: up for 00:00:12 (since Oct 29 23:30:50.259)
  Candidate-paths:
    Preference: 100 (configuration) (active)
      Name: CUST-A-VIA-RT03
      Explicit: segment-list VIA-RT03 (valid)
          SID[0]: 16013
          SID[1]: 16012
  Attributes:
    Binding SID: 24003
```

`SID[0]: 16013` (first to RT03) and `SID[1]: 16012` (then to RT02) are the stacked labels. The transit routers need
nothing special: RT01, RT02 and RT03 only forward on prefix SIDs, as they always do. The state of the policy lives on
the head end only.

The configuration of this policy:

:::config XR01 — a policy with a hand-written path
segment-routing
 traffic-eng
  segment-list VIA-RT03                   ## give the path (the order of the labels) a name
   index 10 mpls label 16013              ## first label: to RT03 first; RT03 is XR01's neighbour, so PHP means it is not actually pushed
   index 20 mpls label 16012              ## second label: then to RT02; the lower the index, the further out the label
  !
  policy CUST-A-VIA-RT03                  ## the policy's name (local to XR01)
   color 100 end-point ipv4 10.255.0.12   ## what identifies the policy: color and end point (the head end is XR01 itself)
   candidate-paths
    preference 100                        ## the candidate path's preference; the highest valid one is used
     explicit segment-list VIA-RT03       ## this candidate path is explicit: it uses the path above
    !
   !
  !
 !
!
:::

### 2.2 Steering by color

A policy carries no traffic until something is steered into it. The steering is done by **automated steering**, which
works where the next hop of a BGP route is resolved (RFC 9256). Follow XR01 as it puts a customer route into its forwarding table:

1. XR01 receives customer A's route 10.101.2.0/24. The next hop is 10.255.0.12.
2. Normally, XR01 looks up the IGP route to the next hop, puts 16012 on and sends the packet to RT01 (section 2.2 of the previous page).
3. If the route carries the BGP **color extended community** 100, and XR01 has a policy "color 100, end point
   10.255.0.12", XR01 looks up the policy instead of the IGP route. The packet gets the policy's labels (section 2.3 of
   the previous page).
4. Customer B's route has no color, so it stays with step 2.

Usually the egress PE sets the color when it advertises its routes. In the lab, RT02 sets no color and the route
reflector cannot be changed, so XR01 sets it as it receives the routes. The inbound route policy on the VPNv4 session
with XR02 matches customer A's route target and does `set extcommunity color` with an `extcommunity-set opaque` that holds 100.
The route then shows the color and the binding SID:

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A 10.101.2.0/24
...
    10.255.0.12 C:100 (bsid:24003) (metric 30) from 10.255.0.21 (10.255.0.12)
      Received Label 22
      Extended community: Color:100 RT:65000:101
      SR policy color 100, up, not-registered, bsid 24003
```

`C:100 (bsid:24003)` marks the route as tied to the policy. CEF resolves the route through the policy
(`next hop srte_c_100_ep_10.255.0.12 labels imposed {ImplNull 22}`): 22 is the VPN label, and the labels above it come
from the policy. Customer B keeps the shortest path. A traceroute from CEA1 crosses RT03 (10.0.3.13), one from CEB1 crosses RT01 (10.0.1.11)
(the traceroutes of sections 2.2 and 2.3 of the previous page).

Put together, the part that sets the color looks like this:

:::config fold XR01 — color 100 on customer A's routes as they arrive
extcommunity-set opaque COLOR-100      ## the color value; a color is a kind of extended community, and the number goes here
  100
end-set
!
extcommunity-set rt CUST-A-RT          ## customer A's route target (unit M9), for matching
  65000:101
end-set
!
route-policy FROM-RR
  if extcommunity rt matches-any CUST-A-RT then
    set extcommunity color COLOR-100   ## add color 100 to customer A's routes only
  endif
  pass                                 ## accept the remaining routes too: an IOS XR route policy drops a route that it neither passes nor modifies
end-policy
!
router bgp 65000
 neighbor 10.255.0.21                  ## the route reflector (XR02)
  address-family vpnv4 unicast
   route-policy FROM-RR in             ## apply it on the routes received
  !
 !
!
:::

:::note
The Segment Routing configuration guide (IOS XR 26.x, "Configure SR-TE Policies") lists the attach points of a route
policy where a color can be set, and gives the VRF import policy as one where it can only be matched. In the lab,
IOS XR 26.1.1 accepted `set extcommunity color` in a VRF import policy (`vrf CUST-B` → `address-family ipv4 unicast` →
`import route-policy`), put the color on the route and steered it into the policy (`SR policy color 100, up,
registered`). Lab XRT-10 accepts either place; the reference solution follows the guide and sets the color on the VPNv4 session.
:::

### 2.3 On-demand policies

Writing a policy for every pair of end point and color cannot keep up as PEs are added. **On-demand next hop**
(ODN) is a template for policies: when the first BGP route with a given color and a new next hop arrives, the head end
builds a policy from the template and computes its path. The configuration is `segment-routing` → `traffic-eng` →
`on-demand color 100` → `dynamic`, with a metric type and constraints.

To keep the path off a link, paint the link with an **affinity** and have that color excluded. An affinity is a named
bit. Name it with `affinity-map` → `name RT01-MAINT bit-position 0`, paint the link with the interface under
`traffic-eng` → `affinity` → the name, and exclude it with `affinity` → `exclude-any` → the name under the template's `dynamic`.

To compute a path, the SR-TE process must know the topology. IS-IS hands it over only with `distribute link-state` under
`router isis`; the guide says to configure it before any SR-TE policy. Without it, the on-demand policy stays down, and
the routes go back to the IGP path without any warning:

```console
    Preference: 200 (BGP ODN) (inactive)
      Name: bgp_c_100_ep_10.255.0.12_discr_200
      Dynamic (inactive)
      Last error: Source node not found in topology
```

With it, the policy comes up at once (`Dynamic (valid)`, `SID[0]: 16013 [Prefix-SID, 10.255.0.13]`,
`SID[1]: 16012 [Prefix-SID, 10.255.0.12]`). The shortest path to RT02 in the topology without PRIMARY is the same path
that section 2.1 wrote by hand. An on-demand policy on IOS XR 26.1.1 has two candidate paths: preference 200, computed by the head end,
and preference 100, handed to a PCE (section 3) if one is configured.

Put together, the parts of an on-demand policy look like this:

:::config fold XR01 — an on-demand policy that avoids PRIMARY
router isis CORE
 distribute link-state               ## hand the IS-IS topology to the SR-TE process (and to a PCE); without it the policy stays down
!
segment-routing
 traffic-eng
  affinity-map
   name RT01-MAINT bit-position 0    ## tie a name for a link color (affinity) to a bit position
  !
  interface GigabitEthernet0/0/0/0   ## PRIMARY
   affinity
    name RT01-MAINT                  ## paint this link
   !
  !
  on-demand color 100                ## the template: when a route with color 100 arrives with a new next hop, build a policy
   dynamic                           ## the head end (XR01) computes the path
    metric
     type igp                        ## what to minimise: the IGP metric
    !
    affinity
     exclude-any
      name RT01-MAINT                ## do not use links with this color
     !
    !
   !
  !
 !
!
:::

:::try
Take the topology away from SR-TE. Do it after Task M10-4 and before Task M10-5, then once more after Task M10-5.

1. On XR01, under `router isis CORE`, remove `distribute link-state` and commit.
2. On XR01, run `show segment-routing traffic-eng policy color 100 detail` and `show bgp vrf CUST-A 10.101.2.0/24`. On
   CEA1, run `traceroute 10.101.2.1 source Loopback10 numeric`.
3. Put the line back and commit, and run the same commands again.

What the lab measured: before Task M10-5, the policy went down with `Last error: Source node not found in topology`, the
BGP route lost its binding SID, and the traffic of customer A went back through RT01. After Task M10-5, the same step
changed nothing that the customer could see: the candidate path with preference 200 became inactive with the same
error, the one with preference 100, handed to XR02, took over (`Dynamic (pce 10.255.0.21) (valid)`), and CEA1's
traceroute still crossed RT03. The PCE knew the affinity of PRIMARY and avoided it too. With the line back, preference 200 was in use again within 15 seconds.
:::

## 3. A path computation element

### 3.1 PCE and PCC

A **path computation element** (PCE) is a server that takes on the computation of paths. A head end, as a **path
computation client** (PCC), asks it for paths over a protocol called PCEP. A stateful PCE remembers the paths it has
handed out, recomputes them when the topology changes, and sends the changes to the head end (RFC 8664 adds SR to PCEP).

On IOS XR, the PCE runs with `pce` → `address ipv4 <address>`. It learns the topology from its own IGP with
`distribute link-state`, or from BGP-LS for other areas. The guide recommends IOS XRv 9000 for an SR-PCE; the IOS XRd
data sheet places the control-plane form of XRd for roles that do little forwarding, route reflectors and PCEs. In the
lab, XR02 (XRd) is both.

The PCC is `segment-routing` → `traffic-eng` → `pcc` → `source-address ipv4` and `pce address ipv4`. With a candidate
path of `dynamic` → `pcep`, the computation is handed to the PCE: the PCE computes it and the head end installs it in its forwarding table.

```console
RP/0/RP0/CPU0:XR02#show pce ipv4 peer
Peer address: 10.255.0.1
  State: Up
  Capabilities: Stateful, Segment-Routing, Update, Instantiation, SRv6, SR-P2MP

RP/0/RP0/CPU0:XR02#show pce ipv4 topology summary
Nodes:
  Total:                       5
Prefix SIDs:
  Total:                       4
Adjacency SIDs:
  Total:                      13
```

The PCE needs about 40 seconds after it starts before it computes paths (`Topology Ready Summary: Ready: no` with a timer).

The configuration is split between the two sides:

:::config fold XR02 — the PCE
pce
 address ipv4 10.255.0.21   ## the address on which the PCE waits for PCEP connections (its loopback)
!
router isis CORE
 distribute link-state      ## hand the topology to the PCE (the same line as on XR01 in section 2.3)
!
:::

:::config fold XR01 — the PCC
segment-routing
 traffic-eng
  pcc
   source-address ipv4 10.255.0.1   ## the source of the PCEP session (its loopback)
   pce address ipv4 10.255.0.21     ## the PCE to ask for paths
  !
 !
!
:::

### 3.2 Paths that must not meet

Two policies that must share no link need someone who sees both. On the head end, the two candidate paths name the same
**disjointness group** (`constraints` → `disjoint-path group-id 1 type link`), and the PCE places them apart. In the lab,
the PCE put color 201 on the shortest path through RT01 (16012, metric 20) and color 202 through RT03 (16013 then 16012,
metric 200):

```console
RP/0/RP0/CPU0:XR02#show pce association
Association: Type Link-Disjoint, Group 1, Not Strict
 Associated LSPs:
  LSP[0]:
   PCC 10.255.0.1, tunnel name cfg_DISJ-2_discr_100,  PLSP ID 3, tunnel ID 4, LSP ID 2, Configured on PCC
  LSP[1]:
   PCC 10.255.0.1, tunnel name cfg_DISJ-1_discr_100,  PLSP ID 2, tunnel ID 3, LSP ID 2, Configured on PCC
 Status: Satisfied
```

`Status: Satisfied` means that a pair meeting the condition could be placed. "Not Strict" means the PCE may fall back to
paths that are not disjoint when no disjoint pair exists; a strict group would rather leave a policy down.

The configuration of the two policies:

:::config fold XR01 — two policies computed by the PCE
segment-routing
 traffic-eng
  policy DISJ-1
   color 201 end-point ipv4 10.255.0.12
   candidate-paths
    preference 100
     dynamic
      pcep                                 ## hand the path computation to the PCE
      !
      metric
       type igp
      !
     !
     constraints
      disjoint-path group-id 1 type link   ## share no link with the other policies of group 1
     !
    !
   !
  !
  policy DISJ-2                            ## the second one: only the color differs
   color 202 end-point ipv4 10.255.0.12
   candidate-paths
    preference 100
     dynamic
      pcep
      !
      metric
       type igp
      !
     !
     constraints
      disjoint-path group-id 1 type link
     !
    !
   !
  !
 !
!
:::

:::try
Take away the constraint. Do it after Task M10-5.

1. On XR01, remove `constraints` from both DISJ-1 and DISJ-2, and commit.
2. On XR01, run `show segment-routing traffic-eng policy color 201 detail` and `… color 202 detail`. On XR02, run
   `show pce association` and `show pce lsp detail`.
3. Put the constraints back and commit.

What the lab measured: both policies moved to the shortest path through RT01 (`SID[0]: 16012`, metric 20).
`show pce association` no longer listed the group, and `show pce lsp detail` showed both paths as `LSP Role: Single LSP`.
With the constraints back, color 202 moved to RT03 again (16013, 16012, metric 200) within 30 seconds.
:::

## 4. Command names

| Purpose | On IOS XR |
|---|---|
| Policies, explicit paths | `segment-routing` → `traffic-eng` → `policy`, `segment-list` |
| Setting a color | `set extcommunity color` in a route policy (`extcommunity-set opaque`) |
| On-demand policies | `segment-routing` → `traffic-eng` → `on-demand color <color>` |
| Handing the topology to SR-TE and the PCE | `router isis` → `distribute link-state` |
| PCE, PCC | `pce` → `address ipv4`, `segment-routing` → `traffic-eng` → `pcc` |
| Checking | `show segment-routing traffic-eng policy color <color> detail`, `show pce ipv4 peer`, `show pce association` |

## Practice

In lab **XRT-10**, do Tasks M10-4 and M10-5. The flexible algorithm and SRv6 are in the appendix.

<p class="tolab"><a href="/_learn?id=XRT-10&amp;step=m10t4">Open Task M10-4 in the workspace</a> — <a href="a5-m10-practice-3.html">The tasks</a></p>

:::note
Sources: the Segment Routing Configuration Guide for the ASR 9000, IOS XR 26.1.x–26.3.x (2026: SR-TE policies, ODN,
automated steering, affinity, SR-PCE) and its command reference (2025); the IOS XRd data sheet (2026); RFC 8664 and 9256.
All checked October 2026. The on-demand policy without `distribute link-state`, the color set in a VRF import policy and
the PCE on XRd come from measurement in lab XRT-10 and its PoC.
:::
