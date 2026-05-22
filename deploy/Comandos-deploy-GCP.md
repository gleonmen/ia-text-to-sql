# Deploy en Google Cloud Run

Este proyecto es un monolito Streamlit. El entrypoint productivo es
`main.py`, empaquetado con `deploy/Dockerfile.prod`.

## Requisitos locales

1. Instala Google Cloud CLI:
   https://cloud.google.com/sdk/docs/install
2. Inicia sesion:

```powershell
gcloud init
gcloud auth login
gcloud auth application-default login
```

3. Verifica que `.env` tenga estos valores locales:

```env
OPENAI_API_KEY=...
GOOGLE_CLOUD_PROJECT=...
GOOGLE_CLOUD_LOCATION=us-central1
DB_USER=postgres.<project-ref>
DB_PASSWORD=...
DB_HOST=...pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_SCHEMA=agent_text_to_sql
```

No subas `.env` ni `credentials/`; `.gitignore`, `.dockerignore` y
`.gcloudignore` ya los excluyen.

## Deploy automatico recomendado

Desde la raiz del proyecto:

```powershell
.\deploy\deploy-cloud-run.ps1
```

Con parametros explicitos:

```powershell
.\deploy\deploy-cloud-run.ps1 `
  -ProjectId "ia-agentes-15" `
  -Region "us-central1" `
  -Repository "langgraph-text-to-sql" `
  -ImageName "langgraph-text-to-sql-streamlit" `
  -ServiceName "langgraph-text-to-sql"
```

El script hace lo siguiente:

- habilita APIs necesarias;
- crea el repositorio Docker en Artifact Registry si falta;
- crea un service account para Cloud Run si falta;
- da permiso `roles/bigquery.jobUser`;
- da permiso `roles/bigquery.readSessionUser`;
- sube `OPENAI_API_KEY` y `DB_PASSWORD` a Secret Manager;
- construye la imagen con Cloud Build;
- despliega la imagen en Cloud Run.

## Comandos manuales equivalentes

```powershell
$PROJECT_ID="ia-agentes-15"
$REGION="us-central1"
$REPO="langgraph-text-to-sql"
$IMAGE="langgraph-text-to-sql-streamlit"
$SERVICE="langgraph-text-to-sql"

gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com bigquery.googleapis.com bigquerystorage.googleapis.com

gcloud artifacts repositories create $REPO `
  --repository-format docker `
  --location $REGION `
  --project $PROJECT_ID

gcloud builds submit . `
  --config deploy/cloudbuild.yaml `
  --substitutions "_REGION=$REGION,_AR_REPO=$REPO,_IMAGE_NAME=$IMAGE" `
  --project $PROJECT_ID

gcloud run deploy $SERVICE `
  --image "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/${IMAGE}:latest" `
  --region $REGION `
  --platform managed `
  --allow-unauthenticated
```
