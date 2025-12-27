"""
Frontend Status Update Implementation - Real-time Invoice Status Updates

=== PROBLEM ===
Invoices in the "Scanned Invoices" tab were not updating their processing status 
in real-time as they moved through the processing pipeline (preprocessing → OCR → LLM → extraction → evaluation).

Status only updated when manually navigating back to the view or doing a full page refresh.

=== SOLUTION ===
Implemented automatic polling mechanism that fetches document status updates every 2 seconds
while viewing the "Scanned Invoices" tab.

=== CHANGES MADE ===

1. POLLING IMPLEMENTATION
   File: Dashboard.jsx
   
   Added useEffect hook that:
   - Fetches documents immediately when entering "scanned-invoices" view
   - Sets up interval to fetch documents every 2 seconds
   - Clears interval when leaving the view
   - Automatically refreshes the invoice list with latest status

   Code:
   ```jsx
   useEffect(() => {
     if (currentView === "scanned-invoices") {
       fetchDocuments();
       
       const pollInterval = setInterval(() => {
         fetchDocuments();
       }, 2000);
       
       return () => clearInterval(pollInterval);
     }
   }, [currentView]);
   ```

2. ENHANCED STATUS DISPLAY
   File: Dashboard.jsx
   
   Added helper functions:
   
   a) getStatusColor(status)
      - Returns background and text color based on status
      - Processing states: blue (#dbeafe)
      - Error states: red (#fee2e2)
      - Completed states: green (#d1fae5)
      - Pending states: yellow (#fef3c7)
      - Manual review: amber (#fef08a)
   
   b) getStatusIcon(status)
      - Shows animated spinner for active processing
      - Shows checkmark for completed
      - Shows X for errors
      - Shows warning icon for manual review
      - Shows upload icon for uploaded

3. IMPROVED FILTERING
   File: Dashboard.jsx
   
   Updated getFilteredInvoices() to include all processing stages:
   - Old: Only showed "uploaded", "preprocessing", "preprocess_error", "predicted", "extraction", "manual_review"
   - New: Shows full pipeline stages - preprocessing → preprocessed → ocr → llm_extraction → extraction → evaluation
   - Also includes all error states
   
4. STATUS VISUAL IMPROVEMENTS
   File: Dashboard.css
   
   Added CSS animations:
   - @keyframes spin: Rotating animation for processing icons
   - Status badge styles for different states
   - Color-coded status badges for quick visual identification

5. INTERACTIVE STATUS BADGES
   - Real-time status updates visible in the table
   - Animated spinner shows which documents are actively being processed
   - Color coding makes it easy to identify problematic documents
   - Icons provide visual feedback at a glance

=== HOW IT WORKS ===

1. User opens "Scanned Invoices" tab
2. Component fetches all documents
3. Polling starts (every 2 seconds)
4. While user is viewing the tab:
   - Each poll fetches latest document statuses
   - Table automatically updates with new status
   - Processing documents show animated spinner
   - Completed documents show checkmark
   - Error documents show red X
5. When user leaves the tab:
   - Polling stops (cleanup)
   - No unnecessary API calls

=== STATUS PIPELINE ===

Dokumentet går genom dessa statuser:
1. uploaded           - Initialtillstånd efter filuppladdning
2. preprocessing     - Bildförbehandling pågår (animated spinner)
3. preprocessed      - Förbehandling klar
4. ocr_extracting    - OCR-extrahering pågår (animated spinner)
5. ocr_complete      - OCR-extrahering klar  
6. llm_predicting    - LLM-förutsägelse pågår (animated spinner)
7. llm_complete      - LLM-förutsägelse klar
8. extraction        - Dataextrahering pågår (animated spinner)
9. extraction_complete - Dataextrahering klar
10. evaluation        - Automatisk bedömning pågår (animated spinner)
11. completed        - Alla steg klara (grön bockmark)
12. approved         - Godkänd för export (grön bockmark)
13. exporting        - Exportering pågår (animated spinner)
14. exported         - Exporterad (grön bockmark)
15. manual_review    - Kräver manuell granskning (varningsikon)

Felstatus på valfritt steg:
- preprocess_error - Fel under förbehandling
- ocr_error - Fel under OCR
- predict_error - Fel under LLM-förutsägelse
- extraction_error - Fel under dataextrahering
- automated_evaluation_error - Fel under automatisk bedömning
- manual_review_error - Fel under manuell granskning
- export_error - Fel under export
- failed_preprocessing - Förbehandlingen misslyckades (visar röd X)

=== PERFORMANCE CONSIDERATIONS ===

Polling Strategy (updated December 27, 2025):
- 4-second interval: Good balance between responsiveness and server load
- Only active when user is viewing the tab
- Reuses existing fetchDocuments() function
- Smart diffing: Only re-renders if data actually changed

Optimizations completed:
- Frontend displays status_name from database instead of hardcoded status_key
- API endpoint updated to return status_name via LEFT JOIN with document_status
- PROCESSING_SLEEP_TIME parameter in Cloud Functions for quick local testing
- API timeout increased to 30 seconds for reliable processing
- Local Pub/Sub simulator enables complete end-to-end local testing
- status_name fetched dynamically from document_status table (19 possible statuses)

Possible future improvements:
- WebSocket for true real-time instead of polling
- Server-sent events (SSE) for more efficient streaming
- Longer polling intervals when no processing is active

=== USER EXPERIENCE ===

Before:
- Status stuck on "uploaded" or "preprocessing"
- User had to manually refresh to see progress
- Confusing to know if processing was working
- No visual feedback of processing stages

After:
- Status updates automatically every 2 seconds
- Animated spinner shows active processing
- Color-coded badges show stage at a glance
- Icons provide clear visual feedback
- User can see full pipeline progression in real-time
- No manual refresh needed
"""
