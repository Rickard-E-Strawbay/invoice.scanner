#!/bin/bash

# Deploy Processing Worker Service to Google Cloud Run
# Validates requirements.txt, installs dependencies, and deploys

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Invoice Scanner - Processing Worker Service (GCP Deploy)      ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Configuration
SERVICE_NAME="invoice-scanner-processing"
GCP_PROJECT=${GCP_PROJECT:-strawbayscannertest}
GCP_REGION=${GCP_REGION:-europe-west1}
IMAGE_REGISTRY="europe-west1-docker.pkg.dev"
IMAGE_REPO="strawbayscannertest/invoice-scanner"
IMAGE_NAME="$SERVICE_NAME"

echo "📋 Configuration:"
echo "   Service Name: $SERVICE_NAME"
echo "   Project: $GCP_PROJECT"
echo "   Region: $GCP_REGION"
echo "   Registry: $IMAGE_REGISTRY/$GCP_PROJECT/$IMAGE_REPO/$IMAGE_NAME"

# Step 1: Validate requirements.txt
echo ""
echo "📦 Step 1: Validating requirements.txt..."
cd "$SCRIPT_DIR"

if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found"
    exit 1
fi

# Check for common issues
if grep -q "^#" requirements.txt | head -1; then
    echo "✅ requirements.txt has comments (OK)"
fi

PACKAGE_COUNT=$(grep -v "^#" requirements.txt | grep -v "^$" | wc -l)
echo "✅ Found $PACKAGE_COUNT packages"

# Step 2: Check system dependencies (on build machine)
echo ""
echo "⚙️  Step 2: Checking system dependencies..."
MISSING=""

if ! command -v docker &> /dev/null; then
    MISSING="$MISSING docker"
fi

if ! command -v gcloud &> /dev/null; then
    MISSING="$MISSING gcloud"
fi

if [ -n "$MISSING" ]; then
    echo "❌ Missing tools:$MISSING"
    echo "   Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "✅ Required tools installed"

# Step 3: Build Docker image
echo ""
echo "🐳 Step 3: Building Docker image..."
IMAGE_TAG="$IMAGE_REGISTRY/$GCP_PROJECT/$IMAGE_REPO/$IMAGE_NAME:latest"

if ! docker build -t "$IMAGE_TAG" \
    --build-arg SERVICE_NAME="$SERVICE_NAME" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --build-arg VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
    . ; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Docker image built: $IMAGE_TAG"

# Step 4: Push to Artifact Registry
echo ""
echo "📤 Step 4: Pushing to Artifact Registry..."

# Ensure user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated with gcloud"
    echo "   Run: gcloud auth login"
    exit 1
fi

if ! docker push "$IMAGE_TAG"; then
    echo "❌ Docker push failed"
    exit 1
fi

echo "✅ Image pushed to registry"

# Step 5: Deploy to Cloud Run
echo ""
echo "🚀 Step 5: Deploying to Cloud Run..."

gcloud run deploy "$SERVICE_NAME" \
    --image="$IMAGE_TAG" \
    --project="$GCP_PROJECT" \
    --region="$GCP_REGION" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=4Gi \
    --cpu=2 \
    --timeout=3600 \
    --max-instances=10 \
    --min-instances=1 \
    --set-env-vars="GCP_PROJECT_ID=$GCP_PROJECT,PROCESSING_LOG_LEVEL=INFO,WORKER_MAX_PROCESSES=5" \
    --set-cloudsql-instances="strawbayscannertest:europe-west1:invoice-scanner-main" \
    --service-account="invoice-scanner-worker@$GCP_PROJECT.iam.gserviceaccount.com" \
    --vpc-connector="projects/$GCP_PROJECT/locations/$GCP_REGION/connectors/invoice-scanner-connector" \
    --vpc-egress=all

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --project="$GCP_PROJECT" \
    --region="$GCP_REGION" \
    --format='value(status.url)')

echo "✅ Deployment complete!"
echo ""
echo "📍 Service URL: $SERVICE_URL"
echo ""
echo "📝 Next steps:"
echo "   1. Set up Pub/Sub subscriptions:"
echo "      - document-processing-subscription → $SERVICE_URL/pubsub"
echo "      - document-ocr-subscription → $SERVICE_URL/pubsub"
echo "      - document-llm-subscription → $SERVICE_URL/pubsub"
echo "      - document-extraction-subscription → $SERVICE_URL/pubsub"
echo "      - document-evaluation-subscription → $SERVICE_URL/pubsub"
echo ""
echo "   2. Test health check:"
echo "      curl $SERVICE_URL/health"
echo ""
echo "   3. Monitor logs:"
echo "      gcloud run logs read $SERVICE_NAME --project=$GCP_PROJECT --region=$GCP_REGION --follow"
