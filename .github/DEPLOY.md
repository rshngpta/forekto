# CI/CD — how the pipeline works and how to set it up

Forekto ships through **GitHub Actions**. There are two workflows in
`.github/workflows/`:

| Workflow | When it runs | What it does |
| --- | --- | --- |
| `ci.yaml` | every push / PR to `main` | flake8 → pytest → docker build → Trivy scan |
| `cd.yaml` | manual (button) for now | build → push to ECR → deploy to EKS |

## CI — works immediately, no setup

As soon as you push this repo to GitHub, `ci.yaml` runs on its own. It needs
**no secrets and no AWS** — it lints, tests, builds the Docker image, and scans
it with Trivy on GitHub's runners. You'll see a green check on each commit.

To push the repo the first time:

```bash
cd forekto
git init
git add .
git commit -m "Forekto: horse-racing module + CI"
git branch -M main
git remote add origin https://github.com/<you>/forekto.git
git push -u origin main
```

Then open the **Actions** tab on GitHub to watch the CI run.

### Notes on CI
- **Trivy is set to report, not block** (`exit-code: "0"`). Base-image CVEs are
  often outside your control, so the scan surfaces them without failing the
  build. To make vulnerabilities a hard gate, change `exit-code` to `"1"` in
  `ci.yaml`.
- The build job trains a model from **synthetic** data so the image has a
  `model/horse_rf.pkl` without needing the Kaggle dataset in CI.

## CD — needs AWS, run it only when you want a live cluster

`cd.yaml` is **manual** (`workflow_dispatch`) on purpose, so it never fails
before your AWS infrastructure exists. You'll enable it in Phase 3 once
Terraform has created the VPC, EKS cluster and ECR repo.

When you're ready, the one-time setup is:

1. **Create the ECR repo and EKS cluster** (Phase 3, via Terraform).
2. **Create an IAM role for GitHub OIDC** — a role GitHub Actions can assume
   with no stored keys. Trust policy allows
   `token.actions.githubusercontent.com` for your repo; permissions allow ECR
   push and EKS deploy.
3. **Add the role ARN as a repo secret** named `AWS_DEPLOY_ROLE_ARN`
   (Settings → Secrets and variables → Actions).
4. **Adjust the env block** in `cd.yaml` (`AWS_REGION`, `ECR_REPOSITORY`,
   `EKS_CLUSTER`, `K8S_NAMESPACE`) to match what Terraform created.
5. Either click **Run workflow** in the Actions tab, or uncomment the `push:`
   trigger at the top of `cd.yaml` to deploy automatically on every push.

### Why OIDC (worth saying in an interview)
GitHub Actions assumes a short-lived IAM role via OpenID Connect instead of
storing long-lived AWS access keys in GitHub. Nothing secret sits in the repo,
and the credentials expire after each run.
