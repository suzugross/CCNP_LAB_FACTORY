
## S1 SSH 鍵長/version/show ip ssh  (2026-09-13 09:17)

**S1-0 鍵なしの状態 — RT01# show ip ssh**

```
SSH Disabled - version 2.0
%Please create EC or RSA keys to enable SSH (and of atleast 2048 bits for SSH v2 in case of RSA).
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): NONE
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-0 vty(基線) — RT01# show running-config | section line vty**

```
line vty 0 4
 exec-timeout 0 0
 login local
 transport input ssh
```

**S1-1 鍵なしで ip ssh version 2**

```
ip ssh version 2
---
(応答なし)
```

**S1-1 その後の show ip ssh — RT01# show ip ssh**

```
SSH Disabled - version 2.0
%Please create EC or RSA keys to enable SSH (and of atleast 2048 bits for SSH v2 in case of RSA).
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): NONE
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-1 running-config の ip ssh 行 — RT01# show running-config | include ip ssh**

```
ip ssh bulk-mode 131072
```

**S1-1 ホストから ssh(鍵なし)**

```
debug1: connect to address 10.1.10.45 port 22: Connection refused
ssh: connect to host 10.1.10.45 port 22: Connection refused
```

**S1-2 crypto key generate rsa modulus 512**

```
crypto key generate rsa modulus 512
---
% Invalid input detected at '^' marker.
```

**S1-2 [512] show ip ssh (version 未指定) — RT01# show ip ssh**

```
SSH Disabled - version 2.0
%Please create EC or RSA keys to enable SSH (and of atleast 2048 bits for SSH v2 in case of RSA).
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): NONE
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-2 [512] mypubkey rsa — RT01# show crypto key mypubkey rsa | include Key name|Key type|Usage|bits|Storage**

```

```

**S1-2 [512] ip ssh version 2**

```
ip ssh version 2
---
(応答なし)
```

**S1-2 [512] show ip ssh (version 2 投入後) — RT01# show ip ssh**

```
SSH Disabled - version 2.0
%Please create EC or RSA keys to enable SSH (and of atleast 2048 bits for SSH v2 in case of RSA).
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): NONE
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-2 [512] running-config の ip ssh 行 — RT01# show running-config | include ip ssh**

```
ip ssh bulk-mode 131072
```

**S1-2 [512] OpenSSH 接続段階(legacy alg 許可)**

```
debug1: connect to address 10.1.10.45 port 22: Connection refused
ssh: connect to host 10.1.10.45 port 22: Connection refused
```

**S1-2 [512] OpenSSH 接続段階(既定 alg)**

```
debug1: connect to address 10.1.10.45 port 22: Connection refused
ssh: connect to host 10.1.10.45 port 22: Connection refused
```

**S1-2 [512] paramiko ログイン → NG**

```
NoValidConnectionsError: [Errno None] Unable to connect to port 22 on 10.1.10.45
```

**S1-2 crypto key generate rsa modulus 768**

```
crypto key generate rsa modulus 768
---
% Invalid input detected at '^' marker.
```

**S1-2 [768] show ip ssh (version 未指定) — RT01# show ip ssh**

```
SSH Disabled - version 2.0
%Please create EC or RSA keys to enable SSH (and of atleast 2048 bits for SSH v2 in case of RSA).
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): NONE
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-2 [768] mypubkey rsa — RT01# show crypto key mypubkey rsa | include Key name|Key type|Usage|bits|Storage**

```

```

**S1-2 [768] ip ssh version 2**

```
ip ssh version 2
---
(応答なし)
```

**S1-2 [768] show ip ssh (version 2 投入後) — RT01# show ip ssh**

```
SSH Disabled - version 2.0
%Please create EC or RSA keys to enable SSH (and of atleast 2048 bits for SSH v2 in case of RSA).
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): NONE
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-2 [768] running-config の ip ssh 行 — RT01# show running-config | include ip ssh**

```
ip ssh bulk-mode 131072
```

**S1-2 [768] OpenSSH 接続段階(legacy alg 許可)**

```
debug1: connect to address 10.1.10.45 port 22: Connection refused
ssh: connect to host 10.1.10.45 port 22: Connection refused
```

**S1-2 [768] OpenSSH 接続段階(既定 alg)**

```
debug1: connect to address 10.1.10.45 port 22: Connection refused
ssh: connect to host 10.1.10.45 port 22: Connection refused
```

**S1-2 [768] paramiko ログイン → NG**

```
NoValidConnectionsError: [Errno None] Unable to connect to port 22 on 10.1.10.45
```

**S1-2 crypto key generate rsa modulus 1024**

```
crypto key generate rsa modulus 1024
---
% Invalid input detected at '^' marker.
```

**S1-2 [1024] show ip ssh (version 未指定) — RT01# show ip ssh**

```
SSH Disabled - version 2.0
%Please create EC or RSA keys to enable SSH (and of atleast 2048 bits for SSH v2 in case of RSA).
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): NONE
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-2 [1024] mypubkey rsa — RT01# show crypto key mypubkey rsa | include Key name|Key type|Usage|bits|Storage**

```

```

**S1-2 [1024] ip ssh version 2**

```
ip ssh version 2
---
(応答なし)
```

**S1-2 [1024] show ip ssh (version 2 投入後) — RT01# show ip ssh**

```
SSH Disabled - version 2.0
%Please create EC or RSA keys to enable SSH (and of atleast 2048 bits for SSH v2 in case of RSA).
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): NONE
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-2 [1024] running-config の ip ssh 行 — RT01# show running-config | include ip ssh**

```
ip ssh bulk-mode 131072
```

**S1-2 [1024] OpenSSH 接続段階(legacy alg 許可)**

```
debug1: connect to address 10.1.10.45 port 22: Connection refused
ssh: connect to host 10.1.10.45 port 22: Connection refused
```

**S1-2 [1024] OpenSSH 接続段階(既定 alg)**

```
debug1: connect to address 10.1.10.45 port 22: Connection refused
ssh: connect to host 10.1.10.45 port 22: Connection refused
```

**S1-2 [1024] paramiko ログイン → NG**

```
NoValidConnectionsError: [Errno None] Unable to connect to port 22 on 10.1.10.45
```

**S1-2 crypto key generate rsa modulus 2048**

```
crypto key generate rsa modulus 2048
---
% The key modulus size is 2048 bits
% Generating 2048 bit RSA keys, keys will be non-exportable...
```

**S1-2 [2048] show ip ssh (version 未指定) — RT01# show ip ssh**

```
SSH Enabled - version 2.0
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): RT01.ccnp.local
Modulus Size : 2048 bits
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCvop4vrt73V98HI9/PUYWLMOp9KFZjgnbMBWcWyo9H
fCn3Mnvn/yFYqoodVQvW2RV3Cjf41GkZnrRQfQMZ+0BAH451QRR8ZDXdN3s7I4XG7EM4+nyGCcXtV2tp
eB/6rdn19IZ2I7mslHGKOZZtR1c+C4Gpy/qjQ2Ie5IEbIzDVcsEHea2ROuD7xUucL4P01xBkuvvU++17
p+jHOyaM020SlN1+eAlnjzK4zHyOjB87YltsUty+wIs/+F6Ve10hsuwIXeFM8oPTKC0q4WGJlzuNrzG3
xr8FolKRkY+Gg7184xy7mKM35j6xvYWweTbRW+xuBc+WJEuVH3JotADHJ2J9                    
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-2 [2048] mypubkey rsa — RT01# show crypto key mypubkey rsa | include Key name|Key type|Usage|bits|Storage**

```
Key name: RT01.ccnp.local
Key type: RSA KEYS      2048 bits
 Storage Device: not specified
 Usage: General Purpose Key
Key name: RT01.ccnp.local.server
Key type: RSA KEYS      2176 bits
 Usage: Encryption Key
```

**S1-2 [2048] ip ssh version 2**

```
ip ssh version 2
---
(応答なし)
```

**S1-2 [2048] show ip ssh (version 2 投入後) — RT01# show ip ssh**

```
SSH Enabled - version 2.0
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): RT01.ccnp.local
Modulus Size : 2048 bits
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCvop4vrt73V98HI9/PUYWLMOp9KFZjgnbMBWcWyo9H
fCn3Mnvn/yFYqoodVQvW2RV3Cjf41GkZnrRQfQMZ+0BAH451QRR8ZDXdN3s7I4XG7EM4+nyGCcXtV2tp
eB/6rdn19IZ2I7mslHGKOZZtR1c+C4Gpy/qjQ2Ie5IEbIzDVcsEHea2ROuD7xUucL4P01xBkuvvU++17
p+jHOyaM020SlN1+eAlnjzK4zHyOjB87YltsUty+wIs/+F6Ve10hsuwIXeFM8oPTKC0q4WGJlzuNrzG3
xr8FolKRkY+Gg7184xy7mKM35j6xvYWweTbRW+xuBc+WJEuVH3JotADHJ2J9                    
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-2 [2048] running-config の ip ssh 行 — RT01# show running-config | include ip ssh**

```
ip ssh bulk-mode 131072
```

**S1-2 [2048] OpenSSH 接続段階(legacy alg 許可)**

```
debug1: Remote protocol version 2.0, remote software version Cisco-1.25
debug1: compat_banner: match: Cisco-1.25 pat Cisco-1.* compat 0x60000000
debug1: kex: algorithm: curve25519-sha256
debug1: kex: host key algorithm: rsa-sha2-512
debug1: Server host key: ssh-rsa SHA256:4/GvV2oMk53vyh1kz1QTLfNcc9LBqGzz1P4G36ykoRc
debug1: Authentications that can continue: publickey,keyboard-interactive,password
debug1: Authentications that can continue: publickey,keyboard-interactive,password
SUZUKI@10.1.10.45: Permission denied (publickey,keyboard-interactive,password).
```

**S1-2 [2048] OpenSSH 接続段階(既定 alg)**

```
debug1: Remote protocol version 2.0, remote software version Cisco-1.25
debug1: compat_banner: match: Cisco-1.25 pat Cisco-1.* compat 0x60000000
debug1: kex: algorithm: curve25519-sha256
debug1: kex: host key algorithm: rsa-sha2-512
debug1: Server host key: ssh-rsa SHA256:4/GvV2oMk53vyh1kz1QTLfNcc9LBqGzz1P4G36ykoRc
debug1: Authentications that can continue: publickey,keyboard-interactive,password
debug1: Authentications that can continue: publickey,keyboard-interactive,password
SUZUKI@10.1.10.45: Permission denied (publickey,keyboard-interactive,password).
```

**S1-2 [2048] paramiko ログイン → OK**

```



RT01#terminal length 0
RT01#show ip ssh
SSH Enabled - version 2.0
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): RT01.ccnp.local
Modulus Size : 2048 bits
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCvop4vrt73V98HI9/PUYWLMOp9KFZjgnbMBWcWyo9H
fCn3Mnvn/yFYqoodVQvW2RV3Cjf41GkZnrRQfQMZ+0BAH451QRR8ZDXdN3s7I4XG7EM4+nyGCcXtV2tp
eB/6rdn19IZ2I7mslHGKOZZtR1c+C4Gpy/qjQ2Ie5IEbIzDVcsEHea2ROuD7xUucL4P01xBkuvvU++17
p+jHOyaM020SlN1+eAlnjzK4zHyOjB87YltsUty+wIs/+F6Ve10hsuwIXeFM8oPTKC0q4WGJlzuNrzG3
xr8FolKRkY+Gg7184xy7mKM35j6xvYWweTbRW+xuBc+WJEuVH3JotADHJ2J9                    
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
RT01#
```

**S1-3 ip ssh version 1 (2048 鍵)**

```
ip ssh version 1
---
% Invalid input detected at '^' marker.
```

**S1-3 show ip ssh — RT01# show ip ssh**

```
SSH Enabled - version 2.0
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 120 secs; Authentication retries: 3
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): RT01.ccnp.local
Modulus Size : 2048 bits
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCvop4vrt73V98HI9/PUYWLMOp9KFZjgnbMBWcWyo9H
fCn3Mnvn/yFYqoodVQvW2RV3Cjf41GkZnrRQfQMZ+0BAH451QRR8ZDXdN3s7I4XG7EM4+nyGCcXtV2tp
eB/6rdn19IZ2I7mslHGKOZZtR1c+C4Gpy/qjQ2Ie5IEbIzDVcsEHea2ROuD7xUucL4P01xBkuvvU++17
p+jHOyaM020SlN1+eAlnjzK4zHyOjB87YltsUty+wIs/+F6Ve10hsuwIXeFM8oPTKC0q4WGJlzuNrzG3
xr8FolKRkY+Gg7184xy7mKM35j6xvYWweTbRW+xuBc+WJEuVH3JotADHJ2J9                    
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-4 time-out 60 / retries 2**

```
no ip ssh version 1
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 2
---
% Invalid input detected at '^' marker.
```

**S1-4 show ip ssh — RT01# show ip ssh**

```
SSH Enabled - version 2.0
Authentication methods:publickey,keyboard-interactive,password
Authentication Publickey Algorithms:ssh-rsa,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,ssh-ed25519,x509v3-ecdsa-sha2-nistp256,x509v3-ecdsa-sha2-nistp384,x509v3-ecdsa-sha2-nistp521,rsa-sha2-256,rsa-sha2-512,x509v3-rsa2048-sha256
Hostkey Algorithms:ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,rsa-sha2-512,rsa-sha2-256,ssh-rsa
Encryption Algorithms:chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-gcm,aes256-gcm,aes128-ctr,aes192-ctr,aes256-ctr
MAC Algorithms:hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
KEX Algorithms:curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512
Authentication timeout: 60 secs; Authentication retries: 2
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): RT01.ccnp.local
Modulus Size : 2048 bits
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCvop4vrt73V98HI9/PUYWLMOp9KFZjgnbMBWcWyo9H
fCn3Mnvn/yFYqoodVQvW2RV3Cjf41GkZnrRQfQMZ+0BAH451QRR8ZDXdN3s7I4XG7EM4+nyGCcXtV2tp
eB/6rdn19IZ2I7mslHGKOZZtR1c+C4Gpy/qjQ2Ie5IEbIzDVcsEHea2ROuD7xUucL4P01xBkuvvU++17
p+jHOyaM020SlN1+eAlnjzK4zHyOjB87YltsUty+wIs/+F6Ve10hsuwIXeFM8oPTKC0q4WGJlzuNrzG3
xr8FolKRkY+Gg7184xy7mKM35j6xvYWweTbRW+xuBc+WJEuVH3JotADHJ2J9                    
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S1-4 running-config — RT01# show running-config | include ip ssh**

```
ip ssh bulk-mode 131072
ip ssh time-out 60
ip ssh authentication-retries 2
```

## S2 vty transport/login/access-class  (2026-09-13 09:18)

**S2-1 vty transport input を既定へ**

```
line vty 0 4
default transport input
---
(応答なし)
```

**S2-1 running-config(既定の transport) — RT01# show running-config | section line vty**

```
line vty 0 4
 exec-timeout 0 0
 login local
 transport input ssh
```

**S2-1 show line vty 0 (Allowed transports) — RT01# show line vty 0 | include transport|Allowed**

```
Allowed input transports are ssh.
Allowed output transports are lat pad telnet rlogin mop ssh nasi.
Preferred transport is lat.
```

**S2-1 ホストから telnet(23) 既定**

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**S2-1 transport input ssh の show line — RT01# show line vty 0 | include transport|Allowed**

```
Allowed input transports are ssh.
Allowed output transports are lat pad telnet rlogin mop ssh nasi.
Preferred transport is lat.
```

**S2-1 ホストから telnet(23) ssh 限定後**

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**S2-1 transport input telnet のとき ssh**

```
debug1: connect to address 10.1.10.45 port 22: Connection refused
ssh: connect to host 10.1.10.45 port 22: Connection refused
```

**S2-2 login(line password) で SSH**

```
line vty 0 4
login
password vtypass
---
% Login disabled on line 2, until 'password' is set
% Login disabled on line 3, until 'password' is set
% Login disabled on line 4, until 'password' is set
% Login disabled on line 5, until 'password' is set
% Login disabled on line 6, until 'password' is set
```

**S2-2 login+password: user SUZUKI/vtypass → NG**

