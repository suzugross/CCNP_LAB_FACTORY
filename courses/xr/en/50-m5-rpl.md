# M5 — Routing Policy Language

On IOS you filter and change routes with prefix lists, AS-path access lists, community lists and route maps.
IOS XR replaces all of them with one language, the Routing Policy Language (RPL). You will meet it before you get
very far with BGP on IOS XR, because without a policy an eBGP neighbour exchanges nothing.

The outputs in this unit were captured on IOS XRd 26.1.1 (lab XRT-03). The same commands gave the same results on
IOS XRv 9000 26.1.1.

## 1. Why a policy is required

IOS XR follows RFC 8212: an eBGP neighbour with no inbound policy accepts no routes, and with no outbound policy
sends none. The session comes up as usual; only the routes are missing. The BGP summary says so, and marks the
neighbours with `!`:

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast summary
...
Some configured eBGP neighbors (under default or non-default vrfs)
do not have both inbound and outbound policies configured for IPv4 Unicast
address family. These neighbors will default to sending and/or
receiving no routes and are marked with '!' in the output below.
Use the 'show bgp neighbor <nbr_address>' command for details.

Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.0.11.2         0 65101       3       5            5    0    0 00:00:55          0!
10.0.12.2         0 65102       3       3            5    0    0 00:00:57          0!
```

The neighbour detail says which direction is missing, and counts what was refused:

```console
RP/0/RP0/CPU0:XR01#show bgp neighbor 10.0.11.2 | include "olic|denied|No policy|By policy"
  eBGP neighbor with no inbound or outbound policy; defaults to 'drop'
  Cumulative no. of prefixes denied: 5
    No policy: 5, Failed RT match: 0
    By ORF policy: 0, By policy: 0
```

"No policy" counts routes refused because there was no policy at all. "By policy" counts routes that a policy
dropped. Keep both counters in mind: they tell the two failures apart. iBGP neighbours are not affected.

## 2. Sets

A set is a named list that a policy can test a route against. It replaces the IOS lists.

| On IOS | On IOS XR |
|---|---|
| `ip prefix-list` | `prefix-set` |
| `ip as-path access-list` | `as-path-set` |
| `ip community-list` | `community-set` |
| `ip extcommunity-list` | `extcommunity-set` |

A set is written as a block, with the entries separated by commas and the block closed by `end-set`:

```console
prefix-set PRIVATE
  10.0.0.0/8 le 32,
  172.16.0.0/12 le 32,
  192.168.0.0/16 le 32
end-set
```

Differences from what you know:

- A prefix-set entry takes `ge` and `le` as a prefix list does, but there is no sequence number and no permit or deny.
  A set only says whether a route matches; what to do about it is the policy's business.
- Entering a set that already exists **replaces** it. The CLI warns: `Policy object prefix-set PS-24 exists!
  Reconfiguring it via CLI will replace current definition.` To add one entry you type the whole set again.
- An `as-path-set` entry is a regular expression written as `ios-regex '…'`. A `community-set` entry can contain
  wildcards (`65000:*`) and ranges.
- A set can also be written inline, inside a condition: `destination in (0.0.0.0/0, 0.0.0.0/0 ge 25)`.

## 3. How a policy decides

A policy is a small program between `route-policy NAME` and `end-policy`:

```console
route-policy RP-IN
  if destination in PS-24 then
    set community CS-TAG
    apply SET-LP(200)
  elseif destination in (172.16.2.0/25) and as-path in AS-ORIGIN then
    pass
  endif
end-policy
```

Conditions test the route: `destination in` (a prefix-set), `as-path in` (an as-path-set), `community matches-any`
or `matches-every` (a community-set), and helpers such as `as-path originates-from '65201'`, `as-path neighbor-is`
and `as-path length`. They combine with `and`, `or` and `not`, and branch with `if`, `elseif`, `else` and `endif`.

Actions decide the route's fate or change it:

| Action | Effect |
|---|---|
| `pass` | The route is accepted. The policy goes on running, so later statements can still change it |
| `drop` | The route is rejected. The policy stops |
| `done` | The route is accepted. The policy stops |
| `set …` | Changes an attribute. A route that has been changed is accepted |

And the rule that matters most:

**A route that reaches `end-policy` without being passed, done or changed by a `set` is dropped.**

So the policy above accepts the /24 prefixes it tags and the one /25 it passes. Everything else reaches the end
and is dropped, with no line saying so. The lab measured both halves of the rule:

- A policy with only `set local-preference 150` accepted every route, each with local preference 150.
- A policy with only `if destination in (11.0.0.0/8) then set local-preference 150 endif` accepted 11.0.0.0/8 and
  dropped everything else.

This is where IOS habits mislead. A route map also ends with an implicit deny, but a policy written as "drop what is
bad" — `if destination in PRIVATE then drop endif` — reads like a complete filter and accepts nothing at all. It needs
a `pass` after the `endif`.

## 4. Parameters and apply

A policy can take parameters. They are declared after the name, used with `$`, and given values where the policy is
attached:

```console
route-policy SET-LP($lp)
  set local-preference $lp
