# ACL 単独読解 紙面ファミリ（shape=`acl`）— 設計メモ (BL-106)

作成: 2026-08-09 / 発端: ユーザ指示（BL-100 の優先題材 ③「ACL 単独読解」の具体化）

## 出題意図（ユーザ指示の整理）

> - **TS 系**= 既設の ACL だと希望のアドレスレンジが選ばれない
> - **構築系**= このレンジを指定するにはどのコマンド（ACL）を選べばよいか
> - それぞれ **AAA のときのように 2 択（複数選択）でも**出題できるように
> - シナリオは **フィルタリング / uRPF / ルートフィルタリング / CoPP** などを使う
> - ※ 結局のところは ACL 問題だが、**問題の体裁とノイズ**として上記シナリオで
>   **ACL にロールを着せる**イメージ

→ `gen_paper_pbr` / `gen_paper_urpf`（BL-081/084）で確立した**被覆エンジン方式**に載せる。
ロールは「permit/deny の帰結写像」として扱い、レバーは **ACL の意味評価 1 本**に保つ。

---

## 0. 既存資産との棲み分け（重複回避）

| 既存 | 何を扱っているか | 新 shape との関係 |
|---|---|---|
| `gen_paper_pbr.py`（shape=pbr） | 第3オクテット **8bit 限定**のキューブ被覆・要件世界 single/strict・ACL は PBR の match 道具 | **被覆エンジンの原型**。32bit へ一般化したものが新 shape の構築系。**PBR ロールは pbr に譲る**（新 shape の衣装から除外） |
| `gen_paper_urpf.py`（shape=urpf） | uRPF の strict/loose・例外 ACL・`acl_num_mismatch` | uRPF は**衣装として軽く使うだけ**。モード論（strict/loose の選択）には踏み込まない |
| `gen_list_dojo.py --dojo acl`（GEN-DOJO-ACL） | **ラボ側**= 学習者が実機で ACL を書き `acl_vectors` で採点 | 紙面は「読む・選ぶ」で棲み分け。`ACL_VECTORS`（ベクタ battery）と `acl_cli()` は紙面へ流用可 |
| `topologies/acl_model.py` | `show access-lists` パーサ＋first-match 評価器（非連続 WC・established・ポート名・ICMP タイプ対応） | **中核**。要拡張（§7） |
| ラボ資産 | ENCOR-ACL-EXTENDED-01 / ACL-NAMED-01 / COPP-01〜03 / VACL-01,02 / ENCOR-DHCP-01(ACL) | 紙面の題材源 |

---

## 1. 骨格

レバーは **「ACL の意味評価」1 本**。ロールは permit/deny の**帰結写像**であって別レバーではない
（この整理により「1 shape = 1 レバー」原則と要件世界の直交性を守る）。

```
盤面 = ACL本体(中身・順序・適用面) × ロール(衣装) × 要件世界 × 出題形
```

---

## 2. ★ロール別 permit/deny 意味論表 — 本ファミリ最大の教育核

**同じ文面の ACL でも、着せる衣装によって permit の意味がまるで違う。**

