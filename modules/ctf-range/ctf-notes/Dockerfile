# ctf-notes: the Notes page, a browser editor for ~/lab/notes.md in a student's terminal home.
# Stdlib Python, nothing to install. It runs as root INSIDE the container with only the two
# capabilities it needs (DAC_OVERRIDE to open a 0700 home, CHOWN to hand a new file to its owner);
# notes.py walks the path with O_NOFOLLOW and checks ownership, so a symlink in a student's home
# cannot point it at someone else's file.
FROM docker.io/library/python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

COPY notes.py /app/notes.py
COPY static/ /app/static/
COPY _shared/ /app/_shared/
WORKDIR /app

ENV PYTHONUNBUFFERED=1
EXPOSE 9300
ENTRYPOINT ["python3", "/app/notes.py"]
