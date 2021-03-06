FROM ubuntu:16.04
MAINTAINER djungelorm <djungelorm@users.noreply.github.com>

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    autoconf \
    automake \
    ca-certificates \
    cmake \
    curl \
    g++ \
    git \
    inotify-tools \
    libasio-dev \
    libboost-dev \
    libenchant1c2a \
    liblua5.1-0-dev \
    librsvg2-bin \
    libtool \
    libxml2-dev \
    libxslt1-dev \
    lua5.1 \
    luarocks \
    make \
    pkg-config \
    python \
    python-dev \
    python-pip \
    python-setuptools \
    python-virtualenv \
    texlive-fonts-recommended \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-latex-recommended \
    tzdata \
    unzip \
    virtualenv \
    wget && \
    rm -rf /var/lib/apt/lists/*

RUN apt-key adv \
      --keyserver hkp://keyserver.ubuntu.com:80 \
      --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF && \
    echo "deb http://download.mono-project.com/repo/debian wheezy main" | \
      tee /etc/apt/sources.list.d/mono-xamarin.list && \
    apt-get update && apt-get install -y mono-devel && \
    rm -rf /var/lib/apt/lists/*

ENV gosu_version 1.9
RUN apt-get update && \
    apt-get install -y --no-install-recommends sudo && \
    rm -rf /var/lib/apt/lists/* && \
    dpkgArch="$(dpkg --print-architecture | awk -F- '{ print $NF }')" && \
    wget -O /usr/local/bin/gosu \
      "https://github.com/tianon/gosu/releases/download/$gosu_version/gosu-$dpkgArch" && \
    wget -O /usr/local/bin/gosu.asc \
      "https://github.com/tianon/gosu/releases/download/$gosu_version/gosu-$dpkgArch.asc" && \
    export GNUPGHOME="$(mktemp -d)" && \
    gpg --keyserver ha.pool.sks-keyservers.net \
        --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 && \
    gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu && \
    rm -r "$GNUPGHOME" /usr/local/bin/gosu.asc && \
    chmod +x /usr/local/bin/gosu && \
    gosu nobody true

ARG bazel_version=0.5.0
RUN curl https://bazel.build/bazel-release.pub.gpg | apt-key add - && \
    echo "deb [arch=amd64] http://storage.googleapis.com/bazel-apt stable jdk1.8" | \
      tee /etc/apt/sources.list.d/bazel.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends bazel=${bazel_version} && \
    rm -rf /var/lib/apt/lists/*
COPY bazelrc /etc/bazel.bazelrc
RUN chmod 0644 /etc/bazel.bazelrc

ARG protobuf_version=3.3.0
WORKDIR /usr/local/src/protobuf-cpp-${protobuf_version}
RUN wget https://github.com/google/protobuf/releases/download/v${protobuf_version}/protobuf-cpp-${protobuf_version}.tar.gz && \
  tar -xf protobuf-cpp-${protobuf_version}.tar.gz --strip=1 && \
  ./configure && \
  make -j`nproc` && \
  make install && \
  ldconfig && \
  rm -rf rm -rf protobuf-cpp-$VERSION protobuf-cpp-$VERSION.tar.gz

ARG ksp_version
WORKDIR /usr/local/lib/ksp-${ksp_version}
RUN wget https://s3.amazonaws.com/krpc/lib/ksp-${ksp_version}.tar.gz && \
    tar -xf ksp-${ksp_version}.tar.gz && \
    ln -s /usr/local/lib/ksp-${ksp_version} /usr/local/lib/ksp && \
    rm /usr/local/lib/ksp-${ksp_version}/ksp-${ksp_version}.tar.gz

RUN user_id=1000 && \
    addgroup -q --gid $user_id build && \
    adduser -q --system --uid $user_id --home /build --disabled-password --ingroup build build
USER build
WORKDIR /build
RUN git clone http://github.com/krpc/krpc --depth 1 && \
    cd krpc && \
    bazel fetch //... && \
    bazel build \
      @cpp_protobuf//:protobuf \
      @cpp_googletest//:gtest \
      @cpp_googletest//:gmock && \
    cd .. && \
    rm -rf krpc
USER root
RUN deluser build

WORKDIR /
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
