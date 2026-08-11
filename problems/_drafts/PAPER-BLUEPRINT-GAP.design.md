# 紙面問題 × ENARSI ブループリント 突合せと強化題材 (BL-100)

2026-08-08 作成。ユーザ指示「紙面問題の、特に**考えさせる系**の範囲を強化したい。
最新ブループリントと突き合わせて、何がカバーできていないか確認」への回答を正典化したもの。

出典= **ENARSI 300-410 v1.1**(2023改訂・Cisco 公式 exam topics PDF)。
本メモは「どの題材を紙面ファミリ(shape)にするか」の選定台帳であり、
個別ファミリの詳細設計は着手時に `problems/_drafts/<名前>.design.md` を別途起こす。

---

## 0. 結論(要旨)

- 現行の紙面 shape は **9 種のうち 7 種が「1.4 再配送とその周辺」に集中**。
  ブループリント加重で見た紙面カバー率は **ざっくり 2 割前後**(L3 35% の半分弱＋α)。
- **2.0 VPN(20%) は紙面ゼロ**、**4.0 Infrastructure Services(25%) は 4.3 debug の一部のみ**、
  **3.0 Infrastructure Security(20%) は uRPF のみ**。
- L3 内部でも、**思考量の多い定番論点**(BGP ベストパス・OSPF エリア/LSA/パス選好・
  EIGRP FD/FS/variance)がまるごと未実装。再配送だけが飽和している。

---

## 1. 現行の紙面 shape 一覧(2026-08-08 時点)

`topologies/gen_paper_mcq.py --shape <...>` の 9 種。

| shape | 生成器 | 主カバー(v1.1 項番) | 備考 |
|---|---|---|---|
| chain | gen_paper_mcq.py 内 | 1.4 / 1.2 | 再配送欠落・誤設定 |
| ring | gen_paper_mcq.py 内 | 1.1 / 1.3 / 1.4 | 定常ループ・distance/filter/tag |
| mploop | gen_paper_mcq.py 内 | 1.1 / 1.3 / 1.4 | 多点相互再配送の誤選択ループ |
| pbr | gen_paper_pbr.py | 1.6 / 3.2.a(道具として) | 被覆エンジン(要件世界で正解反転)の原型 |
| urpf | gen_paper_urpf.py | 3.2.c | 紙面専用。`acl_model.py` で ACL を機械評価 |
| bgpdbg | gen_paper_bgpdbg.py | 1.11.b の一部 / 4.3 の一部 | 紙面初の記述式 |
| leakmap | gen_paper_leakmap.py | 1.5(EIGRP) / 1.2 | fix/cause/read の 3 形 |
| ospfv3pl | gen_paper_ospfv3pl.py | 1.10.a の一部 / 1.2 | fix/read/patch。dual_select(両掛け) |
| aaa | gen_paper_aaa.py | 3.1 | 故障15種・出題形9(BL-101/103) |
| acl | gen_paper_acl.py | 3.2.a / 1.2 | ★ロールを衣装として着せる。6ロール・8形(BL-106) |
| aclv6 | gen_paper_aclv6.py | 3.2.b | IPv4 との差分が主題。select/read/cause/counter(BL-106 P3) |
| v6redist | gen_paper_v6redist.py | 1.4(IPv6 AF) | fix/cause/read/trace(ping 3値) |

### 再利用できる横断資産(新ファミリ実装の初速を決める)

- **`acl_model.py`** = 汎用 ACL 意味評価器(非連続 WC・established・ポート名対応)。
  → **ACL 単独読解・CoPP・IPv6 traffic filter は、この 1 本で「正解の一意性」を機械検証できる。**
- **被覆エンジン方式**(BL-081 で確立) = 故障種 × 要件世界で**正解が反転**する組を作り、
  「直る候補 ≥2・要件適合 = 1」を全組合せ × N seed で機械検証(selftest)。
