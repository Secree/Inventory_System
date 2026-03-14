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
from pressure_sensor import PressureSensor
import os
import re
import serial
import serial.tools.list_ports
import threading
import time
from datetime import datetime
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# IoT components (optional — app still works if Flask is not installed)
try:
    import web_server
    import cloud_logger
    _IOT_AVAILABLE = True
except ImportError:
    _IOT_AVAILABLE = False


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
        
        # Initialize pressure sensor for leak detection
        try:
            self.pressure_sensor = PressureSensor(
                sensor_type='simulation',  # Avoid opening serial port at app startup
                pin=None,
                threshold=5.0,         # 5% pressure drop triggers leak
                monitoring_duration=30 # Monitor for 30 seconds
            )
            print("[SUCCESS] Pressure sensor initialized")
        except Exception as e:
            print(f"[WARNING] Pressure sensor not available: {e}")
            self.pressure_sensor = None
        
        # Arduino1 serial connection for automated workflow
        self.arduino_serial = None
        self.arduino_port = None
        # Arduino2 serial connection for secondary fill controller
        self.fill_arduino_serial = None
        self.fill_arduino_port = None
        self.fill_arduino_preferred_port = "COM7"
        self.workflow_state = "IDLE"  # IDLE, SCANNING, CHECKING_DEFECT, CHECKING_PRESSURE, MOVING, FILLING, COMPLETE
        self.current_gallon_id = None
        self.workflow_running = False
        self._qr_scan_after_id = None
        self.manual_defect_fallback = False
        self.arduino_firmware_unsupported = False
        self.arduino_firmware_warned = False
        
        # Arduino connection is manual via the Connect button to avoid
        # triggering board reset/self-test routines at app startup.
        
        # Track canvas widgets for scrolling
        self.canvas_widgets = {}

        # IoT — start Flask web server in background thread
        self.web_server_port = 5000
        self.web_server_url = ""
        self._start_iot_server()

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
            text="Water Gallon Inventory",
            font=("Arial", 14, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=10)
        
        # Fullscreen toggle button
        fullscreen_btn = tk.Button(
            title_frame,
            text="Full Screen",
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
        self.notebook.add(inventory_tab, text="Inventory")
        self.setup_inventory_list(inventory_tab)
        
        # Tab 2: Add Gallon only
        controls_tab = tk.Frame(self.notebook)
        self.notebook.add(controls_tab, text="Add Gallon")
        self.setup_add_gallon_panel(controls_tab)
        
        # Tab 3: Automated Workflow
        automation_tab = tk.Frame(self.notebook)
        self.notebook.add(automation_tab, text="🤖 Auto Workflow")
        self.setup_automation_panel(automation_tab)
        
        # Tab 4: Statistics
        stats_tab = tk.Frame(self.notebook)
        self.notebook.add(stats_tab, text="Stats")
        self.setup_statistics_panel(stats_tab)

        # Tab 5: IoT / Web Dashboard
        iot_tab = tk.Frame(self.notebook)
        self.notebook.add(iot_tab, text="🌐 IoT")
        self.setup_iot_panel(iot_tab)
    
    def _start_iot_server(self):
        """Start the Flask web server in a background daemon thread."""
        if not _IOT_AVAILABLE:
            self.web_server_url = "Flask not installed"
            return
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
        except Exception:
            local_ip = "127.0.0.1"

        self.web_server_url = f"http://{local_ip}:{self.web_server_port}"
        web_server.start_server_thread(self.db, port=self.web_server_port)
        print(f"[IoT] Web dashboard: {self.web_server_url}")

    def setup_iot_panel(self, parent):
        """IoT / Web Dashboard control panel."""
        outer = tk.Frame(parent, bg="#1a1a2e")
        outer.pack(fill=tk.BOTH, expand=True)

        # ── Title bar ──────────────────────────────────────────────
        title_bar = tk.Frame(outer, bg="#16213e", pady=10)
        title_bar.pack(fill=tk.X)
        tk.Label(title_bar, text="🌐 IoT Dashboard & Remote Monitoring",
                 font=("Arial", 14, "bold"), bg="#16213e", fg="#4fc3f7").pack()

        content = tk.Frame(outer, bg="#1a1a2e", padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)

        # ── Web Dashboard card ─────────────────────────────────────
        web_card = tk.LabelFrame(content, text="  🖥  Local Network Dashboard  ",
                                 font=("Arial", 11, "bold"),
                                 fg="#4fc3f7", bg="#16213e",
                                 labelanchor="n", padx=15, pady=15)
        web_card.pack(fill=tk.X, pady=(0, 12))

        if _IOT_AVAILABLE:
            status_color = "#66bb6a"
            status_text = "● Running"
        else:
            status_color = "#ef5350"
            status_text = "● Flask not installed"

        tk.Label(web_card, text=status_text, font=("Arial", 10, "bold"),
                 fg=status_color, bg="#16213e").pack()

        url_frame = tk.Frame(web_card, bg="#0d1117", bd=1, relief=tk.SUNKEN, padx=8, pady=6)
        url_frame.pack(fill=tk.X, pady=8)

        self.iot_url_label = tk.Label(url_frame, text=self.web_server_url or "—",
                                      font=("Courier", 11, "bold"),
                                      fg="#ffa726", bg="#0d1117", cursor="hand2")
        self.iot_url_label.pack()
        self.iot_url_label.bind("<Button-1>", self._open_dashboard_browser)

        hint = "Click the URL above to open in your browser, or enter it on any device connected to the same Wi-Fi."
        tk.Label(web_card, text=hint, font=("Arial", 9), fg="#8892b0",
                 bg="#16213e", wraplength=540, justify=tk.CENTER).pack(pady=(0, 4))

        btn_row = tk.Frame(web_card, bg="#16213e")
        btn_row.pack()
        tk.Button(btn_row, text="🌍 Open in Browser",
                  command=self._open_dashboard_browser,
                  bg="#4fc3f7", fg="#000", font=("Arial", 10, "bold"),
                  cursor="hand2", padx=14, pady=5, relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row, text="📋 Copy URL",
                  command=self._copy_dashboard_url,
                  bg="#22263a", fg="#e8eaf6", font=("Arial", 10),
                  cursor="hand2", padx=14, pady=5, relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

        # ── API Endpoints card ─────────────────────────────────────
        api_card = tk.LabelFrame(content, text="  📡  REST API Endpoints  ",
                                 font=("Arial", 11, "bold"),
                                 fg="#ab47bc", bg="#16213e",
                                 labelanchor="n", padx=15, pady=12)
        api_card.pack(fill=tk.X, pady=(0, 12))

        base = self.web_server_url if self.web_server_url and "http" in self.web_server_url else "http://<ip>:5000"
        endpoints = [
            ("GET",  f"{base}/api/inventory",       "All gallons (JSON)"),
            ("GET",  f"{base}/api/stats",            "Statistics summary"),
            ("GET",  f"{base}/api/activity",         "Activity log (last 50)"),
            ("GET",  f"{base}/api/sensor",           "Live sensor readings"),
            ("POST", f"{base}/api/inventory/<id>/refill", "Trigger a refill"),
            ("POST", f"{base}/api/inventory/<id>/defect", "Report a defect"),
        ]

        for method, path, desc in endpoints:
            row = tk.Frame(api_card, bg="#16213e")
            row.pack(fill=tk.X, pady=1)
            method_color = "#66bb6a" if method == "GET" else "#ffa726"
            tk.Label(row, text=f" {method} ", font=("Courier", 9, "bold"),
                     fg=method_color, bg="#0d1117", width=5).pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(row, text=path, font=("Courier", 9),
                     fg="#e8eaf6", bg="#16213e", anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=f" — {desc}", font=("Arial", 9),
                     fg="#8892b0", bg="#16213e", anchor="w").pack(side=tk.LEFT)

        # ── Cloud Logger card ──────────────────────────────────────
        cloud_card = tk.LabelFrame(content, text="  ☁  Cloud Sync (Firebase)  ",
                                   font=("Arial", 11, "bold"),
                                   fg="#66bb6a", bg="#16213e",
                                   labelanchor="n", padx=15, pady=12)
        cloud_card.pack(fill=tk.X, pady=(0, 12))

        if _IOT_AVAILABLE:
            cloud_ok = cloud_logger.is_connected()
            cloud_status = ("● Connected" if cloud_ok else "○ Disabled — add firebase_credentials.json to enable")
            cloud_color  = "#66bb6a" if cloud_ok else "#8892b0"
        else:
            cloud_status = "○ cloud_logger not loaded"
            cloud_color  = "#8892b0"

        tk.Label(cloud_card, text=cloud_status, font=("Arial", 10),
                 fg=cloud_color, bg="#16213e").pack()

        cloud_hint = ("Create firebase_credentials.json and firebase_config.json in the project folder to enable "
                      "real-time cloud sync with Firebase Realtime Database.")
        tk.Label(cloud_card, text=cloud_hint, font=("Arial", 9), fg="#8892b0",
                 bg="#16213e", wraplength=540, justify=tk.CENTER).pack(pady=(6, 0))

    def _open_dashboard_browser(self, _event=None):
        """Open the web dashboard URL in the default browser."""
        url = self.web_server_url
        if not url or "http" not in url:
            messagebox.showinfo("IoT Dashboard", "Web server is not running.\nInstall Flask: pip install flask flask-cors")
            return
        import webbrowser
        webbrowser.open(url)

    def _copy_dashboard_url(self):
        """Copy the dashboard URL to the clipboard."""
        url = self.web_server_url
        if not url:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        messagebox.showinfo("Copied", f"URL copied to clipboard:\n{url}")

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
        stats_frame = tk.LabelFrame(stats_container, text="Statistics", font=("Arial", 12, "bold"), padx=10, pady=10)
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
        graph_frame = tk.LabelFrame(stats_container, text="Visual Analytics", font=("Arial", 12, "bold"), padx=10, pady=10)
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
        """Setup add gallon panel - centred, max-width card layout"""
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Outer wrapper so the card stays centred and has max width
        wrapper = tk.Frame(parent)
        wrapper.grid(row=0, column=0)

        card = tk.LabelFrame(wrapper, text="Add New Gallon",
                             font=("Arial", 13, "bold"), padx=20, pady=18)
        card.pack(padx=40, pady=40, ipadx=10, ipady=6)
        card.config(width=520)

        # Auto-generated ID
        tk.Label(card, text="Inventory ID (Auto-generated):",
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 4))
        self.id_display = tk.Label(card, text="Will be generated automatically",
                                   font=("Arial", 11), bg="#ecf0f1",
                                   anchor=tk.W, padx=10, pady=8, width=44)
        self.id_display.pack(fill=tk.X, pady=(0, 14))

        # Gallon Name
        tk.Label(card, text="Gallon Name:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 4))
        self.name_entry = tk.Entry(card, font=("Arial", 12))
        self.name_entry.pack(fill=tk.X, pady=(0, 16), ipady=8)
        self.name_entry.bind('<KeyRelease>', lambda e: self.update_id_preview())

        # Buttons
        btn_frame = tk.Frame(card)
        btn_frame.pack(fill=tk.X)

        tk.Button(
            btn_frame, text="➕  Add & Generate QR",
            command=self.add_gallon,
            bg="#27ae60", fg="white", font=("Arial", 11, "bold"),
            cursor="hand2", pady=12
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6))

        tk.Button(
            btn_frame, text="Clear",
            command=self.clear_form,
            bg="#95a5a6", fg="white",
            font=("Arial", 11), cursor="hand2", pady=12
        ).pack(side=tk.RIGHT, expand=True, fill=tk.X)
    
    def setup_qr_scanner_panel(self, parent):
        """Setup QR scanner panel"""
        scanner_frame = tk.LabelFrame(parent, text="QR Code Scanner", font=("Arial", 11, "bold"), padx=10, pady=10)
        scanner_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # USB Handheld Scanner Input (MH-ET LIVE and similar)
        usb_scanner_frame = tk.LabelFrame(
            scanner_frame,
            text="🔴 Handheld Scanner (MH-ET LIVE)",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=8,
            fg="#e74c3c"
        )
        usb_scanner_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            usb_scanner_frame,
            text="Click field, press scanner button, scan QR code:",
            font=("Arial", 9),
            fg="gray"
        ).pack(pady=(0, 5))
        
        # Input frame with entry and clear button
        input_frame = tk.Frame(usb_scanner_frame)
        input_frame.pack(fill=tk.X)
        
        self.scanner_input = tk.Entry(
            input_frame,
            font=("Arial", 12),
            bg="#fff3cd",
            fg="#000",
            relief=tk.SOLID,
            borderwidth=2
        )
        self.scanner_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.scanner_input.bind('<Return>', self.process_scanner_input)
        self.scanner_input.bind('<KP_Enter>', self.process_scanner_input)  # Numpad Enter
        
        tk.Button(
            input_frame,
            text="✕",
            command=lambda: self.scanner_input.delete(0, tk.END),
            bg="#95a5a6",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=3
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        tk.Label(
            usb_scanner_frame,
            text="✓ Auto-processes when scanner sends data",
            font=("Arial", 8),
            fg="#27ae60"
        ).pack(pady=(5, 0))
        
        # Separator
        tk.Frame(scanner_frame, height=2, bg="#bdc3c7").pack(fill=tk.X, pady=10)
        
        # Camera/Image Scanning Options
        tk.Label(
            scanner_frame,
            text="Or scan using camera/image:",
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
    
    def setup_automation_panel(self, parent):
        """Setup automated workflow panel with GUI controls - 2 column layout"""
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

        # ── Top banner (full width) ──────────────────────────────────────────
        banner = tk.Frame(parent, bg="#2c3e50", padx=15, pady=12)
        banner.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 0))

        tk.Label(banner, text="🤖 Automated Gallon Workflow",
                 font=("Arial", 14, "bold"), bg="#2c3e50", fg="white").pack(side=tk.LEFT)

        right_banner = tk.Frame(banner, bg="#2c3e50")
        right_banner.pack(side=tk.RIGHT)

        tk.Button(right_banner, text="🔄 Connect", command=self.connect_arduino,
                  bg="#3498db", fg="white", font=("Arial", 9, "bold"),
                  cursor="hand2", padx=8, pady=4, relief=tk.FLAT
        ).pack(side=tk.RIGHT)

        self.fill_arduino_status_label = tk.Label(
            right_banner, text="⚠ Arduino2: Not Connected",
            font=("Arial", 9, "bold"), bg="#e74c3c", fg="white", padx=8, pady=4
        )
        self.fill_arduino_status_label.pack(side=tk.RIGHT, padx=(10, 0))

        # Arduino connection badge on the right of banner
        self.arduino_status_label = tk.Label(
            banner, text="⚠ Arduino1: Not Connected",
            font=("Arial", 9, "bold"), bg="#e74c3c", fg="white", padx=8, pady=4
        )
        self.arduino_status_label.pack(side=tk.RIGHT, padx=(10, 0))
        self.refresh_arduino_connection_badges()

        # ── LEFT COLUMN: Steps 1, 2, 3 ──────────────────────────────────────
        left = tk.Frame(parent, padx=8, pady=8)
        left.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_columnconfigure(0, weight=1)

        # Step 1 – QR Scan
        step1 = tk.LabelFrame(left, text="Step 1 — Scan QR Code",
                              font=("Arial", 11, "bold"), bg="#f0f4f8", padx=10, pady=10)
        step1.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        step1.grid_columnconfigure(0, weight=1)

        tk.Label(step1, text="Click field then scan with handheld scanner:",
                 font=("Arial", 9), fg="#555", bg="#f0f4f8").grid(row=0, column=0, sticky="w")

        self.auto_qr_input = tk.Entry(
            step1, font=("Arial", 13, "bold"),
            bg="#fff3cd", fg="#000", relief=tk.SOLID, borderwidth=2, justify=tk.CENTER
        )
        self.auto_qr_input.grid(row=1, column=0, sticky="ew", pady=6, ipady=10)
        self.auto_qr_input.bind('<Return>', lambda e: self.workflow_scan_qr(force=True))
        self.auto_qr_input.bind('<KP_Enter>', lambda e: self.workflow_scan_qr(force=True))
        self.auto_qr_input.bind('<Tab>', lambda e: self.workflow_scan_qr(force=True) or "break")
        self.auto_qr_input.bind('<KeyRelease>', self.schedule_workflow_scan)

        self.qr_status_label = tk.Label(
            step1, text="Waiting for scan...",
            font=("Arial", 10), bg="#f0f4f8", fg="#888"
        )
        self.qr_status_label.grid(row=2, column=0, pady=(0, 2))

        # Step 2 – Combined Pressure/Defect Decision
        step2 = tk.LabelFrame(left, text="Step 2 — Pressure + Defect Decision",
                              font=("Arial", 11, "bold"), bg="#f0f4f8", padx=10, pady=10)
        step2.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        step2.grid_columnconfigure(0, weight=1)
        step2.grid_columnconfigure(1, weight=1)

        tk.Label(step2, text="Pressure checks automatically. If unavailable, decide manually:",
                 font=("Arial", 10, "bold"), bg="#f0f4f8").grid(
                 row=0, column=0, columnspan=2, pady=(0, 8))

        self.defect_btn = tk.Button(
            step2, text="❌  DEFECT FOUND",
            command=lambda: self.workflow_defect_check(has_defect=True),
            bg="#e74c3c", fg="white", font=("Arial", 11, "bold"),
            cursor="hand2", pady=18, state=tk.DISABLED
        )
        self.defect_btn.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        self.no_defect_btn = tk.Button(
            step2, text="✓  NO DEFECT",
            command=lambda: self.workflow_defect_check(has_defect=False),
            bg="#27ae60", fg="white", font=("Arial", 11, "bold"),
            cursor="hand2", pady=18, state=tk.DISABLED
        )
        self.no_defect_btn.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        self.defect_status_label = tk.Label(
            step2, text="", font=("Arial", 10), bg="#f0f4f8"
        )
        self.defect_status_label.grid(row=2, column=0, columnspan=2, pady=(8, 0))

        # Pressure status (part of Step 2 flow)
        step3 = tk.LabelFrame(left, text="Pressure Status (Step 2)",
                              font=("Arial", 11, "bold"), bg="#f0f4f8", padx=10, pady=10)
        step3.grid(row=2, column=0, sticky="ew")
        step3.grid_columnconfigure(0, weight=1)

        self.pressure_status_label = tk.Label(
            step3, text="Waiting…",
            font=("Arial", 11, "bold"), bg="#f0f4f8", padx=10, pady=14
        )
        self.pressure_status_label.grid(row=0, column=0, sticky="ew")

        self.pressure_value_label = tk.Label(
            step3, text="Pressure: --",
            font=("Arial", 10), bg="#f0f4f8", fg="#555"
        )
        self.pressure_value_label.grid(row=1, column=0, pady=(2, 6))

        # ── RIGHT COLUMN: Step 3 + Controls + Log ────────────────────────────
        right = tk.Frame(parent, padx=8, pady=8)
        right.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)   # log expands

        # Step 3 – Automatic Filling
        step4 = tk.LabelFrame(right, text="Step 3 — Automatic Filling",
                              font=("Arial", 11, "bold"), bg="#f0f4f8", padx=10, pady=10)
        step4.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        step4.grid_columnconfigure(0, weight=1)
        step4.grid_columnconfigure(1, weight=1)
        step4.grid_columnconfigure(2, weight=1)
        step4.grid_columnconfigure(3, weight=1)

        self.filling_status_label = tk.Label(
            step4, text="Waiting…", font=("Arial", 11, "bold"),
            bg="#f0f4f8", padx=10, pady=12
        )
        self.filling_status_label.grid(row=0, column=0, columnspan=4, sticky="ew")

        # Indicator dots grid
        indicators = [
            ("Conveyor",    "conveyor_status",    0, 0),
            ("Position",    "position_status",    0, 2),
            ("Valve",       "valve_status",       1, 0),
            ("Water Level", "water_level_status", 1, 2),
        ]
        for label_text, attr, row, col in indicators:
            tk.Label(step4, text=f"{label_text}:", font=("Arial", 9),
                     bg="#f0f4f8").grid(row=row + 1, column=col, sticky="e", padx=(6, 2), pady=6)
            dot = tk.Label(step4, text="●", font=("Arial", 16), fg="#bdc3c7", bg="#f0f4f8")
            dot.grid(row=row + 1, column=col + 1, sticky="w", padx=(0, 6))
            setattr(self, attr, dot)

        self.ultrasonic_distance_label = tk.Label(
            step4, text="Distance: -- cm", font=("Arial", 9), bg="#f0f4f8", fg="#555"
        )
        self.ultrasonic_distance_label.grid(row=3, column=0, columnspan=4, pady=(0, 4))

        # Control Buttons
        ctrl = tk.Frame(right, padx=2, pady=2)
        ctrl.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctrl.grid_columnconfigure(0, weight=1)
        ctrl.grid_columnconfigure(1, weight=1)
        ctrl.grid_columnconfigure(2, weight=1)

        self.start_workflow_btn = tk.Button(
            ctrl, text="▶ START",
            command=self.start_automated_workflow,
            bg="#27ae60", fg="white", font=("Arial", 11, "bold"),
            cursor="hand2", pady=14
        )
        self.start_workflow_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self.stop_workflow_btn = tk.Button(
            ctrl, text="⏹ STOP",
            command=self.stop_automated_workflow,
            bg="#e74c3c", fg="white", font=("Arial", 11, "bold"),
            cursor="hand2", pady=14, state=tk.DISABLED
        )
        self.stop_workflow_btn.grid(row=0, column=1, sticky="ew", padx=3)

        self.reset_workflow_btn = tk.Button(
            ctrl, text="🔄 RESET",
            command=self.reset_workflow,
            bg="#95a5a6", fg="white", font=("Arial", 11, "bold"),
            cursor="hand2", pady=14
        )
        self.reset_workflow_btn.grid(row=0, column=2, sticky="ew", padx=(3, 0))

        # Workflow Log
        log_frame = tk.LabelFrame(right, text="Workflow Log",
                                  font=("Arial", 10, "bold"), padx=6, pady=6)
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.grid(row=0, column=1, sticky="ns")

        self.workflow_log = tk.Text(
            log_frame, font=("Consolas", 9),
            bg="#2c3e50", fg="#ecf0f1",
            yscrollcommand=log_scroll.set,
            state=tk.DISABLED, wrap=tk.WORD
        )
        self.workflow_log.grid(row=0, column=0, sticky="nsew")
        log_scroll.config(command=self.workflow_log.yview)
    
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
            ("View", self.view_qr_selected, "#3498db"),
            ("Refill", self.refill_selected, "#27ae60"),
            ("Defect", self.defect_selected, "#e74c3c"),
            ("View", self.view_details, "#9b59b6"),
            ("Delete", self.delete_selected, "#95a5a6")
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
    
    def process_scanner_input(self, event=None):
        """Process input from USB handheld scanner (MH-ET LIVE, etc.)"""
        scanned_text = self.scanner_input.get().strip()
        
        if not scanned_text:
            return
        
        # Clear the input field
        self.scanner_input.delete(0, tk.END)
        
        # Parse the scanned data
        # Expected format: "INVENTORY_ID:WG-0001|NAME:Blue Container"
        try:
            data_dict = {}
            parts = scanned_text.split('|')
            
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    data_dict[key.strip()] = value.strip()
            
            # Check if we have the required fields
            if 'INVENTORY_ID' in data_dict:
                # Get gallon from database to verify and get name
                gallon = self.db.get_gallon(data_dict['INVENTORY_ID'])
                
                if gallon:
                    # Process as normal scanned QR
                    processed_data = {
                        'inventory_id': data_dict['INVENTORY_ID'],
                        'name': gallon['name']
                    }
                    self.process_scanned_qr(processed_data)
                else:
                    messagebox.showerror(
                        "Not Found",
                        f"Gallon ID '{data_dict['INVENTORY_ID']}' not found in database."
                    )
            else:
                # Try to extract inventory ID pattern (WG-####)
                inventory_match = re.search(r'WG-\d{4}', scanned_text)
                
                if inventory_match:
                    inventory_id = inventory_match.group(0)
                    gallon = self.db.get_gallon(inventory_id)
                    
                    if gallon:
                        processed_data = {
                            'inventory_id': inventory_id,
                            'name': gallon['name']
                        }
                        self.process_scanned_qr(processed_data)
                    else:
                        messagebox.showerror(
                            "Not Found",
                            f"Gallon ID '{inventory_id}' not found in database."
                        )
                else:
                    messagebox.showerror(
                        "Invalid Format",
                        f"Could not parse scanned data:\n{scanned_text}\n\n"
                        "Expected format: INVENTORY_ID:WG-0001|NAME:..."
                    )
        
        except Exception as e:
            messagebox.showerror(
                "Scan Error",
                f"Error processing scanned data:\n{str(e)}\n\nScanned text:\n{scanned_text}"
            )
    
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
            text="REFILL",
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
                text="DEFECT",
                command=lambda: self.report_defect(inventory_id, action_window),
                bg="#e74c3c",
                fg="white",
                font=("Arial", 16, "bold"),
                cursor="hand2",
                pady=18
            ).pack(fill=tk.X, pady=8)
            
            # Add Leak Detection button if pressure sensor is available
            if self.pressure_sensor:
                tk.Button(
                    action_frame,
                    text="🔍 TEST FOR LEAKS",
                    command=lambda: self.start_leak_detection(inventory_id, action_window),
                    bg="#f39c12",
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
            if _IOT_AVAILABLE:
                gallon = self.db.get_gallon(inventory_id)
                cloud_logger.log_refill(inventory_id, gallon.get('name', '') if gallon else '')
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
                if _IOT_AVAILABLE:
                    gallon = self.db.get_gallon(inventory_id)
                    cloud_logger.log_defect(inventory_id, gallon.get('name', '') if gallon else '')
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
    
    def start_leak_detection(self, inventory_id, parent_window=None):
        """Start automated leak detection for a gallon"""
        if not self.pressure_sensor:
            messagebox.showerror("Error", "Pressure sensor not available")
            return
        
        # Check if already monitoring
        if self.pressure_sensor.is_monitoring:
            messagebox.showwarning("Busy", "Already monitoring another gallon. Please wait.")
            return
        
        # Create monitoring window
        monitor_window = tk.Toplevel(self.root)
        monitor_window.title(f"Leak Detection - {inventory_id}")
        monitor_window.geometry("500x400")
        monitor_window.transient(self.root)
        monitor_window.grab_set()
        
        # Instructions
        tk.Label(
            monitor_window,
            text=f"🔍 Testing Gallon {inventory_id} for Leaks",
            font=("Arial", 16, "bold"),
            pady=20
        ).pack()
        
        tk.Label(
            monitor_window,
            text="Please place gallon on pressure sensor\nand ensure proper seal.",
            font=("Arial", 11),
            justify=tk.CENTER,
            pady=10
        ).pack()
        
        # Status frame
        status_frame = tk.LabelFrame(monitor_window, text="Test Status", padx=20, pady=15)
        status_frame.pack(fill=tk.BOTH, padx=20, pady=20)
        
        # Status labels
        status_label = tk.Label(status_frame, text="⏳ Initializing...", font=("Arial", 12, "bold"))
        status_label.pack(pady=5)
        
        baseline_label = tk.Label(status_frame, text="Baseline: -- PSI", font=("Arial", 10))
        baseline_label.pack(pady=3)
        
        current_label = tk.Label(status_frame, text="Current: -- PSI", font=("Arial", 10))
        current_label.pack(pady=3)
        
        drop_label = tk.Label(status_frame, text="Drop: --%", font=("Arial", 10))
        drop_label.pack(pady=3)
        
        time_label = tk.Label(status_frame, text="Elapsed: 0s / 30s", font=("Arial", 10))
        time_label.pack(pady=3)
        
        # Progress bar
        progress = ttk.Progressbar(monitor_window, length=400, mode='determinate')
        progress.pack(pady=10)
        
        # Cancel button
        cancel_btn = tk.Button(
            monitor_window,
            text="Cancel Test",
            command=lambda: self.cancel_leak_detection(monitor_window),
            bg="#95a5a6",
            fg="white",
            font=("Arial", 11),
            cursor="hand2",
            padx=20
        )
        cancel_btn.pack(pady=10)
        
        # Start monitoring
        def leak_callback(inv_id, drop_pct, baseline, current):
            """Called when leak is detected"""
            # Update UI
            status_label.config(text="🚨 LEAK DETECTED!", fg="red")
            
            # Add defect to database
            success, message = self.db.add_defect(inv_id)
            
            if success:
                # Log the event
                self.logger.log(
                    f"LEAK DETECTED - {inv_id}: "
                    f"Pressure dropped {drop_pct:.2f}% "
                    f"({baseline:.2f} → {current:.2f} PSI)"
                )
                
                # Show result
                messagebox.showwarning(
                    "🚨 Leak Detected!",
                    f"Gallon {inv_id} has a leak!\n\n"
                    f"Pressure Drop: {drop_pct:.2f}%\n"
                    f"Baseline: {baseline:.2f} PSI\n"
                    f"Current: {current:.2f} PSI\n\n"
                    f"✅ Defect counter incremented automatically."
                )
                
                # Refresh display
                self.refresh_inventory_list()
                self.update_statistics()
                
                # Close windows
                monitor_window.destroy()
                if parent_window:
                    parent_window.destroy()
            else:
                messagebox.showerror("Error", f"Could not record defect: {message}")
        
        # Update loop
        def update_status():
            if self.pressure_sensor.is_monitoring:
                status = self.pressure_sensor.get_status()
                
                # Update labels
                if status['baseline_pressure'] > 0:
                    baseline_label.config(text=f"Baseline: {status['baseline_pressure']:.2f} PSI")
                    current_label.config(text=f"Current: {status['current_pressure']:.2f} PSI")
                    drop_label.config(text=f"Drop: {status['pressure_drop']:.2f}%")
                    time_label.config(text=f"Elapsed: {int(status['elapsed_time'])}s / 30s")
                    
                    # Update progress bar
                    progress['value'] = (status['elapsed_time'] / 30.0) * 100
                    
                    # Update status text
                    if status['elapsed_time'] < 5:
                        status_label.config(text="⏳ Stabilizing...", fg="orange")
                    else:
                        status_label.config(text="📊 Monitoring pressure...", fg="blue")
                
                # Schedule next update
                monitor_window.after(500, update_status)
            else:
                # Monitoring finished
                if not self.pressure_sensor.leak_detected:
                    status_label.config(text="✅ NO LEAK DETECTED", fg="green")
                    progress['value'] = 100
                    
                    # Show success message
                    messagebox.showinfo(
                        "✅ Test Complete",
                        f"Gallon {inventory_id} passed leak test!\n\n"
                        "No pressure drop detected.\n"
                        "Gallon is sealed properly."
                    )
                    
                    # Log the test
                    self.logger.log(f"LEAK TEST PASSED - {inventory_id}: No leak detected")
                    
                    # Close windows
                    monitor_window.destroy()
                    if parent_window:
                        parent_window.destroy()
        
        # Start monitoring in separate thread
        self.pressure_sensor.start_monitoring(inventory_id, callback=leak_callback)
        
        # Start UI update loop
        monitor_window.after(500, update_status)
    
    def cancel_leak_detection(self, window):
        """Cancel ongoing leak detection"""
        if self.pressure_sensor and self.pressure_sensor.is_monitoring:
            self.pressure_sensor.stop_monitoring()
            messagebox.showinfo("Cancelled", "Leak detection test cancelled.")
        window.destroy()
    
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
            
            # Tab 3: Stats - scroll the canvas
            elif current_tab == 3 and 'stats' in self.canvas_widgets:
                self.canvas_widgets['stats'].yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass  # Silently ignore any scrolling errors
    
    # ========================================================================
    # AUTOMATED WORKFLOW METHODS
    # ========================================================================
    
    def extract_inventory_id(self, qr_data):
        """Extract inventory ID from QR code data"""
        try:
            # Try format: "INVENTORY_ID:WG-0001|NAME:..."
            if 'INVENTORY_ID:' in qr_data:
                parts = qr_data.split('|')
                for part in parts:
                    if 'INVENTORY_ID:' in part:
                        return part.split(':', 1)[1].strip()
            
            # Try to find WG-#### pattern
            inventory_match = re.search(r'WG-\d{4}', qr_data)
            if inventory_match:
                return inventory_match.group(0)
            
            return None
        except:
            return None
    
    def connect_arduino(self):
        """Connect to Arduino1 for automated workflow"""
        try:
            self.arduino_firmware_unsupported = False
            self.arduino_firmware_warned = False

            # Proactively connect Arduino2 so user can verify it is reachable.
            fill_connected = self.ensure_fill_arduino_connected()
            if fill_connected:
                self.log_workflow(f"✓ Arduino2 ready on {self.fill_arduino_port}")
            else:
                self.log_workflow(
                    f"⚠ Arduino2 not detected on {self.fill_arduino_preferred_port}. "
                    "Check USB cable/port and close Serial Monitor."
                )

            # If we already hold a serial handle, close it before reconnecting.
            if self.arduino_serial and hasattr(self.arduino_serial, 'is_open') and self.arduino_serial.is_open:
                try:
                    self.arduino_serial.close()
                except Exception:
                    pass
                self.arduino_serial = None

            # Reuse the serial connection already opened by PressureSensor to avoid
            # opening the same port twice (which causes PermissionError on Windows).
            if (self.pressure_sensor is not None
                    and hasattr(self.pressure_sensor, 'sensor')
                    and self.pressure_sensor.sensor is not None
                    and hasattr(self.pressure_sensor.sensor, 'is_open')
                    and self.pressure_sensor.sensor.is_open):
                self.arduino_serial = self.pressure_sensor.sensor
                self.arduino_port = self.arduino_serial.port
                self.log_workflow(f"✓ Connected to Arduino1 on {self.arduino_port} (shared connection)")
                self.refresh_arduino_connection_badges()
                self.start_arduino_monitor()
                return True

            # PressureSensor not available — open a fresh connection
            ports = list(serial.tools.list_ports.comports())
            if not ports:
                self.log_workflow("⚠ No Arduino1 found")
                return fill_connected

            # Prioritize COM11, then likely Arduino USB serial devices.
            # Never use Arduino2 preferred port for Arduino1 connection.
            # Use the actual connected port (fill_arduino_port) if available,
            # otherwise fall back to the preferred port setting.
            blocked_port = self.fill_arduino_port or self.fill_arduino_preferred_port
            priority_ports = []
            for port in ports:
                if port.device == 'COM11' and port.device != blocked_port:
                    priority_ports.append(port.device)
            for port in ports:
                if (port.device != blocked_port and
                        ('Arduino' in port.description or 'CH340' in port.description or 'USB Serial' in port.description) and
                        port.device not in priority_ports):
                    priority_ports.append(port.device)
            for port in ports:
                if port.device != blocked_port and port.device not in priority_ports:
                    priority_ports.append(port.device)

            last_error = None
            for candidate in priority_ports:
                try:
                    self.arduino_serial = serial.Serial(candidate, 9600, timeout=1)
                    self.arduino_port = candidate
                    time.sleep(2)  # Wait for Arduino to reset

                    # Identify Arduino2 fill firmware and skip it for Arduino1 slot.
                    banner = []
                    probe_deadline = time.time() + 0.8
                    while time.time() < probe_deadline:
                        if self.arduino_serial.in_waiting:
                            line = self.arduino_serial.readline().decode('utf-8', errors='ignore').strip()
                            if line:
                                banner.append(line.upper())
                        else:
                            time.sleep(0.05)

                    banner_text = " ".join(banner)
                    if ("ENABLE | DISABLE | STATUS" in banner_text or
                            "FILL:ENABLED" in banner_text or
                            "FILL:DISABLED" in banner_text):
                        self.log_workflow(f"⚠ {candidate} appears to be Arduino2 firmware; skipping for Arduino1")
                        try:
                            self.arduino_serial.close()
                        except Exception:
                            pass
                        self.arduino_serial = None
                        self.arduino_port = None
                        continue

                    self.log_workflow(f"✓ Connected to Arduino1 on {candidate}")
                    self.refresh_arduino_connection_badges()

                    # Start monitoring thread
                    self.start_arduino_monitor()
                    return True
                except Exception as err:
                    last_error = err
                    self.log_workflow(f"⚠ Could not open {candidate}: {err}")

            self.log_workflow("❌ Could not open any serial port for Arduino1. Close Arduino Serial Monitor/other apps using COM ports and try Connect again.")
            if last_error:
                self.log_workflow(f"❌ Last port error: {last_error}")
            self.arduino_serial = None
            self.arduino_port = None
            self.refresh_arduino_connection_badges()
            return fill_connected

        except Exception as e:
            self.log_workflow(f"❌ Arduino1 connection error: {e}")
            self.arduino_serial = None
            self.arduino_port = None
            self.refresh_arduino_connection_badges()
            return False
    
    def start_arduino_monitor(self):
        """Start thread to monitor Arduino responses"""
        def monitor():
            while self.arduino_serial and self.arduino_serial.is_open:
                try:
                    if self.arduino_serial.in_waiting:
                        line = self.arduino_serial.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            self.process_arduino_response(line)
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Monitor error: {e}")
                    break
            self.root.after(0, self.refresh_arduino_connection_badges)
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

    def ensure_fill_arduino_connected(self):
        """Connect to Arduino2 (secondary controller for solenoid fill)."""
        if self.fill_arduino_serial and self.fill_arduino_serial.is_open:
            self.refresh_arduino_connection_badges()
            return True

        ports = list(serial.tools.list_ports.comports())
        if not ports:
            return False

        candidates = []
        if self.fill_arduino_preferred_port:
            candidates.append(self.fill_arduino_preferred_port)

        for port in ports:
            if port.device == self.arduino_port:
                continue
            if ('Arduino' in port.description or 'CH340' in port.description or 'USB Serial' in port.description):
                if port.device not in candidates:
                    candidates.append(port.device)
        for port in ports:
            if port.device != self.arduino_port and port.device not in candidates:
                candidates.append(port.device)

        for candidate in candidates:
            try:
                ser = serial.Serial(candidate, 9600, timeout=1)
                time.sleep(1.5)
                self.fill_arduino_serial = ser
                self.fill_arduino_port = candidate
                self.log_workflow(f"✓ Connected to Arduino2 on {candidate}")
                self.refresh_arduino_connection_badges()
                self.start_fill_arduino_monitor()
                return True
            except Exception:
                continue

            self.fill_arduino_serial = None
            self.fill_arduino_port = None
            self.refresh_arduino_connection_badges()
        return False

    def start_fill_arduino_monitor(self):
        """Start thread to monitor Arduino2 fill-controller responses."""
        def monitor_fill():
            while self.fill_arduino_serial and self.fill_arduino_serial.is_open:
                try:
                    if self.fill_arduino_serial.in_waiting:
                        line = self.fill_arduino_serial.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            self.process_fill_arduino_response(line)
                    time.sleep(0.1)
                except Exception:
                    break
            self.root.after(0, self.refresh_arduino_connection_badges)

        monitor_thread = threading.Thread(target=monitor_fill, daemon=True)
        monitor_thread.start()

    def refresh_arduino_connection_badges(self):
        """Refresh top-banner connection badges for Arduino1 and Arduino2."""
        if hasattr(self, 'arduino_status_label'):
            arduino1_connected = bool(
                self.arduino_serial and
                hasattr(self.arduino_serial, 'is_open') and
                self.arduino_serial.is_open
            )
            if arduino1_connected and self.arduino_port:
                self.arduino_status_label.config(text=f"✓ Arduino1: {self.arduino_port}", bg="#27ae60")
            else:
                self.arduino_status_label.config(text="⚠ Arduino1: Not Connected", bg="#e74c3c")

        if hasattr(self, 'fill_arduino_status_label'):
            arduino2_connected = bool(
                self.fill_arduino_serial and
                hasattr(self.fill_arduino_serial, 'is_open') and
                self.fill_arduino_serial.is_open
            )
            if arduino2_connected and self.fill_arduino_port:
                self.fill_arduino_status_label.config(text=f"✓ Arduino2: {self.fill_arduino_port}", bg="#27ae60")
            else:
                self.fill_arduino_status_label.config(text="⚠ Arduino2: Not Connected", bg="#e74c3c")

    def process_fill_arduino_response(self, response):
        """Process responses from Arduino2 (ultrasonic + solenoid fill controller)."""
        self.log_workflow(f"Arduino2: {response}")

        if "DISTANCE:" in response:
            try:
                distance = response.split(":")[1].replace("cm", "").strip()
                self.root.after(0, lambda: self.ultrasonic_distance_label.config(text=f"Distance: {distance} cm"))
                if _IOT_AVAILABLE:
                    web_server.update_sensor_state(distance_cm=float(distance), workflow_state=self.workflow_state)
            except Exception:
                pass

        elif "GALLON:DETECTED" in response:
            self.root.after(0, lambda: self.position_status.config(text="●", fg="#2ecc71"))
            if self.workflow_state == "MOVING":
                self.root.after(0, lambda: self.filling_status_label.config(
                    text="⏳ Gallon detected, waiting fill delay...",
                    bg="#f39c12",
                    fg="white"
                ))

        elif "FILLING:START" in response:
            if self.workflow_state in ("MOVING", "SCANNING", "CHECKING_PRESSURE"):
                self.workflow_state = "FILLING"
                self.root.after(0, self.workflow_start_filling)
            if _IOT_AVAILABLE:
                web_server.update_sensor_state(valve_open=True, workflow_state="FILLING")
            self.root.after(0, lambda: self.valve_status.config(text="●", fg="#3498db"))
            self.root.after(0, lambda: self.filling_status_label.config(
                text="💧 Filling in progress...",
                bg="#3498db",
                fg="white"
            ))

        elif "FILLING:COMPLETE" in response:
            if _IOT_AVAILABLE:
                web_server.update_sensor_state(valve_open=False, workflow_state="COMPLETE")
            self.root.after(0, lambda: self.valve_status.config(text="●", fg="#95a5a6"))
            self.root.after(0, lambda: self.water_level_status.config(text="●", fg="#2ecc71"))
            self.root.after(0, lambda: self.filling_status_label.config(
                text="✓ Filling Complete!",
                bg="#27ae60",
                fg="white"
            ))
            self.workflow_state = "COMPLETE"
            self.root.after(0, self.workflow_complete)

        elif "FILLING:STOPPED_NO_GALLON" in response:
            self.root.after(0, lambda: self.valve_status.config(text="●", fg="#95a5a6"))
            self.root.after(0, lambda: self.filling_status_label.config(
                text="⚠ Gallon removed during fill",
                bg="#e67e22",
                fg="white"
            ))

    def send_fill_arduino_command(self, command):
        """Send command to Arduino2 fill controller."""
        if not self.ensure_fill_arduino_connected():
            self.log_workflow(f"⚠ Arduino2 not connected (skipped command: {command})")
            return False

        try:
            self.fill_arduino_serial.write(f"{command}\n".encode())
            self.fill_arduino_serial.flush()
            return True
        except Exception as e:
            self.log_workflow(f"⚠ Arduino2 send error ({command}): {e}")
            return False
    
    def send_arduino_command(self, command):
        """Send command to Arduino1"""
        if self.arduino_firmware_unsupported:
            self.log_workflow(f"⚠ Command blocked ({command}): unsupported Arduino1 firmware")
            return False

        if self.arduino_serial and self.arduino_serial.is_open:
            try:
                self.arduino_serial.write(f"{command}\n".encode())
                self.arduino_serial.flush()
                return True
            except Exception as e:
                self.log_workflow(f"❌ Send error: {e}")
                return False
        return False
    
    def process_arduino_response(self, response):
        """Process responses from Arduino"""
        self.log_workflow(f"Arduino1: {response}")

        upper = response.upper()
        xtl_markers = (
            "XTL ACTUATOR READY",
            "STROKE:",
            "EXTENDING...",
            "RETRACTING..."
        )
        if any(marker in upper for marker in xtl_markers):
            self.arduino_firmware_unsupported = True

            # One-time safety stop request if firmware supports it.
            if self.arduino_serial and self.arduino_serial.is_open and "EXTENDING" in upper:
                try:
                    self.arduino_serial.write(b"STOP\n")
                    self.arduino_serial.flush()
                except Exception:
                    pass

            if not self.arduino_firmware_warned:
                self.arduino_firmware_warned = True
                self.log_workflow("⚠ Unsupported Arduino1 firmware detected. Upload automated_refill_system.ino.")
                self.root.after(0, lambda: self.arduino_status_label.config(
                    text="⚠ Arduino1 Firmware",
                    bg="#e74c3c"
                ))
            return
        
        # Update UI based on responses
        if "PRESSURE:" in response:
            try:
                match = re.search(r'[-+]?\d*\.?\d+', response)
                if not match:
                    raise ValueError("No pressure number found")
                pressure = float(match.group(0))
                self.root.after(0, lambda: self.pressure_value_label.config(text=f"Pressure: {pressure:.1f}"))
                if _IOT_AVAILABLE:
                    web_server.update_sensor_state(pressure_psi=pressure, workflow_state=self.workflow_state)
            except:
                pass
        
        elif "DISTANCE:" in response:
            try:
                distance = response.split(":")[1].replace("cm", "").strip()
                self.root.after(0, lambda: self.ultrasonic_distance_label.config(text=f"Distance: {distance} cm"))
                if _IOT_AVAILABLE:
                    web_server.update_sensor_state(distance_cm=float(distance), workflow_state=self.workflow_state)
            except:
                pass
        
        elif "LEAK:DETECTED" in response:
            if _IOT_AVAILABLE:
                web_server.update_sensor_state(leak_detected=True, workflow_state="CHECKING_PRESSURE")
            self.root.after(0, lambda: self.pressure_status_label.config(
                text="❌ LEAK DETECTED!",
                bg="#e74c3c",
                fg="white"
            ))
            if self.arduino_serial and self.arduino_serial.is_open:
                self.send_arduino_command("RAISE")
                self.log_workflow("⬆ Actuator raised after leak check")
            self.send_fill_arduino_command("DISABLE")
            self.root.after(0, lambda: self.enable_manual_defect_decision(
                "❌ Leak detected. Confirm defect manually to trigger actuator."
            ))
        
        elif "LEAK:OK" in response:
            if _IOT_AVAILABLE:
                web_server.update_sensor_state(leak_detected=False, workflow_state=self.workflow_state)
            self.root.after(0, lambda: self.pressure_status_label.config(
                text="✓ No Leak - Pressure OK",
                bg="#27ae60",
                fg="white"
            ))
            if self.arduino_serial and self.arduino_serial.is_open:
                self.send_arduino_command("RAISE")
                self.log_workflow("⬆ Actuator raised after pressure OK")
            self.send_fill_arduino_command("ENABLE")
            if self.workflow_state == "CHECKING_PRESSURE":
                self.workflow_state = "MOVING"
                self.root.after(0, self.workflow_move_to_fill)

        elif "CONVEYOR:MOVING" in response:
            if _IOT_AVAILABLE:
                web_server.update_sensor_state(conveyor_running=True, workflow_state=self.workflow_state)
            self.root.after(0, lambda: self.conveyor_status.config(text="●", fg="#2ecc71"))
        
        elif "CONVEYOR:STOPPED" in response:
            if _IOT_AVAILABLE:
                web_server.update_sensor_state(conveyor_running=False, workflow_state=self.workflow_state)
            self.root.after(0, lambda: self.conveyor_status.config(text="●", fg="#95a5a6"))
        
        elif "GALLON:DETECTED" in response:
            self.root.after(0, lambda: self.position_status.config(text="●", fg="#2ecc71"))
            if self.workflow_state == "MOVING":
                self.root.after(0, lambda: self.filling_status_label.config(
                    text="⏳ Gallon detected, waiting fill delay...",
                    bg="#f39c12",
                    fg="white"
                ))
        
        elif "FILLING:START" in response:
            if self.workflow_state == "MOVING":
                self.workflow_state = "FILLING"
                self.root.after(0, self.workflow_start_filling)
            if _IOT_AVAILABLE:
                web_server.update_sensor_state(valve_open=True, workflow_state="FILLING")
            self.root.after(0, lambda: self.valve_status.config(text="●", fg="#3498db"))
            self.root.after(0, lambda: self.filling_status_label.config(
                text="💧 Filling in progress...",
                bg="#3498db",
                fg="white"
            ))
        
        elif "FILLING:COMPLETE" in response:
            if _IOT_AVAILABLE:
                web_server.update_sensor_state(valve_open=False, workflow_state="COMPLETE")
            self.root.after(0, lambda: self.valve_status.config(text="●", fg="#95a5a6"))
            self.root.after(0, lambda: self.water_level_status.config(text="●", fg="#2ecc71"))
            self.root.after(0, lambda: self.filling_status_label.config(
                text="✓ Filling Complete!",
                bg="#27ae60",
                fg="white"
            ))
            self.workflow_state = "COMPLETE"
            self.root.after(0, self.workflow_complete)
        
        elif "CYCLE:COMPLETE" in response:
            self.root.after(0, self.workflow_complete)

        elif "REJECT:START" in response:
            if _IOT_AVAILABLE:
                web_server.update_sensor_state(valve_open=True, workflow_state="CHECKING_DEFECT")
            self.root.after(0, lambda: self.valve_status.config(text="●", fg="#e67e22"))

        elif "REJECT:DONE" in response:
            if _IOT_AVAILABLE:
                web_server.update_sensor_state(valve_open=False, workflow_state="CHECKING_DEFECT")
            self.root.after(0, lambda: self.valve_status.config(text="●", fg="#95a5a6"))

    def log_workflow(self, message):
        """Add message to workflow log"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            self.workflow_log.config(state=tk.NORMAL)
            self.workflow_log.insert(tk.END, f"[{timestamp}] {message}\n")
            self.workflow_log.see(tk.END)
            self.workflow_log.config(state=tk.DISABLED)
        except:
            pass
    
    def start_automated_workflow(self):
        """Start the automated workflow"""
        if self.arduino_firmware_unsupported:
            messagebox.showerror(
                "Unsupported Firmware",
                "Detected XTL actuator firmware on Arduino.\n"
                "Upload automated_refill_system.ino before starting workflow."
            )
            return

        if not self.arduino_serial:
            self.log_workflow("⚠ Arduino not connected - running with manual pressure decision")
        
        self.workflow_running = True
        self.workflow_state = "SCANNING"
        
        self.start_workflow_btn.config(state=tk.DISABLED)
        self.stop_workflow_btn.config(state=tk.NORMAL)
        
        self.log_workflow("=" * 50)
        self.log_workflow("🤖 AUTOMATED WORKFLOW STARTED")
        self.log_workflow("=" * 50)
        
        # Focus on QR input
        self.auto_qr_input.focus()
        self.qr_status_label.config(text="👉 Scan QR code now", fg="#e67e22")
    
    def stop_automated_workflow(self):
        """Stop the automated workflow"""
        self.workflow_running = False
        self.workflow_state = "IDLE"
        
        # Send stop command to Arduino
        if self.arduino_serial:
            self.send_arduino_command("STOP")
        self.send_fill_arduino_command("DISABLE")
        
        self.start_workflow_btn.config(state=tk.NORMAL)
        self.stop_workflow_btn.config(state=tk.DISABLED)
        
        self.log_workflow("⏹ Workflow stopped")
    
    def reset_workflow(self):
        """Reset workflow to initial state"""
        if self._qr_scan_after_id is not None:
            self.root.after_cancel(self._qr_scan_after_id)
            self._qr_scan_after_id = None

        self.workflow_state = "IDLE"
        self.current_gallon_id = None
        self.workflow_running = False
        self.manual_defect_fallback = False
        
        # Reset UI
        self.auto_qr_input.delete(0, tk.END)
        self.qr_status_label.config(text="Waiting for scan...", fg="gray")
        self.defect_status_label.config(text="")
        self.pressure_status_label.config(text="Waiting...", bg="#ecf0f1", fg="black")
        self.pressure_value_label.config(text="Pressure: --")
        self.filling_status_label.config(text="Waiting...", bg="#ecf0f1", fg="black")
        self.ultrasonic_distance_label.config(text="Distance: -- cm")
        
        self.defect_btn.config(state=tk.DISABLED)
        self.no_defect_btn.config(state=tk.DISABLED)
        
        # Reset status indicators
        self.conveyor_status.config(text="●", fg="gray")
        self.position_status.config(text="●", fg="gray")
        self.valve_status.config(text="●", fg="gray")
        self.water_level_status.config(text="●", fg="gray")
        
        self.start_workflow_btn.config(state=tk.NORMAL)
        self.stop_workflow_btn.config(state=tk.DISABLED)
        
        # Send reset to Arduino
        if self.arduino_serial:
            self.send_arduino_command("RESET")
        self.send_fill_arduino_command("DISABLE")
        
        self.log_workflow("🔄 Workflow reset")
    
    def schedule_workflow_scan(self, _event=None):
        """Schedule QR processing after scanner input stabilizes."""
        if self.workflow_state not in ("SCANNING", "IDLE"):
            return

        if self._qr_scan_after_id is not None:
            self.root.after_cancel(self._qr_scan_after_id)

        self._qr_scan_after_id = self.root.after(120, self.workflow_scan_qr)

    def workflow_scan_qr(self, force=False):
        """Handle QR code scan in workflow"""
        if self._qr_scan_after_id is not None:
            self.root.after_cancel(self._qr_scan_after_id)
            self._qr_scan_after_id = None
        
        qr_data = self.auto_qr_input.get().strip()
        if not qr_data:
            return

        # Allow scanner input to kick off workflow automatically.
        if self.workflow_state == "IDLE":
            self.workflow_running = True
            self.workflow_state = "SCANNING"
            self.start_workflow_btn.config(state=tk.DISABLED)
            self.stop_workflow_btn.config(state=tk.NORMAL)
            self.log_workflow("▶ Workflow auto-started from QR scan")

        if self.workflow_state != "SCANNING":
            return

        # In auto mode, avoid parsing too early while scanner is still typing.
        if not force:
            has_inventory_field = "INVENTORY_ID:" in qr_data.upper()
            has_id_pattern = re.search(r'WG-\d{4}', qr_data) is not None
            if not (has_inventory_field or has_id_pattern):
                self._qr_scan_after_id = self.root.after(120, self.workflow_scan_qr)
                return
        
        # Process QR code
        inventory_id = self.extract_inventory_id(qr_data)
        
        if inventory_id:
            self.current_gallon_id = inventory_id
            self.manual_defect_fallback = False
            self.log_workflow(f"✓ Scanned: {inventory_id}")
            
            self.qr_status_label.config(
                text=f"✓ Scanned: {inventory_id}",
                fg="#27ae60"
            )
            self.auto_qr_input.delete(0, tk.END)
            
            # Lower actuator then wait 5 s before pressure check
            self.workflow_state = "CHECKING_PRESSURE"
            self.defect_btn.config(state=tk.DISABLED)
            self.no_defect_btn.config(state=tk.DISABLED)
            self.defect_status_label.config(
                text="⏳ Running automatic pressure check...",
                fg="#e67e22"
            )
            if self.arduino_serial and self.arduino_serial.is_open:
                self.send_arduino_command("LOWER")
                self.log_workflow("⬇ Actuator lowering...")
            self._start_pressure_check_countdown(5)
        else:
            self.log_workflow(f"❌ Invalid QR code: {qr_data}")
            self.qr_status_label.config(
                text="❌ Invalid QR code. Scan again.",
                fg="#e74c3c"
            )
            self.auto_qr_input.delete(0, tk.END)
    
    def workflow_defect_check(self, has_defect):
        """Handle manual defect check"""
        if self.workflow_state != "CHECKING_DEFECT":
            return
        
        self.defect_btn.config(state=tk.DISABLED)
        self.no_defect_btn.config(state=tk.DISABLED)
        
        if has_defect:
            self.manual_defect_fallback = False
            # Mark as defective and activate reject actuator (if connected)
            self.log_workflow(f"❌ Defect found on {self.current_gallon_id}")
            success, message = self.db.add_defect(self.current_gallon_id)
            if not success:
                self.log_workflow(f"⚠ Could not save defect: {message}")

            reject_triggered = False
            if self.arduino_serial and self.arduino_serial.is_open:
                reject_triggered = self.send_arduino_command("REJECT")
                if reject_triggered:
                    self.log_workflow("↪ Reject actuator opened to push gallon outside conveyor")
                else:
                    self.log_workflow("⚠ Failed to send REJECT command to Arduino")
            else:
                self.log_workflow("⚠ Arduino not connected - reject actuator not triggered")
            
            self.defect_status_label.config(
                text="❌ Defect reported. Gallon rejected.",
                fg="#e74c3c"
            )
            
            messagebox.showwarning(
                "Defect Detected",
                f"Gallon {self.current_gallon_id} marked as defective.\n"
                + ("Reject actuator triggered to push gallon outside conveyor."
                   if reject_triggered else
                   "Please remove from line manually.")
            )
            
            # Reset for next gallon
            self.reset_workflow()
        else:
            # Manual fallback decision when automatic pressure check is unavailable
            if self.manual_defect_fallback:
                self.manual_defect_fallback = False
                self.log_workflow(f"✓ Manual decision: no defect on {self.current_gallon_id}")
                self.defect_status_label.config(
                    text="✓ Manual check passed",
                    fg="#27ae60"
                )
                self.pressure_status_label.config(
                    text="✓ Manual decision accepted",
                    bg="#27ae60",
                    fg="white"
                )
                self.send_fill_arduino_command("ENABLE")
                self.log_workflow("✓ Arduino2 enabled after manual no-defect decision")
                self.workflow_state = "MOVING"
                self.workflow_move_to_fill()
            else:
                # Backward-compatible path
                self.log_workflow(f"✓ No defect on {self.current_gallon_id}")
                self.defect_status_label.config(
                    text="✓ No defect detected",
                    fg="#27ae60"
                )
                self.send_fill_arduino_command("ENABLE")
                self.log_workflow("✓ Arduino2 enabled after no-defect decision")
                self.workflow_state = "CHECKING_PRESSURE"
                self.workflow_check_pressure()

    def enable_manual_defect_decision(self, reason):
        """Fallback path when automatic pressure check is not available."""
        if self.workflow_state not in ("CHECKING_PRESSURE", "SCANNING"):
            return

        self.manual_defect_fallback = True
        self.workflow_state = "CHECKING_DEFECT"
        self.log_workflow(reason)

        self.pressure_status_label.config(
            text="⚠ Pressure check unavailable",
            bg="#e67e22",
            fg="white"
        )
        self.defect_status_label.config(
            text="⚠ Choose manually: DEFECT FOUND or NO DEFECT",
            fg="#e67e22"
        )
        self.defect_btn.config(state=tk.NORMAL)
        self.no_defect_btn.config(state=tk.NORMAL)
    
    def _start_pressure_check_countdown(self, seconds_left):
        """Countdown after actuator lowered before starting pressure check."""
        if self.workflow_state != "CHECKING_PRESSURE":
            return
        if seconds_left > 0:
            self.pressure_status_label.config(
                text=f"⏳ Actuator lowering... {seconds_left}s",
                bg="#8e44ad",
                fg="white"
            )
            self.root.after(1000, lambda: self._start_pressure_check_countdown(seconds_left - 1))
        else:
            self.workflow_check_pressure()

    def workflow_check_pressure(self):
        """Check pressure/leak"""
        self.log_workflow("Testing pressure...")
        self.pressure_status_label.config(
            text="⏳ Testing pressure...",
            bg="#f39c12",
            fg="white"
        )

        if not self.arduino_serial or not self.arduino_serial.is_open:
            # No Arduino — fallback to manual defect decision
            self.enable_manual_defect_decision("⚠ No Arduino. Manual defect decision required.")
            return

        # Send STATUS command; Arduino will respond with LEAK:OK or LEAK:DETECTED
        threading.Thread(target=self._pressure_check_thread, daemon=True).start()

    def _show_manual_pressure_dialog(self):
        """Compatibility wrapper for old calls."""
        self.enable_manual_defect_decision("⚠ Manual pressure dialog replaced by defect decision fallback")

    def _pressure_check_thread(self):
        """Background thread: send STATUS, wait for Arduino pressure test result"""
        if not self.send_arduino_command("STATUS"):
            self.root.after(0, lambda: self.enable_manual_defect_decision(
                "⚠ Failed to request pressure status. Manual defect decision required."
            ))
            return

        # Arduino STATUS pressure test now runs for ~15 seconds.
        deadline = time.time() + 22
        while time.time() < deadline:
            time.sleep(0.2)
            # process_arduino_response() handles state transitions;
            # if LEAK:OK or LEAK:DETECTED arrive we're done
            if self.workflow_state != "CHECKING_PRESSURE":
                return

        # Timeout — Arduino didn't respond in time
        self.root.after(0, self._pressure_timeout)

    def _pressure_timeout(self):
        """Called when Arduino doesn't reply to pressure check in time"""
        if self.workflow_state != "CHECKING_PRESSURE":
            return  # Already resolved
        self.enable_manual_defect_decision("⚠ Pressure check timed out — manual defect decision required")

    def workflow_move_to_fill(self):
        """Move gallon to filling station"""
        self.log_workflow("Moving to fill station...")
        self.filling_status_label.config(
            text="⏳ Moving to fill station...",
            bg="#f39c12",
            fg="white"
        )
        
        # Arduino automatically moves conveyor and detects position
        # When ultrasonic detects gallon, it will trigger filling
    
    def workflow_start_filling(self):
        """Start filling process"""
        self.log_workflow("Starting fill process...")
        # Arduino automatically opens valve and monitors water level
    
    def workflow_complete(self):
        """Complete workflow cycle"""
        if self.current_gallon_id:
            # Update refill count
            self.db.increment_refills(self.current_gallon_id)
            self.log_workflow(f"✓ Gallon {self.current_gallon_id} refilled successfully!")
            
            messagebox.showinfo(
                "Success",
                f"Gallon {self.current_gallon_id} refilled!\n\nReady for next gallon."
            )
        
        # Reset for next gallon
        self.reset_workflow()
        
        # Refresh inventory
        self.refresh_inventory_list()
        self.update_statistics()
    
    def on_closing(self):
        """Handle application closing"""
        # Close Arduino connection
        if self.arduino_serial and self.arduino_serial.is_open:
            try:
                self.send_arduino_command("STOP")
                time.sleep(0.5)
                self.arduino_serial.close()
            except:
                pass

        if self.fill_arduino_serial and self.fill_arduino_serial.is_open:
            try:
                self.send_fill_arduino_command("DISABLE")
                time.sleep(0.2)
                self.fill_arduino_serial.close()
            except:
                pass
        
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
