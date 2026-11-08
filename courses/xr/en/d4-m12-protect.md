# M12 — Protecting the data plane

The previous two pages treated good packets differently. This page drops the packets that should not arrive at all:
packets with a forged source, packets aimed at the provider's infrastructure, and packets to a destination under
attack. It covers 1.7 of the blueprint (implementing data-plane security: uRPF, ACLs, RTBH, MACsec), and touches on
BGP FlowSpec (1.5.f) and DDoS (1.6.d).

## 1. What it is good for

### 1.1 The problem: forged sources, attacks on the infrastructure, floods

On the Internet, the sender writes whatever source address it likes. Attackers send floods of packets whose source is
forged to be somebody else's address. The receiver cannot trace the real sender, and the replies go to the owner of the
forged address (a reflection attack). Not letting packets with forged sources out of its own customers, and not
accepting them from outside, is part of a provider's job (RFC 3704, BCP 84).

The provider's infrastructure itself (the addresses of its loopbacks and core links) is also a target. Nothing from
outside needs to reach those addresses directly.

When a customer is hit by a flood (DDoS), the flood crosses the provider's core before it reaches the customer's link.
The customer's link fills up, and so does the core. The provider wants to drop it as close to the entrance of its
network as it can.

### 1.2 What came before: hand-written ACLs

In Task M2-5 of M2, an input ACL dropped the packets with forged sources that came from the guest network. ACLs are
precise, but they are written by hand and need rewriting every time a customer's addresses change. With thousands of
customers, mistakes and omissions are certain.

ACLs are also slow against an attack. Adding the address under attack to the ACLs of every Internet border router is not
realistic in the middle of an attack.

### 1.3 The answer: protect with the routing information

- **uRPF** (Unicast Reverse Path Forwarding): checks the source address against the router's own routing table. The
  customers' addresses are in the routing table, so each customer is judged correctly without writing an ACL.
- **Infrastructure ACL**: the infrastructure addresses that nothing outside needs to reach are few and do not change, so
  an ACL protects them.
- **RTBH** (Remotely Triggered Black Hole): register an address to drop in one place, BGP hands it to every edge router,
  and the edge routers drop the packets to (or from) that address.

## 2. How it works

### 2.1 uRPF: checking the source against the routing table

A router normally forwards on the destination alone. uRPF also looks up the **source** address of an incoming packet in
the routing table (the CEF FIB, to be exact).

- **Strict**: passes the packet if the route to the source points out of the interface the packet came in on. It checks
  that "this source should be behind this interface". It suits places where routing is symmetric, that is, customers
  attached by a single link.
- **Loose**: passes the packet if there is a route to the source anywhere. Where it points does not matter. It is used
  where routing can be asymmetric (borders with several providers). Addresses with no route anywhere (unused numbers,
  private numbers and so on) are dropped.

With a default route, every address "has a route". So the default route is normally not counted, and `allow-default`
makes it count.

