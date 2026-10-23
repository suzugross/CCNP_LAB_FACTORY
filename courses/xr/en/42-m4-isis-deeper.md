# M4 — IS-IS in depth

The first M4 page covered what every IS-IS network needs. This page adds four things that a provider network uses
every day and that the later units do not bring up again on their own: authentication, broadcast segments and the
DIS, summarization, and area addresses. Overload, timers, BFD and graceful restart come with M7 (high availability),
and the IS-IS extensions for MPLS and segment routing with M8 and M10.

The outputs on this page were captured on IOS XRd 26.1.1 and IOS XE 17.15 on IOL (lab XRT-05).

## 1. Authentication

### 1.1 What is authenticated

IS-IS authenticates PDUs, not sessions, and it does so in two separate places:

| What | Covers | Configured on IOS XR | Configured on IOS |
|---|---|---|---|
| Hellos | the IIHs of one interface | `hello-password` under the interface in `router isis` | `isis authentication …` on the interface |
| The database | LSPs and the sequence number PDUs (CSNP, PSNP) of one level | `lsp-password` under `router isis` | `authentication …` under `router isis` |

Both are set per level. Without a level keyword the setting covers Level 1 and Level 2. On a point-to-point link one
hello serves both levels, so the level keyword means nothing there for hellos.

The authentication value travels in a TLV (type 10) inside the PDU. The value is either a clear-text password, which
anyone on the link can read, or an HMAC-MD5 digest of the whole PDU (RFC 5304). The HMAC-MD5 TLV carries no key ID, so
the routers at the two ends need the same key string, but not the same key number. Stronger algorithms (HMAC-SHA,
RFC 5310) add a key ID.

### 1.2 Key chains on IOS XR

A key chain gives a key a name, a string, an algorithm and the time during which it may be used. IOS XR is strict about
all of them, and it does not always say so when you commit:

| Item | What IOS XR does |
|---|---|
| `key-string clear <text>` | stores the string, shown encrypted afterwards. `clear` is the default. |
| `key-string password <text>` | expects the **encrypted** form. A plain string fails the commit: `'Key Chain Server Process' detected the 'fatal' condition 'Incorrect or NULL parameter(s)'` |
| no `cryptographic-algorithm` | the commit succeeds, but no digest can be computed: the key is not used |
| no `accept-lifetime` / `send-lifetime` | the commit succeeds, but the key is not valid: it is not used |
| a key chain that does not exist, named in `hello-password keychain` | the commit succeeds, and every received hello fails authentication |

`show key chain` tells you whether a key is usable. A key without lifetimes shows `Not configured` and no `[Valid now]`:

```console
RP/0/RP0/CPU0:XR01#show key chain ISIS-L2
Key-chain: ISIS-L2 -

  timezone -- local
  Key 1 -- text "01310454550E4B5D711E18"
    Cryptographic-Algorithm -- HMAC_MD5
    Send lifetime -- Not configured
    Accept lifetime -- Not configured
```

and once both lifetimes are set:

```console
    Send lifetime --  00:00:00, 01 Jan 2026 - Always valid  [Valid now]
    Accept lifetime -- 00:00:00, 01 Jan 2026 - Always valid [Valid now]
```

:::note
Cisco's keychain configuration guide says that a key configured without a lifetime is invalid and "rejected during
configuration". On IOS XRd 26.1.1 such a key is accepted by the commit and is simply not used, with the same result in
the end: authentication fails. The same guide marks the lifetime commands as optional. Check `show key chain`, not the
commit, to know whether a key will be used.
:::

### 1.3 What a mismatch looks like

A router that has no authentication configured does not check it. It accepts PDUs that carry a digest, and its own PDUs
carry none. A router that has authentication configured discards every PDU that does not carry the right digest. So a
half-done change shows up on one side only.

When the neighbours authenticate hellos and XR01 does not, XR01 sees their hellos and lists them as `Init`, while they
discard XR01's hellos. The adjacency never comes up. When XR01 authenticates hellos but with a key it cannot use, it is
XR01 that discards, and it says so in the interface view:

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/1 | include "Rejected|Received"
  Last IIH Received:        12:59:15 (00:02:16 ago), 1496 octets
  Last PDU Rejected:        13:01:29 (2.18 sec ago), 1496 octets, P2P IIH, Authentication Failed
