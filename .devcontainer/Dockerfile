FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies only (no build tools needed)
RUN apt update && apt install --assume-yes \
    curl \
    git \
    openjdk-25-jdk \
    uuid-dev \
    zsh \
    && apt autoremove -y \
    && apt clean -y \
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

# Python configuration
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE

# Shell setup
RUN chsh -s /bin/zsh
COPY ["./zshrc", "/root/.zshrc"]
