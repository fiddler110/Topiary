# ctf-flags — the flag submission service (plan §5). Pure stdlib Python,
# nothing to install and no network at build time. Holds a secret
# (STUDENT_PASSWORD_SEED) but no capability: no socket, no volume beyond its
# own code, reachable only on workshop_lab.
FROM docker.io/library/python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

COPY service.py flags.py /app/
COPY _shared/ /app/_shared/
WORKDIR /app

RUN useradd --uid 10016 --no-create-home --home-dir /app --shell /usr/sbin/nologin ctf-flags
USER ctf-flags

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
ENTRYPOINT ["python3", "/app/service.py"]
