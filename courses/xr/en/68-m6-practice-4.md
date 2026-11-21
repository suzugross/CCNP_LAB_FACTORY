# M6 — Practice 4: prefix limits, dampening and aggregation

These are the tasks of lab **XRT-17**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M6 — BGP (supplement)

### Task M6-9
<p class="tolab"><a href="/_learn?id=XRT-17&amp;step=m6t9">Open in the lab workspace</a> — Read: <a href="67-m6-limit-damp-agg.html#s2-1">2.1 The prefix limit</a> · <a href="67-m6-limit-damp-agg.html#s3-1">3.1 The maximum-prefix configuration</a> · <a href="67-m6-limit-damp-agg.html#s3-4">3.4 Reading the output, and pitfalls</a></p>


Prevent a configuration mistake at the customer from flooding PE1 with routes.

- PE1 must accept at most four IPv4 unicast routes from CE1, and log a warning when the number reaches three.
- When the number exceeds four, PE1 must tear down the session with CE1 and re-establish it automatically after two minutes.

### Task M6-10
<p class="tolab"><a href="/_learn?id=XRT-17&amp;step=m6t10">Open in the lab workspace</a> — Read: <a href="67-m6-limit-damp-agg.html#s2-2">2.2 Dampening: penalty and half-life</a> · <a href="67-m6-limit-damp-agg.html#s2-3">2.3 Aggregation, and suppressing the more specific routes</a> · <a href="67-m6-limit-damp-agg.html#s3-2">3.2 The dampening configuration</a> · <a href="67-m6-limit-damp-agg.html#s3-3">3.3 The aggregation configuration</a> · <a href="67-m6-limit-damp-agg.html#s3-4">3.4 Reading the output, and pitfalls</a></p>


- PE2 must use route flap dampening for the routes learned from X1. Use a half-life of 10 minutes and the default values for the
  others.
- PE2 and PE3 must advertise the customer addresses 192.168.0.0/22 to X1 and X2 as one route, and must not advertise the individual
  routes inside it to X1 and X2.