```
AuthenticationException: Authentication failed.
```

**S2-2 login+password: user nobody/vtypass → NG**

```
AuthenticationException: Authentication failed.
```

**S2-2 login+password: user SUZUKI/CCNP(username の secret) → NG**

```
AuthenticationException: Authentication failed.
```

**S2-2 login だが password なし**

```
line vty 0 4
no password
login
---
% Login disabled on line 2, until 'password' is set
% Login disabled on line 3, until 'password' is set
% Login disabled on line 4, until 'password' is set
% Login disabled on line 5, until 'password' is set
% Login disabled on line 6, until 'password' is set
```

**S2-2 login/password なし → NG**

```
AuthenticationException: Authentication failed.
```

**S2-2 ログ(SSH/LOGIN) — RT01# show logging | include SSH|SEC_LOGIN|LOGIN**

```
*Sep 13 09:17:22.557: %SSH-5-ENABLED: SSH 2.0 has been enabled
*Sep 13 09:17:27.970: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 0) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:30.101: %SSH-5-SSH2_USERAUTH: User '' authentication for SSH2 Session from 10.1.10.6 (tty = 0) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Failed
*Sep 13 09:17:30.101: %SSH-5-SSH2_CLOSE: SSH2 Session from 10.1.10.6 (tty = 0) for user '' using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' closed
*Sep 13 09:17:30.125: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 1) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:32.249: %SSH-5-SSH2_USERAUTH: User '' authentication for SSH2 Session from 10.1.10.6 (tty = 1) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Failed
*Sep 13 09:17:32.250: %SSH-5-SSH2_CLOSE: SSH2 Session from 10.1.10.6 (tty = 1) for user '' using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' closed
*Sep 13 09:17:32.394: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 0) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:32.535: %SEC_LOGIN-5-LOGIN_SUCCESS: Login Success [user: SUZUKI] [Source: 10.1.10.6] [localport: 22] at 09:17:32 UTC Sun Sep 13 2026
*Sep 13 09:17:32.535: %SSH-5-SSH2_USERAUTH: User 'SUZUKI' authentication for SSH2 Session from 10.1.10.6 (tty = 0) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:38.296: %SSH-5-SSH2_CLOSE: SSH2 Session from 10.1.10.6 (tty = 0) for user '' using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' closed
*Sep 13 09:17:47.082: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 0) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:49.370: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 1) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:51.703: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 2) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:54.704: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 3) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
```

**S2-2 no login**

```
line vty 0 4
no login
---
(応答なし)
```

**S2-2 no login → NG**

```
AuthenticationException: Authentication failed.
```

**S2-2 login local + 未定義ユーザ → NG**

```
NoValidConnectionsError: [Errno None] Unable to connect to port 22 on 10.1.10.45
```

**S2-2 ログ(SSH/LOGIN) その2 — RT01# show logging | include SSH|SEC_LOGIN|LOGIN**

```
*Sep 13 09:17:22.557: %SSH-5-ENABLED: SSH 2.0 has been enabled
*Sep 13 09:17:27.970: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 0) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:30.101: %SSH-5-SSH2_USERAUTH: User '' authentication for SSH2 Session from 10.1.10.6 (tty = 0) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Failed
*Sep 13 09:17:30.101: %SSH-5-SSH2_CLOSE: SSH2 Session from 10.1.10.6 (tty = 0) for user '' using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' closed
*Sep 13 09:17:30.125: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 1) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:32.249: %SSH-5-SSH2_USERAUTH: User '' authentication for SSH2 Session from 10.1.10.6 (tty = 1) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Failed
*Sep 13 09:17:32.250: %SSH-5-SSH2_CLOSE: SSH2 Session from 10.1.10.6 (tty = 1) for user '' using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' closed
*Sep 13 09:17:32.394: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 0) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:32.535: %SEC_LOGIN-5-LOGIN_SUCCESS: Login Success [user: SUZUKI] [Source: 10.1.10.6] [localport: 22] at 09:17:32 UTC Sun Sep 13 2026
*Sep 13 09:17:32.535: %SSH-5-SSH2_USERAUTH: User 'SUZUKI' authentication for SSH2 Session from 10.1.10.6 (tty = 0) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:38.296: %SSH-5-SSH2_CLOSE: SSH2 Session from 10.1.10.6 (tty = 0) for user '' using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' closed
*Sep 13 09:17:47.082: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 0) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:49.370: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 1) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:51.703: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 2) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:54.704: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 3) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:17:57.950: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 4) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
```

**S2-3 access-class 10 in (ホスト不許可)**

```
access-list 10 permit 10.1.10.99
line vty 0 4
access-class 10 in
---
(応答なし)
```

**S2-3 ホストから ssh(ACL 不許可)**

```
debug1: connect to address 10.1.10.45 port 22: Connection refused
ssh: connect to host 10.1.10.45 port 22: Connection refused
```

**S2-3 ホストから tcp 22**

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**S2-3 ACL カウンタ — RT01# show access-lists 10**

```
Standard IP access list 10
    10 permit 10.1.10.99
```

**S2-3 access-class 55 in (ACL 55 未定義)**

```
line vty 0 4
access-class 55 in
---
(応答なし)
```

**S2-3 未定義 ACL の access-class → ssh NG**

```
NoValidConnectionsError: [Errno None] Unable to connect to port 22 on 10.1.10.45
```

**S2-3 ACL 10 permit ホスト → ssh NG**

```
NoValidConnectionsError: [Errno None] Unable to connect to port 22 on 10.1.10.45
```

**S2-3 ACL カウンタ(許可後) — RT01# show access-lists 10**

```
Standard IP access list 10
    20 permit 10.1.10.6
    10 permit 10.1.10.99
```

**S2-4 vty の本数 — RT01# show line | include VTY|vty**

```
*     2 VTY              -    -      -    -    -      3       0     0/0       -
*     3 VTY              -    -      -    -    -      2       0     0/0       -
*     4 VTY              -    -      -    -    -      1       0     0/0       -
*     5 VTY              -    -      -    -    -      1       0     0/0       -
*     6 VTY              -    -      -    -    -      1       0     0/0       -
```

## S3 (例外で中断)  (2026-09-13 09:18)

**S3-0 show logging(基線・全文) — RT01# show logging**

```
Syslog logging: enabled (0 messages dropped, 4 messages rate-limited, 0 flushes, 0 overruns, xml disabled, filtering disabled)

No Active Message Discriminator.



No Inactive Message Discriminator.


    Console logging: disabled
    Monitor logging: level debugging, 0 messages logged, xml disabled,
                     filtering disabled
    Buffer logging:  level debugging, 228 messages logged, xml disabled,
                    filtering disabled
    Exception Logging: size (4096 bytes)
    Count and timestamp logging messages: disabled
    Persistent logging: disabled
    Trap logging: level informational, 230 message lines logged
        Logging Source-Interface:       VRF Name:

Log Buffer (4096 bytes):

*Sep 13 09:18:06.323: %SYS-5-CONFIG_I: Configured from console by console
```

**S3-0 running-config の logging 行 — RT01# show running-config | include logging|service timestamps|service sequence**

```
service timestamps debug datetime msec
service timestamps log datetime msec
no logging console
no logging btrace
 logging synchronous
```

**S3-1 send log 4 SVC-TEST-WARN の応答**

```

```

**S3-1 send log 6 SVC-TEST-INFO の応答**

```

```

**S3-1 buffer に入った send log — RT01# show logging | include SVC-TEST**

```
*Sep 13 09:18:08.457: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TEST-WARN
```

**S3-2 logging host + trap warnings**

```
logging host 10.1.10.6 transport udp port 5514
logging trap warnings
---
(応答なし)
```

**S3-2 ホストが受信した syslog(trap warnings)**

```
<188>233: *Sep 13 09:18:12.291: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-WARN4
```

**S3-2 show logging の宛先行 — RT01# show logging | include Trap|Logging to|Buffer|Console|Monitor**

```
    Console logging: disabled
    Monitor logging: level debugging, 0 messages logged, xml disabled,
    Buffer logging:  level debugging, 241 messages logged, xml disabled,
    Trap logging: level warnings, 233 message lines logged
        Logging to 10.1.10.6  (udp port 5514, audit disabled,
Log Buffer (4096 bytes):
*Sep 13 09:18:09.564: %SYS-6-LOGGINGHOST_STARTSTOP: Logging to host 10.1.10.6 port 0 CLI Request Triggered
*Sep 13 09:18:12.292: %SYS-6-LOGGINGHOST_STARTSTOP: Logging to host 10.1.10.6 port 5514 started - CLI initiated
```

**S3-2 buffer の中身 — RT01# show logging | include SVC-|UPDOWN|CHANGED**

```
*Sep 13 09:18:08.457: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TEST-WARN
*Sep 13 09:18:08.759: %SYS-6-USERLOG_INFO: Message from tty0(user id: ): SVC-TEST-INFO
*Sep 13 09:18:11.990: %SYS-3-USERLOG_ERR: Message from tty0(user id: ): SVC-ERR3
*Sep 13 09:18:12.291: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-WARN4
*Sep 13 09:18:12.593: %SYS-5-USERLOG_NOTICE: Message from tty0(user id: ): SVC-NOTE5
*Sep 13 09:18:12.898: %SYS-6-USERLOG_INFO: Message from tty0(user id: ): SVC-INFO6
*Sep 13 09:18:15.402: %LINK-5-CHANGED: Interface Ethernet0/1, changed state to administratively down
*Sep 13 09:18:17.923: %LINK-5-UPDOWN: Interface Ethernet0/1, changed state to up
```

**S3-2 trap informational(既定)で受信**

```
<189>234: *Sep 13 09:18:23.080: %SYS-5-CONFIG_I: Configured from console by console
<190>235: *Sep 13 09:18:23.282: %SYS-6-USERLOG_INFO: Message from tty0(user id: ): SVC-INFO6b
```

**S3-3 logging buffered warnings**

```
logging buffered warnings
---
(応答なし)
```

**S3-3 buffered warnings のときの show logging(全文) — RT01# show logging**

```
Syslog logging: enabled (0 messages dropped, 4 messages rate-limited, 0 flushes, 0 overruns, xml disabled, filtering disabled)

No Active Message Discriminator.



No Inactive Message Discriminator.


    Console logging: disabled
    Monitor logging: level debugging, 0 messages logged, xml disabled,
                     filtering disabled
    Buffer logging:  level warnings, 1 messages logged, xml disabled,
                    filtering disabled
    Exception Logging: size (4096 bytes)
    Count and timestamp logging messages: disabled
    Persistent logging: disabled
    Trap logging: level informational, 243 message lines logged
        Logging to 10.1.10.6  (udp port 5514, audit disabled,
              link up),
              11 message lines logged, 
              0 message lines rate-limited, 
              0 message lines dropped-by-MD, 
              xml disabled, sequence number disabled
              filtering disabled
        Logging Source-Interface:       VRF Name:

Log Buffer (4096 bytes):

*Sep 13 09:18:27.621: %SYS-3-USERLOG_ERR: Message from tty0(user id: ): SVC-ERR3c
```

- S3 例外: NoValidConnectionsError: [Errno None] Unable to connect to port 22 on 10.1.10.45

## S4 service timestamps  (2026-09-13 09:18)

**S4-0 show clock(NTP 未同期) — RT01# show clock**

```
*09:18:35.291 UTC Sun Sep 13 2026
```

**S4-0 show clock detail — RT01# show clock detail**

```
*09:18:35.594 UTC Sun Sep 13 2026
Time source is hardware calendar
```

**S4 [基線] running-config — RT01# show running-config | include service timestamps|service sequence|clock timezone**

```
service timestamps debug datetime msec
service timestamps log datetime msec
```

**S4 [基線] buffer の該当行 — RT01# show logging | include SVC-TS**

```

```

**S4 [datetime] running-config — RT01# show running-config | include service timestamps|service sequence|clock timezone**

```
service timestamps debug datetime msec
service timestamps log datetime
```

**S4 [datetime] buffer の該当行 — RT01# show logging | include SVC-TS**

```
*Sep 13 09:18:36.198: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-e:g7
```

**S4 [datetime msec] running-config — RT01# show running-config | include service timestamps|service sequence|clock timezone**

```
service timestamps debug datetime msec
service timestamps log datetime msec
```

**S4 [datetime msec] buffer の該当行 — RT01# show logging | include SVC-TS**

```
*Sep 13 09:18:36.198: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-e:g7
*Sep 13 09:18:37: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
```

**S4 [datetime msec localtime show-timezone (clock timezone JST 9)] running-config — RT01# show running-config | include service timestamps|service sequence|clock timezone**

```
service timestamps debug datetime msec
service timestamps log datetime msec localtime show-timezone
clock timezone JST 9 0
```

**S4 [datetime msec localtime show-timezone (clock timezone JST 9)] buffer の該当行 — RT01# show logging | include SVC-TS**

```
*Sep 13 09:18:36.198: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-e:g7
*Sep 13 09:18:37: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 09:18:39.349: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
```

**S4 [datetime year] running-config — RT01# show running-config | include service timestamps|service sequence|clock timezone**

```
service timestamps debug datetime msec
service timestamps log datetime year
clock timezone JST 9 0
```

**S4 [datetime year] buffer の該当行 — RT01# show logging | include SVC-TS**

```
*Sep 13 09:18:36.198: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-e:g7
*Sep 13 09:18:37: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 09:18:39.349: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 18:18:40.962 JST: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
```

**S4 [datetime localtime (timezone JST)] running-config — RT01# show running-config | include service timestamps|service sequence|clock timezone**

```
service timestamps debug datetime msec
service timestamps log datetime localtime
clock timezone JST 9 0
```

**S4 [datetime localtime (timezone JST)] buffer の該当行 — RT01# show logging | include SVC-TS**

```
*Sep 13 09:18:36.198: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-e:g7
*Sep 13 09:18:37: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 09:18:39.349: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 18:18:40.962 JST: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 2026 09:18:42: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
```

**S4 [uptime] running-config — RT01# show running-config | include service timestamps|service sequence|clock timezone**

```
service timestamps debug datetime msec
service timestamps log uptime
clock timezone JST 9 0
```

**S4 [uptime] buffer の該当行 — RT01# show logging | include SVC-TS**

```
*Sep 13 09:18:36.198: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-e:g7
*Sep 13 09:18:37: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 09:18:39.349: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 18:18:40.962 JST: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 2026 09:18:42: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 18:18:44: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
```

**S4 [no service timestamps log] running-config — RT01# show running-config | include service timestamps|service sequence|clock timezone**

```
service timestamps debug datetime msec
no service timestamps log
clock timezone JST 9 0
```

**S4 [no service timestamps log] buffer の該当行 — RT01# show logging | include SVC-TS**

```
*Sep 13 09:18:36.198: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-e:g7
*Sep 13 09:18:37: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 09:18:39.349: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 18:18:40.962 JST: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 2026 09:18:42: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 18:18:44: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
00:04:18: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-uptime
```

**S4 [service sequence-numbers + datetime msec] running-config — RT01# show running-config | include service timestamps|service sequence|clock timezone**

```
service timestamps debug datetime msec
service timestamps log datetime msec
service sequence-numbers
clock timezone JST 9 0
```

**S4 [service sequence-numbers + datetime msec] buffer の該当行 — RT01# show logging | include SVC-TS**

```
*Sep 13 09:18:36.198: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-e:g7
*Sep 13 09:18:37: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 09:18:39.349: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 18:18:40.962 JST: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 2026 09:18:42: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
*Sep 13 18:18:44: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-datetime
00:04:18: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-uptime
%SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TS-no
```

**S4 復旧後 — RT01# show running-config | include service timestamps**

```
service timestamps debug datetime msec
service timestamps log datetime msec
```

## S5 debug condition interface  (2026-09-13 09:19)

**S5-1 debug condition interface Ethernet0/0 — RT01# debug condition interface Ethernet0/0**

```
Condition 1 set
```

**S5-1 show debug condition — RT01# show debug condition**

```

Condition 1: interface Et0/0 (1 flags triggered)
	Flags: Et0/0
```

**S5-1 debug ip icmp — RT01# debug ip icmp**

```
ICMP packet debugging is on
```

**S5-1 debug ip packet — RT01# debug ip packet**

```
IP packet debugging is on
```

