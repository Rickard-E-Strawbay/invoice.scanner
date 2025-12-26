#!/bin/bash

# ============================================================
# Cloud Functions Deployment Script
# Deploys all 5 document processing stages to Google Cloud
# ============================================================

set -e

# Configuration
PROJECT_ID=${1:-strawbayscannertest}
REGION=${2:-europe-west1}
BUCKET_NAME="gs://invoice-scanner-cloud-functions"

echo "[DEPLOY] Starting Cloud Functions deployment to project: $PROJECT_ID"

# Create storage bucket for Cloud Functions code (if not exists)
echo "[DEPLOY] Creating GCS bucket for function code..."
gsutil mb -p "$PROJECT_ID" -l "$REGION" "$BUCKET_NAME" 2>/dev/null || echo "Bucket already exists"

# Set current project
gcloud config set project "$PROJECT_ID"

# Create Pub/Sub topics if they don't exist
echo "[DEPLOY] Creating Pub/Sub topics..."
gcloud pubsub topics create document-processing --project="$PROJECT_ID" 2>/dev/null || echo "Topic document-processing exists"
gcloud pubsub topics create document-ocr --project="$PROJECT_ID" 2>/dev/null || echo "Topic document-ocr exists"
gcloud pubsub topics create document-llm --project="$PROJECT_ID" 2>/dev/null || echo "Topic document-llm exists"
gcloud pubsub topics create document-extraction --project="$PROJECT_ID" 2>/dev/null || echo "Topic document-extraction exists"
gcloud pubsub topics create document-evaluation --project="$PROJECT_ID" 2>/dev/null || echo "Topic document-evaluation exists"

# Get Cloud SQL connection name
CLOUD_SQL_INSTANCE="invoice-scanner-test"  # Change to -prod for production
if [ "$PROJECT_ID" = "strawbayscannerprod" ]; then
    CLOUD_SQL_INSTANCE="invoice-scanner-prod"
fi

CLOUD_SQL_CONN=$(gcloud sql instances describe "$CLOUD_SQL_INSTANCE" --project="$PROJECT_ID" --format='value(connectionName)')
echo "[DEPLOY] Cloud SQL connection: $CLOUD_SQL_CONN"

# Deploy Cloud Function 1: Preprocessing
echo "[DEPLOY] Deploying cf-preprocess-document..."
gcloud functions deploy cf-preprocess-document \
    --runtime python311 \
    --trigger-topic document-processing \
    --entry-point cf_preprocess_document \
    --source . \
    --region "$REGION" \
    --memory 512MB \
    --timeout 300 \
    --env-vars-file=.env.cloud.functions.yaml \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,CLOUD_SQL_CONN=$CLOUD_SQL_CONN" \
    --project="$PROJECT_ID"

# Deploy Cloud Function 2: OCR
echo "[DEPLOY] Deploying cf-extract-ocr-text..."
gcloud functions deploy cf-extract-ocr-text \
    --runtime python311 \
    --trigger-topic document-ocr \
    --entry-point cf_extract_ocr_text \
    --source . \
    --region "$REGION" \
    --memory 1024MB \
    --timeout 300 \
    --env-vars-file=.env.cloud.functions.yaml \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,CLOUD_SQL_CONN=$CLOUD_SQL_CONN" \
    --project="$PROJECT_ID"

# Deploy Cloud Function 3: LLM
echo "[DEPLOY] Deploying cf-predict-invoice-data..."
gcloud functions deploy cf-predict-invoice-data \
    --runtime python311 \
    --trigger-topic document-llm \
    --entry-point cf_predict_invoice_data \
    --source . \
    --region "$REGION" \
    --memory 512MB \
    --timeout 300 \
    --env-vars-file=.env.cloud.functions.yaml \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,CLOUD_SQL_CONN=$CLOUD_SQL_CONN" \
    --project="$PROJECT_ID"

# Deploy Cloud Function 4: Extraction
echo "[DEPLOY] Deploying cf-extract-structured-data..."
gcloud functions deploy cf-extract-structured-data \
    --runtime python311 \
    --trigger-topic document-extraction \
    --entry-point cf_extract_structured_data \
    --source . \
    --region "$REGION" \
    --memory 512MB \
    --timeout 300 \
    --env-vars-file=.env.cloud.functions.yaml \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,CLOUD_SQL_CONN=$CLOUD_SQL_CONN" \
    --project="$PROJECT_ID"

# Deploy Cloud Function 5: Evaluation
echo "[DEPLOY] Deploying cf-run-automated-evaluation..."
gcloud functions deploy cf-run-automated-evaluation \
    --runtime python311 \
    --trigger-topic document-evaluation \
    --entry-point cf_run_automated_evaluation \
    --source . \
    --region "$REGION" \
    --memory 512MB \
    --timeout 300 \
    --env-vars-file=.env.cloud.functions.yaml \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,CLOUD_SQL_CONN=$CLOUD_SQL_CONN" \
    --project="$PROJECT_ID"

echo "[DEPLOY] ✓ All Cloud Functions deployed successfully!"
echo ""
echo "Verify deployment:"
echo "  gcloud functions list --project=$PROJECT_ID"
echo ""
echo "View logs:"
echo "  gcloud functions logs read cf-preprocess-document --limit 50 --project=$PROJECT_ID"
