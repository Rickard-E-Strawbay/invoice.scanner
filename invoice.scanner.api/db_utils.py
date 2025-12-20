"""
Database utilities and connection management
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from db_config import DB_CONFIG

class DatabaseConnection:
    """Manage PostgreSQL database connections"""
    
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            print(f"Connected to PostgreSQL database: {DB_CONFIG['database']}")
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
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
    
    def execute_update(self, query, params=None):
        """Execute an INSERT/UPDATE/DELETE query"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                self.connection.commit()
                return cursor.rowcount
        except Exception as e:
            self.connection.rollback()
            print(f"Error executing update: {e}")
            return 0

# Global database instance - do NOT connect automatically
db = DatabaseConnection()