| ロール | 適用コマンド | permit の意味 | deny の意味 | 暗黙 deny の帰結 | 固有の罠 |
|---|---|---|---|---|---|
| **filter** | `ip access-group N in\|out` | 転送する | 破棄する | 全破棄 | ★**out はルータ自身が生成したパケットに効かない**（ping/routing update が抜ける）・in は自分宛にも効く |
| **urpf** | `ip verify unicast source reachable-via rx N` | **RPF 失敗でも通す（免除）** | 例外にしない（RPF 判定に従う） | 例外なし | permit が「許可」でなく「免除」。BL-084 で実装済 |
| **routefilter** | `distribute-list N in` / `distribute-list route-map M in` | 経路を受理／広告する | 経路を捨てる | 全経路遮断 | ★★**参照の経路で意味論が入れ替わる**（実測 poc/acl §4-4）。**直接指定**= src=広告元の隣接ルータ／dst=広告されたネットワーク（長さは見ない）。**route-map 経由**= src=ネットワーク／dst=サブネット・マスク（＝教科書の形。「広告元」の概念は無く、**長さで絞れる**）。／**名前付き拡張 ACL は「定義→参照」の順だと拒否**されるが「参照→定義」なら受理（順序依存）／→ **長さを絞る手段は prefix-list と route-map 経由の2つ**あり、「どちらを禁じるか」で正解が反転する盤面を作れる |
| **redist filter** | `route-map ... match ip address N` | 再配送する | しない | — | route-map の permit/deny と**二重の否定** |
| **copp** | `class-map match access-group N` | **そのクラスに分類**（→ police/drop） | **クラスに入らない → 次の class、最後は class-default** | — | ★**deny は「通す」ではない**・class-default の道連れ（QoS シリーズの教訓の紙面版） |
| **nat** | `ip nat inside source list N ...` | 変換する | **変換しない（素通り）** | 変換なし | VPN 対象を deny で除外する定番（BL-064 実測と直結） |
| **crypto** | `crypto map ... match address N` | **暗号化する** | 平文で出す | — | NAT との適用順（BL-063/064 実測） |
| **vty** | `access-class N in\|out` | 接続を受理 | 拒否 | 全拒否 | 標準 ACL・in=接続元／out=接続先 |
| **snmp/ntp** | `snmp-server community X RO N` | 問い合わせに応答 | 無視 | — | 軽い衣装（ノイズ用の併載 ACL に最適） |

★**この表そのものを出題形にできる**= 同一の ACL 文面を 2 ロールで使い回し、「片方では意図どおり・
片方では逆に働く」盤面（BL-096 の「エコ形＝共用形」と同じ発想。実装実績あり）。

---

## 3. ACL 本体の論点カタログ

### A. アドレス／ワイルドカード（構築系の本丸）
1. 連続レンジの**最小キューブ**（`172.16.8.0 0.0.7.255` = 8〜15）
2. **非連続ワイルドカード**（奇数サブネットのみ等）※acl_model 対応済
3. **境界 off-by-one**（キューブ直上／直下）※pbr で実績
4. ★**ビット境界に載らないレンジ**（10.1.4.0〜10.1.10.255）→ 1 行では書けない →
   「複数行」か「過剰被覆＋deny 先行」か。要件世界で正解が反転
5. ワイルドカード ⇄ サブネットマスク取り違え。★**実測（§8 P10）**= エラーなく受理されるうえ
   **don't care 側のビットがアドレスから落とされて別物になる**
   （`permit 10.0.0.0 255.0.0.0` → `permit 0.0.0.0, wildcard bits 255.0.0.0`
   ＝「第2〜4オクテットが 0.0.0 の全アドレス」）。錯乱肢として一級品
6. 標準 ACL の `host` / 裸 IP / `any` の表示形
7. 過剰被覆の**巻き添え**（要件は満たすが別セグメントも許可／遮断する）
8. 逆問題「この 1 行が許可する範囲はどれか」

### B. 順序・シーケンス
9. **shadowing**（先行の広い permit が後続 deny を無効化）
10. ~~★番号付き ACL への追記は末尾にしか付かない ⇄ named は seq 指定で挿入可~~
    → ★**実測で否定（§8 P6）**。`ip access-list extended 150` に入れば
    **番号付きでも seq 挿入できる**（エラーなく 10 と 20 の間に入った）。
    差は「番号付き/名前付き」ではなく**編集モード**（`access-list ...` のグローバル形式は
    末尾追記のみ／`ip access-list ...` の named モードなら挿入可）。
    → 要件世界 `no_delete` は成立するが、**正解を named 側に寄せる仕掛けには使えない**
