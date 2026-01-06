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
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class InventoryApp:
    def __init__(self, root):
        """Initialize the main application"""
        self.root = root
        self.root.title("Water Gallon Inventory Management System Prototype")
        
        # Create necessary directories if they don't exist
        os.makedirs('logs', exist_ok=True)
        os.makedirs('qr_codes', exist_ok=True)
        
        # Responsive design for small screens
        self.is_fullscreen = False
        
        # Set smaller default size for small screens
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Use 90% of screen size or max 1200x700
        window_width = min(int(screen_width * 0.9), 1200)
        window_height = min(int(screen_height * 0.85), 700)
        
        # Center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(800, 500)
        
        # Initialize components
        self.db = InventoryDatabase()
        self.qr_gen = QRCodeGenerator()
        self.qr_scanner = QRCodeScanner()
        self.logger = TextFileLogger()
        
        # Track canvas widgets for scrolling
        self.canvas_widgets = {}
        
        # Bind F11 for fullscreen toggle
        self.root.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.root.bind('<Escape>', lambda e: self.exit_fullscreen())
        
        # Setup UI
        self.setup_ui()
        self.refresh_inventory_list()
        self.update_statistics()
        self.update_id_preview()
        
        # Bind global mouse wheel scrolling
        self.root.bind_all("<MouseWheel>", self.on_mousewheel_global)
    
    def setup_ui(self):
        """Setup the user interface"""
        # Compact Title for small screens
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=45)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🚰 Water Gallon Inventory",
            font=("Arial", 14, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=10)
        
        # Fullscreen toggle button
        fullscreen_btn = tk.Button(
            title_frame,
            text="⛶",
            command=self.toggle_fullscreen,
            bg="#34495e",
            fg="white",
            font=("Arial", 16, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        fullscreen_btn.place(relx=0.98, rely=0.5, anchor=tk.E)
        
        # Main container with notebook (tabs) for small screens
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Enable tab reordering/dragging
        self.notebook.enable_traversal()
        
        # Tab 1: Inventory List
        inventory_tab = tk.Frame(self.notebook)
        self.notebook.add(inventory_tab, text="📦 Inventory")
        self.setup_inventory_list(inventory_tab)
        
        # Tab 2: Controls (Add & Scan)
        controls_tab = tk.Frame(self.notebook)
        self.notebook.add(controls_tab, text="➕ Add/Scan")
        
        # Create scrollable frame for controls
        canvas = tk.Canvas(controls_tab)
        scrollbar = ttk.Scrollbar(controls_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Store canvas for global scrolling
        self.canvas_widgets['controls'] = canvas
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add panels to scrollable frame
        self.setup_add_gallon_panel(scrollable_frame)
        self.setup_qr_scanner_panel(scrollable_frame)
        
        # Tab 3: Statistics
        stats_tab = tk.Frame(self.notebook)
        self.notebook.add(stats_tab, text="📊 Stats")
        self.setup_statistics_panel(stats_tab)
    
    def setup_statistics_panel(self, parent):
        """Setup statistics display panel with graphs"""
        # Create scrollable frame for stats
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        stats_container = tk.Frame(canvas)
        
        stats_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=stats_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Store canvas for global scrolling
        self.canvas_widgets['stats'] = canvas
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Stats cards at top
        stats_frame = tk.LabelFrame(stats_container, text="📊 Statistics", font=("Arial", 12, "bold"), padx=10, pady=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.stats_labels = {}
        stats_info = [
            ("total", "Total Gallons:", "#3498db"),
            ("active", "Active:", "#27ae60"),
            ("defective", "Defective:", "#e74c3c"),
            ("refills", "Total Refills:", "#f39c12"),
            ("defects", "Total Defects:", "#95a5a6")
        ]
        
        for key, label, color in stats_info:
            frame = tk.Frame(stats_frame, bg=color, padx=10, pady=8)
            frame.pack(fill=tk.X, pady=2)
            
            tk.Label(frame, text=label, font=("Arial", 11), bg=color, fg="white").pack(side=tk.LEFT)
            self.stats_labels[key] = tk.Label(frame, text="0", font=("Arial", 11, "bold"), bg=color, fg="white")
            self.stats_labels[key].pack(side=tk.RIGHT)
        
        # Graphs section
        graph_frame = tk.LabelFrame(stats_container, text="📈 Visual Analytics", font=("Arial", 12, "bold"), padx=10, pady=10)
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create frame to hold graphs
        self.graph_canvas_frame = tk.Frame(graph_frame)
        self.graph_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Refresh button for graphs
        tk.Button(
            stats_frame,
            text="🔄 Refresh Graphs",
            command=self.update_graphs,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            pady=5
        ).pack(fill=tk.X, pady=(10, 0))
    
    def setup_add_gallon_panel(self, parent):
        """Setup add gallon panel"""
        add_frame = tk.LabelFrame(parent, text="➕ Add New Gallon", font=("Arial", 11, "bold"), padx=10, pady=10)
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Auto-generated ID display (read-only)
        tk.Label(add_frame, text="Inventory ID (Auto-generated):", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(3, 0))
        self.id_display = tk.Label(add_frame, text="Will be generated automatically", font=("Arial", 11), bg="#ecf0f1", anchor=tk.W, padx=10, pady=8)
        self.id_display.pack(fill=tk.X, pady=(0, 8))
        
        # Gallon Name
        tk.Label(add_frame, text="Gallon Name:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(3, 0))
        self.name_entry = tk.Entry(add_frame, font=("Arial", 11))
        self.name_entry.pack(fill=tk.X, pady=(0, 10), ipady=5)
        self.name_entry.bind('<KeyRelease>', lambda e: self.update_id_preview())
        
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
            cursor="hand2",
            pady=8
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        tk.Button(
            btn_frame,
            text="Clear",
            command=self.clear_form,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 10),
            cursor="hand2",
            pady=8
        ).pack(side=tk.RIGHT, expand=True, fill=tk.X)
    
    def setup_qr_scanner_panel(self, parent):
        """Setup QR scanner panel"""
        scanner_frame = tk.LabelFrame(parent, text="📷 QR Code Scanner", font=("Arial", 11, "bold"), padx=10, pady=10)
        scanner_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            scanner_frame,
            text="Scan QR codes for actions:",
            font=("Arial", 9),
            fg="gray"
        ).pack(pady=(0, 8))
        
        tk.Button(
            scanner_frame,
            text="📷 Scan from Camera",
            command=self.scan_from_camera,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            pady=8
        ).pack(fill=tk.X, pady=3)
        
        tk.Button(
            scanner_frame,
            text="🖼️ Scan from Image",
            command=self.scan_from_image,
            bg="#9b59b6",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            pady=8
        ).pack(fill=tk.X, pady=3)
    
    def setup_quick_actions_panel(self, parent):
        """Setup quick actions panel"""
        actions_frame = tk.LabelFrame(parent, text="⚡ Quick Actions", font=("Arial", 14, "bold"), padx=15, pady=15)
        actions_frame.pack(fill=tk.X, pady=(0, 15))
        
        buttons = [
            (" Backup", self.backup_to_text, "#16a085"),
            ("📋 Report", self.generate_report, "#f39c12")
        ]
        
        for text, command, color in buttons:
            tk.Button(
                actions_frame,
                text=text,
                command=command,
                bg=color,
                fg="white",
                font=("Arial", 12, "bold"),
                cursor="hand2",
                pady=15
            ).pack(fill=tk.X, pady=6)
    
    def setup_inventory_list(self, parent):
        """Setup inventory list with treeview"""
        list_frame = tk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure grid for list_frame
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Search bar
        search_frame = tk.Frame(list_frame)
        search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        tk.Label(search_frame, text="Search:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = tk.Entry(search_frame, font=("Arial", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), ipady=3)
        self.search_entry.bind('<KeyRelease>', lambda e: self.refresh_inventory_list())
        
        tk.Button(
            search_frame,
            text="↻",
            command=self.refresh_inventory_list,
            font=("Arial", 14, "bold"),
            cursor="hand2",
            bg="#3498db",
            fg="white",
            padx=8,
            pady=2
        ).pack(side=tk.RIGHT)
        
        # Treeview - Scrollbars
        vsb = ttk.Scrollbar(list_frame, orient="vertical")
        hsb = ttk.Scrollbar(list_frame, orient="horizontal")
        
        # Create treeview
        self.tree = ttk.Treeview(
            list_frame,
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
        
        # Make columns fill the space and stretch
        self.tree.column("ID", width=120, minwidth=100, stretch=True)
        self.tree.column("Name", width=250, minwidth=150, stretch=True)
        self.tree.column("Refills", width=100, minwidth=80, stretch=True)
        self.tree.column("Defects", width=100, minwidth=80, stretch=True)
        self.tree.column("Status", width=120, minwidth=100, stretch=True)
        self.tree.column("Modified", width=180, minwidth=150, stretch=True)
        
        # Grid layout for better space filling
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")
        
        # Store tree for inventory scrolling
        self.canvas_widgets['inventory'] = self.tree
        
        # Style for compact rows on small screens
        style = ttk.Style()
        style.configure("Treeview", rowheight=25, font=("Arial", 9))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        
        # Touch-friendly action buttons below tree
        action_button_frame = tk.Frame(list_frame)
        action_button_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        touch_buttons = [
            ("📱", self.view_qr_selected, "#3498db"),
            ("➕", self.refill_selected, "#27ae60"),
            ("⚠️", self.defect_selected, "#e74c3c"),
            ("🔍", self.view_details, "#9b59b6"),
            ("🗑️", self.delete_selected, "#95a5a6")
        ]
        
        for text, command, color in touch_buttons:
            tk.Button(
                action_button_frame,
                text=text,
                command=command,
                bg=color,
                fg="white",
                font=("Arial", 14),
                cursor="hand2",
                pady=5
            ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        # Context menu (still available for non-touch devices)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", lambda e: self.view_details())
    
    def add_gallon(self):
        """Add a new gallon and generate QR code"""
        name = self.name_entry.get().strip()
        
        if not name:
            messagebox.showwarning("Input Error", "Please enter Gallon Name")
            return
        
        # Auto-generate inventory ID
        inventory_id = self.db.generate_inventory_id()
        
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
                
                # Display QR code in app
                self.display_qr_code(qr_path, inventory_id, name)
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
        """Process scanned QR code data - Show choice between Refill and Defect"""
        inventory_id = data['inventory_id']
        gallon = self.db.get_gallon(inventory_id)
        
        if not gallon:
            messagebox.showerror("Not Found", f"Gallon {inventory_id} not found in database")
            return
        
        # Show action choice dialog
        action_window = tk.Toplevel(self.root)
        action_window.title("Choose Action")
        action_window.geometry("500x450")
        action_window.transient(self.root)
        action_window.grab_set()
        
        # Display info
        info_frame = tk.LabelFrame(action_window, text="Gallon Information", padx=25, pady=15, font=("Arial", 12, "bold"))
        info_frame.pack(fill=tk.BOTH, padx=20, pady=(20, 10))
        
        tk.Label(info_frame, text=f"ID: {gallon['inventory_id']}", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=4)
        tk.Label(info_frame, text=f"Name: {gallon['name']}", font=("Arial", 11)).pack(anchor=tk.W, pady=4)
        tk.Label(info_frame, text=f"Refills: {gallon['refills']}", font=("Arial", 11)).pack(anchor=tk.W, pady=4)
        tk.Label(info_frame, text=f"Defects: {gallon['defects']}", font=("Arial", 11)).pack(anchor=tk.W, pady=4)
        tk.Label(info_frame, text=f"Status: {gallon['status'].upper()}", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=4)
        
        # Choose action label
        tk.Label(
            action_window,
            text="What do you want to do?",
            font=("Arial", 14, "bold"),
            pady=15
        ).pack()
        
        # Actions
        action_frame = tk.Frame(action_window)
        action_frame.pack(fill=tk.BOTH, padx=20, pady=10)
        
        tk.Button(
            action_frame,
            text="➕ REFILL",
            command=lambda: self.record_refill(inventory_id, action_window),
            bg="#27ae60",
            fg="white",
            font=("Arial", 16, "bold"),
            cursor="hand2",
            pady=18
        ).pack(fill=tk.X, pady=8)
        
        if gallon['status'] == 'active':
            tk.Button(
                action_frame,
                text="⚠️ DEFECT",
                command=lambda: self.report_defect(inventory_id, action_window),
                bg="#e74c3c",
                fg="white",
                font=("Arial", 16, "bold"),
                cursor="hand2",
                pady=18
            ).pack(fill=tk.X, pady=8)
        else:
            tk.Button(
                action_frame,
                text="✅ FIX DEFECT",
                command=lambda: self.fix_defect(inventory_id, action_window),
                bg="#3498db",
                fg="white",
                font=("Arial", 16, "bold"),
                cursor="hand2",
                pady=18
            ).pack(fill=tk.X, pady=8)
        
        tk.Button(
            action_frame,
            text="Cancel",
            command=action_window.destroy,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 12),
            cursor="hand2",
            pady=12
        ).pack(fill=tk.X, pady=8)
        
        # Center the window
        action_window.update_idletasks()
        width = action_window.winfo_width()
        height = action_window.winfo_height()
        x = (action_window.winfo_screenwidth() // 2) - (width // 2)
        y = (action_window.winfo_screenheight() // 2) - (height // 2)
        action_window.geometry(f'+{x}+{y}')
    
    def display_qr_code(self, qr_path, inventory_id, name):
        """Display QR code in a new window within the app"""
        try:
            # Create new window
            qr_window = tk.Toplevel(self.root)
            qr_window.title(f"QR Code - {inventory_id}")
            qr_window.transient(self.root)
            
            # Load and display image
            img = Image.open(qr_path)
            
            # Resize if too large (max 600x600)
            max_size = 600
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            
            # Create frame
            frame = tk.Frame(qr_window, padx=20, pady=20)
            frame.pack()
            
            # Display info
            info_label = tk.Label(
                frame,
                text=f"QR Code for: {name} ({inventory_id})",
                font=("Arial", 12, "bold")
            )
            info_label.pack(pady=(0, 10))
            
            # Display image
            img_label = tk.Label(frame, image=photo)
            img_label.image = photo  # Keep a reference
            img_label.pack()
            
            # File path info
            path_label = tk.Label(
                frame,
                text=f"Saved to: {qr_path}",
                font=("Arial", 9),
                fg="gray"
            )
            path_label.pack(pady=(10, 0))
            
            # Buttons
            button_frame = tk.Frame(frame)
            button_frame.pack(pady=(15, 0))
            
            tk.Button(
                button_frame,
                text="Open in File Explorer",
                command=lambda: os.startfile(os.path.dirname(qr_path)),
                bg="#3498db",
                fg="white",
                font=("Arial", 10),
                cursor="hand2",
                padx=10
            ).pack(side=tk.LEFT, padx=5)
            
            tk.Button(
                button_frame,
                text="Close",
                command=qr_window.destroy,
                bg="#95a5a6",
                fg="white",
                font=("Arial", 10),
                cursor="hand2",
                padx=20
            ).pack(side=tk.LEFT, padx=5)
            
            # Center the window
            qr_window.update_idletasks()
            width = qr_window.winfo_width()
            height = qr_window.winfo_height()
            x = (qr_window.winfo_screenwidth() // 2) - (width // 2)
            y = (qr_window.winfo_screenheight() // 2) - (height // 2)
            qr_window.geometry(f'+{x}+{y}')
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not display QR code: {str(e)}")
    
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
        
        # Update graphs if on stats tab
        self.update_graphs()
    
    def update_graphs(self):
        """Update visual graphs in statistics panel"""
        try:
            # Clear previous graphs
            for widget in self.graph_canvas_frame.winfo_children():
                widget.destroy()
            
            stats = self.db.get_statistics()
            gallons = self.db.get_all_gallons()
            
            if not gallons:
                tk.Label(
                    self.graph_canvas_frame,
                    text="No data to display. Add gallons to see graphs.",
                    font=("Arial", 12),
                    fg="gray"
                ).pack(pady=50)
                return
            
            # Create figure with subplots
            fig = Figure(figsize=(10, 8), facecolor='#ecf0f1')
            
            # 1. Pie chart - Active vs Defective
            ax1 = fig.add_subplot(2, 2, 1)
            if stats['total_gallons'] > 0:
                sizes = [stats['active_gallons'], stats['defective_gallons']]
                labels = ['Active', 'Defective']
                colors = ['#27ae60', '#e74c3c']
                explode = (0.05, 0.05)
                
                ax1.pie(sizes, explode=explode, labels=labels, colors=colors,
                       autopct='%1.1f%%', shadow=True, startangle=90)
                ax1.set_title('Gallon Status Distribution', fontweight='bold', fontsize=11)
            
            # 2. Bar chart - Top 10 gallons by refills
            ax2 = fig.add_subplot(2, 2, 2)
            sorted_gallons = sorted(gallons, key=lambda x: x['refills'], reverse=True)[:10]
            if sorted_gallons:
                ids = [g['inventory_id'] for g in sorted_gallons]
                refills = [g['refills'] for g in sorted_gallons]
                
                bars = ax2.barh(ids, refills, color='#3498db')
                ax2.set_xlabel('Refills', fontweight='bold')
                ax2.set_title('Top 10 Most Refilled Gallons', fontweight='bold', fontsize=11)
                ax2.invert_yaxis()
                
                # Add value labels on bars
                for i, (bar, value) in enumerate(zip(bars, refills)):
                    ax2.text(value, i, f' {value}', va='center', fontweight='bold')
            
            # 3. Bar chart - Gallons with defects
            ax3 = fig.add_subplot(2, 2, 3)
            defective_gallons = [g for g in gallons if g['defects'] > 0][:10]
            if defective_gallons:
                ids = [g['inventory_id'] for g in defective_gallons]
                defects = [g['defects'] for g in defective_gallons]
                
                bars = ax3.bar(ids, defects, color='#e74c3c')
                ax3.set_ylabel('Defects', fontweight='bold')
                ax3.set_title('Gallons with Defects', fontweight='bold', fontsize=11)
                ax3.tick_params(axis='x', rotation=45)
                
                # Add value labels on bars
                for bar, value in zip(bars, defects):
                    height = bar.get_height()
                    ax3.text(bar.get_x() + bar.get_width()/2., height,
                            f'{int(value)}', ha='center', va='bottom', fontweight='bold')
            else:
                ax3.text(0.5, 0.5, 'No defects recorded!', 
                        ha='center', va='center', transform=ax3.transAxes,
                        fontsize=12, color='#27ae60', fontweight='bold')
                ax3.set_title('Gallons with Defects', fontweight='bold', fontsize=11)
            
            # 4. Summary statistics
            ax4 = fig.add_subplot(2, 2, 4)
            ax4.axis('off')
            
            summary_text = f"""
INVENTORY SUMMARY

Total Gallons: {stats['total_gallons']}
Active: {stats['active_gallons']} ({stats['active_gallons']/max(stats['total_gallons'],1)*100:.1f}%)
Defective: {stats['defective_gallons']} ({stats['defective_gallons']/max(stats['total_gallons'],1)*100:.1f}%)

Total Refills: {stats['total_refills']}
Avg Refills per Gallon: {stats['total_refills']/max(stats['total_gallons'],1):.1f}

Total Defects: {stats['total_defects']}
Avg Defects per Gallon: {stats['total_defects']/max(stats['total_gallons'],1):.2f}

Most Refilled: {sorted_gallons[0]['inventory_id'] if sorted_gallons else 'N/A'}
  ({sorted_gallons[0]['refills']} refills)
            """
            
            ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
                    fontsize=10, verticalalignment='top', family='monospace',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            fig.tight_layout(pad=2.0)
            
            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.graph_canvas_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            tk.Label(
                self.graph_canvas_frame,
                text=f"Error generating graphs: {str(e)}",
                font=("Arial", 10),
                fg="red"
            ).pack(pady=20)
    
    def show_context_menu(self, event):
        """Show context menu on right-click"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="View Details", command=self.view_details)
            menu.add_command(label="📱 View QR Code", command=self.view_qr_selected)
            menu.add_separator()
            menu.add_command(label="Record Refill", command=self.refill_selected)
            menu.add_command(label="Report Defect", command=self.defect_selected)
            menu.add_separator()
            menu.add_command(label="Delete Gallon", command=self.delete_selected)
            
            menu.post(event.x_root, event.y_root)
    
    def view_details(self):
        """View details of selected gallon with QR code"""
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
        details_window.geometry("900x600")
        
        # Main container with two columns
        main_frame = tk.Frame(details_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left column - Info and Activity
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Info section
        info_frame = tk.LabelFrame(left_frame, text="Gallon Information", padx=20, pady=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        for key, value in gallon.items():
            tk.Label(info_frame, text=f"{key.replace('_', ' ').title()}: {value}", 
                    font=("Arial", 10), anchor=tk.W).pack(fill=tk.X, pady=2)
        
        # Activity log section
        log_frame = tk.LabelFrame(left_frame, text="Recent Activity", padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        log_text = tk.Text(log_frame, height=10, font=("Courier", 9))
        log_text.pack(fill=tk.BOTH, expand=True)
        
        for activity in activity_log[:10]:  # Show last 10 activities
            log_text.insert(tk.END, f"[{activity['timestamp']}] {activity['activity_type']}\n")
            log_text.insert(tk.END, f"  {activity['description']}\n\n")
        
        log_text.config(state=tk.DISABLED)
        
        # Right column - QR Code
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        
        qr_frame = tk.LabelFrame(right_frame, text="QR Code", padx=15, pady=15)
        qr_frame.pack(fill=tk.BOTH, expand=True)
        
        # Check if QR code exists
        qr_path = os.path.join(self.qr_gen.output_dir, f"{inventory_id}_labeled.png")
        
        if os.path.exists(qr_path):
            try:
                # Load and display QR code
                img = Image.open(qr_path)
                
                # Resize to fit (max 400x400)
                max_size = 400
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(img)
                
                # Display image
                img_label = tk.Label(qr_frame, image=photo)
                img_label.image = photo  # Keep a reference
                img_label.pack(pady=10)
                
                # File path info
                path_label = tk.Label(
                    qr_frame,
                    text=f"Saved to:\n{qr_path}",
                    font=("Arial", 8),
                    fg="gray",
                    wraplength=350
                )
                path_label.pack(pady=(10, 0))
                
                # Open folder button
                tk.Button(
                    qr_frame,
                    text="Open Folder",
                    command=lambda: os.startfile(os.path.dirname(qr_path)),
                    bg="#3498db",
                    fg="white",
                    font=("Arial", 9),
                    cursor="hand2",
                    padx=15,
                    pady=5
                ).pack(pady=(10, 0))
                
            except Exception as e:
                tk.Label(
                    qr_frame,
                    text=f"Error loading QR code:\n{str(e)}",
                    font=("Arial", 10),
                    fg="red",
                    wraplength=350
                ).pack(pady=20)
        else:
            # QR code doesn't exist
            tk.Label(
                qr_frame,
                text="QR code not found",
                font=("Arial", 11, "bold"),
                fg="gray"
            ).pack(pady=20)
            
            tk.Button(
                qr_frame,
                text="Generate QR Code",
                command=lambda: self.generate_missing_qr(inventory_id, gallon['name'], details_window),
                bg="#27ae60",
                fg="white",
                font=("Arial", 10, "bold"),
                cursor="hand2",
                padx=20,
                pady=10
            ).pack(pady=10)
        
        # Bottom buttons
        button_frame = tk.Frame(details_window)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        tk.Button(
            button_frame,
            text="Close",
            command=details_window.destroy,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 10),
            cursor="hand2",
            padx=30,
            pady=8
        ).pack(side=tk.RIGHT, padx=5)
    
    def generate_missing_qr(self, inventory_id, name, parent_window):
        """Generate QR code that's missing and refresh the details window"""
        success, message, qr_path = self.qr_gen.generate_qr_with_label(inventory_id, name)
        if success:
            messagebox.showinfo("Success", "QR code generated successfully!")
            # Close and reopen details window to show new QR
            parent_window.destroy()
            self.view_details()
        else:
            messagebox.showerror("Error", f"Failed to generate QR code:\n{message}")
    
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
    
    def view_qr_selected(self):
        """View QR code for selected gallon"""
        selection = self.tree.selection()
        if not selection:
            return
        
        values = self.tree.item(selection[0])['values']
        inventory_id = values[0]
        name = values[1]
        
        # Check if QR code exists
        qr_path = os.path.join(self.qr_gen.output_dir, f"{inventory_id}_labeled.png")
        
        if os.path.exists(qr_path):
            self.display_qr_code(qr_path, inventory_id, name)
        else:
            # QR code doesn't exist, offer to generate it
            if messagebox.askyesno("QR Code Not Found", 
                                   f"QR code for {inventory_id} not found.\n\nWould you like to generate it now?"):
                success, message, qr_path = self.qr_gen.generate_qr_with_label(inventory_id, name)
                if success:
                    self.display_qr_code(qr_path, inventory_id, name)
                else:
                    messagebox.showerror("Error", f"Failed to generate QR code:\n{message}")
    
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
        self.name_entry.delete(0, tk.END)
        self.update_id_preview()
    
    def update_id_preview(self):
        """Update the preview of the next auto-generated ID"""
        try:
            next_id = self.db.generate_inventory_id()
            self.id_display.config(text=f"{next_id} (Next available)")
        except:
            self.id_display.config(text="WG-0001 (Next available)")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        return "break"
    
    def exit_fullscreen(self):
        """Exit fullscreen mode"""
        self.is_fullscreen = False
        self.root.attributes("-fullscreen", False)
        return "break"
    
    def on_mousewheel_global(self, event):
        """Handle mouse wheel scrolling globally based on active tab"""
        try:
            # Get the current active tab
            current_tab = self.notebook.index(self.notebook.select())
            
            # Tab 0: Inventory - scroll the tree
            if current_tab == 0 and 'inventory' in self.canvas_widgets:
                self.canvas_widgets['inventory'].yview_scroll(int(-1*(event.delta/120)), "units")
            
            # Tab 1: Controls - scroll the canvas
            elif current_tab == 1 and 'controls' in self.canvas_widgets:
                self.canvas_widgets['controls'].yview_scroll(int(-1*(event.delta/120)), "units")
            
            # Tab 2: Stats - scroll the canvas
            elif current_tab == 2 and 'stats' in self.canvas_widgets:
                self.canvas_widgets['stats'].yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass  # Silently ignore any scrolling errors
    
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
