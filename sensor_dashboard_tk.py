import os
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import colors as mcolors
from dateutil import tz
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

class SensorGrapher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sensor Data Grapher (CSV/TXT)")

        # Get screen dimensions for adaptive sizing
        # Small delay to ensure window is created before getting screen info
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate window size: ~90% of screen, capped at reasonable maximums
        window_width = min(int(screen_width * 0.9), 1920)
        window_height = min(int(screen_height * 0.9), 1080)

        # Center the window on screen
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2

        self.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

        # Set minimum window size based on screen (scale with resolution)
        min_width = max(min(int(screen_width * 0.6), 1400), 900)
        min_height = max(min(int(screen_height * 0.55), 800), 550)
        self.minsize(min_width, min_height)

        # Store screen info for use in dialogs and other components
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.window_width = window_width
        self.window_height = window_height

        print(f"[Window Init] Screen: {screen_width}x{screen_height}px")
        print(f"[Window Init] Window: {window_width}x{window_height}px at ({position_x}, {position_y})")
        print(f"[Window Init] Minimum: {min_width}x{min_height}px")
        
        # Make window resizable
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        self.df = None
        self.time_col = None
        self.all_columns = []  # Store all available columns
        self.left_selected = set()  # Track selected items
        self.right_selected = set()  # Track selected items
        self.column_display_map = {}  # Map display names to actual column names
        self.column_to_display = {}  # Reverse map: actual column names to display names
        
        # Store custom line properties for each series (keyed by actual column name)
        self.series_properties = {}  # {column_name: {'color': str, 'linestyle': str, 'linewidth': float, 'marker': str, 'markersize': float}}

        # Keep references to last-plotted matplotlib Line2D per axis and series
        self.last_series_lines = {"left": {}, "right": {}}

        # Time display timezone (12-hour Pacific Time)
        self.display_tz_name = 'US/Pacific'
        self.display_tz = tz.gettz(self.display_tz_name)

        # Watermark (loaded once)
        self.watermark_image = None  # numpy array RGBA
        self.watermark_artist = None
        self._load_watermark_image()
        
        # Sensor descriptions dictionary (middle numbers removed for matching)
        self.sensor_descriptions = {
            'AT-3007': 'DOWNSTREAM CO2 PPM',
            'AT-3008': 'DOWNSTREAM H2O PPT',
            'AT-3003': 'UPSTREAM CO2 PPM',
            'AT-3004': 'UPSTREAM H2O PPT',
            'AT-5002': 'PRODUCT DEW POINT',
            'AT-1002': 'GAS DELIVERY DEW POINT',
            'AT-1206': 'AIR HUMIDIFIER EXHAUST DEW POINT',
            'AT-2309': 'DEW POINT TRANSMITTER EXHAUST DEW POINT',
            'AT-5005': 'PRODUCT CO2 CONCENTRATION',
            'FT-1001': 'DRY AIR',
            'FT-1003': 'HUMID AIR',
            'FT-2303': 'NITROGEN',
            'FT-5003': 'PRODUCT FLOW TRANSMITTER',
            'PT-1102': 'AIR SUPPLY',
            'PT-2204': 'STEAM VESSEL PRESSURE',
            'TT-1202': 'AIR HUMIDIFIER LIQUID',
            'TT-1302': 'GAS DELIVERY TEMPERATURE',
            'TT-3001': 'GAS ENTRANCE',
            'TT-3101': 'CONTACTOR FRONT',
            'TT-3201': 'HOUSING FRONT',
            'TT-3102': 'CONTACTOR CENTER',
            'TT-3202': 'HOUSING REAR',
            'TT-3103': 'CONTACTOR EXHAUST',
            'TT-3002': 'GAS EXHAUST',
            'TT-2314': 'N2 HEATED RECIRC',
            'TT-2307': 'N2 HUMIDIFIER LIQ',
            'TT-4106': 'RECIRCULATING CHILLER',
            'TT-5001': 'PRODUCT TEMPERATURE',
            'TT-2203': 'STEAM VESSEL TEMPERATURE',
            'TT-1205': 'AIR HUMIDIFIER EXHAUST',
            'TT-2308': 'N2 HUMIDIFER EXHAUST',
            'TT-1010': 'HEAT TRACE ZONE 1 TEMPERATURE',
            'TT-3210': 'HEAT TRACE ZONE 2 TEMPERATURE',
            'FC-1002': 'DRY AIR',
            'FC-1004': 'HUMID AIR',
            'FC-2304': 'NITROGEN',
            'IP-2211': 'STEAM CONTROL VALVE I/P',
            'TC-1303': 'GAS DELIVERY TEMPERATURE CONTROL',
            'HS-3005': 'DOWNSTREAM ANALYSIS PUMP',
            'HS-3001': 'UPSTREAM ANALYSIS PUMP',
            'HS-5004': 'PRODUCT ANALYSIS PUMP',
            'HS-1010': 'ON/OFF CONTROL HEAT TRACE ZONE 1',
            'HS-3210': 'ON/OFF CONTROL HEAT TRACE ZONE 2',
            'XV-2306': 'HUMID N2 VALVE',
            'XV-2202': 'STEAM INLET TO SYSTEM',
            'XV-2305': 'DRY N2 BYPASS',
            'XV-1004': 'CONTACTOR INLET ISOLATION',
            'XV-1003': 'AIR DELIVERY ANALYSIS VALVE',
            'XV-4004': 'AIR EXHAUST ANALYSIS VALVE',
            'XV-4003': 'SEPARATOR BACKFILL AND COOL N2 ANALYSIS',
            'XV-4001': 'AIR EXHAUST',
            'XV-4002': 'COOLING ISOLATION',
            'XV-4103': 'SEPARATOR DRAIN',
            'CR-1301A': 'W1301A CONTROLLER - GAS HEATER CONTROL',
            'CR-1301B': 'W1301B CONTROLLER - GAS HEATER CONTROL',
            'CR-1204': 'HEATED RECIRCULATOR SHUTOFF',
            'CR-1214': 'HEATED RECIRCULATOR SHUTOFF',
            'CR-4201': 'VACUUM PUMP ON/OFF CONTROL',
            'CR-4104': 'CHILLER SHUTOFF',
            'TC-1203': 'AIR HEATED RECIRC',
            'TC-2313': 'N2 HEATED RECIRC',
            'TC-4105': 'RECIRCULATING CHILLER',
            'TC-1010': 'HEAT TRACE ZONE 1 TEMPERATURE CONTROL',
            'TC-3210': 'HEAT TRACE ZONE 2 TEMPERATURE CONTROL',
            'TT-1204': 'AIR HEATED RECIRC',
            'TT-1005': 'AMBIENT AIR TEMPERATURE',
            'HTR-1301A': 'INLINE HEATER 1',
            'HTR-1301B': 'INLINE HEATER 2',
            'HTR-1204': 'RECIRCULATING HEATER AIR',
            'HTR-1214': 'RECIRCULATING HEATER NITROGEN',
        }

        # === Main container with grid ===
        main_container = ttk.Frame(self)
        main_container.grid(row=0, column=0, sticky="nsew")
        main_container.rowconfigure(2, weight=1)  # Graph row expands
        main_container.columnconfigure(0, weight=1)

        # Adaptive padding based on screen size
        base_padding = 8 if screen_width >= 1600 else 6 if screen_width >= 1200 else 4
        calc_padding = max(base_padding//2, 3)  # Secondary padding for internal elements

        # === Top controls ===
        top = ttk.Frame(main_container)
        top.grid(row=0, column=0, sticky="ew", padx=base_padding, pady=max(base_padding//2, 4))
        ttk.Button(top, text="Open Data File...", command=self.open_csv).pack(side=tk.LEFT)
        ttk.Button(top, text="Export PNG", command=lambda: self.export_graph('png')).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Export JPEG", command=lambda: self.export_graph('jpeg')).pack(side=tk.LEFT, padx=5)
        self.status = tk.StringVar(value="No file loaded")
        ttk.Label(top, textvariable=self.status).pack(side=tk.LEFT, padx=10)

        # === Scrollable controls area ===
        controls_canvas_frame = ttk.Frame(main_container)
        controls_canvas_frame.grid(row=1, column=0, sticky="ew", padx=base_padding, pady=max(base_padding//2, 2))
        controls_canvas_frame.columnconfigure(0, weight=1)
        
        # Canvas with scrollbar for horizontal scrolling if needed
        # Adaptive height: ~25% of window height, bounded between 200-360px
        controls_height = max(min(int(window_height * 0.25), 360), 200)
        print(f"[Controls] Canvas height: {controls_height}px (~25% of {window_height}px)")
        self.controls_canvas = tk.Canvas(controls_canvas_frame, height=controls_height, highlightthickness=0)
        scrollbar = ttk.Scrollbar(controls_canvas_frame, orient="horizontal", command=self.controls_canvas.xview)
        self.controls_canvas.configure(xscrollcommand=scrollbar.set)
        
        self.controls_canvas.grid(row=0, column=0, sticky="ew")
        scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Frame inside canvas for all controls
        mid = ttk.Frame(self.controls_canvas)
        self.controls_canvas_window = self.controls_canvas.create_window((0, 0), window=mid, anchor="nw")
        
        # Update scrollregion when frame size changes
        mid.bind("<Configure>", lambda e: self.controls_canvas.configure(scrollregion=self.controls_canvas.bbox("all")))
        
        # Bind canvas resize to update window width
        self.controls_canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Enable mouse wheel scrolling (horizontal)
        self.controls_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.controls_canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        # For Linux
        self.controls_canvas.bind("<Button-4>", lambda e: self.controls_canvas.xview_scroll(-1, "units"))
        self.controls_canvas.bind("<Button-5>", lambda e: self.controls_canvas.xview_scroll(1, "units"))

        sel_frame = ttk.LabelFrame(mid, text="Series Selection"); sel_frame.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2, fill=tk.Y)
        
        # Left axis with filter
        ttk.Label(sel_frame, text="Left Y-axis").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        # Calculate adaptive widths based on screen size
        listbox_width = max(min(int(screen_width / 25), 50), 35)
        entry_width = listbox_width
        self.left_filter = ttk.Entry(sel_frame, width=entry_width)
        self.left_filter.grid(row=1, column=0, padx=4, pady=2)
        self.left_filter.insert(0, "Filter...")
        self.left_filter.bind("<FocusIn>", lambda e: self.on_filter_focus_in(self.left_filter))
        self.left_filter.bind("<FocusOut>", lambda e: self.on_filter_focus_out(self.left_filter))
        self.left_filter.bind("<KeyRelease>", lambda e: self.filter_listbox("left"))
        
        # Left axis select/deselect buttons
        left_btn_frame = ttk.Frame(sel_frame)
        left_btn_frame.grid(row=2, column=0, sticky="w", padx=4, pady=2)
        ttk.Button(left_btn_frame, text="Select All", command=lambda: self.select_all("left"), width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_btn_frame, text="Deselect All", command=lambda: self.deselect_all("left"), width=12).pack(side=tk.LEFT, padx=2)
        ttk.Label(left_btn_frame, text="(Ctrl+Click, Shift+Click)", font=("TkDefaultFont", 7), foreground="gray").pack(side=tk.LEFT, padx=4)
        
        self.left_list = tk.Listbox(sel_frame, selectmode=tk.EXTENDED, width=listbox_width, height=10, exportselection=False)
        self.left_list.grid(row=3, column=0, padx=4, pady=2)
        
        # Right axis with filter
        ttk.Label(sel_frame, text="Right Y-axis").grid(row=0, column=1, sticky="w", padx=4, pady=2)
        self.right_filter = ttk.Entry(sel_frame, width=entry_width)
        self.right_filter.grid(row=1, column=1, padx=4, pady=2)
        self.right_filter.insert(0, "Filter...")
        self.right_filter.bind("<FocusIn>", lambda e: self.on_filter_focus_in(self.right_filter))
        self.right_filter.bind("<FocusOut>", lambda e: self.on_filter_focus_out(self.right_filter))
        self.right_filter.bind("<KeyRelease>", lambda e: self.filter_listbox("right"))
        
        # Right axis select/deselect buttons
        right_btn_frame = ttk.Frame(sel_frame)
        right_btn_frame.grid(row=2, column=1, sticky="w", padx=4, pady=2)
        ttk.Button(right_btn_frame, text="Select All", command=lambda: self.select_all("right"), width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(right_btn_frame, text="Deselect All", command=lambda: self.deselect_all("right"), width=12).pack(side=tk.LEFT, padx=2)
        ttk.Label(right_btn_frame, text="(Ctrl+Click, Shift+Click)", font=("TkDefaultFont", 7), foreground="gray").pack(side=tk.LEFT, padx=4)
        
        self.right_list = tk.Listbox(sel_frame, selectmode=tk.EXTENDED, width=listbox_width, height=10, exportselection=False)
        self.right_list.grid(row=3, column=1, padx=4, pady=2)

        opt_frame = ttk.LabelFrame(mid, text="Plot Options"); opt_frame.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2, fill=tk.Y)
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Show grid", variable=self.grid_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        self.smooth_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_frame, text="Moving-average smoothing", variable=self.smooth_var, command=self.toggle_smooth).grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        ttk.Label(opt_frame, text="Window (samples):").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.window_entry = ttk.Entry(opt_frame, width=8); self.window_entry.insert(0, "21"); self.window_entry.grid(row=2, column=1, sticky="w", padx=4, pady=2)
        self.window_entry.state(["disabled"])
        self.watermark_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Show watermark", variable=self.watermark_var).grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        
        # Legend customization section
        legend_frame = ttk.LabelFrame(mid, text="Legend Options"); legend_frame.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2, fill=tk.Y)
        
        self.show_legend_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(legend_frame, text="Show legend", variable=self.show_legend_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        
        ttk.Label(legend_frame, text="Position:").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        self.legend_position = ttk.Combobox(legend_frame, width=15, state="readonly")
        self.legend_position['values'] = ("Upper Left", "Upper Right", "Lower Left", "Lower Right", "Best", "Outside Right", "Outside Bottom")
        self.legend_position.current(0)  # Default to "Upper Left"
        self.legend_position.grid(row=1, column=1, sticky="w", padx=4, pady=2)
        
        ttk.Label(legend_frame, text="Font size:").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.legend_fontsize = ttk.Spinbox(legend_frame, from_=4, to=20, width=8)
        self.legend_fontsize.set(8)  # Default font size
        self.legend_fontsize.grid(row=2, column=1, sticky="w", padx=4, pady=2)
        
        ttk.Label(legend_frame, text="Columns:").grid(row=3, column=0, sticky="w", padx=4, pady=2)
        self.legend_columns = ttk.Spinbox(legend_frame, from_=1, to=5, width=8)
        self.legend_columns.set(1)  # Default to single column
        self.legend_columns.grid(row=3, column=1, sticky="w", padx=4, pady=2)
        
        self.legend_framealpha_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(legend_frame, text="Semi-transparent", variable=self.legend_framealpha_var).grid(row=4, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        
        # Axis labels and title section (adaptive sizing)
        label_frame = ttk.LabelFrame(mid, text="Graph Labels"); label_frame.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2, fill=tk.Y)
        
        ttk.Label(label_frame, text="Graph Title:").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        # Adaptive entry field width
        label_entry_width = max(min(int(screen_width / 50), 25), 18)
        self.graph_title = ttk.Entry(label_frame, width=label_entry_width)
        self.graph_title.insert(0, "Sensor Time Series")
        self.graph_title.grid(row=1, column=0, padx=4, pady=2)
        
        ttk.Label(label_frame, text="Left Y-axis label:").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.left_ylabel = ttk.Entry(label_frame, width=label_entry_width)
        self.left_ylabel.insert(0, "Left axis")
        self.left_ylabel.grid(row=3, column=0, padx=4, pady=2)
        
        ttk.Label(label_frame, text="Right Y-axis label:").grid(row=4, column=0, sticky="w", padx=4, pady=2)
        self.right_ylabel = ttk.Entry(label_frame, width=label_entry_width)
        self.right_ylabel.insert(0, "Right axis")
        self.right_ylabel.grid(row=5, column=0, padx=4, pady=2)
        
        ttk.Label(label_frame, text="X-axis label:").grid(row=6, column=0, sticky="w", padx=4, pady=2)
        self.xlabel = ttk.Entry(label_frame, width=label_entry_width)
        self.xlabel.insert(0, "Time")
        self.xlabel.grid(row=7, column=0, padx=4, pady=2)

        time_frame = ttk.LabelFrame(mid, text="Time Window (optional, PST timezone)"); time_frame.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2, fill=tk.Y)
        ttk.Label(time_frame, text="Start:").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        ttk.Label(time_frame, text="End:").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        self.start_entry = ttk.Entry(time_frame, width=label_entry_width); self.start_entry.grid(row=0, column=1, padx=4, pady=2)
        self.end_entry = ttk.Entry(time_frame, width=label_entry_width); self.end_entry.grid(row=1, column=1, padx=4, pady=2)
        
        # Time selection buttons
        time_btn_frame = ttk.Frame(time_frame)
        time_btn_frame.grid(row=2, column=0, columnspan=2, padx=4, pady=6)
        self.time_select_btn = ttk.Button(time_btn_frame, text="Select Time Range", command=self.toggle_time_selection)
        self.time_select_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(time_btn_frame, text="Clear Selection", command=self.clear_time_selection).pack(side=tk.LEFT, padx=2)

        # Plot and customization buttons (adaptive padding)
        plot_customize_frame = ttk.Frame(mid)
        plot_customize_frame.pack(side=tk.LEFT, padx=max(base_padding, 6), pady=calc_padding//2)
        ttk.Button(plot_customize_frame, text="Customize Series", command=self.open_customize_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(plot_customize_frame, text="Plot", command=self.plot).pack(side=tk.LEFT, padx=2)

        # === CO2 Capture Calculation (in scrollable area) ===
        calc_frame = ttk.LabelFrame(main_container, text="CO₂ Capture Calculation (No-leak assumption: F_out = F_in)")
        calc_frame.grid(row=3, column=0, sticky="ew", padx=base_padding, pady=max(base_padding//2, 2))
        
        # Column selection for mass balance
        col_select = ttk.Frame(calc_frame); col_select.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2)
        
        ttk.Label(col_select, text="Inlet CO₂ (ppm):").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        # Adaptive combo box width for CO2 calculation
        combo_width = max(min(int(screen_width / 35), 30), 20)
        self.inlet_co2_combo = ttk.Combobox(col_select, width=combo_width, state="readonly")
        self.inlet_co2_combo.grid(row=0, column=1, padx=4, pady=2)
        
        ttk.Label(col_select, text="Outlet CO₂ (ppm):").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        self.outlet_co2_combo = ttk.Combobox(col_select, width=combo_width, state="readonly")
        self.outlet_co2_combo.grid(row=1, column=1, padx=4, pady=2)
        
        ttk.Label(col_select, text="Flow Rate (SLPM):").grid(row=2, column=0, sticky="e", padx=4, pady=2)
        self.inlet_flow_combo = ttk.Combobox(col_select, width=combo_width, state="readonly")
        self.inlet_flow_combo.grid(row=2, column=1, padx=4, pady=2)
        
        # Parameters for Vm calculation
        param_calc = ttk.Frame(calc_frame); param_calc.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2)
        
        ttk.Label(param_calc, text="Temperature (°C):").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        self.temp_entry = ttk.Entry(param_calc, width=8)
        self.temp_entry.insert(0, "25")
        self.temp_entry.grid(row=0, column=1, padx=4, pady=2)
        self.temp_entry.bind("<KeyRelease>", lambda e: self.update_vm())
        
        ttk.Label(param_calc, text="Pressure:").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        pressure_frame = ttk.Frame(param_calc)
        pressure_frame.grid(row=1, column=1, sticky="w", padx=4, pady=2)
        self.pressure_entry = ttk.Entry(pressure_frame, width=8)
        self.pressure_entry.insert(0, "1.0")
        self.pressure_entry.pack(side=tk.LEFT, padx=(0, 2))
        self.pressure_entry.bind("<KeyRelease>", lambda e: self.update_vm())
        self.pressure_unit_combo = ttk.Combobox(pressure_frame, width=5, state="readonly")
        self.pressure_unit_combo['values'] = ("atm", "psi")
        self.pressure_unit_combo.current(0)  # Default to atm
        self.pressure_unit_combo.pack(side=tk.LEFT)
        self.pressure_unit_combo.bind("<<ComboboxSelected>>", lambda e: self.update_vm())
        
        ttk.Label(param_calc, text="Compressibility (Z):").grid(row=2, column=0, sticky="e", padx=4, pady=2)
        self.z_entry = ttk.Entry(param_calc, width=8)
        self.z_entry.insert(0, "1.0")
        self.z_entry.grid(row=2, column=1, padx=4, pady=2)
        ttk.Label(param_calc, text="(1.0 for air, ideal)", font=("TkDefaultFont", 7), foreground="gray").grid(row=2, column=2, sticky="w", padx=4, pady=2)
        self.z_entry.bind("<KeyRelease>", lambda e: self.update_vm())
        
        ttk.Label(param_calc, text="Vm (L/mol):", font=("TkDefaultFont", 9, "bold")).grid(row=3, column=0, sticky="e", padx=4, pady=4)
        self.vm_display = ttk.Label(param_calc, text="24.465", font=("TkDefaultFont", 9, "bold"), foreground="darkblue")
        self.vm_display.grid(row=3, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(param_calc, text="(calculated)", font=("TkDefaultFont", 7), foreground="gray").grid(row=3, column=2, sticky="w", padx=4, pady=4)
        
        btn_frame = ttk.Frame(param_calc)
        btn_frame.grid(row=4, column=0, columnspan=3, padx=4, pady=6)
        ttk.Button(btn_frame, text="Quick Plot Sensors", command=self.quick_plot_co2_sensors).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Calculate CO₂ Captured", command=self.calculate_co2_capture).pack(side=tk.LEFT, padx=2)
        
        # Results display
        result_frame = ttk.Frame(calc_frame); result_frame.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2)
        
        self.co2_result_var = tk.StringVar(value="No calculation yet")
        result_label = ttk.Label(result_frame, textvariable=self.co2_result_var, font=("TkDefaultFont", 10, "bold"), foreground="darkgreen")
        result_label.pack(padx=4, pady=4)

        # === Figure area (expands to fill space) ===
        # Calculate figure size adaptively based on window dimensions
        # Figure dimensions are approximate - the canvas will scale with window resize
        fig_width_inches = max(window_width / 150, 8)
        fig_height_inches = max(window_height / 220, 4)

        # Use higher DPI for high-resolution screens
        dpi = 120 if screen_width >= 1920 else 100

        print(f"[Figure] Size: {fig_width_inches:.1f}x{fig_height_inches:.1f} inches @ {dpi} DPI")

        self.fig = plt.Figure(figsize=(fig_width_inches, fig_height_inches), dpi=dpi)
        self.ax_left = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_container)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=2, column=0, sticky="nsew", padx=base_padding, pady=base_padding)
        
        # Connect mouse click event for time selection
        self.canvas.mpl_connect('button_press_event', self.on_graph_click)
        self.time_selection_mode = False
        self.selected_time_start = None
        self.selected_time_end = None
        self.time_selection_lines = []
        
        # Connect mouse motion event for hover tooltips
        self.canvas.mpl_connect('motion_notify_event', self.on_graph_hover)
        self.hover_annotation = None
        self.hover_vline = None
        self.hover_hline = None
        self.hover_points = []  # Store scatter points for each hovered data point

        # Initial adaptive control sizing
        try:
            self._update_adaptive_controls(self.window_width, self.window_height)
        except Exception:
            pass

        # Bind window resize event for responsive canvas updates
        self.bind('<Configure>', self._on_window_resize)

    def _on_canvas_configure(self, event):
        """Update the canvas window width when canvas is resized."""
        canvas_width = event.width
        self.controls_canvas.itemconfig(self.controls_canvas_window, width=canvas_width)

    def _on_window_resize(self, event):
        """Handle window resize events to maintain responsive layout."""
        # Only process resize events for the main window itself, not child widgets
        if event.widget == self:
            # Update stored window dimensions
            self.window_width = event.width
            self.window_height = event.height

            # The matplotlib canvas automatically resizes due to grid weights
            # Force a canvas redraw if we have data plotted
            if hasattr(self, 'canvas') and self.df is not None:
                try:
                    # Use draw_idle() to queue redraw without blocking
                    self.canvas.draw_idle()
                except Exception:
                    # Silently ignore drawing errors during resize
                    pass

            # Adapt control widths and controls canvas height
            try:
                self._update_adaptive_controls(self.window_width, self.window_height)
            except Exception:
                pass

    def _update_adaptive_controls(self, window_width: int, window_height: int):
        """Dynamically adjust widths/heights of top controls to fit the screen elegantly.
        Keeps everything visible by shrinking controls on smaller windows.
        """
        # Compute adaptive character widths
        listbox_width = max(min(int(window_width / 40), 46), 32)
        entry_width = listbox_width
        label_entry_width = max(min(int(window_width / 60), 22), 16)
        combo_width = max(min(int(window_width / 45), 26), 18)

        # Listboxes and filter entries
        if hasattr(self, 'left_list'):
            try:
                self.left_list.config(width=listbox_width)
                self.right_list.config(width=listbox_width)
            except Exception:
                pass
        if hasattr(self, 'left_filter'):
            try:
                self.left_filter.config(width=entry_width)
                self.right_filter.config(width=entry_width)
            except Exception:
                pass

        # Label entries
        for w_name in ['graph_title', 'left_ylabel', 'right_ylabel', 'xlabel', 'start_entry', 'end_entry']:
            w = getattr(self, w_name, None)
            if w is not None:
                try:
                    w.config(width=label_entry_width)
                except Exception:
                    pass

        # Comboboxes in CO2 calc
        for w_name in ['inlet_co2_combo', 'outlet_co2_combo', 'inlet_flow_combo']:
            w = getattr(self, w_name, None)
            if w is not None:
                try:
                    w.config(width=combo_width)
                except Exception:
                    pass

        # Controls area height ~25% of window height
        try:
            controls_height = max(min(int(window_height * 0.25), 360), 200)
            self.controls_canvas.config(height=controls_height)
        except Exception:
            pass
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling (horizontal by default)."""
        self.controls_canvas.xview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_shift_mousewheel(self, event):
        """Handle shift+mouse wheel scrolling (also horizontal)."""
        self.controls_canvas.xview_scroll(int(-1*(event.delta/120)), "units")
    
    def get_display_name(self, column_name):
        """Create a display name for a column by adding sensor description if available.
        
        Args:
            column_name: The actual column name from the CSV
            
        Returns:
            A formatted display name with description if available, otherwise the original column name
        """
        # Check if any sensor ID is in the column name
        for sensor_id, description in self.sensor_descriptions.items():
            if sensor_id.upper() in column_name.upper():
                # Format: "COLUMN_NAME - DESCRIPTION"
                display_name = f"{column_name} - {description}"
                print(f"[Sensor Description] Mapped '{column_name}' to '{display_name}'")
                return display_name
        
        # If no sensor ID found, return original name
        return column_name
    
    def get_column_from_display(self, display_name):
        """Get the actual column name from a display name.
        
        Args:
            display_name: The formatted display name shown in the listbox
            
        Returns:
            The actual column name from the CSV
        """
        return self.column_display_map.get(display_name, display_name)
    
    def toggle_smooth(self):
        if self.smooth_var.get():
            self.window_entry.state(["!disabled"])
        else:
            self.window_entry.state(["disabled"])

    def on_filter_focus_in(self, entry):
        """Clear placeholder text when filter box is focused."""
        if entry.get() == "Filter...":
            entry.delete(0, tk.END)
            entry.config(foreground="black")

    def on_filter_focus_out(self, entry):
        """Restore placeholder text if filter box is empty."""
        if not entry.get():
            entry.insert(0, "Filter...")
            entry.config(foreground="gray")

    def filter_listbox(self, side):
        """Filter the listbox based on the search text."""
        if not self.all_columns:
            return
        
        # Get the appropriate filter entry and listbox
        if side == "left":
            filter_entry = self.left_filter
            listbox = self.left_list
            selected_set = self.left_selected
        else:
            filter_entry = self.right_filter
            listbox = self.right_list
            selected_set = self.right_selected
        
        # Update selected items tracking before clearing
        for idx in listbox.curselection():
            selected_set.add(listbox.get(idx))
        
        # Get filter text
        filter_text = filter_entry.get().strip().lower()
        if filter_text == "filter...":
            filter_text = ""
        
        # Clear and repopulate listbox with filtered items
        listbox.delete(0, tk.END)
        
        matched_count = 0
        for col in self.all_columns:
            display_name = self.column_to_display.get(col, col)
            # Filter based on display name (which includes both column name and description)
            if not filter_text or filter_text in display_name.lower():
                listbox.insert(tk.END, display_name)
                matched_count += 1
                # Restore selection if this item was previously selected
                if display_name in selected_set:
                    listbox.selection_set(tk.END)
        
        # Log filtering activity
        if filter_text:
            print(f"[Filter] {side.capitalize()} axis: '{filter_text}' matched {matched_count}/{len(self.all_columns)} columns")

    def select_all(self, side):
        """Select all visible items in the listbox."""
        if side == "left":
            listbox = self.left_list
            selected_set = self.left_selected
        else:
            listbox = self.right_list
            selected_set = self.right_selected
        
        # Select all visible items
        listbox.selection_set(0, tk.END)
        
        # Update tracking set
        for i in range(listbox.size()):
            selected_set.add(listbox.get(i))
        
        print(f"[Select All] {side.capitalize()} axis: Selected {listbox.size()} visible columns")

    def deselect_all(self, side):
        """Deselect all items in the listbox."""
        if side == "left":
            listbox = self.left_list
            selected_set = self.left_selected
        else:
            listbox = self.right_list
            selected_set = self.right_selected
        
        # Get currently visible items to remove from tracking
        visible_items = [listbox.get(i) for i in range(listbox.size())]
        
        # Clear selection
        listbox.selection_clear(0, tk.END)
        
        # Remove only visible items from tracking set
        for item in visible_items:
            selected_set.discard(item)
        
        print(f"[Deselect All] {side.capitalize()} axis: Deselected {len(visible_items)} visible columns")

    def export_graph(self, fmt):
        if self.df is None:
            messagebox.showwarning("No graph", "Please plot data before exporting.")
            return
        filetypes = [(f"{fmt.upper()} files", f"*.{fmt}"), ("All files", "*.*")]
        path = filedialog.asksaveasfilename(defaultextension=f".{fmt}", filetypes=filetypes)
        if not path:
            return
        try:
            self.fig.savefig(path, format=fmt, bbox_inches='tight')
            messagebox.showinfo("Export successful", f"Graph exported as {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Export error", str(e))
    
    def open_customize_dialog(self):
        """Open dialog to customize series properties (colors, line styles, etc.)."""
        if self.df is None:
            messagebox.showwarning("No data", "Please load a data file first.")
            return
        
        # Get currently selected series from both axes
        left_cols = self.get_selected(self.left_list, "left")
        right_cols = self.get_selected(self.right_list, "right")
        all_series = left_cols + right_cols
        
        if not all_series:
            messagebox.showwarning("No series selected", "Please select at least one series to customize.")
            return
        
        print(f"[Customize] Opening dialog for {len(all_series)} series")
        
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Customize Series")
        dialog.geometry("700x600")
        dialog.transient(self)
        dialog.grab_set()
        
        # Main frame with scrollbar
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store widget references for each series
        series_widgets = {}
        
        # Line style and marker options
        linestyles = ['-', '--', '-.', ':', 'None']
        markers = ['None', 'o', 's', '^', 'v', '<', '>', 'd', 'p', '*', 'h', 'H', '+', 'x', 'D', '|', '_']
        
        # Create customization controls for each series
        for idx, col in enumerate(all_series):
            # Start with explicit custom properties if user set any previously
            props = dict(self.series_properties.get(col, {}))

            # If no explicit customization, try to read from last plotted line
            if not props:
                line = None
                if col in self.last_series_lines.get("left", {}):
                    line = self.last_series_lines["left"].get(col)
                if line is None and col in self.last_series_lines.get("right", {}):
                    line = self.last_series_lines["right"].get(col)
                if line is not None:
                    try:
                        # Extract live properties from the matplotlib Line2D
                        props = {
                            'color': line.get_color(),
                            'linestyle': line.get_linestyle() or '-',
                            'linewidth': float(line.get_linewidth()),
                            'marker': line.get_marker() if line.get_marker() not in [None, 'None'] else None,
                            'markersize': float(line.get_markersize()),
                        }
                    except Exception:
                        props = {}

            # Fallback defaults if anything missing
            current_color = props.get('color', None)
            current_linestyle = props.get('linestyle', '-')
            current_linewidth = props.get('linewidth', 1.5)
            # If marker was stored as None, show 'None' option in the combobox
            current_marker = props.get('marker') or 'None'
            current_markersize = props.get('markersize', 6)
            
            # Series frame
            series_frame = ttk.LabelFrame(scrollable_frame, text=col)
            series_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Color selection
            color_frame = ttk.Frame(series_frame)
            color_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=3)
            
            ttk.Label(color_frame, text="Color:").pack(side=tk.LEFT, padx=5)
            
            color_display = tk.Canvas(color_frame, width=40, height=20, bg=current_color if current_color else "white", relief=tk.SUNKEN, bd=1)
            color_display.pack(side=tk.LEFT, padx=5)
            
            color_var = tk.StringVar(value=current_color if current_color else "")
            
            def make_choose_color(col_name, color_var, color_display):
                def choose_color():
                    color = colorchooser.askcolor(title=f"Choose color for {col_name}")
                    if color[1]:  # color[1] is hex string
                        color_var.set(color[1])
                        color_display.config(bg=color[1])
                        print(f"[Customize] {col_name}: color set to {color[1]}")
                return choose_color
            
            ttk.Button(color_frame, text="Choose Color", 
                      command=make_choose_color(col, color_var, color_display)).pack(side=tk.LEFT, padx=5)
            
            def make_reset_color(col_name, color_var, color_display):
                def reset_color():
                    color_var.set("")
                    color_display.config(bg="white")
                    print(f"[Customize] {col_name}: color reset to default")
                return reset_color
            
            ttk.Button(color_frame, text="Auto", 
                      command=make_reset_color(col, color_var, color_display)).pack(side=tk.LEFT, padx=5)
            
            # Line style
            ttk.Label(series_frame, text="Line Style:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
            linestyle_combo = ttk.Combobox(series_frame, values=linestyles, width=10, state="readonly")
            linestyle_combo.set(current_linestyle)
            linestyle_combo.grid(row=1, column=1, sticky="w", padx=5, pady=3)
            
            # Line width
            ttk.Label(series_frame, text="Line Width:").grid(row=1, column=2, sticky="e", padx=5, pady=3)
            linewidth_spinbox = ttk.Spinbox(series_frame, from_=0.5, to=10.0, increment=0.5, width=8)
            linewidth_spinbox.set(current_linewidth)
            linewidth_spinbox.grid(row=1, column=3, sticky="w", padx=5, pady=3)
            
            # Marker style
            ttk.Label(series_frame, text="Marker:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
            marker_combo = ttk.Combobox(series_frame, values=markers, width=10, state="readonly")
            try:
                marker_combo.set(str(current_marker))
            except Exception:
                # Fallback safely if an unexpected value occurs
                marker_combo.set('None')
            marker_combo.grid(row=2, column=1, sticky="w", padx=5, pady=3)
            
            # Marker size
            ttk.Label(series_frame, text="Marker Size:").grid(row=2, column=2, sticky="e", padx=5, pady=3)
            markersize_spinbox = ttk.Spinbox(series_frame, from_=1, to=20, increment=1, width=8)
            markersize_spinbox.set(current_markersize)
            markersize_spinbox.grid(row=2, column=3, sticky="w", padx=5, pady=3)
            
            # Store widgets
            series_widgets[col] = {
                'color_var': color_var,
                'linestyle': linestyle_combo,
                'linewidth': linewidth_spinbox,
                'marker': marker_combo,
                'markersize': markersize_spinbox
            }
        
        # Button frame at bottom
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def apply_changes():
            """Apply customizations to series_properties."""
            for col, widgets in series_widgets.items():
                color = widgets['color_var'].get()
                linestyle = widgets['linestyle'].get()
                linewidth = float(widgets['linewidth'].get())
                marker = widgets['marker'].get()
                markersize = float(widgets['markersize'].get())
                
                # Store properties
                self.series_properties[col] = {
                    'color': color if color else None,
                    'linestyle': linestyle,
                    'linewidth': linewidth,
                    'marker': marker if marker != 'None' else None,
                    'markersize': markersize
                }
                
                print(f"[Customize] {col}: color={color if color else 'auto'}, "
                      f"linestyle={linestyle}, linewidth={linewidth}, "
                      f"marker={marker}, markersize={markersize}")
            
            messagebox.showinfo("Success", f"Customizations applied to {len(series_widgets)} series.\nClick 'Plot' to see changes.")
            dialog.destroy()
        
        def reset_all():
            """Reset all customizations for selected series."""
            for col in series_widgets.keys():
                if col in self.series_properties:
                    del self.series_properties[col]
            print(f"[Customize] Reset all customizations for {len(series_widgets)} series")
            messagebox.showinfo("Reset", "All customizations cleared. Click 'Plot' to see changes.")
            dialog.destroy()
        
        ttk.Button(button_frame, text="Apply", command=apply_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset All", command=reset_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Enable mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Cleanup binding when dialog closes
        def on_close():
            canvas.unbind_all("<MouseWheel>")
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_close)

    def open_csv(self):
        """Open a CSV or tab-delimited TXT file and populate the listboxes with available columns."""
        path = filedialog.askopenfilename(
            title="Select data file (CSV or TXT)",
            filetypes=[("Data files", "*.csv *.txt"), ("CSV files", "*.csv"), ("TXT files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        
        try:
            # Detect file type and use appropriate delimiter
            file_ext = os.path.splitext(path)[1].lower()
            if file_ext == '.txt':
                # Tab-delimited for .txt files
                delimiter = '\t'
                print(f"[File Load] Detected TXT file - using tab delimiter")
            else:
                # Default to comma for .csv and unknown types
                delimiter = ','
                print(f"[File Load] Using comma delimiter for {file_ext} file")
            
            self.df = pd.read_csv(path, delimiter=delimiter)
            if self.df.empty:
                messagebox.showerror("Error", "The file appears to be empty.")
                return
            
            # Detect and parse time column
            self.time_col = self.infer_time_column(self.df)
            if self.time_col is None:
                messagebox.showerror("Error", "Couldn't find a time-like column.\nInclude a column such as 'YYMMDD_HHMMSS', 'Time', or 'timestamp'.")
                return
            
            dt = self.to_datetime(self.df[self.time_col])
            if dt.notna().sum() == 0:
                messagebox.showerror("Error", f"Could not parse timestamps in column '{self.time_col}'.\nTry converting to a standard datetime format.")
                return
            
            self.df[self.time_col] = dt
            self.df = self.df.dropna(subset=[self.time_col]).sort_values(self.time_col).reset_index(drop=True)

            # Create display timezone-converted timestamp for plotting (12-hour PST)
            try:
                self.df['_plot_time'] = self.to_display_tz_series(self.df[self.time_col])
            except Exception as e:
                print(f"[Time TZ] Failed to convert to display timezone: {e}")
                self.df['_plot_time'] = self.df[self.time_col]
            
            # Get numeric columns
            num_cols = self.numeric_columns(self.df)
            if not num_cols:
                messagebox.showerror("Error", "No numeric columns detected to plot.")
                return
            
            # Store all columns and reset filters
            self.all_columns = num_cols
            self.left_selected = set()
            self.right_selected = set()
            
            # Build display name mappings
            self.column_display_map = {}  # display_name -> column_name
            self.column_to_display = {}   # column_name -> display_name
            for col in num_cols:
                display_name = self.get_display_name(col)
                self.column_display_map[display_name] = col
                self.column_to_display[col] = display_name
            
            print(f"[File Load] Found {len(num_cols)} numeric columns in {os.path.basename(path)}")
            print(f"[File Load] Columns: {', '.join(num_cols[:10])}{'...' if len(num_cols) > 10 else ''}")
            
            # Clear and reset filter boxes
            self.left_filter.delete(0, tk.END)
            self.left_filter.insert(0, "Filter...")
            self.left_filter.config(foreground="gray")
            self.right_filter.delete(0, tk.END)
            self.right_filter.insert(0, "Filter...")
            self.right_filter.config(foreground="gray")
            
            # Populate listboxes with display names
            self.left_list.delete(0, tk.END)
            self.right_list.delete(0, tk.END)
            
            for col in num_cols:
                display_name = self.column_to_display[col]
                self.left_list.insert(tk.END, display_name)
                self.right_list.insert(tk.END, display_name)
            
            # Auto-select defaults (only FT-1001, FT-1003, and FT-2303) using display names
            default_sensors = ['FT-1001', 'FT-1003', 'FT-2303']
            for i, col in enumerate(num_cols):
                display_name = self.column_to_display[col]
                # Check if column contains any of the default sensor IDs
                should_select = any(sensor_id in col.upper() for sensor_id in default_sensors)
                if should_select:
                    self.left_list.selection_set(i)
                    self.left_selected.add(display_name)
                    print(f"[File Load] Auto-selected: {display_name}")
            
            self.status.set(f"Loaded: {os.path.basename(path)} ({len(self.df)} rows, {len(num_cols)} numeric columns)")
            
            # Populate CO2 capture calculation dropdowns
            self.populate_co2_dropdowns(num_cols)
            
        except Exception as e:
            messagebox.showerror("Error loading file", f"Failed to load file:\n{str(e)}")
    
    def infer_time_column(self, df: pd.DataFrame):
        """Infer the time column from the DataFrame."""
        candidates = []
        if "YYMMDD_HHMMSS" in df.columns:
            candidates.append("YYMMDD_HHMMSS")
        for c in df.columns:
            name = c.lower()
            if ("time" in name or "date" in name or "timestamp" in name) and c not in candidates:
                candidates.append(c)
        return candidates[0] if candidates else None
    
    def to_datetime(self, series: pd.Series):
        """Convert series to datetime."""
        try:
            return pd.to_datetime(series, format="%y%m%d_%H%M%S", errors="coerce")
        except Exception:
            pass
        return pd.to_datetime(series, errors="coerce")

    def to_display_tz_series(self, series: pd.Series):
        """Convert a datetime series to the app's display timezone (PST), timezone-aware."""
        s = pd.to_datetime(series, errors='coerce')
        try:
            if getattr(s.dt, 'tz', None) is None:
                s = s.dt.tz_localize(self.display_tz)
            else:
                s = s.dt.tz_convert(self.display_tz)
        except Exception:
            # Fallback: localize naive values row-wise
            s = s.apply(lambda x: x.tz_localize(self.display_tz) if pd.notna(x) and x.tzinfo is None else (x.tz_convert(self.display_tz) if pd.notna(x) else x))
        return s

    def _load_watermark_image(self):
        """Load and cache the watermark image from PNG or SVG file.
        PNG is preferred if available.
        """
        try:
            # Try PNG first (no dependencies needed)
            png_path = os.path.join(os.path.dirname(__file__), 'OrbitalDarkPurple.png')
            if os.path.isfile(png_path):
                image = Image.open(png_path).convert('RGBA')
                self.watermark_image = image
                print(f"[Watermark] Loaded PNG watermark from {png_path}")
                return
            
            # Fall back to SVG if PNG not found
            svg_path = os.path.join(os.path.dirname(__file__), 'OrbitalDarkPurple.svg')
            if os.path.isfile(svg_path):
                try:
                    import cairosvg
                    png_bytes = cairosvg.svg2png(url=svg_path, output_width=800)
                    image = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
                    self.watermark_image = image
                    print(f"[Watermark] Loaded SVG watermark from {svg_path}")
                    return
                except Exception as e:
                    print(f"[Watermark] CairoSVG not available or failed ({e}) - watermark disabled")
                    return
            
            print(f"[Watermark] No PNG or SVG watermark file found")
        except Exception as e:
            print(f"[Watermark] Failed to load watermark: {e}")
    
    def numeric_columns(self, df: pd.DataFrame):
        """Get list of numeric columns (excluding time column)."""
        numeric_cols = []
        for c in df.columns:
            if c == self.time_col:
                continue
            col = pd.to_numeric(df[c], errors="coerce")
            if col.notna().sum() > 0:
                numeric_cols.append(c)
        return numeric_cols
    
    def split_by_units(self, cols):
        """Split columns by units - send temp columns to right axis by default."""
        left_default, right_default = [], []
        for c in cols:
            cl = c.lower()
            if "degc" in cl or "°c" in cl or "(c)" in cl or "temp" in cl or re.search(r"\btt-\d+", cl):
                right_default.append(c)
            else:
                left_default.append(c)
        return left_default, right_default
    
    def get_selected(self, listbox, side):
        """Get selected items from a listbox and update tracking.
        
        Returns the actual column names (not display names) for plotting.
        """
        # Determine which tracking set to use
        if side == "left":
            selected_set = self.left_selected
        else:
            selected_set = self.right_selected
        
        # Update tracking with current selections (as display names)
        selected_set.clear()
        indices = listbox.curselection()
        for i in indices:
            selected_set.add(listbox.get(i))
        
        # Convert display names to actual column names for plotting
        actual_columns = []
        for display_name in selected_set:
            actual_col = self.column_display_map.get(display_name, display_name)
            actual_columns.append(actual_col)
        
        return actual_columns
    
    def update_vm(self):
        """Calculate molar volume (Vm) based on temperature, pressure, and compressibility.
        
        Formula: Vm,real = Z × R × T / P
        Where:
        - R = 0.082057 L·atm·mol⁻¹·K⁻¹ (gas constant)
        - T = temperature in Kelvin
        - P = pressure in atm (absolute)
        - Z = compressibility factor (1.0 for ideal gas)
        """
        try:
            # Get input values
            temp_c = float(self.temp_entry.get())
            pressure_value = float(self.pressure_entry.get())
            pressure_unit = self.pressure_unit_combo.get()
            z_factor = float(self.z_entry.get())
            
            # Convert pressure to atm if needed
            if pressure_unit == "psi":
                pressure_atm = pressure_value / 14.696  # 1 atm = 14.696 psi
            else:
                pressure_atm = pressure_value
            
            # Gas constant
            R = 0.082057  # L·atm·mol⁻¹·K⁻¹
            
            # Convert temperature to Kelvin
            temp_k = temp_c + 273.15
            
            # Calculate Vm using real gas equation
            vm_real = (z_factor * R * temp_k) / pressure_atm
            
            # Update display
            self.vm_display.config(text=f"{vm_real:.4f}")
            
            # Log calculation
            print(f"[Vm Calc] T={temp_c}°C ({temp_k}K), P={pressure_value} {pressure_unit} ({pressure_atm:.4f} atm), Z={z_factor} → Vm={vm_real:.4f} L/mol")
            
        except ValueError:
            # If inputs are invalid, show error in display
            self.vm_display.config(text="Error")
    
    def populate_co2_dropdowns(self, columns):
        """Populate the CO2 capture calculation dropdowns with column names."""
        # Add empty option at the beginning
        col_list = [""] + list(columns)
        
        self.inlet_co2_combo['values'] = col_list
        self.outlet_co2_combo['values'] = col_list
        self.inlet_flow_combo['values'] = col_list
        
        # Try to auto-select based on common naming patterns
        # Prioritize FT-1003 for flow rate
        flow_selected = False
        for col in columns:
            col_lower = col.lower()
            if 'at-3003' in col_lower or ('inlet' in col_lower and 'co2' in col_lower):
                self.inlet_co2_combo.set(col)
            elif 'at-3007' in col_lower or ('outlet' in col_lower and 'co2' in col_lower):
                self.outlet_co2_combo.set(col)
            elif 'ft-1003' in col_lower:
                self.inlet_flow_combo.set(col)
                flow_selected = True
        
        # If FT-1003 not found, fall back to other flow sensors
        if not flow_selected:
            for col in columns:
                col_lower = col.lower()
                if 'ft-2303' in col_lower or 'flow' in col_lower:
                    self.inlet_flow_combo.set(col)
                    break
        
        print(f"[CO2 Calc] Dropdowns populated with {len(columns)} columns (no-leak assumption)")
    
    def toggle_time_selection(self):
        """Toggle time selection mode for graph clicking."""
        self.time_selection_mode = not self.time_selection_mode
        
        if self.time_selection_mode:
            self.time_select_btn.config(text="✓ Selection Active", style="Accent.TButton")
            self.status.set("Click on graph to select start time, then click again for end time")
            print("[Time Selection] Mode ENABLED - Click on graph to select start and end times")
        else:
            self.time_select_btn.config(text="Select Time Range")
            self.status.set("Time selection mode disabled")
            print("[Time Selection] Mode DISABLED")
    
    def on_graph_click(self, event):
        """Handle mouse clicks on the graph for time selection."""
        print(f"[Time Selection DEBUG] Click detected! Event: {event}")
        print(f"[Time Selection DEBUG] - time_selection_mode: {self.time_selection_mode}")
        print(f"[Time Selection DEBUG] - event.inaxes: {event.inaxes}")
        print(f"[Time Selection DEBUG] - self.ax_left: {self.ax_left}")
        
        if not self.time_selection_mode:
            print("[Time Selection DEBUG] Mode is OFF - ignoring click")
            return
        
        # Check if click is inside the plot area
        if event.inaxes is None:
            print(f"[Time Selection DEBUG] Click outside plot area - ignoring")
            return
        
        if self.df is None or self.time_col is None:
            print(f"[Time Selection DEBUG] No data loaded - df: {self.df is not None}, time_col: {self.time_col}")
            return
        
        # Get the x-coordinate (time) of the click
        clicked_time = event.xdata
        print(f"[Time Selection DEBUG] - clicked_time (xdata): {clicked_time}")
        print(f"[Time Selection DEBUG] - clicked_time type: {type(clicked_time)}")
        
        # Convert matplotlib date to datetime if needed (this will be in PST since x-axis uses _plot_time)
        clicked_timestamp = None
        if isinstance(clicked_time, (int, float)):
            # If x-axis is datetime, convert from matplotlib date number
            try:
                from matplotlib.dates import num2date
                clicked_datetime = num2date(clicked_time)
                print(f"[Time Selection DEBUG] - Converted to datetime: {clicked_datetime}")
                # Convert to pandas timestamp and ensure it's timezone-aware (PST)
                clicked_timestamp = pd.Timestamp(clicked_datetime)
                # Localize to PST if naive, or convert to PST if already aware
                if clicked_timestamp.tzinfo is None:
                    clicked_timestamp = clicked_timestamp.tz_localize(self.display_tz)
                else:
                    clicked_timestamp = clicked_timestamp.tz_convert(self.display_tz)
                print(f"[Time Selection DEBUG] - Pandas timestamp (PST): {clicked_timestamp}")
            except Exception as e:
                print(f"[Time Selection DEBUG] - Conversion error: {e}")
                import traceback
                traceback.print_exc()
                clicked_timestamp = None
        else:
            # May already be a datetime object
            try:
                clicked_timestamp = pd.Timestamp(clicked_time)
                if clicked_timestamp.tzinfo is None:
                    clicked_timestamp = clicked_timestamp.tz_localize(self.display_tz)
                else:
                    clicked_timestamp = clicked_timestamp.tz_convert(self.display_tz)
                print(f"[Time Selection DEBUG] - Direct timestamp conversion (PST): {clicked_timestamp}")
            except Exception as e:
                print(f"[Time Selection DEBUG] - Direct conversion error: {e}")
        
        if clicked_timestamp is None:
            print("[Time Selection] ERROR: Could not determine time from click")
            return
        
        # Set start or end time
        print(f"[Time Selection DEBUG] - selected_time_start: {self.selected_time_start}")
        print(f"[Time Selection DEBUG] - selected_time_end: {self.selected_time_end}")
        
        if self.selected_time_start is None:
            # First click - set start time
            print("[Time Selection DEBUG] Setting START time...")
            self.selected_time_start = clicked_timestamp
            self.start_entry.delete(0, tk.END)
            # Display time in PST with timezone info
            time_str = clicked_timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
            self.start_entry.insert(0, time_str)
            self.status.set(f"Start time set (PST). Now click to select end time.")
            print(f"[Time Selection] ✓ Start time (PST): {clicked_timestamp}")
            
            # Draw vertical line at start
            self._draw_time_selection_lines()
            
        elif self.selected_time_end is None:
            # Second click - set end time
            print("[Time Selection DEBUG] Setting END time...")
            self.selected_time_end = clicked_timestamp
            self.end_entry.delete(0, tk.END)
            # Display time in PST with timezone info
            time_str = clicked_timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
            self.end_entry.insert(0, time_str)
            self.status.set(f"Time range selected (PST). Click 'Calculate CO₂ Captured' to use this range.")
            print(f"[Time Selection] ✓ End time (PST): {clicked_timestamp}")
            print(f"[Time Selection] ✓ Range ready (PST): {self.selected_time_start} to {self.selected_time_end}")
            
            # Draw both lines and shaded region
            self._draw_time_selection_lines()
            
            # Auto-disable selection mode after both points are selected
            self.time_selection_mode = False
            self.time_select_btn.config(text="Select Time Range")
            print("[Time Selection] Mode auto-disabled after selecting both times")
        else:
            # Both already selected - reset and start over
            print("[Time Selection DEBUG] RESETTING - both times already set")
            self.selected_time_start = clicked_timestamp
            self.selected_time_end = None
            self.start_entry.delete(0, tk.END)
            time_str = clicked_timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
            self.start_entry.insert(0, time_str)
            self.end_entry.delete(0, tk.END)
            self.status.set(f"Start time reset (PST). Now click to select end time.")
            print(f"[Time Selection] ✓ Reset - New start time (PST): {clicked_timestamp}")
            
            self._draw_time_selection_lines()
    
    def _draw_time_selection_lines(self):
        """Draw vertical lines and shaded region showing selected time range."""
        print(f"[Time Selection DEBUG] _draw_time_selection_lines called")
        print(f"[Time Selection DEBUG] - start: {self.selected_time_start}")
        print(f"[Time Selection DEBUG] - end: {self.selected_time_end}")
        
        # Remove old lines
        for line in self.time_selection_lines:
            try:
                line.remove()
                print(f"[Time Selection DEBUG] - Removed old line/span")
            except Exception as e:
                print(f"[Time Selection DEBUG] - Error removing line: {e}")
        self.time_selection_lines.clear()
        
        # Draw new lines
        try:
            if self.selected_time_start:
                print(f"[Time Selection DEBUG] Drawing START line at {self.selected_time_start}")
                line1 = self.ax_left.axvline(self.selected_time_start, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Start')
                self.time_selection_lines.append(line1)
                print(f"[Time Selection DEBUG] ✓ START line drawn")
            
            if self.selected_time_end:
                print(f"[Time Selection DEBUG] Drawing END line at {self.selected_time_end}")
                line2 = self.ax_left.axvline(self.selected_time_end, color='red', linestyle='--', linewidth=2, alpha=0.7, label='End')
                self.time_selection_lines.append(line2)
                print(f"[Time Selection DEBUG] ✓ END line drawn")
                
                # Draw shaded region between start and end
                if self.selected_time_start:
                    print(f"[Time Selection DEBUG] Drawing SHADED region from {self.selected_time_start} to {self.selected_time_end}")
                    span = self.ax_left.axvspan(self.selected_time_start, self.selected_time_end, 
                                              alpha=0.2, color='yellow', label='Selected Range')
                    self.time_selection_lines.append(span)
                    print(f"[Time Selection DEBUG] ✓ SHADED region drawn")
            
            print(f"[Time Selection DEBUG] Calling canvas.draw()...")
            self.canvas.draw()
            print(f"[Time Selection DEBUG] ✓ Canvas redrawn successfully")
            
        except Exception as e:
            print(f"[Time Selection DEBUG] ERROR drawing lines: {e}")
            import traceback
            traceback.print_exc()
    
    def on_graph_hover(self, event):
        """Handle mouse hover on the graph to display data point values with elegant crosshair and tooltip."""
        # Only show hover tooltips when not in time selection mode
        if self.time_selection_mode:
            self._clear_hover_elements()
            return
        
        # Check if hover is inside the plot area
        if event.inaxes is None:
            self._clear_hover_elements()
            return
        
        if self.df is None or self.time_col is None:
            return
        
        try:
            # Log hover event occasionally (every 50th call to avoid spam)
            if not hasattr(self, '_hover_call_count'):
                self._hover_call_count = 0
            self._hover_call_count += 1
            log_this_call = (self._hover_call_count % 50 == 1)
            # Get all plotted lines from both axes
            left_lines = self.ax_left.get_lines()
            right_lines = []
            
            # Check if right axis exists
            ax_right = None
            for ax in self.fig.get_axes():
                if ax != self.ax_left and hasattr(ax, 'get_ylabel') and ax.get_ylabel():
                    ax_right = ax
                    right_lines = ax.get_lines()
                    break
            
            # Skip time selection lines (dashed green/red lines)
            left_lines = [line for line in left_lines if line not in self.time_selection_lines 
                         and not (hasattr(line, 'get_linestyle') and line.get_linestyle() == '--' 
                         and hasattr(line, 'get_color') and line.get_color() in ['green', 'red', 'g', 'r'])]
            
            if not left_lines and not right_lines:
                self._clear_hover_elements()
                return
            
            # Get cursor position
            cursor_x = event.xdata
            cursor_y = event.ydata
            
            # Convert matplotlib date to pandas timestamp if needed
            from matplotlib.dates import num2date, date2num
            cursor_time = None
            if isinstance(cursor_x, (int, float)):
                cursor_datetime = num2date(cursor_x)
                cursor_time = pd.Timestamp(cursor_datetime)
                if cursor_time.tzinfo is None:
                    cursor_time = cursor_time.tz_localize(self.display_tz)
                else:
                    cursor_time = cursor_time.tz_convert(self.display_tz)
            
            # Find nearest data points for all series
            hover_data = []
            nearest_x = None
            min_distance = float('inf')
            
            # Check left axis lines
            for line in left_lines:
                xdata = line.get_xdata()
                ydata = line.get_ydata()
                label = line.get_label()
                color = line.get_color()
                
                if len(xdata) == 0 or label.startswith('_'):
                    continue
                
                # Convert xdata to matplotlib date numbers if needed (handle Timestamp objects)
                xdata_numeric = xdata
                if len(xdata) > 0 and isinstance(xdata[0], (pd.Timestamp, np.datetime64)):
                    xdata_numeric = date2num(xdata)
                
                # Find nearest point
                distances = np.abs(xdata_numeric - cursor_x)
                idx = np.argmin(distances)
                
                if distances[idx] < min_distance:
                    min_distance = distances[idx]
                    nearest_x = xdata[idx]
                
                # Store data for tooltip
                hover_data.append({
                    'label': label,
                    'x': xdata[idx],
                    'y': ydata[idx],
                    'color': color,
                    'axis': 'left'
                })
            
            # Check right axis lines
            for line in right_lines:
                xdata = line.get_xdata()
                ydata = line.get_ydata()
                label = line.get_label()
                color = line.get_color()
                
                if len(xdata) == 0 or label.startswith('_'):
                    continue
                
                # Convert xdata to matplotlib date numbers if needed (handle Timestamp objects)
                xdata_numeric = xdata
                if len(xdata) > 0 and isinstance(xdata[0], (pd.Timestamp, np.datetime64)):
                    xdata_numeric = date2num(xdata)
                
                # Find nearest point
                distances = np.abs(xdata_numeric - cursor_x)
                idx = np.argmin(distances)
                
                if distances[idx] < min_distance:
                    min_distance = distances[idx]
                    nearest_x = xdata[idx]
                
                # Store data for tooltip
                hover_data.append({
                    'label': label,
                    'x': xdata[idx],
                    'y': ydata[idx],
                    'color': color,
                    'axis': 'right'
                })
            
            if not hover_data or nearest_x is None:
                self._clear_hover_elements()
                return
            
            # Convert nearest_x to matplotlib date number for comparison if needed
            nearest_x_numeric = nearest_x
            if isinstance(nearest_x, (pd.Timestamp, np.datetime64)):
                nearest_x_numeric = date2num(nearest_x)
            
            # Only show tooltip if cursor is reasonably close to data
            xlim = self.ax_left.get_xlim()
            x_range = xlim[1] - xlim[0]
            threshold = x_range * 0.02  # Within 2% of x-axis range
            
            if min_distance > threshold:
                self._clear_hover_elements()
                return
            
            # Filter to only show data at the nearest x position
            # Convert each x value to numeric for comparison
            filtered_data = []
            for d in hover_data:
                x_val_numeric = d['x']
                if isinstance(x_val_numeric, (pd.Timestamp, np.datetime64)):
                    x_val_numeric = date2num(x_val_numeric)
                if abs(x_val_numeric - nearest_x_numeric) < threshold * 0.1:
                    filtered_data.append(d)
            hover_data = filtered_data
            
            # Clear previous hover elements
            self._clear_hover_elements()
            
            # Draw elegant crosshair at nearest x position (use original value, not numeric)
            self.hover_vline = self.ax_left.axvline(nearest_x, color='gray', linestyle='-', 
                                                    linewidth=0.8, alpha=0.5, zorder=100)
            
            # Draw marker points on each line at the hover position
            for data in hover_data:
                if data['axis'] == 'left':
                    point = self.ax_left.scatter([data['x']], [data['y']], 
                                                color=data['color'], s=60, zorder=101,
                                                edgecolors='white', linewidths=1.5)
                else:
                    point = ax_right.scatter([data['x']], [data['y']], 
                                           color=data['color'], s=60, zorder=101,
                                           edgecolors='white', linewidths=1.5)
                self.hover_points.append(point)
            
            # Create beautiful tooltip text
            tooltip_lines = []
            
            # Add timestamp - convert nearest_x to proper datetime
            if isinstance(nearest_x, (pd.Timestamp, np.datetime64)):
                # Already a timestamp
                time_pd = pd.Timestamp(nearest_x)
            else:
                # It's a matplotlib date number, convert it
                time_obj = num2date(nearest_x)
                time_pd = pd.Timestamp(time_obj)
            
            # Ensure timezone is set correctly
            if time_pd.tzinfo is None:
                time_pd = time_pd.tz_localize(self.display_tz)
            else:
                time_pd = time_pd.tz_convert(self.display_tz)
            
            time_str = time_pd.strftime('%m/%d/%Y %I:%M:%S %p')
            tooltip_lines.append(f"Time: {time_str}")
            tooltip_lines.append("─" * 40)  # Separator
            
            # Add each series value with color coding
            for data in hover_data:
                # Truncate long labels
                label = data['label']
                if len(label) > 45:
                    label = label[:42] + "..."
                
                # Format value with appropriate precision
                value = data['y']
                if abs(value) < 0.01 and value != 0:
                    value_str = f"{value:.6f}"
                elif abs(value) < 1:
                    value_str = f"{value:.4f}"
                elif abs(value) < 100:
                    value_str = f"{value:.3f}"
                else:
                    value_str = f"{value:.2f}"
                
                tooltip_lines.append(f"{label}: {value_str}")
            
            tooltip_text = "\n".join(tooltip_lines)
            
            # Position tooltip smartly (avoid cursor and edge of plot)
            xlim = self.ax_left.get_xlim()
            ylim = self.ax_left.get_ylim()
            
            # Determine if cursor is on left or right side of plot (use numeric version for comparison)
            x_relative = (nearest_x_numeric - xlim[0]) / (xlim[1] - xlim[0])
            y_relative = (cursor_y - ylim[0]) / (ylim[1] - ylim[0])
            
            # Position tooltip on opposite side of cursor
            if x_relative > 0.5:
                # Cursor on right, put tooltip on left
                box_x = 0.02
                ha = 'left'
            else:
                # Cursor on left, put tooltip on right
                box_x = 0.98
                ha = 'right'
            
            if y_relative > 0.5:
                # Cursor on top, put tooltip on bottom
                box_y = 0.02
                va = 'bottom'
            else:
                # Cursor on bottom, put tooltip on top
                box_y = 0.98
                va = 'top'
            
            # Create elegant annotation box
            bbox_props = dict(
                boxstyle='round,pad=0.7',
                facecolor='white',
                edgecolor='#333333',
                alpha=0.95,
                linewidth=1.5
            )
            
            self.hover_annotation = self.ax_left.annotate(
                tooltip_text,
                xy=(nearest_x, cursor_y),
                xytext=(box_x, box_y),
                textcoords='axes fraction',
                fontsize=8,
                fontfamily='monospace',
                bbox=bbox_props,
                ha=ha,
                va=va,
                zorder=102
            )
            
            # Redraw canvas
            self.canvas.draw_idle()
            
            # Log successful tooltip display occasionally
            if log_this_call:
                print(f"[Hover] Tooltip displayed successfully - {len(hover_data)} series at time {time_str}")
            
        except Exception as e:
            print(f"[Hover] Error displaying tooltip: {e}")
            import traceback
            traceback.print_exc()
            self._clear_hover_elements()
    
    def _clear_hover_elements(self):
        """Remove all hover visualization elements from the plot."""
        try:
            # Remove annotation
            if self.hover_annotation is not None:
                self.hover_annotation.remove()
                self.hover_annotation = None
            
            # Remove vertical line
            if self.hover_vline is not None:
                self.hover_vline.remove()
                self.hover_vline = None
            
            # Remove horizontal line
            if self.hover_hline is not None:
                self.hover_hline.remove()
                self.hover_hline = None
            
            # Remove scatter points
            for point in self.hover_points:
                point.remove()
            self.hover_points.clear()
            
            # Redraw canvas
            if hasattr(self, 'canvas'):
                self.canvas.draw_idle()
        except Exception:
            pass
    
    def clear_time_selection(self):
        """Clear the time selection and remove visual indicators."""
        self.selected_time_start = None
        self.selected_time_end = None
        self.start_entry.delete(0, tk.END)
        self.end_entry.delete(0, tk.END)
        
        # Remove visual indicators
        for line in self.time_selection_lines:
            try:
                line.remove()
            except:
                pass
        self.time_selection_lines.clear()
        
        self.canvas.draw()
        self.status.set("Time selection cleared")
        print("[Time Selection] Cleared")
    
    def quick_plot_co2_sensors(self):
        """Quick plot the inlet CO2, outlet CO2, and flow rate sensors selected for calculation."""
        if self.df is None:
            messagebox.showwarning("No data", "Please load a CSV file first.")
            return
        
        # Get selected columns for CO2 calculation
        inlet_co2_col = self.inlet_co2_combo.get()
        outlet_co2_col = self.outlet_co2_combo.get()
        inlet_flow_col = self.inlet_flow_combo.get()
        
        # Validate at least one column is selected
        if not any([inlet_co2_col, outlet_co2_col, inlet_flow_col]):
            messagebox.showwarning("No sensors selected", "Please select at least one sensor (inlet CO2, outlet CO2, or flow rate) to plot.")
            return
        
        print(f"[Quick Plot] Plotting CO2 calculation sensors...")
        
        # Clear current selections
        self.left_list.selection_clear(0, tk.END)
        self.right_list.selection_clear(0, tk.END)
        self.left_selected.clear()
        self.right_selected.clear()
        
        # Add CO2 sensors to left axis (comparing actual column names)
        left_count = 0
        for i in range(self.left_list.size()):
            display_name = self.left_list.get(i)
            actual_col = self.column_display_map.get(display_name, display_name)
            if actual_col in [inlet_co2_col, outlet_co2_col] and actual_col:
                self.left_list.selection_set(i)
                self.left_selected.add(display_name)
                left_count += 1
        
        # Add flow sensor to right axis (comparing actual column names)
        right_count = 0
        for i in range(self.right_list.size()):
            display_name = self.right_list.get(i)
            actual_col = self.column_display_map.get(display_name, display_name)
            if actual_col == inlet_flow_col and actual_col:
                self.right_list.selection_set(i)
                self.right_selected.add(display_name)
                right_count += 1
        
        print(f"[Quick Plot] Selected {left_count} CO2 sensors (left) and {right_count} flow sensor (right)")
        
        # Auto-set axis labels for clarity
        if inlet_co2_col or outlet_co2_col:
            self.left_ylabel.delete(0, tk.END)
            self.left_ylabel.insert(0, "CO2 (ppm)")
        if inlet_flow_col:
            self.right_ylabel.delete(0, tk.END)
            self.right_ylabel.insert(0, "Flow Rate (SLPM)")
        
        # Call plot method
        self.plot()
    
    def calculate_co2_capture(self):
        """Calculate CO2 captured using mass balance equation with no-leak assumption (F_out = F_in)."""
        if self.df is None:
            messagebox.showwarning("No data", "Please load a CSV file first.")
            return
        
        # Get selected columns
        inlet_co2_col = self.inlet_co2_combo.get()
        outlet_co2_col = self.outlet_co2_combo.get()
        inlet_flow_col = self.inlet_flow_combo.get()
        
        # Validate selections
        if not all([inlet_co2_col, outlet_co2_col, inlet_flow_col]):
            messagebox.showwarning("Incomplete selection", "Please select inlet CO₂, outlet CO₂, and flow rate columns.")
            return
        
        # Get calculated Vm parameter
        try:
            Vm = float(self.vm_display.cget("text"))
            if Vm <= 0:
                raise ValueError("Vm must be positive")
        except (ValueError, tk.TclError):
            messagebox.showerror("Invalid Vm", "Please check your temperature, pressure, and compressibility inputs.\nVm calculation resulted in an error.")
            return
        
        try:
            # Apply time window filtering if specified (using PST times)
            df_calc = self.df.copy()
            start_str = self.start_entry.get().strip()
            end_str = self.end_entry.get().strip()
            
            # Use _plot_time for filtering (which is in PST) instead of self.time_col
            time_col_to_filter = '_plot_time' if '_plot_time' in df_calc.columns else self.time_col
            
            if start_str:
                start_time = pd.to_datetime(start_str)
                # Ensure timezone-aware comparison (localize to PST if naive)
                if start_time.tzinfo is None:
                    start_time = start_time.tz_localize(self.display_tz)
                print(f"[CO2 Calc Filter] Start time (PST): {start_time}")
                df_calc = df_calc[df_calc[time_col_to_filter] >= start_time]
            
            if end_str:
                end_time = pd.to_datetime(end_str)
                # Ensure timezone-aware comparison (localize to PST if naive)
                if end_time.tzinfo is None:
                    end_time = end_time.tz_localize(self.display_tz)
                print(f"[CO2 Calc Filter] End time (PST): {end_time}")
                df_calc = df_calc[df_calc[time_col_to_filter] <= end_time]
            
            if df_calc.empty:
                messagebox.showwarning("No data", "No data in the selected time window.")
                return
            
            # Extract time in seconds (assuming time column is datetime)
            if pd.api.types.is_datetime64_any_dtype(df_calc[self.time_col]):
                t_seconds = (df_calc[self.time_col] - df_calc[self.time_col].iloc[0]).dt.total_seconds().values
            else:
                # If time column is numeric (seconds), use directly
                t_seconds = df_calc[self.time_col].values - df_calc[self.time_col].values[0]
            
            # Extract data
            inlet_co2_ppm = pd.to_numeric(df_calc[inlet_co2_col], errors='coerce').values
            outlet_co2_ppm = pd.to_numeric(df_calc[outlet_co2_col], errors='coerce').values
            inlet_flow_slpm = pd.to_numeric(df_calc[inlet_flow_col], errors='coerce').values
            
            # Remove NaN values
            valid = ~(np.isnan(inlet_co2_ppm) | np.isnan(outlet_co2_ppm) | np.isnan(inlet_flow_slpm))
            
            t_seconds = t_seconds[valid]
            inlet_co2_ppm = inlet_co2_ppm[valid]
            outlet_co2_ppm = outlet_co2_ppm[valid]
            inlet_flow_slpm = inlet_flow_slpm[valid]
            
            if len(t_seconds) == 0:
                messagebox.showwarning("No valid data", "No valid data points for calculation.")
                return
            
            # Calculate CO2 capture with no-leak assumption (F_out = F_in)
            # Convert ppm to mole fraction
            x_in = inlet_co2_ppm / 1e6
            x_out = outlet_co2_ppm / 1e6
            
            # Calculate molar flow rate of CO2 captured (mol/s)
            # Flow in SLPM (L/min) -> convert to L/s by dividing by 60
            # Since F_out = F_in, we can factor out the flow rate:
            # CO2_captured = F × (x_in - x_out)
            mol_s = inlet_flow_slpm * (x_in - x_out) / 60.0 / Vm
            
            # Integrate over time to get total moles
            M_CO2 = 44.01  # g/mol
            m_CO2_g = M_CO2 * np.trapezoid(mol_s, t_seconds)
            
            # Calculate time span
            time_span_min = (t_seconds[-1] - t_seconds[0]) / 60.0
            time_span_hr = time_span_min / 60.0
            
            # Display result
            result_text = f"CO₂ Captured: {m_CO2_g:.2f} g ({m_CO2_g/1000:.4f} kg) over {time_span_min:.1f} min"
            self.co2_result_var.set(result_text)
            
            # Log detailed results (using plain text for console compatibility)
            print(f"\n[CO2 Calc] ========================================")
            print(f"[CO2 Calc] Assumption: No leaks (F_out = F_in)")
            print(f"[CO2 Calc] Inlet CO2: {inlet_co2_col}")
            print(f"[CO2 Calc] Outlet CO2: {outlet_co2_col}")
            print(f"[CO2 Calc] Flow Rate: {inlet_flow_col}")
            print(f"[CO2 Calc] Vm: {Vm} L/mol")
            print(f"[CO2 Calc] Time span: {time_span_min:.2f} min ({time_span_hr:.2f} hr)")
            print(f"[CO2 Calc] Data points: {len(t_seconds)}")
            print(f"[CO2 Calc] Avg inlet CO2: {np.mean(inlet_co2_ppm):.1f} ppm")
            print(f"[CO2 Calc] Avg outlet CO2: {np.mean(outlet_co2_ppm):.1f} ppm")
            print(f"[CO2 Calc] Avg CO2 difference: {np.mean(inlet_co2_ppm - outlet_co2_ppm):.1f} ppm")
            print(f"[CO2 Calc] Avg flow rate: {np.mean(inlet_flow_slpm):.1f} SLPM")
            print(f"[CO2 Calc] CO2 CAPTURED: {m_CO2_g:.2f} g ({m_CO2_g/1000:.4f} kg)")
            print(f"[CO2 Calc] Capture rate: {m_CO2_g/time_span_hr:.2f} g/hr")
            print(f"[CO2 Calc] ========================================\n")
            
            messagebox.showinfo("Calculation Complete", 
                              f"CO₂ Captured: {m_CO2_g:.2f} g ({m_CO2_g/1000:.4f} kg)\n\n"
                              f"Time span: {time_span_min:.1f} min ({time_span_hr:.2f} hr)\n"
                              f"Capture rate: {m_CO2_g/time_span_hr:.2f} g/hr\n\n"
                              f"Check console for detailed breakdown.")
            
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Failed to calculate CO₂ capture:\n{str(e)}")
            print(f"[CO2 Calc] Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def plot(self):
        """Generate the plot based on current selections."""
        if self.df is None:
            messagebox.showwarning("No data", "Please load a CSV file first.")
            return
        
        left_cols = self.get_selected(self.left_list, "left")
        right_cols = self.get_selected(self.right_list, "right")
        
        print(f"[Plot] Selected {len(left_cols)} left axis columns: {left_cols}")
        print(f"[Plot] Selected {len(right_cols)} right axis columns: {right_cols}")
        
        if not left_cols and not right_cols:
            messagebox.showwarning("No selection", "Please select at least one series to plot.")
            return
        
        # Time window filtering (using PST times)
        df_plot = self.df.copy()
        start_str = self.start_entry.get().strip()
        end_str = self.end_entry.get().strip()
        
        # Use _plot_time for filtering (which is in PST) instead of self.time_col
        time_col_to_filter = '_plot_time' if '_plot_time' in df_plot.columns else self.time_col
        
        if start_str:
            try:
                start_time = pd.to_datetime(start_str)
                # Ensure timezone-aware comparison (localize to PST if naive)
                if start_time.tzinfo is None:
                    start_time = start_time.tz_localize(self.display_tz)
                print(f"[Plot Filter] Start time (PST): {start_time}")
                df_plot = df_plot[df_plot[time_col_to_filter] >= start_time]
            except Exception as e:
                messagebox.showerror("Invalid start time", f"Could not parse start time:\n{str(e)}")
                return
        
        if end_str:
            try:
                end_time = pd.to_datetime(end_str)
                # Ensure timezone-aware comparison (localize to PST if naive)
                if end_time.tzinfo is None:
                    end_time = end_time.tz_localize(self.display_tz)
                print(f"[Plot Filter] End time (PST): {end_time}")
                df_plot = df_plot[df_plot[time_col_to_filter] <= end_time]
            except Exception as e:
                messagebox.showerror("Invalid end time", f"Could not parse end time:\n{str(e)}")
                return
        
        if df_plot.empty:
            messagebox.showwarning("No data", "No data in the selected time window.")
            return
        
        # Apply smoothing if requested
        if self.smooth_var.get():
            try:
                window = int(self.window_entry.get())
                if window % 2 == 0:
                    window += 1  # Make it odd
                for c in [*left_cols, *right_cols]:
                    if c in df_plot.columns:
                        df_plot[c] = pd.to_numeric(df_plot[c], errors="coerce").rolling(window, min_periods=1, center=True).mean()
            except ValueError:
                messagebox.showerror("Invalid window", "Smoothing window must be a valid integer.")
                return
        
        # Clear previous plot
        self.fig.clear()
        self.ax_left = self.fig.add_subplot(111)
        
        # Plot left axis
        # Reset last-plotted lines tracking
        self.last_series_lines = {"left": {}, "right": {}}

        for c in left_cols:
            y = pd.to_numeric(df_plot[c], errors="coerce")
            
            # Get custom properties if they exist
            props = self.series_properties.get(c, {})
            display_label = self.column_to_display.get(c, self.get_display_name(c))
            plot_kwargs = {'label': display_label}
            
            if props.get('color'):
                plot_kwargs['color'] = props['color']
            if 'linestyle' in props:
                plot_kwargs['linestyle'] = props['linestyle']
            if 'linewidth' in props:
                plot_kwargs['linewidth'] = props['linewidth']
            if props.get('marker'):
                plot_kwargs['marker'] = props['marker']
            if 'markersize' in props:
                plot_kwargs['markersize'] = props['markersize']
            
            # Use timezone-adjusted plotting series if present
            x_series = df_plot['_plot_time'] if '_plot_time' in df_plot.columns else df_plot[self.time_col]
            line_left, = self.ax_left.plot(x_series, y, **plot_kwargs)
            # Record last-plotted line for introspection by customize dialog
            self.last_series_lines["left"][c] = line_left
            
            if props:
                print(f"[Plot] Applied custom properties to '{c}': {props}")
        
        # Use custom axis labels
        x_label = self.xlabel.get().strip() or self.time_col
        left_y_label = self.left_ylabel.get().strip() or "Left axis"
        right_y_label = self.right_ylabel.get().strip() or "Right axis"
        
        print(f"[Plot] Axis labels - X: '{x_label}', Left Y: '{left_y_label}', Right Y: '{right_y_label}'")
        
        self.ax_left.set_xlabel(x_label)
        self.ax_left.set_ylabel(left_y_label)
        
        if self.grid_var.get():
            self.ax_left.grid(True, which="both", linestyle=":")
        
        # Configure x-axis formatter for 12-hour PST
        try:
            locator = mdates.AutoDateLocator()
            self.ax_left.xaxis.set_major_locator(locator)
            self.ax_left.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %I:%M %p', tz=self.display_tz))
        except Exception as e:
            print(f"[Time TZ] Could not set 12-hour PST formatter: {e}")

        # Plot right axis
        ax_right = None
        if right_cols:
            ax_right = self.ax_left.twinx()
            for c in right_cols:
                y = pd.to_numeric(df_plot[c], errors="coerce")
                
                # Get custom properties if they exist
                props = self.series_properties.get(c, {})
                display_label = self.column_to_display.get(c, self.get_display_name(c))
                plot_kwargs = {'label': display_label}
                
                # Default to dashed line for right axis if not customized
                if 'linestyle' in props:
                    plot_kwargs['linestyle'] = props['linestyle']
                else:
                    plot_kwargs['linestyle'] = '--'
                
                if props.get('color'):
                    plot_kwargs['color'] = props['color']
                if 'linewidth' in props:
                    plot_kwargs['linewidth'] = props['linewidth']
                if props.get('marker'):
                    plot_kwargs['marker'] = props['marker']
                if 'markersize' in props:
                    plot_kwargs['markersize'] = props['markersize']
                
                x_series = df_plot['_plot_time'] if '_plot_time' in df_plot.columns else df_plot[self.time_col]
                line_right, = ax_right.plot(x_series, y, **plot_kwargs)
                # Record last-plotted line for introspection by customize dialog
                self.last_series_lines["right"][c] = line_right
                
                if props:
                    print(f"[Plot] Applied custom properties to '{c}' (right axis): {props}")
            
            ax_right.set_ylabel(right_y_label)
        
        # Compose legend with customization options
        if self.show_legend_var.get():
            handles_left, labels_left = self.ax_left.get_legend_handles_labels()
            handles_right, labels_right = (ax_right.get_legend_handles_labels() if ax_right else ([], []))
            handles = handles_left + handles_right
            labels = labels_left + labels_right
            
            if handles:
                # Map position names to matplotlib location codes
                position_map = {
                    "Upper Left": "upper left",
                    "Upper Right": "upper right",
                    "Lower Left": "lower left",
                    "Lower Right": "lower right",
                    "Best": "best",
                    "Outside Right": "center left",
                    "Outside Bottom": "upper center"
                }
                
                legend_pos = self.legend_position.get()
                loc = position_map.get(legend_pos, "upper left")
                
                # Get legend parameters
                try:
                    fontsize = int(self.legend_fontsize.get())
                except ValueError:
                    fontsize = 8
                
                try:
                    ncol = int(self.legend_columns.get())
                except ValueError:
                    ncol = 1
                
                framealpha = 0.7 if self.legend_framealpha_var.get() else 1.0
                
                # Handle "outside" positions
                if legend_pos == "Outside Right":
                    legend = self.ax_left.legend(handles, labels, loc=loc, bbox_to_anchor=(1.05, 0.5),
                                                fontsize=fontsize, ncol=ncol, framealpha=framealpha)
                elif legend_pos == "Outside Bottom":
                    legend = self.ax_left.legend(handles, labels, loc=loc, bbox_to_anchor=(0.5, -0.15),
                                                fontsize=fontsize, ncol=ncol, framealpha=framealpha)
                else:
                    legend = self.ax_left.legend(handles, labels, loc=loc,
                                                fontsize=fontsize, ncol=ncol, framealpha=framealpha)
                
                print(f"[Plot] Legend: position={legend_pos}, fontsize={fontsize}, columns={ncol}, alpha={framealpha}")
        else:
            print(f"[Plot] Legend hidden")
        
        # Use custom graph title
        title = self.graph_title.get().strip() or "Sensor Time Series"
        self.fig.suptitle(title)
        print(f"[Plot] Graph title: '{title}'")
        
        # Add watermark if available and enabled (top-right, semi-transparent, behind lines)
        if self.watermark_var.get():
            try:
                if self.watermark_image is not None:
                    # Scale watermark relative to figure size - half the previous size
                    fig_w, fig_h = self.fig.get_size_inches()
                    dpi = self.fig.get_dpi()
                    target_width_px = int(fig_w * dpi * 0.1375)  # ~13.75% of figure width (half of previous)
                    ratio = target_width_px / max(self.watermark_image.width, 1)
                    target_height_px = max(int(self.watermark_image.height * ratio), 1)
                    wm_resized = self.watermark_image.resize((max(target_width_px,1), target_height_px), Image.LANCZOS)
                    
                    # Convert to numpy array and modify alpha channel directly
                    wm_array = np.array(wm_resized, dtype=float) / 255.0  # Normalize to 0-1
                    if wm_array.shape[-1] == 4:  # Has alpha channel
                        # Multiply existing alpha by desired opacity (15%)
                        wm_array[:, :, 3] = wm_array[:, :, 3] * 0.15
                    else:
                        # Add alpha channel if not present
                        alpha = np.ones((wm_array.shape[0], wm_array.shape[1], 1)) * 0.15
                        wm_array = np.concatenate([wm_array, alpha], axis=2)
                    
                    # Create OffsetImage with modified array
                    imagebox = OffsetImage(wm_array, zoom=1.0)
                    ab = AnnotationBbox(
                        imagebox, 
                        (0.82, 0.88),  # Top-right position within plot area
                        xycoords='axes fraction', 
                        frameon=False,
                        box_alignment=(1.0, 1.0),  # Align box to top-right corner
                        zorder=0  # Behind data lines
                    )
                    # Remove previous
                    if self.watermark_artist is not None:
                        try:
                            self.watermark_artist.remove()
                        except Exception:
                            pass
                    self.watermark_artist = self.ax_left.add_artist(ab)
                    print(f"[Watermark] Placed watermark at top-right (0.82, 0.88): {target_width_px}x{target_height_px}px, alpha=0.15 (15% opacity), zorder=0")
            except Exception as e:
                print(f"[Watermark] Failed to place watermark: {e}")
                import traceback
                traceback.print_exc()
        else:
            # Remove watermark if checkbox is unchecked
            if self.watermark_artist is not None:
                try:
                    self.watermark_artist.remove()
                    self.watermark_artist = None
                    print(f"[Watermark] Watermark disabled by user")
                except Exception:
                    pass

        self.fig.tight_layout()
        self.canvas.draw()
        
        self.status.set(f"Plotted {len(left_cols)} left + {len(right_cols)} right series ({len(df_plot)} points)")

if __name__ == "__main__":
    app = SensorGrapher()
    app.mainloop()