11. `no <seq>` による 1 行削除／`ip access-list resequence`（隙間切れ）
12. **同一番号での再定義は追記であって置換ではない**（`no access-list 101` しないと消えない）
13. 暗黙 deny（**ログを出さない**）

### C. プロトコル／ポート／状態
14. `established`（TCP のみ・ACK/RST）と戻り通信
15. ポート演算子 eq/neq/gt/lt/range（`neq` の罠）
16. ★**送信元ポートと宛先ポートの位置**（`src [op port] dst [op port]`）の取り違え
17. ICMP タイプ（`echo` vs `echo-reply`）＝ ping を片方向だけ許す
18. `ip` 指定時はポートが書けない／`log` の副作用

### D. 適用面・方向
19. in/out 取り違え（pbr の `acl_dir` の一般化）
20. ~~★outbound は自機生成トラフィックに効かない~~
    → ★**実測で否定・論点として削除（§8 P4）**。IOL-XE 17.15 では
    **自機生成の ping も outbound ACL に当たって落ちる**（5発ごとにカウンタが
    0→5→10→15 と正確に増え、既定送信元・Lo0 送信元・通過の3ケースとも 0%）。
    一般に流布する「router 生成トラフィックは outbound ACL を素通りする」は
    **この機種では成り立たない**ので、この挙動に依存した設問は作れない
21. **inbound は転送前評価**＝自分宛の管理接続も落ちる
22. 適用先 IF の取り違え（隣接 IF に当ててしまう）

### E. time-based
23. `time-range` absolute / periodic（weekdays / weekend）
24. **非アクティブな ACE は「存在しない」扱い**→ 次の行に落ちる（結果が反転）
25. クロック／NTP 依存（`show time-range` と現在時刻を提示）

### F. 未定義・空・参照ミス
26. ★**未定義 ACL の参照はロールごとに帰結が違う** → **実測で確定（§8 P1・対照実験つき）**:
    interface / distribute-list / uRPF 例外 = **全許可**（uRPF は RPF 失敗が
    `suppressed verification drops` に計上され免除される）／
    CoPP の `match access-group` / NAT の `source list` = **どれにも一致しない**。
    → リポの「未定義参照」類型に **ACL 版**を追加（PL 未定義=全許可／route-map 未定義=全拒否／
    AAA 未定義=default へ／**ACL 未定義=ロール依存**）
27. ~~named ACL を作ったが**中身が空**＝暗黙 deny のみ＝全断~~
    → ★**実測で否定（§8 P12/P13）**。空の ACL は interface でも distribute-list でも
    **全許可**（未定義と同じ）。「空だから全部落ちる」は誤り
28. 参照番号 ≠ 定義番号（BL-084 `acl_num_mismatch` の一般化・ノイズ ACL 併載と相性◎）
29. ★**ログは `log` を書いた行でしか出ない**（§8 P9）。カウンタは進むのにログが無い＝
    「別の行で落ちた」という消去推論が成立する。ニモニックは TCP/UDP=`IPACCESSLOGP`・
    ICMP=`IPACCESSLOGDP`（ICMP は `(8/0)` の type/code 付き）

---

## 4. 出題形（既存語彙＋新形 3 つ）