At XR01's entrance from CUST1 (a customer attached by a single link, 198.51.100.0/25), three sources were tried. The
packets were sent to CUST2, and what CUST2 received showed whether XR01 dropped them (replies to a forged source never
come back, so the sender's success rate tells nothing).

| XR01 configuration | Source in its own allocation (198.51.100.1) | An Internet number (203.0.113.99) | A number with no route anywhere (10.99.99.1) |
|---|---|---|---|
| None | Arrives | Arrives | Arrives |
| Strict | Arrives | **Dropped** (its route points to INET) | **Dropped** |
| Loose | Arrives | Arrives (there is a route) | **Dropped** |
| Loose (with a default route) | Arrives | Arrives | **Dropped** (the default route does not count) |
| Loose + `allow-default` | Arrives | Arrives | Arrives |

### 2.2 The infrastructure ACL

An ACL at the entrance of the provider's network that protects the addresses nothing outside needs to reach. The Cisco
TAC document recommends building it in four parts: ① drop forged sources; ② permit what the infrastructure does need
(BGP with the neighbour, for example); ③ drop everything else to the infrastructure; ④ permit the traffic passing
through (to the customers). ① can also be left to uRPF.

The ACL drops control packets to the router itself too. Leave out ② and the BGP session with the neighbour drops when its
hold time runs out (just as the OSPF adjacency dropped in M2-5).

### 2.3 RTBH: dropping by destination

The idea of RTBH is "hand every edge router, by BGP, a route to the address to drop, whose next hop is a route to the
discard address" (RFC 5635, section 3).

1. Every edge router has a static route from an unused address (the discard address; 192.0.2.1/32 is common) to Null0.
2. On the **trigger** router (RR1 in this lab), register the destination under attack as a static route with a marker (a
   tag).
3. When the trigger router puts the tagged route into BGP, it rewrites the next hop to the discard address 192.0.2.1, and
   adds a community mark (65000:666 in this lab) and `no-export`.
4. The edge routers receive the route. It is a /32, so it wins over the customer's route. Its next hop, 192.0.2.1, points
   to Null0, so the packets to that destination are dropped at the edge router's entrance.

`no-export` is the mark that keeps this /32 from going to other ASes. Forget it, and a specific route leaks to the
Internet. RFC 7999 defines a BLACKHOLE mark (65535:666) and recommends that the receiver add `no-export` or
`no-advertise`.

Dropping by destination stops the attack, but the destination under attack becomes unreachable for everyone. The
provider completes the attacker's job for them, which is the limit of RTBH.

### 2.4 RTBH: dropping by source

If the attacker's address is known, register it the same way and turn on **loose uRPF** at the entrance of the edge
routers (RFC 5635, section 4). The route to the attacker points to the discard address, so packets from there fail uRPF.
The destination under attack stays reachable from other sources.

Here IOS and IOS XR differ. IOS drops by uRPF when the route to the source points to Null0 through 192.0.2.1 (a Cisco
white paper, 2005). IOS XR on the ASR 9000 does not do a "recursive lookup to Null0" for uRPF (TAC document 116386).
XRv 9000 behaves the same.

| Route to the attacker (203.0.113.66) as XR01 received it | XR01's route | With loose uRPF on the INET side |
|---|---|---|
| Next hop 192.0.2.1 (rewritten at the trigger) | `via 192.0.2.1/32, recursive` → null0 | **Gets through** (all 10 to CUST2) |
| `set next-hop discard` (XR01's inbound policy) | `directly connected, via Null0` | **Dropped** (CUST2 got 0) |

In IOS XR, the RPL action `set next-hop discard` points a received route straight at Null0. Source-based RTBH on IOS XR
needs it.

### 2.5 Key points

- Strict for single-homed customers, loose at the border. The default route does not count by default
  (`allow-default` makes it count).
- An infrastructure ACL has four parts. Do not forget to permit your own BGP.
- RTBH is "hand out a /32 that points to the discard address, by BGP", with a mark and `no-export`. Dropping by
  destination makes that destination unreachable for everyone.
- To drop by source, loose uRPF at the edge. IOS XR needs `set next-hop discard`.

## 3. Building it in IOS XR

### 3.1 uRPF

:::config fold XR01 — strict at a customer's entrance, loose at the Internet border
interface GigabitEthernet0/0/0/2              ## CUST1 (single link)
 ipv4 verify unicast source reachable-via rx  ## Strict: the route to the source must point out of this interface
!
interface GigabitEthernet0/0/0/3              ## INET (the border)
 ipv4 verify unicast source reachable-via any ## Loose: there must be a route somewhere; the default route does not count
:::

`allow-default` makes the default route count. `allow-self-ping` lets through pings sourced from the router's own
address. Both can be added to strict and to loose.

```console
RP/0/RP0/CPU0:XR01#show cef ipv4 interface GigabitEthernet0/0/0/2 detail
...
  IP unicast RPF check is enabled
  RPF mode strict
...
RP/0/RP0/CPU0:XR01#show cef ipv4 drops
...
  RPF drops            packets :              17
```

The drops appear as `RPF drops` in `show cef ipv4 drops` (they too rise a little late).

### 3.2 The infrastructure ACL

:::config fold XR01 — drop packets from the Internet to the provider's infrastructure
ipv4 access-list FROM-INTERNET
 10 permit tcp host 10.0.100.100 host 10.0.100.1 eq bgp   ## ② BGP from the neighbour to me
 20 permit tcp host 10.0.100.100 eq bgp host 10.0.100.1   ## ② The return of BGP that I opened
 30 deny ipv4 any 10.0.0.0/16                 ## ③ The core links
 40 deny ipv4 any 10.255.0.0/24               ## ③ The loopbacks
 50 permit ipv4 any any                       ## ④ Transit (to the customers)
!
interface GigabitEthernet0/0/0/3
 ipv4 access-group FROM-INTERNET ingress hardware-count   ## hardware-count makes the hardware count each line
:::

```console
RP/0/RP0/CPU0:XR01#show access-lists ipv4 FROM-INTERNET hardware ingress location 0/0/CPU0
 10 permit tcp host 10.0.100.100 host 10.0.100.1 eq bgp
 20 permit tcp host 10.0.100.100 eq bgp host 10.0.100.1 (27 hw matches)
 30 deny ipv4 any 10.0.0.0 0.0.255.255 (8 hw matches)
 40 deny ipv4 any 10.255.0.0 0.0.0.255 (11 hw matches)
 50 permit ipv4 any any (40 hw matches)
```

The counts are totals since the ACL was applied (this output also counts the test traffic of the lab's checks). The
BGP packets with INET were counted on line 20.

- Without `hardware-count`, there are no hardware counts (the default for IPv4 ACLs; IPv6 always counts).
  `show access-lists ipv4 <name>` (without hardware) counts only the packets handled in software.
- ★On XRv 9000 26.1.1, `object-group`, which groups addresses, was not available (`Object groups not supported on this
  platform`). Write lines.
- ★An ACL named `ABF` was refused as a reserved word.
- IOS XR ACLs do not act on packets that carry MPLS labels, which means they are of no use on core-facing interfaces.

### 3.3 The RTBH trigger

On the trigger router (RR1), rewrite the tagged static routes with RPL and put them into BGP.

The RTBH configuration spans two routers: RR1 in this section and XR01 in section 3.4. The figure follows the route from
RR1 to XR01, and then an attack packet that arrives afterwards; rest the pointer on a number (or tap it on a phone) to
see that part of the configuration.

:::walk
legend: "On the wire: the route that BGP hands out. Orange: rewritten attributes."
rows:
  - panel: RR1
    sub: trigger
    items:
      - ref: 1
        head: "**Register the address to drop** `router static`"
        then: ["`198.51.100.130/32 Null0 tag 666`  with the marker tag 666"]
      - ref: 2
        head: "**Into BGP** `redistribute static route-policy RTBH-TRIGGER`"
        match:
          - ["if tag eq 666", true, match]
          - ["else", false, "other static routes: drop"]
        then:
          - "→ `set next-hop 192.0.2.1`  rewrite to the discard address"
          - "→ `set community (65000:666, no-export)`  the edges' mark; stays out of other ASes"
  - {wire: "[[=198.51.100.130/32]] [[!NH 192.0.2.1]] [[!65000:666 no-export]] _iBGP to the edges"}
  - panel: XR01
    sub: border (towards INET)
    items:
      - ref: 3
        head: "**Check on receipt** `route-policy FROM-RR in`"
        say: ["Routes from RR1 (10.255.0.52) go through the inbound RPL"]
        match:
          - ["if community matches-any RTBH", true, "matches 65000:666"]
        then: ["→ `set next-hop discard`  straight to Null0; other routes `pass` as they are"]
      - say: ["~RIB and CEF: 198.51.100.130/32 is directly connected, via Null0 (null0 adjacency)"]
      - say: ["[[IP → 198.51.100.130]] ~an attack packet from INET", "~is dropped where it enters XR01 and never reaches CUST2 (behind PE2)"]
  - aside: "Without ③ (only RR1's rewrite)"
    say:
      - "~XR01's route points to Null0 through 192.0.2.1 (as on PE2)"
      - "~Source-based RTBH (loose uRPF) then fails: IOS XR does not follow Null0 recursively (2.4)"
:::

:::config RR1 — hand out the static routes tagged 666 as routes towards the discard address
route-policy RTBH-TRIGGER                     ## ②
  if tag eq 666 then                          ## Only the tagged static routes
    set next-hop 192.0.2.1                    ## Rewrite to the discard address (every edge router has 192.0.2.1/32 → Null0)
    set community (65000:666, no-export)      ## The mark the edges pick up, and the mark that stays out of other ASes
    pass
  else
    drop                                      ## Do not hand out the other static routes
  endif
end-policy
!
router static
 address-family ipv4 unicast
  192.0.2.1/32 Null0                          ## ② The discard address here too (to resolve the rewritten next hop)
  198.51.100.130/32 Null0 tag 666             ## ① Register the address to drop
!
router bgp 65000
 address-family ipv4 unicast
  redistribute static route-policy RTBH-TRIGGER  ## ②
:::

An IOS edge router (PE2 in this lab) resolves the received next hop 192.0.2.1 with its static route to Null0.

```console
PE2#show ip cef 198.51.100.130 255.255.255.255 detail
198.51.100.130/32, epoch 0, flags [rib only nolabel, rib defined all labels]
  recursive via 192.0.2.1
    attached to Null0
```

### 3.4 The border router: set next-hop discard

On XR01, point the marked routes received from RR1 straight at Null0.

:::config fold XR01 — drop the marked routes directly
community-set RTBH                            ## ③
  65000:666
end-set
!
route-policy FROM-RR                          ## ③
  if community matches-any RTBH then
    set next-hop discard                      ## Straight to Null0; source-based uRPF drops with this too
  endif
  pass                                        ## Take the other routes as they are
end-policy
!
router bgp 65000
 neighbor 10.255.0.52                         ## RR1
  address-family ipv4 unicast
   route-policy FROM-RR in                    ## ③
:::

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 198.51.100.130/32
...
  Local
    10.255.0.52 (discarded) from 10.255.0.52 (10.255.0.52)
      Origin incomplete, metric 0, localpref 100, valid, internal, best, group-best
      Received Path ID 0, Local Path ID 1, version 8
      Community: 65000:666 no-export
RP/0/RP0/CPU0:XR01#show route 198.51.100.130/32
Routing entry for 198.51.100.130/32
  Known via "bgp 65000", distance 200, metric 0, type internal
  ...
    directly connected, via Null0
RP/0/RP0/CPU0:XR01#show cef 198.51.100.130/32
198.51.100.130/32, version 27, null0 adjacency, internal 0x5000001 0x40 (ptr 0x1063ed48) [1], 0x400 (0x107d55d8), 0x0 (0x0)
...
```

`(discarded)` shows that BGP treats the path's next hop as discarded (`N` in the status column of the table). This
output is from a trigger that only added the mark and did not rewrite the next hop (the next hop is still RR1).
According to the ASR 9000 guide, such a path is a candidate for best path even if the received next hop is unreachable,
and it cannot be used for L3VPN iBGP routes.

### 3.5 Checking it

| What to look at | Command |
|---|---|
| Whether uRPF is on, and what it dropped | `show cef ipv4 interface <IF> detail`, `show cef ipv4 drops` |
| The count per ACL line | `show access-lists ipv4 <name> hardware ingress location 0/0/CPU0` |
| The route the trigger handed out | On the trigger, `show bgp ipv4 unicast <address>` (next hop and mark) |
| Whether the edge now discards | `show bgp ipv4 unicast <address>` (`discarded`), `show route`, `show cef <address>` (`null0`) |
| Whether it leaked to the Internet | On the neighbouring AS (INET in this lab), `show ip bgp <address>` |
| Whether the packets were really dropped | What the destination received (in this lab, the echo count in CUST2's `show ip traffic`) |

### 3.6 Other tools: ABF and FlowSpec

**ABF** (ACL Based Forwarding) writes a next hop in an ACL line and sends the matching packets there, whatever the
routing table says. One use is to steer the packets to a destination under attack to a cleaning device (a scrubbing
centre) instead of dropping them.

:::config XR01 — steer the packets to the destination under attack to a cleaner (towards CUST1)
ipv4 access-list TO-SCRUB
 10 permit ipv4 any host 198.51.100.130 nexthop1 ipv4 172.20.1.1   ## On a match, send to 172.20.1.1
 20 permit ipv4 any any                       ## Forward the rest normally
!
interface GigabitEthernet0/0/0/3
 ipv4 access-group TO-SCRUB ingress hardware-count
:::

With this ACL applied, 20 packets sent from INET to 198.51.100.130 matched line 10 (`20 hw matches (next-hop:
addr=172.20.1.1, vrf name=default)`), and 20 packets left XR01's interface towards CUST1. ABF acted first even though
RTBH pointed 198.51.100.130 at Null0.

**BGP FlowSpec** (RFC 8955) hands out, by BGP, pairs of "conditions on destination, source, protocol, port and so on" and
"actions: drop, limit the rate, re-mark, steer into another VRF". Where RTBH "drops everything for an address", FlowSpec
can cut finely, as in "only this UDP port to this destination". The side that builds and sends the rules is the
controller; the side that receives them and puts them into its own hardware is the client.

With RR1 (XRd) as the controller and XR01 as the client, the rule (ICMP to 198.51.100.129 at 0 bps) reached XR01, and
`show flowspec ipv4 detail` showed `Traffic-rate: 0 bps`, but the packets were not dropped. XRv 9000 cannot apply rules
as a client (the same as an answer on the Cisco Community; FlowSpec is not in the official support table either). The
mechanism and the form of the configuration are in the appendix.

:::try
With ABF, steer the packets to the destination under attack instead of dropping them. Do it after Task M12-5, and always
put things back at the end.

1. On XR01, add `45 permit ipv4 any host 198.51.100.130 nexthop1 ipv4 172.20.1.1` to the ACL you applied on the INET side
   in Task M12-4, and commit.
2. On XR01, look at `show interfaces GigabitEthernet0/0/0/2 | include packets output`, then run
   `ping 198.51.100.130 source Loopback0 repeat 20 timeout 1` on INET, and look again. Look at the ACL counts too.
3. Remove line 45 and commit.

An example result: across the 20 pings, `packets output` on GigabitEthernet0/0/0/2 went from 26 to 46, and line 45
showed `(20 hw matches) (next-hop: addr=172.20.1.1, vrf name=default)`. INET's ping success rate was 0 (CUST1, the
cleaner, does not own the address, so nothing replies). ABF acted first even for a destination that RTBH pointed at
Null0.
:::

## Practice

Do Tasks M12-4 and M12-5 in lab **XRT-14**.

<p class="tolab"><a href="/_learn?id=XRT-14">Open lab XRT-14 in the workspace</a> — <a href="d5-m12-practice-3.html">Tasks M12-4 and M12-5</a></p>

:::note
The output on this page was taken on the same board as the previous pages.
Sources: RFC 3704 (sections 2.2 to 2.5), RFC 8704 (section 3), RFC 5635 (sections 3 and 4), RFC 7999 (sections 2, 3 and 5),
RFC 3882, RFC 8955. The ASR 9000 IP Addresses and Services Command Reference and Configuration Guide (IOS XR 24.x:
`ipv4 verify unicast source reachable-via`, strict and loose, `ipv4 access-group … hardware-count`, object-groups, ABF),
the ASR 9000 Routing Configuration Guide (IOS XR 7.10.x: RTBH and `set next-hop discard`) and the Cisco 8000 RPL command
reference, the BGP FlowSpec chapter for the ASR 9000 (IOS XR 24.x), the Cisco TAC documents "Protecting Your Core:
Infrastructure Protection Access Control Lists" (43920) and 116386 (uRPF and RTBH on the ASR 9000), and the Cisco white
paper "Remotely Triggered Black Hole Filtering—Destination Based and Source Based" (2005). All checked in November 2026.
The following come from measurements on the PoC board (the same shape as XRT-14): the uRPF table, the ACL counts, the
object-group and reserved-word findings, the two forms of RTBH and source-based uRPF, ABF, and FlowSpec not taking effect.
:::
