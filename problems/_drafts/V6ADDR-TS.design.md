# IPv6 自動アドレッシング TS 生成器（BL-149・gen_v6addr_ts.py）設計メモ

作成 2026-08-25（ユーザ発案）。BL-034 の将来項目「gen_dhcpv6_ts.py（故障11種）」を吸収し、
**SLAAC / stateless DHCPv6 / stateful DHCPv6 / PD を一枚の固定盤面で扱い、
要件 seed 抽選で「正解のアーキテクチャ＝ラボの顔」が変わる**生成器へ拡張する。
GEN-RTCTL v2 の多層抽選（手段×骨格×形）と gen_ipsla_ts のチケット形式を踏襲。

土台: ENARSI-DHCPV6-01（実機済・DHCPV6-SERIES.design.md）＋ PoC 罠8点（poc/dhcpv6/README.md）。

## 0. コア発想 — 「同じ観測、要件次第で verdict が反転」

v4 の gen_dhcp_ts が「故障を当てる」問なのに対し、本生成器は**要件書を読まないと
何が故障かすら決まらない**形を狙う。反転ペアの例:

| 観測される事実 | 世界A では | 世界B では |
|---|---|---|
| クライアントに SLAAC と DHCPv6 のアドレスが両方付く | 純 stateful 要件 → **故障**（no-autoconfig 欠落） | 併存容認要件 → **正常**（触ると減点） |
| LAN で RA が観測されない | SLAAC 要件 → **故障**（ra suppress 残骸） | 「RA 抑止がセキュリティ方針」要件 → **仕様**（真の故障は別、例: クライアントの静的デフォルト欠落） |
| GW が bare `ipv6 dhcp server`（automatic） | named 固定を明記する要件 → **是正対象** | 複数 LAN 集約要件 → **正解形**（named 化すると 1IF1プール置換で壊れる） |
| クライアントのデフォルト経路が静的 | RA 配布要件 → **過剰設定**（RA 由来へ是正） | RA 抑止方針 → **正解** |

★v6 の重要事実（作問の錨）: **DHCPv6 はデフォルトゲートウェイを配れない**（RA が唯一の
配布経路・PoC 実証済み）。「DHCP がデフォルト GW を配る」は v4 の Option 3 の記憶で誤答させる
定番罠 → 要件抽選軸は「RA 由来 / 静的」の2値であり「DHCPv6 が配る」世界は存在させない
（solution.md の裏話と、紙面転用時の誤選択肢に使う）。

## 1. 盤面（固定・5〜6 IOL）

ENARSI-DHCPV6-01 の4台形を拡張。RT02 のデータ IF は 3 本上限内。

```
            RT01 (DHCPv6サーバ, Lo0=2001:DB8:1::1)
              │ 2001:DB8:12::/64
              │
        ┌── RT02 (GW/リレー) ──┐
        │                      │
   LAN-A: CLA            LAN-B: CLB
   (方式は抽選)           (方式は抽選)
```

- 盤面バリアント抽選（骨格）: **(a) 2LAN 形**（上図・4台）/ **(b) 1LAN+PD スパー形**
  （LAN-B を CPE ルータ RT03＋配下 LAN に置換・PD 世界用・5台）。
- サーバ配置抽選: RT01 専用サーバ+リレー / RT02 の GW 直乗せ（リレー故障群の有効・無効が変わる）。

## 2. 要件抽選の3軸（顔を決める）

1. **LAN ごとの方式世界**（LAN-A/B 独立抽選・同一方式の重複は避ける）:
   - W-S: 純 SLAAC（A=1, M=0, O=0）。DNS は RDNSS（`ipv6 nd ra dns server`・★IOL 17.15 対応要 PoC。
     不発なら「DNS 要件なし」世界に縮退）
   - W-SO: SLAAC + stateless DHCPv6（A=1, O=1）— DHCPV6-01 の LAN-A 形
   - W-M: 純 stateful（M=1 + `ipv6 nd prefix ... no-autoconfig`・EUI-64 アドレス禁止の負要件つき）
   - W-MA: stateful + SLAAC 併存容認（M=1, A=1）— 「2重アドレスは故障」という思い込みを外す世界
   - W-PD: CPE が IA_PD で /48 を受け、配下 LAN へ派生 /64 を広告（骨格 (b) 専用）
2. **デフォルト経路の出どころ**: RA 既定 / **RA 抑止方針**（要件書に「LAN では RA を止める」と
   明記 → クライアントは静的デフォルトが正解）
3. **サーバのバインド様式**: automatic（bare）指定 / named 指定 / 指定なし（どちらでも可）

## 3. 故障カタログ（26種・5レイヤ）

既存11種（DHCPV6-SERIES.design.md 末尾）に 15 種を追加。◎=PoC 済メカニズム、○=要 PoC。

