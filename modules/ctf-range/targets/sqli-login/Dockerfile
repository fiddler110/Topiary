# sqli-login — CTF target 0 (plan §7.3, CTF-1 "Access and identity"). A
# single deliberately-vulnerable Flask app with no second stage — see
# app.py's module docstring for the bug and the flag.
#
# Unlike targets/customer-portal, this image has no ctf-host-side base-image
# dependency to stay in sync with: ctf-builder never rebuilds an attack-ladder
# target (students here don't patch and redeploy, they only attack it), so
# there's no offline-rebuild constraint (CTF-D24) to design around — a plain
# pinned base plus this image's own tiny requirements.txt is enough.
FROM docker.io/library/python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app.py sshshell.py /app/
COPY assets/ /app/assets/

# Fixed high uid, no home, no login — same convention as customer-portal,
# a different uid so the two never collide if ever run on the same host
# outside a container (they never are, but it costs nothing to keep distinct).
RUN useradd --uid 10015 --no-create-home --home-dir /app --shell /usr/sbin/nologin sqli

ENV PORT=5000 \
    PYTHONUNBUFFERED=1
# 2222 is the SSH service (sshshell.py: a real SSH server, emulated shell); the host publishes it as 22.
# §7.3's nmap primer) — see its module-bottom comment. Not a real sshd.
EXPOSE 5000 2222 2121 8081

USER sqli
WORKDIR /app
ENTRYPOINT ["python3", "/app/app.py"]
