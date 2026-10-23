#!/bin/bash
# BL-246 M4 追補(IS-IS の 2 周目)の PoC。盤面= problems/XRT-05(XR01= XRd 26.1.1・IOL 17.15)。記録= design §18。
# usage: source poc/xr/env.sh; poc/xr/isis2_poc.sh <XR01> <RT01> <RT02> <RT03> <phase…>(管理 IP)
#   phase は a〜f を順に流す前提(各 phase は前の状態の上に積む)。出力は標準出力(呼び出し側で poc/xr/isis2-<phase>.log へ)
cd "$(dirname "$0")/../.."
XR=$1 R1=$2 R2=$3 R3=$4; shift 4
X() { .venv/bin/python poc/xr/xrsh.py "$XR" "$@" 2>&1; }
R() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
XS() { X 'show isis adjacency' 'show route ipv4 isis' 'show route ipv6 isis' "$@"; }
G1=GigabitEthernet0/0/0/0 G2=GigabitEthernet0/0/0/1 G3=GigabitEthernet0/0/0/2 G4=GigabitEthernet0/0/0/3

a() {
  H "a-1: 初期状態(M4 解答済み+バックボーンが L2 認証済み・XR01 は未対応)"
  XS 'show isis interface brief' "show isis interface $G2" 'show isis adjacency-log' 'show isis statistics' \
     'show isis database' 'show logging last 40'
  H "a-2: IOS 側"
  R "$R2" 'show clns neighbors' 'show clns traffic' 'show isis database' 'show ip route isis'
  R "$R1" 'show clns neighbors' 'show ip route isis' 'show ipv6 route isis' 'show isis database detail'
  R "$R3" 'show clns neighbors' 'show clns interface Ethernet0/2' 'show isis database'
}

b() {
  # 実行記録= isis2-b.log(b-1/b-2)・isis2-b2.log(b-1b/b-1c/b-2b)・isis2-b3.log(b-3)
  H "b-1: 鍵を key-string password <平文> で作る → コミット失敗(password は暗号化済みの形を渡す指定)"
  X configure 'key chain ISIS-L2' 'key 1' 'key-string password Bb0ne-2026' 'cryptographic-algorithm HMAC-MD5' commit \
    'show configuration failed' abort
  H "b-2: 鍵チェーンが無いまま hello-password keychain を付ける → コミットは通り、受けたハローを全部 Authentication Failed で捨てる"
  X configure 'router isis CORE' "interface $G2" 'hello-password keychain ISIS-L2' root \
    'router isis CORE' "interface $G3" 'hello-password keychain ISIS-L2' commit 'show configuration failed' end
  sleep 45
  XS "show isis interface $G2 | include \"Rejected|Received|Sent\""
  H "b-1b: key-string clear(アルゴリズム・有効期間なし)→ b-1c: アルゴリズムを足す(有効期間なし)= まだ失敗"
  X configure 'key chain ISIS-L2' 'key 1' 'key-string clear Bb0ne-2026' commit end 'show key chain ISIS-L2'
  X configure 'key chain ISIS-L2' 'key 1' 'cryptographic-algorithm HMAC-MD5' commit end 'show key chain ISIS-L2' 'show running-config key chain'
  sleep 45
  XS "show isis interface $G2 | include \"Rejected|Received|Sent\""
  H "b-3: 有効期間を足す → [Valid now] になり隣接が上がる。ハローだけ合った状態= XR はバックボーンの LSP を受けるが、RT02 は XR の LSP を捨てる"
  X configure 'key chain ISIS-L2' 'key 1' 'accept-lifetime 00:00:00 january 01 2026 infinite' 'send-lifetime 00:00:00 january 01 2026 infinite' \
    commit end 'show key chain ISIS-L2'
  sleep 40
  XS 'show isis database'
  R "$R2" 'show clns neighbors' 'show isis database' 'show ip route isis | begin Gateway'
  R "$R1" 'show ip route isis | begin Gateway'
}

