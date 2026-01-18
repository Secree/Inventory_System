"""
Text File Logger for Water Gallon Inventory System
Stores inventory data in text files as backup
"""

import os
from datetime import datetime


class TextFileLogger:
    def __init__(self, log_dir='logs'):
        """Initialize text file logger"""
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self.inventory_file = os.path.join(log_dir, 'inventory_backup.txt')
        self.activity_file = os.path.join(log_dir, 'activity_log.txt')
    
    def save_inventory_snapshot(self, gallons_list):
        """
        Save current inventory snapshot to text file
        
        Args:
            gallons_list: List of gallon dictionaries from database
        
        Returns:
            tuple: (success, message)
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.inventory_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("WATER GALLON INVENTORY SYSTEM - BACKUP\n")
                f.write(f"Generated: {timestamp}\n")
                f.write("="*80 + "\n\n")
                
                if not gallons_list:
                    f.write("No gallons in inventory.\n")
                else:
                    f.write(f"Total Gallons: {len(gallons_list)}\n\n")
                    f.write("-"*80 + "\n")
                    
                    for gallon in gallons_list:
                        f.write(f"\nInventory ID: {gallon['inventory_id']}\n")
                        f.write(f"Name: {gallon['name']}\n")
                        f.write(f"Refills: {gallon['refills']}\n")
                        f.write(f"Defects: {gallon['defects']}\n")
                        f.write(f"Status: {gallon['status']}\n")
                        f.write(f"Created: {gallon['created_date']}\n")
                        f.write(f"Last Modified: {gallon['last_modified']}\n")
                        f.write("-"*80 + "\n")
            
            return True, f"Inventory backup saved to {self.inventory_file}"
            
        except Exception as e:
            return False, f"Error saving inventory backup: {str(e)}"
    
    def log_activity(self, inventory_id, activity_type, description):
        """
        Log an activity to text file
        
        Args:
            inventory_id: Inventory ID of the gallon
            activity_type: Type of activity (ADDED, REFILL, DEFECT, etc.)
            description: Description of the activity
        
        Returns:
            tuple: (success, message)
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.activity_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] [{activity_type}] ID:{inventory_id} - {description}\n")
            
            return True, "Activity logged"
            
        except Exception as e:
            return False, f"Error logging activity: {str(e)}"
    
    def export_gallon_details(self, gallon_data, activity_log=None):
        """
        Export detailed information for a specific gallon
        
        Args:
            gallon_data: Dictionary containing gallon information
            activity_log: Optional list of activity logs for this gallon
        
        Returns:
            tuple: (success, message, file_path)
        """
        try:
            inventory_id = gallon_data['inventory_id']
            filename = f"gallon_{inventory_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            file_path = os.path.join(self.log_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("GALLON DETAILED REPORT\n")
                f.write("="*80 + "\n\n")
                
                f.write(f"Inventory ID: {gallon_data['inventory_id']}\n")
                f.write(f"Name: {gallon_data['name']}\n")
                f.write(f"Refills: {gallon_data['refills']}\n")
                f.write(f"Defects: {gallon_data['defects']}\n")
                f.write(f"Status: {gallon_data['status']}\n")
                f.write(f"Created: {gallon_data['created_date']}\n")
                f.write(f"Last Modified: {gallon_data['last_modified']}\n")
                
                if activity_log:
                    f.write("\n" + "="*80 + "\n")
                    f.write("ACTIVITY HISTORY\n")
                    f.write("="*80 + "\n\n")
                    
                    for activity in activity_log:
                        f.write(f"[{activity['timestamp']}] {activity['activity_type']}\n")
                        f.write(f"  {activity['description']}\n\n")
            
            return True, "Gallon details exported", file_path
            
        except Exception as e:
            return False, f"Error exporting gallon details: {str(e)}", None
    
    def create_daily_report(self, statistics, gallons_list):
        """
        Create a daily report with statistics
        
        Args:
            statistics: Dictionary containing inventory statistics
            gallons_list: List of all gallons
        
        Returns:
            tuple: (success, message, file_path)
        """
        try:
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = f"daily_report_{date_str}.txt"
            file_path = os.path.join(self.log_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"DAILY INVENTORY REPORT - {date_str}\n")
                f.write("="*80 + "\n\n")
                
                f.write("SUMMARY STATISTICS\n")
                f.write("-"*80 + "\n")
                f.write(f"Total Gallons: {statistics['total_gallons']}\n")
                f.write(f"Active Gallons: {statistics['active_gallons']}\n")
                f.write(f"Defective Gallons: {statistics['defective_gallons']}\n")
                f.write(f"Total Refills: {statistics['total_refills']}\n")
                f.write(f"Total Defects: {statistics['total_defects']}\n\n")
                
                # Active gallons
                f.write("="*80 + "\n")
                f.write("ACTIVE GALLONS\n")
                f.write("="*80 + "\n")
                active_gallons = [g for g in gallons_list if g['status'] == 'active']
                
                if active_gallons:
                    f.write(f"{'ID':<15} {'Name':<30} {'Refills':<10} {'Defects':<10}\n")
                    f.write("-"*80 + "\n")
                    for gallon in active_gallons:
                        f.write(f"{gallon['inventory_id']:<15} {gallon['name']:<30} "
                               f"{gallon['refills']:<10} {gallon['defects']:<10}\n")
                else:
                    f.write("No active gallons.\n")
                
                # Defective gallons
                f.write("\n" + "="*80 + "\n")
                f.write("DEFECTIVE GALLONS\n")
                f.write("="*80 + "\n")
                defective_gallons = [g for g in gallons_list if g['status'] == 'defective']
                
                if defective_gallons:
                    f.write(f"{'ID':<15} {'Name':<30} {'Refills':<10} {'Defects':<10}\n")
                    f.write("-"*80 + "\n")
                    for gallon in defective_gallons:
                        f.write(f"{gallon['inventory_id']:<15} {gallon['name']:<30} "
                               f"{gallon['refills']:<10} {gallon['defects']:<10}\n")
                else:
                    f.write("No defective gallons.\n")
                
                f.write("\n" + "="*80 + "\n")
                f.write(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*80 + "\n")
            
            return True, "Daily report created", file_path
            
        except Exception as e:
            return False, f"Error creating daily report: {str(e)}", None
    
    def read_activity_log(self, lines=50):
        """
        Read recent activity log entries
        
        Args:
            lines: Number of recent lines to read
        
        Returns:
            list: List of log entries
        """
        try:
            if not os.path.exists(self.activity_file):
                return []
            
            with open(self.activity_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # Return last N lines
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
            
        except Exception as e:
            print(f"Error reading activity log: {e}")
            return []


if __name__ == '__main__':
    # Test text file logger
    logger = TextFileLogger()
    
    # Test activity logging
    success, msg = logger.log_activity('GAL001', 'TEST', 'Testing text logger')
    print(msg)
    
    # Test inventory snapshot
    test_gallons = [
        {
            'inventory_id': 'GAL001',
            'name': 'Blue Container',
            'refills': 5,
            'defects': 0,
            'status': 'active',
            'created_date': '2025-12-21 10:00:00',
            'last_modified': '2025-12-21 10:30:00'
        }
    ]
    
    success, msg = logger.save_inventory_snapshot(test_gallons)
    print(msg)
