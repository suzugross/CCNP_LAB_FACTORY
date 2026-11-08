# CTRL-HOST-MAC — 制御ホストを MacBook へ移す(BL-265)

2026-11-07 起票。状態(2026-11-08)= ①〜⑤完了(試運転はスリープの確認だけ残り)。次= ⑥片付け(1〜2 週間後)。
★Mac のアドレスは **10.1.10.3**(ユーザが固定済み・2026-11-08 決定)。旧 VM の .6 は引き継がない(§6.1)。

## 1. 目的と判断

**目的**: CML と同じホスト PC で動いている制御用 VM を止め、ホストのメモリを空ける。移す先はメモリに余裕のある MacBook。

**実測(2026-11-07)**

| 対象 | 状況 |
|---|---|
| 制御用 VM(Ubuntu 24.04 x86) | 割り当て 8GB・2 vCPU・スワップなし。使用 3.1GB。内訳= VS Code サーバ 約 1.3GB(古い版の残り 約 350MB を含む)・Claude Code 4 セッション 約 1.2GB・配信サーバとワークスペース 約 0.1GB |
| メモリ不足 | 10/31〜11/01 に OOM で数十回プロセスが落ちた(同じ VM の別プロジェクトの node 系開発サーバを動かしていた時) |
| CML | 47GB 中 25GB 使用(11 台のラボ 1 本が稼働中) |

重いのはラボの道具ではなく開発ツール(VS Code・Claude Code)。VM を縮める手は OOM の実績があるので取らない。

**移せないもの**: CML(x86 の仮想化支援が前提。Apple Silicon は非対応)、containerlab ホスト(vJunos EVO は x86 の KVM が前提)。
どちらも今のまま。制御ホストは CML へ API・SSH、containerlab ホストへ SSH するだけ。

**最大の制約**: 機器の管理 IF には自宅セグメント(10.1.10.0/26)以外への経路がない
(`roles/baseline/templates/` の router・iosxr は MGMT VRF に経路なし、switch は管理 SVI に既定 GW なし)。
制御ホストはこのセグメントに直接いること。VPN で別サブネットの IP をもらうと、CML の API・コンソールは使えるが
機器への SSH(構築の完了確認・採点・パック作成)は返事が戻らない。**VPN 越しの制御はユーザ判断で対象外**。

**方式**: Mac の Docker に開発コンテナを作り、今の Linux 環境をそのまま持っていく。
Mac ネイティブは手直しが要るので採らない(ping の `-W` が macOS ではミリ秒・telnet がない・ansible-pylibssh に
macOS arm64 の配布物がない・Ansible の fork の安全装置)。

## 2. 構成(`.devcontainer/`)

| ファイル | 役目 |
|---|---|
| `Dockerfile` | Ubuntu 24.04・Python 3.12・利用者 suzuki(UID 1000)・`/opt/venv`・コレクション・rclone 1.75.1・telnet/ping/jq/poppler/rsync |
| `requirements.txt` | 旧 VM の `.venv` の pip freeze(127 個) |
| `requirements.yml` | pip の ansible に入っていないコレクション 3 つ(cisco.cml 1.2.0・juniper.device 2.0.2・junipernetworks.junos 11.1.1) |
| `devcontainer.json` | マウント・ポート・拡張 |
| `post-create.sh` | `.venv` → `/opt/venv` のリンク・git の safe.directory・道具と行き先の確認表示(何度でも走らせてよい) |
| `pull-from-vm.sh` | 旧 VM からコンテナのホームへ写す(下見が既定・`--go`・`--final`) |

- **ホスト側の 1 フォルダ `~/ccnp-home`(名前は固定)をコンテナのホーム `/home/suzuki` として見せる**。リポは
  `~/ccnp-home/ansible/CCNP01` = コンテナの `/home/suzuki/ansible/CCNP01`。旧 VM と同じパスなので、
  Claude Code のメモリ(`~/.claude/projects/-home-suzuki-ansible-CCNP01/`)とスクリプトの絶対パスがそのまま通る。
  Mac のファイルとして見えるので Time Machine の対象にもなる。