c() {
  H "c-1: LSP/SNP の認証をレベル 2 だけに足す"
  X configure 'router isis CORE' 'lsp-password keychain ISIS-L2 level 2' commit 'show configuration failed' end
  sleep 45
  XS 'show isis database' 'show running-config router isis CORE'
  R "$R2" 'show clns traffic' 'show isis database' 'show ip route isis' 'show ipv6 route isis'
  R "$R1" 'show ip route isis' 'show ipv6 route isis' 'ping 10.20.0.1 source 10.255.0.11'
  H "c-2: レベルを付けずに入れ替える(L1 にも効くか・RT01 の経路は)"
  X configure 'router isis CORE' 'no lsp-password keychain ISIS-L2 level 2' 'lsp-password keychain ISIS-L2' commit \
    'show configuration failed' end
  sleep 45
  XS 'show isis database' 'show isis database detail level 1' 'show isis statistics' 'show running-config router isis CORE'
  R "$R1" 'show clns traffic' 'show isis database detail' 'show ip route isis' 'ping 10.20.0.1 source 10.255.0.11'
  H "c-3: レベル 2 だけへ戻す"
  X configure 'router isis CORE' 'no lsp-password keychain ISIS-L2' 'lsp-password keychain ISIS-L2 level 2' commit end
  sleep 40
  XS
  R "$R1" 'show ip route isis'
  # 実行記録= isis2-c4.log・isis2-c6.log
  H "c-4: レベル指定なしに戻し、RT01 に経路を足して LSP を作り直させる → XR は L1 LSP を Authentication Failed で捨てる(古い版が残る)"
  X configure 'router isis CORE' 'no lsp-password keychain ISIS-L2 level 2' 'lsp-password keychain ISIS-L2' commit end
  sleep 10
  R "$R1" 'configure terminal' 'interface Loopback99' 'ip address 10.11.99.1 255.255.255.0' 'ip router isis' end
  sleep 25
  X 'show route ipv4 10.11.99.0/24' 'show isis database RT01.00-00' "show isis interface $G1 | include \"Rejected|Received\""
  H "c-5: レベル 2 だけへ戻す → 届く"
  X configure 'router isis CORE' 'no lsp-password keychain ISIS-L2' 'lsp-password keychain ISIS-L2 level 2' commit end
  sleep 30
  X 'show route ipv4 10.11.99.0/24'
  R "$R1" 'configure terminal' 'no interface Loopback99' end
  H "c-6: 鍵のアルゴリズムを外す(有効期間はあり)→ ハローが認証に失敗して隣接が落ちる → 戻す"
  X configure 'key chain ISIS-L2' 'key 1' 'no cryptographic-algorithm' commit end
  sleep 45
  X 'show isis adjacency level 2' "show isis interface $G2 | include \"Rejected|Received\""
  X configure 'key chain ISIS-L2' 'key 1' 'cryptographic-algorithm HMAC-MD5' commit end
  sleep 35
  X 'show isis adjacency level 2'
}

d() {
  H "d-1: SVC-LAN を M4-1 の癖で p2p にして載せる(L2 だけ・ハロー認証あり)"
  X configure 'router isis CORE' "interface $G4" 'circuit-type level-2-only' 'point-to-point' 'hello-password keychain ISIS-L2' \
    'address-family ipv4 unicast' exit 'address-family ipv6 unicast' commit 'show configuration failed' end
  sleep 40
  XS "show isis interface $G4"
  R "$R2" 'show clns neighbors' 'show clns interface Ethernet0/2'
  H "d-2: broadcast に戻す(優先度は既定)"
  X configure 'router isis CORE' "interface $G4" 'no point-to-point' commit end
  sleep 50
  XS "show isis interface $G4" 'show isis database' 'show isis neighbors'
  R "$R2" 'show clns neighbors' 'show clns interface Ethernet0/2' 'show isis database'
  R "$R3" 'show clns interface Ethernet0/2'
  H "d-3: 優先度 100(レベルなし)= 奪い取るか"
  X configure 'router isis CORE' "interface $G4" 'priority 100' commit 'show configuration failed' end
  sleep 30
  X "show isis interface $G4" 'show isis database' 'show isis adjacency-log' 'show running-config router isis CORE interface'" $G4"
  R "$R3" 'show clns interface Ethernet0/2' 'show isis database'
  H "d-4: レベル 2 だけ 100(レベル 1 は既定)"
  X configure 'router isis CORE' "interface $G4" 'no priority 100' 'priority 100 level 2' commit 'show configuration failed' end
  sleep 20
  X "show isis interface $G4"
  H "d-5: circuit-type を外したとき(L1 ハローも出す)の見え方"
  X configure 'router isis CORE' "interface $G4" 'no circuit-type' commit end
  sleep 30
  X "show isis interface $G4" 'show isis adjacency'
  X configure 'router isis CORE' "interface $G4" 'circuit-type level-2-only' commit end
}

