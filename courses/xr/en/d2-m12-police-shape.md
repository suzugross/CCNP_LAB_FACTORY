# M12 — Policing and shaping

The previous page marked the packets to tell the core which class they belong to. This page uses those marks to decide
quantities: what to do with traffic beyond the contracted rate (policing), and how to line packets up at a busy exit
(shaping and queuing). It covers 4.5.b of the blueprint (congestion avoidance, traffic policing and shaping).

## 1. What it is good for

### 1.1 The problem: contracted rates and busy exits

Customer A has a contract for its business traffic (AF11 or AF21) such as "up to 256 kbps normally, up to 512 kbps when
there is room". The customer's CE can send at line rate (a 1 Gbps port, say), so unless the provider holds the excess
back at the entrance, one customer can use up the core and take the share of the others.

There is a problem in the other direction too. The exit towards a customer's site may be a 1 Gbps port with only a
2 Mbps contract behind it. If the provider sends at 1 Gbps, packets get dropped further on (in the customer's access
equipment, say) with no judgement about which to drop: voice and bulk data alike.

### 1.2 What came before

- **Make the contract the line rate**: for a 2 Mbps contract, provide a 2 Mbps line, and the physical speed is the
  limit. But every change of contract means a new line, and several customers cannot share one fat line.
- **Drop everything over the limit at the entrance**: dropping all traffic beyond the contract does protect the core.
  But TCP cuts its rate sharply after a few losses, so there is no gentle treatment such as "carry a little extra, and
  drop it first only when things are busy".

### 1.3 The answer of policing and shaping

- **Policing**: measures the incoming rate and colours the traffic in three (or two): within the contract, a little
  over, far over. For each colour it decides "carry as it is", "re-mark and carry" or "drop". It never makes packets
  wait, so it adds no delay, but the excess is dealt with on the spot.
- **Shaping**: evens the outgoing rate to a set value. The excess waits in a queue and is sent a little later. It delays
  instead of dropping, which TCP prefers, but delay goes up.
- **Queues and priority**: build several queues at the exit and send the voice queue first (a priority queue). It is
  the traffic that is not in a hurry that waits.

## 2. How it works

### 2.1 The token bucket: single rate, two colours

A policer measures the rate with a bucket of tokens. Tokens flow into the bucket at the contracted rate (CIR, Committed
Information Rate), and the bucket holds up to the burst (Bc). When a packet arrives, it **conforms** if there are tokens
for its length, and uses them up; if not, it **exceeds**.

- A full bucket means up to Bc may be sent at once (a momentary clump is allowed).
- Over a long time, the conforming amount is CIR × time + Bc.

On XR01, a 64 kbps policer was applied to the AF11 class, and 500-byte pings were sent back to back from CE1. Of the
876 packets counted, 5 conformed and the other 871 exceeded and were dropped.

```console
RP/0/RP0/CPU0:XR01#show policy-map interface GigabitEthernet0/0/0/1 input
...
Class BULK
  Classification statistics          (packets/bytes)     (rate - kbps)
    Matched             :                 876/453768               0
    Transmitted         : N/A
    Total Dropped       :                 871/451178               0
  Policing statistics                (packets/bytes)     (rate - kbps)
    Policed(conform)    :                   5/2590                 0
    Policed(exceed)     :                 871/451178               0
    Policed(violate)    :                   0/0                    0
    Policed and dropped :                 871/451178
```

### 2.2 Two rates, three colours

A second bucket makes three colours (the trTCM of RFC 2698). The first fills at the contracted rate (CIR), the second
at the peak rate (PIR, Peak Information Rate).

| Colour | Condition | Usual treatment |
|---|---|---|
| Conform | The CIR bucket has tokens | Carry as it is |
| Exceed | The CIR bucket is empty, the PIR bucket has tokens | Re-mark to a higher drop precedence and carry (AF11 → AF12) |
| Violate | Both buckets are empty | Drop |