### L1: RA/ND（GW 側）
| id | 仕込み | 症状指紋 |
|---|---|---|
| ra_suppress ◎ | `ipv6 nd ra suppress all` 残骸 | SLAAC クライアントが LL のみ・RS にも無応答。★P0 実証: **素の `suppress` は RS 応答が生きる**（バウンス client は再取得）ので故障は `suppress all` 固定。★解錠罠: `no ipv6 nd ra suppress` では `all` は消えない（`no ... suppress all` が要る）→ solution に明記 |
| ra_lifetime_zero ◎ | `ipv6 nd ra lifetime 0` | P0 実証: GUA・DNS は付くのに **デフォルト経路だけ消える**（`show ipv6 route ::/0`=Route not found／brief に GUA あり／`show ipv6 routers` の Lifetime=0）。ra_suppress との切り分けが学び |
| o_flag_missing ◎ | other-config 欠落 | アドレス OK・DNS が来ない（W-SO 世界） |
| m_flag_missing ◎ | managed-config 欠落 | stateful のはずが EUI-64 アドレスに（binding 空） |
| a_not_suppressed ◎ | no-autoconfig 欠落 | W-M 世界でアドレス2重＝負要件違反。W-MA 世界では正常＝**要件反転ペアの主役** |
| nd_prefix_stale ○ | リナンバ前の旧プレフィクスの `ipv6 nd prefix` が併存広告 | 旧 GUA が付き source selection で旧側が選ばれ戻りが死ぬ（旧経路は撤去済）。ping 片方向型 |
| nd_prefix_wrong_len ◎ | /64 以外（例 /72）を広告 | P0 実証: RA に `Prefix .../72 onlink autoconfig` は載る（autoconfig フラグ付き）のに **SLAAC アドレスは生成されない**（IOS は非 /64 で autoconfig しない）＝サイレント。指紋= `show ipv6 routers` に prefix あり／brief に GUA なし |
| flags_swapped ◎ | LAN-A と LAN-B のフラグ一式を入れ替え | 症状がクロスする 2-in-1（`--faults 1` でも読解量が増える複合味） |

### L2: DHCPv6 サーバ
| id | 仕込み | 症状指紋 |
|---|---|---|
| server_attach_missing ◎ | IF の `ipv6 dhcp server` 忘れ（ユーザ例③） | SOLICIT 到達・無応答のサイレント |
| server_named_wrong_pool ◎ | named で別プールに固定 | 誤プール応答 or 無応答。automatic が正解の世界では「named 化した」こと自体が原因 |
| pd_automatic_trap ◎ | PD サーバが bare automatic のまま | **automatic は直接接続の IA_PD に応答しない**（PoC 実証）→ IA_NA は付くのに PD だけ来ない好指紋 |
| link_address_missing ◎ | stateless プールの `link-address` 欠落 | リレー越し LAN だけプール不選択（PoC 実証の教育核心） |
| pool_prefix_mismatch ◎ | `address prefix` がリレー元と不一致 | binding 空のサイレント |
| dns_option_missing ◎ | プールに dns-server 無し | bind は成立・名前解決だけ死ぬ |
| dns_wrong_addr ○ | dns-server がタイポ（別 GUA） | 全チェック緑に見えて DNS 参照先だけ誤り＝show の読み取り採点 |
| pd_pool_missing ◎ | `prefix-delegation pool` 欠落/ヒント不一致 | IA_NA のみ返り general-prefix 空 |
| pd_upstream_route_missing ○ | 委任 /48 への上流側経路欠落 | CPE 配下から外向きは出るが戻りが死ぬ（サーバの自動 static はあるが、その先が無い） |

### L3: リレー / 経路・フィルタ
| id | 仕込み | 症状指紋 |
|---|---|---|
| relay_missing ◎ | LAN IF の relay destination 欠落 | SOLICIT がサーバに届かない（SLAAC は生きる） |
| relay_wrong_dest ◎ | 宛先がサーバの旧アドレス等 | 同上だがリレーのカウンタは進む |
| acl_blocks_dhcpv6 ◎ | 中継 IF の IPv6 ACL（**明示 `permit ipv6 any any` + `deny udp any any eq 546/547`**）を in 適用 | P0 実証: DHCPv6 は `Address State is SOLICIT (6)` で停止・アドレス無し、SLAAC/ND は生存（`Known via "ND"`）。★**deny のみ形は RA(SLAAC) も巻き込み全断**（IPv6 ACL の暗黙 permit は **NS/NA のみ**・RS/RA 対象外を実証）→ 故障は必ず明示 permit 込みで生成。解答者の naive な ACL 縮小が SLAAC を殺す教育点 |
| server_return_route_missing ◎ | サーバから LAN プレフィクスへの戻り経路欠落 | ★P0 で症状是正: **アドレス割当は正常に成立**（binding OK・`Address State OPEN`。リレー制御は接続済み区間+LL で完結し route 不要）。**壊れるのは client→サーバの到達性のみ**（ping 0%・データプレーン片方向）。アドレスが付くので不注意な解答者は原因を探し違える罠 |

### L4: クライアント
| id | 仕込み | 症状指紋 |
|---|---|---|
| ipv6_enable_missing ◎ | `ipv6 address dhcp` 単体で LL 無し | SOLICIT 自体が出ない最凶サイレント（debug `SAS retured Null`・PoC 実証） |
| client_mode_mismatch ◎ | 要件 stateful なのに autoconfig（逆も） | 要件書と `show ipv6 interface` の突き合わせでしか気づけない |
| client_default_missing ◎ | stateful 世界で `autoconfig default` 欠落 | アドレス OK・off-link 死（stateful はデフォルトを配らない、の実技版） |
| client_static_default_missing ◎ | RA 抑止方針世界で静的デフォルト無し | 「RA が止まってる！」と GW を直しに行くと要件違反＝**世界2の主役罠** |
| client_stale_static ○ | リナンバ残骸の静的旧 GUA が併存 | nd_prefix_stale のクライアント側版・source selection 起因の片方向 |

