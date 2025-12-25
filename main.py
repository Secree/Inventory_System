"""
Main Application - Water Gallon Inventory Management System
GUI interface for managing water gallon inventory with QR codes
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import InventoryDatabase
from qr_generator import QRCodeGenerator
from qr_scanner import QRCodeScanner
from text_logger import TextFileLogger
import os
from datetime import datetime


class InventoryApp:
    def __init__(self, root):
        """Initialize the main application"""
        self.root = root
        self.root.title("Water Gallon Inventory Management System")
        self.root.geometry("1200x700")
        
        # Initialize components
        self.db = InventoryDatabase()
        self.qr_gen = QRCodeGenerator()
        self.qr_scanner = QRCodeScanner()
        self.logger = TextFileLogger()
        
        # Setup UI
        self.setup_ui()
        self.refresh_inventory_list()
        self.update_statistics()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Title
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🚰 Water Gallon Inventory Management System",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=15)
        
        # Main container
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls
        left_panel = tk.Frame(main_container, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        
        # Statistics Panel
        self.setup_statistics_panel(left_panel)
        
        # Add Gallon Panel
        self.setup_add_gallon_panel(left_panel)
        
        # Quick Actions Panel
        self.setup_quick_actions_panel(left_panel)
        
        # Right panel - Inventory List
        right_panel = tk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.setup_inventory_list(right_panel)
    
    def setup_statistics_panel(self, parent):
        """Setup statistics display panel"""
        stats_frame = tk.LabelFrame(parent, text="📊 Statistics", font=("Arial", 12, "bold"), padx=10, pady=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_labels = {}
        stats_info = [
            ("total", "Total Gallons:", "#3498db"),
            ("active", "Active:", "#27ae60"),
            ("defective", "Defective:", "#e74c3c"),
            ("refills", "Total Refills:", "#f39c12"),
            ("defects", "Total Defects:", "#95a5a6")
        ]
        
        for key, label, color in stats_info:
            frame = tk.Frame(stats_frame, bg=color, padx=10, pady=5)
            frame.pack(fill=tk.X, pady=2)
            
            tk.Label(frame, text=label, font=("Arial", 10), bg=color, fg="white").pack(side=tk.LEFT)
            self.stats_labels[key] = tk.Label(frame, text="0", font=("Arial", 10, "bold"), bg=color, fg="white")
            self.stats_labels[key].pack(side=tk.RIGHT)
    
    def setup_add_gallon_panel(self, parent):
        """Setup add gallon panel"""
        add_frame = tk.LabelFrame(parent, text="➕ Add New Gallon", font=("Arial", 12, "bold"), padx=10, pady=10)
        add_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Inventory ID
        tk.Label(add_frame, text="Inventory ID:", font=("Arial", 10)).pack(anchor=tk.W, pady=(5, 0))
        self.id_entry = tk.Entry(add_frame, font=("Arial", 10))
        self.id_entry.pack(fill=tk.X, pady=(0, 5))
        
        # Gallon Name
        tk.Label(add_frame, text="Gallon Name:", font=("Arial", 10)).pack(anchor=tk.W, pady=(5, 0))
        self.name_entry = tk.Entry(add_frame, font=("Arial", 10))
        self.name_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Buttons
        btn_frame = tk.Frame(add_frame)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(
            btn_frame,
            text="Add & Generate QR",
            command=self.add_gallon,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2"
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        tk.Button(
            btn_frame,
            text="Clear",
            command=self.clear_form,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 10),
            cursor="hand2"
        ).pack(side=tk.RIGHT, expand=True, fill=tk.X)
    
    def setup_quick_actions_panel(self, parent):
        """Setup quick actions panel"""
        actions_frame = tk.LabelFrame(parent, text="⚡ Quick Actions", font=("Arial", 12, "bold"), padx=10, pady=10)
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        buttons = [
            ("📷 Scan QR from Camera", self.scan_from_camera, "#3498db"),
            ("🖼️ Scan QR from Image", self.scan_from_image, "#9b59b6"),
            ("💾 Backup to Text File", self.backup_to_text, "#16a085"),
            ("📋 Generate Report", self.generate_report, "#f39c12")
        ]
        
        for text, command, color in buttons:
            tk.Button(
                actions_frame,
                text=text,
                command=command,
                bg=color,
                fg="white",
                font=("Arial", 10),
                cursor="hand2"
            ).pack(fill=tk.X, pady=2)
    
    def setup_inventory_list(self, parent):
        """Setup inventory list with treeview"""
        list_frame = tk.LabelFrame(parent, text="📦 Inventory List", font=("Arial", 12, "bold"), padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search bar
        search_frame = tk.Frame(list_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame, text="Search:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = tk.Entry(search_frame, font=("Arial", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.search_entry.bind('<KeyRelease>', lambda e: self.refresh_inventory_list())
        
        tk.Button(
            search_frame,
            text="Refresh",
            command=self.refresh_inventory_list,
            font=("Arial", 9),
            cursor="hand2"
        ).pack(side=tk.RIGHT)
        
        # Treeview
        tree_frame = tk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Create treeview
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Name", "Refills", "Defects", "Status", "Modified"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Define columns
        self.tree.heading("ID", text="Inventory ID")
        self.tree.heading("Name", text="Gallon Name")
        self.tree.heading("Refills", text="Refills")
        self.tree.heading("Defects", text="Defects")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Modified", text="Last Modified")
        
        self.tree.column("ID", width=100)
        self.tree.column("Name", width=200)
        self.tree.column("Refills", width=80)
        self.tree.column("Defects", width=80)
        self.tree.column("Status", width=100)
        self.tree.column("Modified", width=150)
        
        # Pack
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Context menu
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", lambda e: self.view_details())
    
    def add_gallon(self):
        """Add a new gallon and generate QR code"""
        inventory_id = self.id_entry.get().strip()
        name = self.name_entry.get().strip()
        
        if not inventory_id or not name:
            messagebox.showwarning("Input Error", "Please enter both Inventory ID and Name")
            return
        
        # Add to database
        success, message = self.db.add_gallon(inventory_id, name)
        
        if success:
            # Generate QR code
            qr_success, qr_message, qr_path = self.qr_gen.generate_qr_with_label(inventory_id, name)
            
            if qr_success:
                # Log to text file
                self.logger.log_activity(inventory_id, 'ADDED', f'New gallon "{name}" added')
                
                messagebox.showinfo(
                    "Success",
                    f"Gallon added successfully!\n\nQR Code saved to:\n{qr_path}"
                )
                
                self.clear_form()
                self.refresh_inventory_list()
                self.update_statistics()
                
                # Ask if user wants to open QR code
                if messagebox.askyesno("Open QR Code", "Do you want to view the QR code?"):
                    os.startfile(qr_path)
            else:
                messagebox.showerror("QR Error", qr_message)
        else:
            messagebox.showerror("Error", message)
    
    def scan_from_camera(self):
        """Scan QR code from camera"""
        messagebox.showinfo("Camera Scan", "Camera will open. Point at QR code.\nPress 'Q' to cancel.")
        
        success, data, message = self.qr_scanner.scan_from_camera()
        
        if success:
            self.process_scanned_qr(data)
        else:
            messagebox.showwarning("Scan Failed", message)
    
    def scan_from_image(self):
        """Scan QR code from image file"""
        file_path = filedialog.askopenfilename(
            title="Select QR Code Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
        )
        
        if file_path:
            success, data, message = self.qr_scanner.scan_from_image(file_path)
            
            if success:
                self.process_scanned_qr(data)
            else:
                messagebox.showerror("Scan Failed", message)
    
    def process_scanned_qr(self, data):
        """Process scanned QR code data"""
        inventory_id = data['inventory_id']
        gallon = self.db.get_gallon(inventory_id)
        
        if not gallon:
            messagebox.showerror("Not Found", f"Gallon {inventory_id} not found in database")
            return
        
        # Show action dialog
        action_window = tk.Toplevel(self.root)
        action_window.title(f"Gallon {inventory_id}")
        action_window.geometry("400x350")
        action_window.transient(self.root)
        action_window.grab_set()
        
        # Display info
        info_frame = tk.LabelFrame(action_window, text="Gallon Information", padx=20, pady=10)
        info_frame.pack(fill=tk.BOTH, padx=20, pady=10)
        
        tk.Label(info_frame, text=f"ID: {gallon['inventory_id']}", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=2)
        tk.Label(info_frame, text=f"Name: {gallon['name']}", font=("Arial", 10)).pack(anchor=tk.W, pady=2)
        tk.Label(info_frame, text=f"Refills: {gallon['refills']}", font=("Arial", 10)).pack(anchor=tk.W, pady=2)
        tk.Label(info_frame, text=f"Defects: {gallon['defects']}", font=("Arial", 10)).pack(anchor=tk.W, pady=2)
        tk.Label(info_frame, text=f"Status: {gallon['status']}", font=("Arial", 10)).pack(anchor=tk.W, pady=2)
        
        # Actions
        action_frame = tk.Frame(action_window)
        action_frame.pack(fill=tk.BOTH, padx=20, pady=10)
        
        tk.Button(
            action_frame,
            text="➕ Record Refill",
            command=lambda: self.record_refill(inventory_id, action_window),
            bg="#27ae60",
            fg="white",
            font=("Arial", 10),
            cursor="hand2"
        ).pack(fill=tk.X, pady=5)
        
        if gallon['status'] == 'active':
            tk.Button(
                action_frame,
                text="⚠️ Report Defect",
                command=lambda: self.report_defect(inventory_id, action_window),
                bg="#e74c3c",
                fg="white",
                font=("Arial", 10),
                cursor="hand2"
            ).pack(fill=tk.X, pady=5)
        else:
            tk.Button(
                action_frame,
                text="✅ Fix Defect",
                command=lambda: self.fix_defect(inventory_id, action_window),
                bg="#3498db",
                fg="white",
                font=("Arial", 10),
                cursor="hand2"
            ).pack(fill=tk.X, pady=5)
        
        tk.Button(
            action_frame,
            text="Close",
            command=action_window.destroy,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 10),
            cursor="hand2"
        ).pack(fill=tk.X, pady=5)
    
    def record_refill(self, inventory_id, window=None):
        """Record a refill for a gallon"""
        success, message = self.db.increment_refills(inventory_id)
        
        if success:
            self.logger.log_activity(inventory_id, 'REFILL', 'Gallon refilled')
            messagebox.showinfo("Success", "Refill recorded successfully!")
            self.refresh_inventory_list()
            self.update_statistics()
            if window:
                window.destroy()
        else:
            messagebox.showerror("Error", message)
    
    def report_defect(self, inventory_id, window=None):
        """Report a defect for a gallon"""
        if messagebox.askyesno("Confirm", "Mark this gallon as defective?"):
            success, message = self.db.add_defect(inventory_id)
            
            if success:
                self.logger.log_activity(inventory_id, 'DEFECT', 'Defect detected')
                messagebox.showinfo("Success", "Defect recorded. Gallon marked as defective.")
                self.refresh_inventory_list()
                self.update_statistics()
                if window:
                    window.destroy()
            else:
                messagebox.showerror("Error", message)
    
    def fix_defect(self, inventory_id, window=None):
        """Fix a defect and return gallon to active"""
        if messagebox.askyesno("Confirm", "Mark defect as fixed and return to active?"):
            success, message = self.db.fix_defect(inventory_id)
            
            if success:
                self.logger.log_activity(inventory_id, 'FIXED', 'Defect fixed')
                messagebox.showinfo("Success", "Defect fixed! Gallon returned to active inventory.")
                self.refresh_inventory_list()
                self.update_statistics()
                if window:
                    window.destroy()
            else:
                messagebox.showerror("Error", message)
    
    def backup_to_text(self):
        """Backup inventory to text file"""
        gallons = self.db.get_all_gallons()
        success, message = self.logger.save_inventory_snapshot(gallons)
        
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
    
    def generate_report(self):
        """Generate daily report"""
        stats = self.db.get_statistics()
        gallons = self.db.get_all_gallons()
        
        success, message, file_path = self.logger.create_daily_report(stats, gallons)
        
        if success:
            if messagebox.askyesno("Success", f"{message}\n\nDo you want to open the report?"):
                os.startfile(file_path)
        else:
            messagebox.showerror("Error", message)
    
    def refresh_inventory_list(self):
        """Refresh the inventory list"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get search term
        search_term = self.search_entry.get().lower()
        
        # Get all gallons
        gallons = self.db.get_all_gallons()
        
        # Filter and display
        for gallon in gallons:
            if search_term:
                if search_term not in gallon['inventory_id'].lower() and \
                   search_term not in gallon['name'].lower():
                    continue
            
            # Color coding based on status
            tag = 'active' if gallon['status'] == 'active' else 'defective'
            
            self.tree.insert("", tk.END, values=(
                gallon['inventory_id'],
                gallon['name'],
                gallon['refills'],
                gallon['defects'],
                gallon['status'].upper(),
                gallon['last_modified']
            ), tags=(tag,))
        
        # Configure tags
        self.tree.tag_configure('active', background='#d5f4e6')
        self.tree.tag_configure('defective', background='#fadbd8')
    
    def update_statistics(self):
        """Update statistics display"""
        stats = self.db.get_statistics()
        
        self.stats_labels['total'].config(text=str(stats['total_gallons']))
        self.stats_labels['active'].config(text=str(stats['active_gallons']))
        self.stats_labels['defective'].config(text=str(stats['defective_gallons']))
        self.stats_labels['refills'].config(text=str(stats['total_refills']))
        self.stats_labels['defects'].config(text=str(stats['total_defects']))
    
    def show_context_menu(self, event):
        """Show context menu on right-click"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="View Details", command=self.view_details)
            menu.add_command(label="Record Refill", command=self.refill_selected)
            menu.add_command(label="Report Defect", command=self.defect_selected)
            menu.add_separator()
            menu.add_command(label="Delete Gallon", command=self.delete_selected)
            
            menu.post(event.x_root, event.y_root)
    
    def view_details(self):
        """View details of selected gallon"""
        selection = self.tree.selection()
        if not selection:
            return
        
        values = self.tree.item(selection[0])['values']
        inventory_id = values[0]
        
        gallon = self.db.get_gallon(inventory_id)
        activity_log = self.db.get_activity_log(inventory_id)
        
        # Create details window
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Details - {inventory_id}")
        details_window.geometry("500x400")
        
        # Info section
        info_frame = tk.LabelFrame(details_window, text="Gallon Information", padx=20, pady=10)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        for key, value in gallon.items():
            tk.Label(info_frame, text=f"{key.replace('_', ' ').title()}: {value}", 
                    font=("Arial", 10), anchor=tk.W).pack(fill=tk.X, pady=2)
        
        # Activity log section
        log_frame = tk.LabelFrame(details_window, text="Recent Activity", padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        log_text = tk.Text(log_frame, height=10, font=("Courier", 9))
        log_text.pack(fill=tk.BOTH, expand=True)
        
        for activity in activity_log[:10]:  # Show last 10 activities
            log_text.insert(tk.END, f"[{activity['timestamp']}] {activity['activity_type']}\n")
            log_text.insert(tk.END, f"  {activity['description']}\n\n")
        
        log_text.config(state=tk.DISABLED)
    
    def refill_selected(self):
        """Record refill for selected gallon"""
        selection = self.tree.selection()
        if selection:
            inventory_id = self.tree.item(selection[0])['values'][0]
            self.record_refill(inventory_id)
    
    def defect_selected(self):
        """Report defect for selected gallon"""
        selection = self.tree.selection()
        if selection:
            inventory_id = self.tree.item(selection[0])['values'][0]
            self.report_defect(inventory_id)
    
    def delete_selected(self):
        """Delete selected gallon"""
        selection = self.tree.selection()
        if not selection:
            return
        
        inventory_id = self.tree.item(selection[0])['values'][0]
        
        if messagebox.askyesno("Confirm Delete", f"Delete gallon {inventory_id}?\nThis cannot be undone."):
            success, message = self.db.delete_gallon(inventory_id)
            
            if success:
                messagebox.showinfo("Success", "Gallon deleted")
                self.refresh_inventory_list()
                self.update_statistics()
            else:
                messagebox.showerror("Error", message)
    
    def clear_form(self):
        """Clear input form"""
        self.id_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
    
    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.db.close()
            self.root.destroy()


def main():
    """Main application entry point"""
    root = tk.Tk()
    app = InventoryApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