The re-marked AF12 stays in the same class (AF1), so the order is kept; it is only dropped before AF11 when the core or
the exit is busy. Sent the same way with a CIR of 64 kbps and a PIR of 1 Mbps, XR01 counted 5 conforming, 41 exceeding
and 789 violating packets, and CE2 at site 2 received 5 packets as AF11 and 41 as AF12. The counts agree packet for
packet.

```console
RP/0/RP0/CPU0:XR01#show policy-map interface GigabitEthernet0/0/0/1 input
...
    Policed(conform)    :                   5/2590                 0
    Policed(exceed)     :                  41/21238                0
    Policed(violate)    :                 789/408702               0
    Policed and dropped :                 789/408702
```

Over the same time, the counting-only policy on CE2's input counted 5 packets in D-AF11 and 41 in D-AF12.

### 2.3 Shaping: wait and even out

A shaper measures the rate with the same kind of token bucket, but a packet without enough tokens is not dropped; it
waits in a queue. When tokens have built up, it is sent. However fast the traffic comes in, it never goes out faster
than the set rate.

A 100 kbps shaper was applied to the output of XR01 towards CE1, and 1000-byte packets were sent from CE2 at about
4 Mbps. Of 11878 packets, XR01 sent 205 to CE1 (about 76 kbps); the rest overflowed the queue and were dropped at its
tail.

```console
RP/0/RP0/CPU0:XR01#show policy-map interface GigabitEthernet0/0/0/1 output
...
Class class-default
    Matched             :               11878/12073804             0
    Transmitted         :                 205/190690               0
    Total Dropped       :               11673/11883114             0
  Policy CE-OUT-CHILD Class class-default
...
      Taildropped(packets/bytes)           : 11673/11883114
```

Waiting adds delay. A 1000-byte ping that normally takes 2 ms took 63 ms on average and 82 ms at most. Sending
1000 bytes at 100 kbps takes 80 ms, so the ping waited for about one packet in the queue (section 2.7).

### 2.4 Queues and priority: LLQ

Build a queue per class at the exit. Packets in the **priority queue** (LLQ in IOS, `priority level 1` in XR) are sent
before those in the other queues, so they do not wait even when the exit is busy. The other side of it: if the priority
queue used up the exit, no other queue could send at all. So a priority queue always gets an upper limit with a policer
(the ASR 9000 guide, too: "you must configure a policer to limit the priority traffic").

The other classes are given shares of what is left of the exit (`bandwidth remaining`). Classes without a share split
what is left equally.

### 2.5 Hierarchical QoS

"Shape each customer to 2 Mbps, and within those 2 Mbps send voice first" takes a policy in two tiers.

- **Parent**: shapes all packets (`class-default`) to 2 Mbps. Give the parent only `class-default`. A packet enters only
  one class at each level, so a packet that matches another class in the parent never passes through the child and
  never enters the priority queue (IOS XRv 9000 commits such a parent without an error).
- **Child**: builds the queues per class (the priority one and the rest) within the 2 Mbps the parent sends. Write
  `service-policy <child>` under the parent's `class-default` (without the `input`/`output` keyword).

The parent decides the amount and the child decides the order. When one port carries many customers on sub-interfaces,
put a parent on each sub-interface to give each customer its contracted rate.

### 2.6 Congestion avoidance: WRED

If a queue is left to fill up and then drops at its tail (tail drop), all the TCP sessions through that queue lose
packets at once, slow down at once and come back at once. The link is used in waves, and its average use goes down.

**WRED** (Weighted Random Early Detection) starts dropping a few packets at random as soon as the queue starts to grow.
Once the queue passes a minimum threshold it starts to drop, and the closer it gets to the maximum threshold, the higher
the drop probability. "Weighted" means the thresholds differ by mark. With a lower threshold for AF12 than for AF11,
AF12 is dropped first when things start to get busy (RFC 2597, section 4, gives RED as an example of how to implement
the AF drop precedences). WRED works only in a class that has a queue, so the same class needs `shape`, `bandwidth` or
`bandwidth remaining`.

