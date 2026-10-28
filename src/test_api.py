import json
import urllib.error
import urllib.request

URL = "http://127.0.0.1:8000"


def post(payload):
    req = urllib.request.Request(f"{URL}/score", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


cases = {
    "drains whole balance (TRANSFER)": {"type": "TRANSFER", "amount": 803441.0, "old_bal_org": 803441.0, "old_bal_dest": 0.0},
    "drains whole balance (CASH_OUT)": {"type": "CASH_OUT", "amount": 69040.0, "old_bal_org": 69040.0, "old_bal_dest": 250000.0},
    "small slice of a big balance":    {"type": "CASH_OUT", "amount": 25102.0, "old_bal_org": 1000000.0, "old_bal_dest": 50000.0},
    "sender balance is zero":          {"type": "TRANSFER", "amount": 5000.0, "old_bal_org": 0.0, "old_bal_dest": 0.0},
    "invalid type (expect 422)":       {"type": "PAYMENT", "amount": 100.0, "old_bal_org": 500.0, "old_bal_dest": 0.0},
}

with urllib.request.urlopen(f"{URL}/health") as r:
    print("health:", json.loads(r.read()))

for name, payload in cases.items():
    status, body = post(payload)
    print(f"\n{name}\n  HTTP {status}: {body}")