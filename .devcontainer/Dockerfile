# syntax=docker/dockerfile:1
FROM astral/uv:python3.13-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/code \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" 

# Install the base toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    build-essential \
    ca-certificates \
    curl \
    default-jdk-headless \
    gh \
    git \
    gnupg \
    gpg \
    locales \
    openssh-client \
    uuid-dev \
    unzip \
    zsh \
    && rm -rf /var/lib/apt/lists/*


# Download ANTLR artifacts
RUN cd /usr/local/lib && \
    curl -O https://www.antlr.org/download/antlr-4.13.2-complete.jar

# Configure ANTLR
RUN echo 'export CLASSPATH=".:/usr/local/lib/antlr-4.13.2-complete.jar:$CLASSPATH"' >> /etc/profile.d/setClassPath.sh && \
    echo '#!/bin/sh -ue' > /usr/bin/antlr && \
    echo 'java -jar /usr/local/lib/antlr-4.13.2-complete.jar $@' >> /usr/bin/antlr && \
    chmod 755 /usr/bin/antlr && \
    ldconfig

# Rust configuration
ENV PATH="/root/.cargo/bin:${PATH}"
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# make zsh the default shell
RUN chsh -s $(which zsh)

RUN sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# install eza
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://raw.githubusercontent.com/eza-community/eza/main/deb.asc | gpg --dearmor -o /etc/apt/keyrings/gierens.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/gierens.gpg] http://deb.gierens.de stable main" | tee /etc/apt/sources.list.d/gierens.list \
    && chmod 644 /etc/apt/keyrings/gierens.gpg /etc/apt/sources.list.d/gierens.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends eza \
    && rm -rf /var/lib/apt/lists/*

# upgrade all packages to ensure we have the latest security updates
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Create the project virtualenv so it survives the workspace bind
# mount used by the dev container. The actual `uv sync` happens after the repo
# is mounted by devcontainer.json.
RUN uv python install 3.13 \
    && uv venv --python 3.13 "${UV_PROJECT_ENVIRONMENT}"

# Keep Codex config inside the container, but let auth be mounted in from the
# host so the CLI can reuse an existing login without copying secrets into git.
RUN mkdir -p /root/.codex \
    && printf '%s\n' \
    'model = "gpt-5.4"' \
    'model_reasoning_effort = "high"' \
    'approval_policy = "never"' \
    'sandbox_mode = "danger-full-access"' \
    > /root/.codex/config.toml

WORKDIR /code

# set the ~/.zshrc file 
COPY zshrc /root/.zshrc 

# source the .zshrc file to ensure the aliases are available in the dev container
RUN zsh -c "source /root/.zshrc"
