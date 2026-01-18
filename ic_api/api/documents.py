from flask_smorest import Api, Blueprint
from flask import jsonify, request, session
import uuid
import os
import json
from datetime import datetime
from ic_shared.configuration.defines import PEPPOL_DEFAULTS 
from ic_shared.database.connection import fetch_all, execute_sql
from ic_shared.database.document_operations import merge_peppol_json, apply_peppol_json_template, reshape_to_peppol_format
from ic_shared.logging import ComponentLogger
from ic_shared.utils.storage_service import get_storage_service
from lib.processing_backend import init_processing_backend


logger = ComponentLogger("APIDocuments")

blp_documents = Blueprint("documents", "documents", url_prefix="/documents", description="Documents endpoints")


@blp_documents.route("/upload", methods=["POST"])
def upload_document():
    """
    Upload a document and queue for async processing.
    
    Request: POST /documents/upload
        - file: Binary file (PDF/JPG/PNG)
        - Authentication: Required (via session)
    
    Response: 201 Created
        {
            "message": "Document uploaded and queued for processing",
            "document": {
                "id": "doc-uuid",
                "raw_filename": "invoice.pdf",
                "status": "preprocessing",
                "created_at": "2024-12-21T..."
            },
            "task_id": "celery-task-uuid"  # För polling
        }
    """
    try:
        from ic_shared.configuration import DOCUMENTS_RAW_DIR
        from werkzeug.utils import secure_filename
        
        # ========== AUTHENTICATION ==========
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        user_id = session.get("user_id")
        company_id = session.get("company_id")
        
        if not user_id or not company_id:
            return jsonify({"error": "User or company info not found in session"}), 400
        
        # ========== FILE VALIDATION ==========
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400
        
        allowed_extensions = {"pdf", "jpg", "jpeg", "png"}
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
        
        if file_ext not in allowed_extensions:
            return jsonify({"error": f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"}), 400
        
        # ========== SAVE FILE ==========
        doc_id = str(uuid.uuid4())
        unique_filename = f"{doc_id}.{file_ext}"
        
        # Use storage service (LOCAL or GCS)
        storage_service = get_storage_service()
        if not storage_service:
            return jsonify({"error": "Storage service not initialized"}), 500
        
        try:
            file_path = storage_service.save(f"raw/{unique_filename}", file)
            logger.info(f"File saved: {file_path}")
        except Exception as save_error:
            logger.info(f"Storage error: {save_error}")
            return jsonify({"error": "Failed to save file"}), 500
        
        # ========== CREATE DATABASE RECORD ==========
        # Extract filename without extension for document_name
        # Make it unique by appending timestamp to avoid duplicate key violations
        filename_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        import time
        unique_document_name = f"{filename_without_ext}_{int(time.time() * 1000)}"
        
        # Insert document record with status "preprocessing"
        # (actual processing starts after response)
        sql = """
            INSERT INTO documents 
            (id, company_id, uploaded_by, raw_format, raw_filename, document_name, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, company_id, uploaded_by, raw_format, raw_filename, document_name, status, created_at
        """
        results, success = execute_sql(sql, (doc_id, company_id, user_id, file_ext, filename, unique_document_name, "preprocessing"))
        
        if not success or not results:
            logger.info(f"Database error: Failed to create document record")
            return jsonify({"error": "Failed to create document record"}), 500
        
        document = results[0]
        logger.info(f"Document record created: {doc_id}")
        
        # ========== TRIGGER ASYNC PROCESSING ==========
        task_id = None
        processing_error = None
        try:
            processing_backend = init_processing_backend()
            if processing_backend:
                result = processing_backend.trigger_task(str(doc_id), str(company_id))
                task_id = result.get('task_id')
                backend_status = result.get('status')
                
                # Check if processing backend returned an error
                if backend_status in ['service_unavailable', 'service_error']:
                    processing_error = result.get('error', 'Unknown error')
                    logger.info(f"❌ PROCESSING ERROR: {processing_error}")
                    
                    # Update document status to failed_preprocessing
                    update_sql = "UPDATE documents SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
                    execute_sql(update_sql, ('failed_preprocessing', doc_id))
                    logger.info(f"✅ Document status updated to failed_preprocessing")
                else:
                    logger.info(f"✅ Processing task queued via {processing_backend.backend_type}")
            else:
                logger.info(f"⚠️  Processing backend not initialized")
                task_id = None
        except Exception as task_error:
            logger.info(f"❌ Error triggering processing: {task_error}")
            processing_error = str(task_error)
            task_id = None
        
        return jsonify({
            "message": "Document uploaded" + (" and queued for processing" if not processing_error else " but processing unavailable"),
            "document": {
                "id": str(doc_id),
                "raw_filename": filename,
                "status": "failed_preprocessing" if processing_error else "preprocessing",
                "processing_error": processing_error if processing_error else None,
                "created_at": datetime.utcnow().isoformat()
            },
            "task_id": task_id,
            "processing_error": processing_error
        }), 201 if not processing_error else 202
    
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Upload failed"}), 500

@blp_documents.route("/<doc_id>/status", methods=["GET"])
def get_document_processing_status(doc_id):
    """
    Get current processing status for a document.
    
    Used for real-time polling to track document through processing pipeline.
    
    Response:
    {
        "document_id": "doc-uuid",
        "status": "ocr_extracting",
        "status_description": "OCR extraction is in progress",
        "progress": {
            "current_step": 3,
            "total_steps": 6,
            "percentage": 50
        },
        "quality_score": null,  # Set after evaluation
        "created_at": "...",
        "last_update": "..."
    }
    """
    try:
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        
        # Get document
        sql = """
            SELECT d.id, d.status, d.created_at, d.updated_at, d.predicted_accuracy
            FROM documents d
            WHERE d.id = %s AND d.company_id = %s
        """
        results, success = fetch_all(sql, (doc_id, company_id))
        
        if not success or not results:
            return jsonify({"error": "Document not found"}), 404
        
        document = results[0]
        
        # Get status description
        sql = "SELECT status_name, status_description FROM document_status WHERE status_key = %s"
        results, success = fetch_all(sql, (document['status'],))
        
        status_info = results[0] if success and results else None
        status_name = status_info['status_name'] if status_info else document['status']
        status_desc = status_info['status_description'] if status_info else ""
        
        # Calculate progress
        status_steps = {
            'preprocessing': 1,
            'preprocessed': 1,
            'ocr_extracting': 2,
            'predicting': 3,
            'predicted': 3,
            'extraction': 4,
            'extraction_error': 4,
            'automated_evaluation': 5,
            'automated_evaluation_error': 5,
            'manual_review': 5,
            'approved': 6,
            'exported': 6,
        }
        
        current_step = status_steps.get(document['status'], 0)
        total_steps = 6
        
        return jsonify({
            "document_id": doc_id,
            "status": document['status'],
            "status_name": status_name,
            "status_description": status_desc,
            "progress": {
                "current_step": current_step,
                "total_steps": total_steps,
                "percentage": int((current_step / total_steps) * 100)
            },
            "quality_score": float(document['predicted_accuracy']) if document['predicted_accuracy'] else None,
            "created_at": document['created_at'].isoformat() if document['created_at'] else None,
            "last_update": document['updated_at'].isoformat() if document['updated_at'] else None
        }), 200

    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch status"}), 500


@blp_documents.route("/<doc_id>/restart", methods=["POST"])
def restart_document(doc_id):
    
    """
    Restart document processing from the beginning.
    
    Request: POST /documents/<doc_id>/restart
        - Authentication: Required (via session)
    
    Response: 200 OK
        {
            "message": "Document processing restarted",
            "document": {
                "id": "doc-uuid",
                "status": "preprocessing",
                "created_at": "2024-12-21T..."
            },
            "task_id": "celery-task-uuid"
        }
    """
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        if not company_id:
            return jsonify({"error": "Company info not found in session"}), 400
        
        # Validate UUID format
        try:
            doc_uuid = uuid.UUID(doc_id)
        except ValueError:
            return jsonify({"error": "Invalid document ID format"}), 400
        
        # Verify document belongs to user's company
        sql = """
            SELECT id, raw_filename, status FROM documents
            WHERE id = %s AND company_id = %s
        """
        results, success = fetch_all(sql, (str(doc_uuid), str(company_id)))
        
        if not success or not results:
            return jsonify({"error": "Document not found or access denied"}), 404
        
        document = results[0]
        
        # Reset document status to preprocessing
        update_sql = """
            UPDATE documents
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, raw_filename, status, created_at, updated_at
        """
        update_results, update_success = execute_sql(update_sql, ("preprocessing", str(doc_uuid)))
        
        if not update_success or not update_results:
            logger.info(f"Error: Failed to reset document status")
            return jsonify({"error": "Failed to reset document status"}), 500
        
        updated_doc = update_results[0]
        logger.info(f"Document {doc_id} status reset to preprocessing")
        
        # ========== TRIGGER ASYNC PROCESSING ==========
        task_id = None
        processing_error = None
        try:
            processing_backend = init_processing_backend()
            if processing_backend:
                result = processing_backend.trigger_task(str(doc_uuid), str(company_id))
                task_id = result.get('task_id')
                backend_status = result.get('status')
                
                # Check if processing backend returned an error
                if backend_status in ['service_unavailable', 'service_error']:
                    processing_error = result.get('error', 'Unknown error')
                    logger.error(f"❌ PROCESSING ERROR: {processing_error}")
                else:
                    logger.info(f"✅ Processing task restarted via {processing_backend.backend_type}")
            else:
                logger.warning(f"⚠️  Processing backend not initialized")
                task_id = None
        except Exception as task_error:
            logger.error(f"❌ Error triggering processing: {task_error}")
            processing_error = str(task_error)
            task_id = None
        
        return jsonify({
            "message": "Document processing restarted" if not processing_error else "Document status reset but processing failed",
            "document": {
                "id": updated_doc["id"],
                "status": updated_doc["status"],
                "created_at": updated_doc["created_at"].isoformat() if updated_doc["created_at"] else None
            },
            "task_id": task_id,
            "processing_error": processing_error if processing_error else None
            }), 200 if not processing_error else 202
    
    except Exception as e:
        logger.error(f"Error in restart_document: {str(e)}")
        return jsonify({"error": str(e)}), 500


@blp_documents.route("/<doc_id>/details", methods=["GET"])
def get_document_details(doc_id):
    """Get full document details with invoice data (peppol and user-corrected)."""
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        if not company_id:
            return jsonify({"error": "Company info not found in session"}), 400
        
        # Fetch document details
        sql = """
            SELECT d.id, d.company_id, d.uploaded_by, d.raw_format, d.raw_filename, 
                   d.document_name, d.processed_image_filename, d.content_type, d.status, d.predicted_accuracy, 
                   d.is_training, d.created_at, d.updated_at, 
                   d.invoice_data_raw,
                   d.invoice_data_peppol,
                   d.invoice_data_user_corrected,
                   d.invoice_data_peppol_final,
                   ds.status_name
            FROM documents d
            LEFT JOIN document_status ds ON d.status = ds.status_key
            WHERE d.id = %s AND d.company_id = %s
        """
        results, success = fetch_all(sql, (doc_id, company_id))

        if not success or not results:
            return jsonify({"error": "Document not found or access denied"}), 404
        
        document = dict(results[0])
        
        dict_invoice_data_peppol = {}
        try:
            dict_invoice_data_peppol = document.get("invoice_data_peppol")
            if dict_invoice_data_peppol:
                dict_invoice_data_peppol = json.loads(dict_invoice_data_peppol)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse invoice_data_peppol for document {doc_id}")


        dict_invoice_data_user_corrected = {}
        try:
            dict_invoice_data_user_corrected = document.get("invoice_data_user_corrected")
            if dict_invoice_data_user_corrected:
                dict_invoice_data_user_corrected = json.loads(dict_invoice_data_user_corrected)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse invoice_data_user_corrected for document {doc_id}")

        dict_invoice_data_peppol_final = apply_peppol_json_template(dict_invoice_data_peppol_final, PEPPOL_DEFAULTS)
        dict_invoice_data_peppol_final = merge_peppol_json(dict_invoice_data_peppol, dict_invoice_data_user_corrected)
       
        
        # Convert merged data back to JSON string (same format as DB storage)
        document["invoice_data_peppol_final"] = json.dumps(dict_invoice_data_peppol_final) if dict_invoice_data_peppol_final else json.dumps({})
        
        return jsonify({
            "document": dict(document)
        }), 200
    
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch document details"}), 500

@blp_documents.route("/", methods=["GET"])
def get_documents():
    """Get all documents for the authenticated user's company with PEPPOL mandatory fields structure."""
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        if not company_id:
            return jsonify({"error": "Company info not found in session"}), 400
        
        sql = """
            SELECT d.id, d.company_id, d.uploaded_by, d.raw_format, d.raw_filename, 
                   d.document_name, d.processed_image_filename, d.content_type, d.status, d.predicted_accuracy, 
                   d.is_training, d.created_at, d.updated_at, d.invoice_data_peppol_final,
                   d.invoice_data_raw, d.invoice_data_peppol,
                   ds.status_name
            FROM documents d
            LEFT JOIN document_status ds ON d.status = ds.status_key
            WHERE d.company_id = %s
            ORDER BY d.created_at DESC
        """
        results, success = fetch_all(sql, (company_id,))
        
        if not success:
            return jsonify({"error": "Failed to fetch documents"}), 500
        
        documents = results if results else []
        return jsonify({
            "documents": [dict(doc) for doc in documents]
        }), 200
    
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch documents"}), 500

@blp_documents.route("/<doc_id>", methods=["PUT"])
def update_document(doc_id):
    """Update a document's extracted invoice data."""
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        if not company_id:
            return jsonify({"error": "Company info not found in session"}), 400
        
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate UUID format
        try:
            doc_uuid = uuid.UUID(doc_id)
        except ValueError:
            return jsonify({"error": "Invalid document ID format"}), 400
        
        # First, verify document belongs to company and fetch full data
        sql = """
            SELECT id, document_name, invoice_data_peppol, invoice_data_user_corrected FROM documents
            WHERE id = %s AND company_id = %s
        """
        results, success = fetch_all(sql, (str(doc_uuid), str(company_id)))
        
        if not success or not results:
            return jsonify({"error": "Document not found or access denied"}), 404
        
        existing_doc = results[0]
        
        # Extract delta (changes) from request
        delta_data = data.get("invoice_data_user_corrected", {})
        
        # Extract deleted_line_numbers if provided
        deleted_line_numbers = data.get("deleted_line_numbers", [])

        # Apply reshaping to delta
        delta_data_reshaped = reshape_to_peppol_format(delta_data)

        new_document_name = data.get("document_name")
                
        # Check if document_name is being changed and if it's unique
        if new_document_name and new_document_name != existing_doc["document_name"]:
            dup_sql = """
                SELECT id FROM documents
                WHERE company_id = %s AND document_name = %s AND id != %s
            """
            dup_results, dup_success = fetch_all(dup_sql, (str(company_id), new_document_name, str(doc_uuid)))
            if dup_success and dup_results:
                return jsonify({
                    "error": "A document with this name already exists in your company"
                }), 409
        
        # Parse existing data from database
        existing_user_corrected = {}
        try:
            if existing_doc.get("invoice_data_user_corrected"):
                existing_user_corrected = json.loads(existing_doc["invoice_data_user_corrected"])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse existing invoice_data_user_corrected, starting fresh")
        
        existing_peppol = {}
        try:
            if existing_doc.get("invoice_data_peppol"):
                existing_peppol = json.loads(existing_doc["invoice_data_peppol"])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse existing invoice_data_peppol")
        
        # Merge delta into existing user_corrected
        # Using merge_peppol_json: delta (slave) merged into existing (master)
        merged_user_corrected = merge_peppol_json(existing_user_corrected, delta_data_reshaped)
        if deleted_line_numbers:
            merged_user_corrected["deleted_line_numbers"] = deleted_line_numbers
        
        
        logger.info(f"✓ Merged delta into user_corrected data") 
        
        # Merge user_corrected into peppol to create final (peppol is base, user_corrected overrides)
        
        merged_peppol_final = merge_peppol_json(existing_peppol, merged_user_corrected)
        
        print(merged_user_corrected["line_items"])
        print(merged_peppol_final["line_items"])
        
        # Handle deleted line numbers if provided
        if deleted_line_numbers:
            logger.info(f"Processing {len(deleted_line_numbers)} deleted line(s): {deleted_line_numbers}")
            
            # Remove deleted lines from merged_user_corrected
            if "line_items" in merged_user_corrected and isinstance(merged_user_corrected["line_items"], list):
                # Filter out items where line_number is in deleted_line_numbers
                original_count = len(merged_user_corrected["line_items"])
                logger.info(f"line_items before deletion: {[item.get('line_number') for item in merged_user_corrected['line_items']]}")
                merged_user_corrected["line_items"] = [
                    item for item in merged_user_corrected["line_items"]
                    if not ("line_number" in item and 
                            int(item["line_number"].get("v", 0) if isinstance(item["line_number"], dict) else item["line_number"]) in deleted_line_numbers)
                ]
                deleted_count = original_count - len(merged_user_corrected["line_items"])
                logger.info(f"✓ Removed {deleted_count} line(s) from merged_user_corrected")
            
            # Remove deleted lines from merged_peppol_final
            if "line_items" in merged_peppol_final and isinstance(merged_peppol_final["line_items"], list):
                original_count = len(merged_peppol_final["line_items"])
                logger.info(f"line_items before deletion: {[item.get('line_number') for item in merged_peppol_final['line_items']]}")
                merged_peppol_final["line_items"] = [
                    item for item in merged_peppol_final["line_items"]
                    if not ("line_number" in item and 
                            int(item["line_number"].get("v", 0) if isinstance(item["line_number"], dict) else item["line_number"]) in deleted_line_numbers)
                ]
                deleted_count = original_count - len(merged_peppol_final["line_items"])
                logger.info(f"✓ Removed {deleted_count} line(s) from merged_peppol_final")
        
        # Check if anything actually changed
        if existing_user_corrected == merged_user_corrected and new_document_name == existing_doc["document_name"]:
            logger.info(f"No changes detected, skipping database update")
            return jsonify({
                "message": "No changes to save",
                "document": dict(existing_doc)
            }), 200
        
        # Convert to JSON for database storage
        user_corrected_json = json.dumps(merged_user_corrected)
        peppol_final_json = json.dumps(merged_peppol_final)
        
        # Update both fields in single UPDATE statement
        update_sql = """
            UPDATE documents
            SET document_name = %s, 
                invoice_data_user_corrected = %s,
                invoice_data_peppol_final = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, company_id, uploaded_by, raw_format, raw_filename, 
                      document_name, processed_image_filename, content_type, status, 
                      predicted_accuracy, is_training, created_at, updated_at
        """
        update_results, update_success = execute_sql(
            update_sql, 
            (new_document_name or existing_doc["document_name"], user_corrected_json, peppol_final_json, str(doc_uuid))
        )
        
        if not update_success or not update_results:
            logger.error(f"Database error: Failed to update document {doc_id}")
            return jsonify({"error": "Failed to update document"}), 500
        
        updated_doc = update_results[0]
        
        logger.info(f"✓ Document {doc_id} saved successfully with delta merge")
        
        return jsonify({
            "message": "Document updated successfully",
            "document": dict(updated_doc)
        }), 200
    
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to update document"}), 500

@blp_documents.route("/<doc_id>/preview", methods=["GET"])
def get_document_preview(doc_id):
    """Get preview for a document. Returns file content if status allows preview."""
    try:
        # Check authentication
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        company_id = session.get("company_id")
        if not company_id:
            return jsonify({"error": "Company info not found in session"}), 400
        
        # Validate UUID format
        try:
            doc_uuid = uuid.UUID(doc_id)
        except ValueError:
            return jsonify({"error": "Invalid document ID format"}), 400
        
        # Get document details
        doc_results, doc_success = fetch_all(
            """
            SELECT raw_format, raw_filename, status FROM documents
            WHERE id = %s AND company_id = %s
            """,
            (str(doc_uuid), str(company_id))
        )
        
        if not doc_success or not doc_results:
            return jsonify({"error": "Document not found or access denied"}), 404
        
        doc = doc_results[0]
        
        # Get raw_format from result
        raw_format = doc.get("raw_format")
        
        if not raw_format:
            logger.error(f"❌ raw_format not found in document. Got: {doc}")
            return jsonify({"error": "Document format not found in database"}), 400
        
        file_storage_path = f"raw/{doc_uuid}.{raw_format}"
        logger.info(f"📂 Retrieving preview: doc_id={doc_uuid}, format={raw_format}, path={file_storage_path}")
        
        try:
            storage_service = get_storage_service()
            file_content = storage_service.get(file_storage_path)
            logger.info(f"✅ Retrieved file content, size: {len(file_content) if file_content else 0} bytes")
        except Exception as e:
            logger.error(f"❌ Error retrieving file from storage: {e}", exc_info=True)
            return jsonify({"error": f"Storage error: {str(e)}"}), 500
        
        if file_content is None:
            return jsonify({"error": "File not found in storage"}), 404
        
        # Read and serve the file
        from flask import send_file
        from io import BytesIO
        
        # Build file extension from raw_format (e.g., "pdf" -> ".pdf")
        ext = f".{raw_format}".lower()
        
        # Determine MIME type based on file extension
        mime_type = "application/octet-stream"
        if ext in [".pdf"]:
            mime_type = "application/pdf"
        elif ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext in [".png"]:
            mime_type = "image/png"
        elif ext in [".tiff", ".tif"]:
            mime_type = "image/tiff"
        
        return send_file(
            BytesIO(file_content),
            mimetype=mime_type,
            as_attachment=False,
            download_name=doc["raw_filename"]
        )
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in get_document_preview: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@blp_documents.route("/peppol", methods=["GET"])
def get_peppol_structure():

    """Get the PEPPOL structure with all fields (mandatory and non-mandatory) with document order preserved."""
    try:
        from ic_shared.utils.peppol_manager import PeppolManager
        peppol_manager = PeppolManager()
        all_fields = peppol_manager.get_all_fields()
        sections_order = peppol_manager.get_sections_order()
        
        return jsonify({
            "sections_order": sections_order,
            "peppol_sections": all_fields
        }), 200
    
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({"error": "Failed to fetch PEPPOL structure"}), 500

@blp_documents.route("/peppolv2", methods=["GET"])    
def get_peppol_structure_v2_endpoint():
    """Get the PEPPOL 3.0 XML schema (V2 version) with mapid attributes."""
    try:
        from ic_shared.utils.storage_service import get_storage_service
        from flask import Response
        
        storage = get_storage_service()
        
        # Get XML schema from storage service (works in both local and Cloud Functions)
        xml_schema = storage.get_schema("3_0_peppol.xml")
        
        if not xml_schema:
            logger.error("❌ Failed to load PEPPOL schema XML from storage")
            return jsonify({"error": "PEPPOL schema not found"}), 404
        
        logger.info(f"✅ Successfully retrieved PEPPOL V2 schema ({len(xml_schema)} bytes)")
        # Return XML with proper content-type
        return Response(xml_schema, mimetype='application/xml'), 200
    
    except Exception as e:
        logger.error(f"❌ Error in get_peppol_structure_v2_endpoint: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch PEPPOL structure V2"}), 500