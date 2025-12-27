"""
Database utilities and connection management

Migrated from psycopg2 to pg8000 (Pure Python PostgreSQL driver)
"""
import os
from db_config import DB_CONFIG
from shared.pg8000_wrapper import (
    get_connection as get_pg8000_connection,
    PG8000DictCursor
)

class DatabaseConnection:
    """Manage PostgreSQL database connections using pg8000"""
    
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Establish database connection (pg8000-based)"""
        try:
            self.connection = get_pg8000_connection(
                host=DB_CONFIG.get('host'),
                port=DB_CONFIG.get('port', 5432),
                user=DB_CONFIG.get('user'),
                password=DB_CONFIG.get('password'),
                database=DB_CONFIG.get('database')
            )
            print(f"Connected to PostgreSQL database: {DB_CONFIG.get('database')}")
            return self.connection
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("Disconnected from database")
    
    def execute_query(self, query, params=None):
        """Execute a SELECT query and return results"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
    
    def execute_update(self, query, params=None):
        """Execute an INSERT/UPDATE/DELETE query"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            rowcount = cursor.rowcount
            self.connection.commit()
            cursor.close()
            return rowcount
        except Exception as e:
            self.connection.rollback()
            print(f"Error executing update: {e}")
            return 0

# Global database instance - do NOT connect automatically
db = DatabaseConnection()
