FROM ubuntu:22.04@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11 AS python
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev libffi-dev liblzma-dev libzstd-dev \
    libgl1 libegl1 libglib2.0-0 libfontconfig1 libxkbcommon-x11-0 \
    libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 libxcb-render-util0 \
    libdbus-1-3 libwayland-client0 libxrender1 libxcomposite1 libxi6 \
    ffmpeg patchelf binutils
COPY build-tools/linux/Python-3.14.10.tar.xz /tmp/Python.tar.xz
RUN echo 'de414a57119abef52784d8993e341d53aed635fc2b05c2607d9f98a2c5b72032  /tmp/Python.tar.xz' | sha256sum -c - \
    && cd /tmp && tar xf Python.tar.xz \
    && cd Python-3.14.10 && ./configure --prefix=/opt/python --enable-shared --with-ensurepip=install \
    && make -j2 && make install
ENV PATH=/opt/python/bin:$PATH LD_LIBRARY_PATH=/opt/python/lib
FROM python AS dependencies
COPY packaging/linux/python-py314-x86_64.lock /tmp/python.lock
RUN python3.14 -m pip install --index-url https://pypi.org/simple \
    --require-hashes --only-binary=:all: -r /tmp/python.lock
FROM dependencies AS freeze
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer libreoffice-calc libreoffice-impress fonts-liberation2
WORKDIR /work
COPY src /work/src
COPY packaging /work/packaging
COPY pyproject.toml README.md LICENSE /work/
COPY build-tools/linux/pandoc-linux.tar.gz /tmp/pandoc.tar.gz
RUN python3.14 -m pip install --no-deps --no-build-isolation . \
    && python3.14 -m pip check \
    && python3.14 -m PyInstaller --clean --noconfirm packaging/linux/Filewheel.spec \
    && python3.14 packaging/linux/bundle_tools.py dist/Filewheel
FROM freeze AS verified
RUN QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
    FILEWHEEL_BUNDLED_TOOLS_ONLY=1 FILEWHEEL_LOG_DIR=/tmp/frozen-smoke \
    dist/Filewheel/filewheel --self-test --ui-backend quick; result=$?; \
    cat /tmp/frozen-smoke/self-test.json; \
    if [ -f /tmp/frozen-smoke/conversion-debug.log ]; then cat /tmp/frozen-smoke/conversion-debug.log; fi; \
    if [ "$result" -ne 0 ]; then exit "$result"; fi; \
    python3.14 packaging/linux/verify_smoke.py /tmp/frozen-smoke/self-test.json
