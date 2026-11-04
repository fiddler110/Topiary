"""Identity for Dojo WAN: who owns which token and which org.

Every roster member (studentNN, testuserN demo bots, the facilitator) has one API token and one org, both derived
from the signing key by wan_ids.py. The terminal-side broker hands each Linux user only their own values; this side
recomputes them to check a request. The signing key lives in a root-only file in the wan_secrets volume.
"""
import hmac

import wan_ids


def roster(env):
    """All usernames that hold credentials, named exactly as the engine and the terminal broker name them:
    students zero-padded to two digits (student01), demo bots not padded (testuser1), then the facilitator."""
    users = []
    for prefix_var, count_var, default_prefix, pad in (("STUDENT_PREFIX", "STUDENT_COUNT", "student", "02d"),
                                                       ("BOT_PREFIX", "BOT_COUNT", "testuser", "d")):
        prefix = env.get(prefix_var, default_prefix)
        try:
            count = int(env.get(count_var, "0") or 0)
        except ValueError:
            count = 0
        users += [f"{prefix}{n:{pad}}" for n in range(1, count + 1)]
    fac = env.get("FACILITATOR_USERNAME", "root")
    if fac and fac not in users:
        users.append(fac)
    return users


class Auth:
    def __init__(self, key, users, facilitator):
        self.key = key
        self.users = list(users)
        self.facilitator = facilitator
        self.tokens = [(wan_ids.api_token(key, u), u) for u in self.users]
        self.org_of = {u: wan_ids.org_id(key, u) for u in self.users}
        self.user_of_org = {o: u for u, o in self.org_of.items()}

    def is_facilitator(self, user):
        return bool(self.facilitator) and user == self.facilitator

    def user_for_token(self, token):
        """The user a token belongs to, else None. Compares against every token in constant time per token."""
        found = None
        for tok, user in self.tokens:
            if hmac.compare_digest(tok.encode(), (token or "").encode()):
                found = user
        return found

    def can_access_org(self, user, org_id):
        return self.is_facilitator(user) or self.org_of.get(user) == org_id

    def orgs_for(self, user):
        """[{"id", "name", "user"}] the user may see: their own org, or every org for the facilitator."""
        users = self.users if self.is_facilitator(user) else [user]
        return [{"id": self.org_of[u], "name": f"Dojo Org {u}", "user": u} for u in sorted(users)]
