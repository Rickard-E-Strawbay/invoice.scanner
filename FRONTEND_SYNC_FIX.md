# Frontend Status Update Not Reflecting - ROOT CAUSE & FIX

## Problem
When pressing the restart button on a document, the frontend wasn't showing status updates in real-time.

## Root Causes Identified & Fixed

### 1. **Missing Evaluation Worker** ❌→✅
**Problem:** The docker-compose.yml had workers for preprocessing, OCR, LLM, and extraction, but NO worker for the evaluation stage.

**Impact:** When the task chain reached the evaluation stage, no worker existed to execute it, so the task would hang indefinitely in the Redis queue.

**Fix:** Added `worker_evaluation_1` container:
```yaml
worker_evaluation_1:
  extends:
    service: processing
  container_name: invoice.scanner.worker.evaluation.1
  ports: []
  command: celery -A tasks.celery_app worker -Q evaluation -l info -c 2 --hostname=evaluation-1@%h
  environment:
    WORKER_TYPE: evaluation
```

### 2. **Status String Mismatch** ❌→✅
**Problem:** Task code was using status values that didn't exist in the database schema.

**Database Schema Defines:**
```sql
'preprocessing', 'preprocessed', 'ocr_extracting', 'predicting', 
'extraction', 'automated_evaluation', 'approved', etc.
```

**But Code Was Using:**
```python
'preprocessing' ✓ (correct)
'preprocessed' ✓ (correct)
'ocr' ✗ (should be 'ocr_extracting')
'llm_extraction' ✗ (should be 'predicting')
'extraction' ✓ (correct)
'evaluation' ✗ (should be 'automated_evaluation')
'completed' ✗ (should be 'approved')
```

**Impact:** When tasks tried to update status with undefined values, the database might reject them or treat them inconsistently, causing status to remain frozen.

**Fix:** Updated all status values:

**ocr_tasks.py:**
```python
update_document_status(document_id, 'ocr_extracting')  # was: 'ocr'
```

**llm_tasks.py:**
```python
update_document_status(document_id, 'predicting')  # was: 'llm_extraction'
```

**extraction_tasks.py:** (no change needed - 'extraction' is correct)

**evaluation_tasks.py:**
```python
update_document_status(document_id, 'approved')  # was: 'completed'
```

### 3. **Frontend Status Filters Out of Sync** ❌→✅
**Problem:** Frontend Dashboard was checking for old status values that no longer matched what the backend was setting.

**Old Values Being Checked:**
```jsx
"ocr", "llm_extraction", "evaluation", "llm_error", "evaluation_error"
```

**Fix:** Updated Dashboard.jsx status filters:

```jsx
// Old                    → New
"ocr"                   → "ocr_extracting"
"llm_extraction"        → "predicting"  
"evaluation"            → "automated_evaluation"
"llm_error"             → "predict_error"
"evaluation_error"      → "automated_evaluation_error"
```

Also updated status color mappings to match new values.

## Files Modified

### Backend Tasks
1. **ocr_tasks.py** - Status: 'ocr' → 'ocr_extracting'
2. **llm_tasks.py** - Status: 'llm_extraction' → 'predicting'
3. **evaluation_tasks.py** - Status: 'completed' → 'approved'

### Docker Compose
1. **docker-compose.yml** - Added `worker_evaluation_1` container

### Frontend
1. **Dashboard.jsx** - Updated status filter list and color mappings

## Processing Pipeline Status Flow (Corrected)

```
User clicks Restart
    ↓
API resets status: "preprocessing"
    ↓
Task Chain Starts
    ↓
[1] preprocessing_tasks → Status: "preprocessing" → "preprocessed"
    ↓
[2] ocr_tasks → Status: "ocr_extracting" ✓ (WAS: "ocr")
    ↓
[3] llm_tasks → Status: "predicting" ✓ (WAS: "llm_extraction")
    ↓
[4] extraction_tasks → Status: "extraction"
    ↓
[5] evaluation_tasks → Status: "approved" ✓ (WAS: "completed")
    ↓
Frontend Polls Every 2 Seconds → Sees "approved" → Task Complete
```

## Testing the Fix

### Prerequisites
1. Rebuild and restart the stack:
```bash
docker-compose down
docker-compose up --build -d
```

2. Verify all workers are running:
```bash
docker-compose ps | grep worker
```

You should see:
- worker_preprocessing_1
- worker_preprocessing_2
- worker_ocr_1
- worker_llm_1
- worker_extraction_1
- worker_evaluation_1  ← NEW

### Test Steps

1. **Open Frontend:**
   - Navigate to Dashboard → Scanned Invoices

2. **Upload or Restart a Document:**
   - Click "Restart" on any document

3. **Watch Status Updates in Real-Time:**
   - Watch the status change every 2 seconds:
   - "preprocessing" → "preprocessed" → "ocr_extracting" → "predicting" → "extraction" → "approved"

4. **Check Logs:**
   ```bash
   docker-compose logs -f | grep -E "\[(OCR|LLM|EXTRACTION|EVALUATION)\]"
   ```

   You should see logs for each stage as it executes:
   ```
   worker_ocr_1          | [OCR] Starting text extraction for document: 98416a06...
   worker_llm_1          | [LLM] Starting LLM prediction for document: 98416a06...
   worker_extraction_1   | [EXTRACTION] Starting data extraction for document: 98416a06...
   worker_evaluation_1   | [EVALUATION] Starting automated evaluation for document: 98416a06...
   ```

5. **Verify in Database:**
   ```sql
   SELECT id, status, updated_at FROM documents 
   WHERE id = 'your-document-id'
   ORDER BY updated_at DESC 
   LIMIT 5;
   ```

   Should show status progression.

## Related Documentation

- **Task Chain Architecture:** TASK_CHAIN_FIX.md
- **Real-time Polling:** REAL_TIME_UPDATES_IMPLEMENTATION.md
- **Database Schema:** invoice.scanner.db/init.sql (document_status table)

## Verification Checklist

- [x] Missing evaluation worker added to docker-compose
- [x] Status values match database schema
- [x] Task code uses correct status values  
- [x] Frontend recognizes all status values
- [x] Frontend filters include all processing statuses
- [x] Frontend colors map to correct statuses

## Summary

The issues were:
1. **Missing infrastructure** - No evaluation worker to execute the final stage
2. **Data mismatch** - Status strings didn't match database schema
3. **Frontend desynchronization** - Frontend wasn't checking for the actual status values being set

All three issues have been fixed. The system should now properly track and display document status updates through all 5 processing stages in real-time.
