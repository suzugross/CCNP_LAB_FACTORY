# M13 — Certificates and TLS from the ground up

gNMI and telemetry, on the next page, are both protected by TLS, and certificates decide how they behave. So do tasks
M13-3 and M13-4. Before that, this page lays out certificates and TLS from the ground up: key pairs, signatures,
certificates, certificate authorities (CAs), the four things checked inside TLS, mutual TLS, and how self-signed certificates and chains through an
intermediate CA are checked, in that order. It
covers the TLS and mutual-TLS certificate part of 5.7 of the blueprint.

The only tool is `openssl` on SRV01, and this page changes no router configuration. Where XR01 keeps its certificates,
and how to put them there, is in section 3.2 of the next page.

## 1. What it is good for

### 1.1 The problem: an address proves nothing about who answers

On XRT-15, gnmic on SRV01 connects to port 57400 on XR01's 10.0.50.1 and sends the username and password of the lab
account. In the other direction, XR01 sends its interface counters to port 57500 on 10.0.50.10. Each side knows the
other only by its address.

An address is not proof of identity. If another machine on the NMS segment takes 10.0.50.1, by mistake or on purpose,
SRV01 hands it the password. If it takes 10.0.50.10, XR01 sends it the counters. Anyone reading the wire in between
reads an unencrypted password as it is. A correct address on the envelope says nothing about who opens it.

### 1.2 Before: plain text, passwords, SSH host keys

- **Plain text**: SNMPv2c communities and gRPC without TLS (`no-tls`) carry the password, or what stands for it, as it
  is.
- **Passwords**: they let the server check the client. They do not work the other way round: the client cannot check
  the server with them. A fake server only has to accept the password.
- **SSH host keys** (NETCONF in M13-1): SSH encrypts the connection, and the server shows who it is with its own key
  (the host key). Whether that host key is the real one is usually settled by a person on the first connection, who
  checks it and has it remembered (`known_hosts`). A hundred routers mean a hundred keys to remember. The skeleton in
  M13-1 turned this check off (`hostkey_verify=False`).

### 1.3 The TLS answer: a third party's signature on a name

- **Prove the name**: the server shows a certificate. A certificate is the statement "this public key belongs to
  collector.nms.lab", signed by a certificate authority (CA).
- **One tool is enough to check**: the checking side holds one CA certificate. Every certificate the same CA signed,
  for a hundred devices or more, is checked with that one file. Nothing has to be remembered device by device, as with
  SSH.
- **Encrypt**: once the checks pass, both ends encrypt the connection with keys made on the spot.
- **Works the other way too**: in mutual TLS the client also shows a certificate, and the server checks it. On top of
  the password, the server can check that the peer got its certificate from a given CA.

## 2. How it works: keys, signatures, certificates, CAs

### 2.1 The parts

There are six parts. The second column compares them with a signet ring and a seal registry; the match is close.

| Part | As a seal | What it is | On XRT-15 |
|---|---|---|---|
| Private key | The signet ring | One half of a key pair. Never leaves its owner | `~/pki/client.key` on SRV01, `ems.key` on XR01, telegraf's key |
| Public key | The ring's impression | The other half. May be handed out | Inside the certificate |
| Signature | Pressing the seal | A mark made on data with the private key. The matching public key shows that the data has not changed and that this private key made the mark | Made in every TLS handshake (section 2.5) |
| Certificate | The registry's letter saying whose impression it is | A name, a public key, a validity period and more, signed by the issuer (the CA) | `~/pki/client.pem` (nms-gnmi), the collector's certificate (collector.nms.lab), XR01's `ems.pem` |
| CA certificate | A specimen of the registry's own seal | The CA's own name and public key. Held by the checking side | `~/pki/ca.pem` (NMS-LAB-CA) |
| Request (CSR) | The application to register a seal | The name and public key to be certified, signed with the requester's own private key and sent to the CA | Made when the lab was built (section 3.1) |

### 2.2 Key pairs: a signature made with one half is checked with the other

A key pair is two keys that belong together: a private key and a public key. A signature made with the private key can
be checked with the matching public key, and with no other key. Working out the private key from the public key is
not feasible in practice. So the public key may be handed out, and the private key never leaves its owner.

On SRV01 you can check that the public key in a certificate and the private key in hand are a pair. Take the public
key out of the private key, and compare it, as a hash, with the public key in the certificate. If they are the same,
the two are a pair. The CA's public key is a different one.

```console
$ openssl pkey -in ~/pki/client.key -pubout | sha256sum
233893b38b499c135cf3b94f1050c0436065357330f8c324b5de6fe6b7b82fae  -
$ openssl x509 -in ~/pki/client.pem -noout -pubkey | sha256sum
233893b38b499c135cf3b94f1050c0436065357330f8c324b5de6fe6b7b82fae  -
$ openssl x509 -in ~/pki/ca.pem -noout -pubkey | sha256sum
bb56e6830b0cfb0e2b4f490677688b6f8dfcf420818653a89b844bd412b904ee  -
```

In TLS 1.3 (the connection to the collector used it), the keys that encrypt the connection are not this key pair.
Both ends make keys on the spot in each handshake, agree on them, and throw them away when the connection ends. The
certificate's key is there to sign, which shows who the owner is. In the output of a connection to the collector,
`Server Temp Key` is the key made on the spot, and `Peer signature type` is how the collector signed. The
certificate's key never touches the encryption; it only signs.