| 形 | 内容 | 位置づけ |
|---|---|---|
| **select** | 「このレンジだけを指定する ACL 行はどれか」＝被覆エンジン | ★**構築系**（ユーザ指定） |
| **read** | 「次のパケットのうち転送されるものはどれか」（ベクタ表を提示） | TS 系の基礎 |
| **cause** | 「なぜこの通信だけ落ちるか」（機構を問う） | ★**TS 系**（ユーザ指定） |
| **fix** | 最小の是正コマンド（CLI 提示） | TS 系 |
| **patch** | 既存 ACL に**1 行挿入**。**挿入位置（seq）が本題** | 要件世界と直結 |
| ★**counter**（新） | 「この通信を 1 回行ったとき、カウンタが増えるのはどの行か」 | first-match の理解が直撃。`(N matches)` は実機忠実な証拠 |
| ★**logread**（新） | `%SEC-6-IPACCESSLOGP: list 101 denied tcp 10.1.1.5(1234) -> 10.2.2.2(22), 1 packet` から ACL の中身・どの行で落ちたかを逆算 | AAA の dbgread と同型。★**`log` の無い行で落ちるとログが出ない**消去推論が効く |
| **evidence** | 「次に取得すべき出力はどれか」（`show ip access-lists` / `show ip interface` / `show time-range` / debug の切り分け） | AAA で確立済 |
| **multi（2 つ選べ）** | 「読み取れる事実を 2 つ」「要件を満たす行の組合せ」「落ちるパケットを 2 つ」 | ★**器は BL-103⑥ で実装済み**（`gen_pack.py` の複数記号対応・採点系対応済）＝**追加実装なしで使える** |

記述式（bgpdbg 方式）は将来枠。

---

## 5. 要件世界（正解を反転させる軸）

| 世界 | 内容 | 反転の効き方 |
|---|---|---|
| `one_line` | 1 行で書くこと | 過剰被覆キューブが正解に |
| `exact` | 対象と完全一致（過剰被覆禁止） | 複数行／deny 先行が正解に |
| `no_delete` | 既存行の削除禁止（挿入のみ） | named + seq 挿入が正解／番号付き ACL 解が失格 |
| `keep_counters` | 既存の統計を消すな | ACL 再作成が失格（★実機忠実） |
| `no_host_enum` | ホスト個別列挙禁止 | 集約強制 |
| `no_touch_role` | route-map / class-map / uRPF / IF 設定は触るな | **ACL だけで解け** |
| `return_traffic` | 戻り通信を明示許可せよ | `established` か逆向き明示かの選択 |
| `must_log` | 落としたものを記録すること | `log` 付き明示 deny が必須（暗黙 deny では不可） |
| `time_window` | 平日日中のみ | time-range 解へ |
| `mgmt_survives` | 管理接続を切るな | CoPP／vty ロールで効く |
| `prefixlen_exact` | プレフィックス長を厳密に区別 | ★routefilter で「**ACL では不可能・prefix-list が必要**」が正解に |

---

## 6. バリエーション案

1. **ロール反転形** — 同一 ACL を 2 ロールで共用し、片方だけ意図と逆に働く（uRPF 例外 × 入力フィルタ）
2. **多段落ち** — 上流でも下流でも落ちうる盤面で、**カウンタからどちらで落ちたかを特定**
3. **並べ替えだけで直る形** — `no 20` ＋ `15 permit ...`（patch の純粋形）
4. **ノイズ ACL 併載** — SNMP 用 ACL 10・フィルタ 101・uRPF 例外 20 を併存させ、
   **どれが対象かの特定自体を仕事にする**（BL-088 不親切化と整合）
5. **prefix-list との対比** — 同じ要件を ACL で書けるか／`ge le` が要るか
6. **標準 ACL の限界** — routefilter で /24 と /28 を区別できない
7. **拡張 ACL の distribute-list 特殊解釈** — src=ネットワーク・dst=マスク（単独で 1 問成立する濃さ）
8. **負の要件の紙面化** — 「A は通し B は通すな」で、A だけ見ると複数正解・B で一意化
9. **時計を動かす** — 同じ ACL・同じパケットで平日 10:00 と土曜 10:00 で結果が反転
10. **ICMP 片方向** — `permit icmp any any echo` だけで ping が通らない理由
11. **自機生成トラフィック** — out ACL で全 deny なのにルータからの ping は通る
12. **ACL 更新中の穴** — `no access-list 101` 直後の無防備状態（運用手順＝AAA の patch 形と同型）
13. **CoPP の道連れ** — class-default の police に管理トラフィックが落ちる
14. **NAT × crypto の deny** — VPN 対象を NAT から除外し損ねる（実測知見あり）
15. **IPv6 版への発展** — 器を共用し `ipv6 access-list` / `ipv6 traffic-filter` へ（BL-100 ⑤。
    別 shape 推奨だが**同じエンジンに載る**）