### L5: 異物（セキュリティ接続・BL-146 への橋）
| id | 仕込み | 症状指紋 |
|---|---|---|
| rogue_ra ◎ | LAN 内の別ルータ（先行侵入済の設定残骸という体）が高 preference RA で誤プレフィクス/自身をデフォルト広告 | P0 実証: client に**偽 GUA が追加形成**され `show ipv6 routers` に `Preference=High` の偽ルータが正規(Medium)と並ぶ・外向きは偽デフォルトへ。fix=異物特定と RA 停止。★**採点は「偽ルータ不在＋到達性回復」で**（shut すると最終 RA lifetime 0 で default は数秒で消えるが、**偽 GUA は valid lifetime 分残留**＝消失を条件にしない）。恒久対策=RA Guard（BL-146）へ接続 |
| dad_conflict ◎ | 手動 LL を2台に重複設定（[[ccnp-ipv6-eui64-linklocal]] の「手動 LL が interface-id になる」挙動で衝突を決定論化） | P0 実証: `%IPV6_ND-4-DUPLICATE`／**`IPv6 is stalled, link-local address is FE80::xx [DUP]`**。LL 自体の衝突で IPv6 が丸ごとストール＝強い決定論指紋。fix=一方の LL 変更 or 手動 LL 除去で EUI-64 に戻す |

## 4. 採点設計の要点（PoC/v4 の教訓の持ち込み）

- 動的アドレスはプレフィクス regex＋**EUI-64 判定は `A8BB:CCFF:FE`/`FF:FE`**（負要件は not_regex — DHCPV6-01 実績形。
  P0 実測: DHCP 割当は非 EUI-64 のランダム ID `2001:DB8:A:0:3573:E57C:...`／SLAAC は `2001:DB8:A:0:A8BB:CCFF:FE..`）。
- ★**クライアント視点の RA 検証主力 = `show ipv6 routers`**（P0 採用）: 1 コマンドで受信 RA の
  `AddrFlag`(M)/`OtherFlag`(O)/`Preference`/`Lifetime`/`Prefix .. onlink autoconfig`/`DNS server` を確認。
  M/O 使い分け・rogue の High・lifetime 0・DNS-in-SLAAC・非 /64 prefix の判定を全てここで拾える。
- RA フラグは `show ipv6 interface` の文言行（M 時 `Hosts use DHCP to obtain routable addresses.`）でも可、
  クライアントは `Address State is OPEN` / `show ipv6 general-prefix` / サーバ binding。
- **破壊と観測は1本に閉じ込める**（AAA P2 教訓）＋ v4 教訓「renew 発火はリセット競合」の v6 版:
  クライアント再始動は `no ipv6 address dhcp`→再投入のみ（clear は backoff 中無効）。
  採点はDHCPV6-01 実績の max_attempts=8 / settle_delay=15 を既定に。
- RA 周期 200 秒問題: fix 後の反映待ちは RS で短絡できる（クライアント IF bounce は解答者の操作として
  solution.md に明記）。採点側からは device 設定を触らない。
- rogue_ra は fix 後も**旧デフォルトが lifetime 満了まで残留**する懸念 → 採点前提（クライアント bounce 要否）を PoC で確定させる。
- 症状文（チケット文面）も実測対象（gen_ipsla_ts の教訓: 机上予測チケットの矛盾を出題初日にユーザが発見）。

## 5. 追加 PoC 項目 — ✅ 全項目成立 (2026-08-25・poc/v6addr/README.md)

IOL 17.15 実機（POC-V6ADDR・コンソール専用・撤収済）で 8 項目すべて確認。要点:

1. ✅ `suppress`（RS 応答生存）vs `suppress all`（全断）＝故障は `all` 固定・`no ... all` 解錠罠
2. ✅ `ra lifetime 0`＝GUA 付くがデフォルト経路だけ消える（別指紋）
3. ✅ RDNSS bare 形受理／client は `show ipv6 routers` に表示・実リゾルバ未使用＝**採点は routers 行のみ**
4. ✅ 非 /64＝RA に載るが GUA 生成されない完全サイレント
5. ✅ rogue RA＝偽 GUA+High preference／**fix 後 default は最終 RA で数秒・偽 GUA は残留**＝採点は不在+到達性
6. ✅ DAD＝`IPv6 is stalled ... [DUP]`＋`%IPV6_ND-4-DUPLICATE`（LL 衝突で全ストール・決定論）
7. ✅ ACL＝**明示 permit + deny 546/547** で DHCPv6 のみ死ぬ／deny のみは RA も全断（暗黙 permit=NS/NA のみ）
8. ✅ 戻り経路欠落＝**割当 OK・到達性のみ片方向で死ぬ**（設計ドラフト症状文を是正）

★採用: クライアント視点の RA 検証主力 = **`show ipv6 routers`**（M/O/preference/lifetime/prefix/DNS を一括表示）。

## 6. 実装フェーズ案

