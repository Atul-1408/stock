"""Endpoint auditor for the stock project.  Run from the repo root:

    FLASK_ENV=testing ENABLE_BACKGROUND_WORKERS=false python endpoint_audit.py

Checks every Flask route for: (1) open access without a token, (2) 500s on `null`
and malformed JSON bodies, (3) 500s on authenticated empty-object bodies.
Uses a throw-away SQLite file, never your real database.
"""
import os, re, sys, tempfile

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("ENABLE_BACKGROUND_WORKERS", "false")
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "audit.db")
os.environ.setdefault("JWT_SECRET_KEY", "audit-secret-key-that-is-at-least-32-chars!!")
sys.path.insert(0, "src")

import app as A  # noqa: E402

A.limiter.enabled = False
A.app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
c = A.app.test_client()
SKIP = ("/static", "/<path:path>", "/dist/")

def url_for(rule):
    return re.sub(r"<(?:int:)?[a-z_]+>", "1", rule)

rules = [(r, m) for r in A.app.url_map.iter_rules() if not r.rule.startswith(SKIP) and r.rule != "/"
         for m in sorted(r.methods - {"HEAD", "OPTIONS"})]

print("== 1. Routes reachable WITHOUT a token (review each: should it be public?) ==")
for r, m in sorted(rules, key=lambda x: x[0].rule):
    s = c.open(url_for(r.rule), method=m, json={} if m in ("POST", "PUT") else None).status_code
    if s != 401:
        print(f"  OPEN  {m:6} {r.rule:42} -> {s}")

d = c.post("/api/auth/signup", json={"email": "audit@example.com", "password": "Passw0rd!!", "username": "audit"}).get_json()
H = {"Authorization": f"Bearer {d['access_token']}"}

print("\n== 2. 500 errors on bad bodies (authenticated) ==")
bad = 0
for r, m in sorted(rules, key=lambda x: x[0].rule):
    if m not in ("POST", "PUT", "DELETE") or r.rule.startswith("/api/auth/"):
        continue
    for label, kw in (("null", dict(data="null", content_type="application/json")),
                      ("{bad", dict(data="{bad", content_type="application/json")),
                      ("{}", dict(json={}))):
        s = c.open(url_for(r.rule), method=m, headers=H, **kw).status_code
        if s >= 500:
            bad += 1
            print(f"  500   {m:6} {r.rule:42} body={label}")
print(f"\nTotal 500s on bad input: {bad}  (target: 0)")
