# M11 — Q-in-Q

Each E-Line so far carried one of the customer's VLANs. This page carries several of the customer's VLANs together on
one E-Line, by putting one more tag, the provider's, outside the customer's tag. This is **Q-in-Q** (IEEE 802.1ad). The
lab is still XRT-11; Task M11-5 belongs to this page.

## 1. What it is good for

### 1.1 The trouble with selling one E-Line per VLAN

Customer B uses VLANs 10 and 20 inside its company and wants to stretch them, as they are, between site 1 and site 3.
With one E-Line per VLAN, every VLAN the customer adds means another AC and cross-connect on both PEs. Orders and work
pile up, and the provider's configuration keeps growing for reasons inside the customer's company.

### 1.2 Stacking the tags

The customer's equipment keeps its own VLAN tag (the **C-VLAN**, customer VLAN) and puts one more tag outside it, the
one agreed with the provider (the **S-VLAN**, service VLAN). The PE picks the E-Line by the outer tag only and does not
touch the inner tag. The customer can add VLANs freely, and the provider needs one configuration per S-VLAN.

IEEE 802.1ad (provider bridges) sets the kind (TPID) of the outer tag to 0x88a8. Older implementations use 0x8100 for
the outer tag too, as for the inner one, and "Q-in-Q" is used for both forms. The CEs of this lab (IOL) put an outer tag
of 0x8100.

## 2. How it works

### 2.1 Which frames an AC picks

The `encapsulation` of an AC sub-interface sets which frame forms it picks. With the CE sending a single tag of 500,
double tags of 500/10 and 500/20, and 500/30 to be added later, each form picks the following.

| `encapsulation` | 500 only (single) | 500/10, 500/20 | 500/30 |
|---|---|---|---|
| `dot1q 500` | Picks | Picks | Picks |
| `dot1q 500 exact` | Picks | Does not | Does not |
| `dot1q 500 second-dot1q 10` | Does not | Picks 10 only | Does not |
| `dot1q 500 second-dot1q 10,20` | Does not | Picks | Does not |
| `dot1q 500 second-dot1q any` | Does not | Picks | Picks |

IOS XR's `encapsulation dot1q 500` picks a frame whose outer tag is 500 whether or not an inner tag follows. The form
that picks double-tagged frames only, whatever the inner tag, is `second-dot1q any`. A frame that matches none of them
enters no AC and is dropped.

### 2.2 One hop at a time: CEB1 to CEB3 (inner VLAN 10)

:::topo
nodes:
  CEB1: [0, 1]
  XR01: [1.6, 1]
  XR03: [4.4, 1]
  CEB3: [6, 1]
links:
  - [CEB1, XR01, "tag 500 | tag 10 | IP"]
  - [XR01, XR03, "labels | tag 10 | IP"]
  - [XR03, CEB3, "tag 500 | tag 10 | IP"]
:::

1. XR01's AC (`dot1q 500 second-dot1q any`, `pop 1`) removes only the outer tag, 500. The inner tag, 10, stays.
2. The frame, still with inner tag 10, goes to XR03 on the labels of EVPN-VPWS (previous page).
3. XR03's AC puts the outer tag 500 back on the way out (`symmetric`). The frame reaches CEB3 double-tagged, 500/10.

The inner tag is never looked at inside the provider's network. VLAN 20, and VLAN 30 added later, cross the same E-Line
in the same way.

## 3. IOS XR configuration

### 3.1 Where the configuration goes

:::config fold XR01 (IOS XR) — an E-Line that carries S-VLAN 500 whatever the inner tag
interface GigabitEthernet0/0/0/3.500 l2transport
 encapsulation dot1q 500 second-dot1q any          ## pick double-tagged frames with outer 500 (any inner tag; not single-tagged 500)
 rewrite ingress tag pop 1 symmetric               ## remove the outer tag only; the customer's inner tag is carried
!
l2vpn
 xconnect group CUST-B
  p2p B-500
   interface GigabitEthernet0/0/0/3.500
   neighbor evpn evi 500 target 3 source 1
   !
  !
 !
!
:::

XR03 has the same form, with `target 1 source 3`. With no `rewrite` at either end, carrying both tags as they are, it
also works; then the outer tags at the two ends must be the same number.

To take an outer tag of 802.1ad's 0x88a8, use `encapsulation dot1ad`. IOS XRv 9000 commits the following forms (this
lab has no CE that sends 0x88a8, so they are shown for the syntax only).

:::config IOS XR — when the outer tag is 802.1ad (syntax checked only)
interface GigabitEthernet0/0/0/2.401 l2transport
 encapsulation dot1ad 401 dot1q 10                 ## outer = 401 in 0x88a8, inner = 10 in 0x8100
 rewrite ingress tag pop 1 symmetric               ## remove the outer tag only
!
interface GigabitEthernet0/0/0/2.403 l2transport
 encapsulation dot1q 403                           ## pick single-tagged 403
 rewrite ingress tag translate 1-to-2 dot1ad 500 dot1q 403 symmetric   ## rewrite it to two tags, with 500 in 0x88a8 outside
!
:::

### 3.2 Reading it, and the trap

Picking the wrong forms does not take the E-Line DN. `show l2vpn xconnect` stays UP; only the range of frames carried is
different. To check it, send from the CE both the forms that must be carried and the forms that must not. That is why
the CEs of Task M11-5 have addresses for single-tagged 500 and for VLAN 30.

:::try
See what is carried without `second-dot1q any`. Do this after Task M11-5.

1. Change the `.500` ACs on XR01 and XR03 to `encapsulation dot1q 500` (no `second-dot1q`) and commit.
2. From CEB1, run `ping 172.31.50.3` (single tag) and `ping 172.31.51.3` (inner 10).
3. Put `second-dot1q any` back, commit, and run them again.

An example result: without `second-dot1q`, both the single-tagged 500 and inner 10 got through. With `any` back, the
single tag did not get through, and inner 10 did.
:::

## 4. Command names

| On IOS XE | On IOS XR |
|---|---|
| `encapsulation dot1Q 500 second-dot1q 10` on a router sub-interface | `encapsulation dot1q 500 second-dot1q 10` on an `l2transport` sub-interface |
| `encapsulation dot1q 500 second-dot1q any` in a `service instance` | `encapsulation dot1q 500 second-dot1q any` |
| `encapsulation dot1ad 500 dot1q 10` in a `service instance` | `encapsulation dot1ad 500 dot1q 10` |
| `switchport mode dot1q-tunnel` on a switch port | (taken by the `encapsulation` of the E-Line's AC) |

## Practice

In lab **XRT-11**, work through Task M11-5. Then read on: the supplement takes up E-LAN, multihoming and Ethernet OAM,
which this lab's XR cannot run, in lab XRT-12, and the appendix covers E-Tree, G.8032 and 802.1ah.

<p class="tolab"><a href="/_learn?id=XRT-11">Open lab XRT-11 in the workspace</a> — <a href="b5-m11-practice-3.html">Tasks</a></p>

:::note
Sources: L2VPN and Ethernet Services Configuration Guides for the NCS 5500 and the ASR 9000, IOS XR 25.x (2025;
configuring virtual LANs, the carrier Ethernet model, rewrite restrictions). IEEE 802.1ad. All checked in November 2026.
The following come from measurements in lab XRT-11 and its PoC: the frame forms each `encapsulation` picks, carrying
without rewrite, and the 802.1ad syntax being accepted.
:::