- **出題形の語彙** = fix(CLI/prose) / cause / read(逆引き) / trace(3値読み分け) / patch(最小修正の切り分け)。
- **後処理** = `messy_mermaid()`(BL-087 図の劣化)・`obfuscate_md()`(BL-088 不親切化)。
- **文体規約** = Cisco 語(公式和訳の逐語訳調)。**選択肢に因果を書かない**(BL-080 恒久規約)。

---

## 2. ブループリント v1.1 全項目 × 紙面カバレッジ

凡例: ✅=紙面あり / △=部分・道具としてのみ / ❌=紙面ゼロ
「ラボ」列 = 実機ラボ資産の有無(紙面化の種になる)

### 1.0 Layer 3 Technologies (35%)

| 項番 | 内容 | 紙面 | ラボ |
|---|---|---|---|
| 1.1 | 管理距離 | ✅ ring | あり |
| 1.2 | route-map(属性・タグ・フィルタ) | △ ring(tag)/leakmap/ospfv3pl | あり |
| 1.3 | ループ防止(filtering,tagging,**split horizon**,**route poisoning**) | △ 前半のみ | 一部 |
| 1.4 | 再配送 | ✅✅ 飽和 | 多数 |
| 1.5 | 手動/自動集約(**auto-summary**,**OSPF summary-address**,**BGP aggregate**) | △ EIGRP のみ | 一部 |
| 1.6 | PBR | ✅ pbr | あり |
| 1.7 | **VRF-Lite** | ❌ | ENARSI-EIGRP-VRF-01 / gen_eigrp_vrf_ts |
| 1.8 | **BFD (describe)** | ❌ | 各問 bfd variant |
| 1.9.a | EIGRP AF v4/v6 | △ v6redist | あり |
| 1.9.b | **EIGRP 隣接・認証** | ❌ | あり |
| 1.9.c | **EIGRP 経路選択(RD/FD/FC/successor/FS/SIA)** | ❌ | ENCOR-EIGRP-VARIANCE-01 |
| 1.9.d | **EIGRP stub** | ❌ | 一部 |
| 1.9.e | **等コスト/不等コスト負荷分散(variance)** | ❌ | ENCOR-EIGRP-VARIANCE-01 |
| 1.9.f | メトリック | △ 再配送 seed metric | あり |
| 1.10.a | OSPFv2/v3 AF | △ ospfv3pl/v6redist | あり |
| 1.10.b | **OSPF 隣接・認証**(hello/dead/area/MTU/network type/auth) | ❌ | ENARSI-OSPF-MADJ-01 |
| 1.10.c | **ネットワーク種別・エリア種別・ルータ種別・仮想リンク** | ❌ | 一部 |
| 1.10.d | **パス選好**(intra > inter > E1 > E2・forward metric) | ❌ | なし |
| 1.11.a | BGP AF v4/v6 | ❌ | あり |
| 1.11.b | BGP 隣接・認証(next-hop,multihop,4byte AS,private AS,route refresh,sync,peer group,states/timers) | △ bgpdbg(multihop/update-source/states のみ) | 多数 |
| 1.11.c | **BGP パス選好属性・ベストパス** | ❌ | ENARSI-BGP-POLICY-01 / gen_bgp_ring_ts |
| 1.11.d | **ルートリフレクタ** | ❌ | GEN-BGPRR-* |
| 1.11.e | **BGP ポリシー(in/out フィルタ・パス操作)** | ❌ | あり |

### 2.0 VPN Technologies (20%) — **紙面ゼロ**

| 項番 | 内容 | 紙面 | ラボ |
|---|---|---|---|
| 2.1 | **MPLS 動作(LSR/LDP/label switching/LSP)** | ❌ | ENARSI-MPLS-L3VPN-01〜06 / gen_mpls_ts |
| 2.2 | **MPLS L3VPN(RD/RT/VPNv4/PE-CE)** | ❌ | 同上 |
| 2.3 | **DMVPN(GRE/mGRE,NHRP,IPsec,dynamic neighbor,spoke-to-spoke)** | ❌ | gen_dmvpn_ts(16故障・実機済) |

