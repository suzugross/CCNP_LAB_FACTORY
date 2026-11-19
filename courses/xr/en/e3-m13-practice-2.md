# M13 — Practice 2: gNMI and telemetry

These are the tasks of lab **XRT-15**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M13 — Automation and assurance

### Task M13-3
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t3">Open in the lab workspace</a> — Read: <a href="e15-m13-certificates.html#s2-4">2.4 The CA: where trust starts</a> · <a href="e15-m13-certificates.html#s2-5">2.5 The four checks</a> · <a href="e15-m13-certificates.html#s2-6">2.6 Mutual TLS, and who plays which part on each line</a> · <a href="e15-m13-certificates.html#s3-3">3.3 Self-signed certificates, and chains through an intermediate CA</a> · <a href="e2-m13-gnmi-telemetry.html#s2-1">2.1 gRPC and gNMI</a> · <a href="e2-m13-gnmi-telemetry.html#s2-3">2.3 Dial-in and dial-out</a> · <a href="e2-m13-gnmi-telemetry.html#s2-5">2.5 TLS and mutual TLS: who proves what</a> · <a href="e2-m13-gnmi-telemetry.html#s3-1">3.1 The gRPC server: TLS and mutual TLS</a> · <a href="e2-m13-gnmi-telemetry.html#s3-2">3.2 Putting certificates on IOS XR</a></p>


The NMS will read XR01 through gNMI.

- Run XR01's gRPC server on port 57400, on the NMS segment (the global routing table), with TLS.
- Accept only clients that show a certificate issued by the NMS's certificate authority (`~/pki/ca.pem`). The NMS uses
  `~/pki/client.pem` and `~/pki/client.key`, and still logs in with the lab account.
- Refuse gRPC without TLS.

### Task M13-4
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t4">Open in the lab workspace</a> — Read: <a href="e15-m13-certificates.html#s2-5">2.5 The four checks</a> · <a href="e15-m13-certificates.html#s2-6">2.6 Mutual TLS, and who plays which part on each line</a> · <a href="e15-m13-certificates.html#s3-2">3.2 Checking: openssl s_client</a> · <a href="e2-m13-gnmi-telemetry.html#s2-2">2.2 Subscribe: stream, once and poll</a> · <a href="e2-m13-gnmi-telemetry.html#s2-3">2.3 Dial-in and dial-out</a> · <a href="e2-m13-gnmi-telemetry.html#s2-4">2.4 Encodings and sensor paths</a> · <a href="e2-m13-gnmi-telemetry.html#s2-5">2.5 TLS and mutual TLS: who proves what</a> · <a href="e2-m13-gnmi-telemetry.html#s3-3">3.3 Dial-out: sensor group, destination group, subscription</a> · <a href="e2-m13-gnmi-telemetry.html#s3-4">3.4 Checking it</a></p>


Your predecessor configured XR01 to stream the counters of its interfaces to the telemetry collector on SRV01, with gRPC
dial-out over TLS, every 10 seconds, in subscription `SUB-IF`. Nothing has ever arrived.

- Make the packet counters of XR01's interfaces arrive at the collector every 10 seconds, through subscription `SUB-IF`.
- Keep TLS: XR01 must check the collector's certificate.
- Do not change the collector.
