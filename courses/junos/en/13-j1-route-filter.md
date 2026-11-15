# J1 — route-filter: choosing by prefix and length

## 1. Why route-filter

### 1.1 The problem: choosing by range and by length at once

When you choose routes from an ISP, there are usually two conditions together: "which range is it in" (within the private 10.0.0.0/8?)
and "how long is it" (a fine-grained route longer than /24?). Range alone is not enough, and neither is length alone.

### 1.2 What came before

An IOS prefix list writes a length range with `ge` and `le` after the prefix. `ip prefix-list P permit 10.0.0.0/8 le 32` is
"10.0.0.0/8 and everything within it", and `permit 0.0.0.0/0 ge 25` is "everything of length 25 or more". Lines are checked from the
top, the first match decides, and a route that matches no line hits the implicit deny. An IOS XR prefix-set uses the same idea, with
`ge`, `le` or `eq`.

### 1.3 The Junos answer

A Junos **route-filter** is a pair of a prefix and a **match type**. `10.0.0.0/8 orlonger` is "10.0.0.0/8 and everything within it",
and `0.0.0.0/0 prefix-length-range /25-/32` is "everything of length 25 to 32". A route filter is one of the conditions you write in a
term's `from`, so you can combine it with other conditions (the source, the neighbour and so on).

## 2. How it works

### 2.1 The shape of a route-filter

```
from {
    route-filter prefix/length match-type;
    route-filter prefix/length match-type action;     ← each route filter can carry its own action (section 2.4)
}
```

A route is first compared by the range of the prefix, then by length according to the match type.

### 2.2 Match types

These are the results of trying each match type on the ten routes that the ISP sends to JUN02 (0.0.0.0/0, 10.200.0.0/16,
100.64.0.0/10, 172.31.0.0/16, 192.0.2.0/24, 192.168.50.0/24, 198.18.0.0/15, 198.51.100.0/24, 198.51.100.128/25 and 203.0.113.0/24).

| Match type | Meaning | Route filter tried | ISP routes that matched | As an IOS prefix list |
|---|---|---|---|---|
| `exact` | The prefix itself | `198.51.100.0/24 exact` | 198.51.100.0/24 | `198.51.100.0/24` |
| `orlonger` | It, and anything longer within it | `198.51.100.0/24 orlonger` | 198.51.100.0/24, 198.51.100.128/25 | `198.51.100.0/24 le 32` |
| `longer` | Only the longer ones within it (not itself) | `198.51.100.0/24 longer` | 198.51.100.128/25 | `198.51.100.0/24 ge 25` |
| `upto /n` | From it up to length n | `0.0.0.0/0 upto /16` | 0.0.0.0/0, 10.200.0.0/16, 100.64.0.0/10, 172.31.0.0/16, 198.18.0.0/15 | `0.0.0.0/0 le 16` |
| `prefix-length-range /a-/b` | Within it, lengths a to b | `0.0.0.0/0 prefix-length-range /16-/24` | 10.200.0.0/16, 172.31.0.0/16, 192.0.2.0/24, 192.168.50.0/24, 198.51.100.0/24, 203.0.113.0/24 | `0.0.0.0/0 ge 16 le 24` |
| `through prefix` | Prefixes on the path from it down to the longer prefix given | `198.51.100.0/24 through 198.51.100.128/25` | 198.51.100.0/24, 198.51.100.128/25 | (no equivalent) |

The range of `prefix-length-range` does not include /0. To keep the default route as well, write `0.0.0.0/0 exact` separately.

### 2.3 Several route filters in one term: the longest match decides

When a term's `from` has several route filters, it reads as if the term matches when any one of them matches (OR). But the first
thing Junos does is a **longest match**. It picks the one route filter whose prefix covers the route's prefix most specifically, and
looks only at that one's match type. If the type does not fit, the term does not match, even if another route filter would. Juniper's
documentation puts it as "the route filter stops evaluating other prefixes, even if the match type fails".

Try 198.51.100.128/25 from the ISP against this term.

```
term t {
    from {
        route-filter 198.51.100.0/24 exact;
        route-filter 0.0.0.0/0 upto /25;
    }
    then accept;
}
then reject;
```

```console
admin@jun02> test policy LM 198.51.100.0/24

inet.0: 19 destinations, 19 routes (19 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

198.51.100.0/24    *[BGP/170] 00:04:21, MED 0, localpref 100
                      AS path: 64500 I, validation-state: unverified
                    >  to 10.0.23.2 via et-0/0/1.0

Policy LM: 1 prefix accepted, 1 prefix rejected
```

198.51.100.128/25 fits within `0.0.0.0/0 upto /25`, and still it was rejected. The route filter that covers 198.51.100.128/25 most
specifically is `198.51.100.0/24`, and its type is `exact`. Other routes (192.0.2.0/24 and the like) fall only within the one
`0.0.0.0/0`, so `upto /25` accepts them.

To make Junos go back to the shorter route filters when the type does not fit, configure `set policy-options defaults route-filter walkup`.
With it, the same test accepted 198.51.100.128/25 as well. walkup changes the behaviour of the whole router, so the results of existing
policies can change too. This unit does not use it; instead it splits overlapping route filters into separate terms.

### 2.4 An action per route filter

When you write an action at the end of a route-filter line, a route that matches that route filter gets that action instead of the term's
`then`.

