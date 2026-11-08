# M12 — Marking and the MPLS QoS models

The previous page laid out the parts of QoS inside one router. This page is about the first two jobs, sorting and
marking: where the marks are set, how the MPLS core carries them on the labels, and how the customer's marks are kept
apart from the provider's. It covers 4.5.a of the blueprint (classification and marking) and the QoS architecture of
1.4. The board is XRT-14, shown on the previous page.

## 1. What it is good for

### 1.1 The problem: urgent and patient packets share one core

The voice of customer A's phones does not cope well with delay or jitter. If voice packets wait an extra 100 ms, the
conversation breaks up; if a few percent are lost, the voice drops out. The same links also carry large amounts of
traffic that does not mind waiting a little, such as file transfers and backups.

While the core links are idle, both arrive at once. The trouble comes when they are busy. When an exit queue fills with
bulk packets, a voice packet that arrives later waits behind them, and when the queue overflows it is dropped just the
same. A router that cannot tell which packets are urgent cannot treat them differently.

### 1.2 What came before

There were two ways.

- **Leave bandwidth spare**: with enough bandwidth that nothing is ever busy, there is no need to tell packets apart.
  But demand keeps growing, sizing every link for its busiest moment is expensive, and links get busy anyway when
  traffic detours around a failure.
- **Reserve per flow (IntServ)**: the application reserves bandwidth for a flow with RSVP along the routers on the way,
  and each router keeps state for each flow to honour it (RFC 1633, RFC 2205). The guarantee is firm, but core routers
  would keep state for hundreds of thousands of flows, which does not scale to a provider's core (appendix).

### 1.3 The DiffServ answer

DiffServ (Differentiated Services) decides the treatment by **marking the packets** instead of remembering flows
(RFC 2475).

- At the **edge** of the network (the PE that attaches the customer), packets are classified and marked. How they are
  marked is agreed in the customer's contract.
- Routers **inside** (the core) look only at the mark. They remember no flows; they only need to know the kinds of
  mark, a handful of classes at most.
- Packets with the same mark are treated the same way, as an aggregate. This treatment is called a **PHB** (Per-Hop
  Behavior).

The edge PE takes the heavy work (classifying, checking the contract, marking), and the core does the light work
(queuing by the mark). In an MPLS core, the mark is carried on the labels as well (section 2.3).

## 2. How it works: one packet, hop by hop

### 2.1 The IP mark: DSCP

The IP header has 8 bits for a treatment mark (the ToS byte in IPv4, Traffic Class in IPv6). DiffServ uses the upper
6 of them as the **DSCP** (DiffServ Code Point) (RFC 2474, section 3). The remaining 2 bits are for congestion
notification (ECN). The values in common use are:

| Name | DSCP (binary / decimal) | ToS byte | Top 3 bits | Meaning |
|---|---|---|---|---|
| EF | 101110 / 46 | 0xb8 | 5 | Low delay and jitter, first up to a set rate (RFC 3246) |
| AF21 | 010010 / 18 | 0x48 | 2 | AF class 2, drop precedence 1 (RFC 2597) |
| AF22 | 010100 / 20 | 0x50 | 2 | AF class 2, drop precedence 2 (dropped before AF21 under congestion) |
| AF11 | 001010 / 10 | 0x28 | 1 | AF class 1, drop precedence 1 |
| CS6 | 110000 / 48 | 0xc0 | 6 | Network control (routing protocols) |
| Default (BE) | 000000 / 0 | 0x00 | 0 | No special treatment |

AF (Assured Forwarding) is a set of four classes with three drop precedences: in AF*xy*, *x* is the class and *y* the
drop precedence (higher is dropped first). Packets of one class must not be reordered, so traffic beyond the contract
can be "re-marked AF22 and carried" instead of dropped (page *Policing and shaping*). The top three bits sit where IP
Precedence, the mark before DSCP, used to be.

### 2.2 The trust boundary

A mark is set by the device that builds the packet. A customer's phone marks its packets EF, but a customer's PC may
mark its own packets EF too, to make them faster. If the provider believes the customer's marks as they are, traffic
that is not in the contract travels first and pushes the real voice aside.

