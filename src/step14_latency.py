import http.client
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from explain import make_explainer, top_reasons
from serving_features import build_features

ROOT = Path(__file__).resolve().parents[1]
HOST, PORT = "127.0.0.1", 8000  # use 127.0.0.1, not "localhost" (slow IPv6 fallback on Windows)
random.seed(0)


def summarize(name, times_ms, extra=""):
    t = np.array(times_ms)
    print(f"{name:40s} n={len(t):5d} | p50 {np.percentile(t, 50):7.2f} | "
          f"p95 {np.percentile(t, 95):7.2f} | p99 {np.percentile(t, 99):7.2f} | "
          f"max {t.max():8.2f} ms {extra}")


def alert_payload():
    amt = round(random.uniform(10_000, 5_000_000), 2)
    return {"type": random.choice(["TRANSFER", "CASH_OUT"]), "amount": amt,
            "old_bal_org": amt, "old_bal_dest": round(random.choice([0, random.uniform(1e4, 1e6)]), 2)}


def normal_payload():
    bal = round(random.uniform(500_000, 5_000_000), 2)
    return {"type": random.choice(["TRANSFER", "CASH_OUT"]),
            "amount": round(bal * random.uniform(0.001, 0.2), 2),
            "old_bal_org": bal, "old_bal_dest": round(random.uniform(0, 1e6), 2)}


# ---------- Part 1: in-process breakdown (no HTTP) ----------
art = joblib.load(ROOT / "models" / "final_model.joblib")
model = art["model"]
explainer = make_explainer(model)
sample = alert_payload()
X = build_features(pd.DataFrame([sample]))


def time_it(fn, n=500, warm=30):
    for _ in range(warm):
        fn()
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t0) * 1000)
    return out


print("=== Part 1: in-process (no HTTP) ===")
summarize("DataFrame + build_features", time_it(lambda: build_features(pd.DataFrame([sample]))))
summarize("model.predict_proba (1 row)", time_it(lambda: model.predict_proba(X)))
summarize("SHAP top_reasons (1 row)", time_it(lambda: top_reasons(explainer, X), n=200))


# ---------- Part 2: end-to-end HTTP ----------
def post(conn, payload, path):
    t0 = time.perf_counter()
    conn.request("POST", path, body=json.dumps(payload), headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = resp.read()
    ms = (time.perf_counter() - t0) * 1000
    assert resp.status == 200, (resp.status, data[:200])
    return ms, json.loads(data)


def run_sequential(payload_fn, path, n=1000, warm=50):
    conn = http.client.HTTPConnection(HOST, PORT)
    for _ in range(warm):
        post(conn, payload_fn(), path)
    times, alerts = [], 0
    for _ in range(n):
        ms, body = post(conn, payload_fn(), path)
        times.append(ms)
        alerts += body["alert"]
    conn.close()
    return times, alerts


def worker(n):
    conn = http.client.HTTPConnection(HOST, PORT)
    out = [post(conn, normal_payload(), "/score")[0] for _ in range(n)]
    conn.close()
    return out


print("\n=== Part 2: end-to-end HTTP (keep-alive, one client) ===")
try:
    t, a = run_sequential(normal_payload, "/score")
    summarize("normal txn (no alert, no SHAP)", t, f"| alerts {a}/{len(t)}")
    t, a = run_sequential(alert_payload, "/score")
    summarize("alert + SHAP reasons", t, f"| alerts {a}/{len(t)}")
    t, a = run_sequential(alert_payload, "/score?explain=false")
    summarize("alert, explain=false", t, f"| alerts {a}/{len(t)}")

    workers, per_worker = 8, 250
    t0 = time.perf_counter()
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(worker, [per_worker] * workers))
    wall = time.perf_counter() - t0
    times = [x for r in results for x in r]
    summarize(f"normal txn, {workers} concurrent clients", times,
              f"| {workers * per_worker / wall:.0f} req/s")
except ConnectionRefusedError:
    print("Server not running on 127.0.0.1:8000. Start it in another terminal, then rerun.")