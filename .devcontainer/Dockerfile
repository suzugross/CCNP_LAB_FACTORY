# 制御ホスト(Ansible・pyATS・配信サーバ・Claude Code)の開発コンテナ(BL-265)。
#
# イメージに入れるのは道具だけ。リポ・PVT・資格情報はイメージに入れず、実行時のマウントで見せる
# (ビルドの文脈は .devcontainer/ だけ。リポの残りはビルドに渡らない)。
# 中身は旧制御ホスト(Ubuntu 24.04・Python 3.12)に合わせる。arm64(Apple Silicon)でも amd64 でも組める。
FROM ubuntu:24.04

ARG USERNAME=suzuki
ARG USER_UID=1000
ARG USER_GID=1000
ARG PIP_VERSION=26.1.1
ARG RCLONE_VERSION=1.75.1
ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    TZ=Etc/UTC

# telnet: collect_telnet.py などが pexpect で起動する / ping: 構築前後の疎通確認 / jq: Claude Code のフック
# poppler-utils: PDF の読み取り / rsync: 旧制御ホストからの写し取り(pull-from-vm.sh)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 python3-venv \
      openssh-client rsync git curl ca-certificates unzip \
      telnet iputils-ping iproute2 procps tcpdump \
      jq poppler-utils \
      sudo locales tzdata less vim nano bash-completion \
 && sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen && locale-gen \
 && rm -rf /var/lib/apt/lists/*

# 利用者は旧制御ホストと同じ名前・UID・ホーム(/home/suzuki)。パスが同じなので、Claude Code のメモリ
# (~/.claude/projects/-home-suzuki-ansible-CCNP01/)もそのまま使える。ubuntu:24.04 の既定利用者 ubuntu(UID 1000)は消す。
RUN if id ubuntu >/dev/null 2>&1; then userdel -r ubuntu; fi \
 && groupadd -g "${USER_GID}" "${USERNAME}" \
 && useradd -m -u "${USER_UID}" -g "${USER_GID}" -s /bin/bash "${USERNAME}" \
 && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
 && chmod 0440 "/etc/sudoers.d/${USERNAME}"

# rclone は Ubuntu の版が古いので公式の配布物を入れる(旧制御ホストと同じ版)。
RUN arch="${TARGETARCH:-$(dpkg --print-architecture)}" \
 && curl -fsSL -o /tmp/rclone.zip \
      "https://downloads.rclone.org/v${RCLONE_VERSION}/rclone-v${RCLONE_VERSION}-linux-${arch}.zip" \
 && unzip -q /tmp/rclone.zip -d /tmp \
 && install -m 0755 "/tmp/rclone-v${RCLONE_VERSION}-linux-${arch}/rclone" /usr/local/bin/rclone \
 && rm -rf /tmp/rclone*

# Python の仮想環境はイメージの中(/opt/venv)に作る。リポの .venv はここへのリンク(post-create.sh が張る)。
# スクリプトと playbook は $REPO/.venv/bin/python3 を呼ぶので、リンクがあれば今のまま動く。
COPY requirements.txt requirements.yml /tmp/ccnp/
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir "pip==${PIP_VERSION}" \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/ccnp/requirements.txt \
 && /opt/venv/bin/pip check \
 && /opt/venv/bin/ansible-galaxy collection install -r /tmp/ccnp/requirements.yml \
      -p /usr/share/ansible/collections \
 && chown -R "${USERNAME}:${USERNAME}" /opt/venv \
 && rm -rf /tmp/ccnp

USER ${USERNAME}
WORKDIR /home/${USERNAME}/ansible/CCNP01
