# 問題 GEN-DMVPN-52429 : DMVPN (Phase 3 + IKEv2) トラブルシュート（難易度3）

## 状況

本社 (RT01) をハブ、支店1 (RT02)・支店2 (RT03) をスポークとする **DMVPN**
（IPsec 暗号化つき・Phase 3）が稼働している。RT04 は事業者の WAN 網（**変更禁止**）。
**昨日までは全拠点が正常に通信でき、支店間はオンデマンドの直接暗号化トンネルで
通信していた。** 本日、下記のトラブルチケットが発行された。原因を切り分けて
**設定仕様書どおりの状態へ復旧**せよ。

```
   RT01 (Hub/NHS, Lo0=1.1.1.1)
     |
   RT04 (WAN transit・変更禁止)
   /  \
RT02    RT03 (Spokes, Lo0=2.2.2.2/3.3.3.3)
```

## トラブルチケット

> **本社⇔支店は正常**だが、**支店1⇔支店2 の通信だけが不能**になっている。昨夜、本社ルータで設定restore作業が行われた。

## 設定仕様書（正常時にあるべき姿・この値が正）

| 項目 | 指定値 |
|------|--------|
| トンネル | 全拠点 `Tunnel0` 1本のみ（mGRE）・overlay **`10.255.145.0/24`**（ハブ`.1`/支店1`.2`/支店2`.3`） |
| GRE キー | **543** / NHRP network-id **59** / NHRP 認証 **`CRYPTD52`** |
| フェーズ | **Phase 3**（経路はハブ向きのまま・支店間トラフィックは直接暗号化トンネルで疎通） |
| MTU / MSS | ip mtu **1400** / tcp adjust-mss **1360** |
| IKE | **IKEv2**・AES-GCM-256 / PRF SHA-384 / DH 19・PSK 全拠点共通 **`Ss2026#Gen8044`** ・DPD 30/5 on-demand |
| IPsec | ESP **AES-GCM-256**・**transport mode**・PFS group19 |
| ルーティング | EIGRP **AS 434**（トンネル区間＋各 Loopback0） |

## 遵守事項

1. RT04（WAN 網）と underlay（物理IF の IP・/30）は変更禁止。
2. 仕様書の値・方式へ**復旧**すること（暗号の撤去や別方式への置換による「復旧」は不可）。
3. スポーク間専用トンネルの追加は禁止（`Tunnel0` 1本のみ）。
4. 原因の種類・場所は伏せている。`show dmvpn` / `show crypto ikev2 sa` /
   `show crypto ipsec sa` / `show ip nhrp nhs detail` / `show ip eigrp neighbors`
   などで**状態から**切り分けること。

## アクセス・採点

CML コンソールで各機にログイン（`SUZUKI / CCNP`）。
```
ansible-playbook playbooks/grade.yml -e problem=GEN-DMVPN-52429 --vault-password-file <(printf 'CCNP\n')
```
> 採点はコンソール収集（`access: console`）。支店間の直結は採点時に能動 ping で誘発される。
