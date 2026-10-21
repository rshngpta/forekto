# Forekto

A multi-sport **prediction & analytics platform**, built as a production-style
MLOps project. Two independent ML services — a **horse-race win predictor** and
a **football 1X2 predictor** — sit behind a **gateway** that gives users one
site with a sport switch. Every prediction is stored and scored on an honest,
out-of-sample **accuracy dashboard**.

The project demonstrates the full path from model to running service:
containerisation, Kubernetes, Infrastructure-as-Code, CI/CD, a database, and a
microservices gateway.

---

## Architecture

```
                      Browser
                         │
                 Gateway (:8000)                  ← one page, sport switch
                 /api/horse/*   /api/football/*     + combined dashboard
                    │                │
     horse-racing (:8080)     football (:8081)     ← independent ML services
          │                        │
          └──────── shared ────────┘
              PostgreSQL / SQLite                  ← stored predictions + outcomes
```

Each sport is its own containerised service. The gateway proxies to the right
backend, so adding a sport is: add a module, add one line to the gateway's
backend map.

## Tech stack

| Layer | Technology |
| --- | --- |
| Models | scikit-learn — RandomForest (binary win / 3-class 1X2) |
| API | Flask + gunicorn (Python 3.12) |
| Gateway | Flask reverse proxy (sport switch + API routing) |
| Database | SQLAlchemy — SQLite (local) / PostgreSQL (prod) |
| Container | Docker (multi-stage, non-root) |
| Orchestration | Kubernetes (Deployment, Service, HPA, health probes) |
| Infrastructure as Code | Terraform (AWS VPC, EKS, ECR) |
| CI/CD | GitHub Actions (flake8, pytest, Docker build, Trivy scan) |

## The ML

- **Horse racing** — predicts each runner's win probability, ranks the field.
  Target `won` (~8% winners), so it reports PR-AUC, ROC-AUC and a race-level
  top-1 hit rate vs the market favourite, split by whole races to avoid leakage.
- **Football** — predicts the 1X2 outcome (Home / Draw / Away) from form, rank
  and odds. 3-class model; reports accuracy, log loss and top-1 hit rate vs the
  favourite, with a time-based split.
- Both produce a **ranked set of outcomes with calibrated probabilities**, so
  they share one database and one accuracy dashboard.
- Each module's `features.py` is imported by both training and serving — no
  training/serving skew.

## Repository layout

```
modules/horse-racing/   ML module: win predictor (Flask + model + tests)
modules/football/       ML module: 1X2 predictor (same shape)
platform/gateway/       unified page + API proxy to both services
infra/terraform/        AWS design — VPC, EKS, ECR (written & validated)
infra/k8s/              horse-racing Kubernetes manifests
infra/k8s-football/     football manifests
infra/k8s-gateway/      gateway manifest
infra/local/            kind config; DEMO.md — zero-cost local K8s
.github/workflows/      CI (ci.yaml) and CD (cd.yaml)
```

## Run it locally (3 terminals)

```bash
# 1 — horse racing
cd modules/horse-racing && pip install -r requirements.txt
make sample-data && make train && make seed && python -m app.main   # :8080

# 2 — football
cd modules/football && pip install -r requirements.txt
make sample-data && make train && make seed && python -m app.main   # :8081

# 3 — gateway
cd platform/gateway && pip install -r requirements.txt && python -m app.main   # :8000
```

Open **http://localhost:8000** — switch sports at the top, predict, and view the
shared accuracy dashboard at **/dashboard**.

## Run on Kubernetes (free, local)

Docker Desktop's built-in Kubernetes (or kind — see `infra/DEMO.md`):

```bash
docker build -t forekto-horse-racing:local modules/horse-racing
docker build -t forekto-football:local modules/football
docker build -t forekto-gateway:local platform/gateway
kubectl apply -k infra/k8s
kubectl apply -f infra/k8s-football/football.yaml
kubectl apply -f infra/k8s-gateway/gateway.yaml
kubectl -n forekto get pods
kubectl -n forekto port-forward svc/gateway 8000:80   # http://localhost:8000
```

## CI/CD & Infrastructure

- **CI** runs on every push: flake8 → pytest → Docker build → Trivy scan.
- **CD** builds, pushes to ECR and deploys to EKS via GitHub OIDC (no stored
  keys); manual until a cluster exists.
- The AWS Terraform is fully written and validates cleanly. A live cluster is
  **not** stood up (EKS costs money); the identical manifests are demonstrated
  on a local cluster instead. See `infra/DEMO.md`.

## Notes

- `data/*.csv`, `model/*.pkl` and local `*.db` files are gitignored; CI
  regenerates a model from synthetic data.
- Predictions are a machine-learning demonstration, **not betting advice**.

## Roadmap

- [x] Horse-racing ML module + web UI
- [x] Docker + CI/CD pipeline
- [x] Terraform + Kubernetes, running locally
- [x] Database + honest accuracy dashboard
- [x] Second sport (football)
- [x] Gateway — one site, sport switch, API routing
- [ ] User accounts · observability · public API
