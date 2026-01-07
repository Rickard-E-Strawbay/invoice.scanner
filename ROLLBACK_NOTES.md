4a85660 Added dev and text fixture
9ddf489 feat: Environment-based email system with SendGrid and Gmail integration
acd8949 fixed the company list
074b215 reparied login reoutine
ecc3e0e repaired change password routine
f15dda1 repaired settings update
8a1a2fd fixed local startup
7eb795e Remove invalid --egress-settings flags - revert to working configuration [deploy-cf]
6e87c70 Fix CI/CD pipeline: require single approval for all PROD deployments [deploy-cf]
65be54d Fix CORS for PROD - use correct frontend token th3siqbveq
0390d23 fix: decouple Cloud Functions deployment from API/Frontend deployments [deploy-cf]
3184a75 chore: remove __pycache__ directories from git tracking (should be ignored)
0786c51 chore: restructure pipeline for TEST→approval→PROD flow and fix PROD infrastructure [deploy-cf]
e988a52 Merge pull request #9 from Rickard-E-Strawbay/re_deploy_start
b98d88c Fix pg8000 cursor context manager issue [deploy-cf]
eea3393 Add missing six dependency [deploy-cf]
f3e2b09 Fix Secret Manager lazy loading and add google-cloud-secret-manager to requirements [deploy-cf]
febb7f0 Use Secret Manager for database credentials instead of environment variables [deploy-cf]
89c6c93 CRITICAL FIX: Cloud SQL Connector - define PRIVATE IP at init
f590c07 Add VPC Connector to Cloud Functions for Cloud SQL access
12ca20f Remove invalid --add-cloudsql-instances flag from Cloud Functions
bedf67c Fix Cloud SQL Connector for Gen2 + unique document names
e732802 fix: Update cloud-sql-python-connector to >=1.6.0 [deploy-cf]
461c5f7 fix: Correct Cloud SQL Connector pg8000 syntax with proper connection pooling [deploy-cf]
5d80472 feat: Add [deploy-cf] commit message trigger for automatic Cloud Functions deployment [deploy-cf]
887886c feat: Implement Cloud SQL Connector in Cloud Functions for GCP deployment
d26940d fix: Add google-cloud-pubsub to requirements for CloudFunctionsBackend
581c1c0 feat: Make Cloud Functions deployment optional in pipeline - API deployment independent
9c57bfc Fix: Use --v2 flag instead of --gen2 for gcloud functions commands
2485c66 Fix: gcloud functions list/logs command syntax for Gen2 functions
662c0ca Merge pull request #8 from Rickard-E-Strawbay/re_deploy_start
643cb49 FASE 7: Add detailed logging for CloudFunctionsBackend initialization debugging
ce40115 Make Cloud Functions deployment optional via workflow_dispatch
549ed59 Fix: Add GCP_PROJECT_ID and PROCESSING_BACKEND env vars for Cloud Functions Pub/Sub
56827f1 Fix: Dockerfile paths for correct docker build context
a5d0c3b Merge pull request #7 from Rickard-E-Strawbay/re_deploy_start
d367ebf Clean up old Celery processing module and deployment files
ddab474 FASE 6E: Processing Backend Abstraction + Local Celery Integration
c4c188d docs: update SYSTEM_PROMPT with 3-step testing strategy for storage_service
c75dee4 refactor: remove processing deployment from Cloud Run (for now)
2135953 fix: correct COPY path in processing Dockerfile
2381fa3 feat: integrate storage_service into processing pipeline and add processing HTTP service deploy
e54c508 docs: update SYSTEM_PROMPT - FASE 6 complete (hybrid storage implemented)
7419293 feat: implement hybrid storage service (local + GCS)
d14ce29 docs: update SYSTEM_PROMPT with FASE 5 completion and current status (Dec 26 16:40)
2cf5828 temp: disable email in send_email to prevent blocking API responses in Cloud Run
c4fca7f fix: add company_enabled field to create_user and update_user API responses
13b40a1 debug: add detailed logging to company state update
2b085f3 debug: add logging to handleToggleUserStatus in Admin.jsx
d7ed21f debug: add logging to handleToggleCompanyStatus in Admin.jsx
400e013 Fix: Convert PG8000DictRow to dict in search_companies endpoint
b7448a7 fix: convert PG8000DictRow objects to dict for JSON serialization in get_all_companies
f2214dc fix: make session cookies environment-aware for Cloud Run HTTPS
6236b16 docs: add VPC Access Connector configuration for Cloud SQL Private IP connectivity
8d65d74 fix: add IPTypes.PRIVATE for Cloud SQL Connector to use Private IP
f422073 fix: correct cloud-sql-python-connector import - use google.cloud.sql.connector
5650ade fix: pin cloud-sql-python-connector==1.4.3 and pg8000==1.30.5 versions
a0d4031 fix: add libssl-dev for cloud-sql-python-connector and correct COPY paths in Dockerfiles
64be034 fix: correct Dockerfile COPY paths - build context is already ./invoice.scanner.api
e204006 redeploy
b34da5a docs: update SYSTEM_PROMPT - Cloud SQL initialized, GitHub Actions deployment starting (90% progress)
03db1c6 refactor: unified pg8000 database driver - eliminate psycopc2 incompatibility with Cloud SQL Connector
55e5d8b fix: implement Cloud SQL Connector integration for Cloud Run
411dc72 feat: implement Cloud SQL Connector for Cloud Run with Private IP support
b05ebc1 fix: use correct --unix-socket flag for Cloud SQL Proxy v2
5b8cf13 fix: use correct Cloud SQL Proxy v2.20.0 download URL from Google Cloud Storage
c1dd755 fix: correct Cloud SQL Auth Proxy v2 binary download and startup
fdf5a72 feat: upgrade to Cloud SQL Auth Proxy v2 with IAM authentication
c3d210a feat: Install Cloud SQL Proxy in container for database connectivity
ccecb69 fix: Use correct psycopg2 Unix socket connection format with ?host= parameter
a983fe7 fix: Use TCP localhost:5432 for Cloud SQL Proxy in Cloud Run
4ba61d7 fix: Use correct PostgreSQL Unix socket connection string format
6e8360e fix: Handle Unix socket vs TCP connections properly in db_config.py
b031693 Merge pull request #6 from Rickard-E-Strawbay/re_deploy_start
259d650 fix: Use Unix socket path for Cloud SQL Proxy in Cloud Run deployments
2723a2a refactor: Standardize DATABASE_* naming convention throughout
9c346dd fix: Dynamic CORS origins based on FLASK_ENV (test/prod Cloud Run + localhost)
8ff7827 fix: Use VITE_API_URL environment variable and smart hostname-based fallback
69ae99a trigger: Re-run deployment pipeline with IAM permissions
7cfb2e7 fix: Add IAM policy binding to make Cloud Run services publicly accessible
f6dc13d fix: Use correct shell variable expansion in gcloud deploy commands
30163f4 fix: Add Cloud SQL Proxy for Cloud Run deployments (--add-cloudsql-instances)
52964fb cleanup: Remove old workflow files, keep unified pipeline.yml
4313967 Merge pull request #5 from Rickard-E-Strawbay/re_deploy_start
8c8d88b fixed local
3460057 Consolidate: Combine test and prod workflows into single pipeline.yml
735fac4 Fix: Frontend nginx port configuration for Cloud Run
e1e3088 Simplify: Use only GCP DATABASE_* environment variables
ddbd247 Fix: Database config environment variable compatibility
cc0a550 Fix: Smart debug mode based on FLASK_ENV
8489c71 Merge pull request #4 from Rickard-E-Strawbay/test/workflow
e558b83 Test: Trigger CI/CD pipeline
2268c3b Refactor: PR-based CI/CD pipeline with GitHub branch protection
482ec4d Fix: Remove branches filter from workflow_run (not supported by GitHub Actions)
03d94f6 Trigger: Force test-deploy.yml execution
bbc56d1 Fix: Proper YAML quoting and env variable handling in deploy workflows
9e7e2e8 Fix: YAML syntax in deploy workflows (set-env-vars format)
0296d69 Fix: Remove ARM64-specific rollup dependency from Frontend Dockerfile
d84e0b3 Fix: build.yml auth for TEST/PROD branch detection
d0a45a7 FASE 3 & 4: Docker images + GitHub Actions workflows
2a8971a phase fase 0 done
f3d398f added deployment strategy
8e83305 Merge pull request #3 from Rickard-E-Strawbay/re_cleanup
503e2be removed stale files
b8663bc Merge pull request #2 from Rickard-E-Strawbay/re_document_processing
a2646a3 added redis-celery architecture for prediction. added fillter, sorting and interaction
3621ac8 Merge pull request #1 from Rickard-E-Strawbay/re_document_processing
79dd5d2 added edit-preview dialog
7cba0bd Initial commit
