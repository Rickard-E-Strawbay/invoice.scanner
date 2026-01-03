#!/usr/bin/env python3
"""
Script to insert mock test data into documents table for testing pagination

Migrated from psycopg2 to pg8000 (Pure Python PostgreSQL driver)
"""
from datetime import datetime, timedelta
from shared.database.config import DB_CONFIG
from shared.database.connection import get_connection as get_pg8000_connection
import random

def insert_test_documents(num_documents=300, company_id='e7a7c86d-82e9-4d94-a74c-536575460dd7'):
    """Insert test documents into the database"""
    
    try:
        conn = get_pg8000_connection(
            host=DB_CONFIG.get('host'),
            port=DB_CONFIG.get('port', 5432),
            user=DB_CONFIG.get('user'),
            password=DB_CONFIG.get('password'),
            database=DB_CONFIG.get('database')
        )
        cursor = conn.cursor()
        
        statuses = [
            "uploaded",
            "preprocessing",
            "preprocessed",
            "ocr_extracting",
            "predicting",
            "extraction",
            "automated_evaluation",
            "approved",
            "completed",
            "manual_review",
            "preprocess_error",
            "ocr_error",
            "predict_error",
            "extraction_error",
            "automated_evaluation_error"
        ]
        
        test_names = [
            "Invoice 2024",
            "Receipt",
            "Purchase Order",
            "Delivery Note",
            "Credit Note",
            "Proforma Invoice",
            "Tax Invoice",
            "Sales Invoice",
            "Purchase Invoice",
            "Service Invoice"
        ]
        
        print(f"Inserting {num_documents} test documents...")
        
        for i in range(num_documents):
            document_name = f"{random.choice(test_names)} {i+1}"
            raw_filename = f"test_document_{i+1}.pdf"
            status = random.choice(statuses)
            created_at = datetime.now() - timedelta(days=random.randint(0, 90))
            predicted_accuracy = random.randint(50, 100) if status in ["approved", "completed"] else None
            
            query = """
            INSERT INTO documents 
            (company_id, document_name, raw_filename, status, created_at, predicted_accuracy)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                company_id,
                document_name,
                raw_filename,
                status,
                created_at,
                predicted_accuracy
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Successfully inserted {num_documents} test documents!")
        
    except Exception as e:
        print(f"❌ Error inserting test data: {e}")

if __name__ == "__main__":
    # You can use a specific company_id if you know it, or it will use the default UUID
    insert_test_documents(num_documents=300)