```console
$ openssl s_client -connect 10.0.50.10:57500 -CAfile ~/pki/ca.pem -verify_hostname collector.nms.lab </dev/null 2>&1 | grep -E "Peer signature|Server Temp Key|^New"
Peer signature type: RSA-PSS
Server Temp Key: X25519, 253 bits
New, TLSv1.3, Cipher is TLS_AES_128_GCM_SHA256
```

### 2.3 Certificates: a name and a public key, signed by a CA

A certificate is one document with fixed fields. `openssl x509` reads them.

```console
$ openssl x509 -in ~/pki/client.pem -noout -subject -issuer -dates -ext subjectAltName,extendedKeyUsage,basicConstraints
subject=O = NMS Lab, CN = nms-gnmi
issuer=O = NMS Lab, CN = NMS-LAB-CA
notBefore=Nov 15 14:57:02 2026 GMT
notAfter=Nov 12 14:57:02 2036 GMT
X509v3 Extended Key Usage: 
    TLS Web Client Authentication
```

| Field | What it is | In `client.pem` |
|---|---|---|
| subject | The name of the certificate's owner. The CN (common name) is part of it | CN = nms-gnmi |
| issuer | The name of the CA that signed it | CN = NMS-LAB-CA |
| notBefore, notAfter | The validity period | Ten years from 15 November 2026 |
| subjectAltName (SAN) | The names and IP addresses the certificate is valid for | None |
| extendedKeyUsage | The use: for servers (TLS Web Server Authentication) or for clients | For clients |
| Public key | The owner's public key | The hash in section 2.2 |
| Signature | Made over all the fields above with the issuer's private key | NMS-LAB-CA's signature |

The collector's certificate is for servers, and has its name and its address in the SAN, so a side that connects can
check it whether it dialled the name or the address. The client certificate `client.pem` has no SAN. XR01's gRPC
server, in mutual TLS, accepts `client.pem` without a SAN (next page).

```console
$ openssl s_client -connect 10.0.50.10:57500 </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -ext subjectAltName,extendedKeyUsage
subject=O = NMS Lab, CN = collector.nms.lab
issuer=O = NMS Lab, CN = NMS-LAB-CA
X509v3 Subject Alternative Name: 
    DNS:collector.nms.lab, IP Address:10.0.50.10
X509v3 Extended Key Usage: 
    TLS Web Server Authentication
```

A name can be written in two places, the CN and the SAN. Some clients look at the SAN when they check the name, and
gnmic is one of them: checking XR01's certificate against its address failed with `doesn't contain any IP SANs`
(section 2.5 of the next page). The lab's collector certificate carries its name in both the CN and the SAN.

### 2.4 The CA: where trust starts

The CA certificate `ca.pem` has the same subject and issuer: the CA signed it itself (self-signed). `CA:TRUE` marks it
as the certificate of a CA, allowed to sign other certificates. The CA vouches for itself.

```console
$ openssl x509 -in ~/pki/ca.pem -noout -subject -issuer -dates -ext basicConstraints
subject=O = NMS Lab, CN = NMS-LAB-CA
issuer=O = NMS Lab, CN = NMS-LAB-CA
notBefore=Nov 15 14:57:01 2026 GMT
notAfter=Nov 12 14:57:01 2036 GMT
X509v3 Basic Constraints: critical
    CA:TRUE
