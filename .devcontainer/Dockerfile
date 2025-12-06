FROM python:3.13-slim AS antlr-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install --assume-yes \
    build-essential \
    cmake \
    pkg-config \
    unzip \
    uuid-dev \
    wget

WORKDIR /antlr-build

# Download ANTLR artifacts
RUN wget https://www.antlr.org/download/antlr-4.13.2-complete.jar && \
    wget https://www.antlr.org/download/antlr4-cpp-runtime-4.13.2-source.zip && \
    wget https://www.antlr.org/download/antlr-runtime-4.13.2.jar

# Build C++ runtime
RUN unzip antlr4-cpp-runtime-4.13.2-source.zip -d cpp-runtime && \
    cd cpp-runtime && \
    mkdir build && cd build && \
    cmake .. && \
    make -j $(nproc --all) && \
    DESTDIR=/antlr-install make install


# =============================================================================
# Stage 2: Final Runtime Image
# =============================================================================
FROM python:3-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies only (no build tools needed)
RUN apt update && apt install --assume-yes \
    ant \
    gdb \
    git \
    maven \
    openjdk-25-jdk \
    curl \
    zsh \
    zip \
    uuid-dev \
    && apt autoremove -y \
    && apt clean -y \
    && rm -rf /var/lib/apt/lists/*

# Copy ANTLR artifacts from builder stage
COPY --from=antlr-builder /antlr-build/antlr-4.13.2-complete.jar /usr/local/lib/
COPY --from=antlr-builder /antlr-build/antlr-runtime-4.13.2.jar /usr/local/lib/
COPY --from=antlr-builder /antlr-install/usr/local/lib/ /usr/local/lib/
COPY --from=antlr-builder /antlr-install/usr/local/include/ /usr/local/include/

# Configure ANTLR
RUN echo 'export CLASSPATH=".:/usr/local/lib/antlr-4.13.2-complete.jar:$CLASSPATH"' >> /etc/profile.d/setClassPath.sh && \
    echo '#!/bin/sh -ue' > /usr/bin/antlr && \
    echo 'java -jar /usr/local/lib/antlr-4.13.2-complete.jar $@' >> /usr/bin/antlr && \
    chmod 755 /usr/bin/antlr && \
    ldconfig

# Python configuration
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE

# Install antlr4-tools
# RUN python3 -m pip install --break-system-packages antlr4-tools
# ENV PATH="$PATH:/root/.local/bin"

# Shell setup
RUN chsh -s /bin/zsh
COPY ["./zshrc", "/root/.zshrc"]