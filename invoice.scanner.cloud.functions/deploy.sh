#!/bin/bash

# ============================================================
# Cloud Functions Deployment Script
# Deploys all 5 document processing functions to GCP
# ============================================================

set -e

# Configuration
PROJECT_ID=${1:-strawbayscannertest}
REGION=${2:-europe-west1}

# Get current directory and calculate relative path to repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
CF_DIR="$REPO_ROOT/invoice.scanner.cloud.functions"

# Cleanup function to remove temporary shared module on exit
cleanup() {
    if [ -d "$CF_DIR/shared" ]; then
        rm -rf "$CF_DIR/shared" 2>/dev/null || true
    fi
    if [ -f "$CF_DIR/pyproject.toml" ]; then
        rm -f "$CF_DIR/pyproject.toml" 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "[DEPLOY] Starting Cloud Functions deployment to project: $PROJECT_ID"
echo "[DEPLOY] Region: $REGION"
echo ""

SHARED_DIR="$REPO_ROOT/invoice.scanner.shared"

# Verify both directories exist
if [ ! -d "$CF_DIR" ] || [ ! -d "$SHARED_DIR" ]; then
    echo "❌ ERROR: Could not find required directories"
    echo "  CF_DIR: $CF_DIR"
    echo "  SHARED_DIR: $SHARED_DIR"
    exit 1
fi
echo "✓ Verified repo structure"
echo ""

# Copy shared module into CF directory for pip to access during Cloud Build
# gcloud functions deploy --source CF_DIR will see shared/ during pip install
echo "[DEPLOY] Preparing shared module for Cloud Build..."
TEMP_SHARED="$CF_DIR/shared"
if [ -d "$TEMP_SHARED" ]; then
    rm -rf "$TEMP_SHARED"
fi
cp -r "$SHARED_DIR/shared" "$CF_DIR/shared"
cp "$SHARED_DIR/pyproject.toml" "$CF_DIR/pyproject.toml"
echo "  ✓ Copied shared module to CF directory"
echo ""

# Set current project
gcloud config set project "$PROJECT_ID"

# Create Pub/Sub topics if they don't exist
echo "[DEPLOY] Creating Pub/Sub topics..."
gcloud pubsub topics create document-processing --project="$PROJECT_ID" 2>/dev/null || echo "  ✓ document-processing already exists"
gcloud pubsub topics create document-ocr --project="$PROJECT_ID" 2>/dev/null || echo "  ✓ document-ocr already exists"
gcloud pubsub topics create document-llm --project="$PROJECT_ID" 2>/dev/null || echo "  ✓ document-llm already exists"
gcloud pubsub topics create document-extraction --project="$PROJECT_ID" 2>/dev/null || echo "  ✓ document-extraction already exists"
gcloud pubsub topics create document-evaluation --project="$PROJECT_ID" 2>/dev/null || echo "  ✓ document-evaluation already exists"

# Get Cloud SQL connection name
CLOUD_SQL_INSTANCE="invoice-scanner-test"
if [ "$PROJECT_ID" = "strawbayscannerprod" ]; then
    CLOUD_SQL_INSTANCE="invoice-scanner-prod"
fi

CLOUD_SQL_CONN=$(gcloud sql instances describe "$CLOUD_SQL_INSTANCE" --project="$PROJECT_ID" --format='value(connectionName)')
echo "[DEPLOY] Cloud SQL connection: $CLOUD_SQL_CONN"
echo ""

# Get the default service account for Cloud Functions
SERVICE_ACCOUNT=$(gcloud iam service-accounts list --project="$PROJECT_ID" --format='value(email)' --filter='displayName:"Cloud Functions Service Account"' | head -1)
if [ -z "$SERVICE_ACCOUNT" ]; then
    SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"
fi
echo "[DEPLOY] Service Account: $SERVICE_ACCOUNT"
echo ""

# Grant Secret Manager access to service account
echo "[DEPLOY] Granting Secret Manager access to service account..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet 2>/dev/null || echo "  ✓ Secret Manager access already granted"
echo ""
# Note: DATABASE_USER and DATABASE_PASSWORD are fetched from Secret Manager, not passed as env vars
# Note: DATABASE_HOST and DATABASE_PORT removed - Cloud SQL Connector uses CLOUD_SQL_CONN only
# Determine GCS bucket based on project
if [[ "$PROJECT_ID" == *"prod"* ]]; then
    GCS_BUCKET="invoice-scanner-prod-docs"
else
    GCS_BUCKET="invoice-scanner-test-docs"
fi
ENV_VARS="GCP_PROJECT_ID=$PROJECT_ID,CLOUD_SQL_CONN=$CLOUD_SQL_CONN,DATABASE_NAME=invoice_scanner,STORAGE_TYPE=gcs,GCS_BUCKET_NAME=$GCS_BUCKET,PUBSUB_TOPIC_PREFIX=document-,OPENAI_MODEL=gpt-4o,GOOGLE_MODEL=gemini-2.0-flash,ANTHROPIC_MODEL=claude-3-5-sonnet-20241022,FUNCTION_LOG_LEVEL=INFO,PYTHONUNBUFFERED=1"

# Deploy functions
echo "[DEPLOY] Deploying 5 Cloud Functions..."
echo ""

# Function 1
echo "[1/5] cf_preprocess_document..."
gcloud functions deploy cf-preprocess-document \
    --gen2 \
    --runtime python311 \
    --trigger-topic document-processing \
    --entry-point cf_preprocess_document \
    --source ./invoice.scanner.cloud.functions \
    --region "$REGION" \
    --memory 512MB \
    --timeout 300 \
    --vpc-connector="projects/$PROJECT_ID/locations/$REGION/connectors/run-connector" \
    --set-env-vars="$ENV_VARS" \
    --project="$PROJECT_ID" \
    --quiet

# Function 2
echo "[2/5] cf_extract_ocr_text..."
gcloud functions deploy cf-extract-ocr-text \
    --gen2 \
    --runtime python311 \
    --trigger-topic document-ocr \
    --entry-point cf_extract_ocr_text \
    --source ./invoice.scanner.cloud.functions \
    --region "$REGION" \
    --memory 1024MB \
    --timeout 300 \
    --vpc-connector="projects/$PROJECT_ID/locations/$REGION/connectors/run-connector" \
    --set-env-vars="$ENV_VARS" \
    --project="$PROJECT_ID" \
    --quiet

# Function 3
echo "[3/5] cf_predict_invoice_data..."
gcloud functions deploy cf-predict-invoice-data \
    --gen2 \
    --runtime python311 \
    --trigger-topic document-llm \
    --entry-point cf_predict_invoice_data \
    --source ./invoice.scanner.cloud.functions \
    --region "$REGION" \
    --memory 512MB \
    --timeout 300 \
    --vpc-connector="projects/$PROJECT_ID/locations/$REGION/connectors/run-connector" \
    --set-env-vars="$ENV_VARS" \
    --project="$PROJECT_ID" \
    --quiet

# Function 4
echo "[4/5] cf_extract_structured_data..."
gcloud functions deploy cf-extract-structured-data \
    --gen2 \
    --runtime python311 \
    --trigger-topic document-extraction \
    --entry-point cf_extract_structured_data \
    --source ./invoice.scanner.cloud.functions \
    --region "$REGION" \
    --memory 512MB \
    --timeout 300 \
    --vpc-connector="projects/$PROJECT_ID/locations/$REGION/connectors/run-connector" \
    --set-env-vars="$ENV_VARS" \
    --project="$PROJECT_ID" \
    --quiet

# Function 5
echo "[5/5] cf_run_automated_evaluation..."
gcloud functions deploy cf-run-automated-evaluation \
    --gen2 \
    --runtime python311 \
    --trigger-topic document-evaluation \
    --entry-point cf_run_automated_evaluation \
    --source ./invoice.scanner.cloud.functions \
    --region "$REGION" \
    --memory 512MB \
    --timeout 300 \
    --vpc-connector="projects/$PROJECT_ID/locations/$REGION/connectors/run-connector" \
    --set-env-vars="$ENV_VARS" \
    --project="$PROJECT_ID" \
    --quiet

# Clean up temporary copied shared module
echo "[DEPLOY] Cleaning up temporary files..."
if [ -d "$CF_DIR/shared" ]; then
    rm -rf "$CF_DIR/shared"
fi
if [ -f "$CF_DIR/pyproject.toml" ]; then
    rm -f "$CF_DIR/pyproject.toml"
fi
echo "  ✓ Removed temporary shared module copy"
echo ""

echo "✅ All Cloud Functions deployed successfully!"
echo ""
echo "Verify deployment:"
echo "  gcloud functions list --v2 --project=$PROJECT_ID"
echo ""
echo "View logs:"
echo "  gcloud functions logs read cf-preprocess-document --v2 --limit 50 --project=$PROJECT_ID --region=$REGION"
