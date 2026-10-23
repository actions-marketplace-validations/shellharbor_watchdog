# CI-only SDK builder. Root is required by the upstream compiler toolchain;
# it is not a deployment image and must never be published as Watchdog runtime.
FROM mikefarah/yq:4.47.2@sha256:76def1f56f456ecc1c3173ea275218ee17139bc2018c5a07887b15afd88ec03e AS yq
FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:21f6fab17ace4dc76e1c56de91ee95d3d03da021df94b41056ba036f6c6f55e9

COPY --from=yq /usr/bin/yq /usr/local/bin/yq
COPY service-watchdog.sh VERSION /src/watchdog/
COPY lib/watchdog /src/watchdog/lib/watchdog/
COPY .clusterfuzzlite /src/watchdog/.clusterfuzzlite/
COPY .clusterfuzzlite/build.sh /src/build.sh
WORKDIR /src/watchdog
