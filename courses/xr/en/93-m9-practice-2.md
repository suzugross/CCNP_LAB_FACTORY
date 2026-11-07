# M9 — Practice 2: the route reflector and AS override

These are the tasks of lab **XRT-09**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M9 — L3VPN

### Task M9-2
<p class="tolab"><a href="/_learn?id=XRT-09&amp;step=m9t2">Open in the lab workspace</a> — Read: <a href="90-m9-l3vpn.html#s3-4">3.4 Route-target filtering</a> · <a href="92-m9-rr-same-as.html#s2-1">2.1 A VPNv4 route reflector keeps everything</a> · <a href="92-m9-rr-same-as.html#s2-2">2.2 A client per address family</a> · <a href="92-m9-rr-same-as.html#s2-4">2.4 The AS path check, and AS override</a> · <a href="92-m9-rr-same-as.html#s3-1">3.1 The route reflector</a> · <a href="92-m9-rr-same-as.html#s3-2">3.2 AS override</a></p>


After Task M9-1, the sites of the same customer still cannot reach each other. A colleague set XR02 up as the VPNv4
route reflector of XR01 and RT02 under change CHG-1201, and reported that XR02 holds the routes of both provider edges.

- Make the LANs of the two sites of each customer reach each other in both directions: 10.101.1.0/24 and
  10.101.2.0/24, 10.102.1.0/24 and 10.102.2.0/24.
- Customers A and B must not reach each other.
- You may change XR01 and XR02. Do not change the CEs or RT02, and do not create a VPNv4 session between XR01 and RT02.