```

Nobody above checks `ca.pem`. The only reason to trust it is that this one file arrived by a path you trust. That one
file is called the **trust anchor**. The checking side looks up the CA certificate it holds by the certificate's issuer
name, and checks the signature with that CA's public key. `openssl verify` does the same. Given no CA, it searches
OpenSSL's default store (on Ubuntu, the list of public CAs), and does not find NMS-LAB-CA. The two-level form, a root CA and an intermediate CA, is in section 3.3.

```console
$ cd ~/pki
$ openssl verify -CAfile ca.pem client.pem
client.pem: OK
$ openssl verify client.pem
O = NMS Lab, CN = nms-gnmi
error 20 at 0 depth lookup: unable to get local issuer certificate
error client.pem: verification failed
```

A name can be copied; a signature cannot. As a test, a second CA with the same name, NMS-LAB-CA, was made, and it
issued a certificate for nms-gnmi. Its subject and issuer print exactly as the real `client.pem`'s do. Checked against
the fake CA, it is OK. Checked against the real `ca.pem`, the issuer name matches but the signature does not, and it
fails. openssl does not know which CA is the real one. It checks against the one it is given.

```console
$ openssl x509 -in fake.pem -noout -subject -issuer
subject=O = NMS Lab, CN = nms-gnmi
issuer=O = NMS Lab, CN = NMS-LAB-CA
$ openssl verify -CAfile fake-ca.pem fake.pem
fake.pem: OK
$ openssl verify -CAfile ~/pki/ca.pem fake.pem
O = NMS Lab, CN = nms-gnmi
error 7 at 0 depth lookup: certificate signature failure
error fake.pem: verification failed
...
```

`ems.pem`, which XR01 makes for itself when gRPC is enabled, is self-signed too. Its only name is `ems.cisco.com`. No
CA vouches for it, so a client can trust it only by holding that very file as its CA file, or by not checking at all.
The first means trusting that one file and nothing else. If the peer makes a new certificate, the file has to be
handed out again.

:::try
Make a fake CA with the same name yourself, and see that the real CA does not accept what it signs. Everything is made
in `/tmp/fake-ca`, and removed at the end.

1. Make a place to work: `mkdir /tmp/fake-ca && cd /tmp/fake-ca`.
2. Make the fake CA: `openssl req -x509 -newkey rsa:2048 -nodes -keyout fake-ca.key -out fake-ca.pem -days 30 -subj "/O=NMS Lab/CN=NMS-LAB-CA"`
3. Make a request for nms-gnmi and sign it with the fake CA:
   `openssl req -newkey rsa:2048 -nodes -keyout fake.key -out fake.csr -subj "/O=NMS Lab/CN=nms-gnmi"`,
   then `openssl x509 -req -in fake.csr -CA fake-ca.pem -CAkey fake-ca.key -CAcreateserial -out fake.pem -days 30`
4. Compare `openssl x509 -in fake.pem -noout -subject -issuer` with `openssl x509 -in ~/pki/client.pem -noout -subject -issuer`.
5. Compare `openssl verify -CAfile fake-ca.pem fake.pem` with `openssl verify -CAfile ~/pki/ca.pem fake.pem`.
6. Remove it all: `cd ~ && rm -rf /tmp/fake-ca`.

Example result: the two outputs in step 4 were the same (`subject=O = NMS Lab, CN = nms-gnmi`,
`issuer=O = NMS Lab, CN = NMS-LAB-CA`). In step 5, the fake CA gave `fake.pem: OK`, and the real CA gave
`error 7 at 0 depth lookup: certificate signature failure`.
:::

### 2.5 The four checks

In the TLS 1.3 handshake, the server sends its certificate (Certificate), and then a signature over the exchange so
far, made with its private key (CertificateVerify). The receiving side checks four things.

1. **Signed by a CA it trusts**: it holds the issuer's CA certificate, and the signature matches that CA's public key.
2. **Within the validity period**: the checking side's current time is between notBefore and notAfter.
3. **The name it dialled**: the name or address it meant to reach is in the certificate (in the SAN).
4. **The peer holds the private key**: the CertificateVerify signature matches the public key in the certificate.

Check 1 is needed because anyone can make a document shaped like a certificate (the fake CA in section 2.4). Check 3
is needed because a real certificate from a real CA means nothing if it belongs to someone else. NMS-LAB-CA has issued
two, for collector.nms.lab and for nms-gnmi. Without looking at the name, you cannot tell either of them from someone
else who got a certificate from the same CA. Check 4 is needed because certificates are handed out, and anyone can
hold a copy. Showing a copy does not prove that you hold the private key.

Check 2 uses the checking side's clock. `-attime` gives `openssl verify` a time to use instead of the clock, and it
refuses outside the period: `expired` after it, `not yet valid` before it.

```console
$ openssl verify -attime $(date -d "2037-01-01" +%s) -CAfile ca.pem client.pem
O = NMS Lab, CN = NMS-LAB-CA
error 10 at 1 depth lookup: certificate has expired
O = NMS Lab, CN = nms-gnmi
error 10 at 0 depth lookup: certificate has expired
error client.pem: verification failed
$ openssl verify -attime $(date -d "2026-01-01" +%s) -CAfile ca.pem client.pem
O = NMS Lab, CN = NMS-LAB-CA
error 9 at 1 depth lookup: certificate is not yet valid
error client.pem: verification failed
```

`depth` is the level of the certificate being checked: 0 is the peer's certificate, 1 the CA certificate that signed
it. A CA certificate has a validity period too, and is checked the same way.

### 2.6 Mutual TLS, and who plays which part on each line

In plain TLS, only the server shows a certificate. In mutual TLS, the server asks the client for one as well
(CertificateRequest), and the client sends back its certificate and a CertificateVerify. The server checks it against
the CA it trusts.

Two rules keep this straight.

- **Which end is the TLS server depends on who connects.** The side that listens is the server. The same XR01 plays
  different parts on different lines.
- **The checking side holds the CA certificate.** It holds the certificate of the CA that signed the peer's
  certificate, not one for its own certificate.

Applied to the lines on XRT-15:

| Line (connects → listens) | Certificate the server shows, and how the client checks it | Certificate the client shows, and how the server checks it |
|---|---|---|
| gNMI (M13-3): gnmic on SRV01 → XR01 | `ems.pem` (ems.cisco.com, self-signed). Checked against `ems.pem` itself and the name `ems.cisco.com`, or not checked | With mutual TLS, `client.pem` (nms-gnmi); XR01 checks it against NMS-LAB-CA |
| Telemetry dial-out (M13-4): XR01 → telegraf on SRV01 | collector.nms.lab (issued by NMS-LAB-CA). Checked against NMS-LAB-CA and the name or address expected | None |
| RESTCONF (M13-2): the script on SRV01 → PE2 | PE2's HTTPS certificate. Not checked (`verify=False`) | None |

RESTCONF in M13-2 was TLS underneath as well. The script had the check turned off, so the certificate never came up.

### 2.7 Key points

- Private keys never leave their owners. Only certificates and CA certificates are handed out.
- A certificate is a name and a public key, signed by a CA. The CA certificate is self-signed: the trust anchor.
- The side that receives a certificate checks four things: signed by a CA it trusts, within the validity period, the
  name it dialled, and that the peer holds the private key.
- In TLS 1.3 the encryption keys are made on the spot. The certificate's key is used to sign.
- The TLS server is the side that listens. The checking side holds the CA certificate. In mutual TLS, both sides check.
- A self-signed certificate is trusted only by those who hold that very file. In a CA chain, the server also sends the
  intermediate CA's certificate, and the client follows it up to the root CA it holds (section 3.3).

## 3. Building: making and checking certificates

### 3.1 How a certificate is made: key, request, signature

The lab's certificates were made on SRV01 when the lab was built. The figure follows the collector's certificate from
the first key to the CA certificate reaching the checking side. Rest the pointer on a number in the figure (or tap it on
a phone) to see that part of the commands.

:::walk
legend: "How one certificate is made. Blue numbers: lines in the example below. No private key leaves the machine that made it."
rows:
  - panel: NMS-LAB-CA
    sub: certificate authority
    items:
      - ref: 1
        head: "**Make a key pair and sign for itself** `openssl req -x509 …`"
        say: ["`ca.key` (private key) stays with the CA", "`ca.pem` (subject = issuer = NMS-LAB-CA) is handed out"]
  - panel: collector
    sub: telegraf's owner
    items:
      - ref: 2
        head: "**Make a key pair and a request** `openssl req -newkey … collector.nms.lab`"
        say: ["`collector.key` stays here", "The request (CSR) = name and public key, signed with its own private key"]
  - {wire: "[[=CSR]] [[CN=collector.nms.lab  public key]] _→ to the CA"}
  - panel: NMS-LAB-CA
    sub: certificate authority
    items:
      - ref: 3
        head: "**Add fields and sign** `openssl x509 -req … -CAkey ca.key …`"
        say: ["SAN `DNS:collector.nms.lab` and `IP:10.0.50.10`, use: servers", "Signed with the CA's private key → `collector.pem`"]
  - {wire: ["[[=certificate]] [[collector.nms.lab  public key  validity]]", "[[!NMS-LAB-CA's signature]] _→ to the collector"]}
  - {node: XR01, say: ["The checking side. It receives `ca.pem` only", "~not a single key"]}
  - aside: "If `ca.key` leaves the CA"
    say: ["~whoever holds it can make a certificate for any name, with NMS-LAB-CA's signature (the fake CA of section 2.4, with the real name and the real signature)"]
:::

:::config SRV01 (when the lab was built) — make the NMS CA and issue the collector's certificate
openssl req -x509 -newkey rsa:2048 \     ## ① Make a key pair and sign for itself on the spot (-x509)
  -nodes -keyout ca.key \                ## The CA's private key; -nodes = no passphrase
  -out ca.pem -days 3650 \               ## The CA certificate, valid for ten years
  -subj "/O=NMS Lab/CN=NMS-LAB-CA"       ## The CA's name; it becomes both subject and issuer
openssl req -newkey rsa:2048 -nodes \    ## ② The collector's key pair and request; without -x509 it is a request
  -keyout collector.key \                ## The private key stays with the collector
  -out collector.csr \                   ## The request goes to the CA
  -subj "/O=NMS Lab/CN=collector.nms.lab"   ## The name to be certified
cat > collector.ext <<'EOF'              ## ③ Write the fields the CA will add into a file
subjectAltName=DNS:collector.nms.lab,IP:10.0.50.10   ## ③ The name and address to be checked (SAN)
extendedKeyUsage=serverAuth              ## ③ Use: for servers
EOF
openssl x509 -req -in collector.csr \    ## ③ Turn the request into a certificate
  -CA ca.pem -CAkey ca.key \             ## The issuer is NMS-LAB-CA; the CA's private key signs
  -CAcreateserial \                      ## Also makes the serial-number file
  -out collector.pem -days 3650 \        ## The certificate, valid for ten years
  -extfile collector.ext                 ## Reads the fields to add (SAN and use)
:::

The client certificate `client.pem` follows the same steps, with the name nms-gnmi and only the use field (for clients)
added. The request is signed with the requester's private key, and the CA uses that to check that the requester holds
the private key for the public key in it. For the fake CA in section 2.4, `openssl req -in fake.csr -noout -subject -verify`
answered `Certificate request self-signature verify OK`.

### 3.2 Checking: openssl s_client

`openssl s_client` connects as a TLS client, checks the server's certificate, and prints the result. The figure
follows s_client on SRV01 as it connects to the collector (telegraf), which runs on the same SRV01. XR01's dial-out
checks in the same order.

:::walk
legend: "The collector shows its certificate; the side that connected checks it. Blue numbers: lines in the example below."
rows:
  - {node: openssl, kind: host, say: ["`openssl s_client` on SRV01 (TLS client)", "_holds: `ca.pem` and the name it expects"]}
  - {wire: "[[TCP → 10.0.50.10:57500]] [[=ClientHello]]"}
  - {node: telegraf, kind: host, say: ["The collector on SRV01 (TLS server)", "_holds: the collector's certificate and its private key"]}
  - {wire: "[[=Certificate]] [[collector.nms.lab]] [[!CertificateVerify  RSA-PSS]] _→ to s_client"}
  - panel: openssl
    sub: s_client checks
    items:
      - ref: 1
        head: "**Signed by a CA it trusts** `-CAfile ~/pki/ca.pem`"
        match:
          - ["no CA file given", false, "`21 (unable to verify the first certificate)`"]
          - ["ca.pem (NMS-LAB-CA)", true, "matches"]
      - say: ["**Within the validity period** (by SRV01's clock)", "_Nov 15 2026 to Nov 12 2036"]
      - ref: 2
        head: "**The name it dialled** `-verify_hostname collector.nms.lab`"
        match:
          - ["nms-gnmi (another name from the same CA)", false, "`62 (hostname mismatch)`"]
          - ["collector.nms.lab (DNS in the SAN)", true, "matches"]
      - say: ["**The peer holds the private key**", "_the CertificateVerify signature is checked with the certificate's public key"]
      - ref: 3
        head: "**Stop on failure** `-verify_return_error`"
        say: ["Without it, the connection goes on and the result is only printed"]
      - say: ["~All four pass → encrypted with the keys agreed on the spot (X25519)", "~`Verification: OK`, `Verified peername: collector.nms.lab`"]
  - aside: "If a different CA with the same name had signed it"
    say: ["~the issuer name matches → the signature does not match `ca.pem`'s public key (openssl verify: `7 certificate signature failure`, section 2.4)"]
:::

:::config SRV01 — check the collector's certificate against the CA and the name
openssl s_client -connect 10.0.50.10:57500 \   ## Connect to the collector's port as a TLS client
  -CAfile ~/pki/ca.pem \                        ## ① The CA to trust. The collector's certificate signature is checked with it
  -verify_hostname collector.nms.lab \          ## ② The expected name, compared with the certificate's SAN
  -verify_return_error \                        ## ③ Stop the handshake if a check fails
  -brief </dev/null                             ## Print only the result, and close at once
:::

This is what a pass looks like. The first line, `Can't use SSL_get_servername`, has no bearing on the result of the
checks here (the same output says `Verification: OK`).