```

When the hellos match but only the neighbours authenticate LSPs, the adjacency is up and XR01 accepts their LSPs: XR01
has every backbone route. The neighbours discard XR01's LSPs, so the backbone has no route to XR01's area. One more
clue: the hostname of a router travels in its LSP (TLV 137), so a neighbour that has discarded XR01's LSP shows XR01 by
its system ID:

```console
RT02#show clns neighbors
System Id       Interface     SNPA                State  Holdtime  Type Protocol
0102.5500.0001  Et0/0         5254.00dd.b44f      Up     29        L2   IS-IS
RT03            Et0/1         aabb.cc00.3410      Up     24        L2   IS-IS
RT03            Et0/2         aabb.cc00.3420      Up     8         L2   IS-IS
```

### 1.4 Keeping a level unauthenticated

`lsp-password` without a level authenticates Level 1 as well. An unauthenticated Level 1 neighbour still accepts XR01's
LSPs, but XR01 now discards the neighbour's LSPs and sequence number PDUs. Nothing happens at once: XR01 keeps the copy
of the neighbour's LSP that it already holds. The next time the neighbour changes a prefix and floods a new LSP, XR01
rejects it and keeps routing on the old copy:

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/0 | include "Rejected|Received"
  Last IIH Received:        13:07:00 (3.29 sec ago), 1496 octets
  Last PDU Rejected:        13:07:02 (0.84 sec ago), 285 octets, L1 LSP, Authentication Failed
```

IS-IS removes an LSP whose lifetime (1200 seconds at most) has run out, so when the old copy expires, the neighbour's
routes disappear too. A fault that appears twenty minutes after the change is hard to connect with it. Give the level
explicitly.

## 2. Broadcast segments and the DIS

### 2.1 The pseudonode

On a broadcast segment every router forms an adjacency with every other router on it. If each router listed all the
others as neighbours in its LSP, a segment of n routers would add n × (n − 1) neighbour entries to the database. IS-IS
avoids that by electing a **DIS** (designated intermediate system) per level. The DIS originates an extra LSP for the
segment, the **pseudonode** LSP. Every router on the segment, the DIS included, lists only the pseudonode as its
neighbour on that segment, and the pseudonode lists all the routers, at metric 0.

The pseudonode LSP ID is the DIS's system ID followed by a non-zero circuit number: `XR01.01-00` is the pseudonode that
XR01 originates for one of its LAN interfaces.

The DIS also sends CSNPs on the segment every 10 seconds, the list of every LSP it holds. A router that finds an LSP
missing or older in its own database asks for it with a PSNP. There is no backup DIS: if the DIS fails, the others
elect a new one and the new DIS originates a new pseudonode LSP.

### 2.2 The election

The router with the highest **priority** (0 to 127, default 64) becomes the DIS. On a tie the highest MAC address
(SNPA) wins. Priority is set per level, and Level 1 and Level 2 can have different DISes on the same segment.

Unlike the OSPF DR, the DIS is **pre-emptive**: a router with a higher priority takes the role as soon as it appears,
and the old DIS purges its pseudonode LSP (it shows with a remaining lifetime of 0) while the new DIS originates one.
A role decided by MAC addresses can change when a router is replaced or, in a lab, rebuilt. To pin the role, give the
router a priority higher than all the others.

On IOS XR, the interface view shows the LAN ID (the pseudonode) and the priority of the router and of the DIS:

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/3 | include "Media|LAN ID|Priority"
  Media Type:               LAN
    LAN ID:                 XR01.01
    Priority (Local/DIS):   100/100
```

`show isis interface brief` marks the adjacency count with `*` on the segments where the router itself is the DIS.
On IOS, `show clns interface` gives the same information as `DR ID`.

### 2.3 Point-to-point against broadcast

The mismatch from the first M4 page works in both directions. A LAN interface configured as point-to-point on IOS XR,
facing routers that send LAN hellos, rejects them:

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/3 | include "Media|Rejected"
  Media Type:               P2P
  Last PDU Rejected:        13:10:32 (2.26 sec ago), 1497 octets, L2 LAN IIH, LAN IIH on P2P Interface
```

A segment with more than two routers cannot be point-to-point. A segment with exactly two routers can be, if both ends
agree, and then it has no DIS and no pseudonode.

## 3. Summarization

### 3.1 Where and how

An L1/L2 router can advertise a range in place of the prefixes inside it. On IOS XR, `summary-prefix` goes under the
address family in `router isis`, so IPv4 and IPv6 are summarized separately. The level keyword names the level that
receives the summary. Without a level the summary applies to both levels.

| Behaviour | Detail |
|---|---|
| Metric | the lowest metric among the prefixes inside the range |
| Discard route | the router installs the range towards Null0 (`type manual summary`), so that traffic to an unused part of the range is dropped there instead of following a default route |
| Withdrawal | when no prefix inside the range is reachable any more, the summary is withdrawn |

```console
RP/0/RP0/CPU0:XR01#show route ipv4 10.11.0.0/16

Routing entry for 10.11.0.0/16
  Known via "isis CORE", distance 115, metric 20 (summary), type manual summary
  Installed Oct 22 13:14:04.553 for 00:00:42
  Routing Descriptor Blocks
    directly connected, via Null0
      Route metric is 20
  No advertising protos.
```

In its own Level 2 LSP, IOS XR shows the IPv6 summary as `IPv6-External 2001:db8:1011::/48`, while IOS routers
install it as an ordinary Level 2 route.

### 3.2 What it costs