---

## 7. 実装で要るもの

| 項目 | 内容 |
|---|---|
| ★**32bit 被覆エンジン** | **実装完了= [topologies/acl_cover.py](../../topologies/acl_cover.py)（selftest 420/420）**。当初案の「区間分割」は**誤り**だった（非連続ワイルドカードがあるためアドレス集合は区間にならない）→ **32bit 三値キューブの代数**（交差・差）＋**直積領域の矩形差分解**で有限・厳密に閉じさせた。first-match は「i 番目の実効領域 = 領域_i − ∪(領域_1..i-1)」で畳む |
| 意味シグネチャ | `acl_equivalent()` = 相互差が空。等価な最終状態を畳む（BL-084 方式）。「deny 先行＋広い permit」＝「3行の列挙」の等価を機械証明済み |
| 要件判定 | `permits_exactly()`（要件世界 `exact`）／`covers()`（`one_line`）／`size_ipv4()`（過剰被覆の比較）を用意 |
| 検証 | キューブ差分解を 64K 部分空間で**全数え上げと突合**（200 ペア）＋ **`acl_model.evaluate()` とランダム 2100 ベクタで不一致 0**（同じ ACL を別実装で評価して一致）。★P10 の実機挙動（`10.0.0.0 255.0.0.0` → `0.0.0.0, wildcard bits 255.0.0.0`）と **`Cube` の正規化（`value &= care`）が一致**することも確認 |
| `acl_model.py` **拡張（追加のみ・未着手）** | time-range 対応・`log` の識別（現在は捨てている）・**CLI 文面からの直接パース**（現状は `show` 出力パーサのみ）。★既存 `grade.py`（`acl_vectors:`）依存を壊さないこと |
| ロール意味論の写像層（未着手） | §2 の表を実装に落とす。permit の帰結がロールごとに違う＋**未定義/空 ACL の帰結もロールごとに違う**（§8 P1）ので、ロールは「permit 集合 → 症状」の関数として持つ |
| ベクタ自動生成（未着手） | 境界値（各 ACE の base / base±1 / ワイルドカード境界 / 対象レンジ端）を機械生成して read 形の選択肢に |
| 複数選択 | **追加実装不要**（BL-103⑥ 済） |

---

## 8. 実測 PoC（`poc/acl/`）— **★P0 完了（2026-08-10）**

実測表= [poc/acl/README.md](../../poc/acl/README.md)・生ログ= `poc/acl/results-raw.md`・
駆動= `poc/acl/sweep.py`（CML ラボ **POC-ACL**・IOL-XE 17.15 × 3台・コンソール直駆動・保持）。

| # | 検証項目 | 結果 |
|---|---|---|
| P1 | 未定義 ACL 参照の帰結（ロール別） | ✅ **ロールで割れた**。interface / distribute-list / uRPF = 全許可／CoPP / NAT = 不一致（対照実験つき） |
| P2 | distribute-list × 拡張 ACL | ✅ **定説を否定**。src=広告元ルータ／dst=広告された網／名前付き拡張は使用不可（5 パスで確定） |
| P3 | 標準 ACL とプレフィックス長 | ✅ /24 と /28 が同時に消える＝区別できない |
| P4 | outbound ACL と自機生成 | ✅ **効く**（論点 20 を削除） |
| P5 | seq 挿入・resequence・カウンタ | ✅ 挿入も resequence も**カウンタ保持**／作り直しで消滅 |
| P6 | 番号付き ACL の編集規則 | ✅ **named モードなら番号付きでも seq 挿入可**（論点 10 を訂正） |
| P7 | time-range periodic | ✅ 平日内 0%／時間外・土曜 100%。`show` に `(active)`/`(inactive)` が出る |
| P8 | CoPP の deny ACE | ✅ **class-default に計上** |
| P9 | ログ書式 | ✅ TCP=`IPACCESSLOGP`／ICMP=`IPACCESSLOGDP`（`(8/0)` 付き）。**`log` 無しの行はログを出さない** |
| P10 | WC ⇄ サブネットマスク | ✅ 受理され**アドレスが正規化されて別物になる** |
| P11 | `show` 表示書式 | ✅ remark は出ない／22 は数字・80 は `www`／numbered も running-config は named 形式 |
| P12/P13 | 空 ACL | ✅ interface・distribute-list とも**全許可**（論点 27 を訂正） |

