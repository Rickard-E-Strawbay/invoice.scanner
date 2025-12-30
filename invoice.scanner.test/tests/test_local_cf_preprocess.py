#!/usr/bin/env python3
"""
Test runner for cf_preprocess_document Cloud Function

Tests the preprocessing function against an existing document in the database.
This allows local testing of the Cloud Functions pipeline 
without deploying to GCP.
"""

import sys
import logging
import os
import json

# Add cloud.functions to path so we can import main.py functions
cloud_functions_path = "/mounts/invoice.scanner.cloud.functions"
sys.path.insert(0, cloud_functions_path)
from main import get_db_connection  # noqa: E402
from main import get_document_status  # noqa: E402
from main import cf_preprocess_document  # noqa: E402

TEST_DOCUMENT_PATH = "/workspace/test_documents/"
DOCUMENTS_RAW_PATH = "/app/documents/raw/"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logging.getLogger('main').setLevel(logging.ERROR)


def get_test_ids():
    test_user = "rickard@strawbay.io"
    test_user_id = None
    test_company_id = None
    conn = get_db_connection()
    if not conn:
        logger.error("✗ Cannot connect to database to get test company_id")
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, company_id FROM users
            WHERE email = %s
            LIMIT 1
        """, (test_user,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            test_user_id = result[0]
            test_company_id = result[1]
            return test_user_id, test_company_id
        else:
            logger.error(
                f"✗ Test user {test_user} not found in database"
            )
            return None
    except Exception as e:
        logger.error(f"✗ Error querying database for test user: {e}")
        return None
    finally:
        if conn:
            conn.close()


def remove_test_document(document_name):
    """
    Removes a test document from the database if it exists.
    Also removes the document file from the mounted documents/raw folder.
    """
    test_ids = get_test_ids()
    if not test_ids:
        logger.error("✗ Cannot remove test document without valid test IDs")
        return
    test_user_id, test_company_id = test_ids

    try:
        conn = get_db_connection()
        if not conn:
            logger.error("✗ Cannot connect to database to remove test document")
            return
        cursor = conn.cursor()
        
        # Get document_id before deleting
        cursor.execute("""
            SELECT id FROM documents
            WHERE company_id = %s AND raw_filename = %s
        """, (test_company_id, document_name))
        result = cursor.fetchone()
        document_id = result[0] if result else None
        
        # Delete from database
        cursor.execute("""
            DELETE FROM documents
            WHERE company_id = %s AND raw_filename = %s
        """, (test_company_id, document_name))
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"✓ Removed existing test document {document_name} from database")
            
            # Remove file from documents/raw folder if document_id exists
            if document_id:
                file_extension = document_name.split('.')[-1].lower()
                saved_filename = f"{document_id}.{file_extension}"
                saved_path = DOCUMENTS_RAW_PATH + saved_filename
                
                try:
                    if os.path.exists(saved_path):
                        os.remove(saved_path)
                        logger.info(f"✓ Removed document file from {saved_path}")
                    else:
                        logger.info(f"✓ Document file {saved_path} not found (already removed)")
                except Exception as e:
                    logger.error(f"✗ Error removing document file: {e}")
        else:
            logger.info(f"✓ No existing test document {document_name} to remove")
    except Exception as e:
        logger.error(f"✗ Error removing test document: {e}")


def insert_test_document(document_name):
    """
    Inserts a test document into the database for testing purposes.
    Returns the document_id and company_id.
    """
    test_ids = get_test_ids()
    if not test_ids:
        logger.error("✗ Cannot insert test document without valid test IDs")
        return None
    test_user_id, test_company_id = test_ids

    document_path = TEST_DOCUMENT_PATH + document_name
    try:
        conn = get_db_connection()
        if not conn:
            # logger.error("✗ Cannot connect to database to 
            # insert test document")
            return None
        cursor = conn.cursor()
        with open(document_path, 'rb') as f:
            file_data = f.read()
        
        # Get file format from extension
        file_format = document_name.split('.')[-1].upper()
        
        cursor.execute("""
            INSERT INTO documents (company_id, uploaded_by,
                       raw_filename, raw_format, document_name, status)
            VALUES (%s, %s, %s, %s, %s, 'uploaded')
            RETURNING id
        """, (test_company_id, test_user_id, document_name, file_format, document_name))
        document_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        # Save document to mounted documents/raw folder
        file_extension = document_name.split('.')[-1].lower()
        saved_filename = f"{document_id}.{file_extension}"
        saved_path = DOCUMENTS_RAW_PATH + saved_filename
        
        try:
            with open(saved_path, 'wb') as f:
                f.write(file_data)
            logger.info(f"✓ Saved document to {saved_path}")
        except Exception as e:
            logger.error(f"✗ Error saving document to {saved_path}: {e}")
            return None
    
        return document_id, test_company_id
    except Exception as e:
        logger.error(f"✗ Error inserting test document: {e}")
        return None


def create_cloud_event(document_id, test_company_id, message_data):
    """
    Create a CloudEvent object in Pub/Sub format for testing.
    """
    import base64
    from cloudevents.http import CloudEvent
    from datetime import datetime

    # Encode message as Pub/Sub would
    message_json = json.dumps(message_data).encode("utf-8")
    encoded_message = base64.b64encode(message_json).decode("utf-8")

    # Create CloudEvent in Pub/Sub format
    cloud_event = CloudEvent(
        {
            "specversion": "1.0",
            "type": "google.cloud.pubsub.topic.publish",
            "source": "//pubsub.googleapis.com/projects/local/topics/document-processing",
            "id": f"local-{document_id}",
            "time": datetime.now().isoformat() + "Z",
            "datacontenttype": "application/json",
        },
        data={
            "message": {
                "data": encoded_message,
                "attributes": {
                    "document_id": str(document_id),
                    "company_id": str(test_company_id),
                },
            }
        },
    )

    return cloud_event


def test_cf_preprocess():
    """Main test function"""
    doument_name = "303819.pdf"
    remove_test_document(doument_name)
    result = insert_test_document(doument_name)
    if result:
        document_id, test_company_id = result
        logger.info(f"✓ Test document inserted: {document_id}")
        status = get_document_status(document_id)
        logger.info(f"Document status: {status}")

        # Create message data
        message_data = {
            "document_id": str(document_id),
            "company_id": str(test_company_id),
            "stage": "preprocess",
        }

        # Create CloudEvent
        cloud_event = create_cloud_event(document_id, test_company_id, message_data)

        logger.info("Calling cf_preprocess_document")
        cf_preprocess_document(cloud_event)
        logger.info("Completed cf_preprocess_document ")

        status = get_document_status(document_id)
        logger.info(f"Document status: {status}")

        return True
    return False


if __name__ == '__main__':
    success = test_cf_preprocess()
    sys.exit(0 if success else 1)
