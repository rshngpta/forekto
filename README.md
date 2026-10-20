# Forekto

A multi-sport **prediction & analytics platform**, built as a production-style
MLOps project. The first module is a **horse-race win predictor**: it scores a
race's field with a machine-learning model and returns a ranked set of win
probabilities, served over a Flask API and deployed on Kubernetes.

The project demonstrates a full path from model to running service —
containerisation, Kubernetes, Infrastructure-as-Code and CI/CD — using the same
tools a platform team would use in production.

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Model | scikit-learn — `RandomForestClassifier` |
| API | Flask + gunicorn (Python 3.12) |
| Container | Docker (multi-stage, non-root) |
| Orchestration | Kubernetes (Deployment, Service, HPA, health probes) |
| Infrastructure as Code | Terraform (AWS VPC, EKS, ECR) |
| CI/CD | GitHub Actions (flake8, pytest, Docker build, Trivy scan) |
| Registry | Amazon ECR |

---

## Architecture

```
Client ──▶ Kubernetes Service ──▶ Pod (gunicorn → Flask)
                                     │
                                     ├─ features.py  (raw race → feature vector)
                                     └─ model.py     (RandomForest → win probability)
                                     ▼
                         Ranked field returned as JSON / HTML
```

The same `features.py` is imported by **both** the training script and the live
app, so the features the model learns on and predicts on are identical by
construction — this designs out **training/serving skew**.

---

## The ML

- **Data:** the public Hong Kong racing dataset (`races.csv` + `runs.csv`),
  joined on `race_id`.
- **Target:** `won` (1 = winner) — a binary classification problem.
- **Imbalance:** only ~8% of runners win, so training uses
  `class_weight="balanced"` and evaluation reports **PR-AUC**, **ROC-AUC** and a
  race-level **top-1 hit rate** (plus favourite and random baselines) rather
  than accuracy.
- **No leakage:** train/test split is done by whole races (`GroupShuffleSplit`),
  so no race appears in both sets.
- **Reproducible:** `ml/train.py` retrains from the CSVs and writes
  `model/horse_rf.pkl` + `model/metadata.json`.

---

## Repository layout

```
modules/horse-racing/     the first sport module
  app/        Flask app + model serving (features.py, model.py, main.py, wsgi.py)
  ml/         training + sample-data scripts
  tests/      unit + API tests
  Dockerfile  multi-stage, non-root image
infra/
  terraform/  AWS design — VPC, EKS, ECR (written & validated, not applied)
  k8s/        Namespace, Deployment, Service, HPA, probes
  local/      kind cluster config for a free local demo
  DEMO.md     zero-cost local Kubernetes walkthrough
.github/workflows/  CI (ci.yaml) and CD (cd.yaml)
```

---

## Run it locally

```bash
cd modules/horse-racing
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
make sample-data    # or drop the real Kaggle races.csv + runs.csv into data/
make train          # trains the model, prints metrics
make test           # 9 tests
make run            # http://localhost:8080
```

### Run on Kubernetes (free, local)

Using Docker Desktop's built-in Kubernetes (or kind — see `infra/DEMO.md`):

```bash
docker build -t forekto-horse-racing:local modules/horse-racing
kubectl apply -k infra/k8s
kubectl -n forekto get pods
kubectl -n forekto port-forward svc/horse-racing 8090:80   # http://localhost:8090
```

---

## CI/CD

- **CI** (`ci.yaml`) runs on every push/PR: flake8 → pytest → Docker build →
  Trivy image scan.
- **CD** (`cd.yaml`) builds, pushes to ECR and deploys to EKS, authenticating
  via **GitHub OIDC** (no long-lived AWS keys). Manual trigger until a cluster
  exists.

## Infrastructure

The AWS infrastructure is fully written as Terraform (VPC with public/private
subnets, EKS cluster + managed node group, ECR) and validates cleanly. A live
cluster is **not** stood up, because EKS bills real money and this is a personal
project — the identical Kubernetes manifests are demonstrated on a **local
cluster** instead. See `infra/DEMO.md`.

---

## Notes

- `data/*.csv` and `model/*.pkl` are gitignored (dataset licensing + file size);
  CI regenerates a model from synthetic data.
- Predictions are a machine-learning demonstration, **not betting advice**.

## Roadmap

- [x] Horse-racing ML module + web UI
- [x] Docker + CI/CD pipeline
- [x] Terraform + Kubernetes, running locally
- [ ] Platform shell: API gateway, Postgres, accuracy dashboard, accounts
- [ ] Second sport (football) + observability