- 仮想環境はイメージの中(`/opt/venv`)。スクリプトと playbook が呼ぶ `$REPO/.venv/bin/python3` はリンクで通す。
  パッケージを足す時は `requirements.txt` に足してコンテナを作り直す。
- コレクションは `/usr/share/ansible/collections`(既定の検索先。pip の ansible の同梱版より先に見つかる)。
- 8899(配信サーバ)・8897(ワークスペース)は**同じ番号で**公開する。配信サーバはワークスペースへの案内 URL を
  `Host` ヘッダとワークスペースのポート番号から組み立て、ワークスペースは Origin を `Host` と照合するため。
- `shutdownAction: none`: VS Code の窓を閉じてもコンテナは止まらない(配信サーバと夜間のパック作成を続ける)。
- **PVT と資格情報はイメージに入れない**。ビルドの文脈は `.devcontainer/` だけで、リポ直下の `.dockerignore` は
  全除外(誤ってリポ直下でビルドした時の保険)。イメージはどこにも push しない。

## 3. 手順

| 段 | 内容 | 担当 | 状態 |
|---|---|---|---|
| ① 準備 | `.devcontainer/` 一式・依存の固定・検証(§7) | Claude(VM 上) | ✅ 2026-11-07 |
| ② Mac の用意 | §4 | ユーザ | ✅ 2026-11-08(containerlab への経路だけ未設定。ホストを動かす時に入れる) |
| ③ コピー(1 回目) | §4 の最後。VM は動かしたまま | ユーザ+Mac の Claude Code | ✅ 2026-11-08 |
| ④ 試運転 | §5。VM と並行 | 同上 | ✅ 2026-11-08(結果は §5.1。スリープだけ未確認) |
| ⑤ 切り替え | §6 | 同上 | ✅ 2026-11-08(確認の記録は §6.1 の末尾) |
| ⑥ 片付け | §6。1〜2 週間後 | ユーザ | |

## 4. Mac の用意と 1 回目のコピー(②③)

### 4.1 用意

1. **OrbStack を入れる**(Docker Desktop より勧める)。公式の説明では、公開したポートは既定で LAN の他の機器から届き
   (設定 `Expose ports to LAN`)、ping・traceroute にも対応する。メモリは使った分だけ取る。
   Docker Desktop には「コンテナから Mac のいる LAN の機器へ届かない」という報告がある(2025-12・フォーラム)。
2. VS Code と Dev Containers 拡張(日本語の言語パックは Mac 側の VS Code に入れる)。
3. Mac のアドレスを 10.1.10.0/26 の中にする。MGMT プール(.11〜.20・.31〜.60)と被らないこと。
   → **10.1.10.3 に決定**(2026-11-08。ユーザが固定済み)。旧 VM の .6 は引き継がない。
   機器・CML・containerlab には制御ホストのアドレスで絞る設定がない(vty の ACL なし・管理 IF は /26 の中なら返事を返す)ので、
   .3 のままで動く。.6 を書いていたのは案内の文と文書だけ(7 か所・2026-11-08 に .3 へ直した)。
   紙面の問題文の「管理ステーション 10.1.10.6」(`gen_paper_svc.py`・出題済みの問)は架空の値なので触らない。
4. containerlab の管理網への経路(再起動後も残る):
   `networksetup -listallnetworkservices` でサービス名を確かめ、
   `sudo networksetup -setadditionalroutes "<サービス名>" 172.20.20.0 255.255.255.0 10.1.10.9`。
   Wi-Fi と有線の両方を使うなら、両方のサービスに入れる。
5. スリープ: 電源接続時はディスプレイが切れても自動でスリープしない設定にする。外部ディスプレイなしで蓋を閉じると眠る
   (夜間だけなら `caffeinate -s` でもよい)。

### 4.2 `.devcontainer` を Mac へ持ってくる(Mac のターミナル)