A summary hides detail on purpose. The backbone no longer sees a single access LAN fail, and it does not recompute
anything when one does. The price is the same as in OSPF: with two L1/L2 routers in an area, each advertising the same
summary, the backbone can no longer tell which of them is closer to a given LAN. Prefixes that need their own route,
such as the loopbacks that MPLS will need, must stay outside the range.

## 4. Area addresses

### 4.1 More than one NET

A router may have up to **three** NETs. They must all have the same system ID; only the area part may differ. IOS XR
refuses anything else at commit time:

```console
!!% System ID must not change: 0102.5500.0001
!!% Maximum area address count exceeded: maximum number of area addresses is 3
```

A Level 1 adjacency needs **one** area address in common, not all of them. A router with two NETs therefore belongs to
both areas at once, and the two areas merge into one Level 1 area. `show isis` lists the areas configured on the router
(`Manual area address(es)`) and the areas of the whole Level 1 area as learned from the neighbours (`Routing for area
address(es)`). When no area address is shared, the Level 1 adjacency goes down with `Area addr/level differ` in the
adjacency log and `Level or Area Addr mismatch` as the last rejected PDU.

### 4.2 Renumbering an area

Multiple NETs are how an area is renumbered without an outage: add the new area address to every router of the area,
then remove the old one from every router. At every step each pair of neighbours shares at least one area.

On IOS XR the two steps must be two commits. Replacing the NET in one commit (`no net` the old one and `net` the new
one), even with the system ID unchanged and a neighbour that already has both areas, restarts **every** adjacency of
the router, Level 2 included:

```console
RP/0/RP0/CPU0:XR01#show isis adjacency-log
  IS-IS CORE  Level 1  Adjacency Log             Capacity: 100, Size: 2
When          System          Interface          State   Details
--- Thu Oct 22 2026 ---
13:18:36.328  RT01            Gi0/0/0/0          d -> i
13:18:36.632  RT01            Gi0/0/0/0          i -> u  New adjacency
  IS-IS CORE  Level 2  Adjacency Log             Capacity: 100, Size: 6
When          System          Interface          State   Details
--- Thu Oct 22 2026 ---
13:18:36.028  RT03            Gi0/0/0/3          d -> u  New adjacency
13:18:36.326  RT03            Gi0/0/0/2          d -> i
13:18:36.326  RT02            Gi0/0/0/1          d -> i
13:18:36.498  RT02            Gi0/0/0/3          d -> u  New adjacency
13:18:36.628  RT03            Gi0/0/0/2          i -> u  New adjacency
13:18:36.630  RT02            Gi0/0/0/1          i -> u  New adjacency
```

Adding the new NET in one commit and removing the old one in another changed nothing in the log. `show isis
adjacency-log` keeps the last 100 state changes per level, with no configuration needed, and is the quickest way to
see whether a change disturbed anything.

## 5. Command names

| On IOS | On IOS XR |
|---|---|
| `isis authentication mode md5` + `isis authentication key-chain …` on the interface | `hello-password keychain …` under the interface in `router isis` |
| `authentication mode md5` + `authentication key-chain …` under `router isis` | `lsp-password keychain … [level 1 \| 2]` under `router isis` |
| `show key chain` | `show key chain` |
| `isis priority …` | `priority … [level 1 \| 2]` under the interface in `router isis` |
| `show clns interface` (`DR ID`) | `show isis interface <name>` (`LAN ID`, `Priority (Local/DIS)`) |
| `summary-address …` under `router isis` | `summary-prefix … [level 1 \| 2]` under the address family in `router isis` |
| `net …` (several) | `net …` (several, up to 3) |
| `show clns neighbors detail` (`Uptime`) | `show isis adjacency-log` |

## Practice

Go to lab **XRT-05** and do the second series of M4 tasks. It starts where XRT-04 ended.

<p class="tolab"><a href="/_learn?id=XRT-05">Open lab XRT-05 in the workspace</a> — <a href="43-m4-practice-2.html">The tasks</a></p>

:::note
Sources: the IOS XR *IS-IS command reference* for Cisco 8000 and NCS 5500 (`lsp-password` and `hello-password`, both
levels when none is given, SNPs covered by `lsp-password`, `summary-prefix` with its metric and discard route, `priority`
and the pre-emptive DIS, at most three NETs with one system ID, `show isis adjacency-log`) and the IOS XR *keychain
management* guide and command reference (`key-string clear | password`, the cryptographic algorithm, lifetimes), checked
October 2026; the IOS XE 17.x *IP Routing Configuration Guide*, "Enhancing Security in an IS-IS Network" (hellos on the
interface, LSPs and SNPs on the instance); RFC 5304 (HMAC-MD5, no key ID) and RFC 5310; RFC 1142 (the text of ISO 10589:
the DIS and the pseudonode). The following come from measurement on IOS XRd 26.1.1 and IOS XE 17.15: the commit messages,
keys that commit but are not used, the rejected-PDU messages, the one-sided acceptance of LSPs, the delayed effect of
authenticating Level 1, the `*` in the interface summary, the `IPv6-External` display of the summary, and the restart of
every adjacency when the NET is replaced in one commit.
:::
