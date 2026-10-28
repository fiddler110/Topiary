"""netlab verifier verbs (see verifiers.json). Stdlib only. Every verb is `fn(api, args, ctx) -> (passed, message)`.
`api` is the Forgejo client the runner passes to every verb; these ignore it.

The proof is the netlab-checker's own record of its last run per lab (POST /proof, authenticated with
NETLAB_PROOF_TOKEN, which only this service and the checker hold; student terminals never get it). The pod is
found by the checker from the user name, so no argument can name another student's pod."""
import json
import os
import urllib.error
import urllib.request


class Unavailable(Exception):
    """The netlab checker couldn't be asked (try again)."""


def _ask(user, labs):
    base, token = os.environ.get("NETLAB_CHECKER_URL", ""), os.environ.get("NETLAB_PROOF_TOKEN", "")
    if not base or not token:
        raise Unavailable("no NETLAB_CHECKER_URL or NETLAB_PROOF_TOKEN set")
    req = urllib.request.Request(f"{base.rstrip('/')}/proof", json.dumps({"user": user, "labs": labs}).encode(),
                                 {"X-Netlab-Proof-Token": token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise Unavailable(f"the netlab checker answered {e.code}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise Unavailable(f"the netlab checker isn't reachable ({e.__class__.__name__})")


def netlab_labs_passed(api, args, ctx):
    if "user" in args and args["user"] != ctx["user"]:
        return False, "this check reads only your own pod"
    labs = args.get("labs")
    if not isinstance(labs, list) or not labs or not all(isinstance(x, str) for x in labs):
        return False, "no labs named"
    doc = _ask(ctx["user"], [str(x) for x in labs])
    if doc.get("passed") is True:
        return True, "ok"
    missing = doc.get("missing") or []
    return False, "the checker has not seen these labs pass on your pod yet: " + ", ".join(str(m) for m in missing)


VERBS = {"netlab_labs_passed": netlab_labs_passed}
