# U-M13 自動化とアシュアランス(SPCOR 5.0)— 出典照合表(ソース検証マトリクス)

目的: SPCOR 5.0 の知識問(紙面)の正誤の根拠をそろえる(BL-264)。対象は、XR トラック M13 の読み物
([付録](../courses/xr/en/e6-m13-appendix.md)・本文 e00/e0/e2/e4)が述べる 5.1〜5.6 の事実と、5.7〜5.10 のうち版によらない
プロトコルの事実。知識項目 108 件(5.1〜5.6 が #1〜#83、5.7〜5.10 が #84〜#108)。判定は確定 98 件・要実測 1 件・要ユーザ判断 9 件。
照合日 2026-11-10。
実機欄の根拠は PoC の盤面(`problems/_POC-XRAUTO`・XRv 9000 と XRd の 26.1.1 を並べたもの。記録 `poc/xr/expAUTO-*.log`)と
XRT-15 の盤面(XRd 26.1.1・Catalyst 8000V 17.15.1a・IOL 17.15。記録 `poc/xr/expXRT15-*.log`)、設計書
[XR-TRACK.design.md](../problems/_drafts/XR-TRACK.design.md) の §30.4・§30.9。

**凡例**
- 列「Cisco 公式」= cisco.com の設定ガイド・コマンド リファレンス・TAC 文書、nso-docs.cisco.com(NSO の公式文書)、Cisco が公開する
  YANG のモデル(github.com/YangModels/yang の vendor/cisco)。列「標準・ツールの公式」= RFC(rfc-editor.org)、IANA の登録表、OpenConfig の
  gNMI の仕様と gNOI・gRIBI のリポジトリ、P4Runtime のリポジトリ、docs.ansible.com とコレクションの文書、developer.hashicorp.com、
  CiscoDevNet の Terraform のプロバイダーの文書(Terraform Registry と GitHub)。
- 出典欄: ○= 一致 / △= 表現差・一部のみ記載・機種や版の差 / ×= 相違 / —= 未記載。続けて出典キー(下表)と要旨・原文の短い引用。
- 引用の表記: 「」= 本文をテキストで取得して照合した**原文**(RFC・IANA・OpenConfig/GitHub・nso-docs・docs.ansible.com・HashiCorp・
  Terraform のプロバイダーは curl で取得、cisco.com の PDF は pdftotext で取り出したもの)。〔要旨〕= cisco.com の HTML を WebFetch の要約経由で
  読んだもの(cisco.com は curl が 403。**言い回しを出題の根拠にしない**)。
- 実機欄: ○= 実測済(要点) / ×= 実機と相違 / 要実測 / 未実測(この単元の機材では試せない・試していない) / 不要(概念)。
- 判定: **確定**(出題に使ってよい) / **要実測**(実機で確かめてから出題) / **要ユーザ判断**(出典が割れる・版で変わる・文書に無く実機だけ。
  出題上の扱いを決める必要)。
- 信頼順 2 の解説サイト(ネットワークエンジニアとして)と商用問題集は、この表では照合していない。xrdocs.io は使っていない。

## 出典キー

### Cisco 公式

| キー | 文書 | URL | 取得 |
|---|---|---|---|
| C-PRG-A9K | Programmability Configuration Guide for ASR 9000, IOS XR 26.1.x–26.3.x(2026-09-08。章: drive-network-automation…、use-netconf…、use-grpc…、unified-data-models、automation-scripts、config-scripts) | https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/26xx/programmability/configuration/guide/b-programmability-cg-asr9000-26xx.html | WebFetch〔要旨〕 |
| C-PRG-8K | Programmability Configuration Guide for Cisco 8000, IOS XR(累積版・2026-06-09。章: Data Models for Network Automation、gRPC Fundamentals、gRPC Applications and Configuration) | https://www.cisco.com/c/en/us/td/docs/iosxr/cisco8000/programmability/b-programmability-configuration-guide-cisco8000.html | WebFetch〔要旨〕 |
| C-DM-2019 | Cisco 8000 Data Models(2019。モデル名の接尾辞の定義) | https://www.cisco.com/c/en/us/td/docs/iosxr/datamodels/b-install-data-models.html | WebFetch〔要旨〕 |
| C-SYS-A9K-NC | System Management Configuration Guide for ASR 9000, IOS XR 26.1.x–26.3.x — Configuring Network Configuration Protocol | https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/system-management/configuration/guide/b-system-management-cg-asr9000-26xx/configuring-netconf.html | WebFetch〔要旨〕 |
| C-TEL-8K | Telemetry Configuration Guide for Cisco 8000(累積版・2026-09-08) | https://www.cisco.com/c/en/us/td/docs/iosxr/cisco8000/telemetry/configuration-guide/telemetry-cg-8000.html | WebFetch〔要旨〕 |
| C-TEL-5500 | Telemetry Configuration Guide for NCS 5500, IOS XR 26.1.x–26.3.x | https://www.cisco.com/c/en/us/td/docs/iosxr/ncs5500/telemetry/26xx/configuration/guide/b-telemetry-cg-ncs5500-26xx.html | WebFetch〔要旨〕 |
| C-NF-A9K | Netflow Configuration Guide for ASR 9000, IOS XR 26.1.x–26.3.x | https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/26xx/netflow/configuration/guide/b-netflow-cg-asr9k-26xx.html | WebFetch〔要旨〕 |
| C-SNMP-5500 | System Management Configuration Guide for NCS 5500, IOS XR 26.1.x–26.3.x — Configuring Simple Network Management Protocol | https://www.cisco.com/c/en/us/td/docs/iosxr/ncs5500/sysman/26xx/configuration/guide/b-system-management-cg-ncs5500-26xx.html | WebFetch〔要旨〕 |
| C-ZTP-540 | System Setup and Software Installation Guide for NCS 540, IOS XR 25.1.x–25.4.x — Provision Network Devices using Zero Touch Provisioning | https://www.cisco.com/c/en/us/td/docs/iosxr/ncs5xx/system-setup/25xx/b-system-setup-cg-25xx-ncs540/configure-ztp.html | WebFetch〔要旨〕 |
| C-ZTP-CR | System Management Command Reference for Cisco 8000 — Zero Touch Provisioning Commands | https://www.cisco.com/c/en/us/td/docs/iosxr/cisco8000/system-management/b-system-management/m-ztp-commands.html | WebFetch〔要旨〕 |
| C-ZTP-TAC | TAC 217224 Zero Touch Provisioning Implementation and Troubleshooting Tips | https://www.cisco.com/c/en/us/support/docs/ios-nx-os-software/ios-xr-software/217224-zero-touch-provisioning-implementation-a.pdf | PDF 原文 |
| C-SZTP-5500 | System Setup Guide for NCS 5500, IOS XR 25.1.x–25.4.x — Deploy Router Using Secure ZTP | https://www.cisco.com/c/en/us/td/docs/iosxr/ncs5500/system-setup/25xx/configuration/guide/b-system-setup-cg-ncs5500-25xx/m-secure-ztp.pdf | PDF 原文 |
| C-SZTP-73 | System Setup Guide for NCS 5500, IOS XR 7.3.x — Securely Provision Your Network Devices | https://www.cisco.com/c/en/us/td/docs/iosxr/ncs5500/system-setup/73x/b-system-setup-cg-ncs5500-73x/m-secure-ztp.pdf | PDF 原文 |
| C-XE-NC / C-XE-RC / C-XE-GN / C-XE-MDT | Programmability Configuration Guide, Cisco IOS XE 17.15.x — NETCONF / RESTCONF / gNMI / Model-Driven Telemetry | https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/prog/configuration/1715/b_1715_programmability_cg/m_1715_prog_yang_netconf.html (以下 m_1715_prog_restconf.html・m_1715_prog_gnmi.html・m_1715_prog_ietf_telemetry.html) | WebFetch〔要旨〕 |
| C-XE-HTTPS | HTTP Services Configuration Guide, IOS XE 17 — HTTPS–HTTP Server and Client with SSL 3.0 | https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/https/configuration/xe-17/https-xe-17-book/HTTPS--HTTP_Server_and_Client_with_SSL_3-0.html | WebFetch〔要旨〕 |
| C-XE-FNF | Network Services Configuration Guide, IOS XE 17.x — Flexible Netflow Overview(ルータ向け) | https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ntw-servs/b-network-services/m_fnf-fnetflow.html | WebFetch〔要旨〕 |
| C-XE-FNF-C9K | Cisco IOS XE 17 — Flexible NetFlow(Catalyst 9000 向け・2025-09-25) | https://www.cisco.com/c/en/us/td/docs/switches/lan/c9000/fnf-avc/flexible-netflow-configuration-guide.html | WebFetch〔要旨〕 |
| C-XE-SNMP | SNMP Configuration Guide, IOS XE 17 — Configuring SNMP Support | https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/snmp/configuration/xe-17-x/snmp-xe-17-book/nm-snmp-cfg-snmp-support.html | WebFetch〔要旨〕 |
| C-YANG-2611 | Cisco が公開する IOS XR 26.1.1 の YANG のモデルと能力の一覧(cap-2611-xrd-vrouter.xml ほか) | https://github.com/YangModels/yang/tree/main/vendor/cisco/xr/2611 | 原文(curl・pyang 2.7.1) |
| N-AAG | NSO 6.7 — Get Started → NSO at a Glance | https://nso-docs.cisco.com/nso-basics/nso-at-a-glance | 原文 |
| N-FAQ | NSO 6.7 — Get Started → FAQs | https://nso-docs.cisco.com/nso-basics/faqs | 原文 |
| N-CDB | NSO 6.7 — Development → Introduction to Automation → CDB and YANG | https://nso-docs.cisco.com/guides/development/introduction-to-automation/cdb-and-yang | 原文 |
| N-NED | NSO 6.7 — Operation & Usage → Operations → NEDs and Adding Devices | https://nso-docs.cisco.com/guides/operation-and-usage/operations/neds-and-adding-devices | 原文 |
| N-DEVNED | NSO 6.7 — Development → Advanced Development → Developing NEDs | https://nso-docs.cisco.com/guides/development/advanced-development/developing-neds | 原文 |
| N-SVC | NSO 6.7 — Development → Core Concepts → Services | https://nso-docs.cisco.com/guides/development/core-concepts/services | 原文 |
| N-IMPL | NSO 6.7 — Development → Core Concepts → Implementing Services | https://nso-docs.cisco.com/guides/development/core-concepts/implementing-services | 原文 |
| N-DEEP / N-LIFE | NSO 6.7 — Services Deep Dive / Lifecycle Operations | https://nso-docs.cisco.com/guides/development/advanced-development/developing-services/services-deep-dive ・ https://nso-docs.cisco.com/guides/operation-and-usage/operations/lifecycle-operations | 原文 |
| N-BASIC | NSO 6.7 — Operation & Usage → Operations → Basic Operations | https://nso-docs.cisco.com/guides/operation-and-usage/operations/basic-operations | 原文 |
| N-DM | NSO 6.7 — Operation & Usage → Operations → Device Manager | https://nso-docs.cisco.com/guides/operation-and-usage/operations/nso-device-manager | 原文 |
| N-NB / N-SNMP / N-CLI | NSO 6.7 — Northbound APIs / NSO SNMP Agent / Introduction to NSO CLI・CLI Commands | https://nso-docs.cisco.com/guides/development/core-concepts/northbound-apis ・ …/northbound-apis/nso-snmp-agent ・ https://nso-docs.cisco.com/guides/operation-and-usage/cli/introduction-to-nso-cli | 原文 |

### 標準・ツールの公式

| キー | 文書 | URL |
|---|---|---|
| R-6020 | RFC 6020 YANG 1.0(5.6.4 節: hello の能力の URI の `deviations=`) | https://www.rfc-editor.org/rfc/rfc6020.html |
| R-6241 | RFC 6241 NETCONF | https://www.rfc-editor.org/rfc/rfc6241.html |
| R-6242 | RFC 6242 NETCONF over SSH | https://www.rfc-editor.org/rfc/rfc6242.html |
| R-7950 | RFC 7950 YANG 1.1 | https://www.rfc-editor.org/rfc/rfc7950.html |
| R-7951 | RFC 7951 JSON Encoding of Data Modeled with YANG | https://www.rfc-editor.org/rfc/rfc7951.html |
| R-8040 | RFC 8040 RESTCONF | https://www.rfc-editor.org/rfc/rfc8040.html |
| R-8340 | RFC 8340 YANG Tree Diagrams | https://www.rfc-editor.org/rfc/rfc8340.html |
| R-8366 | RFC 8366 A Voucher Artifact for Bootstrapping Protocols | https://www.rfc-editor.org/rfc/rfc8366.html |
| R-8572 | RFC 8572 Secure Zero Touch Provisioning (SZTP) | https://www.rfc-editor.org/rfc/rfc8572.html |
| R-3954 | RFC 3954 NetFlow v9(Informational) | https://www.rfc-editor.org/rfc/rfc3954.html |
| R-7011 | RFC 7011 IPFIX Protocol Specification | https://www.rfc-editor.org/rfc/rfc7011.html |
| R-3411 / R-3414 / R-3415 / R-3416 / R-3417 | RFC 3411(SNMP のアーキテクチャ)・3414(USM)・3415(VACM)・3416(PDU)・3417(トランスポート) | https://www.rfc-editor.org/rfc/rfc3411.html ほか |
| R-3826 | RFC 3826 AES for the SNMP USM | https://www.rfc-editor.org/rfc/rfc3826.html |
| R-1901 | RFC 1901 Community-based SNMPv2(Experimental) | https://www.rfc-editor.org/rfc/rfc1901.html |
| I-PORTS | IANA Service Name and Transport Protocol Port Number Registry | https://www.iana.org/assignments/service-names-port-numbers/ |
| I-IPFIX | IANA IPFIX Information Elements | https://www.iana.org/assignments/ipfix/ |
| O-GNMI | gNMI Specification 0.10.0(2023-05-25)と gnmi.proto | https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md |
| O-GNOI / O-GRIBI | openconfig/gnoi・openconfig/gribi の README | https://github.com/openconfig/gnoi ・ https://github.com/openconfig/gribi |
| P4-RT | p4lang/p4runtime の README | https://github.com/p4lang/p4runtime |
| A-INTRO / A-GS / A-PULL | docs.ansible.com: Introduction to Ansible / Getting started / ansible-pull | https://docs.ansible.com/projects/ansible/latest/getting_started/introduction.html ・ …/getting_started/index.html ・ …/cli/ansible-pull.html |
| A-BASIC / A-NETDIFF | Network Getting Started: Basic Concepts / How Network Automation is Different | https://docs.ansible.com/projects/ansible/latest/network/getting_started/basic_concepts.html ・ …/network_differences.html |
| A-IOSXR / A-IOS / A-PLATIDX | Platform Options: IOS-XR / IOS / Settings by Platform | https://docs.ansible.com/projects/ansible/latest/network/user_guide/platform_iosxr.html ・ …/platform_ios.html ・ …/platform_index.html |
| A-RM / A-CHECK | Network Resource Modules / Validating tasks: check mode and diff mode | https://docs.ansible.com/projects/ansible/latest/network/user_guide/network_resource_modules.html ・ …/playbook_guide/playbooks_checkmode.html |
| A-DOC / A-SRC | cisco.iosxr 12.3.1・cisco.ios 11.4.1 の ansible-doc とソース(ansible-core 2.20.6) | ローカルの `.venv`(galaxy の最新は cisco.iosxr 13.0.0) |
| T-INTRO / T-LANG | Terraform: What is Terraform / The Terraform language | https://developer.hashicorp.com/terraform/intro ・ https://developer.hashicorp.com/terraform/language |
| T-PROV / T-INIT / T-PLAN / T-APPLY / T-DESTROY / T-STATE / T-REFRESH | Terraform: providers・init・plan・apply・destroy・state・refresh | https://developer.hashicorp.com/terraform/language/providers ・ …/cli/commands/init ・ …/plan ・ …/apply ・ …/destroy ・ …/language/state ・ …/cli/commands/refresh |
| T-IOSXR | CiscoDevNet/iosxr 0.7.1(2026-04-10)の docs/index.md・resources と CHANGELOG | https://registry.terraform.io/providers/CiscoDevNet/iosxr ・ https://github.com/CiscoDevNet/terraform-provider-iosxr |
| T-IOSXE | CiscoDevNet/iosxe 1.2.0(2026-11-01)の docs/index.md と CHANGELOG | https://registry.terraform.io/providers/CiscoDevNet/iosxe ・ https://github.com/CiscoDevNet/terraform-provider-iosxe |

---

## 1. プログラマブルなインターフェイス(5.1)

| # | 事実(短く) | Cisco 公式 | 標準・ツールの公式 | 実機 | 判定 |
|---|---|---|---|---|---|
| 1 | モデル駆動の動機= CLI のスクレイピングは柔軟でなく最適でない | ○ C-PRG-A9K〔要旨〕「the general mechanism of CLI scraping is not flexible and optimal」 | — | 不要(概念) | 確定 |
| 2 | NETCONF= XML のエンコード・RPC。SSH のサブシステム "netconf"・IANA の TCP 830 | ○ C-SYS-A9K-NC〔要旨〕「830 is the IANA-assigned TCP port for NETCONF over SSH」 | ○ R-6241 Abstract「It uses an Extensible Markup Language (XML)-based data encoding」/ R-6242「the SSH session is established using the IANA-assigned TCP port 830」/ I-PORTS netconf-ssh 830 | ○ XR01 で 830 が開く(expAUTO-nc) | 確定 |
| 3 | RESTCONF= HTTP の上で YANG のデータに NETCONF のデータストアの考え方でアクセス。https 必須・既定 443 | △ C-XE-HTTPS〔要旨〕 IOS XE の HTTPS サーバの既定 443 | ○ R-8040 Abstract「an HTTP-based protocol that provides a programmatic interface for accessing data defined in YANG」/ §2.2「MUST support the "https" URI scheme, which has the IANA-assigned default port 443」 | ○ PE2 の 443 で GET 200(expXRT15-rc) | 確定 |
| 4 | RESTCONF のメソッド⇔NETCONF の操作(GET= get-config/get、POST= create、PUT= create/replace、PATCH= 中身による、DELETE= delete)。メディア型は application/yang-data+xml・+json | — | ○ R-8040 §4 の表 / §11.3 / R-7951 Abstract | ○ GET 200・PATCH 204 | 確定 |
| 5 | gNMI の RPC は Capabilities・Get・Set・Subscribe | △ C-PRG-A9K〔要旨〕 gNMI の定義のみ | ○ O-GNMI §3「The service consists of the following RPCs」・gnmi.proto の 4 つの rpc | ○ gnmic で 4 つとも(expAUTO-gi) | 確定 |
| 6 | gNMI の仕様はセッションに TLS を必須とし、平文へ落とすことを禁じる | × XR は `no-tls` を持つ(C-PRG-A9K〔要旨〕 認証方式の表「metadata without TLS」) | ○ O-GNMI §3.1「MUST NOT fall back to unencrypted sessions」 | ○ XR の `no-tls` で平文が通る | 要ユーザ判断(D1) |
| 7 | gNMI の 1 つの SetRequest は全部か無しか(トランザクション) | — | ○ O-GNMI §3.4.3「either all modifications within the request are applied, or the target MUST rollback」 | 要実測(任意) | 確定 |
| 8 | gNMI のエンコードは JSON・BYTES・PROTO・ASCII・JSON_IETF の 5 つ | — 対応するエンコードの記述なし | ○ O-GNMI §2.3 の表 | △ XR 26.1.1 の Capabilities は JSON_IETF だけ。JSON の Get は「unsupported get-request encoding」 | 確定(仕様の列挙)。XR の対応は要ユーザ判断(D2) |
| 9 | gNOI= 運用の操作のための gRPC のマイクロサービス群(ping・reboot・file・cert・os など) | ○ C-PRG-A9K〔要旨〕「defines a set of gRPC-based microservices for executing operational commands on network devices」 | ○ O-GNOI README 同文・サービスのディレクトリ(system・file・cert・os ほか) | 不要 | 確定 |
| 10 | gRIBI= 外のクライアントが RIB のエントリを足し引きする(OpenConfig の AFT) | ○ C-PRG-8K〔要旨〕「allows an external client to programmatically manage the routes in the Routing Information Base」 | ○ O-GRIBI「entries can be injected from an external client to a network element」 | 不要 | 確定 |
| 11 | P4Runtime= P4 のプログラムが定めるデータ プレーンの要素を制御する制御プレーンのプロトコル | ○ C-PRG-8K〔要旨〕「a control plane API」 | ○ P4-RT「a control plane protocol for controlling the data plane elements of a device or program defined by a P4 program」 | 不要 | 確定 |
| 12 | IANA のポート: gNMI/gNOI 9339・gRIBI 9340・P4Runtime 9559 | △ C-PRG-8K〔要旨〕 24.1.1 から IANA のポートで待ち受けられる | ○ I-PORTS「gnmi-gnoi,9339」「gribi,9340」「p4runtime,9559」 | 未実測 | 確定(番号)。XR がどれで待つかは版依存(D3) |
| 13 | XR の gRPC のポートは 57344〜57999・既定 57400 | ○ C-PRG-A9K〔要旨〕「The port number ranges from 57344 to 57999」/ △ C-PRG-8K「Earlier … default listening port of 57400」 | — | ○ 57400 | 確定(D3 の注意つき) |
| 14 | テレメトリ: ダイヤルアウト= 機器が収集役へ接続、ダイヤルイン= 収集役が機器へ。ダイヤルインは gRPC だけ。TCP・UDP はダイヤルアウトだけで、UDP は本番に非推奨 | ○ C-TEL-8K〔要旨〕「Dial-out mode: The device initiates the connection to the collector」「Only gRPC supports dial-in sessions」「UDP for Telemetry is not recommended for production networks」 | — | ○ TCP・gRPC(TLS あり/なし)で届く。UDP は未実測 | 確定 |
| 15 | テレメトリのエンコード= compact GPB・self-describing GPB・JSON | ○ C-TEL-8K〔要旨〕 | — | ○ self-describing-gpb | 確定 |
| 16 | テレメトリはプッシュ、SNMP・syslog・CLI はプル | ○ C-TEL-5500〔要旨〕「These traditional methods use a pull model」「Telemetry uses a push model」 | — | 不要 | 確定 |
| 17 | オンボックスの自動化スクリプト 4 種(config・exec・process・EEM)。Python | ○ C-PRG-A9K〔要旨〕 automation-scripts の各行 | — | 未実測 | 確定(Python の版は出題しない) |
| 18 | config スクリプトはコミット時に自動で呼ばれ、エラーで止める・警告・設定の修正ができる | ○ C-PRG-A9K config-scripts〔要旨〕「invoked automatically when you change a configuration and commit the changes」 | — | 未実測 | 確定 |
| 19 | NETCONF は CLI の認可を迂回し、CLI が読むだけのユーザにも既定で書き込みを許す(AAA の認可で抑える) | ○ C-PRG-A9K〔要旨〕 Note「grants by default write permissions for a user, in spite of read-only access configured for this user for CLI access, as CLI authorization is bypassed」 | — | 要実測 | 要実測 |

## 2. YANG(5.4)

| # | 事実(短く) | Cisco 公式 | 標準・ツールの公式 | 実機 | 判定 |
|---|---|---|---|---|---|
| 20 | YANG= 設定データ・状態データ・RPC・通知をモデル化する言語(現行は 1.1) | — | ○ R-7950 Abstract「YANG is a data modeling language used to model configuration data, state data, Remote Procedure Calls, and notifications」 | 不要 | 確定 |
| 21 | module= 自己完結で compilable。import= 他のモジュールの定義を使う、include= 自分の submodule を取り込む | ○ C-YANG-2611(UM が `Cisco-IOS-XR-types` を import) | ○ R-7950 §3「a module is self-contained and "compilable"」/ §7.1.5・§7.1.6 | 不要 | 確定 |
| 22 | submodule= 部分的な定義。belongs-to で所属を書き、所属のモジュールかその submodule からだけ include できる | ○ C-YANG-2611 tailf-common が tailf-meta-extensions・tailf-cli-extensions を include | ○ R-7950 §7.2.2「A submodule MUST only be included by either the module to which it belongs or another submodule that belongs to that module」 | 不要 | 確定 |
| 23 | container(値なしでまとめる)・list(キーで見分ける複数のエントリ)・leaf(値 1 つ)・leaf-list(同じ型の値をいくつも) | ○ C-YANG-2611 um-domain-cfg の木 | ○ R-7950 §3 の定義 | ○ pyang で確認 | 確定 |
| 24 | 設定を表す list には key が必須 | — | ○ R-7950 §7.8.2「MUST be present if the list represents configuration」 | 不要 | 確定 |
| 25 | presence container= 在ること自体が意味を持つ(ツリー図で `!`) | ○ C-YANG-2611 `domain lookup disable` の `disable!` | ○ R-7950 §7.5.1 / R-8340 §2.6「!  for a presence container」 | 不要 | 確定 |
| 26 | config false= 状態データで、設定データストアに入らない。指定が無ければ親と同じ(最上位は true)。false の下に true は置けない | — | ○ R-7950 §7.21.1「Data nodes representing state data are not part of configuration datastores」 | 不要 | 確定 |
| 27 | get-config は設定だけ、get は設定と状態を返す | — | ○ R-6241 §7.1「Retrieve all or part of a specified configuration」/ §7.7「Retrieve running configuration and device state information」 | ○ OpenConfig の `<get>` で state が返る(expAUTO-nc) | 確定 |
| 28 | OpenConfig は物ごとに config(求めたもの)と state(実際)を並べる。XR のネイティブは -cfg と -oper のモジュールに分ける | ○ C-YANG-2611 openconfig-interfaces の木 / C-DM-2019〔要旨〕 | — | ○ | 確定 |
| 29 | augment= ほかのモジュールの木にノードを足す。ツリー図では `prefix:name` | ○ C-YANG-2611 um-ntp-cfg が `/snmp-server/traps` に `ntp` を足す(pyang で `um-ntp-cfg:ntp!`) | ○ R-7950 §7.17 / R-8340 §2.6 | 不要 | 確定 |
| 30 | deviation= サーバがモデルのとおりに実装しない所を示す。deviate は not-supported・add・replace・delete の 4 種 | ○ C-YANG-2611 cisco-xr-openconfig-system-grpc-deviations(`deviate not-supported`)/ C-PRG-8K〔要旨〕 非対応のパスは deviation として公開 | ○ R-7950 §5.6.3・§7.20.3.2 | 不要 | 確定 |
| 31 | hello の能力の URI が `deviations=` で deviation のモジュールを示す | ○ C-YANG-2611 XRd 26.1.1 の能力一覧(23 件に `deviations=`) | ○ R-6020 §5.6.4「deviation-parameter = "deviations=" deviation」/ △ R-7950 §5.6.4 は yang-library での告知に変えた | 未実測(hello の全文は記録していない) | 確定 |
| 32 | rpc= モジュールの操作(input・output)、action= データの木のノードに結び付く操作(1.1 で追加)、notification= サーバが送る出来事 | ○ C-YANG-2611 `Cisco-IOS-XR-ping-act` の `rpcs: ping` | ○ R-7950 §3「action: An operation defined for a node in the data tree」/ §7.14〜7.16 | ○ hello に notification・interleave | 確定 |
| 33 | XR のモデル名の接尾辞: -cfg= 設定、-oper= 運用状態、-act= アクション | △ C-DM-2019〔要旨〕「-cfg indicates a configuration model」「-act indicates a NETCONF action model」(26.x のガイドは例だけ) | — | ○ hello に 3 種 | 確定 |
| 34 | XR のモデルは 3 系統: ネイティブ・統一モデル(UM)・OpenConfig | ○ C-PRG-8K〔要旨〕「Cisco XR native models, Unified models and OpenConfig models」 | — | ○ XRd の hello: UM 約 220・OpenConfig 約 54(全 857) | 確定(個数は出題しない) |
| 35 | 統一モデル= CLI から生成。名前に `um`(`Cisco-IOS-XR-um-<feature>-cfg`)。7.0.1 で導入 | ○ C-PRG-A9K unified-data-models〔要旨〕「Unified models are generated from the CLI」 | — | ○ | 確定(導入の版は出題しない) |
| 36 | ツリー図の記号: rw・ro・`?`・`*`・`[keys]`・`!`・`-x`・`-w`・`-n` | — | ○ R-8340 §2.6 | ○ pyang 2.7.1 で 26.1.1 のモデルから | 確定 |
| 37 | NETCONF の validate= 当てる前に設定全体の構文・意味の誤りを確かめる | — | ○ R-6241 §8.6「checking a complete configuration for syntactical and semantic errors before applying」 | ○ hello に validate:1.1 | 確定 |

## 3. NSO(5.3)

| # | 事実(短く) | Cisco 公式 | 標準・ツールの公式 | 実機 | 判定 |
|---|---|---|---|---|---|
| 38 | NSO= 設定したい人・ソフトとネットワークの機器の間のインターフェイス。マルチベンダー。モデル駆動 | ○ N-AAG「acting as an interface between people or software that want to configure the network and the devices in the network」「hybrid multi-vendor network」「model-driven architecture」 | — | 不要 | 確定 |
| 39 | CDB= YANG のスキーマで定義された木構造の DB。機器の設定の写し・サービスのパラメータ・NSO 自身の設定 | ○ N-AAG「a tree-structured database that is defined by a YANG schema」/ N-CDB「device configurations, service parameters, and even configuration for NSO itself」 | — | 不要 | 確定(起動設定 `ncs.conf` は CDB でなくファイル) |
| 40 | NED= NSO と機器の接続。パッケージとして入れる。機器のインターフェイスで 4 種(NETCONF・CLI・Generic・SNMP)。NETCONF の NED はコード不要 | ○ N-NED「There are four categories of NEDs depending on the device interface」/ N-DEVNED「requires no code. Only YANG models」/ △ N-AAG「two main categories of NEDs: the CLI NEDs, and the Generic NEDs」 | — | 不要 | 確定(「4 種」は機器のインターフェイスでの分類と明記して問う) |
| 41 | CLI の NED は YANG のモデルから CLI を組み立て、出力を読む(コードなし)。SSH・Telnet | ○ N-FAQ「renders Cisco CLI sequences and parses CLI outputs without any code」/ N-NED(管理)の表 | — | 不要 | 確定 |
| 42 | サービス= YANG のサービス モデル+対応付け(XML のテンプレート・Python/Java のコード・両方) | ○ N-SVC「a YANG service model and a mapping definition to the device YANG」/ N-IMPL「you can also implement the mapping logic completely in the code」 | — | 不要 | 確定 |
| 43 | FASTMAP: create だけを書く。逆差分をインスタンスと一緒にしまい、変更・削除は自動 | ○ N-SVC「a single data-mapping definition for the "create" scenario」/ N-IMPL「the reverse of the resulting device configuration is stored together with the service instance」 | — | 不要 | 確定 |
| 44 | create のコードは、同じ入力で毎回同じ機器の変更を生まなければならない | ○ N-IMPL「very important that the service create code produces the same device changes for a given set of input parameters every time」 | — | 不要 | 確定 |
| 45 | re-deploy= 対応付けを再実行して違いを当てる。un-deploy= 機器の設定は消すがサービスは残す | ○ N-DEEP「Re-run the service mapping logic and deploy any changes」/ N-LIFE「Undo the effects of the service instance but keep the service itself」 | — | 不要 | 確定 |
| 46 | トランザクションは全機器にまたがってアトミック。1 台でも失敗すれば全部戻し、CDB も更新しない。CLI の機器も含む | ○ N-AAG「distributed and atomic transaction across all devices in parallel」/ N-BASIC「all changes will be rolled back … and the NSO CDB will not be updated」/ N-FAQ「This includes non-transactional devices like CLI and SNMP」 | — | 不要 | 確定 |
| 47 | `commit dry-run outformat native`= 機器へ送るネイティブのコマンドを、送らずに見せる。コミットごとにロールバックのファイル | ○ N-BASIC「display the net result device commands that will be generated over the native interface」「stores a roll-back file for every commit」 | — | 不要 | 確定(ロールバックのコマンド名は出題しない= D4) |
| 48 | 帯域外の変更: check-sync・compare-config・sync-from・sync-to | ○ N-DM「once an out-of-band configuration has been performed, NSO can detect the fact」 | — | 不要 | 確定 |
| 49 | ノースバウンド: Web UI・CLI(C 形式と J 形式)・RESTCONF・NETCONF・JSON-RPC・Java/Python/Erlang の API。SNMP のエージェントは監視と通知用 | ○ N-AAG「human interfaces like web UI and a CLI, programmable interfaces including RESTCONF, NETCONF, JSON-RPC」/ N-CLI「C-Style (Cisco XR style) and the J-style」/ N-SNMP「used mainly for monitoring and notifications」 | — | 不要 | 確定(6.7 の MCP サーバは出題しない) |

## 4. Ansible と Terraform(5.5)

| # | 事実(短く) | Cisco 公式 | 標準・ツールの公式 | 実機 | 判定 |
|---|---|---|---|---|---|
| 50 | Ansible はエージェントレス。SSH で入る。既定は push(pull は ansible-pull) | — | ○ A-INTRO「Agent-less architecture」「using SSH with existing OS credentials」/ A-PULL「inverts the default push architecture of ansible into a pull architecture」 | 不要 | 確定 |
| 51 | control node・managed node・inventory。playbook は YAML、play は順番のあるタスクの並び、module は collection にまとまる | — | ○ A-GS「A system on which Ansible is installed」「A list of managed nodes」/ A-BASIC「Playbooks are written in YAML」「Ansible modules are grouped in collections」 | 不要 | 確定 |
| 52 | ネットワークのモジュールは機器でなくコントロール ノードで動く | — | ○ A-NETDIFF「the Ansible network modules are executed on the Ansible control node」 | 不要 | 確定 |
| 53 | 接続のプラグイン: network_cli= CLI over SSH、netconf= XML over SSH、httpapi= API over HTTP/HTTPS | — | ○ A-NETDIFF の表 | 不要 | 確定 |
| 54 | ansible_network_os は `cisco.iosxr.iosxr`・`cisco.ios.ios` | — | ○ A-IOSXR・A-IOS | ○ 機器なしの rendered で使用 | 確定 |
| 55 | cisco.iosxr で netconf の接続を使うモジュールは一部だけ | — | △ A-IOSXR「only for modules iosxr_banner, iosxr_interface, iosxr_logging, iosxr_system, iosxr_user」/ × A-PLATIDX の表は netconf 無印 / A-SRC は banner・system・user だけ | 不要 | 要ユーザ判断(D5) |
| 56 | リソース モジュールの state 7 種(merged・replaced・overridden・deleted・gathered・rendered・parsed)。既定 merged。rendered と parsed は機器と通信しない | — | ○ A-RM「does not communicate with the network device and can be used offline」/ A-DOC「choices: [merged, parsed, deleted, replaced, rendered, gathered, overridden] default: merged」 | ○ rendered で XR の `ipv4 address 10.255.210.1 255.255.255.255` | 確定 |
| 57 | 冪等: 望む状態にあれば何も変えない | — | ○ A-INTRO「When the system is in the state your playbook describes, Ansible does not change anything」 | 不要 | 確定 |
| 58 | `--check`= 変えずに、変わるはずのことを報告。`--diff`= 前と後 | — | ○ A-CHECK「In check mode, Ansible runs without making any changes on remote systems」「In diff mode, Ansible provides before-and-after comparisons」 | 不要 | 確定 |
| 59 | Terraform は宣言的(最終の形を書く)。言語は HCL | — | ○ T-INTRO「declarative, meaning that they describe the end state of your infrastructure」/ T-LANG「describing an intended goal rather than the steps」 | 不要 | 確定 |
| 60 | プロバイダー= API と話すプラグイン。`terraform init` が導入する | — | ○ T-PROV「relies on plugins called providers」/ T-INIT「attempts to install the plugins for those providers」 | 不要 | 確定 |
| 61 | plan= 変更の計画を見せる、apply= 実行(承認を求める)、destroy= 管理する物を全部消す | — | ○ T-PLAN「creates an execution plan」/ T-APPLY「executes the operations proposed in a Terraform plan」/ T-DESTROY「deprovisions all objects managed by a Terraform configuration」 | 不要 | 確定 |
| 62 | ステート ファイル(既定 terraform.tfstate)がリソースと実物を結び付ける。操作の前に refresh で実物に合わせる | — | ○ T-STATE「stores each workspace's state in a local file named terraform.tfstate」「store bindings between objects in a remote system and resource instances」「Prior to any operation, Terraform does a refresh」 | 不要 | 確定 |
| 63 | Ansible と Terraform の違い: 手続き(順番のあるタスク)⇔宣言(最終の形)、ステート ファイルが無い⇔有る | — | ○ #51・#57・#59・#62 の出典の組合せ | 不要 | 確定(概念) |
| 64 | Terraform の Cisco のプロバイダー: iosxr= gNMI(既定ポート 57400・TLS 既定 true・証明書の確認は既定 false)、iosxe= NETCONF(1.0.0 で RESTCONF を削除) | — | ○ T-IOSXR 0.7.1「The provider supports the gNMI (HTTP/2-based) protocol for device communication by default」/ T-IOSXE 1.2.0「It communicates with devices using the NETCONF protocol over SSH」・CHANGELOG 1.0.0「Remove RESTCONF protocol support」 | 未実測(Terraform は動かしていない) | 要ユーザ判断(D6) |

## 5. ZTP とセキュア ZTP(5.6)

| # | 事実(短く) | Cisco 公式 | 標準・ツールの公式 | 実機 | 判定 |
|---|---|---|---|---|---|
| 65 | 従来の ZTP は、前の設定が無ければ起動時に自動で始まる | ○ C-ZTP-540〔要旨〕「the ZTP process initiates automatically if the device does not have a prior configuration」 | — | △ M1 のコミット一覧に `ZTP` のコミット(中身は未確認) | 確定 |
| 66 | ファイルの在りかは DHCPv4 のオプション 67・DHCPv6 のオプション 59。管理のポートとデータのポートの両方で、IPv4 が先 | ○ C-ZTP-540〔要旨〕「DHCPv4 using Option 67 (bootfile-name)」「DHCPv6 using Option 59」/ C-ZTP-TAC「The DHCP Offer from the server includes the boot file name in Option 67」 | — | 未実測 | 確定 |
| 67 | ユーザ クラス `xr-config`(7.3.2 から。7.3.1 までは `exr-config`) | ○ C-ZTP-540〔要旨〕 / △ C-ZTP-TAC(古い版の `exr-config`) | — | 未実測 | 要ユーザ判断(D7) |
| 68 | 1 行目で判定: `!! IOS XR`= 設定、`#! /bin/bash`・`#! /bin/sh`・`#! /usr/bin/python`= スクリプト | ○ C-ZTP-TAC「If the file starts with !! IOS XR denotes a configuration file」/ C-ZTP-540〔要旨〕 | — | 未実測 | 確定 |
| 69 | `ztp initiate`(手で始める)・`terminate`・`clean`・`enable`/`disable`(起動時に動かすか) | ○ C-ZTP-CR〔要旨〕「To invoke a new ZTP DHCP session, use the ztp initiate command」/ C-ZTP-540〔要旨〕 | — | 未実測 | 確定 |
| 70 | 従来の ZTP の弱さ: DHCP・DNS・取り外せる記憶装置は信頼できない出どころ。iPXE は HTTPS 非対応 | △ C-ZTP-TAC「Hypertext Transfer Protocol Secure (HTTPS) is not supported as it cannot predict which signature to verify」 | ○ R-8572 §4.1「A removable storage device is an untrusted source」/ §4.3「A DHCP server is an untrusted source of bootstrapping data」 | 不要 | 確定 |
| 71 | SZTP(RFC 8572)= 置いて線をつなぐだけで、安全にブートストラップのデータを得る。XR は RFC 8572 どおりに実装 | ○ C-SZTP-5500「The Cisco IOS XR software implements the secure zero touch provisioning capabilities as described in RFC 8572」 | ○ R-8572 §1「no installer action beyond physical placement and connecting network and power cables」 | 未実測 | 確定 |
| 72 | ブートストラップ サーバ= RFC 8572 の YANG モジュールを実装した RESTCONF サーバ(Cisco の ZTP サーバ= RESTCONF か HTTPS のサーバ) | ○ C-SZTP-5500「can be a RESTCONF or HTTPs server」 | ○ R-8572 §1.2「any RESTCONF server implementing the YANG module defined in Section 7.3」 | 未実測 | 確定 |
| 73 | ブートストラップのデータ= 3 つの成果物(伝達情報・所有者証明書・所有権バウチャー) | ○ C-SZTP-5500 の部品の表 | ○ R-8572 §1.2「the three artifacts defined in Section 3 (conveyed information, owner certificate, and ownership voucher)」 | 未実測 | 確定 |
| 74 | 伝達情報= リダイレクト情報(サーバの一覧と任意のトラスト アンカー)かオンボーディング情報(ブート イメージ・初期設定・スクリプト) | ○ C-SZTP-5500「contains either the redirect information or onboarding information」 | ○ R-8572 §2.1・§2.2 | 未実測 | 確定 |
| 75 | オンボーディング情報の処理順: ブート イメージ → 設定前のスクリプト → 初期設定のコミット → 設定後のスクリプト | — | ○ R-8572 §5.6「first process the boot image information (if any), then execute the pre-configuration script (if any), then commit the initial configuration (if any), and then execute the post-configuration script」 | 未実測 | 確定 |
| 76 | 所有者証明書= 持ち主の身元を公開鍵に結ぶ X.509。伝達情報の署名を確かめる | ○ C-SZTP-5500「uses the owner certificate to verify the signature in the conveyed information artifact」 | ○ R-8572 §1.2 | 未実測 | 確定 |
| 77 | 所有権バウチャー= RFC 8366。メーカー(MASA)が署名。シリアル番号と pinned-domain-cert を持つ。Cisco は依頼に応じて発行(PDC とシリアル番号を出す) | ○ C-SZTP-5500「Cisco supplies Ownership Voucher in response to your request. You must submit the Pinned Domain Certificate and device serial numbers」 | ○ R-8572 §3.3「The ownership voucher is signed by the device's manufacturer」/ R-8366 Abstract「Manufacturer Authorized Signing Authority (MASA)」 | 未実測 | 確定 |
| 78 | 署名付きのデータの検証の順: バウチャー(メーカーのトラスト アンカー・シリアル番号・期限)→ 所有者証明書(pinned-domain-cert への証明書パス)→ 伝達情報の署名。どれかが失敗すれば捨てる | ○ C-SZTP-5500「verifies the ownership voucher by validating its signature to one of its preconfigured trusts anchors」(3 段) | ○ R-8572 §5.4 | 未実測 | 確定 |
| 79 | DHCP は署名付きのデータを運べず、署名なしのリダイレクトだけ。署名なしのリダイレクトでは、サーバの証明書を無条件に受け入れる仮の接続 | — | ○ R-8572 §4.3「only unsigned redirect information can be conveyed via DHCP」/ §5.5「by blindly accepting its TLS server certificate」 | 未実測 | 確定 |
| 80 | DHCP のオプション: v4 は 143、v6 は 136 | ○ C-SZTP-5500「OPTION_V4_SZTP_REDIRECT (143)」「OPTION_V6_SZTP_REDIRECT (136): Use this DHCP v4 code for IPV6」(v6 の行の「v4」は原文の誤記) | ○ R-8572 §8.1「OPTION_V4_SZTP_REDIRECT (143)」・§8.2「OPTION_V6_SZTP_REDIRECT (136)」 | 未実測 | 確定 |
| 81 | 機器の身元= IDevID(IEEE 802.1AR)を推奨。Cisco は SUDI を HW の TAm に持ち、ZTP サーバは Cisco の CA の連なりで SUDI を確かめる | ○ C-SZTP-5500「Routers with HW TAM have the SUDI embedded in TAM」「The ZTP server authenticates the router … using the Trust Anchor Certificate (SUDI certificate)」 | ○ R-8572 §9.2「IDevID certificates, as defined in [Std-802.1AR], are RECOMMENDED」 | 未実測 | 確定(CA の名前は出題しない) |
| 82 | XR のセキュア ZTP は HW の TAm を持つ機種だけ | ○ C-SZTP-5500「Secure ZTP is supported only on platforms that have Hardware TAM support」 | — | 未実測 | 確定 |
| 83 | XR: `ztp secure-mode enable` の後に再起動。出どころは DHCP と USB(USB は署名付きのオンボーディング情報だけ)。セキュアのモードは option 67 を無視。解除は consent token | ○ C-SZTP-5500「enable secure ZTP on the router using the ztp secure-mode enable command and then reload the router」「accepts only the secure-redirect-URL and ignores the presence of boot file name option」/ C-SZTP-73(7.3.1 で導入) | △ R-8572 §4 は DNS も出どころに挙げる(XR の文書は DHCP と USB だけ) | 未実測 | 確定(導入の版は出題しない) |

## 6. 5.7〜5.10 の、版によらないプロトコルの事実

| # | 事実(短く) | Cisco 公式 | 標準・ツールの公式 | 実機 | 判定 |
|---|---|---|---|---|---|
| 84 | NETCONF の candidate= 今の設定に影響せずに組み立てる作業場。commit で running へ。confirmed commit は既定 600 秒で、persist なしならセッションの終了で元に戻る | △ C-PRG-8K〔要旨〕 能力の例に candidate:1.0・confirmed-commit:1.1 | ○ R-6241 §8.3「can be manipulated without impacting the device's current configuration」/ §8.4「by default 600 seconds」「If the session issuing the confirmed commit is terminated … the server MUST restore the configuration」 | ○ XRv 9000: セッションを閉じて約 4 秒後に取り消し(expAUTO-ncconf) | 確定 |
| 85 | XR の NETCONF の有効化= `netconf-yang agent ssh`+`ssh server netconf vrf <vrf>`。IOS XE= `netconf-yang`(権限 15) | ○ C-SYS-A9K-NC〔要旨〕(例に `netconf agent ssh` の誤記)/ C-XE-NC〔要旨〕「you must be a user with privilege level 15」 | — | ○ XR(expAUTO-nc)。XE は要実測 | 確定 |
| 86 | IOS XE の RESTCONF= `ip http secure-server`+`restconf`+権限 15 のユーザ | ○ C-XE-RC〔要旨〕 | — | ○ 8000V: 権限 1 は 403(expXRT15-rc2) | 確定 |
| 87 | XR(XRd・XRv 9000)には RESTCONF のサーバが無い | △ C-PRG-A9K・C-PRG-8K〔要旨〕 YANG の運び手は NETCONF と gRPC とだけ書く(8000 の EEM の章に「NETCONF or RESTCONF」の一文) | — | ○ 26.1.1 で `restconf` が無い(expAUTO-iolrc) | 要ユーザ判断(D8) |
| 88 | テレメトリのダイヤルアウト= destination-group・sensor-group・subscription。既定で TLS(`protocol grpc no-tls` で外す)。tls-hostname は証明書の名前と一致させる。sample-interval はミリ秒(0= イベント駆動) | ○ C-TEL-8K・C-TEL-5500〔要旨〕 | — | ○ 名前違いで宛先が NA(設計書 §30.9) | 確定 |
| 89 | gNMI の Subscribe: ONCE・POLL・STREAM。STREAM は SAMPLE・ON_CHANGE・TARGET_DEFINED。sample_interval はナノ秒。ON_CHANGE は最初に全パスを送り、後は変化時 | △ C-TEL〔要旨〕 SAMPLE・ON_CHANGE・TARGET_DEFINED | ○ O-GNMI §3.5「(`ONCE`)…(`POLL`)…(`STREAM`)」/ §3.5.1.5.2「nanoseconds between samples」「the target MUST first generate updates for all paths」 | ○ ONCE・SAMPLE 10 秒・ON_CHANGE(expAUTO-gi2) | 確定 |
| 90 | XR の相互 TLS= `tls-mutual`。証明書が無いと「certificate required」、信頼しない CA だと「bad certificate」 | ○ C-PRG-A9K〔要旨〕 認証方式の表(metadata with mutual TLS) | — | ○(expAUTO-mtls) | 確定(エラー文は出題しない) |
| 91 | XR が信頼するクライアントの CA は `/misc/config/grpc/ca.cert`、差し替えには `process restart emsd`。ダイヤルアウトの CA は `/misc/config/grpc/dialout/` | △ C-TEL-8K〔要旨〕 ダイヤルアウトの証明書の置き場のみ。ca.cert の差し替えの記述なし | — | ○(expAUTO-mtls2・expXRT15) | 要ユーザ判断(D9) |
| 92 | XR はダイヤルアウトでクライアント証明書を出さない(収集役が求めるとつながらない) | — 記述なし | — | ○(expAUTO-tlsout) | 要ユーザ判断(D9) |
| 93 | NetFlow v9= RFC 3954(Informational)。テンプレートで形を定義する | — | ○ R-3954「The version 9 export format uses templates」・IESG Note | ○ | 確定 |
| 94 | IPFIX= RFC 7011。版番号 10(0x000a)。既定ポート 4739(SCTP・TCP・UDP)、TLS/DTLS は 4740 | △ C-XE-FNF〔要旨〕 `export-protocol ipfix` | ○ R-7011 §3.1「0x000a for the current version」/ §10.1「listens for connections on SCTP, TCP, and/or UDP port 4739」/ I-PORTS ipfix 4739 | ○ 8000V「IPFIX (Version 10)」・nfcapd の 4739 | 確定 |
| 95 | IPFIX のセット= テンプレート セット・オプション テンプレート セット・データ セット。データの記録はテンプレートが定める | — | ○ R-7011 §2「There are three different types of Sets: Template Sets, Options Template Sets, and Data Sets」 | ○ `show flow exporter … templates` | 確定 |
| 96 | UDP ではテンプレートを定期的に送り直さなければならない | — | ○ R-7011 §8.4「MUST periodically retransmit each active Template at regular intervals」 | 要実測(任意) | 確定 |
| 97 | IPFIX の情報要素の番号: 8 sourceIPv4Address・12 destinationIPv4Address・4 protocolIdentifier・7/11 送信元/宛先ポート・10 ingressInterface・1 octetDeltaCount・2 packetDeltaCount・152/153 flowStart/EndMilliseconds | — | ○ I-IPFIX(ElementID と Name) | ○ 8000V の templates の表示 | 確定(番号の暗記は出題しない) |
| 98 | IOS XE の Flexible NetFlow= flow record・flow exporter・flow monitor と、IF の `ip flow monitor <M> input` | ○ C-XE-FNF〔要旨〕 | — | ○ 8000V・IOL | 確定 |
| 99 | IOS XE の cache timeout(active・inactive)。既定 active 1800 秒・inactive 15 秒 | △ C-XE-FNF-C9K〔要旨〕(スイッチ向け)/ C-XE-FNF は active だけ | — | △ 8000V は 1〜604800 を受け付ける・IOL は cache timeout が無い | 要ユーザ判断(D10) |
| 100 | IOS XR の NetFlow= exporter-map・monitor-map・sampler-map。exporter の source は必須 | ○ C-NF-A9K〔要旨〕 | — | × XRd・XRv 9000 26.1.1 に構文が無い | 確定(構文の知識として。仮想の XR の盤面では出さない) |
| 101 | SNMP: エージェントは UDP 161、通知の受け手は UDP 162。メッセージは BER | — | ○ R-3417 §3.2「listen on UDP port 161」「listen on UDP port 162」/ §8 / I-PORTS | ○ | 確定 |
| 102 | SNMPv3 のセキュリティ レベル: noAuthNoPriv・authNoPriv・authPriv | ○ C-SNMP-5500〔要旨〕 group の noauth/auth/priv | ○ R-3411 §3.4.3 | ○ authPriv(SHA・AES 128) | 確定 |
| 103 | USM: 応答を求めない PDU(トラップ)は送り手が権威のエンジン → 受け手は送り手の engine ID でユーザを作る | — | ○ R-3414 §1.5.1「then the sender of such a message is authoritative」 | ○ snmptrapd に `createUser -e 0x<engineID>` | 確定 |
| 104 | AES-128(CFB128)を USM で使う規定= RFC 3826 | — | ○ R-3826「The CFB128-AES-128 Privacy Protocol」 | ○ `priv aes 128` | 確定 |
| 105 | VACM: グループに read・write・notify のビューを当てる | ○ C-SNMP-5500〔要旨〕 / C-XE-SNMP〔要旨〕「[read readview] [write writeview] [notify notifyview]」 | ○ R-3415「viewType - view to be checked (read, write or notify)」 | ○ | 確定 |
| 106 | XR の v3 のトラップは、グループに notify のビューが無いと送られない | △ C-SNMP-5500〔要旨〕 書式に notify はあるが、無いと出ないとは書かない | △ R-3415(notify のビューの存在のみ) | ○ Trap PDUs 0 → notify を足すと届く(expAUTO-sn4) | 要ユーザ判断(D11) |
| 107 | SNMPv2c= コミュニティによる方式(RFC 1901・Experimental)。トラップは確認なし、インフォームは確認あり | — | ○ R-1901 / R-3416 §4.2.6・§4.2.7 / R-3414 §1.5.1(Confirmed・Unconfirmed の Class) | 不要 | 確定 |
| 108 | `snmp-server ifindex persist`= 再起動で ifIndex を変えない(XR・XE とも) | ○ C-SNMP-5500〔要旨〕 / C-XE-SNMP〔要旨〕「ifIndex values that will remain constant across reboots」 | — | ○ XR | 確定 |

---

## 出題しない事柄(版で変わる・この表の外に置く)

- XR の SNMPv3 で DES・3DES が使えなくなった版(25.4.x)、26.3.1 の `secure-v3` と v1/v2c の非推奨の警告。
- XR の gRPC の名前付きのサーバ・SSL プロファイル(25.4.1・Cisco 8000 の文書)、`/misc/config/grpc` の証明書の非推奨の予告、TLS 1.0/1.1 の非推奨。
- gNMI のサブモード(`grpc gnmi port 9339`・24.1.1)と、各機種の既定ポート。
- NSO の版ごとの新機能(6.7 の MCP サーバ)、ロールバックのコマンド名。
- Ansible・Terraform のコレクション/プロバイダーの版と、各版の対応プロトコル。
- XRd 26.1.1 の、トラップの宛先を `auth` から `priv` へ上書きしても `show snmp host` が `v3 auth` のまま、という癖(文書に無い)。

## 食い違い・注意点

| ID | 論点 | 内容 | 出題への影響 |
|---|---|---|---|
| D1 | gNMI の TLS(#6) | 仕様は TLS 必須で平文へのフォールバックを禁じる。XR は `no-tls` で平文を受ける(実装の選択肢) | 「仕様では」と明記するなら確定。「XR では TLS が必須」とは問わない |
| D2 | gNMI のエンコード(#8) | 26.1.1 の XR は JSON_IETF だけを広告し、JSON を拒む。文書に対応表なし | XR の対応を正誤に使わない(版で変わる可能性) |
| D3 | gRPC のポート(#12・#13) | ASR 9000 26.x は 57344〜57999・既定 57400。Cisco 8000 の文書は 24.1.1 から IANA のポート(9339 ほか)を選べると書く | ポートを問うなら「XR の gRPC の既定(57400)」と「IANA の gNMI(9339)」を区別して出す |
| D4 | NSO のロールバック(#47) | 6.x の文書のコマンドは `rollback-files apply-rollback-file`。ファイルを残すことは版によらない | コマンド名は出題しない |
| D5 | Ansible の NETCONF(#55) | IOS-XR のページは 5 つのモジュール(うち 2 つは今は無い名前)、設定の表は無印、コレクションのソースは banner・system・user | 「network_cli が既定で一般的」までを確定として扱う |
| D6 | Terraform のプロバイダー(#64) | iosxr は 0.7.1 で gNMI だけ(開発中の枝に NETCONF)。iosxe は 0.15.0 で NETCONF が既定、1.0.0 で RESTCONF を削除。どちらも最低の版を書かない | 版を明記しない問いでは、プロトコルを正誤に使わない |
| D7 | ZTP のユーザ クラス(#67) | 7.3.2 から `xr-config`、それまでは `exr-config`。TAC 文書と一部のガイドは古い値 | 版を明記しない問いでは使わない |
| D8 | XR の RESTCONF(#87) | 文書は「YANG は NETCONF か gRPC」とだけ書き、RESTCONF の設定が無い(8000 のガイドに 1 か所「NETCONF or RESTCONF」)。26.1.1 の XRd・XRv 9000 にコマンドが無い | 「XR は RESTCONF を持たない」と断定する問いは避ける。「この盤面の XR では」と限る |
| D9 | XR の証明書(#91・#92) | ca.cert の差し替えと emsd の再起動、ダイヤルアウトでクライアント証明書を出さないことは文書に無く、実機だけ。25.4.1 から証明書の管理が SSL プロファイルへ移る予告 | 出題しない(ラボの課題と読み物の落とし穴に留める) |
| D10 | FNF の cache timeout(#99) | ルータ向けの文書は active だけ、スイッチ向けは active/inactive と既定値。8000V は両方を受け、IOL は無い | 既定値は出題しない |
| D11 | v3 のトラップと notify のビュー(#106) | XR では notify が無いと 0 件(実測)。文書は書式だけ。IOS XE の振る舞いは未実測 | 「XR では」と限る。IOS 系と一般化しない |
| D12 | SNMP が答える所 | NCS 5500 26.x の文書は「既定で管理のインターフェイスだけ」。26.1.1 の XRd・XRv 9000 は MPP なしで帯域内でも答えた(版差か機種差) | 出題しない。読み物は「MPP と ACL で絞る」に留める |
| D13 | 文書の誤記 | C-SYS-A9K-NC の例 `netconf agent ssh`(正しくは `netconf-yang agent ssh`)・C-SZTP-5500 の「v6 の行に v4」・C-TEL-8K の `address family ipv4`(ハイフンなし) | 文書の例を問題文に写すときは実機の構文に直す |

## 実機で裏どりが必要な論点

優先度: A= 出題の正誤に直結 / B= 表示・採点に必要 / C= 任意。

| # | 優先 | 論点 | 確認方法の案 | 関連項目 |
|---|---|---|---|---|
| M1 | A | NETCONF が CLI の認可を迂回するか(読むだけのタスク グループのユーザで edit-config が通るか、`aaa authorization exec` で止まるか) | XRT-15 の XR01 に read-only のユーザを作り、ncclient で edit-config | #19 |
| M2 | B | IOS XE の NETCONF(`netconf-yang`・830・candidate の有効化)と gNMI(`gnxi`) | 8000V で有効にして ncclient と gnmic | #85・D3 |
| M3 | B | IOS XE の SNMPv3 のトラップで、グループに notify が無いときの振る舞い | 8000V で XR と同じ手順 | #106・D11 |
| M4 | C | gNMI の SetRequest のトランザクション(1 つの要求に正しい更新と誤った更新を混ぜる) | gnmic set に 2 つの update | #7 |
| M5 | C | IPFIX の UDP のテンプレートの送り直しの間隔(8000V の既定) | nfcapd で受け、tcpdump でテンプレート セットの間隔を測る | #96 |
| M6 | C | テレメトリのダイヤルアウトの UDP | `protocol udp` で telegraf(受け手を UDP に) | #14 |

---

更新方法: 実測したら該当行の「実機」欄を ○+要点に書き換え、判定を更新する。実測の記録の詳細は設計書
[XR-TRACK.design.md](../problems/_drafts/XR-TRACK.design.md) の §30 に追記する(この表には要点だけ書く)。