```console
$ openssl s_client -connect 10.0.50.10:57500 -CAfile ~/pki/ca.pem -verify_hostname collector.nms.lab -verify_return_error -brief </dev/null
Can't use SSL_get_servername
CONNECTION ESTABLISHED
Protocol version: TLSv1.3
Ciphersuite: TLS_AES_128_GCM_SHA256
Peer certificate: O = NMS Lab, CN = collector.nms.lab
Hash used: SHA256
Signature type: RSA-PSS
Verification: OK
Verified peername: collector.nms.lab
Server Temp Key: X25519, 253 bits
```

With the name nms-gnmi, `-verify_return_error` stops the handshake with `certificate verify failed`.

```console
$ openssl s_client -connect 10.0.50.10:57500 -CAfile ~/pki/ca.pem -verify_hostname nms-gnmi -verify_return_error </dev/null
Can't use SSL_get_servername
depth=0 O = NMS Lab, CN = collector.nms.lab
verify error:num=62:hostname mismatch
4067344802700000:error:0A000086:SSL routines:tls_post_process_server_certificate:certificate verify failed:../ssl/statem/statem_clnt.c:1889:
CONNECTED(00000003)
...
Verification error: hostname mismatch
```

Without `-verify_return_error`, s_client prints `verify error:num=62:hostname mismatch`, carries on with the
connection, and ends with `Verify return code: 62 (hostname mismatch)`. The failure is reported. It is only reported.
gnmic and XR01 give up the connection when a check fails (the error messages in section 3.4 of the next page).