### 3.0 Infrastructure Security (20%) — uRPF のみ

| 項番 | 内容 | 紙面 | ラボ |
|---|---|---|---|
| 3.1 | **AAA(TACACS+/RADIUS/local・method list)** | ✅ **aaa(BL-101/103)** | GEN-RADIUS-100 / GEN-AAAGRP / ENCOR-EDGE-HARDEN-01 |
| 3.2.a | **IPv4 ACL(standard/extended/time-based)単独読解** | ✅ **acl(BL-106・2026-08-10)** | ACL 道場(gen_list_dojo) |
| 3.2.b | **IPv6 traffic filter** | ✅ **aclv6(BL-106 P3・2026-08-10)** | PoC のみ(poc/acl §14) |
| 3.2.c | uRPF | ✅ urpf | PoC |
| 3.3 | **CoPP** | ❌ | ENCOR-COPP-01/02/03 |
| 3.4 | **IPv6 First Hop Security**(RA guard/DHCP guard/binding table/ND inspection/source guard) | ❌ | **なし**(完全空白) |

### 4.0 Infrastructure Services (25%) — 4.3 の一部のみ

| 項番 | 内容 | 紙面 | ラボ |
|---|---|---|---|
| 4.1 | **機器管理(console/VTY, telnet/http/https/ssh/scp, tftp)** | ❌ | 一部 |
| 4.2 | **SNMPv2c/v3** | ❌ | gen_snmpv3_ts |
| 4.3 | ログ/syslog/debug/条件付き debug/timestamps | △ bgpdbg(debug 読解) | 一部 |
| 4.4 | **DHCP v4/v6(client/server/relay/options)** | ❌ | ENCOR-DHCP-01 / gen_dhcp_ts / DHCPV6-01 |
| 4.5 | **IP SLA・track** | ❌ | ENCOR-IPSLA-01/02 |
| 4.6 | **NetFlow(v5/v9/FNF)** | ❌ | ENCOR-FNF-01 / gen_fnf_ts |
| 4.7 | **DNA Center assurance** | ❌ | **なし**(実機不可 → 紙面が唯一の受け皿) |

---

## 3. ★ユーザ優先題材(2026-08-08 本人指定) — 実装の第一群

指定は **BGP / AAA / ACL 単独読解 / CoPP / IPv6 traffic filter** の 5 本。
以下は着手順の推奨と、各ファミリの初期設計スケッチ。

### P-A. BGP(1.11.c/e/d/b) — 最優先・複数 shape に分割

紙面 shape 1 本に押し込まず、**論点ごとに shape を分ける**(1 shape = 1 レバーの原則)。

1. **`bgpbest`(1.11.c ベストパス)** — 最有力。
   - 盤面= 同一プレフィックスに 3〜5 経路。属性表(weight/LP/AS-PATH長/origin/MED/eBGP-iBGP/IGP metric/RID)を提示。
   - **要件世界で正解反転**= 「LP は触るな」「AS-PATH prepend 禁止」「対向 AS の設定は不可(inbound のみ)」
     「ベストパスは変えず戻りだけ変える」等 → 同じ盤面でも取るべき手段が変わる。
   - 出題形= fix(どの属性をどこで操作するか) / **read**(現在のベストパスはどれか= 11 段階の適用順) /
     cause(なぜ意図した経路が選ばれないか) / **patch**(既に一部操作済みで理想でない → 最小修正)。
   - ★ 錯乱肢の宝庫= weight は**ローカル専用で伝播しない**・MED は**同一隣接 AS 間でしか比較されない**・
     iBGP 学習経路は**再広告されない**・`bgp always-compare-med` の有無・**next-hop 未解決で候補から落ちる**。
   - 種= `gen_bgp_ring_ts.py`(4台リング・AS 配置抽選)の盤面と実測知見をそのまま流用可。
   - **紙面専用で成立**(show ip bgp の表を合成)。ただし表書式は実測に忠実にすること(BL-095 read 形の教訓)。
