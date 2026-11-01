# One-shot: creates the certs.dojo.test zone on dns-server and one A
# record per configured student pointing at demo-app, via PowerDNS's HTTP
# API. See seed.sh. Runs every `docker compose up`; idempotent.
FROM docker.io/library/alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a

RUN apk add --no-cache curl jq

COPY seed.sh /seed.sh
RUN chmod +x /seed.sh

ENTRYPOINT ["/seed.sh"]
