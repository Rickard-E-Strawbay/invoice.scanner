# Cloud Functions Deployment Guide

## Overview

This guide explains how to deploy the document processing pipeline to Google Cloud Functions on GCP.

## Architecture

The processing pipeline is divided into 5 serverless Cloud Functions, each handling one stage:

```
API Upload
    ↓
Pub/Sub: document-processing
    ↓
Cloud Function: cf_preprocess_document
    ↓
Pub/Sub: document-ocr
    ↓
Cloud Function: cf_extract_ocr_text
    ↓
Pub/Sub: document-llm
    ↓
Cloud Function: cf_predict_invoice_data
    ↓
Pub/Sub: document-extraction
    ↓
Cloud Function: cf_extract_structured_data
    ↓
Pub/Sub: document-evaluation
    ↓
Cloud Function: cf_run_automated_evaluation
    ↓
Database: status = 'completed'
```

## Prerequisites

Before deploying, ensure:

1. **GCP Project Setup** ✅ (Already done in FASE 0)
   - Project ID: `strawbayscannertest` (or `strawbayscannerprod`)
   - APIs enabled: Cloud Functions, Pub/Sub, Cloud SQL

2. **Cloud SQL Instance** ✅ (Already done in FASE 2)
   - Instance name: `invoice-scanner-test` or `invoice-scanner-prod`
   - Private IP connectivity
   - Database: `invoice_scanner`

3. **GCP Secrets** ✅ (Already done in FASE 1)
   - Database credentials in Secret Manager
   - LLM API keys in Secret Manager

4. **gcloud CLI** installed and authenticated
   ```bash
   gcloud auth login
   gcloud config set project strawbayscannertest
   ```

## Deployment Steps

### Step 1: Create Pub/Sub Topics

```bash
# Create all 5 topics
gcloud pubsub topics create document-processing \
    --project=strawbayscannertest

gcloud pubsub topics create document-ocr \
    --project=strawbayscannertest

gcloud pubsub topics create document-llm \
    --project=strawbayscannertest

gcloud pubsub topics create document-extraction \
    --project=strawbayscannertest

gcloud pubsub topics create document-evaluation \
    --project=strawbayscannertest

# Verify
gcloud pubsub topics list --project=strawbayscannertest
```

### Step 2: Deploy Cloud Functions

Use the automated script:

```bash
chmod +x deploy_cloud_functions.sh
./deploy_cloud_functions.sh strawbayscannertest europe-west1
```

Or deploy manually:

```bash
# 1. Preprocess
gcloud functions deploy cf-preprocess-document \
    --runtime python311 \
    --trigger-topic document-processing \
    --entry-point cf_preprocess_document \
    --source . \
    --region europe-west1 \
    --memory 512MB \
    --timeout 300 \
    --project=strawbayscannertest \
    --env-vars GCP_PROJECT_ID=strawbayscannertest

# 2. OCR (repeat for each function)
# ... (see deploy_cloud_functions.sh for exact commands)
```

### Step 3: Configure API Environment

Update Cloud Run API service environment variables:

```bash
gcloud run services update invoice-scanner-api-test \
    --update-env-vars=PROCESSING_BACKEND=cloud_functions \
    --update-env-vars=GCP_PROJECT_ID=strawbayscannertest \
    --update-env-vars=PUBSUB_TOPIC_ID=document-processing \
    --region=europe-west1 \
    --project=strawbayscannertest
```

### Step 4: Test End-to-End

1. **Upload Document**
   ```bash
   curl -X POST http://localhost:5001/documents/upload \
     -F "file=@invoice.pdf" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. **Monitor Processing**
   ```bash
   # Check document status
   curl http://localhost:5001/documents/{document_id}/status \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **View Logs**
   ```bash
   # Cloud Function logs
   gcloud functions logs read cf-preprocess-document \
     --limit 50 \
     --project=strawbayscannertest

   # Pub/Sub monitoring
   gcloud pubsub subscriptions list --project=strawbayscannertest
   ```

## Configuration

### Environment Variables (Cloud Run API)

```yaml
PROCESSING_BACKEND: cloud_functions
GCP_PROJECT_ID: strawbayscannertest
PUBSUB_TOPIC_ID: document-processing
STORAGE_TYPE: gcs
GCS_BUCKET_NAME: invoice-scanner-test-docs
```

### Environment Variables (Cloud Functions)

Set via deploy script or manually:

```bash
gcloud functions deploy cf-preprocess-document \
    --set-env-vars="GCP_PROJECT_ID=strawbayscannertest,CLOUD_SQL_CONN=..." \
    ...
```

## Monitoring & Troubleshooting

### View Function Status

```bash
# List all functions
gcloud functions list --project=strawbayscannertest

# Get function details
gcloud functions describe cf-preprocess-document \
    --region=europe-west1 \
    --project=strawbayscannertest
```

### View Logs

```bash
# Recent logs
gcloud functions logs read cf-preprocess-document \
    --limit 50 \
    --project=strawbayscannertest

# Live logs (follow)
gcloud functions logs read cf-preprocess-document \
    --limit 10 \
    --follow \
    --project=strawbayscannertest
```

### Pub/Sub Monitoring

```bash
# View topic messages (pull sample)
gcloud pubsub subscriptions pull test-subscription \
    --limit=5 \
    --project=strawbayscannertest

# Check subscription status
gcloud pubsub subscriptions describe document-processing-subscription \
    --project=strawbayscannertest
```

### Common Issues

**Problem: Function not triggering**
- Check Pub/Sub topic has a subscription pointing to function
- Verify function permissions (Cloud Functions service account has Editor role)
- Check function logs for errors

**Problem: Database connection timeout**
- Verify Cloud SQL instance has Private IP in same VPC
- Ensure Cloud Run has VPC Access Connector configured
- Check CLOUD_SQL_CONN environment variable is correct

**Problem: Function timeout**
- Increase timeout in deploy script (default 300s = 5 min)
- Check if actual processing logic is running (mocked version is only 5s)
- Monitor Cloud Function performance in GCP console

## Rollback

If issues occur, revert to local processing:

```bash
# API: Set processing backend to local
gcloud run services update invoice-scanner-api-test \
    --update-env-vars=PROCESSING_BACKEND=local \
    --region=europe-west1 \
    --project=strawbayscannertest

# This requires processing_http service accessible from Cloud Run
# (Not recommended for production - use Cloud Functions for production)
```

## Next Steps

1. ✅ Deploy Cloud Functions (this guide)
2. Test end-to-end with sample invoice
3. Monitor performance and costs
4. Implement actual processing logic (currently mocked)
5. Set up Cloud Monitoring and alerts
6. Production deployment to PROD project

## References

- [Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [Pub/Sub Guide](https://cloud.google.com/pubsub/docs)
- [Cloud SQL Private IP](https://cloud.google.com/sql/docs/postgres/private-ip)
- [Python Functions Framework](https://github.com/GoogleCloudPlatform/functions-framework-python)