2. **`bgppol`(1.11.e ポリシー)** — prefix-list / as-path ACL / community による in/out フィルタとパス操作。
   - `gen_list_dojo.py`(prefix/as-path/ACL 道場)の意味評価器を紙面へ転用できるか要確認。
   - ★ 論点= 送信側抑止は**ピア単位でありAS単位でない**(L3VPN PoC 実測)・`soft-reconfiguration`/`route refresh` 無しでの反映・
     inbound と outbound のどちらで落とすかの選択(要件世界で反転)。
3. **`bgprr`(1.11.d ルートリフレクタ)** — RR の広告ルール(client 学習 → 全体へ、non-client 学習 → client のみ)を
   読解させる。クラスタ ID・冗長 RR・**RR を経由すると next-hop が書き換わらない**問題。
   - 種= 既存 `problems/GEN-BGPRR-80424/`。
4. **`bgpnbr`(1.11.b 残り)** — next-hop-self 欠落・peer-group・timers 不一致・4byte AS 表記・private AS 除去。
   - bgpdbg(記述式)と重複しない範囲を選ぶこと(bgpdbg は update-source/multihop/states を既に押さえている)。

**着手順の推奨= ① bgpbest → ② bgppol → ③ bgprr → ④ bgpnbr。**

### P-B. ACL 単独読解(3.2.a) — 実装が最も軽い(acl_model.py 直結)

- 現状 ACL は pbr/urpf の**道具**でしかなく、ACL そのものを読ませる問題が無い。
- 盤面= 名前付き/番号付き ACL を IF に in/out 適用。**シーケンス番号・順序・暗黙 deny**。
- 出題形=
  - **read**= 「次のパケットのうち通過するのはどれか」(送信元/宛先/プロトコル/ポートの組を 4〜6 個提示)。
  - **fix**= 要件(例: 特定ホストだけ SSH 許可・戻り通信は許可・時間帯限定)を満たす**最小の追加/挿入**。
  - **patch**= 既存 ACL に 1 行挿入して要件を満たす。**挿入位置(シーケンス番号)が本題**。
  - cause= 「なぜこの通信だけ落ちるか」。
- ★ 論点候補= 先頭一致で後続が**影になる**(shadowing)・`established` と戻り通信・
  **time-based** の絶対/定期(periodic)・非連続ワイルドカード・`log` の副作用・
  **in と out の適用面の取り違え**・番号付き ACL の追記は**末尾に付く**(既存順序を壊せない)。
- **要件世界で反転**= 「既存行の削除禁止(挿入のみ)」「1 行で実現」「ホスト単位列挙禁止」「戻り通信を明示許可せよ」。
- 一意性検証= `acl_model.py` でパケットベクタを全評価 → 「要件適合=1」を機械保証。**紙面専用で成立**。

### P-C. CoPP(3.3) — ACL 読解の応用層。ラボ資産あり

- 盤面= class-map(ACL match) → policy-map(police/drop) → `control-plane` service-policy。
- ★ 論点= **class-default に落ちた管理トラフィックが道連れで落ちる**(QoS 系の定番教訓＝
  「負の要件は単独採点しない」の紙面版)・ACL の順序で誤ったクラスに入る・
  **conform/exceed action の取り違え**・`police` レート単位・**適用方向(input のみ)**・
  ARP/OSPF hello/BGP keepalive の扱い(control-plane に上がるものは何か)。
- 出題形= read(このパケットはどのクラスに入るか / 落ちるか) / cause(SSH だけ切れる) /
  fix(要件= 「BGP は保護しつつ ICMP を絞る」等)。
- 要件世界で反転= 「新しいクラスを増やすな」「ACL を書き換えるな」「class-default は触るな」。
- 種= ENCOR-COPP-01/02/03(実機済)。ACL 部は `acl_model.py` を再利用。**紙面専用で成立**。

### P-D. AAA(3.1) — 「method list の適用順」が思考の核