**S5-1 show debugging — RT01# show debugging**

```
Generic IP:
  ICMP packet debugging is on
  IP packet debugging is on
Packet Infra debugs:

Ip Address                                               Port
------------------------------------------------------|----------


Condition 1: interface Et0/0 (1 flags triggered)
	Flags: Et0/0
```

**S5-1 条件あり: RT02→e0/0 とホスト→e0/3 の ping のデバッグ出力 — RT01# show logging | include ICMP|IP:**

```
*Sep 13 09:18:55.037: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 13 09:18:55.037: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, rcvd 2
*Sep 13 09:18:55.037: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, stop process pak for forus packet
*Sep 13 09:18:55.037: IP: tableid=0, s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (Ethernet0/0) nexthop=10.99.12.1, routed via RIB
*Sep 13 09:18:55.037: ICMP: echo reply sent, src 10.99.12.1, dst 10.99.12.2, topology BASE, dscp 0 topoid 0
*Sep 13 09:18:55.037: IP: tableid=0, s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0) nexthop=10.99.12.2, routed via FIB
*Sep 13 09:18:55.037: IP: s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0), len 100, sending
*Sep 13 09:18:55.037: IP: s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0), len 100, sending full packet
*Sep 13 09:18:55.038: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 13 09:18:55.038: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, rcvd 2
*Sep 13 09:18:55.038: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, stop process pak for forus packet
*Sep 13 09:18:55.038: IP: tableid=0, s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (Ethernet0/0) nexthop=10.99.12.1, routed via RIB
*Sep 13 09:18:55.038: ICMP: echo reply sent, src 10.99.12.1, dst 10.99.12.2, topology BASE, dscp 0 topoid 0
*Sep 13 09:18:55.038: IP: tableid=0, s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0) nexthop=10.99.12.2, routed via FIB
*Sep 13 09:18:55.038: IP: s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0), len 100, sending
*Sep 13 09:18:55.038: IP: s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0), len 100, sending full packet
*Sep 13 09:18:55.199: IP: s=10.1.10.6 (Ethernet0/3), d=10.1.10.45 (nil), len 84, stop process pak for forus packet
*Sep 13 09:18:55.199: ICMP: echo reply sent, src 10.1.10.45, dst 10.1.10.6, topology BASE, dscp 0 topoid 0
*Sep 13 09:18:56.200: IP: s=10.1.10.6 (Ethernet0/3), d=10.1.10.45 (nil), len 84, stop process pak for forus packet
*Sep 13 09:18:56.200: ICMP: echo reply sent, src 10.1.10.45, dst 10.1.10.6, topology BASE, dscp 0 topoid 0
```

**S5-2 条件解除 — RT01# no debug condition interface Ethernet0/0**

```
This condition is the last interface condition set.
Removing all conditions may cause a flood of debugging
messages to result, unless specific debugging flags
are first removed.

Proceed with removal? [yes/no]: y
Condition 1 has been removed
```

**S5-2 show debug condition — RT01# show debug condition**

```


% No conditions found
```

**S5-2 条件なし: 同じ 2 経路の ping — RT01# show logging | include ICMP|IP:**

```
*Sep 13 09:19:00.042: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 13 09:19:00.042: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, rcvd 2
*Sep 13 09:19:00.042: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, stop process pak for forus packet
*Sep 13 09:19:00.042: IP: tableid=0, s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (Ethernet0/0) nexthop=10.99.12.1, routed via RIB
*Sep 13 09:19:00.042: ICMP: echo reply sent, src 10.99.12.1, dst 10.99.12.2, topology BASE, dscp 0 topoid 0
*Sep 13 09:19:00.042: IP: tableid=0, s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0) nexthop=10.99.12.2, routed via FIB
*Sep 13 09:19:00.042: IP: s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0), len 100, sending
*Sep 13 09:19:00.042: IP: s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0), len 100, sending full packet
*Sep 13 09:19:00.043: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 13 09:19:00.043: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, rcvd 2
*Sep 13 09:19:00.043: IP: s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (nil), len 100, stop process pak for forus packet
*Sep 13 09:19:00.043: IP: tableid=0, s=10.99.12.2 (Ethernet0/0), d=10.99.12.1 (Ethernet0/0) nexthop=10.99.12.1, routed via RIB
*Sep 13 09:19:00.043: ICMP: echo reply sent, src 10.99.12.1, dst 10.99.12.2, topology BASE, dscp 0 topoid 0
*Sep 13 09:19:00.043: IP: tableid=0, s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0) nexthop=10.99.12.2, routed via FIB
*Sep 13 09:19:00.043: IP: s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0), len 100, sending
*Sep 13 09:19:00.043: IP: s=10.99.12.1 (local), d=10.99.12.2 (Ethernet0/0), len 100, sending full packet
*Sep 13 09:19:00.200: IP: s=10.1.10.6 (Ethernet0/3), d=10.1.10.45 (nil), len 84, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 13 09:19:00.200: IP: s=10.1.10.6 (Ethernet0/3), d=10.1.10.45 (nil), len 84, rcvd 2
*Sep 13 09:19:00.200: IP: s=10.1.10.6 (Ethernet0/3), d=10.1.10.45 (nil), len 84, stop process pak for forus packet
*Sep 13 09:19:00.200: IP: tableid=0, s=10.1.10.6 (Ethernet0/3), d=10.1.10.45 (Ethernet0/3) nexthop=10.1.10.45, routed via RIB
*Sep 13 09:19:00.200: ICMP: echo reply sent, src 10.1.10.45, dst 10.1.10.6, topology BASE, dscp 0 topoid 0
*Sep 13 09:19:00.200: IP: tableid=0, s=10.1.10.45 (local), d=10.1.10.6 (Ethernet0/3) nexthop=10.1.10.6, routed via FIB
*Sep 13 09:19:00.200: IP: s=10.1.10.45 (local), d=10.1.10.6 (Ethernet0/3), len 84, sending
*Sep 13 09:19:00.200: IP: s=10.1.10.45 (local), d=10.1.10.6 (Ethernet0/3), len 84, sending full packet
*Sep 13 09:19:01.245: IP: s=10.1.10.6 (Ethernet0/3), d=10.1.10.45 (nil), len 84, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 13 09:19:01.245: IP: s=10.1.10.6 (Ethernet0/3), d=10.1.10.45 (nil), len 84, rcvd 2
*Sep 13 09:19:01.245: IP: s=10.1.10.6 (Ethernet0/3), d=10.1.10.45 (nil), len 84, stop process pak for forus packet
*Sep 13 09:19:01.245: IP: tableid=0, s=10.1.10.6 (Ethernet0/3), d=10.1.10.45 (Ethernet0/3) nexthop=10.1.10.45, routed via RIB
*Sep 13 09:19:01.245: ICMP: echo reply sent, src 10.1.10.45, dst 10.1.10.6, topology BASE, dscp 0 topoid 0
*Sep 13 09:19:01.245: IP: tableid=0, s=10.1.10.45 (local), d=10.1.10.6 (Ethernet0/3) nexthop=10.1.10.6, routed via FIB
*Sep 13 09:19:01.245: IP: s=10.1.10.45 (local), d=10.1.10.6 (Ethernet0/3), len 84, sending
*Sep 13 09:19:01.245: IP: s=10.1.10.45 (local), d=10.1.10.6 (Ethernet0/3), len 84, sending full packet
```

## S8 archive  (2026-09-13 09:19)

**S8-0 show archive(未構成) — RT01# show archive**

```
 Archive feature not enabled
```

**S8-0 show archive log config all(未構成) — RT01# show archive log config all**

```
% Config Logger disabled.
```

**S8-0 手動バックアップ — RT01# copy running-config flash:manual.cfg**

```
*Sep 13 09:19:04.780: %SYS-5-LOG_CONFIG_CHANGE: Console logging: level debugging, xml disabled, filtering disabled
*Sep 13 09:19:04.894: %SYS-5-LOG_CONFIG_CHANGE: Buffer logging: level debugging, xml disabled, filtering disabled, size (8192)
*Sep 13 09:19:05.182: %SYS-5-CONFIG_I: Configured from console by console
```

**S8-1 archive 未構成で configure replace — RT01# configure replace flash:manual.cfg force**

```
*Sep 13 09:19:16.400: %LINEPROTO-5-UPDOWN: Line protocol on Interface Loopback55, changed state to up
```

**S8-1 Loopback55 は残っているか — RT01# show running-config | include Loopback55**

```
configure replace flash:manual.cfg force
                       ^
% Invalid input detected at '^' marker.
```

**S8-2 archive path/write-memory/time-period**

```
archive
path flash:RT01-bk
write-memory
time-period 1440
---
% Invalid input detected at '^' marker.
```

**S8-2 show archive(保存前) — RT01# show archive**

```
 Archive feature not enabled
```

**S8-2 write memory — RT01# write memory**

```
Building configuration...
[OK]
```

**S8-2 show archive(write 後) — RT01# show archive**

```
*Sep 13 09:19:27.881: %SYS-5-CONFIG_I: Configured from console by console
```

**S8-2 archive config(手動) — RT01# archive config**

```
show archive
 Archive feature not enabled
```

**S8-2 show archive(手動後) — RT01# show archive**

```
archive config
 Archive feature not enabled
% Error caught by command handler
```

**S8-2 dir — RT01# dir flash: | include RT01-bk|manual**

```
show archive
 Archive feature not enabled
```

**S8-3 log config / logging enable (hidekeys なし)**

```
archive
log config
logging enable
---
(応答なし)
```

**S8-3 hidekeys なし — RT01# show archive log config all**

```
 idx   sess           user@line      Logged command
    3     1        console@console  |  logging enable 
    4     2        console@console  |username test1 secret *
    5     2        console@console  |!config: USER TABLE MODIFIED
    6     2        console@console  |snmp-server community * ro 
    7     2        console@console  |ntp authentication-key 5 md5 *
    8     2        console@console  |enable secret *
```

**S8-3 hidekeys**

```
archive
log config
hidekeys
---
(応答なし)
```

**S8-3 hidekeys あり — RT01# show archive log config all**

```
 idx   sess           user@line      Logged command
    3     1        console@console  |  logging enable 
    4     2        console@console  |username test1 secret *
    5     2        console@console  |!config: USER TABLE MODIFIED
    6     2        console@console  |snmp-server community * ro 
    7     2        console@console  |ntp authentication-key 5 md5 *
    8     2        console@console  |enable secret *
    9     3        console@console  |archive 
   10     3        console@console  | log config 
   11     3        console@console  |  hidekeys 
   12     4        console@console  |username test2 secret *
   13     4        console@console  |!config: USER TABLE MODIFIED
   14     4        console@console  |snmp-server community * ro 
   15     4        console@console  |ntp authentication-key 6 md5 *
```

**S8-3 notify syslog**

```
archive
log config
notify syslog
---
(応答なし)
```

**S8-3 notify syslog の出方 — RT01# show logging | include PARSER|CONFIG**

```
*Sep 13 09:19:04.780: %SYS-5-LOG_CONFIG_CHANGE: Console logging: level debugging, xml disabled, filtering disabled
*Sep 13 09:19:04.894: %SYS-5-LOG_CONFIG_CHANGE: Buffer logging: level debugging, xml disabled, filtering disabled, size (8192)
*Sep 13 09:19:05.182: %SYS-5-CONFIG_I: Configured from console by console
*Sep 13 09:19:16.708: %SYS-5-CONFIG_I: Configured from console by console
*Sep 13 09:19:27.881: %SYS-5-CONFIG_I: Configured from console by console
*Sep 13 09:19:42.074: %SYS-5-CONFIG_I: Configured from console by console
*Sep 13 09:19:42.477: %AAA-6-USERNAME_CONFIGURATION: user with username: test1 configured
*Sep 13 09:19:42.880: %SYS-5-CONFIG_I: Configured from console by console
*Sep 13 09:19:43.886: %SYS-5-CONFIG_I: Configured from console by console
*Sep 13 09:19:44.206: %AAA-6-USERNAME_CONFIGURATION: user with username: test2 configured
*Sep 13 09:19:44.499: %SYS-5-CONFIG_I: Configured from console by console
*Sep 13 09:19:55.339: %PARSER-5-CFGLOG_LOGGEDCMD: User:console  logged command:notify syslog 
*Sep 13 09:19:55.456: %SYS-5-CONFIG_I: Configured from console by console
```

**S8-4 running-config の archive 節 — RT01# show running-config | section archive**

```

*Sep 13 09:19:56.751: %PARSER-5-CFGLOG_LOGGEDCMD: User:console  logged command:no username test1
*Sep 13 09:19:56.907: %SSH-5-SSH2_USERAUTH: User '' authentication for SSH2 Session from 10.1.10.6 (tty = 3) using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' Failed
*Sep 13 09:19:56.907: %SSH-5-SSH2_CLOSE: SSH2 Session from 10.1.10.6 (tty = 3) for user '' using crypto cipher 'aes128-ctr', hmac 'hmac-sha2-256-etm@openssh.com' closed
*Sep 13 09:19:56.954: %PARSER-5-CFGLOG_LOGGEDCMD: User:console  logged command:no username test2
*Sep 13 09:19:57.055: %PARSER-5-CFGLOG_LOGGEDCMD: User:console  logged command:no snmp-server community *archive
 log config
  logging enable
  notify syslog contenttype plaintext
```

**S8-4 config differences(手動バックアップ vs 現在) — RT01# show archive config differences flash:manual.cfg**

```
                                     ^
% Invalid input detected at '^' marker.
```

## S9 CEF  (2026-09-13 09:20)

**S9-0 show ip cef(全体) — RT01# show ip cef**

```
Prefix               Next Hop             Interface
0.0.0.0/0            no route
0.0.0.0/8            drop
0.0.0.0/32           receive              
1.1.1.1/32           receive              Loopback0
10.1.10.0/26         attached             Ethernet0/3
10.1.10.0/32         receive              Ethernet0/3
10.1.10.6/32         attached             Ethernet0/3
10.1.10.45/32        receive              Ethernet0/3
10.1.10.63/32        receive              Ethernet0/3
10.99.12.0/24        attached             Ethernet0/0
10.99.12.0/32        receive              Ethernet0/0
10.99.12.1/32        receive              Ethernet0/0
10.99.12.2/32        attached             Ethernet0/0
10.99.12.255/32      receive              Ethernet0/0
55.55.55.55/32       receive              Loopback55
127.0.0.0/8          drop
224.0.0.0/4          drop
224.0.0.0/24         receive              
240.0.0.0/4          drop
255.255.255.255/32   receive
```

**S9-0 show ip cef 10.99.12.2/32 detail(隣接解決済) — RT01# show ip cef 10.99.12.2/32 detail**

```
*Sep 13 09:19:58.669: %PARSER-5-CFGLOG_LOGGEDCMD: User:console  logged command:archive 
*Sep 13 09:19:59.172: %SYS-5-CONFIG_I: Configured from console by console
```

**S9-0 show ip cef 10.99.12.0/24 detail(attached) — RT01# show ip cef 10.99.12.0/24 detail**

```
show ip cef 10.99.12.2/32 detail
10.99.12.2/32, epoch 0, flags [attached]
  Adj source: IP adj out of Ethernet0/0, addr 10.99.12.2 7544FBFC4B58
    Dependent covered prefix type adjfib, cover 10.99.12.0/24
  attached to Ethernet0/0
```

**S9-0 receive — RT01# show ip cef 10.99.12.1/32 detail**

```
show ip cef 10.99.12.0/24 detail
10.99.12.0/24, epoch 0, flags [attached, connected, cover dependents, need deagg]
  Covered dependent prefixes: 3
    need deagg: 2
    notify cover updated: 1
  attached to Ethernet0/0
```

**S9-0 adjacency glean — RT01# show ip cef adjacency glean**

```
show ip cef 10.99.12.1/32 detail
10.99.12.1/32, epoch 0, flags [receive, local, source eligible]
  Interface source: Ethernet0/0 flags: local, source eligible flags3: none
  receive for Ethernet0/0
```

**S9-0 adjacency drop — RT01# show ip cef adjacency drop**

```
show ip cef adjacency glean
Prefix               Next Hop             Interface
10.1.10.0/26         attached             Ethernet0/3
10.99.12.0/24        attached             Ethernet0/0
```

