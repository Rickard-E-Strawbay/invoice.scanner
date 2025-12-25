# GitHub Setup - Branch Protection & CI/CD

## 🔒 GitHub Branch Protection Rules

För att använda det nya PR-baserade CI/CD pipelinen behöver du sätta upp Branch Protection Rules.

### Step 1: Skydda `re_deploy_start` branch (TEST environment)

1. Gå till **Settings** → **Branches** → **Add rule**
2. Branch name pattern: `re_deploy_start`
3. Sätt följande:
   - ✅ **Require a pull request before merging**
   - ✅ **Require approvals**: 1
   - ✅ **Dismiss stale pull request approvals when new commits are pushed**
   - ✅ **Require status checks to pass before merging**
     - Select: `Build Docker Images` (build.yml)
   - ✅ **Allow force pushes**: ❌ NO
   - ✅ **Allow deletions**: ❌ NO

4. Click **Create**

### Step 2: Skydda `main` branch (PROD environment) - MER STRIKT

1. Gå till **Settings** → **Branches** → **Add rule**
2. Branch name pattern: `main`
3. Sätt följande:
   - ✅ **Require a pull request before merging**
   - ✅ **Require approvals**: 2 (eller 1 för enklare setup)
   - ✅ **Dismiss stale pull request approvals when new commits are pushed**
   - ✅ **Require status checks to pass before merging**
     - Select: `Build Docker Images` (build.yml)
   - ✅ **Require branches to be up to date before merging**
   - ✅ **Require a pull request before merging**
   - ✅ **Allow force pushes**: ❌ NO
   - ✅ **Allow deletions**: ❌ NO
   - ✅ **Restrict who can push to matching branches** (optional)
     - Du kan begränsa till bara admins

4. Click **Create**

---

## 🔐 GitHub Environments (för PROD approval gate)

En "environment" i GitHub Actions är en säkerhetsgräns som kan kräva manual approval.

### Step 1: Skapa "test" environment (om den inte finns)

1. Gå till **Settings** → **Environments** → **New environment**
2. Name: `test`
3. Click **Configure environment**
4. Du kan lämna den tom - den är bara för organisering
5. Click **Save** (eller X för att stänga)

### Step 2: Skapa "production" environment (kräver approval)

1. Gå till **Settings** → **Environments** → **New environment**
2. Name: `production`
3. Click **Configure environment**
4. ✅ **Required reviewers**: Lägg till dig själv eller team
5. ✅ **Deployment branches and tags**
   - Select: **Protected branches only** (eller **Selected branches**)
   - Branches: `main`
6. ✅ **Timeout (minutes)**: 1440 (24 timmar) - eller din preferens
7. Click **Save**

---

## 🚀 Workflow EFTER att rules är setup

### Scenario 1: Deploy till TEST

```bash
# Developer
git checkout -b feature/my-feature
# ... make changes ...
git push origin feature/my-feature

# GitHub: Creates PR
# Reviewer: Reviews code → Clicks "Approve" → Merges PR

# Automatic:
# - build.yml starts (triggered by push to re_deploy_start)
# - Builds Docker images
# - Pushes to TEST Artifact Registry
# - test-deploy.yml starts
# - Deploys to TEST Cloud Run
# - ✅ TEST environment is live!
```

### Scenario 2: Deploy till PROD

```bash
# Developer creates PR main <- re_deploy_start
# GitHub: Shows status check (build.yml must pass)
# Reviewer: Reviews PR → Clicks "Approve" → Merges

# Automatic:
# - build.yml starts (triggered by push to main)
# - Builds Docker images
# - Pushes to PROD Artifact Registry
# - prod-deploy.yml starts
# - ⚠️ WAITS for approval (GitHub environment: production)
# - Your GitHub environment approver sees notification
# - Clicks "Approve" deployment
# - Deploys to PROD Cloud Run
# - ✅ PROD environment is live!
```

---

## 📋 Checklist

Innan du börjar testa:

- [ ] Branch protection rule för `re_deploy_start` är setup
- [ ] Branch protection rule för `main` är setup
- [ ] GitHub environment `test` exists (om du vill använda den)
- [ ] GitHub environment `production` exists med required reviewer
- [ ] Du har pushed nya workflows (build.yml, test-deploy.yml, prod-deploy.yml)
- [ ] Du har backupat gamla workflows (.bak filer)

---

## ✅ Verifikation

### Test att allt fungerar:

1. **Create test PR:**
   ```bash
   git checkout -b test/ci-workflow
   echo "# Test" >> README.md
   git push origin test/ci-workflow
   ```

2. **Gå till GitHub och skapa PR mot re_deploy_start**

3. **Godkänn PR:en**

4. **Merga PR:en**

5. **Gå till GitHub Actions och se:**
   - build.yml startar ✅
   - Builds Docker images ✅
   - test-deploy.yml startar ✅
   - Deployer till TEST Cloud Run ✅

6. **Om allt fungerar:** TEST är live! 🎉

---

## 🆘 Troubleshooting

**Issue: PR kan inte mergas - "This branch has 1 failing check"**
- build.yml körs inte eller failat
- Lösning: Se till att build.yml är grön innan merge

**Issue: Workflows är fortfarande inaktiva efter push**
- De gamla .bak-filerna kanske fortfarande tolkas som workflows
- Lösning: Gå till GitHub Actions → Ta bort gammal run-historia

**Issue: prod-deploy.yml väntar på approval men ingen notification**
- Du kanske inte är satt som approver i production environment
- Lösning: Gå till Settings → Environments → production → Check Required reviewers

---

## 📚 Mer info

- [GitHub Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/about-environments)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
