# netlab-checker (see checker.py). Stdlib Python; reaches the pod nodes with sshpass + ssh over netlab_mgmt.
FROM docker.io/library/python:3.14-alpine@sha256:f6a589d43c42b9e7f7dc67a12d37132491f362859a5d750607710cc56da3bc72
RUN apk add --no-cache openssh-client sshpass
WORKDIR /app
COPY checker.py /app/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER nobody
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
CMD ["python3", "/app/checker.py"]