### ★測定手法の失敗（次回もここで転ぶ・詳細は poc/acl/README.md 冒頭）

1. **`dev.configure([1行])` を行ごとに呼ぶと config の階層が壊れ**、サブモードのコマンドが
   グローバル config で実行されて `% Invalid input` になる。額面どおり読むと
   **「拡張 ACL は distribute-list に使えない」という偽の結論**が出る（実際に出しかけた）。
2. `show ip route` の**固定長ブロックは経路行にプレフィックス長が付かない**（見出し行から採る）。
3. 「1台を見て全台 skip」する冪等判定は、中断した前回実行の後で**誤って全台 skip** する。
4. 前回の残骸 ACL が seq 衝突（`% Duplicate sequence number`）を起こす。
5. time-range の測定は**時計を戻す**（戻し忘れて以後の syslog が未来日付になった）。

※ `show ip access-lists` の表示形式（標準の `A, wildcard bits W`・ポート名表示）は
**BL-014 で実測確立済み**（acl_model のパーサに反映済み）。今回 P11 で再確認した。

### 参考: 既存の実測知見（流用可）
- OSPF の `distribute-list ... in` は**内部ルータでは RIB のみ**（LSDB に Type-3 は残る）が、
  **ABR に掛けると Type-3 origination 自体が止まる**（poc/ospfv3-pl §E2・OSPFv3 で実測）。
  → routefilter ロールで「distribute-list は LSA に効かない」の例外として使える。**v2 での再確認は要**。

---

## 9. 段階案

