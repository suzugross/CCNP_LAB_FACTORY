# M12 — Practice 2: policing, and the egress PE

These are the tasks of lab **XRT-14**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M12 — Data-plane protection and QoS

### Task M12-2
<p class="tolab"><a href="/_learn?id=XRT-14&amp;step=m12t2">Open in the lab workspace</a> — Read: <a href="d2-m12-police-shape.html#s2-1">2.1 The token bucket: single rate, two colours</a> · <a href="d2-m12-police-shape.html#s2-2">2.2 Two rates, three colours</a> · <a href="d2-m12-police-shape.html#s3-1">3.1 Policers</a> · <a href="d2-m12-police-shape.html#s3-5">3.5 Checking it</a> · <a href="d0-m12-marking.html#s3-5">3.5 Pitfalls</a></p>


In customer A's contract, business traffic (AF21) has a committed rate of 256 kbps and a peak rate of 512 kbps.

- Of the business traffic that XR01 receives from site 1, carry what fits in the committed rate as it is, carry what
  exceeds the committed rate but fits in the peak rate as AF22, and drop what exceeds the peak rate.
- Voice traffic must not be affected by this limit. Keep the behaviour of Task M12-1.

### Task M12-3
<p class="tolab"><a href="/_learn?id=XRT-14&amp;step=m12t3">Open in the lab workspace</a> — Read: <a href="d0-m12-marking.html#s2-5">2.5 The three models: the customer's mark and the provider's mark</a> · <a href="d0-m12-marking.html#s2-6">2.6 PHP and explicit null: where a mark set in the core goes</a> · <a href="d0-m12-marking.html#s3-3">3.3 The egress PE: inherit the EXP</a> · <a href="d2-m12-police-shape.html#s2-4">2.4 Queues and priority: LLQ</a> · <a href="d2-m12-police-shape.html#s2-5">2.5 Hierarchical QoS</a> · <a href="d2-m12-police-shape.html#s3-2">3.2 Shaping and priority (hierarchical)</a></p>


As a precaution against congestion, core router P1 downgrades the business traffic it receives from PE2 (EXP 3) to
EXP 1 (fixed). Customer A wants to see at site 1, in the DSCP, how the core treated its traffic.

- Set the DSCP of the traffic that XR01 sends to site 1 from the EXP that arrived from the core: EF for EXP 5, AF21 for
  3, AF11 for 1 and DSCP 0 for 0.
- Shape the exit towards site 1 to the contracted 2 Mbps. Send voice (what arrived with EXP 5) first, up to 512 kbps.
- Do not change P1 or PE2.
