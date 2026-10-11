# ENCOR-QOS-POLICE-01: Limit the Runaway Backup Transfer to 1Mbps (with Measured Effect)

Difficulty: ★★★☆☆ (3/6) / Points: 100 / Exam: ENCOR (350-401) QoS

QoS hands-on series, question 2. Study order: **CLASS-01 → POLICE-01 → LLQ-01**.

## Scenario

The backup system at Site 1 has started transferring at full rate over the WAN even during business
hours, and it is squeezing other business traffic. The bandwidth settings on the backup vendor's side
cannot be relied on.

It has therefore been decided to limit only the backup transfer to 1Mbps, **forcibly on the network side**.
Excess traffic may be dropped on the spot without buffering
(the backup uses TCP, so the sender slows down on its own; experiencing that is also an aim of this question).

## Topology

```
PC01 ── RT01 ──[ WAN ]── RT02 ── PC02
Site 1         10.1.12.0/30       Site 2
 .10   E0/0        E0/1    E0/1   E0/0   .20
192.168.10.0/24              192.168.20.0/24
```

- PC01 / PC02: Ubuntu (login `SUZUKI` / `CCNP`). iperf3 is installed.
  An iperf3 server runs permanently on PC02.
- The IP addresses and routes of RT01 / RT02 are already configured (**do not change them**).

## Target Traffic

| Internal system | What the traffic actually is | Handling |
|--------------|--------------------|------|
| Backup transfer | **TCP destination port 5201** | **Limit to 1Mbps (drop the excess)** |
| Everything else (voice UDP, liveness-monitoring ICMP, and so on) | All traffic other than the above | **Must not be affected** |

## Requirements

1. On the **WAN output** of RT01, **limit** only the backup transfer (TCP destination 5201)
   **to 1Mbps**. Drop the excess (do not buffer it).
2. Traffic other than the backup must **not be affected in any way**.
3. Make configuration changes on **RT01 only** (changes to RT02 and the PCs are prohibited. Do not change the existing addresses or routes either).
4. The **names** of the class-map / policy-map / ACL and so on **are up to you** (scoring looks at the state and the effect, not the names).

## Hands-on Procedure: See "it is limited", "the sender adapts", and "there is no collateral impact" in numbers

From PC01:

```
# Measurement A: backup transfer (TCP 5201) — compare throughput before and after the implementation
iperf3 -c 192.168.20.20 -t 10

# Measurement B: liveness monitoring during the backup transfer — check for collateral impact
#   (use two terminals or &, while iperf3 is running)
ping -c 20 -i 0.2 192.168.20.20

# Measurement C: voice stream (UDP 5Mbps) — confirm that it is not subject to the limit
iperf3 -c 192.168.20.20 -u -b 5M -l 1200 -t 10
```

Observation on RT01: `show policy-map interface Ethernet0/1`
(you can read the packet counts and rates for conformed (passed) / exceeded (dropped)).

**Record table** (fill it in before and after the implementation):

| Measurement | Before | After |
|------|--------|--------|
| A: TCP throughput | Mbps | Mbps |
| B: ping during the transfer (RTT avg / loss%) | ms / % | ms / % |
| C: receive rate / loss% of UDP 5Mbps | Mbps / % | Mbps / % |
| RT01: conformed / exceeded packets | - | / |

Points to consider: why does the throughput after the implementation settle at "almost 1Mbps"
even though TCP packets are being dropped (who is matching the rate)?
What happens with UDP under the same limit (you will experience this in LLQ-01)?

## Scoring

- Scoring is automatic (state of the configuration + measured effect). The grader also sends traffic from PC01.
- Estimated time: 30 to 45 minutes.