- 盤面= `aaa new-model` + method list(default / 名前付き) + line/VTY への適用 + サーバ group。
- ★ 論点= **default と名前付きの取り違え**(line に適用し忘れると default が効く)・
  **フォールバック順**(group radius → local → none)とサーバ無応答時の実挙動・
  `aaa authorization exec` の有無で**ログインできるが特権に上がれない**・
  **console と VTY で挙動が違う**(`aaa authentication login default` の巻き添え)・
  `enable` 認証の別系統・**サーバ到達不能時に締め出される**構成の判別。
- 出題形= read(この状態で誰がどこからログインできるか) / cause(締め出しの原因) /
  fix(要件= 「サーバ障害時も console からは入れること」)。
- 要件世界で反転= 「local ユーザを増やすな」「default を変えるな」「TACACS+ を必須」。
- 種= GEN-RADIUS-100 / ENCOR-EDGE-HARDEN-01。**実機 PoC が要る論点**(フォールバック実挙動・
  タイムアウト時の見え方)は `poc/aaa/` を起こしてから。

### P-E. IPv6 traffic filter(3.2.b) — 空白かつ ACL 資産が効く

- 盤面= `ipv6 access-list` + `ipv6 traffic-filter <name> in|out`。
- ★ IPv4 ACL との**差分が本題**=
  - **末尾の暗黙 permit が 2 行**(`permit icmp any any nd-na` / `nd-ns`)→ ND が暗黙で通る。
    → **明示 deny を書くと ND が落ちて隣接ごと壊れる**(最大の考えさせポイント)。
    ★**実測で確認済み**(2026-08-10・poc/acl §14-2 の V7)= 隣接が **INCMP** になり、
    `permit icmp any any nd-ns` / `nd-na` を手前に置けば回復する。
    ★ただし**最初の測定では誤った結論を出しかけた**(§14-2b)。測定設計に注意。
  - ワイルドカードマスクではなく**プレフィックス長**表記。
  - 適用コマンドが `ip access-group` ではなく **`ipv6 traffic-filter`**(RA guard/ND inspection とは別物)。
  - リンクローカル宛/発の扱い・`sequence` 番号。
- 出題形= read(通る/落ちる) / cause(フィルタを入れた途端に隣接が落ちた) / fix(最小の是正)。
- 要件世界で反転= 「暗黙 deny に頼らず明示せよ」「ND を壊すな」「link-local は落とすな」。
- **実機 PoC 推奨**(暗黙 permit 2 行の実出力・`show ipv6 access-list` の書式)→ `poc/ipv6-filter/`。

---

## 4. 第二群以降(ユーザ優先の 5 本の次)

順序は「加重 × 思考密度 × 実装容易性」の目安。

1. **OSPF エリア/LSA/パス選好(1.10.c/d)** — LSDB 断片・LSA 種別 × エリア種別(stub/totally/NSSA)の
   到達可否、**intra > inter > E1 > E2** と forward metric。紙面専用で成立・思考密度が高い。
2. **DMVPN 紙面化(2.3)** — 20% セクションへの最初の一手。`gen_dmvpn_ts.py` の 16 故障が種。
   NHRP 登録・mGRE・spoke-to-spoke のショートカット・Attrb 列の読解。
3. **EIGRP FD/RD/FC/FS・variance(1.9.c/e)** — 計算＋条件判定型。`show ip eigrp topology` の
   合成表から FS 判定/負荷分散本数を問う。一意性の機械検証が最も素直に効く。
4. **MPLS ラベル読解(2.1/2.2)** — 実機ラボが 7〜12 台で重いぶん紙面化の費用対効果が高い。
   ラベルスタック(VPN ラベル + トランスポートラベル)・PHP・RD と RT の役割取り違え。
5. **IPv6 First Hop Security(3.4)・DNA Center assurance(4.7)** — 現状ラボにも無い完全な空白。
   describe レベルなので紙面が唯一の受け皿。