So the provider sets a **trust boundary** at the entrance of its network. The PE classifies what it receives from the
customer and re-marks whatever does not fit the contract before it lets the packet into the core. How much of the
marking to believe is decided by the contract, for example "EF only towards the voice network; any other EF goes back to
default" (Task M12-1). An enterprise network sets its boundaries the same way, trusting the IP phones and not the PCs.

### 2.3 The mark on the label: EXP

Routers in an MPLS core forward on the top label alone (M8). To choose a treatment without reading the IP header under
the labels, they need a mark on the label too. Three of the label's 32 bits are kept for it, long called **EXP**
(Experimental). Today's name is **TC** (Traffic Class) (RFC 5462), which is also what packet captures show (`tc`).

Three bits give at most eight marks. An LSP whose per-hop behaviour is chosen by these three bits is an **E-LSP**
(RFC 3270, section 1.2). There is also the **L-LSP**, which sets up a separate label (a separate LSP) for each class and
lets the label stand for the class (section 1.3). Ordinary cores use E-LSPs. So does this lab: LDP gives one label per
destination, whatever the class.

### 2.4 On the wire: with no policy at all

Send three kinds of packet from customer A's site 1 to site 2. By destination, CE1 marks them EF, AF11 or not at all.
The output below shows the packets on the links, with no QoS policy on XR01 or PE2.

:::topo
nodes:
  CE1: {at: [0, 0.5], kind: host}
  XR01: [1.4, 0.5]
  P1: [2.8, 0.5]
  PE2: [4.2, 0.5]
  CE2: {at: [5.6, 0.5], kind: host}
links:
  - [CE1, XR01, "IP EF"]
  - [XR01, P1, "16(5) | 23(5)"]
  - [P1, PE2, "23(5)"]
  - [PE2, CE2, "IP EF"]
:::

The numbers on a link are labels, with the EXP in brackets; the top label is on the left.

```console
# On the XR01 → P1 link (EF, then AF11)
MPLS (label 16, tc 5, ttl 254) (label 23, tc 5, [S], ttl 254) IP (tos 0xb8, ttl 254, proto ICMP (1)) 10.46.0.1 > 10.46.0.2: ICMP echo request, id 11, seq 0
MPLS (label 16, tc 1, ttl 254) (label 24, tc 1, [S], ttl 254) IP (tos 0x28, ttl 254, ...) 10.10.0.1 > 10.10.0.2: ICMP echo request, id 12, seq 0
# On the P1 → PE2 link
MPLS (label 23, tc 5, [S], ttl 253) IP (tos 0xb8, ttl 254, proto ICMP (1)) 10.46.0.1 > 10.46.0.2: ICMP echo request, id 11, seq 0
# On the PE2 → CE2 link
IP (tos 0xb8, ttl 252, proto ICMP (1)) 10.46.0.1 > 10.46.0.2: ICMP echo request, id 11, seq 0
```

Read it one hop at a time.

1. CE1 sends an IP packet marked EF (ToS 0xb8) to XR01.
2. XR01 pushes two labels: the outer one is the LDP label 16 that P1 gave PE2's loopback, the inner one is the VPN label
   23 that PE2 gave this route of VRF A. With no policy, it **copies the top three bits of the DSCP (5 for EF, 1 for
   AF11) into the EXP of every label it pushes**.
3. P1 looks only at the outer label. It is one hop before PE2, so it pops the outer label (PHP) and sends the packet to
   PE2. The EXP of the remaining inner label is still 5.
4. PE2 pops the inner label and sends the IP packet to CE2. The DSCP is still the EF that CE1 set.

The other direction (from CE2 to site 1) was the same: PE2 (IOS XE) also copied the top three bits of the DSCP into the
EXP. The documentation says so too: when a label is pushed, "the identified precedence, DSCP, or MPLS EXP value is used
for the EXP bits" (ASR 9000), and "the 1st three bits of the DSCP bit is copied to the MPLS EXP bits of all pushed
label(s)" (an IOS TAC document). When a label is popped, the DSCP is not rewritten unless a policy says so.

