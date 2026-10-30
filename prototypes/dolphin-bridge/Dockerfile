FROM ubuntu:26.04
ENV DEBIAN_FRONTEND=noninteractive
# All package/source changes are confined to this disposable build container.
RUN sed -i 's/Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake ninja-build patch dpkg-dev \
    && apt-get build-dep -y dolphin
WORKDIR /work
RUN apt-get source dolphin \
    && test -d dolphin-25.12.3
COPY clicked-uri.patch /work/clicked-uri.patch
RUN cd dolphin-25.12.3 && patch --dry-run -p1 < /work/clicked-uri.patch \
    && patch -p1 < /work/clicked-uri.patch
RUN cmake -S dolphin-25.12.3 -B build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/filewheel-dolphin-probe \
    -DBUILD_TESTING=OFF -DCMAKE_DISABLE_FIND_PACKAGE_KF6UserFeedback=ON \
    && cmake --build build --parallel 2 \
    && cmake --install build