```
term t {
    from {
        route-filter 198.51.100.0/24 exact accept;      ← accept the /24 itself
        route-filter 198.51.100.0/24 longer reject;     ← reject the finer routes within it
        route-filter 192.0.2.0/24 exact;                ← a line with no action follows the term's then
    }
    then {
        local-preference 300;
        accept;
    }
}
```

With this, 198.51.100.0/24 was accepted and 198.51.100.128/25 was rejected. When the same prefix appears on two lines, the types are
checked from the top, and the first line whose type fits gives the action.

### 2.5 prefix-list and prefix-list-filter

A **prefix list** is a named list of prefixes. You create it under `policy-options` and can name it from many policies.

```
set policy-options prefix-list PL 198.51.100.0/24
```

`from prefix-list PL` matches only the prefixes in the list **themselves** (exact). You cannot write a length range. When you want
one, name the list with a match type, as in `from prefix-list-filter PL orlonger`.

| Written as | ISP routes that matched |
|---|---|
| `from prefix-list PL` | 198.51.100.0/24 |
| `from prefix-list-filter PL orlonger` | 198.51.100.0/24, 198.51.100.128/25 |

Its role differs from an IOS prefix list. In IOS the prefix list itself carries permit or deny and `ge` or `le`; a Junos prefix list is
just a list, and the policy's `then` decides whether to allow or reject.

### 2.6 Side by side with IOS and IOS XR

| What you want | IOS prefix list | IOS XR prefix-set | Junos route-filter |
|---|---|---|---|
| 10.0.0.0/8 and everything within it | `10.0.0.0/8 le 32` | `10.0.0.0/8 le 32` | `10.0.0.0/8 orlonger` |
| Everything of length /25 or more | `0.0.0.0/0 ge 25` | `0.0.0.0/0 ge 25` | `0.0.0.0/0 prefix-length-range /25-/32` |
| Everything of length /8 to /24 | `0.0.0.0/0 ge 8 le 24` | `0.0.0.0/0 ge 8 le 24` | `0.0.0.0/0 prefix-length-range /8-/24` |
| The default route only | `0.0.0.0/0` | `0.0.0.0/0` | `0.0.0.0/0 exact` |
| Order of evaluation | Line order (first line that matches) | A set (tested with `if destination in`) | The one longest match (walkup changes it) |
| No match | Implicit deny | The `if` is false | The term does not match → next term |

## 3. Configuration example

### 3.1 Accept only the ISP's own network and the default route

Of the routes that JUN02 receives from the ISP, accept only the ISP's own network (203.0.113.0/24 and within it up to /25) and the
default route.

:::config JUN02 — choose the routes accepted from the ISP by range and length
set policy-options policy-statement ISP-OWN term OWN from route-filter 203.0.113.0/24 upto /25 ## 203.0.113.0/24 down to /25
set policy-options policy-statement ISP-OWN term OWN then accept                            ## 
set policy-options policy-statement ISP-OWN term DEFAULT from route-filter 0.0.0.0/0 exact  ## The default route itself
set policy-options policy-statement ISP-OWN term DEFAULT then accept                        ## 
set policy-options policy-statement ISP-OWN term REST then reject                           ## Reject the rest. Without it, BGP's default (accept)
set protocols bgp group ISP import ISP-OWN                                                  ## Apply at the way in of the ISP group
:::

A `0.0.0.0/0` route filter covers the prefix of every route. Written in the same term as other route filters, it needs care because of
the longest match in section 2.3. Here the terms are kept separate.

Result:

```console
admin@jun02> show route receive-protocol bgp 10.0.23.2 table inet.0

inet.0: 19 destinations, 19 routes (11 active, 0 holddown, 8 hidden)
  Prefix                  Nexthop              MED     Lclpref    AS path
* 0.0.0.0/0               10.0.23.2            0                  64500 I
* 203.0.113.0/24          10.0.23.2            0                  64500 I

admin@jun02> show route receive-protocol bgp 10.0.23.2 hidden table inet.0

inet.0: 19 destinations, 19 routes (11 active, 0 holddown, 8 hidden)
  Prefix                  Nexthop              MED     Lclpref    AS path
  10.200.0.0/16           10.0.23.2            0                  64500 I
  100.64.0.0/10           10.0.23.2            0                  64500 I
  172.31.0.0/16           10.0.23.2            0                  64500 I
  192.0.2.0/24            10.0.23.2            0                  64500 I
  192.168.50.0/24         10.0.23.2            0                  64500 I
  198.18.0.0/15           10.0.23.2            0                  64500 I
  198.51.100.0/24         10.0.23.2            0                  64500 I
  198.51.100.128/25       10.0.23.2            0                  64500 I
```

Routes that are not accepted do not vanish; they stay as hidden. Why one is not used shows in the `Hidden reason:` line of
`show route 10.200.0.0/16 hidden extensive` (section 2.3 of the next page).

## Practice

Move to lab **JNT-02** and work on task J1-3.

<p class="tolab"><a href="/_learn?id=JNT-02">Open lab JNT-02 in the workspace</a> — <a href="14-j1-practice-2.html">Tasks</a></p>

:::note
Sources: Juniper Networks, *Routing Policies, Firewall Filters, and Traffic Policers User Guide* (2026-06-23), the section on route
filter match types, "How Route Filters Are Evaluated in Routing Policy Match Conditions" (the longest match; evaluation stops even if
the match type fails; the note on walkup; the same prefix is scanned from the top), and the sections on prefix lists and prefix-list
filters. The IOS XR prefix-set is from M5 of the IOS XR track. The output was captured on vJunos-Evolved (Junos OS Evolved 26.2R1.7)
in containerlab.
:::