:::try
Make two of the four checks fail on purpose with s_client. Each step only connects to the collector once and closes;
the collector's configuration does not change.

1. Connect without a CA: `openssl s_client -connect 10.0.50.10:57500 </dev/null 2>&1 | grep -E "verify error|Verify return"`
2. Connect with the right CA and a wrong name: `openssl s_client -connect 10.0.50.10:57500 -CAfile ~/pki/ca.pem -verify_hostname nms-gnmi </dev/null 2>&1 | grep -E "verify error|Verify return"`
3. Check the address instead of the name: `openssl s_client -connect 10.0.50.10:57500 -CAfile ~/pki/ca.pem -verify_ip 10.0.50.10 </dev/null 2>&1 | grep "Verify return"`

Example result: step 1 gave `verify error:num=20:unable to get local issuer certificate` and `Verify return code: 21 (unable to verify the first certificate)`,
step 2 `verify error:num=62:hostname mismatch` and `Verify return code: 62 (hostname mismatch)`, and step 3 `Verify return code: 0 (ok)`.
In steps 1 and 2, the connection itself still went through to the end.
:::

### 3.3 Self-signed certificates, and chains through an intermediate CA

So far the CA has had one level: NMS-LAB-CA signs the collector's certificate directly. Server certificates on the
internet are usually not signed by a root CA directly; an **intermediate CA** stands in between. www.cisco.com, for
example, sent three certificates: its own, that of the intermediate CA that signed it (HydrantID Server CA O1), and
that of the root CA above (IdenTrust Commercial Root CA 1).

A server's certificate can be trusted in two ways. The two figures below show them one at a time. The values come from
test certificates made in a temporary place on SRV01: the root CA DEMO-ROOT-CA, the intermediate CA DEMO-ISSUING-CA,
the server www.demo.lab, and the self-signed server self.demo.lab.