```
mkdir -p ~/ccnp-home/ansible/CCNP01
scp -r suzuki@10.1.10.6:ansible/CCNP01/.devcontainer ~/ccnp-home/ansible/CCNP01/
ls ~/ccnp-home/ansible/CCNP01/.devcontainer     # 6 個(Dockerfile・devcontainer.json・post-create.sh・pull-from-vm.sh・requirements.txt/.yml)
```
- Mac(szk-MAC01)の鍵は VM の authorized_keys に登録済みなので、パスワードは聞かれないはず。
- `~/ccnp-home` の名前は変えない(devcontainer.json がこの名前で参照する)。

### 4.3 コンテナを開く

1. OrbStack を起動しておく。
2. VS Code で「ファイル → フォルダーを開く」→ `~/ccnp-home/ansible/CCNP01`。
3. 右下の通知の「コンテナーで再度開く(Reopen in Container)」。出なければ ⌘⇧P →「Dev Containers: Reopen in Container」。
4. 初回はイメージのビルド(Ubuntu の取得・apt・Python 127 個・コレクション)。通知の「ログの表示」で進み具合が見える。
   失敗したらログの末尾を旧 VM の Claude Code に渡して `Dockerfile` を直し、4.2 の `scp` をやり直して
   ⌘⇧P →「Dev Containers: Rebuild Container」。
5. 終わると `post-create.sh` の表示がターミナルに出る。この時点では `local.yml`・鍵・`rclone.conf` が「なし」で正常。

### 4.4 写す(1 回目)

VS Code の「ターミナル → 新しいターミナル」(プロンプトが `suzuki@ccnp-ctrl`)で:
```
.devcontainer/pull-from-vm.sh          # 下見。最後に「Total file size: 約 1.06G」と出る(--list で 1 ファイルずつ)
.devcontainer/pull-from-vm.sh --go     # 写す
```
- VM の鍵の指紋は初回だけ自動で受け入れる(`StrictHostKeyChecking=accept-new`)。パスワードを聞かれたら VM の suzuki のもの
  (Mac の ssh-agent に鍵が載っていれば、VS Code が転送するので聞かれない)。
- ★2026-11-08 実測: 写した `~/.ssh/id_ed25519` は **VM 自身の鍵**なので、コンテナから VM へはこの鍵では入れない
  (VM の authorized_keys にない)。コンテナから VM へ ssh するには、Mac のターミナルで `ssh-add` して Mac の鍵を
  ssh-agent に載せる(VS Code がコンテナへ転送する)。載っていない時は「The agent has no identities」になり、パスワードを聞かれる。
- 終わると `post-create.sh` がもう一度走り、全部 OK/あり になる。
- ⌘⇧P →「Developer: Reload Window」で窓を読み直す(写した `.bashrc` などを効かせる)。
- 写している間は VM 側で大きな作業をしない。
- 写すもの・写さないものは `pull-from-vm.sh` の冒頭。Claude Code のログイン情報は写さない。

### 4.5 Claude Code にログイン

コンテナの中の Claude Code のパネルを開いてサインインする(ブラウザが開く)。
起動時に「学習ノルマの現況」が出れば SessionStart のフックが動いている。
「BL-265 の現在地は?」と聞いて答えられれば、メモリ(`-home-suzuki-ansible-CCNP01`)が読めている。

## 5. 試運転(④)

約束:
- 試運転の間は **VM 側でラボを出さない**(MGMT の貸出台帳 `topologies/_state/` が 2 つに割れ、同じアドレスを配る)。
- **試運転で出したラボは必ず撤収してから切り替える**(最終の写しで台帳が VM の状態に戻るため)。
- Mac 側で作ったもの・変えたものは、⑤の最終の写しで VM の状態に上書きされる(試運転は使い捨て)。

