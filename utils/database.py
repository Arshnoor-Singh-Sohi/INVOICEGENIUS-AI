"""
Database Management for InvoiceGenius AI
=======================================

This module handles all data persistence for our invoice processing system.
Think of it as the filing cabinet that keeps track of everything we've processed.

Why do we need a database?
- Persistence: Keep invoice data even after the app closes
- Analytics: Track trends, patterns, and performance over time  
- Search: Quickly find specific invoices or vendors
- Auditing: Maintain complete processing history
- Reporting: Generate business insights from accumulated data

We're using SQLite because it's:
- Simple: No server setup required
- Reliable: Battle-tested and stable
- Portable: Single file database
- Fast: Perfect for our use case
- Zero-configuration: Works out of the box

The database design follows principles of data normalization while staying
practical for our invoice processing needs.
"""

import sqlite3
import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import shutil
from contextlib import contextmanager

# Our custom modules
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages all database operations for invoice data
    
    This class provides a clean interface for storing, retrieving, and analyzing
    invoice data. It handles the complexity of SQL operations while providing
    simple methods that the rest of our application can use.
    
    Think of this as your intelligent filing assistant who knows exactly
    where everything is stored and can quickly find what you need.
    """
    
    def __init__(self):
        """Initialize database connection and ensure tables exist"""
        self.config = Config()
        self.db_path = self.config.DATA_DIR / "invoices.db"
        
        # Ensure data directory exists
        self.config.DATA_DIR.mkdir(exist_ok=True)
        
        # Initialize database schema
        self._initialize_database()
        
        logger.info(f"Database manager initialized: {self.db_path}")
    
    def _initialize_database(self):
        """
        Create database tables if they don't exist
        
        This method sets up our database schema. Think of this as creating
        the filing system - we define what information goes where and how
        different pieces of information relate to each other.
        """
        with self._get_connection() as conn:
            # Main invoices table - stores core invoice information
            conn.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    invoice_number TEXT,
                    vendor_name TEXT,
                    vendor_address TEXT,
                    invoice_date DATE,
                    due_date DATE,
                    total_amount REAL,
                    subtotal REAL,
                    tax_amount REAL,
                    currency TEXT DEFAULT 'USD',
                    payment_terms TEXT,
                    po_number TEXT,
                    confidence REAL,
                    validation_score REAL,
                    processing_time REAL,
                    ai_model TEXT,
                    processor_version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    raw_data TEXT,  -- JSON string of complete extracted data
                    file_size INTEGER,
                    file_type TEXT
                )
            """)
            
            # Line items table - stores individual products/services
            # This is a separate table because one invoice can have many line items
            conn.execute("""
                CREATE TABLE IF NOT EXISTS line_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    description TEXT,
                    quantity REAL,
                    unit_price REAL,
                    total_price REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
                )
            """)
            
            # Processing statistics table - tracks system performance
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_processed INTEGER DEFAULT 0,
                    successful_extractions INTEGER DEFAULT 0,
                    failed_extractions INTEGER DEFAULT 0,
                    average_processing_time REAL DEFAULT 0,
                    total_amount_processed REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            """)
            
            # Validation results table - stores detailed validation information
            conn.execute("""
                CREATE TABLE IF NOT EXISTS validation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    validation_type TEXT NOT NULL,
                    passed BOOLEAN NOT NULL,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better query performance
            # Indexes are like the tabs in a filing cabinet - they help find things faster
            conn.execute("CREATE INDEX IF NOT EXISTS idx_invoices_vendor ON invoices(vendor_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_invoices_amount ON invoices(total_amount)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_invoices_created ON invoices(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_line_items_invoice ON line_items(invoice_id)")
            
            conn.commit()
            logger.info("Database schema initialized successfully")
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections
        
        This ensures that database connections are properly opened and closed,
        even if errors occur. It's like making sure you always close the filing
        cabinet when you're done using it.
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,  # Timeout after 30 seconds
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # This lets us access columns by name
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def save_invoice_result(self, invoice_data: Dict) -> int:
        """
        Save a processed invoice to the database
        
        This method takes the structured data from our AI processing and
        stores it in our database. It handles the complexity of splitting
        the data into appropriate tables while maintaining relationships.
        
        Args:
            invoice_data: Dictionary containing extracted invoice information
            
        Returns:
            The database ID of the saved invoice
        """
        try:
            with self._get_connection() as conn:
                # Prepare main invoice data
                invoice_row = self._prepare_invoice_data(invoice_data)
                
                # Insert main invoice record
                cursor = conn.execute("""
                    INSERT INTO invoices (
                        file_name, invoice_number, vendor_name, vendor_address,
                        invoice_date, due_date, total_amount, subtotal, tax_amount,
                        currency, payment_terms, po_number, confidence, 
                        validation_score, processing_time, ai_model, 
                        processor_version, raw_data, file_size, file_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, invoice_row)
                
                invoice_id = cursor.lastrowid
                
                # Save line items if they exist
                if 'line_items' in invoice_data and invoice_data['line_items']:
                    self._save_line_items(conn, invoice_id, invoice_data['line_items'])
                
                # Save validation results if they exist
                if 'validation_results' in invoice_data:
                    self._save_validation_results(conn, invoice_id, invoice_data['validation_results'])
                
                # Update daily statistics
                self._update_daily_stats(conn, invoice_data)
                
                conn.commit()
                logger.info(f"Saved invoice to database with ID: {invoice_id}")
                return invoice_id
                
        except Exception as e:
            logger.error(f"Failed to save invoice: {str(e)}")
            raise
    
    def _prepare_invoice_data(self, invoice_data: Dict) -> Tuple:
        """
        Convert invoice dictionary to database row format
        
        This method transforms our flexible dictionary format into the specific
        format needed for database insertion. It handles type conversions and
        ensures all fields are properly formatted.
        """
        return (
            invoice_data.get('file_name'),
            invoice_data.get('invoice_number'),
            invoice_data.get('vendor_name'),
            invoice_data.get('vendor_address'),
            self._parse_date_for_db(invoice_data.get('invoice_date')),
            self._parse_date_for_db(invoice_data.get('due_date')),
            self._safe_float(invoice_data.get('total_amount')),
            self._safe_float(invoice_data.get('subtotal')),
            self._safe_float(invoice_data.get('tax_amount')),
            invoice_data.get('currency', 'USD'),
            invoice_data.get('payment_terms'),
            invoice_data.get('po_number'),
            self._safe_float(invoice_data.get('confidence')),
            self._safe_float(invoice_data.get('validation_score')),
            self._safe_float(invoice_data.get('processing_time')),
            invoice_data.get('ai_model'),
            invoice_data.get('processor_version'),
            json.dumps(invoice_data),  # Store complete data as JSON
            invoice_data.get('file_size'),
            invoice_data.get('file_type')
        )
    
    def _save_line_items(self, conn, invoice_id: int, line_items: List[Dict]):
        """
        Save line items for an invoice
        
        Line items are stored in a separate table because invoices can have
        multiple line items. This is called database normalization - it prevents
        data duplication and keeps things organized.
        """
        for item in line_items:
            conn.execute("""
                INSERT INTO line_items (
                    invoice_id, description, quantity, unit_price, total_price
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                invoice_id,
                item.get('description'),
                self._safe_float(item.get('quantity')),
                self._safe_float(item.get('unit_price')),
                self._safe_float(item.get('total_price'))
            ))
    
    def _save_validation_results(self, conn, invoice_id: int, validation_results: Dict):
        """
        Save validation results for an invoice
        
        Validation results help us understand the quality of our extractions
        and identify areas where the AI might need improvement.
        """
        for validation_type, result in validation_results.items():
            if isinstance(result, dict):
                conn.execute("""
                    INSERT INTO validation_results (
                        invoice_id, validation_type, passed, message
                    ) VALUES (?, ?, ?, ?)
                """, (
                    invoice_id,
                    validation_type,
                    result.get('passed', False),
                    result.get('message', '')
                ))
    
    def _update_daily_stats(self, conn, invoice_data: Dict):
        """
        Update daily processing statistics
        
        This keeps track of how our system is performing day by day.
        It's valuable for monitoring system health and usage patterns.
        """
        today = date.today()
        total_amount = self._safe_float(invoice_data.get('total_amount', 0))
        processing_time = self._safe_float(invoice_data.get('processing_time', 0))
        
        # Try to update existing record for today
        cursor = conn.execute("""
            UPDATE processing_stats 
            SET total_processed = total_processed + 1,
                successful_extractions = successful_extractions + 1,
                total_amount_processed = total_amount_processed + ?,
                average_processing_time = (
                    (average_processing_time * (total_processed - 1) + ?) / total_processed
                )
            WHERE date = ?
        """, (total_amount, processing_time, today))
        
        # If no record exists for today, create one
        if cursor.rowcount == 0:
            conn.execute("""
                INSERT INTO processing_stats (
                    date, total_processed, successful_extractions, 
                    total_amount_processed, average_processing_time
                ) VALUES (?, 1, 1, ?, ?)
            """, (today, total_amount, processing_time))
    
    def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict]:
        """
        Retrieve a specific invoice by its database ID
        
        This method demonstrates how we can quickly find specific records
        in our database using the primary key (ID).
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM invoices WHERE id = ?
                """, (invoice_id,))
                
                row = cursor.fetchone()
                if row:
                    invoice = dict(row)
                    
                    # Get line items
                    line_items_cursor = conn.execute("""
                        SELECT * FROM line_items WHERE invoice_id = ?
                    """, (invoice_id,))
                    invoice['line_items'] = [dict(item) for item in line_items_cursor.fetchall()]
                    
                    return invoice
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve invoice {invoice_id}: {str(e)}")
            return None
    
    def get_invoices_by_vendor(self, vendor_name: str, limit: int = 100) -> List[Dict]:
        """
        Find all invoices from a specific vendor
        
        This is useful for vendor analysis - understanding how much business
        you do with specific suppliers over time.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM invoices 
                    WHERE vendor_name LIKE ? 
                    ORDER BY invoice_date DESC 
                    LIMIT ?
                """, (f"%{vendor_name}%", limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to retrieve invoices for vendor {vendor_name}: {str(e)}")
            return []
    
    def get_invoices_by_date_range(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Find invoices within a specific date range
        
        This is essential for financial reporting and analysis - you often
        need to look at invoices for specific time periods.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM invoices 
                    WHERE invoice_date BETWEEN ? AND ?
                    ORDER BY invoice_date DESC
                """, (start_date, end_date))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to retrieve invoices for date range: {str(e)}")
            return []
    
    def get_recent_invoices(self, limit: int = 10) -> List[Dict]:
        """
        Get the most recently processed invoices
        
        This provides a quick overview of recent activity and is useful
        for the dashboard display.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM invoices 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to retrieve recent invoices: {str(e)}")
            return []
    
    def get_total_invoices(self) -> int:
        """
        Get total count of invoices in database
        
        Simple but important metric for understanding system usage.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM invoices")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get total invoice count: {str(e)}")
            return 0
    
    def get_invoices_by_date(self, target_date: date) -> List[Dict]:
        """
        Get all invoices processed on a specific date
        
        Useful for daily reporting and monitoring processing volume.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM invoices 
                    WHERE DATE(created_at) = ?
                    ORDER BY created_at DESC
                """, (target_date,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to retrieve invoices for date {target_date}: {str(e)}")
            return []
    
    def get_vendor_summary(self) -> List[Dict]:
        """
        Get summary statistics by vendor
        
        This provides valuable business intelligence - which vendors you
        work with most, total amounts, etc.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        vendor_name,
                        COUNT(*) as invoice_count,
                        SUM(total_amount) as total_amount,
                        AVG(total_amount) as average_amount,
                        MIN(invoice_date) as first_invoice,
                        MAX(invoice_date) as latest_invoice
                    FROM invoices 
                    WHERE vendor_name IS NOT NULL 
                    GROUP BY vendor_name 
                    ORDER BY total_amount DESC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get vendor summary: {str(e)}")
            return []
    
    def get_monthly_totals(self, year: int = None) -> List[Dict]:
        """
        Get monthly invoice totals for analysis
        
        Essential for understanding business trends and seasonal patterns.
        """
        if year is None:
            year = datetime.now().year
            
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        strftime('%Y-%m', invoice_date) as month,
                        COUNT(*) as invoice_count,
                        SUM(total_amount) as total_amount,
                        AVG(total_amount) as average_amount
                    FROM invoices 
                    WHERE strftime('%Y', invoice_date) = ?
                    AND invoice_date IS NOT NULL
                    GROUP BY strftime('%Y-%m', invoice_date)
                    ORDER BY month
                """, (str(year),))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get monthly totals: {str(e)}")
            return []
    
    def search_invoices(self, search_term: str, limit: int = 50) -> List[Dict]:
        """
        Search invoices by various fields
        
        This provides flexible search capability across multiple fields,
        making it easy to find specific invoices.
        """
        try:
            with self._get_connection() as conn:
                search_pattern = f"%{search_term}%"
                cursor = conn.execute("""
                    SELECT * FROM invoices 
                    WHERE vendor_name LIKE ? 
                       OR invoice_number LIKE ? 
                       OR po_number LIKE ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (search_pattern, search_pattern, search_pattern, limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to search invoices: {str(e)}")
            return []
    
    def get_processing_performance(self, days: int = 30) -> Dict:
        """
        Get processing performance metrics
        
        This helps monitor how well our AI processing is performing over time.
        """
        try:
            with self._get_connection() as conn:
                start_date = date.today() - timedelta(days=days)
                
                cursor = conn.execute("""
                    SELECT 
                        AVG(confidence) as avg_confidence,
                        AVG(validation_score) as avg_validation_score,
                        AVG(processing_time) as avg_processing_time,
                        COUNT(*) as total_invoices,
                        SUM(CASE WHEN confidence > 0.8 THEN 1 ELSE 0 END) as high_confidence_count
                    FROM invoices 
                    WHERE DATE(created_at) >= ?
                """, (start_date,))
                
                result = cursor.fetchone()
                if result:
                    return dict(result)
                else:
                    return {}
                    
        except Exception as e:
            logger.error(f"Failed to get processing performance: {str(e)}")
            return {}
    
    def get_all_invoices(self) -> List[Dict]:
        """
        Get all invoices in the database
        
        Use with caution on large databases - consider pagination for
        production systems with thousands of invoices.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM invoices 
                    ORDER BY created_at DESC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to retrieve all invoices: {str(e)}")
            return []
    
    def delete_invoice(self, invoice_id: int) -> bool:
        """
        Delete an invoice and all related data
        
        This will also delete line items and validation results due to
        foreign key constraints (CASCADE DELETE).
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Deleted invoice with ID: {invoice_id}")
                    return True
                else:
                    logger.warning(f"No invoice found with ID: {invoice_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete invoice {invoice_id}: {str(e)}")
            return False
    
    def clear_all_data(self) -> bool:
        """
        Clear all data from the database
        
        This is a dangerous operation that removes all invoices and related data.
        Use only for testing or when explicitly requested by user.
        """
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM validation_results")
                conn.execute("DELETE FROM line_items")
                conn.execute("DELETE FROM invoices")
                conn.execute("DELETE FROM processing_stats")
                conn.commit()
                
                logger.info("All database data cleared")
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear database: {str(e)}")
            return False
    
    def create_backup(self) -> str:
        """
        Create a backup of the database
        
        Creates a copy of the database file with timestamp.
        Essential for data safety and disaster recovery.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"invoices_backup_{timestamp}.db"
            backup_path = self.config.DATA_DIR / backup_filename
            
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Database backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            raise
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """
        Restore database from backup
        
        Replaces current database with backup. Use with extreme caution.
        """
        try:
            if not Path(backup_path).exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create backup of current database before restoring
            current_backup = self.create_backup()
            logger.info(f"Current database backed up to: {current_backup}")
            
            # Replace current database with backup
            shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {str(e)}")
            return False
    
    def optimize_database(self):
        """
        Optimize database performance
        
        Runs VACUUM and ANALYZE to optimize database file and update statistics.
        Good practice to run periodically on active databases.
        """
        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
                conn.commit()
                
                logger.info("Database optimization completed")
                
        except Exception as e:
            logger.error(f"Database optimization failed: {str(e)}")
    
    # Utility methods for data type handling
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float, returning None if conversion fails"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_date_for_db(self, date_str: str) -> Optional[str]:
        """Parse date string for database storage"""
        if not date_str:
            return None
        
        # If it's already in correct format, return as-is
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        
        # Try to parse and reformat
        try:
            # Try common formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        except:
            pass
        
        return None
    
    def get_database_info(self) -> Dict:
        """
        Get information about the database
        
        Useful for monitoring and debugging database health.
        """
        try:
            with self._get_connection() as conn:
                # Get table counts
                tables_info = {}
                
                for table in ['invoices', 'line_items', 'processing_stats', 'validation_results']:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    tables_info[table] = cursor.fetchone()[0]
                
                # Get database file size
                db_size = self.db_path.stat().st_size / (1024 * 1024)  # MB
                
                return {
                    'database_path': str(self.db_path),
                    'database_size_mb': round(db_size, 2),
                    'table_counts': tables_info,
                    'last_backup': None  # Could implement backup tracking
                }
                
        except Exception as e:
            logger.error(f"Failed to get database info: {str(e)}")
            return {}