**S9-0 show adjacency detail — RT01# show adjacency Ethernet0/0 detail**

```
show ip cef adjacency drop
Prefix               Next Hop             Interface
0.0.0.0/8            drop
127.0.0.0/8          drop
224.0.0.0/4          drop
240.0.0.0/4          drop
RT01#
*Sep 13 09:19:59.558: %LINEPROTO-5-UPDOWN: Line protocol on Interface Loopback56, changed state to down
*Sep 13 09:19:59.558: %LINK-5-CHANGED: Interface Loopback56, changed state to administratively down
```

**S9-0 exact-route — RT01# show ip cef exact-route 10.1.10.6 10.99.12.2**

```
show adjacency Ethernet0/0 detail
Protocol Interface                 Address
IP       Ethernet0/0               10.99.12.2(7)
                                   0 packets, 0 bytes
                                   epoch 0
                                   sourced in sev-epoch 0
                                   Encap length 14
                                   AABBCC010700AABBCC0106000800
                                   L2 destination address byte offset 0
                                   L2 destination address byte length 6
                                   Link-type after encap: ip
                                   ARP
```

**S9-1 静的(未解決 next-hop / Null0 / IF 指定)**

```
ip route 172.16.0.0 255.255.0.0 10.99.12.9
ip route 172.17.0.0 255.255.0.0 Null0
ip route 172.18.0.0 255.255.0.0 Ethernet0/0
---
(応答なし)
```

**S9-1 next-hop 未解決(10.99.12.9) — RT01# show ip cef 172.16.0.0/16 detail**

```
*Sep 13 09:20:11.936: %SYS-5-CONFIG_I: Configured from console by console
```

**S9-1 172.16.5.5 の longest match — RT01# show ip cef 172.16.5.5 detail**

```
show ip cef 172.16.0.0/16 detail
172.16.0.0/16, epoch 0
  recursive via 10.99.12.9
    recursive via 10.99.12.0/24
      attached to Ethernet0/0
```

**S9-1 Null0 — RT01# show ip cef 172.17.0.0/16 detail**

```
show ip cef 172.16.5.5 detail
172.16.0.0/16, epoch 0
  recursive via 10.99.12.9
    recursive via 10.99.12.0/24
      attached to Ethernet0/0
```

**S9-1 IF 指定(glean) — RT01# show ip cef 172.18.0.0/16 detail**

```
show ip cef 172.17.0.0/16 detail
172.17.0.0/16, epoch 0, flags [attached]
  attached to Null0
```

**S9-1 adjacency glean(静的後) — RT01# show ip cef adjacency glean**

```
show ip cef 172.18.0.0/16 detail
172.18.0.0/16, epoch 0, flags [attached]
  attached to Ethernet0/0
```

**S9-1 adjacency drop(静的後) — RT01# show ip cef adjacency drop**

```
show ip cef adjacency glean
Prefix               Next Hop             Interface
10.1.10.0/26         attached             Ethernet0/3
10.99.12.0/24        attached             Ethernet0/0
172.18.0.0/16        attached             Ethernet0/0
```

**S9-1 show ip cef(静的後) — RT01# show ip cef**

```
 adjacency drop
Prefix               Next Hop             Interface
0.0.0.0/8            drop
127.0.0.0/8          drop
224.0.0.0/4          drop
240.0.0.0/4          drop
```

**S9-1 経路なし宛先 — RT01# show ip cef 9.9.9.9**

```
show ip cef
Prefix               Next Hop             Interface
0.0.0.0/0            no route
0.0.0.0/8            drop
0.0.0.0/32           receive              
1.1.1.1/32           receive              Loopback0
10.1.10.0/26         attached             Ethernet0/3
10.1.10.0/32         receive              Ethernet0/3
10.1.10.6/32         attached             Ethernet0/3
10.1.10.45/32        receive              Ethernet0/3
10.1.10.63/32        receive              Ethernet0/3
10.99.12.0/24        attached             Ethernet0/0
10.99.12.0/32        receive              Ethernet0/0
10.99.12.1/32        receive              Ethernet0/0
10.99.12.2/32        attached             Ethernet0/0
10.99.12.9/32        10.99.12.9           Ethernet0/0
10.99.12.255/32      receive              Ethernet0/0
55.55.55.55/32       receive              Loopback55
127.0.0.0/8          drop
172.16.0.0/16        10.99.12.9           Ethernet0/0
172.17.0.0/16        attached             Null0
172.18.0.0/16        attached             Ethernet0/0
224.0.0.0/4          drop
224.0.0.0/24         receive              
240.0.0.0/4          drop
255.255.255.255/32   receive
```

**S9-1 RIB 側 — RT01# show ip route 172.16.0.0**

```
show ip cef 9.9.9.9
0.0.0.0/0
  no route
```

**S9-2 no ip cef**

```
no ip cef
---
(応答なし)
```

**S9-2 show ip cef — RT01# show ip cef**

```
Prefix               Next Hop             Interface
0.0.0.0/0            no route
0.0.0.0/8            drop
0.0.0.0/32           receive              
1.1.1.1/32           receive              Loopback0
10.1.10.0/26         attached             Ethernet0/3
10.1.10.0/32         receive              Ethernet0/3
10.1.10.6/32         attached             Ethernet0/3
10.1.10.45/32        receive              Ethernet0/3
10.1.10.63/32        receive              Ethernet0/3
10.99.12.0/24        attached             Ethernet0/0
10.99.12.0/32        receive              Ethernet0/0
10.99.12.1/32        receive              Ethernet0/0
10.99.12.2/32        attached             Ethernet0/0
10.99.12.9/32        10.99.12.9           Ethernet0/0
10.99.12.255/32      receive              Ethernet0/0
55.55.55.55/32       receive              Loopback55
127.0.0.0/8          drop
172.16.0.0/16        10.99.12.9           Ethernet0/0
172.17.0.0/16        attached             Null0
172.18.0.0/16        attached             Ethernet0/0
224.0.0.0/4          drop
224.0.0.0/24         receive              
240.0.0.0/4          drop
255.255.255.255/32   receive
```

**S9-2 show ip interface の switching 行 — RT01# show ip interface Ethernet0/0 | include switching|CEF**

```
  IP fast switching is enabled
  IP Flow switching is disabled
  IP CEF switching is disabled
  IP multicast fast switching is enabled
  IP multicast distributed fast switching is disabled
```

**S9-2 show cef state — RT01# show cef state | include CEF|enabled|disabled**

```
CEF Status:
 common CEF enabled
Label-FIB CEF Status:
IPv4 CEF Status:
 CEF disabled/running
 dCEF disabled/not running
 CEF switching disabled/not running
IPv6 CEF Status:
 CEF disabled/not running
 dCEF disabled/not running
```

- S9-2 no ip cef でも ping 10.99.12.2 = 100%

**S9-3 interface で no ip route-cache cef**

```
interface Ethernet0/0
no ip route-cache cef
---
(応答なし)
```

**S9-3 show ip interface — RT01# show ip interface Ethernet0/0 | include switching|CEF**

```
  IP fast switching is enabled
  IP Flow switching is disabled
  IP CEF switching is disabled
  IP multicast fast switching is enabled
  IP multicast distributed fast switching is disabled
  IP route-cache flags are Fast, No CEF
```

**S9-3 running-config — RT01# show running-config interface Ethernet0/0**

```
Building configuration...

Current configuration : 118 bytes
!
interface Ethernet0/0
 description === to RT02 ===
 ip address 10.99.12.1 255.255.255.0
 no ip route-cache cef
end
```

**S9-3b no ip route-cache(process switching)**

```
interface Ethernet0/0
no ip route-cache
---
(応答なし)
```

**S9-3b show ip interface — RT01# show ip interface Ethernet0/0 | include switching|CEF**

```
  IP fast switching is disabled
  IP Flow switching is disabled
  IP CEF switching is disabled
  IP multicast fast switching is disabled
  IP multicast distributed fast switching is disabled
  IP route-cache flags are No CEF
```

**S9-3c 復旧後 — RT01# show ip interface Ethernet0/0 | include switching|CEF**

```
  IP fast switching is enabled
  IP Flow switching is disabled
  IP CEF switching is disabled
  IP multicast fast switching is enabled
  IP multicast distributed fast switching is disabled
  IP route-cache flags are Fast, No CEF
```

## S10 copy/tftp/ftp/scp  (2026-09-13 09:25)

**S10-0 copy running-config flash:RT01.cfg — RT01# copy running-config flash:RT01.cfg**

```
                          ^
% Invalid input detected at '^' marker.
```

**S10-1 tftp-server**

```
tftp-server flash:RT01.cfg
tftp-server flash:RT01.cfg alias rt01-alias.cfg
---
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
```

**S10-1 ホストの tftp クライアントで RT01.cfg**

```
TftpTimeout: Timed-out waiting for traffic
```

**S10-1 ホストの tftp クライアントで alias**

```
TftpTimeout: Timed-out waiting for traffic
```

**S10-1 ホストの tftp クライアントで未公開ファイル(manual.cfg)**

```
TftpTimeout: Timed-out waiting for traffic
```

**S10-1 RT02 から copy tftp://10.99.12.1/RT01.cfg null: — RT02# copy tftp://10.99.12.1/RT01.cfg null:**

```
Accessing tftp://10.99.12.1/RT01.cfg...
%Error opening tftp://10.99.12.1/RT01.cfg (Timed out)
```

**S10-1 RT02 から存在しないファイル — RT02# copy tftp://10.99.12.1/nothere.cfg null:**

```
Accessing tftp://10.99.12.1/nothere.cfg...
%Error opening tftp://10.99.12.1/nothere.cfg (Timed out)
```

**S10-2 TFTP サーバが無い宛先へ copy(タイムアウト) — RT01# copy running-config tftp://10.1.10.6/RT01.cfg**

```
*Sep 13 09:20:54.307: %SYS-5-CONFIG_I: Configured from console by console
```