| フェーズ | 内容 | 規模 |
|---|---|---|
| P0 | ✅ **完了 (2026-08-25)** 追加 PoC 8項目（§5・poc/v6addr/README.md）— 全成立・故障 ◎ 化 | 済 |
| P1 | ✅ **完了 (2026-08-26)** gen_v6addr_ts.py（4 IOL・点対点＝DHCPV6-01 形）。2 LAN×世界抽選 {W_SO/W_M/W_MA} 相異なる2つ・故障16種5レイヤ・挙動採点(100正規化)・fix.json・チケット。E2E 2 seed 実機= broken→fix→100（下記） | 済 |
| P2 | ✅ **完了 (2026-08-26)**= 反転世界2つ追加。W_S(純SLAAC+RDNSS・故障 rdnss_missing・DNS採点は `show ipv6 routers` の `DNS server <addr>` 行) / W_MP(RA抑止ポリシー=stateful+静的既定・RA停止は仕様・故障 client_static_default_missing・**RA再有効化は過剰解として RT02 `RAs are suppressed (all)` 監査で降格**)。★E2E 実機= broken81→fix**100**(seed 41001=W_S+W_MP)＋**過剰解(RA再有効化)=84 で降格実証**。automatic↔named 反転は 1 LAN 化が要るため別途 | 済 |
| QA | ✅ **完了 (2026-08-27)** 全故障の実機効果スイープ（§9）。故障 17 種＝全て効果確認。★2 no-op 故障を発見・除去/縮小・採点1件を収束安全化 | 済 |
| P3 | 骨格(b) PD スパー＋PD 故障群（BL-034 Phase 2 の PD 構築問と共通 day0 を検討） | 半日〜1日 |
| P4 | L5 異物系（rogue_ra / dad_conflict）＋ BL-146 FHS ラボへの裏話接続 | 半日 |

ID 案: `GEN-V6ADDR-<seed>`（生成器 gen_v6addr_ts.py）。DHCPv6 に閉じないため
gen_dhcpv6_ts.py という旧称は使わない。パック枠名は `v6addr`。

## 7. P1 実装メモ（2026-08-26・gen_v6addr_ts.py）

- 盤面= RT01(サーバ+Lo0) ─core─ RT02(GW/リレー) ─LAN-A─ CLA / ─LAN-B─ CLB（4 IOL 点対点）。
  クライアント CLA/CLB は IOL ルータをホスト役（node_role=router・DHCPV6-01 踏襲）。
- 世界抽選: 2 LAN に {W_SO, W_M, W_MA} から相異なる2つ。サーバは automatic（bare
  `ipv6 dhcp server`）で 2 プール集約（stateless=link-address／stateful=address prefix で選択）。
- 故障 16 種（ra/server/relay/client/data の5レイヤ）。各故障は FAULT_WORLDS で
  適用可能世界を制限し、pick_faults が seed の世界に適合する LAN を抽選。
  `--fault` が世界不適合なら親切にエラー終了（別 seed 誘導）。
- ★実装で刺さった点:
  - **grade.py は re.search で大小区別**。IOS は IPv6 を大文字表示するが生成器は小文字 hex →
    全 regex に `(?i)` を前置（build_grading で一括）。これを忘れると全アドレス系 FAIL。
  - **ra_suppress は W_SO 限定**に制限。stateful は explicit `ipv6 address dhcp` が
    アドレスを取得してしまい「LL のみ」症状が出ない（チケットが盤面と矛盾＝症状是正原則）。
    stateful の「既定経路だけ死ぬ」は ra_lifetime_zero が担当。
  - 採点合計は世界の組合せでチェック数が変わるため **100 に正規化**（端数は末尾チェックで調整）。
  - fix.json の `parents: "interface {{ links[0] }}"` は fix_generated.yml で
    `image_family: iol`（group_vars 既定）から `Ethernet0/0` に解決される（family 追従）。
    grading.yml は静的なので IF 名は Ethernet0/0 直書き（IOL 固定前提）。
- **E2E 実機（iol-xe 17.15・SSH 採点）**:
  - seed 40004（A:W_SO / B:W_M・client_default_missing@B）= broken **90** → fix → **100**。
    W_SO ステートレス＋W_M 純 stateful（no-EUI-64 負要件）の両基線を確認。
  - seed 40033（A:W_SO / B:W_MA・link_address_missing@A）= broken **90** → fix → **100**。W_MA 併存基線を確認。

## 8. P2 実装メモ（2026-08-26・反転世界）

- **W_S（純 SLAAC + RDNSS）**: DHCPv6/リレー無し。RT02 LAN IF に `ipv6 nd ra dns server <dns>`
  （bare 形。IOL 17.15 実機 OK）。DNS 採点は client `show ipv6 routers` の `DNS server <addr>`
  行（`:` 無し・スペース区切り。dhcp interface 形の `DNS server: <addr>` とは別書式）。
  ドメインは RA では配らない（search-list 未使用）→ W_S の要件は DNS サーバのみ。故障 rdnss_missing。
- **W_MP（RA 抑止ポリシー＝ユーザ例②の反転）**: 「RA 停止」は故障でなく仕様。stateful で
  アドレス取得＋**静的既定**。真の故障は client_static_default_missing。
  ★**実装の要点（実機で判明）**: stateful DHCPv6 のアドレスは **/128**（on-link /64 が無い）＋
  RA 停止 → **グローバル next-hop の静的既定は解決できず ping 不達**。解決=RT02 LAN IF に
  **決定的 LL `ipv6 address FE80::1 link-local`** を置き、端末は
  **`ipv6 route ::/0 <if> FE80::1`**（LL next-hop + 出力 IF）で到達（実機 100%）。
  ★**過剰解の防止**: RT02 の RA が停止のままか（`show ipv6 interface <if>`=`RAs are suppressed (all)`）
  を採点。RA を再有効化して autoconfig default で通す“直し”は ping が通っても**この監査＋静的既定
  監査の2つが落ちて降格**（実機実証: 過剰解=84/100）。
- **E2E 実機**: seed 41001（A:W_S / B:W_MP・client_static_default_missing@B）=
  broken **81** → fix → **100**。過剰解（RA 再有効化）= **84**（降格実証）。
- 残: automatic↔named 要件反転（1 LAN 化が要る）/ --faults 2 実機 / P3 PD スパー（骨格 b）/
  P4 L5 異物系（rogue_ra・dad_conflict＝要 SWA 多アクセス）。