| 段階 | 内容 |
|---|---|
| ~~**P0**~~ | ✅ **完了(2026-08-10)**= `poc/acl/` で P1〜P14 実測（§8）。設計メモの論点 5/10/20/26/27 と §2 routefilter を実測で訂正 |
| ~~**P1a**~~ | ✅ **完了(2026-08-10)・出題可**= `gen_paper_mcq.py --shape acl`（mixed 合流済）。素材= [gen_paper_acl.py](../../topologies/gen_paper_acl.py)・エンジン= [acl_cover.py](../../topologies/acl_cover.py)。故障種10（filter 5 / routefilter 5）× 要件世界 3+3 × 形3種（select / read / cause）。検証= selftest（select 一意性 **900/900**・read 観測 **252/252**・cause 一意性 **120/120**・実測との整合 **8/8**）＋E2E30問（10種すべて・形3種・選択肢数と複数選択の個数が一致・NG 0）＋決定性（PYTHONHASHSEED 1 vs 999 で acl 12問・mixed 25問とも全文一致）＋既存10 shape 回帰OK |
| ~~**P1b**~~ | ✅ **完了(2026-08-10)**= 出題形が 3→**6種**に。**counter**=「この1パケットでカウンタが増えるのはどの行か」(first-match が直撃・後続の一致行は増えないのが罠)／**patch**=「既存行を変更せず1行だけ追加」で**★同じ1行をどこに入れるか**を競わせる(seq 5/15/25＋`access-list` グローバル形式=**必ず末尾に付く**という実測 §6 を錯乱肢に)／**fix**= routefilter の是正手段5候補を実測の意味論で判定(標準=長さも広告元も見ない／名前付き拡張=指定ごと拒否／拡張 src に網=何にも一致しない／拡張 src=広告元なら隣接で切れる／prefix-list だけが長さを区別できる)。要件世界が正解を反転= `prefixlen_exact`→**prefix-list のみ**／`by_neighbor`→**拡張ACLのみ**。検証= selftest **440/440**(counter/patch/fix)＋counter 先頭一致 40/40＋E2E40問(6形すべて出現・NG0)＋決定性(acl 16問・mixed 30問)＋全11shape回帰OK |
| ~~**P1c**~~ | ✅ **完了(2026-08-10)**= 出題形 **8種**・ロール **6種**・故障種 **14**。
**evidence**=「次に取得すべき出力はどれか」（★成立の根拠は実測で確定した**区別不能クラス**=
未定義／空／名前付き拡張はいずれも「全部素通り」に化ける。`show ip access-lists` だけが
**3通りに割れ**、`show running-config`・`show ip protocols` は**2通りまで**＝惜しい肢になり
消去法が効かない）／**logread**= ログから読み取る**2つ選べ**（★`log` の無い行で落ちた通信は
**カウンタは進むのに記録に出ない**という消去推論が核心）／ロール拡張= **copp**（deny は
class-default 行き）**urpf**（未定義の例外リスト＝全免除）**nat**（deny＝変換しない）
**vty**（access-class の範囲外で締め出し）。★**追測 P15 が必要になった**=
「未定義の名前を参照したら IOS が空の ACL を自動生成するのか」が未検証で、
生成されるなら未定義と空が同一になり evidence が成立しなかった →
**自動生成されない**ことを実測し 3 仮説の並立を確認（poc/acl §13）。
検証= selftest（select 900/900・read 324/324・cause 168/168・
**P1b/P1c 960/960**・実測整合 8/8・NG 0）＋E2E70問（8形すべて出現・
evidence で答えの出力を提示していないこと・logread の個数指定の保全・NG0）＋
決定性（acl 20問・mixed 30問）＋全11shape回帰OK |
| **P2** | mixed ルーレット合流・`obfuscate_md`／`messy_mermaid` 適用・selftest 全組合せ |
| ~~**P3**~~ | ✅ **完了(2026-08-10)**= **shape=aclv6**（`gen_paper_mcq.py --shape aclv6`・mixed 合流済）。
素材= [gen_paper_aclv6.py](../../topologies/gen_paper_aclv6.py)・
評価器= [acl6_model.py](../../topologies/acl6_model.py)。★**IPv4 とは別エンジン**にした=
IPv6 は**プレフィックス長（連続マスク）しか無い**ので三値キューブ代数は不要で、
前方ビット比較だけで閉じる。故障種**6**・要件世界3・出題形4（select/read/cause/counter）。
★**中核の故障種 `v6_explicit_deny_nd`**= 末尾に明示の `deny ipv6 any any` を書くと
**暗黙の `permit icmp any any nd-na` / `nd-ns` が失われ、近隣探索ごと落ちて隣接が
解決できなくなる**（`show ipv6 neighbors` が **INCMP**）。試験対策教材でも定番の論点。
★★**この結論に至るまでに測定を1度誤った（poc/acl §14-2b）**= 最初の測定は
オンリンクの /64 を permit したまま**そのグローバルアドレスを ping**しており、
NA（送信元＝解決対象そのもの）が**自分で書いた permit に一致して通っていた**。
さらに**判定を ping の成否で行っていた**（正しい指標は隣接の REACH / INCMP）。
一度は「定説は再現しない」と誤結論を出しかけ、**ユーザの指摘で気づいて測り直した**。
他に **空の IPv6 ACL は保持されない**
（未定義と同一の状態＝IPv4 で作れた evidence 形は移植不可）・**`resequence` が無い**・
**`show` は sequence が行末／running-config は行頭**・**ワイルドカード表記は構文エラー**。
検証= selftest（select 一意性 720/720・各形 810/810・**実測整合 11/11**・NG0）＋E2E36問（4形・6種・**ND 故障の盤面だけ隣接表が INCMP** を機械確認・NG0）＋
決定性（aclv6 16問・mixed 40問）＋**全12shape回帰OK** |

