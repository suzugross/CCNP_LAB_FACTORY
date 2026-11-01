# M11 supplement — Practice 5: EVPN multihoming

These are the tasks of lab **XRT-12**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M11 supplement — E-LAN, multihoming and Ethernet OAM

### Task M11-8
<p class="tolab"><a href="/_learn?id=XRT-12&amp;step=m11t8">Open in the lab workspace</a> — Read: <a href="b9-m11-multihoming.html#s2-1">2.1 The Ethernet segment identifier</a> · <a href="b9-m11-multihoming.html#s2-2">2.2 Route type 4: the PEs find each other and elect a forwarder</a> · <a href="b9-m11-multihoming.html#s2-3">2.3 Route type 1: aliasing</a> · <a href="b9-m11-multihoming.html#s3-1">3.1 The configuration</a> · <a href="b9-m11-multihoming.html#s3-2">3.2 LACP: two PEs, one partner</a></p>


Site 4 is a switch, SW1, attached to both XE1 and XE2 for resilience. SW1 bundles its two links with LACP (active) and
uses VLAN 200 on the bundle (172.31.200.4).

- Connect site 4 to the E-LAN of Task M11-7.
- Both links of SW1 forward traffic at the same time. SW1 must see XE1 and XE2 as one LACP partner and bundle both
  links.
- The Ethernet segment of site 4 has the identifier **0000.0000.0000.0000.0401** (type 0).
- XE3 must be able to send site 4's traffic to either XE1 or XE2.
