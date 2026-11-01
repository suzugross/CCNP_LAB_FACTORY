# M11 supplement — Practice 6: Ethernet OAM

These are the tasks of lab **XRT-12**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M11 supplement — E-LAN, multihoming and Ethernet OAM

### Task M11-9
<p class="tolab"><a href="/_learn?id=XRT-12&amp;step=m11t9">Open in the lab workspace</a> — Read: <a href="bb-m11-ethernet-oam.html#s2-1">2.1 Maintenance domains and levels</a> · <a href="bb-m11-ethernet-oam.html#s2-2">2.2 Maintenance associations and MEPs</a> · <a href="bb-m11-ethernet-oam.html#s2-3">2.3 Continuity check: CCMs and the lifetime</a> · <a href="bb-m11-ethernet-oam.html#s2-5">2.5 Y.1731: measuring delay</a> · <a href="bb-m11-ethernet-oam.html#s3-1">3.1 The configuration</a> · <a href="bb-m11-ethernet-oam.html#s3-3">3.3 What goes wrong</a></p>


The provider wants to monitor E-Line 130 (site 1 ⇔ site 3) itself, apart from the customer's traffic, with CFM.

- Use the maintenance domain **PROV** at level **4**, and the maintenance association (service) **E130** for the
  E-Line, whose EVC is `E130`. Put a MEP at each end of the E-Line, on the provider edge's attachment circuit, facing
  the pseudowire. The MEP ID of an end is the number of its site.
- When the E-Line breaks anywhere between XE1 and XE3, both ends must notice within **5 seconds**, even if no
  interface goes down.
- XE1 measures the two-way frame delay of the E-Line to the other end without stopping, with IP SLA operation
  **130** (Y.1731).
