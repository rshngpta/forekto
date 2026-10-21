# Forekto — Platform Gateway

The unified front door. Serves **one web page** with a Horse Racing ⇄ Football
switch, and **proxies** API calls to the two backend module services. Users see
a single site; each sport stays its own independent service.

```
  Browser ──▶ Gateway (:8000)
                 │  /api/horse/*     ──▶ horse-racing (:8080)
                 │  /api/football/*  ──▶ football (:8081)
```

## Run locally (3 terminals)

```bash
# Terminal 1 — horse racing
cd modules/horse-racing && python -m app.main            # :8080

# Terminal 2 — football
cd modules/football && python -m app.main                # :8081

# Terminal 3 — gateway
cd platform/gateway && pip install -r requirements.txt && python -m app.main   # :8000
```

Open **http://localhost:8000** — one page, switch sports at the top. The
accuracy dashboard is at **/dashboard** (also sport-switchable).

## Configuration

Backends are set by env vars (defaults suit local dev):

| Var | Local default | In Kubernetes |
| --- | --- | --- |
| `HORSE_URL` | http://localhost:8080 | http://horse-racing |
| `FOOTBALL_URL` | http://localhost:8081 | http://football |

## Why a gateway (interview point)

Each sport is an independent, separately-deployable service. The gateway gives
users one site and one API surface, and routes to the right backend — a real
microservices / API-gateway pattern. Adding a sport = add a module + one line
in the gateway's backend map.