## 9. 全故障 実機効果スイープ（2026-08-27・出題前 QA）

故障 17 種すべてを実機で「効果あり（broken が意図どおり壊れる）」まで確認。方式=
代表 seed の full cycle（broken→fix→100）＋残りは healthy ラボへ live 注入して症状 probe。

- **full cycle（broken→fix→100）**: client_default_missing(40004:90→100) /
  link_address_missing(40033:90→100) / client_static_default_missing(41001:81→100・
  過剰解84) / server_attach_missing(40006:→100) / **a_not_suppressed+relay_missing(43001・
  --faults 2:63→100)** / **nd_prefix_wrong_len(45000:70→100・SLAAC 再形成の収束確認)**。
- **live 効果 probe（全て EFFECTIVE）**: o_flag_missing / dns_option_missing /
  relay_missing / relay_wrong_dest / pool_prefix_mismatch / server_named_wrong_pool /
  server_return_route_missing（アドレス OK・ping のみ片方向死）。
- **PoC 実証済み機構**（POC-V6ADDR）: ra_suppress / ra_lifetime_zero / nd_prefix_wrong_len /
  rdnss_missing（RDNSS 配布は 41001 基線で確認）。

### ★スイープで発見・是正した不具合（重要）
1. **m_flag_missing = no-op → 故障カタログから削除**。クライアントは explicit
   `ipv6 address dhcp`（M フラグ非依存）でアドレスを取るため、M フラグを外しても
   `Address State OPEN` のまま（実機実証）。IOS のクライアントは autoconfig からの
   stateful 起動をしない＝M フラグは機能トリガにならない。
2. **ipv6_enable_missing を W_MP 限定に縮小**。W_M/W_MA は `ipv6 address autoconfig default`
   が LL を生成するため `ipv6 enable` を外しても無症状（PoC 罠#1）。純 dhcp の W_MP のみ有効。
3. **a_not_suppressed の採点を収束安全化**。「クライアントに EUI-64 が無い」で採点すると、
   修正（no-autoconfig 追加）後も既存 SLAAC アドレスが valid lifetime 残留し誤 FAIL。
   → **GW 側の広告状態（RT02 `show running-config interface` に `no-autoconfig`）**で採点する形へ変更。
4. **server_named_wrong_pool** は実在プール（最初の DHCPv6 LAN）に named 固定し、
   **DHCPv6 LAN が 2 つある seed のみ**適用（1 つだと他 LAN が無く無症状のため）。

### 出題可否
- 17 故障＋ --faults 2＋5 世界（W_SO/W_M/W_MA/W_S/W_MP）が実機で健全。**P1/P2 範囲は出題可**。
- 出題時は新 seed。採点は max_attempts=8 settle_delay=15 を既定（DHCP/RA ラグ吸収）。

## 10. P3/P4 実装検討（2026-08-31）

P1/P2+QA で board(a)（2 LAN 点対点）は出題可。P3(PD)・P4(異物系)は**いずれも新しい
board（トポロジ変種）を要する**のが共通の主作業。現状 problem.yml の lab.links/
target_nodes と rendering は board(a) 固定なので、board を明示選択（`--board a|pd|rogue`・
将来は抽選軸）にする小infraが前提。以下、各々の設計・機構・採点・工数・リスク。

### P4: rogue_ra / dad_conflict（L5 異物系・BL-146 FHS への橋）

- **board(rogue)**: LAN-B を多アクセス化。RT02(GW)＋CLB(client)＋ROG(異物) を1セグメントに
  同居（CML はリンク点対点のみ→**switch ノードが要る**）。
- **★infra gap**: `gen_cml_lab.py` はデータ面の多アクセスを未サポート（`unmanaged_switch`
  は mgmt 網専用・データ nodes は SW*→managed L2(ioll2) のみ）。選択肢=
  (i) **unmanaged_switch をデータノードとして扱う小改修**（PoC は unmanaged_switch 直結で実証済・軽い・推奨）/
  (ii) managed L2(SW*)流用（重い・Vlan999 SVI bounce 罠 [[ccnp-iosvl2-mgmt-svi-bounce]] を持ち込む）。
- **故障（◎ 全て POC-V6ADDR で実証済）**:
  - `rogue_ra`: ROG が `router-preference High`＋偽 prefix/自身 default を広告。採点=client
    `show ipv6 routers` に **High の偽ルータが不在** ＋ 到達性回復。★**偽 GUA の残留は採点条件に
    しない**（shut で最終 RA lifetime0→default は数秒で消えるが GUA は valid lifetime 残留）。
    fix=ROG 中和（IF shut / `no ipv6` / `ra suppress all`）。
  - `dad_conflict`: ROG と CLB に同一手動 LL → victim `IPv6 is stalled ... [DUP]`
    （`%IPV6_ND-4-DUPLICATE`）。採点=CLB が [DUP] でなく正常アドレス保持。fix=一方の LL 変更
    or 手動 LL 除去で EUI-64 化。
- **裏話**: 恒久対策＝RA Guard / DHCPv6 Guard / IPv6 Source Guard ＝ **BL-146 FHS** へ接続
  （solution.md）。★本試験の最大失点源が Security（[[ccnp-status-next]]）＝**学習価値最大**。
- **工数**: board infra（unmanaged_switch データノード対応）半日 ＋ P4 本体 半日（機構は実証済）。
- **リスク: 低**。新規は framework の多アクセス対応のみ。