### 2.7 Key points, and what IOS XRv 9000 showed

- Policing **measures, colours and acts on the spot** (no delay). Shaping **makes packets wait and evens them out**
  (more delay).
- The three colours are "carry, re-mark and carry, drop". Re-marking stays within one AF class (the order is kept).
- A priority queue always gets a policer as its upper limit. A per-customer contract is built in two tiers: the parent
  shapes, the child gives priority.

On IOS XRv 9000 26.1.1 (XR01 in this lab), the following came out. The lab's checks are built around it.

| Item | Result |
|---|---|
| Policers (single rate two colours, two rates three colours, re-marking) | Work; the counts agree with what the other CE counted |
| Shaper and priority queue | The rate is held down, and the priority class counts. But the queue holds only about one packet (the shown Q-Limit is 0) |
| WRED | Accepted, but the drops always show as 0, so its effect cannot be checked |
| Rate without a licence | The documentation says "limited to 200 kbps"; in this lab about 4 Mbps went through |
| Counters | Rise 10 to 30 seconds late |

So this lab does not judge priority by differences in delay. It checks the shape of the policy (`show qos interface`)
and the marks that the other CE counted. For WRED, know how it works and how it is written.

## 3. Building it in IOS XR

### 3.1 Policers

For a single rate and two colours, write `police rate` and the action for each colour.

:::config XR01 — hold bulk data to 64 kbps (single rate, two colours)
policy-map CE-IN
 class BULK
  set mpls experimental imposition 2
  police rate 64 kbps                         ## The contracted rate: bps, kbps, mbps, gbps or pps; the minimum is 64 kbps
   conform-action transmit                    ## Conforming traffic goes as it is
   exceed-action drop                         ## Exceeding traffic is dropped
  !
 !
 end-policy-map
:::

For two rates and three colours, add `peak-rate` and give the exceed and violate actions separately. A mark in the
exceed action counts towards the class's marks too (at most two kinds per class; section 3.5 of the previous page).

:::config fold XR01 — give bulk data a committed and a peak rate (two rates, three colours)
policy-map CE-IN
 class BULK
  set mpls experimental imposition 2          ## The first kind of mark
  police rate 64 kbps peak-rate 1 mbps        ## CIR and PIR
   conform-action transmit
   exceed-action set dscp af12                ## The second kind of mark; adding qos-group here too is refused at commit
   violate-action drop
  !
 !
 end-policy-map
:::

Without a burst, XRv 9000 chose 1600 bytes for 64 kbps and 12500 bytes (100 ms) for 1 Mbps (`Burst: … (0 Default)` in
`show qos interface`).

```console
RP/0/RP0/CPU0:XR01#show qos interface GigabitEthernet0/0/0/1 input
...
Level: 0 Policy: CE-IN Class: BULK
...
Policer Profile: 0 (TrTCM)
Conform: 64 kbps (64 kbps) Burst: 1600 bytes (0 Default)
Peak: 1000 kbps (1 mbps) Burst: 12500 bytes (0 Default)
Child Policer Conform: set exp-imp 2
Child Policer Exceed: set exp-imp 2   set dscp 12
Child Policer Violate: DROP
```

`TrTCM` marks two rates and three colours. `set dscp 12` is AF12 in decimal.

### 3.2 Shaping and priority (hierarchical)

The parent shapes to 100 kbps; the child gives EF priority (up to 32 kbps). For the child's remaining class, it sets the
queue length.

The parent and the child are nested by name: the interface points to the parent, and the parent's class-default
points to the child. The figure follows the packets towards site 1; rest the pointer on a number (or tap it on a phone)
to see that part of the configuration.

