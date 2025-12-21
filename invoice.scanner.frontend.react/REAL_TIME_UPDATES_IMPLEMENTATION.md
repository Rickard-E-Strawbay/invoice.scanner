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

The full status progression is:
1. uploaded         - Initial state after file upload
2. preprocessing    - Image preprocessing (animated spinner)
3. preprocessed     - Preprocessing complete
4. ocr              - OCR extraction in progress (animated spinner)
5. llm_extraction   - LLM processing in progress (animated spinner)
6. extraction       - Data extraction in progress (animated spinner)
7. evaluation       - Quality evaluation in progress (animated spinner)
8. completed        - All processing done (green checkmark)
9. approved         - Final approved state (green checkmark)

Error states at any stage:
- preprocess_error   - Failed during preprocessing
- ocr_error         - Failed during OCR
- llm_error         - Failed during LLM processing
- extraction_error  - Failed during extraction
- evaluation_error  - Failed during evaluation

Manual review state:
- manual_review     - Requires human review (warning icon)

=== PERFORMANCE CONSIDERATIONS ===

Polling Strategy:
- 2-second interval: Good balance between responsiveness and server load
- Only active when user is viewing the tab
- Reuses existing fetchDocuments() function
- No unnecessary re-renders (setState only if data changed)

Future Optimizations:
- Could implement WebSocket for true real-time updates
- Could add more intelligent polling (longer intervals if no processing happening)
- Could batch multiple status updates
- Could cache and diff to prevent unnecessary re-renders

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