---

## 10. 決定事項（2026-08-09 ユーザ承認）

1. **ロールの初期スコープ**= P1a は **filter + routefilter の 2 種**で開始する。
   （routefilter は §2 の「拡張 ACL 特殊解釈」があり**思考密度が最も高い**ため初弾に含める。
   copp / urpf / nat / vty は P1c で追加）
2. **PBR ロールは新 shape の衣装から除外**する（既存 shape=pbr と重複するため）。
3. **shape 名は `acl`**（`gen_paper_mcq.py --shape acl` / 素材は `gen_paper_acl.py`）。

---

## 10-b. P1a 実装で判明した設計上の知見（2026-08-10）

1. ★**「意味だけの要件世界」は単独では一意化できない**。「過剰に許可するな(`exact`)」は
   **厳密一致の書き方が複数ある**（3行の列挙 と `deny` 先行＋広い permit は
   `acl_cover.acl_equivalent()` で**意味的に等価**と証明できる）ため正解が2つになる。
   → **works() は意味・complies() は提示**（行数・`deny` の有無）と役割を分け、
   `exact_no_deny` / `exact_min` のように**意味 × 提示の組**で世界を定義した。
2. ★**「触れてはいけない網」の置き場所が候補の失格を決める**。除外網を上位キューブの
   **内側**（base+5）に置くと、広すぎる候補（`0.0.7.255`）と非連続候補（`0.0.5.255`）が
   機械的に失格になる。外側に置くと両方が「直る候補」に残り一意性が壊れる。
3. ★**フィルタが実質「不在」になる3種は read 形が成立しない**
   （`undef_ref` / `empty_acl` / `ext_named_rejected`）。**全部素通りが実測どおりの正解**
   なので「通るのはどれか」の対比が作れない。→ `forms_for()` で形を盤面ごとに制限する。
   3種が同じ症状に化けるのは欠陥ではなく、この分野の教育点そのもの。
4. ★**BL-088（不親切化）との衝突が4例目**。acl の read 形は**設問文が向き**
   （転送される/破棄される）**と選ぶ個数**を担っているため、汎用文に均すと解答不能になる。
   → `keep_ask` の対象に追加（evidence / patch / dbgconf / authread に続く）。
5. ★**症状が観測に出ない盤面を作りかけた**（BL-103 ③と同型）。cause 形で ACL の構成しか
   出しておらず、「想定と違う挙動」を示す観測が無かった。→ `acl_symptom_block()` を追加し、
   **判定と同じ関数（`read_items` / `route_kept` / `flow_passes`）から描く**。
   read 形では答えになるので出さない。
6. `mask_as_wildcard` と `ext_src_is_network` は、**1行目を正しく書き2行目だけ誤る**形に
   した。全行を誤らせると「全断／全滅」になって観測の対比が消える（部分的な症状のほうが
   読解問題として成立する）。

## 11. 参照

- 上位= [BACKLOG.md](../../BACKLOG.md) BL-106（本メモ）・BL-100（選定台帳=
  [PAPER-BLUEPRINT-GAP.design.md](PAPER-BLUEPRINT-GAP.design.md) §3 P-B）
- 隣接= BL-082（紙面 MCQ 拡張ロードマップ）・BL-084（uRPF）・BL-081（PBR 被覆エンジン）・
  BL-014（ACL 道場・`acl_model.py`）
- 新ファミリ共通チェックリスト 11 項= PAPER-BLUEPRINT-GAP.design.md §5（着手時に必ず確認）