:::walk
rows:
  - {node: P1, say: ["~Voice (EF) and 1000-byte data for site 1 arrive"]}
  - {wire: "[[IP EF]] [[IP data]] [[IP data]]"}
  - panel: XR01
    sub: exit to site 1 (Gi0/0/0/1 output)
    items:
      - ref: 1
        head: "**Parent** `service-policy output CE-OUT`"
        say: ["The parent has class-default only: every packet enters it and goes to the child"]
        match:
          - ["class class-default", true, "all → `service-policy CE-OUT-CHILD`"]
      - ref: 2
        head: "**Child** `policy-map CE-OUT-CHILD` sorts and queues what the parent hands over"
        match:
          - ["class VOICE  match dscp ef", true, "EF → priority queue"]
          - ["class class-default", true, "data → queue for the rest"]
        then:
          - "[[IP EF]] priority queue (`priority level 1`, capped by `police rate 32 kbps`)"
          - "[[IP data]] [[IP data]] queue for the rest (`queue-limit 20 packets`)"
      - ref: 3
        head: "**The parent's shaper** `shape average 100 kbps`"
        say: ["Sends what the child's queues give, at 100 kbps for the whole exit; the excess waits"]
  - {wire: "[[IP EF]] [[IP data]] _100 kbps in all"}
  - {node: CE1, kind: host}
  - aside: "If the parent has a class other than class-default"
    say:
      - "~A packet that enters that class in the parent skips the child: it never reaches the priority"
      - "~queue and waits in the queue for the rest. The configuration still commits"
:::

:::config fold XR01 — shape the exit to site 1 and send voice first
policy-map CE-OUT-CHILD                       ## ② The child decides the order
 class VOICE
  priority level 1                            ## The priority queue
  police rate 32 kbps                         ## Priority needs an upper limit
  !
 !
 class class-default
  queue-limit 20 packets                      ## The length of the remaining queue
 !
 end-policy-map
!
policy-map CE-OUT                             ## ① The parent decides the amount; class-default only
 class class-default
  shape average 100 kbps                      ## ③ the rate of the whole exit
  service-policy CE-OUT-CHILD                 ## Put the child in, without input/output
 !
 end-policy-map
!
interface GigabitEthernet0/0/0/1              ## ① apply the parent to the output
 service-policy output CE-OUT
:::

```console
RP/0/RP0/CPU0:XR01#show qos interface GigabitEthernet0/0/0/1 output
Interface: GigabitEthernet0_0_0_1 output
Bandwidth configured: 100 kbps Bandwidth programmed: 100 kbps
ANCP user configured: 0 kbps ANCP programmed in HW: 0 kbps
Port Shaper programmed in HW: 100 kbps
Policy: CE-OUT Total number of classes: 3
----------------------------------------------------------------------
Level: 0 Policy: CE-OUT Class: class-default
Bandwidth: 0 kbps, BW sum for Level 0: 0 kbps, Excess Ratio: 1
Shape Info: rate 100 kbps, burst 1250 bytes,
QueueID: N/A
----------------------------------------------------------------------
Level: 1 Policy: CE-OUT-CHILD Class: VOICE
Bandwidth: 0 kbps, BW sum for Level 1: 0 kbps, Excess Ratio: 0
Parent Policy: CE-OUT Class: class-default
QueueID: 32 (Priority 1)
Queue Limit: 0 kbytes
Policer Profile: 0 (Single)
Conform: 32 kbps (32 kbps) Burst: 1600 bytes (0 Default)
...
Level: 1 Policy: CE-OUT-CHILD Class: class-default
...
QueueID: 33 (Priority Normal)
Queue Limit: 5 kbytes (20 packets)
```

The parent's `Shape Info` and the child's `QueueID: 32 (Priority 1)` (the priority queue) and `QueueID: 33 (Priority
Normal)` are the two tiers. `bandwidth`, `priority` and `shape average` cannot be written together in one class (the
ASR 9000 guide).

### 3.3 Writing WRED

WRED is written as `random-detect` in a class that has a queue: `random-detect default` for the default thresholds, or
`random-detect dscp <value> <min> <max>` to split by mark (at most two sets of thresholds per class).

