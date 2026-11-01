# attacker-bot: ONE container for the whole room (plan §8.2). No docker socket - it reaches
# each student's target the same way their own terminal does, over `ctf_net`'s published ports
# on ctf-host, and posts straight to achievements over `workshop_lab` (same trust tier as
# ctf-flags: it holds the adapter secret, but no student can ever reach it). See bot.py's
# header comment for the roster/addressing math.
#
# Context is the module root (../modules/ctf-range) so this can COPY the exact exploit payload
# target 14 uses, so the bot and the CI gate can never disagree about what "patched" means.
FROM docker.io/library/python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

COPY attacker-bot/bot.py attacker-bot/personas.py attacker-bot/probes.py attacker-bot/traffic.py attacker-bot/multi.py /app/
COPY attacker-bot/_shared/ /app/_shared/
COPY targets/customer-portal/exploit/dump.py /app/exploit/dump.py
WORKDIR /app

RUN useradd --uid 10018 --no-create-home --home-dir /app --shell /usr/sbin/nologin attacker-bot
USER attacker-bot

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/app/bot.py"]
