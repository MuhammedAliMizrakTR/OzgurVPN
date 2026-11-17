# syntax=docker/dockerfile:1
# Manifest-list digests verified 2026-11-14. Update versions.json + these pins together.
FROM --platform=$BUILDPLATFORM golang:1.27.4-alpine@sha256:0a5f7fe796599ff487605987432e7619ae45beeb2fba4c2ce0b907879932aebf AS build
WORKDIR /src
RUN apk add --no-cache ca-certificates python3
COPY go.mod versions.json ./
COPY cmd ./cmd
COPY internal ./internal
COPY scripts/fetch_core.py ./scripts/fetch_core.py
ARG TARGETOS
ARG TARGETARCH
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -trimpath -ldflags="-s -w" -o /artifacts/vpn-gateway ./cmd/gateway \
 && python3 scripts/fetch_core.py --arch ${TARGETARCH} --dest /artifacts/sing-box

FROM alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf
RUN apk add --no-cache ca-certificates \
 && addgroup -g 10001 -S gateway \
 && adduser -u 10001 -S -G gateway -H -s /sbin/nologin gateway
COPY --from=build /artifacts/vpn-gateway /usr/local/bin/vpn-gateway
COPY --from=build /artifacts/sing-box /usr/local/bin/sing-box
COPY LICENSE THIRD_PARTY_NOTICES.md /usr/share/licenses/ozgurag/
USER 10001:10001
ENV PORT=10000 CORE_PORT=10001
EXPOSE 10000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 CMD ["/usr/local/bin/vpn-gateway", "healthcheck"]
ENTRYPOINT ["/usr/local/bin/vpn-gateway"]
CMD ["serve"]