### P3: Prefix Delegation（W_PD・ENARSI PD トピック）

- **board(pd)**: LAN-B を PD スパーに。RT03(CPE=PD クライアント)＋HST(配下ホスト・SLAAC)。5 IOL。
- **機構（BL-034 PoC 済・ただし v6addr board では未検証）**:
  - Server(RT01): `ipv6 local pool DELEG 2001:DB8:D000::/40 48` ＋ `ipv6 dhcp pool POOL-PD`
    （`prefix-delegation pool DELEG`）＋ **named binding**（automatic は IA_PD 無応答）。
  - CPE(RT03): WAN `ipv6 dhcp client pd DELEG` ＋ LAN `ipv6 address DELEG 0:0:0:1::1/64` ＋ RA。
  - HST: `ipv6 address autoconfig default`。委任 /48 経路はサーバが自動 install。
- **★未解決（実装前に要 PoC・2 点）**:
  1. **リレー越しの IA_PD** が現 board（RT02 リレー）で通るか未検証（PoC は CPE を server 直結で実証）。
     通らないなら **CPE を RT01 直結**にする（board 設計を変える）。
  2. RT01 が LAN-A 用 **automatic** と PD 用 **named** を**同一 core IF 上で両立**できるか
     （1 IF に `ipv6 dhcp server` 文は1つ＝置換）。両立不可なら CPE を別 IF 直結／PD 専用サーバ IF に。
- **故障（◎/○）**: pd_automatic_trap（automatic のまま=PD 無応答）／pd_pool_missing／
  pd_hint_missing／pd_upstream_route_missing（委任先の先が無く戻り死）。
- **採点**: RT01 `show ipv6 dhcp binding` の **IA_PD** ／ RT03 `show ipv6 general-prefix`
  = `acquired via DHCP PD` ／ HST GUA が委任 /48 配下（regex）／ HST→RT01 Lo0 ping（自動経路の実効）。
- **工数**: PoC（board(pd) の PD 配線確定）半日 ＋ 実装 半日〜1日。
- **リスク: 中**。リレー越し PD・サーバ2方式両立の 2 点が未検証（PoC で潰す）。

### 推奨する順序

1. **P4 を先に**。Security（本試験最大の失点源）に直結し **BL-146 FHS の橋**になる。機構は
   全て実証済で**低リスク**。唯一の新規作業＝`gen_cml_lab.py` の多アクセス（unmanaged_switch
   データノード）対応で、これは他問（将来の L2/FHS 系）にも再利用が効く。
2. **P3 は PoC を挟んでから**。ENARSI の PD は独立した価値があるが、Security 優先度が上。
   着手時はまず §10 の未解決2点を POC-V6ADDR 拡張で確定させる。

（automatic↔named 要件反転は 1 LAN board が要るため、board infra 整備時に相乗りで対応可。）

## 11. P4 実装結果（2026-08-31）

- ★**多アクセス board インフラを実装**（`gen_cml_lab.py`）: `lab.switches: [SWB]` で
  **unmanaged_switch をデータノード**として宣言でき、`lab.links` の端点に名前で参照可能
  （target_nodes に含めない＝mgmt/day0/採点の対象外）。将来の L2/FHS 問にも再利用可。
- ★**board=rogue 実装**（`gen_v6addr_ts.py --board rogue`）: 5 IOL＋SWB。
  RT01(サーバ)─RT02(GW/リレー)─[SWB]─CLB(client)/ROG(未認可機)。LAN-A=通常世界(対比)・
  LAN-B=W_SO 固定。故障は ROG/CLB のみ（RT01/RT02/CLA は健全）。
- **rogue_ra = ✅ 完成・実機 E2E（broken 72 → fix 100）**。ROG が `router-preference High`＋
  偽 /64 を広告 → CLB が偽 GUA を追加形成＋偽デフォルトで社外不達。採点=CLB `show ipv6 routers`
  に `Preference=High` 不在（not_regex）＋ 実疎通。fix=ROG の IF `shutdown`（最終 RA lifetime0 で
  偽デフォルトが数秒で消え到達回復）。裏話で RA Guard=BL-146 へ接続。
- **dad_conflict = ⏸ 保留（実機で非決定と判明）**。ROG が静的 `<lanB>::99` を先取り＋CLB は
  手動 LL `FE80::99`＋autoconfig で SLAAC 派生 GUA を `::99` にして重複させる設計だが、
  **DAD は「後から DAD した側が [DUP] になる」boot レース**で、非管理スイッチの起動時
  フォワーディング・ブラックアウトも絡み、**CLB を確実に victim にできない**
  （実測: この seed は逆に **ROG が [DUP]**・CLB は `::99` 健全で ping 100%）。
  → 既定 pick から除外（`L5_FAULTS=["rogue_ra"]`・`--fault dad_conflict` の強制生成のみ残置）。
  決定化の将来案: (i) RT02(GW=早期に安定)の LL/GUA へ CLB を衝突させる（RT02 が defender・
  ただし依然 boot 順依存）(ii) 管理 L2 スイッチで DAD を確実化してから victim を固定する策を検討。
- **出題可否**: **board=rogue rogue_ra は出題可**（BL-146 の橋・Security 補強）。dad_conflict は保留。

## 12. P3 実装結果（2026-08-31）