| # | 確かめること | コマンド・見方 | 期待 |
|---|---|---|---|
| 1 | 機器の網へ出られる | `ping -c 2 10.1.10.10`・`scripts/lab.sh status` | ping が返る・CML のラボ一覧と MGMT の貸出が出る |
| 2 | ラボ一周 | `scripts/lab.sh provision ENARSI-OSPF-MADJ-01` → `scripts/lab.sh grade ENARSI-OSPF-MADJ-01` → `scripts/lab.sh teardown ENARSI-OSPF-MADJ-01` | IOL 6 台。白紙なので 20/100 前後(従来の実測と同じ)。撤収まで通る |
| 3 | 配信とワークスペース | `scripts/pack.sh serve` → 別の端末から `http://<Mac のアドレス>:8899/` | ポータルが開く・ラボのワークスペースでコンソールが映る(見るだけで打たない)。Ctrl+C で止める |
| 4 | Drive・GitHub | `rclone lsd gdrive:`・`git fetch` | 一覧が出る・エラーなし(push はしない) |
| 5 | パック作成 | `scripts/pack.sh new --dry-run` | 下見が最後まで出る |
| 6 | containerlab | ホストが動いている時だけ: `ssh suzuki@10.1.10.9 true` | 通る(止まっていれば飛ばす) |
| 7 | スリープ | 電源につないで画面を消し、しばらくして `scripts/lab.sh status` | コンテナが動き続けている |

届かない時(1 が失敗):
- macOS 15 以降は「システム設定 → プライバシーとセキュリティ → ローカルネットワーク」で OrbStack と VS Code を許可する。
- Mac のアドレスが 10.1.10.0/26 の中か(`ipconfig getifaddr en0`)。
- `~/.ssh` の鍵が使えない時は、Mac のフォルダの上での権限の扱いを疑う(だめなら鍵だけ名前付きボリュームへ逃がす)。

### 5.1 試運転の結果(2026-11-08・Mac 10.1.10.3 のコンテナ)

| # | 結果 |
|---|---|
| 1 | ✅ CML(.10)・旧 VM(.6)へ ping が返る。CML の API(2.10.1・ready)に届く。`lab.sh status` で貸出台帳が読める |
| 2 | ✅ `ENARSI-OSPF-MADJ-01`: provision 51 秒(6 台とも SSH 確認)・grade 2 分 32 秒で 20/100(白紙・従来どおり)・teardown 3 秒(CML の absent と貸出の返却まで) |
| 3 | ✅ ユーザが別の端末から `http://10.1.10.3:8899/` とワークスペースを普段どおり使えた。コンテナの中から .3 経由で開くのも可 |
| 4 | ✅ `rclone`(`gdrive:` はファイルだけのフォルダなので `lsd` は空・`lsf` で中身が出る)・`git fetch` |
| 5 | ✅ `pack.sh new --dry-run` が最後まで出る(2.8 秒)。★下見でも `packs/` に `dry_run: true` のパックを作るので、試運転の後で消した |
| 6 | 飛ばした(containerlab のホストが停止中・Mac に経路も未設定) |
| 7 | 未確認 |

気づいたこと:
- 配信サーバを止めればワークスペースは 1 秒で後を追って止まる(コンテナでも旧 VM と同じ)。
- `rclone` が「共用の client_id は 2026 年中に使えなくなる」と注意を出す(移行とは無関係・旧 VM でも同じ)。
- 試運転の採点で `records/attempts.jsonl` に 1 行入る(今日のノルマに「挑戦中」と出る)。最後の写しで VM の状態に戻る。

## 6. 切り替え・戻し方・片付け(⑤⑥)

### 6.1 切り替え

前提: 試運転のラボは撤収済み。VM でパック作成が走っていない時。切り替え前にコミットしておくと戻す先がはっきりする
(コミットはユーザの指示で)。出題中のラボ(例: XRT-14)は作業フォルダ・`_generated`・`_state` ごと写るので続けられる。

1. **VM の配信サーバを止める**(VM のターミナル):
   ```
   pkill -f topologies/pack_server.py
   pgrep -af "pack_server|lab_console"     # 何も出なければよい(ワークスペースは親と一緒に終わる)
   ```
   VM に開いている VS Code・Claude Code の窓を閉じる。
