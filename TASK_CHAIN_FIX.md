# Task Chain Fix - Document Status Tracking

## Problem

Documents were getting stuck in "preprocessed" status when the restart button was clicked. The issue was that intermediate tasks (OCR, LLM, Extraction, Evaluation) didn't have access to the `document_id` parameter needed to update the database status.

## Root Cause

The Celery task chain was set up like this:
```python
workflow = chain(
    preprocess_document.s(document_id, company_id),     # ✓ has doc_id
    extract_ocr_text.s(),                               # ✗ NO doc_id!
    predict_invoice_data.s(company_id),                 # ✗ NO doc_id!
    extract_structured_data.s(company_id),              # ✗ NO doc_id!
    run_automated_evaluation.s(),                       # ✗ NO doc_id!
)
```

In Celery chains, the previous task's result becomes the first argument of the next task. So:
- `preprocess_document` returns a file path
- `extract_ocr_text` receives the path but has no `document_id` to update database status
- Without status updates, the pipeline appears frozen

## Solution

Modified all task signatures to accept `document_id` as an additional parameter and updated the chain to pass it through:

```python
workflow = chain(
    preprocess_document.s(document_id, company_id),                    # task1(doc_id, company)
    extract_ocr_text.s(document_id),                                   # task2(path, doc_id)
    predict_invoice_data.s(company_id, document_id),                   # task3(ocr, company, doc_id)
    extract_structured_data.s(company_id, document_id),                # task4(llm, company, doc_id)
    run_automated_evaluation.s(document_id),                           # task5(data, doc_id)
)
```

## Files Modified

### 1. **document_tasks.py** (Orchestrator)
- Updated chain to pass `document_id` through all 5 tasks
- Added detailed comments explaining parameter flow
- Added logging with `[ORCHESTRATOR]` prefix

### 2. **ocr_tasks.py** (Stage 2)
- Signature: `extract_ocr_text(preprocessed_image_path, document_id)`
- Added: `update_document_status(document_id, 'ocr')` on success
- Added: `update_document_status(document_id, 'ocr_error', ...)` on error
- Enhanced logging with document_id

### 3. **llm_tasks.py** (Stage 3)
- Signature: `predict_invoice_data(ocr_result, company_id, document_id)`
- Added: `update_document_status(document_id, 'llm_extraction')` on success
- Added: `update_document_status(document_id, 'llm_error', ...)` on error
- Enhanced logging with document_id
- Added import: `from config.db_utils import update_document_status`

### 4. **extraction_tasks.py** (Stage 4)
- Signature: `extract_structured_data(llm_prediction, company_id, document_id)`
- Added: `update_document_status(document_id, 'extraction')` on success
- Added: `update_document_status(document_id, 'extraction_error', ...)` on error
- Enhanced logging with document_id
- Added import: `from config.db_utils import update_document_status`

### 5. **evaluation_tasks.py** (Stage 5)
- Signature: `run_automated_evaluation(structured_data, document_id)`
- Added: `update_document_status(document_id, 'completed')` on success
- Added: `update_document_status(document_id, 'evaluation_error', ...)` on error
- Enhanced logging with document_id
- Added import: `from config.db_utils import update_document_status`

## Expected Behavior After Fix

### Processing Pipeline Flow
1. User clicks "Restart" on a document
2. Orchestrator sets status to `preprocessing`
3. Preprocessing completes → status updates to `preprocessed` ✓
4. OCR starts → status updates to `ocr` ✓
5. LLM starts → status updates to `llm_extraction` ✓
6. Extraction starts → status updates to `extraction` ✓
7. Evaluation starts → status updates to `evaluation`
8. Evaluation completes → status updates to `completed` ✓

### Frontend Display
- Dashboard polls every 2 seconds (from real-time polling implementation)
- Status badges update with color-coded indicators:
  - Blue: Processing/ongoing
  - Green: Completed
  - Red: Error
  - Yellow: Pending
- Document progresses through all 5 stages visible in real-time

## Testing the Fix

To verify the fix is working:

1. **Start the system:**
   ```bash
   docker-compose up -d
   ```

2. **Upload or restart a document:**
   - Navigate to Dashboard → Scanned Invoices
   - Click "Restart" on any document
   - Watch the status update in real-time

3. **Expected timeline:**
   - Seconds 0-5: "preprocessing"
   - Seconds 5-10: "ocr"
   - Seconds 10-15: "llm_extraction"
   - Seconds 15-20: "extraction"
   - Seconds 20-25: "evaluation" → "completed"

4. **Check logs:**
   ```bash
   docker logs invoice.scanner.processing -f | grep "^\[OCR\]\|^\[LLM\]\|^\[EXTRACTION\]\|^\[EVALUATION\]"
   ```
   Should see logs for each stage as processing progresses.

5. **Verify database:**
   - Check database for document status updates
   - Should see entries for each pipeline stage

## Logging Format

All tasks now use consistent logging with stage prefixes:
- `[PREPROCESSING]` - Image preprocessing
- `[OCR]` - Text extraction
- `[LLM]` - Invoice data prediction
- `[EXTRACTION]` - Data extraction and validation
- `[EVALUATION]` - Quality assessment
- `[ORCHESTRATOR]` - Main orchestration task

This makes it easy to trace the pipeline in logs:
```
[ORCHESTRATOR] Starting document processing: 98416a06-3a8 (company: company-123)
[PREPROCESSING] Starting for document 98416a06-3a8
[PREPROCESSING] Completed for document 98416a06-3a8
[OCR] Starting text extraction for document: 98416a06-3a8
[OCR] Completed with mock OCR text for 98416a06-3a8
[LLM] Starting LLM prediction for document: 98416a06-3a8, company: company-123
[LLM] Completed with mock LLM predictions for 98416a06-3a8
[EXTRACTION] Starting data extraction for document: 98416a06-3a8
[EXTRACTION] Completed data extraction for 98416a06-3a8
[EVALUATION] Starting automated evaluation for document: 98416a06-3a8
[EVALUATION] Completed with quality score 0.95 for 98416a06-3a8
```

## Related Documentation

- Real-time polling in frontend: `REAL_TIME_UPDATES_IMPLEMENTATION.md`
- Database utilities: `config/db_utils.py`
- Celery configuration: `config/celery_config.py`
