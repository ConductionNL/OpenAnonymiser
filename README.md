# OpenAnonymizer: Modulaire PII-detectie voor Nederlandse tekst

Presidio-NL is een modulaire API-service voor het detecteren en anonimiseren van privacygevoelige informatie (PII) in Nederlandse tekst. De service is gebaseerd op [Microsoft Presidio](https://github.com/microsoft/presidio) en biedt ondersteuning voor verschillende NLP-modellen (zoals spaCy of HuggingFace transformers) zonder dat de API of logica hoeft te worden aangepast.

## Installatie & Gebruik

Zie ook:
- Gebruikshandleiding met Swagger-stappen: `docs/use-cases.md`
- API voorbeelden (curl): `docs/api-examples.md`
- Leesbaarheid/taalniveau uitleg: `docs/readability.md`
- Productie Swagger: https://api.openanonymiser.commonground.nu/api/v1/docs
- Staging Swagger: https://api.openanonymiser.accept.commonground.nu/api/v1/docs

### 1. Lokaal draaien (voor ontwikkeling)

Installeer dependencies en start de API:

```bash
uv venv
uv sync
uv run api.py
```

De API is nu bereikbaar op [http://localhost:8080/api/v1/docs](http://localhost:8080/api/v1/docs) (Swagger UI).

### 2. Docker Compose (aanbevolen)

Start beide services (API + UI) met docker-compose:

```bash
docker-compose up -d
```

Na opstarten zijn de services bereikbaar op:
- **API**: [http://localhost:8001/api/v1/docs](http://localhost:8001/api/v1/docs) (Swagger UI)
- **UI**: [http://localhost:8002](http://localhost:8002) (Web interface)

### Welke modellen voor welke entiteiten?
- Pattern recognizers (regelgebaseerd via Presidio): `IBAN`, `PHONE_NUMBER`, `EMAIL`
- NLP (NER – SpaCy of Transformers): `PERSON`, `LOCATION`, `ORGANIZATION`
- `ADDRESS`: via NLP (best‑effort), geen pattern‑recognizer; dekking is model‑afhankelijk

Kies patterns voor “vormvaste” entiteiten, en NLP voor “vrije‑tekst” entiteiten.

### 3. Individuele Docker containers

Bouw het backend image:

```bash
docker build -t openanonymizer .
```

Start alleen de backend container:

```bash
docker run -d -p 8001:8080 --name openanonymiser openanonymizer
```

API bereikbaar op [http://localhost:8001/api/v1/docs](http://localhost:8001/api/v1/docs)

### 4. Kubernetes met Helm (productie)

**⚠️ KRITIEKE VEREISTE: PERSISTENT STORAGE** 

OpenAnonymiser vereist persistent storage voor:
- SQLite database (`/app/openanonymiser.db`)
- Geüploade PDF-bestanden (`/app/temp/source/`) 
- Geanonimiseerde bestanden (`/app/temp/anonymized/`)
- Applicatielogs (`/app/logs/`)

**Zonder PVC gaan alle gegevens verloren bij pod restart!**

Installeer de API service in Kubernetes met Helm:

```bash
# Installeer de chart
helm install openanonymiser ./charts/openanonymiser

# Of met custom values
helm install openanonymiser ./charts/openanonymiser -f values-production.yaml

# Upgrade bestaande deployment
helm upgrade openanonymiser ./charts/openanonymiser
```

#### Helm configuratie

Belangrijke configureerbare waarden in `values.yaml`:

```yaml
# Image configuratie
image:
  repository: mwest2020/openanonymiser
  tag: latest

# Ingress voor externe toegang
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: "api.openanonymiser.example.com"

# KRITIEK: Persistent storage configuratie
persistence:
  enabled: true                    # VERPLICHT voor productie!
  storageClass: "fast-ssd"        # Pas aan voor jouw cluster
  size: 50Gi                      # Database + bestanden

# Environment variabelen
app:
  env:
    defaultNlpEngine: "spacy"          # of "transformers"
    defaultSpacyModel: "nl_core_news_md"
    cryptoKey: "your-secret-key"       # Wijzig dit!
  auth:
    username: "admin"                  # Wijzig dit!
    password: "secure-password"        # Wijzig dit!

# Resources
resources:
  requests:
    cpu: 500m
    memory: 4Gi
  limits:
    cpu: 1500m
    memory: 8Gi
```

#### Productie setup

Voor productie gebruik:

1. **Secrets**: Gebruik Kubernetes secrets voor gevoelige waarden:
```bash
kubectl create secret generic openanonymiser-secrets \
  --from-literal=crypto-key=your-secret-key \
  --from-literal=auth-password=secure-password
```

2. **TLS**: Enable TLS in ingress configuratie

3. **Monitoring**: Health checks zijn al geconfigureerd op `/health`

### 5. Testen (pytest)

Gebruik de nieuwe use-case tests in `tests/test_usecases.py`. Stel een BASE URL in of laat default (localhost:8080).

```bash
# Tegen lokale server
pytest -q -k usecases

# Tegen staging of productie
OPENANONYMISER_BASE_URL="https://api.openanonymiser.accept.commonground.nu" pytest -q -k usecases
# of
OPENANONYMISER_BASE_URL="https://api.openanonymiser.commonground.nu" pytest -q -k usecases
```
