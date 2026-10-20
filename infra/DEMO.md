# Phase 3 — Infrastructure, and a $0 live demo

Two things live here:

1. **`infra/terraform/`** — the real AWS design (VPC, EKS, ECR). You **review
   and talk through** this; you do **not** `terraform apply` it, so it costs
   nothing. This is your "here's my Infrastructure-as-Code" artefact.
2. **`infra/k8s/`** — Kubernetes manifests (Namespace, Deployment, Service,
   HPA, health probes) that run **unchanged** on EKS *or* on a **free local
   cluster**. This is how you show it actually running on Kubernetes.

The manifests are the same either way — that's the whole point. You demo
locally for free, and the exact same YAML would deploy to the EKS cluster the
Terraform defines.

---

## A. The $0 live demo (kind — Kubernetes in Docker)

Shows an interviewer: a real cluster, 2 pods, a Service, liveness/readiness
probes, and autoscaling — all on your laptop, no AWS, no cost.

### One-time install
- **Docker Desktop** (you already have Docker)
- **kubectl** — https://kubernetes.io/docs/tasks/tools/
- **kind** — https://kind.sigs.k8s.io/docs/user/quick-start/#installation

### Steps (run from the repo root `forekto/`)

```bash
# 1. Build the app image (trains a model into the image first)
cd modules/horse-racing
make sample-data && make train          # or use your real Kaggle-trained model
docker build -t forekto-horse-racing:local .
cd ../..

# 2. Create a free local cluster
kind create cluster --config infra/local/kind-config.yaml

# 3. Load your image into the cluster (no registry needed)
kind load docker-image forekto-horse-racing:local --name forekto

# 4. Deploy everything
kubectl apply -k infra/k8s

# 5. Watch the pods come up (Running + READY 1/1 = readiness probe passed)
kubectl -n forekto get pods -w

# 6. Reach the app
kubectl -n forekto port-forward svc/horse-racing 8080:80
# open http://localhost:8080
```

### Show the probes and autoscaling (the good interview bits)

```bash
# Probes: describe a pod and point at Liveness/Readiness
kubectl -n forekto describe pod -l app.kubernetes.io/name=horse-racing

# HPA needs metrics-server in kind (one command):
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
# then allow insecure kubelet TLS (kind only):
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'

kubectl -n forekto get hpa          # shows CPU % and replica count 2..6
```

### Tear down (frees everything)

```bash
kind delete cluster --name forekto
```

---

## B. The AWS Terraform (review-only, never applied)

```bash
cd infra/terraform
terraform init      # downloads providers/modules — safe, free, no AWS needed
terraform fmt       # format check
terraform validate  # syntax + internal consistency — free, no AWS call
# terraform plan / apply  <-- NOT run: these need AWS creds and cost money
```

`init` + `validate` prove the code is correct without spending anything. You
can show an interviewer the plan of what it *would* build: a VPC with public and
private subnets across two AZs, a single NAT gateway, an EKS cluster with a
managed node group in the private subnets, and an ECR repo with image scanning
and a 10-image lifecycle policy.

### How to talk about it (honest and strong)
> "The AWS infrastructure is fully written as Terraform — VPC, EKS, ECR — and
> validates cleanly. I didn't stand up a live cluster because an EKS control
> plane and nodes cost real money and this is a personal project. To demo it
> actually running on Kubernetes, I apply the **same manifests** to a local kind
> cluster — so you can see the pods, the Service, the health probes and the HPA
> working, at no cost."

That cost-awareness reads as an operational strength, not a gap.

---

## What maps to what

| Local (kind, free) | AWS (Terraform, on demand) |
| --- | --- |
| kind cluster | EKS cluster + managed node group |
| `kind load docker-image` | push to ECR |
| `port-forward` | Ingress / ALB |
| metrics-server manifest | EKS metrics-server add-on |
| same `infra/k8s` manifests | same `infra/k8s` manifests |
