"""Private CA + server certificate for the Dojo WAN API (api.mist.com inside the lab).

Both private keys stay in wan-api's own data dir. Only the CA certificate goes to the shared wan_pki volume, which
terminals mount read-only and add to their trust store (so a student can never read a key that signs for api.mist.com).
Shells out to openssl, which the Dockerfile installs.
"""
import os
import shutil
import subprocess

HOSTS = ("api.mist.com", "wan-api", "localhost")
IPS = ("127.0.0.1",)
DAYS = "365"


def _run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ensure(private_dir, shared_dir):
    """Create what is missing and return (server cert path, server key path). Idempotent."""
    os.makedirs(private_dir, exist_ok=True)
    ca_key, ca_crt = f"{private_dir}/ca.key", f"{private_dir}/ca.crt"
    key, crt = f"{private_dir}/server.key", f"{private_dir}/server.crt"
    if not (os.path.exists(ca_key) and os.path.exists(ca_crt)):
        _run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", ca_key, "-out", ca_crt,
             "-days", DAYS, "-subj", "/CN=Dojo WAN Training CA",
             # Strict verifiers (Python 3.13+) insist on these.
             "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign",
             "-addext", "subjectKeyIdentifier=hash")
        os.chmod(ca_key, 0o600)
        for stale in (key, crt):
            if os.path.exists(stale):
                os.remove(stale)
    if not (os.path.exists(key) and os.path.exists(crt)):
        csr, ext = f"{private_dir}/server.csr", f"{private_dir}/server.ext"
        sans = [f"DNS:{h}" for h in HOSTS] + [f"IP:{i}" for i in IPS]
        with open(ext, "w") as f:
            f.write("subjectAltName=" + ",".join(sans) + "\n")
            f.write("extendedKeyUsage=serverAuth\nkeyUsage=critical,digitalSignature,keyEncipherment\n")
            f.write("basicConstraints=CA:FALSE\nauthorityKeyIdentifier=keyid\nsubjectKeyIdentifier=hash\n")
        _run("openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", csr, "-subj", "/CN=api.mist.com")
        _run("openssl", "x509", "-req", "-in", csr, "-CA", ca_crt, "-CAkey", ca_key, "-CAcreateserial", "-out", crt,
             "-days", DAYS, "-extfile", ext)
        os.chmod(key, 0o600)
    os.makedirs(shared_dir, exist_ok=True)
    shutil.copyfile(ca_crt, f"{shared_dir}/ca.crt")
    os.chmod(f"{shared_dir}/ca.crt", 0o644)
    return crt, key
