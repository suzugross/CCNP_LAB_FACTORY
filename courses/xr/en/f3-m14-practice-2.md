# M14 — Practice 2: SSM and bidirectional PIM

These are the tasks of lab **XRT-16**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M14 — Multicast

### Task M14-3
<p class="tolab"><a href="/_learn?id=XRT-16&amp;step=m14t3">Open in the lab workspace</a> — Read: <a href="f2-m14-ssm-bidir.html#s2-1">2.1 SSM: the receiver names the source</a> · <a href="f2-m14-ssm-bidir.html#s2-2">2.2 SSM on the board: no RP, no Register</a> · <a href="f2-m14-ssm-bidir.html#s2-3">2.3 The SSM range</a> · <a href="f2-m14-ssm-bidir.html#s3-1">3.1 SSM: the default range and a wider one</a> · <a href="f2-m14-ssm-bidir.html#s3-2">3.2 Checking SSM</a></p>


A second service uses source-specific multicast: the set-top box names both the channel and its source.

- Treat 232.0.0.0/8 and 239.232.0.0/16 as SSM ranges on every router (PE1, PE2, P1, PE3 and PE4).
- A receiver that names SRC1 as the source must receive a channel in either range. A receiver that joins a group in
  these ranges without naming a source must receive nothing.
- Use IGMP version 3 on every router interface that faces hosts.

### Task M14-4
<p class="tolab"><a href="/_learn?id=XRT-16&amp;step=m14t4">Open in the lab workspace</a> — Read: <a href="f2-m14-ssm-bidir.html#s2-4">2.4 Bidirectional PIM: one tree, packets go both ways</a> · <a href="f2-m14-ssm-bidir.html#s2-5">2.5 The designated forwarder</a> · <a href="f2-m14-ssm-bidir.html#s3-3">3.3 Bidirectional PIM</a> · <a href="f2-m14-ssm-bidir.html#s3-4">3.4 When two static RPs cover the same group</a> · <a href="f2-m14-ssm-bidir.html#s3-5">3.5 Checking bidirectional PIM</a></p>


A conferencing service lets every site send to all the others.

- Use bidirectional PIM for 239.48.0.0/16, with PE3's Loopback0 (10.255.0.3) as the RP, on every router.
- Any host may send to a group in 239.48.0.0/16, and every host that joined it must receive it.
- No router may keep per-source state for these groups.