- ★**board=pd 実装**（`gen_v6addr_ts.py --board pd`）: 5 IOL。相談事項2点を**トポロジで回避**=
  CPE(RT03)を **RT01 に直結**（direct PD＝BL-034 PoC で実証済）＋ PD の named binding を
  RT01 の**別 IF(i1)**に置く（LAN-A 用 automatic は i0＝両立）。
  ```
  RT01(サーバ+委任) ─i0─ RT02(GW/リレー) ─ CLA(LAN-A=W_SO)
             └─i1─(直結)─ RT03(CPE) ─ HST(配下・SLAAC)
  ```
- **PD 機構＝実機で全て成立（相談事項2点とも解決）**:
  - RT01: `ipv6 local pool DELEG 2001:DB8:{h}000::/40 48` ＋ `ipv6 dhcp pool POOL-PD`
    (`prefix-delegation pool DELEG`) ＋ i1 に **`ipv6 dhcp server POOL-PD`（named）**。
    i0 は LAN-A 用 **bare `ipv6 dhcp server`（automatic）**＝別 IF なので両立（実機確認）。
  - RT03(CPE): WAN `ipv6 dhcp client pd DELEG`＋静的 WAN /64、LAN `ipv6 address DELEG 0:0:0:1::1/64`、
    上流 `ipv6 route ::/0`。委任 /48 = `2001:DB8:{h}000::/48`、配下 LAN = `...:1::/64`。
  - HST: `ipv6 address autoconfig default` → 委任 /64 から EUI-64 GUA。
  - ★**委任経路はサーバが自動 install**（`S 2001:DB8:{h}000::/48 via <RT03 LL>`・実機確認）→
    戻り経路を書かずに HST→RT01 Lo0 が **ping 100%**。
  - ★収束ラグ: fix 後の binding/general-prefix/自動経路は PD SOLICIT 後 ~30-40s で現れる
    （採点 max_attempts=8 settle_delay=15 で吸収）。
- **故障 4 種＝全て実機で効果確認**:
  - `pd_automatic_trap`（i1 を automatic に）= **full cycle broken→fix 100**（binding/general-prefix
    空→named 化で委任成立）。★automatic は IA_PD 無応答（BL-034 PoC の再確認）。
  - `pd_pool_missing`/`pd_client_missing`/`pd_general_prefix_missing` = live probe で全て EFFECTIVE
    （委任 /48 不達 / 委任要求なし / 配下 LAN プレフィックス不供給）。
- 採点: RT01 `show ipv6 dhcp binding`(IA_PD+/48) / RT03 `show ipv6 general-prefix`(acquired via
  DHCP PD+/48) / HST `show ipv6 interface brief`(委任 /64 の EUI-64) / HST→Lo0 ping ＋ LAN-A(W_SO)。
- **出題可否**: **board=pd 出題可**（4 故障・難4-5）。出題時は新 seed。
- 残（P1-P4 完了後）: automatic↔named 要件反転（board infra で 1 LAN 化）/ dad_conflict 決定化 /
  PD の派生故障（pd_upstream_route_missing 等）。

## 13. 次段の検討（2026-09-03・ユーザ要望= L2 FHS ラボ → 構築版）

### 13.1 `--board fhs`（BL-146 ラボ側・TS 形）
- PoC 全項目成立: [poc/fhs/README.md](../../poc/fhs/README.md)（ioll2-xe 17.15.1・RA Guard/DHCPv6 Guard/device-tracking）。
- 盤面= board=rogue の SWB を **ioll2 管理スイッチ(target_nodes 入り・role=switch→family iol の switch profile=ioll2-xe・mgmt Et3/3)**に置換。
  8 ノード(RT01/RT02/CLA/CLB/ROG/SWB+MGMTSW+EXTC)。VLAN10 アクセス×3(Et0/0=RT02・Et0/1=CLB・Et0/2=ROG)。
- 採点経路= `access: telnet`(ioll2 は SSH 不可・collect_telnet.py)。IOL ルータは baseline が `transport input ssh` のみ
  → 各ルータ initial 末尾に `line vty 0 4 / transport input ssh telnet` を追記して telnet 収集に乗せる。
- 故障候補(1 つ抽選・ROG は「触れない他部署機器」制約で解法を SWB 側に強制):
  | fault | 仕掛け | 症状 | 採点(SWB show + CLB 挙動) |
  |---|---|---|---|
  | fhs_absent | ポリシー無し | CLB 既定GW=ROG・偽GUA・DNS evil | `show ipv6 nd raguard policy` 存在+Et0/2 に attach / CLB routers に High 不在 |
  | fhs_vlan_overblock | HOST を vlan configuration に attach・GW ポート role なし | CLB LL のみ(GW RA も遮断) | Et0/0 に role router(port)or trusted-port / CLB routers に RT02 あり |
  | fhs_role_swapped | ROUTER を Et0/2・HOST を Et0/0 | ROG 通過・GW 遮断 | 上記の逆転是正 |
  | fhs_dhcpguard_wrong_port | dhcp guard role client を Et0/0(GW) | RA は正常だが DNS/ドメイン取れず(O flag) | Et0/0 role server / CLB dhcp interface に RT02 |
  | fhs_pref_cap_low | `router-preference maximum low` を VLAN attach | 正規(Medium)も落ちる | maximum medium 以上 or role 方式 |
  | fhs_prefix_match_wrong | `match ra prefix-list` が正規 /64 を deny | 正規 RA 落ち | PL 是正 |
- 過剰解監査= ROG 無改変(`show running-config interface Et0/0` に `ipv6 nd router-preference High` が残る＝ROG 側で直していない)＋
  SWB のポートが up(shut で解決を封じる)。