| | Self-signed certificate | Certificate signed by a CA |
|---|---|---|
| What the server sends | Its own certificate only | Its own certificate and the intermediate CA's (some servers send the root CA's as well) |
| What the client holds beforehand | The server's certificate itself | The root CA's certificate (for a public CA, it is in the OS's list, the trust store) |
| Where trust starts | The server's certificate | The root CA's certificate |
| When the server makes a new certificate | It has to be handed to the clients again | Nothing to hand out (if it is issued again under the same root CA) |

The fields in the test certificates, and the part each plays, are as follows (read with
`openssl x509 -noout -subject -issuer -ext …`; "A ← B" means subject A, issuer B).

| Certificate | What it says | Who holds it, and what for |
|---|---|---|
| Root CA (`root.pem`) | DEMO-ROOT-CA ← DEMO-ROOT-CA (self-signed). CA:TRUE | Held by the client beforehand. Where trust starts. The server need not send it |
| Intermediate CA (`inter.pem`) | DEMO-ISSUING-CA ← DEMO-ROOT-CA. CA:TRUE, pathlen:0 (no CA below it), use Certificate Sign | Sent by the server. Part of the path only; not trusted by itself |
| Server (`server.pem`) | www.demo.lab ← DEMO-ISSUING-CA. SAN DNS:www.demo.lab | Sent by the server. Its name is compared, and it checks the CertificateVerify signature |
| Self-signed server (`self.pem`) | self.demo.lab ← self.demo.lab. SAN DNS:self.demo.lab | Sent by the server; the client holds the same file beforehand |

**A self-signed certificate.** Trust starts at the server's certificate itself, so there is no level above to follow.
Rest the pointer on a number in the figure (or tap it on a phone) to see that part of the commands.

:::walk
legend: "Checking a self-signed certificate. Trust starts at the server's certificate itself. Blue numbers: lines in the example below."
rows:
  - {node: server, kind: host, say: ["self.demo.lab (a test s_server)", "_holds: self.pem (self-signed) and self.key"]}
  - {wire: ["[[=Certificate]] [[subject self.demo.lab]] [[issuer self.demo.lab]]", "[[!CertificateVerify]] _→ to the client"]}
  - panel: client
    sub: openssl s_client
    items:
      - ref: 1
        head: "**Is this very file in the local list** `-CAfile self.pem`"
        say: ["issuer = subject, so there is nothing above to follow"]
        match:
          - ["not in the list (only the OS's list, or another CA)", false, "`18 (self-signed certificate)`"]
          - ["holds self.pem itself", true, "trusted as the starting point"]
      - say: ["**Within the validity period**"]
      - ref: 2
        head: "**The name it dialled** `-verify_hostname self.demo.lab`"
        say: ["compared with DNS:self.demo.lab in the SAN"]
      - say: ["**The peer holds the private key**", "_the CertificateVerify is checked with self.pem's public key"]
      - say: ["~All passed → `Verification: OK`"]
  - aside: "If the server makes a new certificate"
    say: ["~the client's self.pem is still the old file → the new certificate is not in the list → 18. Hand it out again"]
:::

:::config client — check a self-signed certificate against that one file
openssl s_client -connect 127.0.0.1:44332 \  ## Connect to the test server that shows a self-signed certificate
  -CAfile self.pem \                          ## ① The list to trust = the server's certificate itself
  -verify_hostname self.demo.lab \            ## ② The expected name
  -verify_return_error -brief </dev/null      ## Stop on failure; print only the result
:::

```console
$ openssl s_client -connect 127.0.0.1:44332 -verify_hostname self.demo.lab -verify_return_error </dev/null
Can't use SSL_get_servername
depth=0 O = Demo, CN = self.demo.lab
verify error:num=18:self-signed certificate
...
Verification error: self-signed certificate
$ openssl s_client -connect 127.0.0.1:44332 -CAfile self.pem -verify_hostname self.demo.lab -verify_return_error -brief </dev/null
Can't use SSL_get_servername
CONNECTION ESTABLISHED
...
Verification: OK
Verified peername: self.demo.lab
```

Given `self.pem` as its CA file, the check passes; without it, it stops at `18 (self-signed certificate)`. To the
client, the file is a list that says "trust this one certificate and nothing else". Checking XR01's `ems.pem` with
gnmic takes the same form.

**A certificate signed by a CA, through an intermediate.** The client follows the issuer names of the certificates it
receives upwards to build a path, takes the root CA it holds as the starting point, and checks the signatures level by
level from the top down.

:::walk
legend: "Checking a certificate signed through an intermediate CA. The server sends its own certificate and the intermediate CA's; the client follows them up to the root CA it holds. Blue numbers: lines in the examples below."
rows:
  - {node: server, kind: host, say: ["www.demo.lab (a test s_server)", "_holds: server.pem, server.key, and the intermediate CA's inter.pem"]}
  - {wire: ["[[=Certificate 0]] [[www.demo.lab ← DEMO-ISSUING-CA]]", "[[=Certificate 1]] [[DEMO-ISSUING-CA ← DEMO-ROOT-CA]]", "[[!CertificateVerify]] _the root CA is not sent → to the client"]}
  - panel: client
    sub: build the path upwards by issuer name, then check signatures downwards from the starting point
    items:
      - say: ["**Build the path** (bottom up, by issuer name)", "_www.demo.lab → DEMO-ISSUING-CA (sent, number 1) → DEMO-ROOT-CA (in the local list)"]
      - ref: 1
        head: "**Starting point: the local root CA** `-CAfile root.pem`"
        say: ["Self-signed, so nothing above is followed. It is trusted because it is in the local list"]
        match:
          - ["holds only the intermediate CA", false, "`2 (unable to get issuer certificate)`"]
          - ["sent by the server, but not held", false, "`19 (self-signed certificate in certificate chain)`"]
          - ["holds DEMO-ROOT-CA", true, "the starting point"]
      - ref: 2
        head: "**The intermediate CA's certificate** `-untrusted inter.pem`"
        say: ["Received from the server. Not trusted by itself; used as part of the path"]
        match:
          - ["not sent", false, "`20 (unable to get local issuer certificate)`"]
          - ["a certificate without CA:TRUE", false, "`79 (invalid CA certificate)`"]
          - ["DEMO-ISSUING-CA with CA:TRUE", true, "its signature is checked with the root CA's public key"]
      - say: ["**The server's certificate**", "_its signature is checked with the intermediate CA's public key"]
      - say: ["**Every level within its validity period**"]
      - ref: 3
        head: "**The name it dialled** `-verify_hostname www.demo.lab`"
        say: ["Only depth 0 (the server's certificate) is compared"]
      - say: ["**The peer holds the private key**", "_the CertificateVerify is checked with depth 0's public key"]
      - say: ["~All passed → `Verification: OK`"]
:::

:::config server — send the intermediate CA's certificate along with its own
openssl s_server -accept 127.0.0.1:44330 \  ## A test TLS server
  -cert server.pem -key server.key \         ## Its own certificate and private key
  -cert_chain inter.pem                      ## ② Also send the intermediate CA's certificate
:::

:::config client — follow the received chain up to the local root CA and check it
openssl s_client -connect 127.0.0.1:44330 \  ## Connect to the server that also sends the intermediate CA
  -CAfile root.pem \                          ## ① The starting point = the root CA (in place of the OS's list)
  -verify_hostname www.demo.lab \             ## ③ The expected name, compared with depth 0
  -verify_return_error -brief </dev/null      ## Stop on failure; print only the result
openssl verify -show_chain \                  ## The same with files, printing the chain it built
  -CAfile root.pem \                          ## ① The starting point
  -untrusted inter.pem \                      ## ② A certificate used only for the path (in TLS, the server sends it)
  server.pem                                  ## The certificate to check
:::

```console
$ openssl verify -show_chain -CAfile root.pem -untrusted inter.pem server.pem
server.pem: OK
Chain:
depth=0: O = Demo, CN = www.demo.lab (untrusted)
depth=1: O = Demo, CN = DEMO-ISSUING-CA (untrusted)
depth=2: O = Demo, CN = DEMO-ROOT-CA
$ openssl s_client -connect 127.0.0.1:44330 -CAfile root.pem -verify_hostname www.demo.lab -verify_return_error </dev/null
Can't use SSL_get_servername
depth=2 O = Demo, CN = DEMO-ROOT-CA
verify return:1
depth=1 O = Demo, CN = DEMO-ISSUING-CA
verify return:1
depth=0 O = Demo, CN = www.demo.lab
verify return:1
...
Certificate chain
 0 s:O = Demo, CN = www.demo.lab
   i:O = Demo, CN = DEMO-ISSUING-CA
...
 1 s:O = Demo, CN = DEMO-ISSUING-CA
   i:O = Demo, CN = DEMO-ROOT-CA
...
```

`(untrusted)` marks a certificate that is not in the local list and was only used for the path. Only depth 2, without
the mark, is the starting point. s_client prints from depth 2 down, because it checks the signatures level by level
from the starting point downwards. The server sent two certificates, 0 and 1; it did not send the root CA.

When the path cannot be built, or a level in the middle is not a CA, it stops as follows. `notca.pem` is an ordinary
certificate that the root CA issued with CA:FALSE, and `bad.pem` is a www.demo.lab certificate signed with it.

```console
$ openssl verify -CAfile root.pem server.pem
O = Demo, CN = www.demo.lab
error 20 at 0 depth lookup: unable to get local issuer certificate
error server.pem: verification failed
$ openssl verify -CAfile inter.pem server.pem
O = Demo, CN = DEMO-ISSUING-CA
error 2 at 1 depth lookup: unable to get issuer certificate
error server.pem: verification failed
$ openssl verify -CAfile root.pem -untrusted notca.pem bad.pem
O = Demo, CN = NOT-A-CA
error 79 at 1 depth lookup: invalid CA certificate
error bad.pem: verification failed
```

The first is given no intermediate CA. Connecting to a server that does not send the intermediate CA stopped s_client
with the same `20`. The second takes only the intermediate CA as the starting point; it looks for the root CA above it,
does not find it, and stops. By default OpenSSL does not accept a chain that cannot be followed up to a self-signed
starting point. The third stops because a certificate without CA:TRUE signed the server's.

The intermediate CA's certificate that the server sends is not a reason to trust anything; it is only part of the path.
The only reason to trust is the root CA certificate the client held beforehand. It is the same when the server sends
the root CA as well: if the client does not hold it, the check stops at
`19 (self-signed certificate in certificate chain)`. What a server says about itself is only what that server says.

:::try
Make a three-level set of certificates, root CA, intermediate CA and server, and compare a path that can be built with
paths that cannot. Everything is made in `/tmp/chain-demo`, and removed at the end.

1. `mkdir /tmp/chain-demo && cd /tmp/chain-demo`
2. Root CA: `openssl req -x509 -newkey rsa:2048 -nodes -keyout root.key -out root.pem -days 3650 -subj "/O=Demo/CN=DEMO-ROOT-CA"`
3. Intermediate CA: `openssl req -newkey rsa:2048 -nodes -keyout inter.key -out inter.csr -subj "/O=Demo/CN=DEMO-ISSUING-CA"`,
   `printf "basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\n" > inter.ext`,
   `openssl x509 -req -in inter.csr -CA root.pem -CAkey root.key -CAcreateserial -out inter.pem -days 1825 -extfile inter.ext`
4. Server: `openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr -subj "/O=Demo/CN=www.demo.lab"`,
   `printf "subjectAltName=DNS:www.demo.lab\nextendedKeyUsage=serverAuth\n" > server.ext`,
   `openssl x509 -req -in server.csr -CA inter.pem -CAkey inter.key -CAcreateserial -out server.pem -days 365 -extfile server.ext`
5. Compare `openssl verify -show_chain -CAfile root.pem -untrusted inter.pem server.pem`, `openssl verify -CAfile root.pem server.pem`
   and `openssl verify -CAfile inter.pem server.pem`.
6. Remove it all: `cd ~ && rm -rf /tmp/chain-demo`.

Example result: in step 5, the first gave `server.pem: OK` and the chain from depth 0 to 2, the second
`error 20 at 0 depth lookup: unable to get local issuer certificate`, and the third
`error 2 at 1 depth lookup: unable to get issuer certificate`.
:::

### 3.4 What each device holds on XRT-15

Split what each device holds into what proves itself (held by the side that shows) and what checks the peer (held by
the side that checks), and it comes out as follows. No private key moves from the machine that made it.

| Device | Proves itself with | Checks the peer with |
|---|---|---|
| SRV01 (gnmic and the other tools that connect) | `~/pki/client.pem` and `~/pki/client.key` (shown in mutual TLS) | `~/pki/ca.pem` (for peers issued by NMS-LAB-CA). To check XR01's `ems.pem`, that one file |
| SRV01 (telegraf) | The collector's certificate and key (`/etc/telegraf/pki/`, not readable from the lab account as it is) | — (asks for no client certificate) |
| XR01 | `ems.pem` and `ems.key` (shown by the gRPC server) | A CA file to check gNMI clients, and a CA file to check collectors on dial-out. Where they go and how: section 3.2 of the next page |

### 3.5 Pitfalls

- **Handing out a private key**: the CA receives a request, and the checking side receives the CA certificate. Neither
  needs a private key. Hand out `ca.key`, and whoever gets it can make a certificate for any name as NMS-LAB-CA.
- **Turning the check off**: `--skip-verify`, `verify=False` and `hostkey_verify=False` still encrypt, but do not
  check the peer. The problem in section 1.1 stays as it was. Use them only to see the shape of things in a lab.
- **Not reading s_client's result**: the connection goes on even when a check fails. Read `Verify return code`, or add
  `-verify_return_error`.
- **Names and addresses**: a client that connects to an address looks for that IP address in the SAN. A certificate
  that carries only a name (`ems.pem`) does not pass when checked by address.
- **Clocks**: the validity period is compared with the checking side's clock. A device with a wrong clock refuses a
  correct certificate with `not yet valid` or `expired` (section 2.5 used `-attime` in place of the clock).
- **Forgetting the intermediate CA**: if the server does not send the intermediate CA's certificate, the client cannot
  build the path and stops at `20`. Giving the client only the intermediate CA does not help either: it cannot reach the
  root CA and stops at `2` (section 3.3).
- **A CA with the same name**: a matching CA name does not pass if the signature does not match. Hand out CA
  certificates by their content, not by their file name.

## Practice

Tasks M13-3 and M13-4 come after the next page (gNMI and telemetry). Both tasks are rows of the table in section 2.6
of this page: the gNMI line and the telemetry dial-out line.

<p class="tolab"><a href="/_learn?id=XRT-15">Open lab XRT-15 in the workspace</a> — <a href="e2-m13-gnmi-telemetry.html">Next page: streaming state</a></p>

:::note
The output on this page was taken on SRV01 of XRT-15 (Ubuntu 24.04, OpenSSL 3.0.13). The fake CA and certificate, and the test
certificates and servers of section 3.3 (root CA, intermediate CA, self-signed server), were made in a temporary
place for the test and removed at once. The chain sent by www.cisco.com was checked on 16 November 2026. XR01's certificate (`ems.pem`), gnmic's error messages,
and XR01 accepting a client certificate without a SAN come from the measurements on the next page. Sources: RFC 5280
(4.1 basic certificate fields, 4.2.1.6 SAN, 4.2.1.9 basicConstraints, 4.2.1.12 extendedKeyUsage, 6.1 path validation
and the validity period), RFC 8446 (TLS 1.3; 4.2.8 key_share, 4.3.2 CertificateRequest, 4.4.2 Certificate, 4.4.3
CertificateVerify), RFC 2986 (PKCS #10, certificate requests), RFC 4251 (4.1 host keys), and the OpenSSL 3.0 manual
pages (openssl-req, openssl-x509, openssl-verify, openssl-s_client, openssl-s_server, openssl-verification-options). All checked in November 2026.
:::