**S10-2 URL 書式誤り(// 無し) — RT01# copy running-config tftp:10.1.10.6/RT01.cfg**

```
copy running-config tftp://10.1.10.6/RT01.cfg
.....
%Error opening tftp://10.1.10.6/RT01.cfg (Timed out)
RT01#
Address or name of remote host []? 
?Host name or address not specified
%Error parsing filename (Bad address)
```

**S10-3 ftp URL にユーザ:パスワードとポート — RT01# copy running-config ftp://ftpu:ftpp@10.1.10.6:2121/RT01-ftp1.cfg**

```
Writing RT01-ftp1.cfg !
2772 bytes copied in 0.069 secs (40174 bytes/sec)
```

**S10-3 ip ftp username/password**

```
ip ftp username ftpu
ip ftp password ftpp
---
(応答なし)
```

**S10-3 ip ftp username/password + URL — RT01# copy running-config ftp://10.1.10.6:2121/RT01-ftp2.cfg**

```
Writing RT01-ftp2.cfg !
2814 bytes copied in 0.131 secs (21481 bytes/sec)
```

**S10-3 パスワード誤り — RT01# copy running-config ftp://10.1.10.6:2121/RT01-ftp3.cfg**

```
*Sep 13 09:24:43.803: %SYS-5-CONFIG_I: Configured from console by console
```

**S10-3 ip ftp passive — RT01# copy running-config ftp://10.1.10.6:2121/RT01-ftp4.cfg**

```
Writing RT01-ftp4.cfg !
2814 bytes copied in 0.131 secs (21481 bytes/sec)
```

**S10-3 FTP サーバ側に届いたファイル**

```
RT01-ftp1.cfg 2772 bytes
RT01-ftp2.cfg 2814 bytes
RT01-ftp4.cfg 2814 bytes
```

**S10-3 FTP から取得 — RT01# copy ftp://10.1.10.6:2121/RT01-ftp2.cfg null:**

```
Accessing ftp://10.1.10.6:2121/RT01-ftp2.cfg...!
[OK - 2814/4096 bytes]

2814 bytes copied in 0.007 secs (402000 bytes/sec)
```

**S10-4 ip scp server enable(AAA なし・login local)**

```
ip scp server enable
---
(応答なし)
```

**S10-4 ホストから scp 取得(AAA なし)**

```
rc=0
Authenticated to 10.1.10.45 ([10.1.10.45]:22) using "keyboard-interactive".
debug1: Sending command: scp -v -f running-config
Sink: C0644 2811 running-config
scp: debug1: fd 4 clearing O_NONBLOCK
---

!
! Last configuration change at 09:25:01 UTC Sun Sep 13 2026
!
version 17.15
service timestamps debug datetime msec
service timestamps log datetime msec
!
hostname RT01
!
boot-start-marker
boot-end-marker
!
!
logging buffered 8192
no aaa new-model
!
!
!
!
!
!
!
!
!
!
!
!
!
no ip domain lookup
ip d
```

**S10-4 aaa new-model + authentication login default local**

```
aaa new-model
aaa authentication login CON none
aaa authentication login default local
line con 0
login authentication CON
---
(応答なし)
```

**S10-4 scp(authentication のみ・authorization exec なし)**

```
rc=1
Authenticated to 10.1.10.45 ([10.1.10.45]:22) using "keyboard-interactive".
debug1: Sending command: scp -v -f running-config
Sink: \001Privilege denied.
---
```

**S10-4 + aaa authorization exec default local**

```
aaa authorization exec default local
---
(応答なし)
```

**S10-4 scp(authorization exec あり)**

```
rc=0
Authenticated to 10.1.10.45 ([10.1.10.45]:22) using "keyboard-interactive".
debug1: Sending command: scp -v -f running-config
Sink: C0644 2964 running-config
scp: debug1: fd 4 clearing O_NONBLOCK
---

!
! Last configuration change at 09:25:27 UTC Sun Sep 13 2026
!
version 17.15
service timestamps debug datetime msec
service timestamps log datetime msec
!
hostname RT01
!
boot-start-marker
boot-end-marker
!
!
logging buffered 8192
aaa new-model
!
!
aaa authentication login default local
aaa authen
```

**S10-4 scp でホスト→flash:pushed.txt**

```
rc=1
debug1: Sending command: scp -v -t flash:pushed.txt
scp: debug1: fd 3 clearing O_NONBLOCK
scp: debug1: fd 4 clearing O_NONBLOCK
```

**S10-4 dir — RT01# dir flash: | include pushed**

```
*Sep 13 09:25:27.501: %AAA-6-METHOD_LIST_STATE: authen mlist  pvt_authen_0 of DOT1X service is marked for notifyingstate and its current state is : DEAD
RT01#
*Sep 13 09:25:27.701: %SYS-5-CONFIG_I: Configured from console by console
*Sep 13 09:25:27.815: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 0) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
RT01#
*Sep 13 09:25:30.040: %SEC_LOGIN-5-LOGIN_SUCCESS: Login Success [user: SUZUKI] [Source: 10.1.10.6] [localport: 22] at 09:25:30 UTC Sun Sep 13 2026
*Sep 13 09:25:30.040: %SSH-5-SSH2_USERAUTH: User 'SUZUKI' authentication for SSH2 Session from 10.1.10.6 (tty = 0) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
*Sep 13 09:25:30.171: %SSH-5-SSH2_CLOSE: SSH2 Session from 10.1.10.6 (tty = 0) for user 'SUZUKI' using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' closed
RT01#
*Sep 13 09:25:30.287: %SSH-5-SSH2_SESSION: SSH2 Session request from 10.1.10.6 (tty = 0) using crypto cipher 'chacha20-poly1305@openssh.com', hmac 'hmac-sha2-256-etm@openssh.com' Succeeded
```

**S10-4 running-config — RT01# show running-config | include scp|aaa**

```
dir flash: | include pushed
         ^
% Invalid input detected at '^' marker.
```

## S11 SNMP  (2026-09-13 09:29)

**S11-1 community 3 種**

```
access-list 10 permit 10.1.10.99
snmp-server community PUBRO RO
snmp-server community PRIVRW RW 10
snmp-server community UNDEF RO 55
snmp-server location POC-SVC
snmp-server contact noc@example.com
---
(応答なし)
```

**S11-1 get sysName / PUBRO(RO・ACL なし)**

```
SNMPv2-SMI::mib-2.1.5.0 = RT01.ccnp.local
```

**S11-1 get / PRIVRW(RW・ACL 10 はホスト不許可)**

```
errorIndication: No SNMP response received before timeout
```

**S11-1 get / UNDEF(RO・ACL 55 未定義)**

```
SNMPv2-SMI::mib-2.1.5.0 = RT01.ccnp.local
```

**S11-1 get / WRONG(未定義 community)**

```
errorIndication: No SNMP response received before timeout
```

**S11-1 set sysContact / PUBRO(RO)**

```
errorStatus: noAccess at 1
```

**S11-1 set sysContact / PRIVRW(RW・ACL 許可後)**

```
SNMPv2-SMI::mib-2.1.4.0 = set-by-rw
```

**S11-1 get sysContact / PUBRO(set の反映確認)**

```
SNMPv2-SMI::mib-2.1.4.0 = set-by-rw
```

**S11-1 show snmp カウンタ — RT01# show snmp | include SNMP packets|Bad|Unknown|Illegal|Encoding|Number of requested|Set-request|Get-request|Get-next|Response**

```
7 SNMP packets input
    0 Bad SNMP version errors
    2 Unknown community name
    1 Illegal operation for community name supplied
    0 Encoding errors
    3 Number of requested variables
    3 Get-request PDUs
    0 Get-next PDUs
    2 Set-request PDUs
5 SNMP packets output
    0 Bad values errors
    5 Response PDUs
```

**S11-1 ログ(SNMP) — RT01# show logging | include SNMP**

```
*Sep 13 09:25:55.752: %SNMP-5-WARMSTART: SNMP agent on host RT01 is undergoing a warm start
```

**S11-1 ACL 10 カウンタ — RT01# show access-lists 10**

```
Standard IP access list 10
    20 permit 10.1.10.6 (2 matches)
    10 permit 10.1.10.99
```

**S11-1 show snmp community — RT01# show snmp community**

```

Community name: PRIVRW
Community Index: PRIVRW
Community SecurityName: PRIVRW
storage-type: nonvolatile	 active	access-list: 10


Community name: PUBRO
Community Index: PUBRO
Community SecurityName: PUBRO
storage-type: nonvolatile	 active


Community name: UNDEF
Community Index: UNDEF
Community SecurityName: UNDEF
storage-type: nonvolatile	 active	access-list: 55
```

**S11-2 view で system を excluded**

```
snmp-server view V-SYS iso included
snmp-server view V-SYS system excluded
snmp-server community VIEWED RO view V-SYS
---
% Invalid input detected at '^' marker.
```

**S11-2 get sysName / VIEWED(system excluded)**

```
errorIndication: No SNMP response received before timeout
```

**S11-2 get ifNumber / VIEWED**

```
errorIndication: No SNMP response received before timeout
```

**S11-3 v3 group/user**

```
snmp-server group G3PRIV v3 priv
snmp-server group G3AUTH v3 auth
snmp-server user u3 G3PRIV v3 auth sha AUTHPASS01 priv aes 128 PRIVPASS01
snmp-server user u3a G3PRIV v3 auth sha AUTHPASS01
snmp-server user u3md5 G3AUTH v3 auth md5 AUTHPASS01
---
(応答なし)
```

**S11-3 show snmp user — RT01# show snmp user**

```

User name: u3
Engine ID: 800000090300AABBCC010600
storage-type: nonvolatile	 active
Authentication Protocol: SHA
Privacy Protocol: AES128
Group-name: G3PRIV

User name: u3a
Engine ID: 800000090300AABBCC010600
storage-type: nonvolatile	 active
Authentication Protocol: SHA
Privacy Protocol: None
Group-name: G3PRIV
```

**S11-3 show snmp group — RT01# show snmp group | begin G3**

```
groupname: G3AUTH                           security model:v3 auth 
contextname: <no context specified>         storage-type: nonvolatile
readview : v1default                        writeview: <no writeview specified>        
notifyview: <no notifyview specified>       
row status: active

groupname: G3PRIV                           security model:v3 priv 
contextname: <no context specified>         storage-type: nonvolatile
readview : v1default                        writeview: <no writeview specified>        
notifyview: <no notifyview specified>       
row status: active

groupname: PRIVRW                           security model:v1 
contextname: <no context specified>         storage-type: permanent
readview : v1default                        writeview: v1default                       
notifyview: <no notifyview specified>       
row status: active	access-list: 10

groupname: PRIVRW                           security model:v2c 
contextname: <no context specified>         storage-type: permanent
readview : v1default                        writeview: v1default                       
notifyview: <no notifyview specified>       
row status: active	access-list: 10
```

**S11-3 running-config の snmp-server 行(user は載らない) — RT01# show running-config | include snmp-server**

```
*Sep 13 09:26:32.279: Configuring snmpv3 USM user, persisting snmpEngineBoots. Please Wait...
```

**S11-3 v3 u3 authPriv 正しい**

```
SNMPv2-SMI::mib-2.1.5.0 = RT01.ccnp.local
```

**S11-3 v3 u3 auth パスワード誤り**

```
errorIndication: Wrong SNMP PDU digest
```

**S11-3 v3 u3 priv パスワード誤り**

```
errorIndication: No SNMP response received before timeout
```

**S11-3 v3 u3 authNoPriv で要求(group は priv)**

```
errorStatus: authorizationError at 0
```

**S11-3 v3 u3a(auth のみのユーザ・group priv) authNoPriv**

```
errorStatus: authorizationError at 0
```

**S11-3 v3 未定義ユーザ**

```
errorIndication: Unknown USM user
```

**S11-3 v3 u3md5 を sha で**

```
errorIndication: Unknown USM user
```

**S11-3 v3 u3md5 を md5 で(group auth)**

```
errorIndication: Unknown USM user
```

**S11-3 show snmp の v3 系カウンタ — RT01# show snmp | include Unknown|Bad|Illegal|Unsupported|digest|time window|engine**

```
show running-config | include snmp-server
snmp-server group G3AUTH v3 auth 
snmp-server group G3PRIV v3 priv 
snmp-server view V-SYS iso included
snmp-server view V-SYS system excluded
snmp-server community PUBRO RO
snmp-server community PRIVRW RW 10
snmp-server community UNDEF RO 55
snmp-server location POC-SVC
snmp-server contact set-by-rw
RT01#
*Sep 13 09:26:32.576: %SYS-5-CONFIG_I: Configured from console by console
```

**S11-3 show snmp engineID — RT01# show snmp engineID**

```
show snmp | include Unknown|Bad|Illegal|Unsupported|digest|time window|engine
    0 Bad SNMP version errors
    4 Unknown community name
    1 Illegal operation for community name supplied
    0 Bad values errors
```

**S11-4 snmp-server host(version 未指定)**

```
snmp-server host 10.1.10.6 PUBRO
---
(応答なし)
```

**S11-4 running-config — RT01# show running-config | include snmp-server host**

```
snmp-server host 10.1.10.6 PUBRO
```

**S11-4 show snmp host — RT01# show snmp host**

```
Notification host: 10.1.10.6	udp-port: 162	type: trap
user: PUBRO	security model: v1
```

**S11-4 informs version 1**

```
snmp-server host 10.1.10.6 informs version 1 PUBRO
---
%Informs not supported in SNMPv1
```

**S11-4 traps(1162) と informs(1163)**

```
no snmp-server host 10.1.10.6 PUBRO
snmp-server host 10.1.10.6 version 2c PUBRO udp-port 1162
snmp-server host 10.1.10.6 informs version 2c PUBRO udp-port 1163
---
(応答なし)
```

**S11-4 show snmp host(2 行) — RT01# show snmp host**

```
Notification host: 10.1.10.6	udp-port: 1163	type: inform
user: PUBRO	security model: v2c

Notification host: 10.1.10.6	udp-port: 1162	type: trap
user: PUBRO	security model: v2c
```

**S11-5 enable traps(未設定) — RT01# show running-config | include snmp-server enable**

```

```

- S11-5 enable traps 無しの linkDown/Up: trap 受信 0 個

**S11-5 snmp-server enable traps(引数なし)**

```
snmp-server enable traps
---
(応答なし)
```

- S11-5 引数なし enable traps → running-config に 91 行

**S11-5 running-config の enable traps 行(先頭 15 行)**

```
snmp-server enable traps snmp authentication linkdown linkup coldstart warmstart
snmp-server enable traps vrrp
snmp-server enable traps pfr
snmp-server enable traps flowmon
snmp-server enable traps tty
snmp-server enable traps eigrp
snmp-server enable traps ospf state-change
snmp-server enable traps ospf errors
snmp-server enable traps ospf retransmit
snmp-server enable traps ospf lsa
snmp-server enable traps ospf cisco-specific state-change nssa-trans-change
snmp-server enable traps ospf cisco-specific state-change shamlink interface
snmp-server enable traps ospf cisco-specific state-change shamlink neighbor
snmp-server enable traps ospf cisco-specific errors
snmp-server enable traps ospf cisco-specific retransmit
```

- S11-5 enable traps 後の linkDown/Up: trap 受信 0 個

**S11-5 show snmp inform(受信側なし・再送中) — RT01# show snmp inform**

```
*Sep 13 09:27:43.249: %SYS-5-CONFIG_I: Configured from console by console
RT01#
*Sep 13 09:27:45.150: %LINK-5-UPDOWN: Interface Ethernet0/1, changed state to up
*Sep 13 09:27:46.150: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet0/1, changed state to up
RT01#
               ^
% Invalid input detected at '^' marker.
```

**S11-5 show snmp の通知カウンタ — RT01# show snmp | include Inform|Trap|SNMP.*sent|Notification**

```
    2 Trap PDUs
    4 Inform-request PDUs
    0 Inform request PDUs
    0 Trap PDUs
    Informs in flight 2/25 (current/max)
```

**S11-5 show snmp inform(100 秒後) — RT01# show snmp inform**

```
               ^
% Invalid input detected at '^' marker.
```

## S2b (例外で中断)  (2026-09-13 09:36)

**S2b-0 再測前の show users — RT01# show users**

```
    Line       User       Host(s)              Idle       Location
*  0 con 0                idle                 00:00:00   

  Interface    User               Mode         Idle     Peer Address
```

**S2b-0 show ssh — RT01# show ssh**

```
%No SSHv2 server connections running.
```

**S2b-0 clear line vty 0-4 後**

```
    Line       User       Host(s)              Idle       Location
*  0 con 0                idle                 00:00:00   

  Interface    User               Mode         Idle     Peer Address
```

**S2b-1 対照: login local + SUZUKI → OK**

```



RT01#terminal length 0
RT01#show users
    Line       User       Host(s)              Idle       Location
   0 con 0                idle                 00:00:03   
*  2 vty 0     SUZUKI     idle                 00:00:00 10.1.10.6

  Interface    User               Mode         Idle     Peer Address

RT01#
```

**S2b-2 login + password vtypass**

```
line vty 0 4
password vtypass
login
---
(応答なし)
```

**S2b-2 running-config — RT01# show running-config | section line vty**

```
line vty 0 4
 exec-timeout 0 0
 password vtypass
 login
 transport input ssh
```

- S2b 例外: TIMEOUT: Timeout exceeded.
<pexpect.pty_spawn.spawn object at 0x7b2741dbbb00>
command: /usr/bin/ssh
args: [b'/usr/bin/ssh', b'-o', b'StrictHostKeyChecking=no', b'-o', b'UserKnownHostsFile=/dev/null', b'-o', b'ConnectTimeout=8', b'-o', b'LogLevel=VERBOSE', b'-o', b'HostKeyAlgorithms=+ssh-rsa', b'-o', b'PubkeyAcceptedAlgorithms=+ssh-rsa', b'-o', b'KexAlgorithms=+diffie-hellman-group14-sha1,diffie-hellman-group-exchange-sha1,diffie-hellman-group1-sha1', b'SUZUKI@10.1.10.45', b'show users']
buffer (last 100 chars): ", please try again.\r\r\n\rSUZUKI@10.1.10.45's password: "
before (last 100 chars): ", please try again.\r\r\n\rSUZUKI@10.1.10.45's password: "
after: <class 'pexpect.exceptions.TIMEOUT'>
match: None
match_index: None
exitstatus: None
flag_eof: False
pid: 1339470
child_fd: 13
closed: False
timeout: 20
delimiter: <class 'pexpect.exceptions.EOF'>
logfile: None
logfile_read: None
logfile_send: None
maxread: 2000
ignorecase: False
searchwindowsize: None
delaybeforesend: 0.05
delayafterclose: 0.1
delayafterterminate: 0.1
searcher: searcher_re:
    0: EOF

## S3b (例外で中断)  (2026-09-13 09:37)

**S3-0 show logging(基線・全文) — RT01# show logging**

```
Syslog logging: enabled (0 messages dropped, 4 messages rate-limited, 0 flushes, 0 overruns, xml disabled, filtering disabled)

No Active Message Discriminator.



No Inactive Message Discriminator.


    Console logging: disabled
    Monitor logging: level debugging, 0 messages logged, xml disabled,
                     filtering disabled
    Buffer logging:  level debugging, 1 messages logged, xml disabled,
                    filtering disabled
    Exception Logging: size (4096 bytes)
    Count and timestamp logging messages: disabled
    Persistent logging: disabled
    Trap logging: level informational, 385 message lines logged
        Logging Source-Interface:       VRF Name:

Log Buffer (4096 bytes):
```

**S3-0 running-config の logging 行 — RT01# show running-config | include logging|service timestamps|service sequence**

```
service timestamps debug datetime msec
service timestamps log datetime msec
no logging console
no logging btrace
 logging synchronous
```

**S3-1 send log 4 SVC-TEST-WARN の応答**

```

```

**S3-1 send log 6 SVC-TEST-INFO の応答**

```

```

**S3-1 buffer に入った send log — RT01# show logging | include SVC-TEST**

```
*Sep 13 09:36:30.658: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TEST-WARN
```

**S3-2 logging host + trap warnings**

```
logging host 10.1.10.6 transport udp port 5514
logging trap warnings
---
(応答なし)
```

**S3-2 ホストが受信した syslog(trap warnings)**

```
<188>390: *Sep 13 09:36:34.414: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-WARN4
```

**S3-2 show logging の宛先行 — RT01# show logging | include Trap|Logging to|Buffer|Console|Monitor**

```
    Console logging: disabled
    Monitor logging: level debugging, 0 messages logged, xml disabled,
    Buffer logging:  level debugging, 16 messages logged, xml disabled,
    Trap logging: level warnings, 390 message lines logged
        Logging to 10.1.10.6  (udp port 5514, audit disabled,
Log Buffer (4096 bytes):
*Sep 13 09:36:29.240: %SYS-5-LOG_CONFIG_CHANGE: Buffer logging: level debugging, xml disabled, filtering disabled, size (4096)
*Sep 13 09:36:31.677: %SYS-6-LOGGINGHOST_STARTSTOP: Logging to host 10.1.10.6 port 0 CLI Request Triggered
*Sep 13 09:36:34.415: %SYS-6-LOGGINGHOST_STARTSTOP: Logging to host 10.1.10.6 port 5514 started - CLI initiated
```

**S3-2 buffer の中身 — RT01# show logging | include SVC-|UPDOWN|CHANGED**

```
*Sep 13 09:36:30.658: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-TEST-WARN
*Sep 13 09:36:30.960: %SYS-6-USERLOG_INFO: Message from tty0(user id: ): SVC-TEST-INFO
*Sep 13 09:36:34.111: %SYS-3-USERLOG_ERR: Message from tty0(user id: ): SVC-ERR3
*Sep 13 09:36:34.414: %SYS-4-USERLOG_WARNING: Message from tty0(user id: ): SVC-WARN4
*Sep 13 09:36:34.716: %SYS-5-USERLOG_NOTICE: Message from tty0(user id: ): SVC-NOTE5
*Sep 13 09:36:35.018: %SYS-6-USERLOG_INFO: Message from tty0(user id: ): SVC-INFO6
*Sep 13 09:36:37.535: %LINK-5-CHANGED: Interface Ethernet0/1, changed state to administratively down
*Sep 13 09:36:40.172: %LINK-5-UPDOWN: Interface Ethernet0/1, changed state to up
```

**S3-2 trap informational(既定)で受信**

```
<189>391: *Sep 13 09:36:45.642: %SYS-5-CONFIG_I: Configured from console by console
<190>392: *Sep 13 09:36:45.948: %SYS-6-USERLOG_INFO: Message from tty0(user id: ): SVC-INFO6b
```

**S3-3 logging buffered warnings**

```
logging buffered warnings
---
(応答なし)
```

**S3-3 buffered warnings のときの show logging(全文) — RT01# show logging**

```
Syslog logging: enabled (0 messages dropped, 4 messages rate-limited, 0 flushes, 0 overruns, xml disabled, filtering disabled)

No Active Message Discriminator.



No Inactive Message Discriminator.


    Console logging: disabled
    Monitor logging: level debugging, 0 messages logged, xml disabled,
                     filtering disabled
    Buffer logging:  level warnings, 1 messages logged, xml disabled,
                    filtering disabled
    Exception Logging: size (4096 bytes)
    Count and timestamp logging messages: disabled
    Persistent logging: disabled
    Trap logging: level informational, 400 message lines logged
        Logging to 10.1.10.6  (udp port 5514, audit disabled,
              link up),
              11 message lines logged, 
              0 message lines rate-limited, 
              0 message lines dropped-by-MD, 
              xml disabled, sequence number disabled
              filtering disabled
        Logging Source-Interface:       VRF Name:

Log Buffer (4096 bytes):

*Sep 13 09:36:50.740: %SYS-3-USERLOG_ERR: Message from tty0(user id: ): SVC-ERR3c
```

- S3b 例外: AuthenticationException: Authentication failed.

## S8b archive 再測  (2026-09-13 09:37)

**S8b-0 show archive(未構成) — RT01# show archive**

```
 Archive feature not enabled
```

**S8b-0 log config(未構成) — RT01# show archive log config all**

```
% Config Logger disabled.
```

**S8b-0 手動バックアップ manual2.cfg — RT01# copy running-config flash:manual2.cfg**

```
                          ^
% Invalid input detected at '^' marker.
```

**S8b-1 Loopback57 追加後 — RT01# show running-config | include Loopback57**

```
interface Loopback57
```

**S8b-1 archive 未構成で configure replace list force — RT01# configure replace flash:manual2.cfg list force**

```
                       ^
% Invalid input detected at '^' marker.
```

**S8b-1 replace 後の Loopback57 — RT01# show running-config | include Loopback57**

```
interface Loopback57
```

**S8b-1b force 無し(確認プロンプトに Y) — RT01# configure replace flash:manual2.cfg**

```
                       ^
% Invalid input detected at '^' marker.
```

**S8b-1b replace 後の Loopback58 — RT01# show running-config | include Loopback58**

```
interface Loopback58
```

**S8b-2 投入: archive**

```
archive
---
(応答なし)
```

**S8b-2 投入: archive / path flash:RT01-bk**

```
archive
path flash:RT01-bk
---
% Invalid input detected at '^' marker.
```

**S8b-2 投入: archive / write-memory**

```
archive
write-memory
---
(応答なし)
```

**S8b-2 投入: archive / time-period 1440**

```
archive
time-period 1440
---
(応答なし)
```

**S8b-2 投入: archive / maximum 5**

```
archive
maximum 5
---
(応答なし)
```

**S8b-2 running-config の archive 節 — RT01# show running-config | section archive**

```

```

**S8b-2 show archive(保存前) — RT01# show archive**

```
 Archive feature not enabled
```

**S8b-2 show archive(write memory 後) — RT01# show archive**

```
 Archive feature not enabled
```

**S8b-2 archive config(手動) — RT01# archive config**

```
 Archive feature not enabled
% Error caught by command handler
```

**S8b-2 show archive(手動後) — RT01# show archive**

```
 Archive feature not enabled
```

**S8b-2 dir flash: — RT01# dir flash: | include RT01-bk**

```
         ^
% Invalid input detected at '^' marker.
```

- S8b-2 最新アーカイブ = None

**S8b-3 show archive config differences(最新 vs 現在) — RT01# show archive config differences**

```
!Contextual Config Diffs:
-interface Loopback59
 -ip address 59.59.59.59 255.255.255.255
```

**S8b-3 rollback timer — RT01# show archive config rollback timer**

```
%No Rollback Confirmed Change pending
```

**S8b-4 log config / logging enable**

```
archive
log config
logging enable
---
(応答なし)
```

**S8b-4 running-config(hidekeys は既定か) — RT01# show running-config | section archive**

```
archive
 log config
  logging enable
```

**S8b-4 既定(hidekeys 行なし)での表示 — RT01# show archive log config all**

```
 idx   sess           user@line      Logged command
    1     1        console@console  |  logging enable 
    2     2        console@console  |username test3 secret *
    3     2        console@console  |!config: USER TABLE MODIFIED
    4     2        console@console  |snmp-server community * ro 
    5     2        console@console  |enable secret *
```

**S8b-4 no hidekeys**

```
archive
log config
no hidekeys
---
(応答なし)
```

**S8b-4 running-config(no hidekeys 後) — RT01# show running-config | section archive**

```
archive
 log config
  logging enable
  no hidekeys
```

**S8b-4 no hidekeys での表示 — RT01# show archive log config all**

```
 idx   sess           user@line      Logged command
    1     1        console@console  |  logging enable 
    2     2        console@console  |username test3 secret *
    3     2        console@console  |!config: USER TABLE MODIFIED
    4     2        console@console  |snmp-server community * ro 
    5     2        console@console  |enable secret *
    6     3        console@console  |archive 
    7     3        console@console  | log config 
    8     3        console@console  |  no hidekeys 
    9     4        console@console  |username test4 secret S3cretPW4
   10     4        console@console  |!config: USER TABLE MODIFIED
   11     4        console@console  |snmp-server community SECRETCOMM4 ro 
   12     4        console@console  |ntp authentication-key 7 md5 NTPKEY7
```

**S8b-5 notify syslog**

```
archive
log config
notify syslog
---
(応答なし)
```

**S8b-5 notify syslog の出方 — RT01# show logging | include PARSER|CONFIG**

```

```

**S8b-5 statistics — RT01# show archive log config statistics**

```
Config Log Session Info:
	Number of sessions being tracked: 1
	Memory being held: 3934 bytes
	Total memory allocated for session tracking: 11796 bytes
	Total memory freed from session tracking: 7862 bytes

Config Log log-queue Info:
	Number of entries in the log-queue: 23
	Memory being held by the log-queue: 9024 bytes
	Total memory allocated for log entries: 19591 bytes
	Total memory freed from log entries: 10567 bytes
```

## S9b CEF 再測  (2026-09-13 09:37)

**S9b-0 detail: 隣接解決済(attached) — RT01# show ip cef 10.99.12.2/32 detail**

```
10.99.12.2/32, epoch 0, flags [attached]
  Adj source: IP adj out of Ethernet0/0, addr 10.99.12.2 7544FBFC4B58
    Dependent covered prefix type adjfib, cover 10.99.12.0/24
  attached to Ethernet0/0
```

**S9b-0 detail: receive(self) — RT01# show ip cef 10.99.12.1/32 detail**

```
10.99.12.1/32, epoch 0, flags [receive, local, source eligible]
  Interface source: Ethernet0/0 flags: local, source eligible flags3: none
  receive for Ethernet0/0
```

**S9b-0 detail: attached/connected — RT01# show ip cef 10.99.12.0/24 detail**

```
10.99.12.0/24, epoch 0, flags [attached, connected, cover dependents, need deagg]
  Covered dependent prefixes: 3
    need deagg: 2
    notify cover updated: 1
  attached to Ethernet0/0
```

**S9b-1 未解決 next-hop(recursive) — RT01# show ip cef 172.16.0.0/16 detail**

```
172.16.0.0/16, epoch 0
  recursive via 10.99.12.9
    recursive via 10.99.12.0/24
      attached to Ethernet0/0
```

**S9b-1 Null0 — RT01# show ip cef 172.17.0.0/16 detail**

```
172.17.0.0/16, epoch 0, flags [attached]
  attached to Null0
```

**S9b-1 IF 指定(glean) — RT01# show ip cef 172.18.0.0/16 detail**

```
172.18.0.0/16, epoch 0, flags [attached]
  attached to Ethernet0/0
```

**S9b-1 adjacency glean — RT01# show ip cef adjacency glean**

```
Prefix               Next Hop             Interface
10.1.10.0/26         attached             Ethernet0/3
10.99.12.0/24        attached             Ethernet0/0
172.18.0.0/16        attached             Ethernet0/0
```

**S9b-1 adjacency drop — RT01# show ip cef adjacency drop**

```
Prefix               Next Hop             Interface
0.0.0.0/8            drop
127.0.0.0/8          drop
224.0.0.0/4          drop
240.0.0.0/4          drop
```

**S9b-2 no ip cef 後の show ip cef — RT01# show ip cef**

```
%IPv4 CEF not running
```

**S9b-2 show ip interface — RT01# show ip interface Ethernet0/0 | include CEF|switching|route-cache**

```
  IP fast switching is disabled
  IP Flow switching is disabled
  IP CEF switching is disabled
  IP multicast fast switching is enabled
  IP multicast distributed fast switching is disabled
  IP route-cache flags are Fast
```

- S9b-2 no ip cef でも ping = 100%

**S9b-2 ip cef 復旧後 — RT01# show ip interface Ethernet0/0 | include CEF|switching|route-cache**

```
  IP fast switching is enabled
  IP Flow switching is disabled
  IP CEF switching is enabled
  IP CEF switching turbo vector
  IP multicast fast switching is enabled
  IP multicast distributed fast switching is disabled
  IP route-cache flags are Fast, CEF
```

**S9b-3 IF で no ip route-cache cef — RT01# show ip interface Ethernet0/0 | include CEF|switching|route-cache**

```
  IP fast switching is enabled
  IP Flow switching is disabled
  IP CEF switching is disabled
  IP multicast fast switching is enabled
  IP multicast distributed fast switching is disabled
  IP route-cache flags are Fast, No CEF
```

## S10b copy/tftp 再測  (2026-09-13 09:40)

**S10b-0 copy running-config flash:RT01.cfg(quiet) — RT01# copy running-config flash:RT01.cfg**

```
                          ^
% Invalid input detected at '^' marker.

RT01#
*Sep 13 09:37:56.223: %SYS-5-CONFIG_I: Configured from console by console
*Sep 13 09:37:56.836: %SYS-5-LOG_CONFIG_CHANGE: Console logging: level debugging, xml disabled, filtering disabled
*Sep 13 09:37:56.928: %SYS-5-CONFIG_I: Configured from console by console
```

**S10b-0 dir flash: — RT01# dir flash: | include RT01.cfg|manual**

```
         ^
% Invalid input detected at '^' marker.
```

**S10b-1 tftp-server flash:RT01.cfg**

```
tftp-server flash:RT01.cfg
---
% Invalid input detected at '^' marker.
```

**S10b-1 running-config — RT01# show running-config | include tftp-server**

```

```

**S10b-1 ホスト tftp で公開ファイル RT01.cfg**

```
TftpTimeout: Timed-out waiting for traffic
```

**S10b-1 ホスト tftp で非公開ファイル nvram:startup-config**

```
TftpTimeout: Timed-out waiting for traffic
```

**S10b-1 RT02 から公開ファイル取得 — RT02# copy tftp://10.99.12.1/RT01.cfg null:**

```
Accessing tftp://10.99.12.1/RT01.cfg...
%Error opening tftp://10.99.12.1/RT01.cfg (Timed out)
```

**S10b-1 RT02 から非公開/存在しないファイル — RT02# copy tftp://10.99.12.1/RT99.cfg null:**

```
Accessing tftp://10.99.12.1/RT99.cfg...
%Error opening tftp://10.99.12.1/RT99.cfg (Timed out)
```

## S6 NTP(認証フラグ指紋・全同期は待たない)  (2026-09-13 09:50)

**S6-1 RT02 ntp master 5**

```
ntp master 5
---
(応答なし)
```

**S6-1 RT02 show ntp status(master 5・stratum) — RT02# show ntp status**

```
Clock is unsynchronized, stratum 5, reference is 127.127.1.1    
nominal freq is 250.0000 Hz, actual freq is 250.0000 Hz, precision is 2**10
ntp uptime is 800 (1/100 of seconds), resolution is 4000
reference time is EE50EE18.F58108C8 (09:40:40.959 UTC Sun Sep 13 2026)
clock offset is 0.0000 msec, root delay is 0.00 msec
root dispersion is 7939.08 msec, peer dispersion is 7937.98 msec
loopfilter state is 'FREQ' (Drift being measured), drift is 0.000000000 s/s
system poll interval is 16, last update was 9 sec ago.
```

**S6-1b RT02 ntp master(引数なし=既定 stratum)**

```
no ntp master
ntp master
---
(応答なし)
```

**S6-1b RT02 既定 stratum — RT02# show ntp status | include stratum|synchronized|reference**

```
Clock is unsynchronized, stratum 8, reference is 127.127.1.1    
reference time is EE50EE21.C5E35618 (09:40:49.773 UTC Sun Sep 13 2026)
```

**S6-1b RT02 running-config(ntp master は stratum を省略表示するか) — RT02# show running-config | include ntp**

```
ntp master
```

**S6-2 RT01 ntp server(認証なし)**

```
ntp server 10.99.12.2
---
(応答なし)
```

**S6-2 associations(認証なし・75秒) — RT01# show ntp associations**

```

  address         ref clock       st   when   poll reach  delay  offset   disp
 ~10.99.12.2      .INIT.          16      4     64     0  0.000   0.000 15937.
 * sys.peer, # selected, + candidate, - outlyer, x falseticker, ~ configured
```

**S6-2 status(認証なし) — RT01# show ntp status | include synchronized|stratum|reference**

```
Clock is unsynchronized, stratum 16, no reference clock
reference time is 00000000.00000000 (00:00:00.000 UTC Mon Jan 1 1900)
```

**S6-3 RT02 認証構成**

```
ntp authentication-key 1 md5 NTPKEY1
ntp trusted-key 1
ntp authenticate
---
(応答なし)
```

**S6-3 RT01 [a: 鍵定義のみ・server key 1・authenticate なし・trusted なし]**

```
no ntp server 10.99.12.2
no ntp authenticate
no ntp trusted-key 1
ntp authentication-key 1 md5 NTPKEY1
ntp server 10.99.12.2 key 1
---
%NTP is not initialized
%NTP is not initialized
```

**S6-3 [a: 鍵定義のみ・server key 1・authenticate なし・trusted なし] running-config — RT01# show running-config | include ntp**

```
ntp authentication-key 1 md5 002A27362F7E3257 7
ntp server 10.99.12.2 key 1
```

**S6-3 [a: 鍵定義のみ・server key 1・authenticate なし・trusted なし] associations — RT01# show ntp associations**

```

  address         ref clock       st   when   poll reach  delay  offset   disp
 ~10.99.12.2      .INIT.          16      -     64     0  0.000   0.000 15937.
 * sys.peer, # selected, + candidate, - outlyer, x falseticker, ~ configured
```

**S6-3 [a: 鍵定義のみ・server key 1・authenticate なし・trusted なし] status — RT01# show ntp status | include synchronized|stratum**

```
Clock is unsynchronized, stratum 16, no reference clock
```

**S6-3 RT01 [b: + ntp authenticate(trusted-key なし)]**

```
ntp authenticate
---
(応答なし)
```

**S6-3 [b: + ntp authenticate(trusted-key なし)] running-config — RT01# show running-config | include ntp**

```
ntp authentication-key 1 md5 002A27362F7E3257 7
ntp authenticate
ntp server 10.99.12.2 key 1
```

**S6-3 [b: + ntp authenticate(trusted-key なし)] associations — RT01# show ntp associations**

```

  address         ref clock       st   when   poll reach  delay  offset   disp
 ~10.99.12.2      .AUTH.          16      -     64     0  0.000   0.000 15937.
 * sys.peer, # selected, + candidate, - outlyer, x falseticker, ~ configured
```

**S6-3 [b: + ntp authenticate(trusted-key なし)] status — RT01# show ntp status | include synchronized|stratum**

```
Clock is unsynchronized, stratum 16, no reference clock
```

**S6-3 RT01 [c: + ntp trusted-key 1(完全)]**

```
ntp trusted-key 1
---
(応答なし)
```

**S6-3 [c: + ntp trusted-key 1(完全)] running-config — RT01# show running-config | include ntp**

```
ntp authentication-key 1 md5 002A27362F7E3257 7
ntp authenticate
ntp trusted-key 1
ntp server 10.99.12.2 key 1
```

**S6-3 [c: + ntp trusted-key 1(完全)] associations — RT01# show ntp associations**

```

  address         ref clock       st   when   poll reach  delay  offset   disp
 ~10.99.12.2      .AUTH.          16     31     64     0  0.000   0.000 15937.
 * sys.peer, # selected, + candidate, - outlyer, x falseticker, ~ configured
```

**S6-3 [c: + ntp trusted-key 1(完全)] status — RT01# show ntp status | include synchronized|stratum**

```
Clock is unsynchronized, stratum 16, no reference clock
```

**S6-3 RT01 [d: 鍵不一致(RT01 の鍵1=WRONGKEY)]**

```
no ntp server 10.99.12.2
no ntp authentication-key 1
ntp authentication-key 1 md5 WRONGKEY
ntp server 10.99.12.2 key 1
---
(応答なし)
```

**S6-3 [d: 鍵不一致(RT01 の鍵1=WRONGKEY)] running-config — RT01# show running-config | include ntp**

```
ntp authentication-key 1 md5 113E2B2A393520293D 7
ntp authenticate
ntp trusted-key 1
ntp server 10.99.12.2 key 1
```

**S6-3 [d: 鍵不一致(RT01 の鍵1=WRONGKEY)] associations — RT01# show ntp associations**

```

  address         ref clock       st   when   poll reach  delay  offset   disp
 ~10.99.12.2      .INIT.          16      -     64     0  0.000   0.000 15937.
 * sys.peer, # selected, + candidate, - outlyer, x falseticker, ~ configured
```

**S6-3 [d: 鍵不一致(RT01 の鍵1=WRONGKEY)] status — RT01# show ntp status | include synchronized|stratum**

```
Clock is unsynchronized, stratum 16, no reference clock
```

**S6-3 RT01 [e: 鍵一致だが server 行に key 指定なし]**

```
no ntp server 10.99.12.2
no ntp authentication-key 1
ntp authentication-key 1 md5 NTPKEY1
ntp server 10.99.12.2
---
(応答なし)
```

**S6-3 [e: 鍵一致だが server 行に key 指定なし] running-config — RT01# show running-config | include ntp**

```
ntp authentication-key 1 md5 080F787E223C3C46 7
ntp authenticate
ntp trusted-key 1
ntp server 10.99.12.2
```

**S6-3 [e: 鍵一致だが server 行に key 指定なし] associations — RT01# show ntp associations**

```

  address         ref clock       st   when   poll reach  delay  offset   disp
 ~10.99.12.2      .INIT.          16      8     64     0  0.000   0.000 15937.
 * sys.peer, # selected, + candidate, - outlyer, x falseticker, ~ configured
```

**S6-3 [e: 鍵一致だが server 行に key 指定なし] status — RT01# show ntp status | include synchronized|stratum**

```
Clock is unsynchronized, stratum 16, no reference clock
```

**S6-4 RT01 完全な認証 + source Loopback0**

```
no ntp server 10.99.12.2
ntp authentication-key 1 md5 NTPKEY1
ntp authenticate
ntp trusted-key 1
ntp server 10.99.12.2 key 1
ntp source Loopback0
---
%NTP trusted-key is invalid : key already configured
```

**S6-4 associations(source Lo0・90秒) — RT01# show ntp associations**

```

  address         ref clock       st   when   poll reach  delay  offset   disp
 ~10.99.12.2      .INIT.          16      -     64     0  0.000   0.000 15937.
 * sys.peer, # selected, + candidate, - outlyer, x falseticker, ~ configured
```

**S6-4 status(stratum を master+1 で継ぐか) — RT01# show ntp status | include synchronized|stratum|reference**

```
Clock is unsynchronized, stratum 16, no reference clock
reference time is 00000000.00000000 (00:00:00.000 UTC Mon Jan 1 1900)
```

**S6-4 RT02 側 associations(RT01 が client として見えるか) — RT02# show ntp associations**

```

  address         ref clock       st   when   poll reach  delay  offset   disp
*~127.127.1.1     .LOCL.           7      7     16   377  0.000   0.000  1.204
 * sys.peer, # selected, + candidate, - outlyer, x falseticker, ~ configured
```

## S12 (例外で中断)  (2026-09-13 10:51)

**S12-0 ソフトウェア版 — RT01# show version | include Software|Version|IOS**

```
Cisco IOS Software [IOSXE], Linux Software (X86_64BI_LINUX-ADVENTERPRISEK9-M), Version 17.15.1, RELEASE SOFTWARE (fc4)
```

**S12-0 running-config all の compliance 行 — RT01# show running-config all | include compliance**

```
no eap key-name compliance
no crypto engine compliance shield disable
```

**S12-0 crypto engine compliance ? (ヘルプ)**

```
(help_of failed: StateMachineError: Expected device to reach 'enable' state, but landed on 'config' state.)
```

**S12-0 show crypto engine compliance shield — RT01# show crypto engine compliance shield**

```
                          ^
% Invalid input detected at '^' marker.
```

**S12-1 crypto key generate rsa modulus ? (ヘルプ)**

```
(help_of failed: StateMachineError: Expected device to reach 'enable' state, but landed on 'config' state.)
```

**S12-1 crypto key generate rsa ? (ヘルプ)**

```
(help_of failed: StateMachineError: Expected device to reach 'enable' state, but landed on 'config' state.)
```

**S12-1 ip ssh version ? (ヘルプ)**

```
(help_of failed: StateMachineError: Expected device to reach 'enable' state, but landed on 'config' state.)
```

**S12-1 crypto key generate ec keysize ? (ヘルプ)**

```
(help_of failed: StateMachineError: Expected device to reach 'enable' state, but landed on 'config' state.)
```

**S12-2 modulus 1536**

```
crypto key generate rsa modulus 1536
---
% Invalid input detected at '^' marker.
```

**S12-2 [1536] mypubkey — RT01# show crypto key mypubkey rsa | include Key name|bits**

```

```

**S12-2 modulus 2048**

```
crypto key generate rsa modulus 2048
---
% The key modulus size is 2048 bits
% Generating 2048 bit RSA keys, keys will be non-exportable...
```

**S12-2 [2048] mypubkey — RT01# show crypto key mypubkey rsa | include Key name|bits**

```
Key name: RT01.ccnp.local
Key type: RSA KEYS      2048 bits
```

**S12-2 modulus 3072**

```
crypto key generate rsa modulus 3072
---
% The key modulus size is 3072 bits
% Generating 3072 bit RSA keys, keys will be non-exportable...
```

**S12-2 [3072] mypubkey — RT01# show crypto key mypubkey rsa | include Key name|bits**

```
Key name: RT01.ccnp.local
Key type: RSA KEYS      3072 bits
```

**S12-2 modulus 4096**

```
crypto key generate rsa modulus 4096
---
% The key modulus size is 4096 bits
% Generating 4096 bit RSA keys, keys will be non-exportable...
```

**S12-2 [4096] mypubkey — RT01# show crypto key mypubkey rsa | include Key name|bits**

```
Key name: RT01.ccnp.local
Key type: RSA KEYS      4096 bits
Key name: RT01.ccnp.local.server
Key type: RSA KEYS      2176 bits
```

**S12-2 general-keys modulus 1024 (別構文)**

```
crypto key generate rsa general-keys modulus 1024
---
% Invalid input detected at '^' marker.
```

**S12-2 general-keys modulus 2048 label SSHKEY**

```
crypto key generate rsa general-keys modulus 2048 label SSHKEY
---
% The key modulus size is 2048 bits
% Generating 2048 bit RSA keys, keys will be non-exportable...
```

**S12-2 mypubkey(label 付き) — RT01# show crypto key mypubkey rsa | include Key name|bits**

```
Key name: SSHKEY
Key type: RSA KEYS      2048 bits
Key name: SSHKEY.server
Key type: RSA KEYS      2176 bits
```

**S12-2 show ip ssh 抜粋 — RT01# show ip ssh | include SSH|Minimum|Modulus|SECSH**

```
SSH Enabled - version 2.0
Minimum expected Diffie Hellman key size : 2048 bits
IOS Keys in SECSH format(ssh-rsa, base64 encoded): SSHKEY
Modulus Size : 2048 bits
IOS Keys in SECSH format(ssh-ec, base64 encoded): NONE
```

**S12-3 RSA 消去後 — RT01# show ip ssh | include SSH|Please**

```
SSH Disabled - version 2.0
%Please create EC or RSA keys to enable SSH (and of atleast 2048 bits for SSH v2 in case of RSA).
```

**S12-3 EC 鍵(256)生成**

```
crypto key generate ec keysize 256 label ECKEY
---
(応答なし)
```

**S12-3 EC 鍵だけの show ip ssh — RT01# show ip ssh | include SSH|Please|SECSH**

```
SSH Enabled - version 2.0
IOS Keys in SECSH format(ssh-rsa, base64 encoded): NONE
IOS Keys in SECSH format(ecdsa-sha2-nistp256, base64 encoded): ECKEY
```

**S12-3 EC 鍵だけで paramiko ログイン → OK**

```



RT01#terminal length 0
RT01#show ip ssh | include SSH
SSH Enabled - version 2.0
RT01#
```

**S12-4 running-config all の ip ssh 行(既定値込み) — RT01# show running-config all | include ip ssh**

```
ip ssh bulk-mode 131072
ip ssh time-out 120
ip ssh authentication-retries 3
ip ssh window-size 8192
ip ssh break-string ~break
ip ssh logging events
ip ssh version 2
ip ssh dh min size 2048
no ip ssh rekey time
no ip ssh rekey volume
ip ssh server authenticate user publickey
ip ssh server authenticate user keyboard
ip ssh server authenticate user password
no ip ssh server peruser session limit
ip ssh server certificate profile
ip ssh server algorithm mac hmac-sha2-256-etm@openssh.com hmac-sha2-512-etm@openssh.com
ip ssh server algorithm encryption chacha20-poly1305@openssh.com aes128-gcm@openssh.com aes256-gcm@openssh.com aes128-gcm aes256-gcm aes128-ctr aes192-ctr aes256-ctr
ip ssh server algorithm kex curve25519-sha256 curve25519-sha256@libssh.org ecdh-sha2-nistp256 ecdh-sha2-nistp384 ecdh-sha2-nistp521 diffie-hellman-group14-sha256 diffie-hellman-group16-sha512
ip ssh server algorithm hostkey ecdsa-sha2-nistp256 ecdsa-sha2-nistp384 ecdsa-sha2-nistp521 rsa-sha2-512 rsa-sha2-256 ssh-rsa
ip ssh server algorithm authentication publickey keyboard password
ip ssh server algorithm publickey ssh-rsa ecdsa-sha2-nistp256 ecdsa-sha2-nistp384 ecdsa-sha2-nistp521 ssh-ed25519 x509v3-ecdsa-sha2-nistp256 x509v3-ecdsa-sha2-nistp384 x509v3-ecdsa-sha2-nistp521 rsa-sha2-256 rsa-sha2-512 x509v3-rsa2048-sha256
ip ssh client algorithm mac hmac-sha2-256-etm@openssh.com hmac-sha2-512-etm@openssh.com
ip ssh client algorithm encryption chacha20-poly1305@openssh.com aes128-gcm@openssh.com aes256-gcm@openssh.com aes128-gcm aes256-gcm aes128-ctr aes192-ctr aes256-ctr
ip ssh client algorithm kex curve25519-sha256 curve25519-sha256@libssh.org ecdh-sha2-nistp256 ecdh-sha2-nistp384 ecdh-sha2-nistp521 diffie-hellman-group14-sha256 diffie-hellman-group16-sha512
```

**S12-4 running-config all の archive 節(既定値込み・archive 未構成) — RT01# show running-config all | section archive**

```

```

**S12-4 running-config all の archive 節(log config 構成後) — RT01# show running-config all | section archive**

```
archive
 log config
  no record rc
  logging enable
  no logging persistent reload
  no logging persistent 
  logging size 100
  no notify syslog contenttype plaintext
  no notify syslog contenttype xml
  hidekeys
 no path 
 no rollback filter adaptive
 rollback retry timeout 0
```

**S12-4 running-config(既定は省略) — RT01# show running-config | section archive**

```
archive
 log config
  logging enable
```

**S12-4 archive log config ? (ヘルプ)**

```
(help_of failed: StateMachineError: Expected device to reach 'enable' state, but landed on 'config' state.)
```

- S12 例外: StateMachineError: Expected device to reach 'enable' state, but landed on 'enable' state.

## S12b (例外で中断)  (2026-09-13 10:53)

**S12b-3 RSA 消去後 — RT01# show ip ssh | include SSH|Please**

```
SSH Enabled - version 2.0
```

**S12b-3 EC 鍵(256)生成**

```
crypto key generate ec keysize 256 label ECKEY
---
% You already have EC keys defined named ECKEY.
% Do you really want to replace them? [yes/no]: yes
```

**S12b-3 EC 鍵だけの show ip ssh — RT01# show ip ssh | include SSH|Please|SECSH**

```
SSH Enabled - version 2.0
IOS Keys in SECSH format(ssh-rsa, base64 encoded): NONE
IOS Keys in SECSH format(ecdsa-sha2-nistp256, base64 encoded): ECKEY
```

**S12b-3 EC 鍵だけで paramiko ログイン → OK**

```



RT01#terminal length 0
RT01#show ip ssh | include SSH
SSH Enabled - version 2.0
RT01#
```

**S12b-4 running-config all の ip ssh 行(既定値込み) — RT01# show running-config all | include ip ssh**

```
ip ssh bulk-mode 131072
ip ssh time-out 120
ip ssh authentication-retries 3
ip ssh window-size 8192
ip ssh break-string ~break
ip ssh logging events
ip ssh version 2
ip ssh dh min size 2048
no ip ssh rekey time
no ip ssh rekey volume
ip ssh server authenticate user publickey
ip ssh server authenticate user keyboard
ip ssh server authenticate user password
no ip ssh server peruser session limit
ip ssh server certificate profile
ip ssh server algorithm mac hmac-sha2-256-etm@openssh.com hmac-sha2-512-etm@openssh.com
ip ssh server algorithm encryption chacha20-poly1305@openssh.com aes128-gcm@openssh.com aes256-gcm@openssh.com aes128-gcm aes256-gcm aes128-ctr aes192-ctr aes256-ctr
ip ssh server algorithm kex curve25519-sha256 curve25519-sha256@libssh.org ecdh-sha2-nistp256 ecdh-sha2-nistp384 ecdh-sha2-nistp521 diffie-hellman-group14-sha256 diffie-hellman-group16-sha512
ip ssh server algorithm hostkey ecdsa-sha2-nistp256 ecdsa-sha2-nistp384 ecdsa-sha2-nistp521 rsa-sha2-512 rsa-sha2-256 ssh-rsa
ip ssh server algorithm authentication publickey keyboard password
ip ssh server algorithm publickey ssh-rsa ecdsa-sha2-nistp256 ecdsa-sha2-nistp384 ecdsa-sha2-nistp521 ssh-ed25519 x509v3-ecdsa-sha2-nistp256 x509v3-ecdsa-sha2-nistp384 x509v3-ecdsa-sha2-nistp521 rsa-sha2-256 rsa-sha2-512 x509v3-rsa2048-sha256
ip ssh client algorithm mac hmac-sha2-256-etm@openssh.com hmac-sha2-512-etm@openssh.com
ip ssh client algorithm encryption chacha20-poly1305@openssh.com aes128-gcm@openssh.com aes256-gcm@openssh.com aes128-gcm aes256-gcm aes128-ctr aes192-ctr aes256-ctr
ip ssh client algorithm kex curve25519-sha256 curve25519-sha256@libssh.org ecdh-sha2-nistp256 ecdh-sha2-nistp384 ecdh-sha2-nistp521 diffie-hellman-group14-sha256 diffie-hellman-group16-sha512
```

**S12b-4 running-config all の archive 節(archive 未構成) — RT01# show running-config all | section archive**

```
archive
 log config
  no record rc
  logging enable
  no logging persistent reload
  no logging persistent 
  logging size 100
  no notify syslog contenttype plaintext
  no notify syslog contenttype xml
  hidekeys
 no path 
 no rollback filter adaptive
 rollback retry timeout 0
```

**S12b-4 running-config all の archive 節(log config 構成後) — RT01# show running-config all | section archive**

```
archive
 log config
  no record rc
  logging enable
  no logging persistent reload
  no logging persistent 
  logging size 100
  no notify syslog contenttype plaintext
  no notify syslog contenttype xml
  hidekeys
 no path 
 no rollback filter adaptive
 rollback retry timeout 0
```

**S12b-4 running-config(既定は省略される) — RT01# show running-config | section archive**

```
archive
 log config
  logging enable
```

- S12b 例外: StateMachineError: Expected device to reach 'enable' state, but landed on 'enable' state.

## S12c (例外で中断)  (2026-09-13 10:59)

**S12c-1 crypto engine compliance shield disable**

```
crypto engine compliance shield disable
---
(応答なし)
```

**S12c-1 running-config — RT01# show running-config | include compliance**

```
crypto engine compliance shield disable
```

**S12c-1 write memory — RT01# write memory**

```
Building configuration...
[OK]
```

- S12c 例外: RuntimeError: RT01: console 接続不能(必須)

## S12e 対照: compliance shield 無効(再起動後)で弱い RSA 鍵/SSHv1 が通るか  (2026-09-13 11:11)

**S12e-2 再起動後の uptime — RT01# show version | include uptime**

```
RT01 uptime is 16 minutes
```

**S12e-2 running-config all の compliance 行(再起動後) — RT01# show running-config all | include compliance**

```
no eap key-name compliance
no crypto engine compliance shield disable
```

**S12e-3 shield 無効で modulus 512**

```
crypto key generate rsa modulus 512
---
% Invalid input detected at '^' marker.
```

**S12e-3 [512] mypubkey — RT01# show crypto key mypubkey rsa | include Key name|bits**

```

```

**S12e-3 [512] show ip ssh — RT01# show ip ssh | include SSH|Please|Minimum|Modulus**

```
SSH Enabled - version 2.0
Minimum expected Diffie Hellman key size : 2048 bits
```

**S12e-3 [512] paramiko ログイン → OK**

```



RT01#terminal length 0
RT01#show ip ssh | include SSH
SSH Enabled - version 2.0
RT01#
```

**S12e-3 [512] OpenSSH 接続段階**

```
debug1: Remote protocol version 2.0, remote software version Cisco-1.25
debug1: compat_banner: match: Cisco-1.25 pat Cisco-1.* compat 0x60000000
debug1: kex: algorithm: curve25519-sha256
debug1: kex: host key algorithm: ecdsa-sha2-nistp256
debug1: Server host key: ecdsa-sha2-nistp256 SHA256:rFxOU9gTUfpp7MgnAQIB0tUAUeejI3ofGCQW7r3jylc
debug1: Authentications that can continue: publickey,keyboard-interactive,password
debug1: Authentications that can continue: publickey,keyboard-interactive,password
SUZUKI@10.1.10.45: Permission denied (publickey,keyboard-interactive,password).
```

**S12e-3 shield 無効で modulus 768**

```
crypto key generate rsa modulus 768
---
% Invalid input detected at '^' marker.
```

**S12e-3 [768] mypubkey — RT01# show crypto key mypubkey rsa | include Key name|bits**

```

```

**S12e-3 [768] show ip ssh — RT01# show ip ssh | include SSH|Please|Minimum|Modulus**

```
SSH Enabled - version 2.0
Minimum expected Diffie Hellman key size : 2048 bits
```

**S12e-3 [768] paramiko ログイン → OK**

```



RT01#terminal length 0
RT01#show ip ssh | include SSH
SSH Enabled - version 2.0
RT01#
```

**S12e-3 [768] OpenSSH 接続段階**

```
debug1: Remote protocol version 2.0, remote software version Cisco-1.25
debug1: compat_banner: match: Cisco-1.25 pat Cisco-1.* compat 0x60000000
debug1: kex: algorithm: curve25519-sha256
debug1: kex: host key algorithm: ecdsa-sha2-nistp256
debug1: Server host key: ecdsa-sha2-nistp256 SHA256:rFxOU9gTUfpp7MgnAQIB0tUAUeejI3ofGCQW7r3jylc
debug1: Authentications that can continue: publickey,keyboard-interactive,password
debug1: Authentications that can continue: publickey,keyboard-interactive,password
SUZUKI@10.1.10.45: Permission denied (publickey,keyboard-interactive,password).
```

**S12e-3 shield 無効で modulus 1024**

```
crypto key generate rsa modulus 1024
---
% Invalid input detected at '^' marker.
```

**S12e-3 [1024] mypubkey — RT01# show crypto key mypubkey rsa | include Key name|bits**

```

```

**S12e-3 [1024] show ip ssh — RT01# show ip ssh | include SSH|Please|Minimum|Modulus**

```
SSH Enabled - version 2.0
Minimum expected Diffie Hellman key size : 2048 bits
```

**S12e-3 [1024] paramiko ログイン → OK**

```



RT01#terminal length 0
RT01#show ip ssh | include SSH
SSH Enabled - version 2.0
RT01#
```

**S12e-3 [1024] OpenSSH 接続段階**

```
debug1: Remote protocol version 2.0, remote software version Cisco-1.25
debug1: compat_banner: match: Cisco-1.25 pat Cisco-1.* compat 0x60000000
debug1: kex: algorithm: curve25519-sha256
debug1: kex: host key algorithm: ecdsa-sha2-nistp256
debug1: Server host key: ecdsa-sha2-nistp256 SHA256:rFxOU9gTUfpp7MgnAQIB0tUAUeejI3ofGCQW7r3jylc
debug1: Authentications that can continue: publickey,keyboard-interactive,password
debug1: Authentications that can continue: publickey,keyboard-interactive,password
SUZUKI@10.1.10.45: Permission denied (publickey,keyboard-interactive,password).
```

**S12e-4 shield 無効で ip ssh version 1**

```
ip ssh version 1
---
% Invalid input detected at '^' marker.
```

**S12e-4 running-config all の version/dh 行(shield 無効) — RT01# show running-config all | include ip ssh version|ip ssh dh**

```
ip ssh version 2
ip ssh dh min size 2048
```

**S12e-4 ip ssh dh min size 1024 (shield 無効)**

```
ip ssh dh min size 1024
---
% Invalid input detected at '^' marker.
```

**S12e-4 show ip ssh の Minimum 行 — RT01# show ip ssh | include Minimum**

```
Minimum expected Diffie Hellman key size : 2048 bits
```

**S12e-5 復旧**

```
no ip ssh dh min size
no crypto engine compliance shield disable
crypto key generate rsa modulus 2048
---
% The key modulus size is 2048 bits
% Generating 2048 bit RSA keys, keys will be non-exportable...
```

## S12d 無垢の対照(RT02)と hidekeys の伏字範囲(RT01)  (2026-09-13 11:11)

**S12d-a RT02 show archive(無垢) — RT02# show archive**

```
 Archive feature not enabled
```

**S12d-a RT02 show archive log config all(無垢) — RT02# show archive log config all**

```
% Config Logger disabled.
```

**S12d-a RT02 running-config の archive 節(無垢) — RT02# show running-config | section archive**

```

```

**S12d-a RT02 running-config all の archive 節(無垢) — RT02# show running-config all | section archive**

```

```

**S12d-a RT02 何も構成せずに変更後の show archive log config all — RT02# show archive log config all**

```
% Config Logger disabled.
```

**S12d-a RT02 logging enable を明示**

```
archive
log config
logging enable
---
(応答なし)
```

**S12d-a RT02 logging enable 明示後 — RT02# show archive log config all**

```
 idx   sess           user@line      Logged command
    3     1        console@console  |  logging enable 
    4     2        console@console  |username probe3 secret *
    5     2        console@console  |!config: USER TABLE MODIFIED
```

**S12d-a RT02 running-config(明示後) — RT02# show running-config | section archive**

```
archive
 log config
  logging enable
```

**S12d-b [username password/secret] hidekeys**

```
username hk1 password 0 PlainPW1
username hk2 secret Secret2
---
(応答なし)
```

**S12d-b [enable password] hidekeys**

```
enable password PlainEn3
---
(応答なし)
```

**S12d-b [enable secret] hidekeys**

```
enable secret SecretEn4
---
(応答なし)
```

**S12d-b [snmp community] hidekeys**

```
snmp-server community COMM5 RO
---
(応答なし)
```

**S12d-b [ntp key] hidekeys**

```
ntp authentication-key 6 md5 NTPKEY6
---
(応答なし)
```

**S12d-b [key chain key-string] hidekeys**

```
key chain KC7
key 1
key-string KS7
---
(応答なし)
```

**S12d-b [tacacs key] hidekeys**

```
tacacs server T8
address ipv4 192.0.2.8
key TKEY8
---
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
```

**S12d-b [radius key] hidekeys**

```
radius server R9
address ipv4 192.0.2.9 auth-port 1812 acct-port 1813
key RKEY9
---
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
```

**S12d-b [isakmp key] hidekeys**

```
crypto isakmp key IKEKEY10 address 192.0.2.10
---
(応答なし)
```

**S12d-b [ip ftp password] hidekeys**

```
ip ftp password FTPPW11
---
(応答なし)
```

**S12d-b [line password] hidekeys**

```
line vty 0 4
password VTYPW12
---
(応答なし)
```

**S12d-b [ospf md5] hidekeys**

```
interface Loopback61
ip address 61.61.61.61 255.255.255.255
ip ospf message-digest-key 1 md5 OSPFKEY13
---
(応答なし)
```

**S12d-b [bgp password] hidekeys**

```
router bgp 65000
neighbor 192.0.2.14 remote-as 65001
neighbor 192.0.2.14 password BGPPW14
---
(応答なし)
```

**S12d-b [(対照・秘密なし)] hidekeys**

```
ip ssh authentication-retries 2
---
(応答なし)
```

**S12d-b hidekeys(既定)での記録 — RT01# show archive log config all**

```
 idx   sess           user@line      Logged command
    1    15        console@console  |username hk1 password 0 *
    2    15        console@console  |!config: USER TABLE MODIFIED
    3    15        console@console  |username hk2 secret *
    4    15        console@console  |!config: USER TABLE MODIFIED
    5    16        console@console  |enable password *
    6    17        console@console  |enable secret *
    7    18        console@console  |snmp-server community * ro 
    8    19        console@console  |ntp authentication-key 6 md5 *
    9    20        console@console  |key chain *
   10    20        console@console  | key 1
   11    20        console@console  |  key-string *
   12    23        console@console  |crypto isakmp key * address 192.0.2.10
   13    24        console@console  |ip ftp password *
   14    25        console@console  |line vty 0 4
   15    25        console@console  | password *
   16    26        console@console  |interface Loopback61 
   17    26        console@console  | ip address 61.61.61.61 255.255.255.255
   18    26        console@console  | ip ospf message-digest-key 1 md5 *
   19    27        console@console  |router bgp 65000
   20    27        console@console  | neighbor 192.0.2.14 remote-as 65001
   21    27        console@console  | neighbor 192.0.2.14 password *
   22    28        console@console  |ip ssh authentication-retries 2
```

**S12d-b [username password/secret] no hidekeys**

```
username hk1 password 0 PlainPWb1
username hk2 secret SecretB2
---
(応答なし)
```

**S12d-b [enable password] no hidekeys**

```
enable password PlainEnB3
---
(応答なし)
```

**S12d-b [enable secret] no hidekeys**

```
enable secret SecretEnB4
---
(応答なし)
```

**S12d-b [snmp community] no hidekeys**

```
snmp-server community COMMB5 RO
---
(応答なし)
```

**S12d-b [ntp key] no hidekeys**

```
ntp authentication-key 6 md5 NTPKEYB6
---
(応答なし)
```

**S12d-b [key chain key-string] no hidekeys**

```
key chain KC7
key 1
key-string KSB7
---
(応答なし)
```

**S12d-b [tacacs key] no hidekeys**

```
tacacs server T8
address ipv4 192.0.2.8
key TKEYB8
---
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
```

**S12d-b [radius key] no hidekeys**

```
radius server R9
address ipv4 192.0.2.9 auth-port 1812 acct-port 1813
key RKEYB9
---
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
```

**S12d-b [isakmp key] no hidekeys**

```
crypto isakmp key IKEKEYB10 address 192.0.2.10
---
(応答なし)
```

**S12d-b [ip ftp password] no hidekeys**

```
ip ftp password FTPPWb11
---
(応答なし)
```

**S12d-b [line password] no hidekeys**

```
line vty 0 4
password VTYPWb12
---
(応答なし)
```

**S12d-b [ospf md5] no hidekeys**

```
interface Loopback61
ip address 61.61.61.61 255.255.255.255
ip ospf message-digest-key 1 md5 OSPFKEYB13
---
(応答なし)
```

**S12d-b [bgp password] no hidekeys**

```
router bgp 65000
neighbor 192.0.2.14 remote-as 65001
neighbor 192.0.2.14 password BGPPWb14
---
(応答なし)
```

**S12d-b [(対照・秘密なし)] no hidekeys**

```
ip ssh authentication-retries 3
---
(応答なし)
```

**S12d-b no hidekeys での記録 — RT01# show archive log config all**

```
 idx   sess           user@line      Logged command
    1    30        console@console  |username hk1 password 0 PlainPWb1
    2    30        console@console  |!config: USER TABLE MODIFIED
    3    30        console@console  |username hk2 secret SecretB2
    4    30        console@console  |!config: USER TABLE MODIFIED
    5    31        console@console  |enable password PlainEnB3
    6    32        console@console  |enable secret SecretEnB4
    7    33        console@console  |snmp-server community COMMB5 ro 
    8    34        console@console  |ntp authentication-key 6 md5 NTPKEYB6
    9    35        console@console  |key chain KC7
   10    35        console@console  | key 1
   11    35        console@console  |  key-string KSB7
   12    38        console@console  |crypto isakmp key IKEKEYB10 address 192.0.2.10
   13    39        console@console  |ip ftp password FTPPWb11
   14    40        console@console  |line vty 0 4
   15    40        console@console  | password VTYPWb12
   16    41        console@console  |interface Loopback61 
   17    41        console@console  | ip address 61.61.61.61 255.255.255.255
   18    41        console@console  | ip ospf message-digest-key 1 md5 OSPFKEYB13
   19    42        console@console  |router bgp 65000
   20    42        console@console  | neighbor 192.0.2.14 remote-as 65001
   21    42        console@console  | neighbor 192.0.2.14 password BGPPWb14
   22    43        console@console  |ip ssh authentication-retries 3
```

**S12d-b hidekeys 明示後の running-config — RT01# show running-config | section archive**

```
archive
 log config
  logging enable
```

**S12d 後始末**

```
no username hk1
no username hk2
no enable password
no enable secret
no snmp-server community COMM5
no snmp-server community COMMB5
no ntp authentication-key 6
no key chain KC7
no tacacs server T8
no radius server R9
no crypto isakmp key IKEKEY10 address 192.0.2.10
no crypto isakmp key IKEKEYB10 address 192.0.2.10
no ip ftp password
line vty 0 4
no password
exit
no interface Loopback61
no router bgp 65000
no ip ssh authentication-retries
no archive
---
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
```

## S12f 小確認  (2026-09-13 11:13)

**S12f RT02 show archive log config all(no archive 後) — RT02# show archive log config all**

```
% Config Logger disabled.
```

**S12f RT02 running-config all の archive 節(no archive 後) — RT02# show running-config all | section archive**

```

```

**S12f RT02 running-config all(archive あり・logging enable 明示 off) — RT02# show running-config all | section archive**

```

```

**S12f RT01 startup-config の compliance 行 — RT01# show startup-config | include compliance**

```

```

**S12f RT01 running-config の compliance 行 — RT01# show running-config | include compliance**

```

```

**S12f RT01 再投入**

```
crypto engine compliance shield disable
---
(応答なし)
```

**S12f RT01 再投入後 — RT01# show running-config | include compliance**

```
crypto engine compliance shield disable
```

**S12f RT01 ログ(compliance) — RT01# show logging | include ompliance|shield|CSDL**

```

```