e() {
  H "e-1: 要約の前(バックボーンが見る RT01 のアクセス LAN)"
  R "$R2" 'show ip route 10.11.0.0 255.255.0.0 longer-prefixes' 'show ipv6 route isis'
  H "e-2: レベルを付けずに要約(IPv4・IPv6)"
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'summary-prefix 10.11.0.0/16' root \
    'router isis CORE' 'address-family ipv6 unicast' 'summary-prefix 2001:db8:1011::/48' commit 'show configuration failed' end
  sleep 40
  X 'show route ipv4 10.11.0.0/16 longer-prefixes' 'show route ipv6 2001:db8:1011::/48 longer-prefixes' 'show route ipv4 10.11.0.0/16' \
    'show isis database detail XR01.00-00' 'show isis database detail level 1 XR01.00-00'
  R "$R2" 'show ip route 10.11.0.0 255.255.0.0 longer-prefixes' 'show ipv6 route isis' 'show ip route 10.11.0.0'
  R "$R1" 'show ip route isis'
  H "e-3: level 2 を明示"
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'no summary-prefix 10.11.0.0/16' 'summary-prefix 10.11.0.0/16 level 2' root \
    'router isis CORE' 'address-family ipv6 unicast' 'no summary-prefix 2001:db8:1011::/48' 'summary-prefix 2001:db8:1011::/48 level 2' \
    commit 'show configuration failed' end
  sleep 40
  X 'show isis database detail XR01.00-00' 'show route ipv4 10.11.0.0/16'
  R "$R2" 'show ip route 10.11.0.0 255.255.0.0 longer-prefixes' 'show ipv6 route isis'
  H "e-4: 構成要素を 1 本残して落とす → 全部落とす(RT01 のループバックを shutdown)"
  R "$R1" 'configure terminal' 'interface Loopback11' shutdown 'interface Loopback12' shutdown 'interface Loopback13' shutdown end
  sleep 30
  R "$R2" 'show ip route 10.11.0.0 255.255.0.0 longer-prefixes'
  R "$R1" 'configure terminal' 'interface Loopback14' shutdown end
  sleep 30
  R "$R2" 'show ip route 10.11.0.0 255.255.0.0 longer-prefixes'
  X 'show route ipv4 10.11.0.0/16'
  R "$R1" 'configure terminal' 'interface Loopback11' 'no shutdown' 'interface Loopback12' 'no shutdown' \
    'interface Loopback13' 'no shutdown' 'interface Loopback14' 'no shutdown' end
  sleep 30
  R "$R2" 'show ip route 10.11.0.0 255.255.0.0 longer-prefixes'
}

f() {
  H "f-1: 案 A(付け替え)の準備= RT01 に新エリア 49.0010 の NET を足す"
  R "$R1" 'configure terminal' 'router isis' 'net 49.0010.0102.5500.0011.00' end 'show clns protocol' 'show clns neighbors detail'
  sleep 20
  X 'show isis adjacency' 'show isis adjacency-log' 'show isis' 'show isis database detail RT01.00-00'
  H "f-2: XR01 を 1 コミットで 49.0010 へ入れ替え"
  X configure 'router isis CORE' 'no net 49.0001.0102.5500.0001.00' 'net 49.0010.0102.5500.0001.00' commit 'show configuration failed' end
  sleep 30
  X 'show isis adjacency' 'show isis adjacency-log' 'show isis' 'show logging last 30'
  R "$R1" 'show clns neighbors detail' 'show ip route isis'
  R "$R2" 'show isis database detail XR01.00-00'
  H "f-3: 戻す(足してから外す= 2 コミット)"
  X configure 'router isis CORE' 'net 49.0001.0102.5500.0001.00' commit end
  sleep 15
  X configure 'router isis CORE' 'no net 49.0010.0102.5500.0001.00' commit end
  sleep 30
  X 'show isis adjacency' 'show isis adjacency-log'
  H "f-4: 案 B(併合)= RT01 を 49.0010 だけにする → XR01 は 49.0001 のまま"
  R "$R1" 'configure terminal' 'router isis' 'no net 49.0001.0102.5500.0011.00' end
  sleep 40
  X 'show isis adjacency' 'show isis adjacency-log' "show isis interface $G1"
  R "$R1" 'show clns neighbors' 'show ip route isis'
  H "f-5: XR01 に 2 つ目の NET(49.0010)を足す"
  X configure 'router isis CORE' 'net 49.0010.0102.5500.0001.00' commit 'show configuration failed' end
  sleep 30
  X 'show isis adjacency' 'show isis' 'show isis database detail XR01.00-00'
  R "$R1" 'show clns neighbors' 'show ip route isis'
  R "$R2" 'show isis database detail XR01.00-00'
  H "f-6: システム ID の違う NET を足せるか・4 つ目の NET"
  X configure 'router isis CORE' 'net 49.0020.0000.0000.0099.00' commit 'show configuration failed' abort
  X configure 'router isis CORE' 'net 49.0020.0102.5500.0001.00' 'net 49.0030.0102.5500.0001.00' commit 'show configuration failed' abort
}

for p in "$@"; do "$p"; done
