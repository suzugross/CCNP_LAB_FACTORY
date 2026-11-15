# J1 — Appendix

## 1. The order of evaluation at a glance

The order in which one route goes through import and export policies.

1. The listed policies (the chain), one at a time from the left.
2. Within a policy, the terms one at a time from the top. A `then` outside any term is an unnamed last term.
3. A term's `from` matches when conditions of different kinds all match (AND) and, for values of one kind, one of them matches (OR).
   Route filters, prefix lists and prefix-list filters together form one list, and the match type of the one longest match decides.
4. Run the `then` of the term that matched.
   - `accept`, `reject`: evaluation ends here.
   - `next policy`: skip the remaining terms and go to the next policy.
   - Attribute changes only, or `next term`: go to the next term.
5. If no policy decides, the protocol's default policy does. BGP import accepts; OSPF export rejects.

## 2. Match types at a glance

| Match type | What it matches | As an IOS prefix list |
|---|---|---|
| `P/n exact` | P/n itself | `P/n` |
| `P/n orlonger` | P/n and everything within it | `P/n le 32` |
| `P/n longer` | Everything within it (not P/n itself) | `P/n ge n+1` |
| `P/n upto /m` | From P/n up to length m | `P/n le m` |
| `P/n prefix-length-range /a-/b` | Within it, lengths a to b | `P/n ge a le b` |
| `P/n through Q/m` | Prefixes on the path from P/n down to Q/m | — |
| `prefix-list name` | The prefixes in the list themselves | — |
| `prefix-list-filter name type` | The prefixes in the list, with a match type | — |

## 3. The quirks of this virtual router

### 3.1 The default BGP policy for PTX differs from the documentation

Juniper's BGP User Guide says that the default BGP policy on PTX routers differs from that of other Junos routers. A PTX holds only a
relatively small number of prefixes in its forwarding table, so by default it does not install BGP routes there. A default policy
`junos-ptx-series-default` puts `no-install-to-fib` on BGP routes (inet.0 and inet6.0) and is applied with
`routing-options forwarding-table default-export`. For the routes you do want installed, you add `install-to-fib` in an export policy of
your own.

The router in this lab (vJunos-Evolved, Junos OS Evolved 26.2R1.7, `Model: ptx10001-36mr`) applies a policy of the same name in the same
place, but its contents differ.

```console
admin@jun02> show policy junos-ptx-series-default
Policy junos-ptx-series-default: [CHANGED/RESOLVED]
    Term t1:
        then
               load-balance per-flow
```

There is no `no-install-to-fib` term. BGP routes go into the forwarding table (they are listed as `user` in `show route forwarding-table`),
and JUN02 forwards on BGP routes. So in the labs of this track, as on other Junos routers, a BGP route in use is used for forwarding as it is.

Whether the documentation still describes older PTX routers (Junos OS), or Junos OS Evolved or this virtual router behaves differently,
cannot be told from the documentation. When you work with a real PTX, look at `show policy junos-ptx-series-default` on that device.

### 3.2 The BGP license notice

As with OSPF, configuring BGP prints `warning: requires 'BGP' license` at commit and in `show bgp …`. BGP works. Treat it as the J0
appendix describes for OSPF.

## 4. Commands for checking, at a glance

| What you want to know | Command |
|---|---|
| The policy as written | `show policy-options policy-statement name` (configuration), `show policy name` (as loaded) |
| The policies applied (BGP) | `show bgp neighbor neighbour \| match "Import\|Export"` |
| The policies applied (OSPF) | The `export` line in `show configuration protocols ospf` |
| Routes received by BGP and in use | `show route receive-protocol bgp neighbour` |
| Routes received by BGP but not in use | `show route receive-protocol bgp neighbour hidden`, and `Hidden reason:` in `show route prefix hidden extensive` |
| Counts | `active/received/accepted/damped` under the peer in `show bgp summary` |
| Routes advertised by BGP | `show route advertising-protocol bgp neighbour` |
| External routes sent into OSPF | `show ospf database external extensive` on the neighbour (`Type:`, `Metric:`) |
| Attributes | `show route prefix exact detail` (`Localpref:`, `Communities:`, `AS path:`) |
| Choosing by community | `show route community 65000:200` |
| An aggregate and its contributing routes | `Contributing Routes` in `show route prefix exact detail` |
| Trying before applying | `test policy name prefix` (counts the default as accept; does not evaluate hidden routes) |

## 5. Where to look things up

- *Routing Policies, Firewall Filters, and Traffic Policers User Guide*: policy structure, conditions, actions, chains, route filters,
  the table of default policies, `test policy`. Most of this unit is here.
- *BGP User Guide*: configuring BGP, the levels to write policy at, how RFC 8212 is handled, the default BGP policy on PTX.
- *OSPF User Guide*: OSPF import and export, the external metric types.
- On the device: `help apropos word` (searches the configuration statements for a word) and `?`.

:::note
Sources: Juniper Networks, *BGP User Guide* (2026-07-09), "Understanding the Default BGP Routing Policy on Packet Transport Routers
(PTX Series)" and "Example: Overriding the Default BGP Routing Policy on PTX Series Packet Transport Routers". This text is the same as
Juniper's older documentation page (an example for Junos OS Release 12.1 or later). *Routing Policies, Firewall Filters, and Traffic
Policers User Guide* (2026-06-23), the table of match types and the section on evaluation. The output was captured on vJunos-Evolved
(Junos OS Evolved 26.2R1.7) in containerlab.
:::