end-policy
```

One policy then serves several neighbours with different values, and a new neighbour needs no new definition. A
parameter can stand inside a value, for example in a community: `set community (65000:$tag) additive`.

`apply` runs another policy from inside a policy. It is how you reuse a filter instead of copying it. A route that the
applied policy drops stays dropped; a route that it passes continues in the calling policy.

`set community` replaces the communities a route carries. With `additive` it adds to them. `delete community in
<set>` removes the ones that match a set, and leaves the others.

## 5. Attach points and checking

A policy does nothing until it is attached. For BGP the usual places are under the neighbour's address family:

```console
router bgp 65000
 neighbor 10.0.11.2
  address-family ipv4 unicast
   route-policy ISP-IN(200, 101) in
   route-policy ISP-OUT out
```

Other attach points include redistribution (`redistribute … route-policy`), `network`, `aggregate-address`,
`default-originate`, and the same in OSPF and IS-IS. Not every attribute exists at every attach point. A policy that
sets a community cannot be attached to redistribution into OSPF; the commit fails with
`Policy [RP-IN] uses the 'community' attribute. There is no 'community' attribute at the ospf redistribution attach point.`

To see where a policy or a set is used:

```console
RP/0/RP0/CPU0:XR01#show rpl route-policy ISP-IN attachpoints
BGP Attachpoint: Neighbor
Neighbor/Group     type  afi/safi    in/out  vrf name   bound by
---------------------------------------------------------------------
10.0.11.2          --    IPv4/uni    in      default    ISP-IN(200, 101)
10.0.12.2          --    IPv4/uni    in      default    ISP-IN(100, 102)
```

`show rpl prefix-set NAME attachpoints` does the same for a set. `show rpl active route-policy` lists the policies
in use, including those used only through `apply`; `show rpl inactive route-policy` and `show rpl unused route-policy`
list the rest. `show rpl route-policy NAME detail` prints the policy together with every set and policy it uses.

To see what a policy did, look at the route:

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 11.0.0.0/8
...
  Path #1: Received by speaker 0
  65101
    10.0.11.2 from 10.0.11.2 (101.101.101.101)
      Origin IGP, metric 0, localpref 200, valid, external, best, group-best
      Community: 65000:101
  Path #2: Received by speaker 0
  65102 65101
    10.0.12.2 from 10.0.12.2 (102.102.102.102)
      Origin IGP, metric 0, localpref 100, valid, external, group-best
      Community: 65000:102
```

`show bgp ipv4 unicast neighbors <address> routes` lists the routes accepted from a neighbour, and `advertised-routes`
those sent to it. The routes as received, before the inbound policy, are kept only with `soft-reconfiguration inbound`
on that neighbour; without it, `received routes` answers that inbound soft reconfiguration is not active.

## 6. Changing a policy

A change to a policy or a set takes effect when you commit it. XR01 runs the routes it already holds through the new
policy; no `clear bgp` is needed. In the lab a prefix added to an attached prefix-set showed up in the BGP table
within seconds.

The commit checks the whole picture, and refuses what cannot work:

| You try to | The commit fails with |
|---|---|
| attach a policy that does not exist | `Policy [NOPE] must be defined before it can be attached.` |
| delete a policy that is attached | `Deletion of policy [PASS] is not allowed because it is in use at the bgp neighbor-out-dflt attach point.` |
| add a parameter to a policy that is attached without one | `Mismatch in number of parameters passed to policy at an attachpoint.` |

In each case the fix is to make both changes in the same commit: define and attach together, detach and delete
together, change the definition and the attachments together. `show configuration failed` shows the message after a
failed commit (M1).

## 7. From route maps to RPL

| On IOS | On IOS XR |
|---|---|
| `route-map NAME permit 10` + `match ip address prefix-list L` | `if destination in L then … endif` |
| sequence numbers, evaluated in order | `if` / `elseif` / `else`, written in order |
| `continue` | statements simply follow each other; `pass` does not stop the policy |
| implicit deny at the end | a route not passed or changed by the end is dropped |
| `set local-preference 200` in a permit clause | `set local-preference 200` (the change itself accepts the route) |
| one route map per set of values | one policy with parameters |
| `neighbor … route-map NAME in` | `route-policy NAME in` under the neighbour's address family |
| `neighbor … send-community` | `send-community-ebgp` (only eBGP is affected; iBGP sends communities by default) |
| no route map on an eBGP neighbour: everything passes | no policy on an eBGP neighbour: nothing passes |

## Practice

Go to lab **XRT-03** and do the M5 tasks.

<p class="tolab"><a href="/_learn?id=XRT-03">Open lab XRT-03 in the workspace</a> — <a href="51-m5-practice.html">The tasks</a></p>

:::note
Source: the IOS XR *Routing Configuration Guide* for the ASR 9000, *Implementing Routing Policy*, checked October 2026.
The following come from measurement on IOS XRd 26.1.1 and IOS XRv 9000 26.1.1: the wording of the summary and the
neighbour detail, a route changed by `set` being accepted without `pass`, a change taking effect without `clear bgp`,
and the commit messages in section 6.
:::
