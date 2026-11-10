FROM mikefarah/yq:4.54.2@sha256:5d56494617dce8311106e905aac5c080a2087c905a7f7de2984db2e2cc60ab2e AS yq

FROM alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a

RUN apk add --no-cache \
        bash \
        bind-tools \
        clamav \
        coreutils \
        curl \
        iputils \
        openssl \
        sqlite \
        util-linux

COPY --from=yq /usr/bin/yq /usr/local/bin/yq
COPY service-watchdog.sh /opt/watchdog/service-watchdog.sh
COPY scripts/github-action-entrypoint.sh /usr/local/bin/watchdog-validate

RUN chmod 0555 /opt/watchdog/service-watchdog.sh /usr/local/bin/watchdog-validate

ENTRYPOINT ["/usr/local/bin/watchdog-validate"]