2. **最終の写し**(Mac のコンテナ。**Mac の Claude Code のセッションも閉じてから**、VS Code のターミナルで):
   ```
   .devcontainer/pull-from-vm.sh --go --final                  # VM で消えたファイルはこちらでも消す
   ```
   - `--final` は Mac 側にしかないファイルを消す。`~/.claude` の下の Mac で開いたセッションの記録も消えるので、
     残したい決定は切り替えの前に VM 側へ書いておく(2026-11-08 はそうした= この design・BACKLOG・メモリ・.3 への直し)。
   - `--with-images`(`~/cml-images`)は**持っていかない**(2026-11-08 ユーザ判断)。中身の記録は §6.3。
3. **VM を止める**: VM のターミナルで `sudo poweroff`(VMware からゲストのシャットダウンでもよい)。削除はまだしない。
4. ~~Mac に 10.1.10.6 を引き継ぐ~~ → **やらない**(2026-11-08。Mac は 10.1.10.3 のまま使う。§4.1 の 3)。
   VM(.6)と Mac(.3)は同時にいられるので、戻す時も VM を起動するだけでよい。
5. **配信を再開**(Mac のコンテナ): `nohup scripts/pack.sh serve > /dev/null 2>&1 &`。
   別の端末から `http://10.1.10.3:8899/` が開けば完了(ブックマークは .6 → .3 へ)。
   Mac を再起動した時は、OrbStack → VS Code でコンテナを開く → `pack.sh serve` をもう一度(旧 VM の再起動後と同じ)。
6. コンテナの Claude Code で、メモリの「制御ホスト」の記述が Mac(10.1.10.3)になっているか確かめる(2026-11-08 に VM 側で更新済み)。

**切り替えの確認(2026-11-08・Mac のコンテナの Claude Code)**: VM(.6)は ping に応答なし(停止)。配信サーバと
ワークスペースはコンテナで稼働(01:16 起動・ポータル 200)。`--final` まで走った(試運転で Mac に作ったセッションの記録と
`records/attempts.jsonl` の試運転の 1 行が消え、VM の状態に戻っている)。MGMT の貸出台帳は XRT-14(.11〜.19)を引き継ぎ、
機器へ ping が届く。メモリの制御ホストの記述は .3(古い日付の記録に残る .6 のうち、今のポータルの場所と読めるものは .3 へ直した)。

Windows などから VS Code の Remote-SSH で制御ホストに入る使い方はできなくなる(コンテナに sshd はない)。作業は Mac で行う。

### 6.2 戻し方

VM を起動(.6 のまま。Mac の .3 とは被らない)→ Mac 側の配信サーバを止める → 切り替え後に Mac で変えたものを VM へ戻す(コンテナの中で。
Mac の ssh-agent に鍵を載せておく= §4.4):
```
rsync -a --no-o --no-g --exclude .venv --exclude __pycache__/ ~/ansible/CCNP01/ suzuki@10.1.10.6:ansible/CCNP01/
rsync -a --no-o --no-g ~/.claude/projects/-home-suzuki-ansible-CCNP01/ suzuki@10.1.10.6:.claude/projects/-home-suzuki-ansible-CCNP01/
```
(`--delete` は付けない。VM 側の配信サーバは `nohup scripts/pack.sh serve > /dev/null 2>&1 &` で再開する。)

### 6.3 片付け(1〜2 週間後)

1. **VM を削除する**。同じ VM のほかのプロジェクトは移行済みか破棄済み(2026-11-07 ユーザ確認)なので、残すものはない。
   ★`~/cml-images` は持っていかないと決めた(2026-11-08 ユーザ判断)。VM を消すとなくなる。中身の記録は下の「旧 VM にだけあったもの」。
2. **CML の VM のメモリを増やす**: 稼働中のラボを撤収 → CML を止める(Cockpit `https://10.1.10.10:9090` のシャットダウンか、
   VMware からゲストのシャットダウン)→ VMware で CML の VM のメモリを増やす(今 CML から見えている約 47GB に、旧 VM の分の 8GB を足す)
   → 起動 → Claude に CML の `system_stats` で総量が増えたかを確かめてもらう。
   47GB→55GB でも XRv9000 の同時 3 台は厳しい(1 台で実使用 約 17GB)。効くのは IOL の台数と全体の余裕。
