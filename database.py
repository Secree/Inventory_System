"""
Database handler for Water Gallon Inventory Management System
Manages SQLite database operations for gallon inventory
"""

import sqlite3
from datetime import datetime
import os


class InventoryDatabase:
    def __init__(self, db_name='inventory.db'):
        """Initialize database connection"""
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Create database connection"""
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        # Main gallon inventory table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS gallons (
                inventory_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                refills INTEGER DEFAULT 0,
                defects INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_date TEXT,
                last_modified TEXT
            )
        ''')
        
        # History table for tracking all activities
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id TEXT,
                activity_type TEXT,
                description TEXT,
                timestamp TEXT,
                FOREIGN KEY (inventory_id) REFERENCES gallons (inventory_id)
            )
        ''')
        
        self.conn.commit()
    
    def add_gallon(self, inventory_id, name):
        """Add a new gallon to inventory"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute('''
                INSERT INTO gallons (inventory_id, name, refills, defects, status, created_date, last_modified)
                VALUES (?, ?, 0, 0, 'active', ?, ?)
            ''', (inventory_id, name, timestamp, timestamp))
            
            # Log activity
            self.log_activity(inventory_id, 'ADDED', f'New gallon "{name}" added to inventory')
            
            self.conn.commit()
            return True, "Gallon added successfully"
        except sqlite3.IntegrityError:
            return False, "Inventory ID already exists"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def get_gallon(self, inventory_id):
        """Get gallon information by inventory ID"""
        self.cursor.execute('SELECT * FROM gallons WHERE inventory_id = ?', (inventory_id,))
        result = self.cursor.fetchone()
        if result:
            return {
                'inventory_id': result[0],
                'name': result[1],
                'refills': result[2],
                'defects': result[3],
                'status': result[4],
                'created_date': result[5],
                'last_modified': result[6]
            }
        return None
    
    def get_all_gallons(self):
        """Get all gallons from inventory"""
        self.cursor.execute('SELECT * FROM gallons ORDER BY inventory_id')
        results = self.cursor.fetchall()
        gallons = []
        for result in results:
            gallons.append({
                'inventory_id': result[0],
                'name': result[1],
                'refills': result[2],
                'defects': result[3],
                'status': result[4],
                'created_date': result[5],
                'last_modified': result[6]
            })
        return gallons
    
    def increment_refills(self, inventory_id):
        """Increment refill count for a gallon"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute('''
                UPDATE gallons 
                SET refills = refills + 1, last_modified = ?
                WHERE inventory_id = ?
            ''', (timestamp, inventory_id))
            
            # Log activity
            self.log_activity(inventory_id, 'REFILL', 'Gallon refilled')
            
            self.conn.commit()
            return True, "Refill count updated"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def add_defect(self, inventory_id):
        """Add defect to a gallon and mark as defective"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute('''
                UPDATE gallons 
                SET defects = defects + 1, status = 'defective', last_modified = ?
                WHERE inventory_id = ?
            ''', (timestamp, inventory_id))
            
            # Log activity
            self.log_activity(inventory_id, 'DEFECT', 'Defect detected and reported')
            
            self.conn.commit()
            return True, "Defect recorded"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def fix_defect(self, inventory_id):
        """Fix defect and return gallon to active status"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute('''
                UPDATE gallons 
                SET status = 'active', last_modified = ?
                WHERE inventory_id = ?
            ''', (timestamp, inventory_id))
            
            # Log activity
            self.log_activity(inventory_id, 'FIXED', 'Defect fixed, returned to active inventory')
            
            self.conn.commit()
            return True, "Defect fixed, gallon back to active"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def delete_gallon(self, inventory_id):
        """Delete a gallon from inventory"""
        try:
            self.cursor.execute('DELETE FROM gallons WHERE inventory_id = ?', (inventory_id,))
            self.log_activity(inventory_id, 'DELETED', 'Gallon removed from inventory')
            self.conn.commit()
            return True, "Gallon deleted"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def log_activity(self, inventory_id, activity_type, description):
        """Log activity to history"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('''
            INSERT INTO activity_log (inventory_id, activity_type, description, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (inventory_id, activity_type, description, timestamp))
    
    def get_activity_log(self, inventory_id=None):
        """Get activity log for a specific gallon or all activities"""
        if inventory_id:
            self.cursor.execute('''
                SELECT * FROM activity_log 
                WHERE inventory_id = ?
                ORDER BY timestamp DESC
            ''', (inventory_id,))
        else:
            self.cursor.execute('SELECT * FROM activity_log ORDER BY timestamp DESC')
        
        results = self.cursor.fetchall()
        logs = []
        for result in results:
            logs.append({
                'id': result[0],
                'inventory_id': result[1],
                'activity_type': result[2],
                'description': result[3],
                'timestamp': result[4]
            })
        return logs
    
    def get_statistics(self):
        """Get inventory statistics"""
        stats = {}
        
        # Total gallons
        self.cursor.execute('SELECT COUNT(*) FROM gallons')
        stats['total_gallons'] = self.cursor.fetchone()[0]
        
        # Active gallons
        self.cursor.execute("SELECT COUNT(*) FROM gallons WHERE status = 'active'")
        stats['active_gallons'] = self.cursor.fetchone()[0]
        
        # Defective gallons
        self.cursor.execute("SELECT COUNT(*) FROM gallons WHERE status = 'defective'")
        stats['defective_gallons'] = self.cursor.fetchone()[0]
        
        # Total refills
        self.cursor.execute('SELECT SUM(refills) FROM gallons')
        result = self.cursor.fetchone()[0]
        stats['total_refills'] = result if result else 0
        
        # Total defects
        self.cursor.execute('SELECT SUM(defects) FROM gallons')
        result = self.cursor.fetchone()[0]
        stats['total_defects'] = result if result else 0
        
        return stats
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


if __name__ == '__main__':
    # Test the database
    db = InventoryDatabase()
    print("Database initialized successfully!")
    
    # Test adding a gallon
    success, msg = db.add_gallon('GAL001', 'Blue 5-Gallon Container')
    print(f"Add gallon: {msg}")
    
    # Get statistics
    stats = db.get_statistics()
    print(f"Statistics: {stats}")
    
    db.close()