### 2.5 The three models: the customer's mark and the provider's mark

A provider may want to run its core on its own classes, apart from the customer's DSCP. The customer marks DSCP by its
own rules and wants it carried between its sites unchanged. RFC 3270 sorts out the relation between these two marks
(the customer's DSCP and the provider's EXP) into two models, uniform and pipe, and also defines short pipe as a variation
of pipe (section 2.6). This page sets the three side by side and calls them the three models. TTL has the same models
(RFC 3443).

| Model | Ingress PE (IP → label) | Core | Egress PE (label → IP) |
|---|---|---|---|
| Uniform | Derives the EXP from the DSCP | Treats by EXP, may re-mark it | **Copies the EXP back into the DSCP** (a downgrade in the core shows to the customer) |
| Pipe | Sets the EXP by the provider's policy | Treats by EXP | Leaves the DSCP **as it is**; the exit queue is chosen by the **EXP** |
| Short pipe | Sets the EXP by the provider's policy | Treats by EXP | Leaves the DSCP **as it is**; the exit queue is chosen by the **customer's DSCP** |

Uniform holds that there is one mark across the whole network (only the outermost mark ever means anything, and it is
copied down when a label is popped). Pipe and short pipe carry the customer's mark untouched, as "cargo in the tunnel",
and put the provider's mark only on the outside. They differ in which mark the egress PE uses to choose the queue when it
sends the packet out to the customer.

On XR01, give AF11 an EXP of 2 (and leave the DSCP alone). In the core it travels as EXP 2, and the customer receives
AF11 unchanged. This is the ingress half of pipe and short pipe (the configuration is in section 3.2).

```console
# On the XR01 → P1 link (after giving AF11 an EXP of 2)
MPLS (label 16, tc 2, ttl 254) (label 24, tc 2, [S], ttl 254) IP (tos 0x28, ttl 254, ...) 10.10.0.1 > 10.10.0.2: ICMP echo request, id 15, seq 0
# On the PE2 → CE2 link
IP (tos 0x28, ttl 252, ...) 10.10.0.1 > 10.10.0.2: ICMP echo request, id 15, seq 0
```

### 2.6 PHP and explicit null: where a mark set in the core goes

A core router may re-mark the EXP, for example to downgrade a class as a precaution against congestion. On P1, re-mark
the EXP 5 that comes from XR01 to 0 (IOS XE `set mpls experimental topmost 0`). P1 counts what it re-marked, yet the
packets reaching PE2 still had EXP 5.

```console
# On the P1 → PE2 link (after P1 re-marked EXP 5 to 0)
MPLS (label 23, tc 5, [S], ttl 253) IP (tos 0xb8, ttl 254, proto ICMP (1)) 10.46.0.1 > 10.46.0.2: ICMP echo request, id 17, seq 0
```