3. **記録**: BACKLOG の BL-265 を完了アーカイブへ・この design の状態を更新・メモリの記述(制御ホストの場所・IP)を更新。

**旧 VM にだけあったもの(持っていかない・2026-11-08 ユーザ判断)**

| 場所 | 中身 | 取り直し方 |
|---|---|---|
| `~/cml-images/`(855MB・2026-10-18) | `services.iso`(cml-docker-containers v0.3.1 の refplat-20260701-services.iso・896,307,200 バイト・sha256 `0a924255…f9ca50a5`)・署名 `services.iso.asc`・説明 `README.md` | 公開物。https://github.com/CiscoLearning/cml-docker-containers/releases/tag/v0.3.1 から取り直す |

- CML へ登録済み= `frr-10-6-1-r0`・`tacplus-f4-0-4-28`・`radius-3-2-7-dfsg-1-deb13u2`(VM を消しても CML 側に残る)。
- 未登録= `syslog-4-8-1-5-deb13u1`・`dnsmasq-2-91-1-deb13u1`・`nginx-1-31-2`・`net-tools-2-10-1-3`・`snort-3-10-0-0`・
  `thousandeyes-ea-0-86-0-agent`。ノード定義は CML 2.10.1 に全部入っていて、足りないのはイメージだけ。
- 登録の道具はリポにある: `topologies/cml_image_import.py ls|import <iso> <イメージ ID>…`(取り直した iso を渡す)。

## 7. ①の検証の記録(2026-11-07・VM 上)

- `requirements.txt` から新しい仮想環境を作り直し、`pip check` が通り、`pip freeze` が旧 `.venv` と完全に一致。
  コレクション 3 つも `requirements.yml` から入る。
- 127 個すべてに Linux arm64 向けの配布物がある(PyPI で 1 つずつ確認。pyATS・Genie・Unicon 26.4 は
  manylinux2014_aarch64 あり。f5-icontrol-rest・pyftpdlib・tftpy はソース配布だけだが Python だけ)。
- rclone 1.75.1 の linux-arm64 / linux-amd64 の配布物が取れる。apt のパッケージ名は noble にすべてある。
- `pull-from-vm.sh` の下見(VM の上で `--dest` を一時フォルダに): 21,847 ファイル・1.06GB。
  `.venv`・`~/.local`・`~/.vscode-server`・`~/.nvm`・`.credentials.json`・ほかのプロジェクト・`__pycache__` は 0 件。
  鍵・rclone.conf・`.claude.json`・メモリ・`local.yml`・`private/`・`.git`・`_state` は入っている。
- コンテナの外(VM の上)で写し先を指定せずに走らせると止まる(rc=2)。

**Mac での初回(2026-11-08)**: OrbStack(docker 29.8.2)で arm64 のイメージのビルドが通った(218 秒。うち Python の
仮想環境 162 秒)。コンテナは aarch64・Ubuntu 24.04.5。`post-create.sh` の表示= Python 3.12.3・pyats 26.4・
ansible-core 2.20.6。コレクションが「4 / 3」と出たのは数え方の誤り(pip の ansible に同梱の junipernetworks.junos 11.0.0 も
数えていた)→ 名前を重複なしで数えるよう直した(写し取りで Mac へも届く)。VS Code は Mac の ssh-agent をコンテナへ転送している。

## 8. 未決

- なし。
- 決着済み: Mac のアドレス= 10.1.10.3(2026-11-08 ユーザが固定済み・.6 は引き継がない)。
- 決着済み: 同じ VM のほかのプロジェクトは移行済みか破棄済み(2026-11-07 ユーザ確認)→ VM は最後に削除できる。
  Mac の Docker は OrbStack を勧める(§4.1)。
