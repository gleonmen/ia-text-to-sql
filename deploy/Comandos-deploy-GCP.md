## Paso 0: Vinculación
gcloud init

## Paso 1: Creación del repositorio
gcloud artifacts repositories create repositorio-backend-langchain-inmobiliaria --repository-format docker --project datapath-kevin-inofuentecolque --location us-central1

## Paso 2: Crear la imagen de mi APLICACION y subir al repositorio
gcloud builds submit --config=cloudbuild.yaml --project ia-agentes-15

## Paso 3: Comando para despliegue o ejecución de la imagen en el repositorio
gcloud run services replace service.yaml --region us-central1 --project ia-agentes-15

## Paso 4: OPCIONAL, Dar permisos de acceso a mi APLICACION. ESTO SE EJECUTA UNA SOLA VEZ
gcloud run services set-iam-policy servicio-backend-inmobiliaria-giovanni-leon gcr-service-policy.yaml --region us-central1 --project ia-agentes-15