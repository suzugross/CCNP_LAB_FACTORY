# M11 — Appendix: E-Tree, G.8032 and 802.1ah

This lab's IOS XRv 9000 runs only the E-Line (VPWS) among the L2VPN services, and it has no CFM commands. E-LAN, EVPN
multihoming and Ethernet OAM now have pages of their own in the M11 supplement, practised in lab XRT-12 with Catalyst
8000V routers as the PEs: [E-LAN](b7-m11-e-lan.html), [EVPN multihoming](b9-m11-multihoming.html) and
[Ethernet OAM](bb-m11-ethernet-oam.html). This appendix covers the rest of item 4.2 of the blueprint, which neither lab
builds. The IOS XR forms are shown as Cisco's documents give them.

To try the supplement's services on a Catalyst 8000V of your own: at its default licence level the 8000V has no MPLS
commands at all. Set `license boot level network-advantage addon dna-advantage`, save, and reload (no registration was
needed). In lab XRT-12 the line is in the initial configuration, and the 8000V came up at that level by itself.

## 1. E-Tree

An E-Tree is an E-LAN with roots and leaves. Leaves cannot reach each other; a leaf talks with the roots only. A video
source as the root and each site as a leaf is a typical use. EVPN marks frames that come from a leaf AC and does not send
them out of leaf ACs (RFC 8317). On IOS XR, `etree leaf` on an EVI or a bridge domain makes it a leaf, and one without it
is a root (as Cisco's documents give it).

## 2. G.8032 and 802.1ah

- **G.8032** (ITU-T Ethernet ring protection): on switches joined in a ring, one link (the RPL) is blocked to prevent a
  loop, and opened to go around when another link fails. It aims at switching within 50 ms. A ring needs three switches
  or more, so these labs do not cover it.
- **IEEE 802.1ah** (PBB, provider backbone bridges): wraps the customer's whole frame in a frame with the provider's MAC
  addresses (B-MAC), MAC-in-MAC. Services are told apart by a 24-bit I-SID, past the wall of 4094 VLANs, and the core
  switches need not learn the customers' MACs. Combined with EVPN, it is PBB-EVPN (RFC 7623).
- **E-Access**: an E-Line between a customer and the boundary to another operator's network (the ENNI).

:::note
The labs did not try E-Tree.
Sources: L2VPN and Ethernet Services Configuration Guides for the ASR 9000 and NCS 5500, IOS XR 25.x (2025; E-Tree).
Catalyst 8000V data sheet (2025). RFC 7623, 8317. IEEE 802.1ah. ITU-T G.8032. All checked in November 2026. The licence
level of the 8000V comes from the PoC and from lab XRT-12.
:::
