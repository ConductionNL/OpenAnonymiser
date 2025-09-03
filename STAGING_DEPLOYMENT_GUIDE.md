# 🚀 Staging/Accept Deployment Guide

## ✅ STAP 1: DOCKER IMAGES (COMPLETED!)

```bash
# ✅ DONE: Images gebouwd en gepusht
docker build -t mwest2020/openanonymiser:v1.1.0 .
docker tag mwest2020/openanonymiser:v1.1.0 mwest2020/openanonymiser:latest
docker tag mwest2020/openanonymiser:v1.1.0 mwest2020/openanonymiser:dev
docker push mwest2020/openanonymiser:v1.1.0
docker push mwest2020/openanonymiser:latest
docker push mwest2020/openanonymiser:dev
```

**Images Available:**
- ✅ `mwest2020/openanonymiser:v1.1.0` → Production
- ✅ `mwest2020/openanonymiser:latest` → Production alias
- ✅ `mwest2020/openanonymiser:dev` → Staging

## 📋 STAP 2: DNS CONFIGURATIE

**Benodigde DNS A-records:**

```dns
# Staging domain
api.openanonymiser.accept.commonground.nu → [CLUSTER_IP]

# Production domain  
api.openanonymiser.commonground.nu → [CLUSTER_IP]
```

**❓ ACTION REQUIRED:** Voeg deze DNS records toe in je DNS provider.

## 🔧 STAP 3: ARGOCD CONFIGURATIE  

### Staging Application

```yaml
# staging-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: openanonymiser-staging
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/ConductionNL/OpenAnonymiser.git
    targetRevision: staging  # ← Staging branch
    path: charts/openanonymiser
  destination:
    server: https://kubernetes.default.svc
    namespace: openanonymiser-staging  # ← Staging namespace
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### Production Application

```yaml
# production-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: openanonymiser-production
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/ConductionNL/OpenAnonymiser.git
    targetRevision: main  # ← Production branch
    path: charts/openanonymiser
  destination:
    server: https://kubernetes.default.svc
    namespace: openanonymiser  # ← Production namespace
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

## 🎯 STAP 4: KUBECTL DEPLOYMENT

```bash
# Create namespaces
kubectl create namespace openanonymiser-staging
kubectl create namespace openanonymiser

# Apply ArgoCD applications
kubectl apply -f staging-app.yaml
kubectl apply -f production-app.yaml

# Check deployments
kubectl get applications -n argocd
```

## 🔒 STAP 5: SSL CERTIFICATEN

**Let's Encrypt zal automatisch certificaten aanmaken voor:**
- `api.openanonymiser.accept.commonground.nu` → `openanonymiser-accept-tls`
- `api.openanonymiser.commonground.nu` → `openanonymiser-tls`

**Monitor certificaten:**
```bash
# Check certificates
kubectl get certificates -n openanonymiser-staging
kubectl get certificates -n openanonymiser

# Check challenges (als certificaat pending)
kubectl get challenges -A
```

## 🧪 STAP 6: TESTING PROCEDURES

### Staging Tests (Accept Environment)
```bash
# Health check
curl https://api.openanonymiser.accept.commonground.nu/api/v1/health

# New string endpoints
python test_endpoints.py https://api.openanonymiser.accept.commonground.nu

# Document upload
curl -X POST -F "files=@test.pdf" \
  https://api.openanonymiser.accept.commonground.nu/api/v1/documents/upload
```

### Production Tests (After staging success)
```bash
# Health check  
curl https://api.openanonymiser.commonground.nu/api/v1/health

# Full test suite
python test_endpoints.py https://api.openanonymiser.commonground.nu
```

## 🔄 STAP 7: DEPLOYMENT WORKFLOW

### For Feature Development:
```bash
# 1. Work on feature branch
git checkout feature/new-feature
git push origin feature/new-feature
# → Triggers auto-testing & dev tagging

# 2. Merge to staging for testing
git checkout staging
git merge feature/new-feature
git push origin staging
# → ArgoCD deploys to accept.commonground.nu

# 3. Test staging thoroughly
python test_endpoints.py https://api.openanonymiser.accept.commonground.nu

# 4. If staging OK → deploy to production
git checkout main
git merge staging
git push origin main
# → ArgoCD deploys to commonground.nu
```

## 📊 STAP 8: MONITORING & VERIFICATION

### Check Pod Status
```bash
# Staging
kubectl get pods -n openanonymiser-staging
kubectl logs -l app=openanonymiser -n openanonymiser-staging --tail=50

# Production  
kubectl get pods -n openanonymiser
kubectl logs -l app=openanonymiser -n openanonymiser --tail=50
```

### Check Ingress
```bash
# Staging
kubectl describe ingress openanonymiser -n openanonymiser-staging

# Production
kubectl describe ingress openanonymiser -n openanonymiser
```

### Check SSL
```bash
# Test SSL grades
curl -I https://api.openanonymiser.accept.commonground.nu/api/v1/health
curl -I https://api.openanonymiser.commonground.nu/api/v1/health
```

## 🎊 STAP 9: FINAL VERIFICATION

### ✅ Staging Checklist:
- [ ] DNS resolveert naar accept.commonground.nu
- [ ] SSL certificaat geldig (Let's Encrypt)
- [ ] Health endpoint: `{"ping": "pong"}`
- [ ] New endpoints: `/analyze` en `/anonymize` werken
- [ ] Document upload werkt
- [ ] ArgoCD sync status: Healthy

### ✅ Production Checklist:
- [ ] DNS resolveert naar commonground.nu  
- [ ] SSL certificaat geldig (Let's Encrypt)
- [ ] Health endpoint: `{"ping": "pong"}`
- [ ] New endpoints: `/analyze` en `/anonymize` werken
- [ ] Document upload werkt
- [ ] ArgoCD sync status: Healthy

## 🚨 TROUBLESHOOTING

### Common Issues:

**DNS not resolving:**
```bash
nslookup api.openanonymiser.accept.commonground.nu
nslookup api.openanonymiser.commonground.nu
```

**SSL certificate pending:**
```bash
kubectl describe certificate openanonymiser-accept-tls -n openanonymiser-staging
kubectl get challenges -A
```

**Pod not starting:**
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

**ArgoCD sync issues:**
```bash
kubectl get applications -n argocd
kubectl describe application openanonymiser-staging -n argocd
```

## 🎯 SUCCESS CRITERIA

**Deployment succesvol als:**
1. ✅ Beide environments toegankelijk via HTTPS
2. ✅ SSL certificaten geldig 
3. ✅ String endpoints (analyze/anonymize) werken
4. ✅ Document upload werkt
5. ✅ ArgoCD apps healthy
6. ✅ Tests slagen op beide environments

**🚀 Ready for production use!**