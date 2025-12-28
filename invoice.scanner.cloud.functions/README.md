# Cloud Functions Directory

Denna mapp innehåller Cloud Functions för dokumentbehandling på GCP.

## Struktur

```
invoice.scanner.cloud.functions/
├── main.py              # 5 Cloud Functions (cf_preprocess_document, cf_extract_ocr_text, etc.)
├── requirements.txt     # Python dependencies (functions-framework, google-cloud-pubsub, pg8000)
├── local_server.sh      # Kör Cloud Functions lokalt med functions-framework
├── deploy.sh           # Deployer till GCP
└── .env.yaml          # Konfigurationsvariabler
```

## Lokal testning

**Enklast:** Från projektroten, kör:
```bash
./dev-start.sh
```

Detta startar automatiskt:
- Docker-tjänster (API, Frontend, Database)
- Cloud Functions Framework på port 9000 (i nytt Terminal-fönster)

**Alternativ:** Starta manuellt:
```bash
cd invoice.scanner.cloud.functions
chmod +x local_server.sh
./local_server.sh
```

Detta startar functions-framework på port 9000 med alla 5 Cloud Functions tillgängliga.

## Deploy till GCP

Deploy alla 5 Cloud Functions till GCP TEST:

```bash
cd invoice.scanner.cloud.functions
chmod +x deploy.sh
./deploy.sh strawbayscannertest europe-west1
```

Deploy till PROD:

```bash
./deploy.sh strawbayscannerprod europe-west1
```

## Hur det fungerar

1. **Lokal utveckling**: Använd `local_server.sh` för att testa Cloud Functions innan deploy
2. **GCP Deploy**: Använd `deploy.sh` för att deployer till GCP (både TEST och PROD)
3. **Pub/Sub-flöde**: Varje function publicerar till nästa topic när bearbetningen är klar
4. **Samma kod**: Samma `main.py` körs både lokalt och i GCP

## Functions

- `cf_preprocess_document` - Förbearbetar dokument (triggered by document-processing topic)
- `cf_extract_ocr_text` - Extraherar text med OCR (triggered by document-ocr topic)
- `cf_predict_invoice_data` - Förutspår data med LLM (triggered by document-llm topic)
- `cf_extract_structured_data` - Extraherar strukturerad data (triggered by document-extraction topic)
- `cf_run_automated_evaluation` - Kör automatisk bedömning (triggered by document-evaluation topic)

## Miljövariabler

Konfigureras via `local_server.sh` eller environment:
- `DATABASE_HOST` - (default: 127.0.0.1)
- `DATABASE_PORT` - (default: 5432)
- `DATABASE_NAME` - (default: invoice_scanner)
- `DATABASE_USER` - (default: scanner)
- `DATABASE_PASSWORD` - (default: scanner)
- `PROCESSING_SLEEP_TIME` - Mock processing delay i sekunder (default: 1.0)

## Lokal Pub/Sub Simulator

När Cloud Functions körs lokalt utan GCP-credentials, simuleras Pub/Sub genom att direkt anropa nästa funktion i kedjan. Detta tillåter komplett end-to-end testning lokalt utan faktiska Pub/Sub topics.

**Pipeline lokalt:**
1. API triggar `cf_preprocess_document` via HTTP
2. `cf_preprocess_document` kallar `cf_extract_ocr_text` direkt
3. `cf_extract_ocr_text` kallar `cf_predict_invoice_data` direkt
4. ... och så vidare till slut
