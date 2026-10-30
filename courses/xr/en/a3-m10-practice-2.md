# M10 — Practice 2: TI-LFA

These are the tasks of lab **XRT-10**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M10 — Segment Routing

### Task M10-3
<p class="tolab"><a href="/_learn?id=XRT-10&amp;step=m10t3">Open in the lab workspace</a> — Read: <a href="a2-m10-ti-lfa.html#s1-1">1.1 From a failed link to recovery</a> · <a href="a2-m10-ti-lfa.html#s2-2">2.2 Adding one waypoint</a> · <a href="a2-m10-ti-lfa.html#s2-3">2.3 Choosing the waypoint: P space and Q space</a> · <a href="a2-m10-ti-lfa.html#s2-5">2.5 Configuration</a> · <a href="a2-m10-ti-lfa.html#s4">4. Microloops</a></p>


Losing PRIMARY or BACKUP must not wait for IS-IS to compute a new path.

- On both core links of XR01, make XR01 compute, ahead of time, a backup path for every IS-IS prefix that it reaches
  over the link, so that it can switch to it as soon as the link fails (link protection).
- RT01's loopback has no loop-free alternate in the plain sense: the backup must use segment routing to reach it.
- While the network converges after a link goes up or down, XR01 must avoid the temporary loops that the routers'
  different update times can cause, using segment routing.
