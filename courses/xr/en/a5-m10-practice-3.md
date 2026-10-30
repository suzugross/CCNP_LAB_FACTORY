# M10 — Practice 3: SR policies and the PCE

These are the tasks of lab **XRT-10**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M10 — Segment Routing

### Task M10-4
<p class="tolab"><a href="/_learn?id=XRT-10&amp;step=m10t4">Open in the lab workspace</a> — Read: <a href="a4-m10-sr-policy-pce.html#s1-1">1.1 Same next hop, different paths</a> · <a href="a4-m10-sr-policy-pce.html#s2-1">2.1 Color, end point, candidate paths</a> · <a href="a4-m10-sr-policy-pce.html#s2-2">2.2 Steering by color</a> · <a href="a4-m10-sr-policy-pce.html#s2-3">2.3 On-demand policies</a></p>


RT01 is due for maintenance. Customer A has asked that its traffic from site 1 to site 2 stop crossing the link
between XR01 and RT01 now. Nothing changes for customer B.

- Steer the traffic of customer A from XR01 towards site 2 onto a path that avoids the link PRIMARY. The traffic of
  customer B keeps the shortest path.
- Use the provider's convention: the routes of a service that needs a special path carry the **color 100**.
- The path must be computed by XR01 from the topology. Do not write the hops of the path into the configuration.
- Do not change RT02 or the route reflector.

### Task M10-5
<p class="tolab"><a href="/_learn?id=XRT-10&amp;step=m10t5">Open in the lab workspace</a> — Read: <a href="a4-m10-sr-policy-pce.html#s3-1">3.1 PCE and PCC</a> · <a href="a4-m10-sr-policy-pce.html#s3-2">3.2 Paths that must not meet</a></p>


The provider plans a redundant service that needs two paths from XR01 to RT02 that never share a link. Paths of
this kind are to be computed by a central path computation element.

- Make XR02 a path computation element at its Loopback0 address, using the topology that it learns in IS-IS. XR02
  stays outside the forwarding path.
- On XR01, create two SR policies to RT02 with the colors **201** and **202**. Their paths must be computed by XR02,
  not by XR01, and the two paths must not share any link.
