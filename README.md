# Forekto

A multi-sport prediction & analytics platform. Each sport is a self-contained
ML module behind a shared platform shell, built on the same production stack:
Flask + gunicorn, Docker, Kubernetes on AWS EKS, Terraform, GitHub Actions.

See the build roadmap for the full plan. Current state: **Phase 1 — first ML
module (horse racing)**.

## Layout

```
modules/
  horse-racing/     first sport module (ML core + Flask serving)
platform/           the shell: API gateway, web UI, accounts, dashboard (later)
infra/              Terraform + Kubernetes manifests (later)
.github/workflows/  CI/CD pipelines (later)
```

## Getting started

```bash
cd modules/horse-racing
python3 -m venv .venv && source .venv/bin/activate
make install && make sample-data && make train && make test && make run
```

See `modules/horse-racing/README.md` for details.
