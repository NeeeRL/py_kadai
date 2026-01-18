FROM python:3.12-slim

# 必要なシステムパッケージのインストール
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    python3-dev \
    python3-pygame \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    xvfb x11vnc fluxbox \
    pulseaudio-utils alsa-utils \
    htop fish tmux \
    sudo iputils-ping openvpn \
    curl wget git npm\
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Neovim-settings
RUN curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim-linux-arm64.tar.gz \
    && mkdir -p /usr/local/lib/nvim \
    && tar -C /usr/local/lib/nvim -xzf nvim-linux-arm64.tar.gz --strip-components=1 \
    && ln -sf /usr/local/lib/nvim/bin/nvim /usr/local/bin/nvim \
    && rm nvim-linux-arm64.tar.gz

# PygameなどのPythonパッケージをpipでインストール
RUN pip install --no-cache-dir --break-system-packages pygame

# ユーザー作成
RUN useradd -m -s /usr/bin/fish kali && \
    echo "kali:kali" | chpasswd && \
    usermod -aG sudo kali



RUN mkdir -p /home/kali/.config && \
    git clone --depth 1 https://github.com/NeeeRL/nvim.git /home/kali/.config/nvim && \
    chown -R kali:kali /home/kali

# entrypoint.sh をコピーして実行権限を付与
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 環境変数の設定
ENV DISPLAY=:1
ENV SDL_VIDEODRIVER=x11

# 作業ディレクトリを /opt に設定（マウント先）
WORKDIR /opt

ENTRYPOINT ["/entrypoint.sh"]
CMD ["fish"]
USER kali
