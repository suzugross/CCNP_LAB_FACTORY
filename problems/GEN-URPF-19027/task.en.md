# Problem GEN-URPF-19027 : Anti-spoofing (uRPF) Troubleshooting (Difficulty 4)

## Scenario

Edge router **RT01** is multihomed to two ISPs (routes are received via OSPF). Yesterday, on instruction from the SOC, **source address verification (uRPF) was enabled on both uplinks**.
The trouble ticket below was subsequently issued. Isolate the cause and **restore** the intended behavior.

```
            RT01 (your managed device, Lo0 = 20.20.20.20)
       E0/0 |              | E0/1
    (Uplink-A)          (Uplink-B)
            |              |
      RT02 (ISP)  ------  RT03 (ISP)
              (ISP-to-ISP peering)
```

## Trouble Ticket

> SOC detection: **Suspected source-spoofed packets that impersonate existing prefixes are passing through unchecked on Uplink-A (E0/0)** (there are no verification drops on record).

## Requirements (security policy and change scope)

1. Source verification on both uplinks must be **maintained** (removing it as a "fix" is not allowed).
2. Use the **strictest verification mode technically possible on each interface**.
3. Do not disrupt legitimate flows (ISP NOC liveness monitoring from `32.32.32.32` and customer B traffic from `192.168.52.1`).
4. **Changing or adding routing configuration (OSPF and static routes) on RT01 is prohibited.**
5. Changing the configuration of RT02 / RT03 (ISP equipment) is prohibited (verifying state is allowed).

## Troubleshooting Approach

- The type and location of the cause are not disclosed. Isolate it from the device state using `show ip interface <IF>` (verification statistics), `show ip route <prefix>`, `show ip cef`, and similar commands.
- Scoring examines the **state and the actual drop behavior**, not the literal configuration text.

## Access / Scoring

SSH `SUZUKI / CCNP` (mgmt addresses are assigned in order starting from 10.1.10.11).
```
ansible-playbook playbooks/grade.yml -e problem=GEN-URPF-19027 --vault-password-file <(printf 'CCNP\n')
```
