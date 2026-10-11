# Lab GEN-URPF-90087 : Anti-Spoofing (uRPF) Troubleshooting (Difficulty 4)

## Scenario

The edge router **RT01** is multihomed to two ISPs (routes are received through OSPF).
Yesterday, at the direction of the SOC, **source address verification (uRPF) was deployed on both uplinks**.
After that, the trouble ticket below was issued. Isolate the cause and **restore service**.

```
            RT01 (under your administration, Lo0 = 24.24.24.24)
       E0/0 |              | E0/1
    (Uplink-A)          (Uplink-B)
            |              |
      RT02 (ISP)  ------  RT03 (ISP)
              (inter-ISP peering)
```

## Trouble Ticket

> Customer B (`192.168.121.0/24`) has complained that traffic to RT01 (`24.24.24.24`) **no longer arrives** since the anti-spoofing deployment yesterday.

## Restrictions (Security Policy and Change Scope)

1. Source verification on both uplinks must be **maintained** ("restoring" service by removing it is not acceptable).
2. The verification mode must be **the strictest mode that is technically possible on each interface**.
3. Legitimate flows (the ISP NOC keepalive monitoring sourced from `44.44.44.44`, and Customer B sourced from `192.168.121.1`) must not be dropped.
4. **Changing or adding routing configuration (OSPF, static routes)** on RT01 is not allowed.
5. Changing the configuration of RT02 / RT03 (ISP equipment) is not allowed (verifying their state is allowed).

## Troubleshooting Guidance

- The type and the location of the cause are not disclosed. Isolate it from the device state by using
  `show ip interface <IF>` (verification statistics), `show ip route <prefix>`, `show ip cef`, and so on.
- Scoring is based not on the wording of the configuration but on **the state and the actual drop behavior**.

## Access and Scoring

SSH `SUZUKI / CCNP` (the mgmt addresses are assigned in order, starting from 10.1.10.11).
```
ansible-playbook playbooks/grade.yml -e problem=GEN-URPF-90087 --vault-password-file <(printf 'CCNP\n')
```