P1 re-marked the outer label, and then popped that label with PHP. The EXP of a popped label is copied neither to the
label below nor to the IP header (an IOS TAC document also says "at label disposition, the EXP bits are not copied down
to the newly exposed label EXP bits"). With PHP, **a re-marking in the core never reaches the egress PE**.

If the egress PE advertises explicit null, P1 does not pop the outer label; it swaps it for label 0. The re-marked EXP
rides on that label 0 all the way to PE2.

:::topo
nodes:
  XR01: [0, 0.5]
  P1: [1.6, 0.5]
  PE2: [3.2, 0.5]
links:
  - [XR01, P1, "16(5) | 23(5)"]
  - [P1, PE2, "0(0) | 23(5)"]
:::

```console
# On the P1 → PE2 link (after PE2 advertised explicit null)
MPLS (label 0 (IPv4 explicit NULL), tc 0, ttl 253) (label 23, tc 5, [S], ttl 254) IP (tos 0xb8, ttl 254, proto ICMP (1)) 10.46.0.1 > 10.46.0.2: ICMP echo request, id 20, seq 0
```

This is why RFC 3270 says "the Pipe Model operates only without PHP" (section 2.6.2). The uniform model, too, needs the
outer label to last to the egress if the egress is to receive a re-marking from the core. Short pipe looks at the
customer's DSCP at the egress, so it works with PHP. In an L3VPN, the inner VPN label lasts to the egress, so the EXP
that the ingress PE set can still be read there after PHP. Traffic carried on a single label, such as Internet traffic,
has no label left after PHP, and its EXP is gone too (in this lab, the traffic from CUST1 to CUST2).

### 2.7 TTL is the same story

The 8-bit TTL on the label has the same three models (RFC 3443). The default is uniform: the IP TTL is copied to the
label when it is pushed and copied back when it is popped. That is why a customer's traceroute shows the core routers
one hop at a time.

```console
CE1#traceroute 10.100.2.1 source Loopback100 probe 1 timeout 2
  1 172.16.1.254 4 msec
  2 10.0.1.51 [MPLS: Labels 16/21 Exp 0] 3 msec
  3 172.16.2.254 [MPLS: Labels 0/21 Exp 0] 2 msec
  4 172.16.2.1 2 msec
```

The label on the third hop is `0/21` because PE2 was advertising explicit null at the time (section 2.6).

With `mpls ip-ttl-propagate disable` on XR01, XR01 sets the TTL of the labels it pushes to 255. The TTL no longer runs
out inside the core, and P1 (10.0.1.51) disappeared from the traceroute. Providers that want to hide the shape of their
core from customers use it (the pipe model for TTL).

```console
CE1#traceroute 10.100.2.1 source Loopback100 probe 1 timeout 2
  1 172.16.1.254 2 msec
  2 172.16.2.254 [MPLS: Labels 0/21 Exp 0] 2 msec
  3 172.16.2.1 2 msec
```

### 2.8 Key points

- Marks are set at the edge PE and the core looks only at them (DiffServ). The ingress PE decides how much of the
  customer's marking to believe (the trust boundary).
- In an MPLS core, the mark is also carried in three bits of the label (EXP, now called TC). Without a policy, the top
  three bits of the DSCP are copied into every label pushed. The DSCP does not change when the labels are popped.
- The three models differ in whether the egress PE copies the EXP back into the DSCP, and in which mark chooses the
  queue.
- An EXP re-marked in the core disappears with the outer label at PHP. To deliver it to the egress, use explicit null.

## 3. Building it in IOS XR

### 3.1 The parts of MQC

IOS XR writes QoS in the same three tiers of MQC (Modular QoS CLI) as IOS.

| Part | Role | Differences from IOS |
|---|---|---|
| `class-map` | The conditions that sort packets (`match dscp`, `match mpls experimental topmost`, `match access-group ipv4`, `match qos-group` and others) | Ends with `end-class-map`; `match-any` (any of them) and `match-all` (all of them) are stated explicitly |
| `policy-map` | The actions per class (`set`, `police`, `shape`, `priority` and others) | Ends with `end-policy-map`; the classes are checked in the order written |
| `service-policy` | Applies a policy to an interface, with a direction (`input`/`output`) | The same |

The marking actions are:

| Action | Meaning | Direction |
|---|---|---|
| `set dscp <value>` | Rewrites the IP DSCP | Input and output |
| `set mpls experimental imposition <0-7>` | The EXP of **every** label pushed | Input only (decided before the labels are pushed) |
| `set mpls experimental topmost <0-7>` | The EXP of the top label | Input and output |
| `set qos-group <value>` | A number internal to the router (never on the wire). Set on input, read on output with `match qos-group` | Input only |

`qos-group` is the router's internal mark for carrying what was read on input through to the output. An egress PE
needs it when it reads the EXP on its core-facing input and uses it on its customer-facing output (section 3.3). The
ASR 9000 guide states that it is set only on input and matched only on output.

### 3.2 The ingress PE: classify and set the EXP

This is the configuration used in section 2.5. What arrives from customer A's site 1 is sorted into EF (voice), AF11
(bulk data) and the rest, and given the provider's EXP. The DSCP is left alone.

:::config XR01 — give an EXP to what arrives from site 1
class-map match-any VOICE                     ## The voice class; with one condition, any and all are the same
 match dscp ef
 end-class-map                                ## XR writes the end of the class
!
class-map match-any BULK
 match dscp af11
 end-class-map
!
policy-map CE-IN
 class VOICE
  set mpls experimental imposition 5          ## EXP 5 on every label pushed
 !
 class BULK
  set mpls experimental imposition 2          ## The customer's AF11 (top bits 1) is treated as 2 in the core
 !
 class class-default
  set mpls experimental imposition 0          ## The rest gets 0; left out, the top three bits of the DSCP are copied
 !
 end-policy-map
!
interface GigabitEthernet0/0/0/1              ## The interface to CE1 (VRF A)
 service-policy input CE-IN                   ## On input; imposition can only be written on input
:::

To re-mark the customer's mark at the trust boundary (section 2.2), add `set dscp` to a class. For example, build a
class for "EF not towards the voice network" (combine `match dscp ef` with an ACL on the destination in a
`class-map match-all`, or put a class for EF towards the voice network first and catch the remaining EF in a later
class) and use `set dscp default` there.

If that class has no `set mpls experimental imposition`, the EXP is a copy of the top three bits of the DSCP **after**
the rewrite. On XRv 9000, EF in a class with only `set dscp default` was counted as EXP 0 at P1 (not 5, the value of
EF before the rewrite). The official text quoted in section 2.4, however, does not say whether the value before or
after the rewrite is copied. So it is safer to write `imposition` in a re-marking class too, and set the EXP without relying on
the default copy (if you later change what the DSCP is rewritten to, the EXP does not change with it).

The same thing in IOS XE looks like this (from the fixed configuration of PE2 in the lab). There is no
`end-class-map`, and `set mpls experimental imposition` is written the same way.

:::config PE2 (IOS XE) — give an EXP to what arrives from CE2 (excerpt from the fixed configuration)
class-map match-any VOICE
 match dscp ef
class-map match-any DATA
 match dscp af21
!
policy-map CE-IN
 class VOICE
  set mpls experimental imposition 5
 class DATA
  set mpls experimental imposition 3
 class class-default
  set mpls experimental imposition 0
!
interface Ethernet0/1
 service-policy input CE-IN
:::

### 3.3 The egress PE: inherit the EXP

Build a uniform egress on XR01 (for the packets from CE2 to site 1). P1 re-marks the EXP 5 that comes from PE2 to 0.
XR01 reads the EXP of the outer label on its core-facing input and moves it into a qos-group, then copies the qos-group
into the DSCP on its output towards CE1. With PHP the re-marking would not arrive (section 2.6), so XR01 advertises
explicit null.

The configuration falls into three chunks, which act on a packet from CE2 to site 1 in this order. ① is LDP
configuration: it changes what P1 does before any packet comes. ② and ③ are QoS policies that act on a packet passing
through XR01, on input and then on output. The numbers in the figure are the numbers in the notes of the configuration
below; rest the pointer on a number in the figure (or tap it on a phone) to see that chunk of the configuration.

:::walk
legend: "Packets on the wire: outer label first; tc is a label's EXP. Orange: a mark that was changed."
rows:
  - {node: CE2, kind: host, say: ["~Sends voice marked EF"]}
  - {wire: "[[IP DSCP EF]]"}
  - {node: PE2, say: ["~Input CE-IN puts EXP 5 on EF and pushes two labels", "_(PE2's configuration in section 3.2)"]}
  - {wire: "[[=18 tc 5]] [[=24007 tc 5]] [[IP EF]] _outer: to XR01; inner: VRF A's route"}
  - {node: P1, say: ["~Re-marks the outer EXP from 5 to 0 (demotion in the core; 2.6)", "Swaps the outer label for label 0 instead of popping it (because of ①)"]}
  - {wire: "[[!0 tc 0]] [[=24007 tc 5]] [[IP EF]] ^← the re-marked 0 arrives", gap: 16}
  - panel: XR01
    sub: egress PE
    items:
      - ref: 1
        to: P1
        code: mpls ldp … label local advertise explicit-null
        say: ["Asks P1 to hand packets for XR01 over with label 0 on (no PHP).", "It is in place before any packet comes."]
      - ref: 2
        head: "**Input on Gi0/0/0/0 (to P1)** `service-policy input CORE-IN`"
        say: ["Classes are checked from the top and the first match acts. It reads the top label's EXP"]
        match:
          - ["class EXP5  match mpls experimental topmost 5", false, no match]
          - ["class EXP0  match mpls experimental topmost 0", true, "match → `set qos-group 7`"]
      - say: ["~Pops the labels and picks the exit (Gi0/0/0/1) from VRF A's routes. This is not QoS", "[[IP EF]] [[~qos-group 7]] internal to the router; never on the wire"]
      - ref: 3
        head: "**Output on Gi0/0/0/1 (to CE1)** `service-policy output CE-OUT-UNIFORM`"
        match:
          - ["class QG7  match qos-group 7", true, "match → `set dscp default`"]
  - {wire: "[[!IP DSCP 0]] ^The core's demotion shows to the customer (uniform)"}
  - {node: CE1, kind: host, say: ["~Reaches site 1 with DSCP 0"]}
  - aside: "Without ① (PHP stays)"
    say: ["~P1 pops the outer label → [[=24007 tc 5]] [[IP EF]] ~→ ② reads 5 → ③ no match → CE1 gets EF"]
:::

:::config fold XR01 — copy the core's EXP back into the customer's DSCP at the egress (uniform)
mpls ldp
 address-family ipv4
  label
   local
    advertise
     explicit-null                            ## ① Ask for my loopback to be handed over with label 0 still on (no PHP)
!
class-map match-any EXP5                      ## ②
 match mpls experimental topmost 5            ## On the core-facing input, the EXP of the top label can be read
 end-class-map
class-map match-any EXP0                      ## ②
 match mpls experimental topmost 0
 end-class-map
!
policy-map CORE-IN                            ## ②
 class EXP5
  set qos-group 5                             ## Move the EXP read into the router's internal mark (input only)
 !
 class EXP0
  set qos-group 7
 !
 end-policy-map
!
class-map match-any QG7                       ## ③
 match qos-group 7                            ## Readable on output only
 end-class-map
!
policy-map CE-OUT-UNIFORM                     ## ③
 class QG7
  set dscp default                            ## What the core set to 0 goes to the customer as 0 too
 !
 end-policy-map
!
interface GigabitEthernet0/0/0/0              ## ② The interface to P1
 service-policy input CORE-IN
!
interface GigabitEthernet0/0/0/1              ## ③ The interface to CE1
 service-policy output CE-OUT-UNIFORM
:::

Before explicit null is advertised, the packets reach XR01 with only the inner label (`label 24007, tc 5`); CORE-IN
counts them as EXP 5, and CE1 receives them still EF. After it is advertised, they arrive with
`label 0 (IPv4 explicit NULL), tc 0` on top, are counted in the EXP0 class, and reach CE1 with DSCP 0.

```console
# On the P1 → XR01 link (after XR01 advertised explicit null)
MPLS (label 0 (IPv4 explicit NULL), tc 0, ttl 253) (label 24007, tc 5, [S], ttl 254) IP (tos 0xb8, ttl 254, proto ICMP (1)) 10.46.0.2 > 10.46.0.1: ICMP echo request, id 9, seq 0
# On the XR01 → CE1 link
IP (tos 0x0, ttl 252, proto ICMP (1)) 10.46.0.2 > 10.46.0.1: ICMP echo request, id 9, seq 0
```

For pipe, leave out the `set dscp` on output and choose the exit queue by qos-group. For short pipe, the CORE-IN input
policy is not needed; choose the queue on output by the customer's DSCP (`match dscp`). Building the queues is covered
on the page *Policing and shaping*.

### 3.4 Checking it

```console
RP/0/RP0/CPU0:XR01#show qos interface GigabitEthernet0/0/0/1 input
Interface: GigabitEthernet0_0_0_1 input
Bandwidth configured: 1000000 kbps Bandwidth programmed: 1000000 kbps
...
Policy: CE-IN Total number of classes: 3
----------------------------------------------------------------------
Level: 0 Policy: CE-IN Class: VOICE
Bandwidth: 0 kbps, BW sum for Level 0: 0 kbps, Excess Ratio: 0
QueueID: 25 (Port Default)
Child Mark: set exp-imp 5   set qos-grp 5
...
RP/0/RP0/CPU0:XR01#show policy-map interface GigabitEthernet0/0/0/1 input
...
Class VOICE
  Classification statistics          (packets/bytes)     (rate - kbps)
    Matched             :                   3/354                  0
    Transmitted         : N/A
    Total Dropped       :                   0/0                    0
```

- `show qos interface` shows how the policy went into the hardware (on XRv 9000, the data plane). The `Child Mark:`
  lines are the marks set.
- `show policy-map interface` shows what was counted per class. ★On XRv 9000 these counts rose **10 to 30 seconds
  after** the traffic. Looked at straight away, they stay at 0.
- The EXP inside the core is easiest to count on a P router (in this lab, P1's `COUNT-EXP`; IOS XE `show policy-map
  interface Ethernet0/0 input`).

:::try
Check in the lab how the EXP is copied when there is no policy. Do it after Task M12-1, and always put things back at
the end.

1. On XR01, remove the input policy from the interface towards CE1 (commit `no service-policy input <name>`).
2. On P1, run `clear counters Ethernet0/0`; on CE1, run `ping 10.21.2.1 source Loopback21 repeat 10`.
3. On P1, look at `show policy-map interface Ethernet0/0 input`. Which class counted the business packets (AF21)?
4. Put XR01's policy back.

An example result: `COUNT-EXP`'s EXP5, EXP3, EXP1 and EXP0 all stayed at 0, and `class-default` rose by 11 (the ten
packets and one other). The top three bits of AF21, 2, were copied into the EXP, which matched none of P1's counting
classes.
:::

### 3.5 Pitfalls

- **At most two kinds of mark per class**: XRv 9000 refused to commit, with `only two mark types are allowed per class`,
  when a policer with `set dscp` for the excess was added to a class that already set an EXP and a qos-group (the
  ASR 9000 guide, too: "Choose only two set commands per class"). The marks in a policer's actions count.
- **qos-group is set on input and read on output**: it cannot be done the other way round. To copy the EXP into the DSCP
  at an egress PE takes two policies, an input one and an output one.
- **PHP erases a re-marking**: to use a re-marking from the core at the egress, use explicit null (section 2.6).
- **The counters lag**: wait about half a minute before you check (section 3.4).

## Practice

Do Task M12-1 in lab **XRT-14**. XR01 is IOS XRv 9000, so the lab takes about ten minutes to build.

<p class="tolab"><a href="/_learn?id=XRT-14">Open lab XRT-14 in the workspace</a> — <a href="d1-m12-practice.html">Task M12-1</a></p>

:::note
The output on this page was taken on IOS XRv 9000 26.1.1 (XR01), IOS XRd 26.1.1 (RR1) and IOS XE 17.15 on IOL (the
other routers).
Sources: RFC 2474 (sections 3 and 4), RFC 2475 (section 2), RFC 2597 (sections 2 and 6), RFC 3246 (section 2), RFC 1633,
RFC 2205, RFC 3270 (sections 1.2, 1.3 and 2.6), RFC 3443 (section 3), RFC 5462. The ASR 9000 Modular QoS Configuration Guide
and Modular QoS Command Reference (IOS XR 24.x: default marking, the directions of qos-group and discard-class, the number
of set actions per class, the table of the three MPLS QoS modes and the egress PE examples), the ASR 9000 MPLS Command
Reference (`mpls ip-ttl-propagate disable`, LDP `explicit-null`), and the Cisco TAC document "DiffServ Tunneling Modes for
MPLS Networks" (47815). All checked in November 2026. The following come from measurements on the PoC board (the same
shape as XRT-14): the EXP with no policy (on both XR01 and PE2), the re-marking lost at PHP, the hand-over with explicit
null, the uniform egress, TTL, the counter lag, and the number of marks per class (the wire was captured on CML links).
:::