6. **4.0 の実機資産の紙面転用** — SNMPv3(4.2)/DHCP(4.4)/IP SLA・track(4.5)/NetFlow(4.6)。
   いずれも既存生成器の故障カタログを「紙面の故障種」に写像するだけで初速が出る。
7. **細目の穴埋め** — 1.3 split horizon / route poisoning、1.5 auto-summary・OSPF summary-address・
   BGP aggregate-address、1.7 VRF-Lite、1.8 BFD(describe)、1.9.b/d、4.1、4.3 の条件付き debug。

---

## 5. 新ファミリを起こすときの共通チェックリスト

既存 9 ファミリで踏んだ罠の要約(BL-081/084/095/097/098 由来)。着手時に必ず確認する。

1. **1 shape = 1 レバー**。論点を欲張ると要件世界の直交性が壊れる。
2. **候補は「絶対状態」でなく「現在状態からの差分」で持つ**(BL-098 ①)。
   絶対状態だと「触るな」系の要件が壊れた設定を暗黙修復し、提示 CLI と適合判定がずれる。
3. **fix 形は CLI 提示を基本に**。散文だと「参照や metric の是正を含むか」が曖昧になる(BL-098 ②)。
4. **cause の錯乱肢は claim を機械判定**して偽のものだけ採る。手書きの排他表は破綻する(BL-098 ④)。
5. **要件世界と故障種の非両立**は `compatible_worlds()` で明示的に除外(BL-098 ⑤)。
6. **等価な最終状態は意味シグネチャで畳む**(dedupe・BL-084)。
7. **read 形の出力書式は実測に忠実**に。合成表でも実機の桁・列・語順を守る。
8. **選択肢に因果を書かない**(BL-080 恒久規約)。正解肢と誤答肢の字数粒度も揃える(BL-086)。
9. **文体は Cisco 語**(公式和訳の逐語訳調)。仕上げに `obfuscate_md()`(BL-088)・`messy_mermaid()`(BL-087)。
10. **selftest で一意性を全組合せ × N seed 検証**。ただし**機械検証は自モデルの誤りを検出できない**
    (BL-081 の教訓)→ 挙動の根拠は実測 PoC か、実測済み既存知見に紐付けること。
11. 実機挙動に依存する論点は `poc/<名前>/README.md` に実測表を作ってから実装に入る。
12. ★★**「定説と違う」という結論が出たら、それを最も疑う**(BL-106 で2度踏んだ)。
    採用する前に、**条件を1つずつ変えた対照**を必ず取る。効いた条件は実際に次の4つだった=
    **①観測指標**(ping の成否ではなく隣接の REACH/INCMP だった)
    **②参照の経路**(直接指定か route-map 経由か)
    **③方向**(in か out か)
    **④投入の順序**(定義→参照か参照→定義か)。
    「効いていないように見える」ときは、**その観測が本当に対象を捉えているか**を
    カウンタの内訳で裏取りする(自分の permit 行が対象を覆っていないか)。
13. ★**紙面 shape は実機フルサイクルの安全網が無い**ことを自覚する。
    ラボ問(broken→fix→100)はモデルが実機と食い違えば必ず露見するが、
    **紙面は写像モデルが唯一の真実**なので誤りが露見しない。
    → 紙面ほど PoC の設計(対照の有無)に注意が要る。BL-106 の誤り2件とも紙面で起きた。

---

## 6. 参照

- ENARSI 300-410 v1.1 exam topics(Cisco 公式 PDF)
- 台帳= [BACKLOG.md](../../BACKLOG.md) BL-100(本メモ)・BL-082(紙面MCQ 拡張ロードマップ)
- 既存ファミリ設計= `problems/_drafts/PAPER-PBR-WILDCARD.design.md` /
  `OSPFV3-PL-PAPER.design.md` / `IPV6-REDIST-PAPER.design.md`
- 実測= `poc/leakmap/` `poc/ospfv3-pl/` `poc/v6redist/` `poc/pbr/` `poc/bgpdbg/` `poc/bgp-ring/`