- 曖昧要件の芽= 「不正ルータの排除」を **ROG 特定なしの汎用対策**として要求(端末ポート全部に host role) vs 「ROG のポートだけ」。
  設問文で「今後同種の機器が別ポートに繋がれても防げること」と言えば前者が一意。

### 13.2 構築版（BL-153・要件書駆動）
- 空の RT01/RT02/SWB(＋端末は既設)を要件書どおりに組む。要件抽選軸= 既存 5 世界(W_SO/W_M/W_MA/W_S/W_MP)の
  1 つ×DNS 供給方法(DHCPv6 stateless/RDNSS)×既定GW 供給方法(RA/静的 LL next-hop)×PD 有無×FHS 方針(role 方式/pref 上限方式)。
- 採点は既存 `lan_checks`(挙動)＋rogue_grading(High 不在+到達性)＋pd_grading を**そのまま流用**(TS と同じ最終状態を要求するため)。
- 「顔が変わる」= 同じ盤面で要件書が違えば正解 config が全部違う(TS の反転世界を出題側に回す)。

### 13.3 `--board fhs` 実装結果（2026-09-03・全6故障 実機E2E）
seed 90001（LAN-A=W_MP・VLAN 30・ポリシー名 HOSTS/CLIENTS）を 1 回 provision し、SWB の FHS 設定を
コンソールで差し替えながら 6 故障を順に検証（broken 採点→模範 fix→CLB IF bounce→採点）。

| fault | broken | fixed | 備考 |
|---|---|---|---|
| fhs_vlan_overblock | 61 | 100 | 初回 provision。RA guard 有効チェックの regex は target 名「vlan 30」の空白で `\S+` が外れ→ `^.+\s(PORT|VLAN)` に是正 |
| fhs_absent | 62 | 100 | DNS も evil（DHCPv6 Guard なし） |
| fhs_role_swapped | 68 | 100 | **DNS は正規**（DHCP guard は正しい）→ 症状文から「DNS も想定外」を削除 |
| fhs_dhcpguard_wrong_port | 93 | 100 | DNS/ドメインのみ FAIL（症状文どおり） |
| fhs_pref_cap_low | 66 | 100 | 修正= `router-preference maximum medium` |
| fhs_prefix_match_wrong | 66 | 100 | ★fix 初版が空振り= `no ipv6 prefix-list X seq 10`（prefix 省略）は不受理・同 seq への別 prefix も拒否→ **完全形で削除**して再投入 |

- 実装メモ: (1) ROG は短寿命 RA（`ra interval 30`/`ra lifetime 120`/`nd prefix ... 180 90`）＝ガード適用後に端末の偽 default/偽 GUA が数分で消える。
  (2) DHCPv6 の構成情報は端末が 24h キャッシュ → task で「CLB の IF shutdown/no shutdown は許可」を明記（アドレス設定変更は不可）。
  (3) `show interfaces status` の日本語 description は telnet/console で化ける → SWB の description は ASCII。
  (4) `show running-config` は device-role host / security-level guard の既定値を出さない → 採点は `show device-tracking policies`。
  (5) lab_up.yml に `bringup_nodes`（任意）を追加＝SSH 不可の SWB を SSH bringup から除外（ioll2 のスイッチポートは day0 で up・CVAC shutdown を受けない）。
  (6) SWB への模範解は `solution/fix_console.json`（fix_console.py 形式）。fix.json(ios_config 形式)は参考のみ。
- **出題可**（難4-5）。出題時は新 seed。検証 seed 90001 は掃除済。

### 13.4 構築版 `gen_v6addr_build.py`（BL-153）実装結果（2026-09-04）
- ID= GEN-V6BUILD-<seed>。盤面= board=fhs と同一(8 ノード)。初期状態は**土台のみ**(RT01: Lo0/コア IF/LAN 宛戻り経路・RT02: 全 IF アドレス(W_MP の LAN は FE80::1 LL も)+Lo0 宛経路・端末: IF up のみ・SWB: VLAN+アクセス 3 ポート・ROG: 不正 RA+DHCPv6 稼働)。
- 要件書= LAN ごとの `lan_spec`(世界別の端末/GW/サーバ要件・コマンドは書かない)+DHCPv6 サーバ集約(コア側 1 IF のみ=automatic を暗示)+FHS 方式(role/prefix)+制約(ROG/ポート/土台不変・端末は最小設定・bounce 可)。
- 採点= TS の `lan_checks` 両 LAN+High 不在/Medium あり+偽 GUA 無し+両ガード有効+**方式指紋**(counters の RA guard drop 理由。ROG が 30 秒周期で RA を出すため常時計上)+Et0/2 connected+ROG 無改変。
  DHCPv6 REP の drop 指紋は不採用(端末が問い合わせた時だけ計上・W_S では O=0 で発生しない)。
- E2E: 70001(A=W_MA/B=W_S/role) blank 15→模範 100 / 70081(A=W_MP/B=W_SO/prefix) blank 12→93→100。
  ★93 の原因= fix_console.json の投入順(RT01→…→CLB(bounce)→SWB)で、ガード前の bounce が ROG の DHCPv6 情報(evil DNS)を再学習し 24h キャッシュ。→ dict 順を SWB 先頭に是正(解答者にも同じ罠が起きうる=task の「構築完了後に bounce してよい」で示唆)。
- 定常状態は 1 試行で 100(bounce 20 秒後には正規状態)。genres.yml: first-hop-security/ra-guard/dhcpv6-guard→security・GEN-V6BUILD family=security。
- 出題可(難4-5・出題時新 seed)。検証 seed 70001/70081 は掃除済。
