# Dojo WAN control plane (a simulated Mist API). Stdlib-only Python plus openssl (private CA).
FROM docker.io/library/python:3.14-alpine@sha256:f6a589d43c42b9e7f7dc67a12d37132491f362859a5d750607710cc56da3bc72
RUN apk add --no-cache openssl
WORKDIR /app
COPY wan_ids.py auth.py store.py pki.py tfstate.py mist_api.py portal_api.py renderer.py server.py /app/
# The Dojo WAN portal (static files, served by portal_api.py from PORTAL_DIR, default /app/portal).
COPY portal/ /app/portal/
# Unit tests ride along so `podman exec ... python -m unittest` works in the image. test_contract.py needs terraform
# and the provider, which are not here, so it skips.
COPY wan_testlib.py test_store.py test_api.py test_tfstate.py test_portal.py test_server.py test_contract.py /app/
ENV PYTHONUNBUFFERED=1
# Runs as root on purpose: the signing key in the wan_secrets volume is 0600 and the terminal's root broker reads it, and
# :443 needs NET_BIND_SERVICE (the provider connects to https://api.mist.com with no port). The compose overlay drops
# every other capability. The CA's private key stays in /data/pki; only ca.crt goes to the shared /pki volume.
EXPOSE 443 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/readyz || exit 1
CMD ["python3", "/app/server.py"]
