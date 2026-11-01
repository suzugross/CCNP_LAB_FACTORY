# M11 — Practice 3: Q-in-Q

These are the tasks of lab **XRT-11**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M11 — L2VPN and Carrier Ethernet

### Task M11-5
<p class="tolab"><a href="/_learn?id=XRT-11&amp;step=m11t5">Open in the lab workspace</a> — Read: <a href="b4-m11-qinq.html#s2-1">2.1 Which frames an AC picks</a> · <a href="b4-m11-qinq.html#s2-2">2.2 One hop at a time: CEB1 to CEB3 (inner VLAN 10)</a> · <a href="b4-m11-qinq.html#s3-1">3.1 Where the configuration goes</a> · <a href="b4-m11-qinq.html#s3-2">3.2 Reading it, and the trap</a></p>


Customer B wants to carry its own VLANs 10 and 20 between site 1 and site 3, as they are. The customer's equipment
sends them with an outer tag of **500**, the tag agreed with the provider, outside its own VLAN tag (Q-in-Q).

- Carry the frames of VLANs 10 and 20 inside outer tag 500 between site 1 and site 3 on one E-Line, in EVPN instance
  **500**. The CEs use 172.31.51.0/24 on VLAN 10 and 172.31.52.0/24 on VLAN 20.
- When the customer adds more of its own VLANs inside outer tag 500 later, the E-Line must carry them without any
  change on the provider side.
- Frames that have only the outer tag 500 (no inner tag) must not be carried on this E-Line. The CEs have the
  addresses 172.31.50.0/24 for checking this.