:::config XR01 — WRED by mark on the remaining queue (its effect cannot be checked on XRv 9000)
policy-map CE-OUT-CHILD
 class class-default
  queue-limit 20 packets
  random-detect dscp af11 10 packets 20 packets   ## AF11 starts being dropped at 10 packets and is all dropped at 20
  random-detect dscp default 5 packets 10 packets ## Unmarked traffic starts being dropped earlier
 !
 end-policy-map
:::

XRv 9000 accepts this configuration, but the counts where WRED shows its drops, `RED random drops` and `Taildropped` in
`show policy-map interface`, stayed at 0 (section 2.7).

### 3.4 Writing it in IOS XE

In IOS XE, the differences are the unit of a policer's rates (bps by default) and the way the excess is re-marked.

:::config PE2 (IOS XE) — a two-rate, three-colour policer for business data
policy-map POLICE-DATA
 class DATA
  police cir 256000 pir 512000                ## Written in bps
   conform-action transmit
   exceed-action set-dscp-transmit af22       ## Re-mark and carry
   violate-action drop
:::

Once it is applied, `show policy-map POLICE-DATA` shows `police cir 256000 bc 8000 pir 512000 be 16000`, adding the
default bursts (bc and be, in bytes).

### 3.5 Checking it

| What to look at | Command |
|---|---|
| How the policy went into the router (rates, bursts, queues, actions) | `show qos interface <IF> input`, `output` |
| What was counted per class and per colour | `show policy-map interface <IF> input`, `output` (★wait some tens of seconds) |
| Clearing the counts | `clear qos counters interface <IF> input`, `output` |
| The marks the other end received | A counting-only policy on the other device's input (`COUNT-DSCP` on CE1 and CE2 in this lab) |

:::try
Count the three colours of a policer on both the sending and the receiving side. Do it after Task M12-2 (it changes no
configuration).

1. On XR01, run `clear qos counters interface GigabitEthernet0/0/0/1 input`; on CE2, run `clear counters Ethernet0/0`.
2. On CE1, run `ping 10.21.2.1 source Loopback21 repeat 1000 size 500 timeout 0` (it does not wait for replies, so the
   success rate shows as 0).
3. Look at `show policy-map interface GigabitEthernet0/0/0/1 input` on XR01 straight away, and again 30 seconds later.
   On CE2, look at `show policy-map interface Ethernet0/0 input`.

An example result: looked at straight away, XR01's counts for the DATA class were 0, Matched and every colour alike.
Thirty seconds later they were Matched 924, with 15 conforming, 15 exceeding and 894 violating (dropped). CE2's
`COUNT-DSCP` counted 15 in D-AF21 and 15 in D-AF22, matching XR01's conform and exceed counts.
:::

## Practice

Do Tasks M12-2 and M12-3 in lab **XRT-14**. Task M12-3 combines the egress PE of the previous page (section 3.3) with the
shaping and priority of this page.

<p class="tolab"><a href="/_learn?id=XRT-14">Open lab XRT-14 in the workspace</a> — <a href="d3-m12-practice-2.html">Tasks M12-2 and M12-3</a></p>

:::note
The output on this page was taken on the same board as the previous page.
Sources: RFC 2698 (trTCM), RFC 2597 (section 4), RFC 3246 (section 2). The ASR 9000 Modular QoS Configuration Guide and
Modular QoS Command Reference (IOS XR 24.x: the syntax and units of `police`, the 64 kbps minimum and default burst,
`shape average`, `priority level` and its policer, `bandwidth remaining`, `queue-limit`, `random-detect` and its queue
requirement, the rules for hierarchical policies). The IOS XRv 9000 Installation and Configuration Guide (the Smart
Licensing and data-plane chapters) and the IOS XR 25.1.1 release notes. All checked in November 2026. The following come
from measurements on the PoC board (the same shape as XRT-14): the per-colour counts of the policers and their agreement
with the other CE, the default bursts, the amount and delay through the shaper, the depth of the queue, the WRED counts,
the throughput without a licence, and the counter lag.
:::
