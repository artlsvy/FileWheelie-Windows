# A runtime with ordinary desktop libraries, deliberately no Python or converter tools.
FROM debian:12-slim@sha256:99c0b25c46d0214d5a2091092e7908907dcaecd6a962cde0ac700acee222b6f3
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libegl1 fontconfig fonts-liberation libdbus-1-3 libxkbcommon0 libwayland-client0 \
    && rm -rf /var/lib/apt/lists/*
ENV QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software FILEWHEEL_LOG_DIR=/tmp/check
