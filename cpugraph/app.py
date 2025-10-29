from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from dateutil import tz
from matplotlib import colors as mcolors
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from calculations import (
    CO2CalculationError,
    CO2CaptureCalculator,
    RHCalculationError,
    RHCalculator,
)
from config import (
    DEFAULT_FLOW_SENSORS,
    DEFAULT_INLET_SENSORS,
    DEFAULT_LEFT_AXIS_SENSORS,
    DEFAULT_OUTLET_SENSORS,
    DISPLAY_TZ_NAME,
    SENSOR_DESCRIPTIONS,
)
from data_loader import DataLoadError, SensorDataLoader
from watermark import load_watermark_image
from plotting import SensorPlotter, HoverTooltipHandler, TimeSelectionHandler
from plotting.plotter import PlotOptions
from ui.dialogs import SeriesCustomizeDialog
from ui.controls import (
    SeriesSelector,
    PlotOptionsPanel,
    LegendOptionsPanel,
    GraphLabelsPanel,
    TimeWindowPanel,
    CO2CalculationPanel,
    RHCalculationPanel,
)
from ui.selection import SeriesSelectionManager


class SensorDashboardApp(tk.Tk):
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
        
        self.df: Optional[pd.DataFrame] = None
        self.time_col: Optional[str] = None
        self.all_columns: List[str] = []  # Store all available columns
        self.column_display_map: Dict[str, str] = {}  # Map display names to actual column names
        self.column_to_display: Dict[str, str] = {}  # Reverse map: actual column names to display names
        
        # Initialize selection manager (will be updated when file is loaded)
        self.selection_mgr = SeriesSelectionManager(
            all_columns=self.all_columns,
            column_to_display=self.column_to_display,
            column_display_map=self.column_display_map,
        )
        
        # Store custom line properties for each series (keyed by actual column name)
        self.series_properties = {}  # {column_name: {'color': str, 'linestyle': str, 'linewidth': float, 'marker': str, 'markersize': float}}

        # Keep references to last-plotted matplotlib Line2D per axis and series
        self.last_series_lines = {"left": {}, "right": {}}

        # Time display timezone (12-hour Pacific Time)
        self.display_tz_name = DISPLAY_TZ_NAME
        self.display_tz = tz.gettz(self.display_tz_name)

        # Watermark (loaded once)
        self.watermark_image = load_watermark_image(Path(__file__).resolve().parent.parent)
        self.watermark_artist = None

        # Support services
        self.sensor_descriptions = SENSOR_DESCRIPTIONS
        self.data_loader = SensorDataLoader(sensor_descriptions=self.sensor_descriptions, display_timezone=self.display_tz)
        self.co2_calculator = CO2CaptureCalculator(display_timezone=self.display_tz)
        self.rh_calculator = RHCalculator(display_timezone=self.display_tz)

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

        # Calculate adaptive widths based on screen size
        listbox_width = max(min(int(screen_width / 25), 50), 35)
        
        # Series selector panel (with integrated selection management)
        self.series_selector = SeriesSelector(
            mid, self,
            selection_manager=self.selection_mgr,
            listbox_width=listbox_width,
        )
        self.series_selector.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2, fill=tk.Y)
        
        # Create references for backward compatibility
        self.left_filter = self.series_selector.left_filter
        self.right_filter = self.series_selector.right_filter
        self.left_list = self.series_selector.left_list
        self.right_list = self.series_selector.right_list

        # Plot options panel
        self.plot_options = PlotOptionsPanel(mid, self)
        self.plot_options.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2, fill=tk.Y)
        
        # Create references for backward compatibility
        self.grid_var = self.plot_options.grid_var
        self.smooth_var = self.plot_options.smooth_var
        self.window_entry = self.plot_options.window_entry
        self.watermark_var = self.plot_options.watermark_var
        
        # Legend options panel
        self.legend_options = LegendOptionsPanel(mid, self)
        self.legend_options.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2, fill=tk.Y)
        
        # Create references for backward compatibility
        self.show_legend_var = self.legend_options.show_legend_var
        self.legend_position = self.legend_options.legend_position
        self.legend_fontsize = self.legend_options.legend_fontsize
        self.legend_columns = self.legend_options.legend_columns
        self.legend_framealpha_var = self.legend_options.legend_framealpha_var
        
        # Adaptive entry field width
        label_entry_width = max(min(int(screen_width / 50), 25), 18)
        
        # Graph labels panel
        self.graph_labels = GraphLabelsPanel(mid, self, label_entry_width=label_entry_width)
        self.graph_labels.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2, fill=tk.Y)
        
        # Create references for backward compatibility
        self.graph_title = self.graph_labels.graph_title
        self.left_ylabel = self.graph_labels.left_ylabel
        self.right_ylabel = self.graph_labels.right_ylabel
        self.xlabel = self.graph_labels.xlabel

        # Time window panel
        self.time_window = TimeWindowPanel(
            mid, self,
            label_entry_width=label_entry_width,
            toggle_time_selection_callback=self.toggle_time_selection,
            clear_time_selection_callback=self.clear_time_selection,
        )
        self.time_window.pack(side=tk.LEFT, padx=calc_padding, pady=calc_padding//2, fill=tk.Y)
        
        # Create references for backward compatibility
        self.start_entry = self.time_window.start_entry
        self.end_entry = self.time_window.end_entry
        self.time_select_btn = self.time_window.time_select_btn

        # Plot and customization buttons (adaptive padding)
        plot_customize_frame = ttk.Frame(mid)
        plot_customize_frame.pack(side=tk.LEFT, padx=max(base_padding, 6), pady=calc_padding//2)
        ttk.Button(plot_customize_frame, text="Customize Series", command=self.open_customize_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(plot_customize_frame, text="Plot", command=self.plot).pack(side=tk.LEFT, padx=2)

        # === CO2 Capture Calculation Panel ===
        # Adaptive combo box width for CO2 calculation
        combo_width = max(min(int(screen_width / 35), 30), 20)
        
        self.co2_panel = CO2CalculationPanel(
            main_container, self,
            combo_width=combo_width,
            on_vm_update=self.update_vm,
            on_quick_plot=self.quick_plot_co2_sensors,
            on_calculate=self.calculate_co2_capture,
        )
        self.co2_panel.grid(row=3, column=0, sticky="ew", padx=base_padding, pady=max(base_padding//2, 2))
        
        # Create references for backward compatibility
        self.inlet_co2_combo = self.co2_panel.inlet_co2_combo
        self.outlet_co2_combo = self.co2_panel.outlet_co2_combo
        self.inlet_flow_combo = self.co2_panel.inlet_flow_combo
        self.temp_entry = self.co2_panel.temp_entry
        self.pressure_entry = self.co2_panel.pressure_entry
        self.pressure_unit_combo = self.co2_panel.pressure_unit_combo
        self.z_entry = self.co2_panel.z_entry
        self.vm_display = self.co2_panel.vm_display
        self.co2_result_var = self.co2_panel.co2_result_var

        # === Relative Humidity Calculation Panel ===
        self.rh_panel = RHCalculationPanel(
            main_container, self,
            combo_width=combo_width,
            on_quick_plot=self.quick_plot_rh_sensors,
            on_calculate=self.calculate_relative_humidity,
        )
        self.rh_panel.grid(row=4, column=0, sticky="ew", padx=base_padding, pady=max(base_padding//2, 2))
        
        # Create references for backward compatibility
        self.temp_combo = self.rh_panel.temp_combo
        self.dewpoint_combo = self.rh_panel.dewpoint_combo
        self.rh_result_var = self.rh_panel.rh_result_var

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
        
        # Initialize plotting components
        self.plotter = SensorPlotter(self.fig, self.display_tz, self.watermark_image)
        self.hover_handler = HoverTooltipHandler(self.fig, self.ax_left, self.canvas, self.display_tz)
        self.time_selector = TimeSelectionHandler(self.ax_left, self.canvas, self.display_tz, self.df, self.time_col)
        
        # Wire up time selection callbacks to UI
        self.time_selector.on_mode_changed = self._on_time_selection_mode_changed
        self.time_selector.on_time_selected = self._on_time_selected
        self.time_selector.on_status_update = lambda msg: self.status.set(msg)
        
        # Link time selection lines to hover handler so they're ignored
        self.hover_handler.time_selection_lines = self.time_selector.get_selection_lines()

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

        # Comboboxes in CO2 calc and RH calc
        for w_name in ['inlet_co2_combo', 'outlet_co2_combo', 'inlet_flow_combo', 'temp_combo', 'dewpoint_combo']:
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
    
    # toggle_smooth is now handled by PlotOptionsPanel
    # on_filter_focus_in and on_filter_focus_out are now handled by SelectionManager
    
    # update_selection_tracking is now handled by SelectionManager

    # filter_listbox, select_all, and deselect_all are now handled by SeriesSelectionManager
    # (called directly from SeriesSelector, not from app.py)

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
        
        # Open the customize dialog
        dialog = SeriesCustomizeDialog(
            self,
            all_series,
            self.series_properties,
            self.last_series_lines
        )
        
        updated_properties = dialog.show()
        
        # Update properties if user clicked Apply
        if updated_properties is not None:
            self.series_properties = updated_properties

    def open_csv(self):
        """Open a CSV or tab-delimited TXT file and populate the listboxes with available columns."""
        path = filedialog.askopenfilename(
            title="Select data file (CSV or TXT)",
            filetypes=[("Data files", "*.csv *.txt"), ("CSV files", "*.csv"), ("TXT files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            result = self.data_loader.load(path)
        except DataLoadError as exc:
            messagebox.showerror("Error loading file", f"Failed to load file:\n{exc}")
            return

        self.df = result.dataframe
        self.time_col = result.time_column
        self.all_columns = result.numeric_columns
        self.column_display_map = result.display_to_column
        self.column_to_display = result.column_to_display
        
        # Update selection manager with new columns
        self.selection_mgr.update_columns(
            self.all_columns,
            self.column_to_display,
            self.column_display_map
        )
        
        # Update time selector with new data
        self.time_selector.set_data(self.df, self.time_col)
        
        # Update mode filter with available modes
        self.time_window.update_available_modes(self.df, self.time_col)

        print(
            f"[File Load] Found {len(self.all_columns)} numeric columns in {result.source_path.name}"
        )
        print(
            f"[File Load] Columns: {', '.join(self.all_columns[:10])}{'...' if len(self.all_columns) > 10 else ''}"
        )

        # Reset filters
        self.left_filter.delete(0, tk.END)
        self.left_filter.insert(0, "Filter...")
        self.left_filter.config(foreground="gray")
        self.right_filter.delete(0, tk.END)
        self.right_filter.insert(0, "Filter...")
        self.right_filter.config(foreground="gray")

        # Populate listboxes with display names
        self.left_list.delete(0, tk.END)
        self.right_list.delete(0, tk.END)

        for column in self.all_columns:
            display_name = self.column_to_display[column]
            self.left_list.insert(tk.END, display_name)
            self.right_list.insert(tk.END, display_name)

        # Auto-select default sensors on the left axis
        for index, column in enumerate(self.all_columns):
            if any(sensor_id in column.upper() for sensor_id in DEFAULT_LEFT_AXIS_SENSORS):
                display_name = self.column_to_display[column]
                self.left_list.selection_set(index)
                self.selection_mgr.left_selected.add(display_name)
                print(f"[File Load] Auto-selected: {display_name}")

        self.status.set(
            f"Loaded: {result.source_path.name} ({len(self.df)} rows, {len(self.all_columns)} numeric columns)"
        )

        self.populate_co2_dropdowns(self.all_columns)
        self.populate_rh_dropdowns(self.all_columns)
    
    def get_selected(self, listbox, side):
        """Get selected items from a listbox (delegates to SelectionManager).
        
        Args:
            listbox: The listbox widget
            side: 'left' or 'right'
            
        Returns:
            List of actual column names (not display names) for plotting
        """
        return self.selection_mgr.get_selected_columns(side, listbox)
    
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
    
    def _on_time_selection_mode_changed(self, mode_active: bool) -> None:
        """Callback when time selection mode changes.
        
        Args:
            mode_active: True if selection mode is now active
        """
        if mode_active:
            self.time_select_btn.config(text="✓ Selection Active", style="Accent.TButton")
        else:
            self.time_select_btn.config(text="Select Time Range")
    
    def _on_time_selected(self, start_str: Optional[str], end_str: Optional[str]) -> None:
        """Callback when time selection points are chosen.
        
        Args:
            start_str: Start time string (or None to clear)
            end_str: End time string (or None to clear)
        """
        self.start_entry.delete(0, tk.END)
        if start_str:
            self.start_entry.insert(0, start_str)
        
        self.end_entry.delete(0, tk.END)
        if end_str:
            self.end_entry.insert(0, end_str)
    
    def populate_co2_dropdowns(self, columns):
        """Populate the CO₂ capture calculation dropdowns with column names."""
        column_list = [""] + list(columns)

        self.inlet_co2_combo["values"] = column_list
        self.outlet_co2_combo["values"] = column_list
        self.inlet_flow_combo["values"] = column_list

        inlet_selected = False
        outlet_selected = False
        flow_selected = False

        for column in columns:
            upper_name = column.upper()
            if not inlet_selected and any(sensor in upper_name for sensor in DEFAULT_INLET_SENSORS):
                self.inlet_co2_combo.set(column)
                inlet_selected = True
            if not outlet_selected and any(sensor in upper_name for sensor in DEFAULT_OUTLET_SENSORS):
                self.outlet_co2_combo.set(column)
                outlet_selected = True
            if not flow_selected and any(sensor in upper_name for sensor in DEFAULT_FLOW_SENSORS):
                self.inlet_flow_combo.set(column)
                flow_selected = True

        # Fallback heuristics when no defaults matched
        for column in columns:
            lower_name = column.lower()
            if not inlet_selected and "inlet" in lower_name and "co2" in lower_name:
                self.inlet_co2_combo.set(column)
                inlet_selected = True
            if not outlet_selected and "outlet" in lower_name and "co2" in lower_name:
                self.outlet_co2_combo.set(column)
                outlet_selected = True
            if not flow_selected and "flow" in lower_name:
                self.inlet_flow_combo.set(column)
                flow_selected = True

        print(f"[CO2 Calc] Dropdowns populated with {len(columns)} columns (no-leak assumption)")
    
    def populate_rh_dropdowns(self, columns):
        """Populate the RH calculation dropdowns with temperature and dew point transmitters."""
        column_list = [""] + list(columns)

        self.temp_combo["values"] = column_list
        self.dewpoint_combo["values"] = column_list

        temp_selected = False
        dewpoint_selected = False

        # Auto-select temperature transmitters (TT) and dew point transmitters (AT with DEW POINT)
        for column in columns:
            upper_name = column.upper()
            
            # Look for temperature transmitters (TT)
            if not temp_selected and "TT-" in upper_name and "TEMP" in upper_name:
                # Prefer certain temperature sensors (e.g., gas delivery, ambient)
                if any(keyword in upper_name for keyword in ["DELIVERY", "AMBIENT", "AIR", "GAS ENTRANCE"]):
                    self.temp_combo.set(column)
                    temp_selected = True
            
            # Look for dew point transmitters (AT with DEW POINT)
            if not dewpoint_selected and "AT-" in upper_name and "DEW" in upper_name:
                self.dewpoint_combo.set(column)
                dewpoint_selected = True
            
            # Break early if both are selected
            if temp_selected and dewpoint_selected:
                break
        
        # If no specific match, try broader patterns
        if not temp_selected:
            for column in columns:
                upper_name = column.upper()
                if "TT-" in upper_name:
                    self.temp_combo.set(column)
                    temp_selected = True
                    break
        
        if not dewpoint_selected:
            for column in columns:
                upper_name = column.upper()
                if "DEW" in upper_name and "POINT" in upper_name:
                    self.dewpoint_combo.set(column)
                    dewpoint_selected = True
                    break

        print(f"[RH Calc] Dropdowns populated with {len(columns)} columns")
        if temp_selected:
            print(f"[RH Calc] Auto-selected temperature: {self.temp_combo.get()}")
        if dewpoint_selected:
            print(f"[RH Calc] Auto-selected dew point: {self.dewpoint_combo.get()}")
    
    def quick_plot_rh_sensors(self):
        """Quick plot the temperature and dew point transmitters selected for RH calculation."""
        if self.df is None:
            messagebox.showwarning("No data", "Please load a CSV file first.")
            return
        
        # Get selected columns for RH calculation
        temp_col = self.temp_combo.get()
        dewpoint_col = self.dewpoint_combo.get()
        
        # Validate at least one column is selected
        if not any([temp_col, dewpoint_col]):
            messagebox.showwarning("No sensors selected", "Please select at least one sensor (temperature or dew point) to plot.")
            return
        
        print(f"[Quick Plot] Plotting RH calculation sensors...")
        
        # Clear current selections
        self.left_list.selection_clear(0, tk.END)
        self.right_list.selection_clear(0, tk.END)
        self.selection_mgr.clear_selections()
        
        # Add both sensors to left axis
        count = 0
        for i in range(self.left_list.size()):
            display_name = self.left_list.get(i)
            actual_col = self.column_display_map.get(display_name, display_name)
            if actual_col in [temp_col, dewpoint_col] and actual_col:
                self.left_list.selection_set(i)
                self.selection_mgr.left_selected.add(display_name)
                count += 1
        
        print(f"[Quick Plot] Selected {count} RH sensors (left axis)")
        
        # Auto-set axis label for clarity
        if temp_col or dewpoint_col:
            self.left_ylabel.delete(0, tk.END)
            self.left_ylabel.insert(0, "Temperature (°C)")
        
        # Call plot method
        self.plot()
    
    def calculate_relative_humidity(self):
        """Calculate relative humidity from temperature and dew point using Magnus-Tetens formula."""
        if self.df is None:
            messagebox.showwarning("No data", "Please load a CSV file first.")
            return

        # Get selected columns
        temp_col = self.temp_combo.get()
        dewpoint_col = self.dewpoint_combo.get()

        # Validate selections
        if not all([temp_col, dewpoint_col]):
            messagebox.showwarning("Incomplete selection", "Please select both temperature and dew point transmitters.")
            return

        time_column = "_plot_time" if "_plot_time" in self.df.columns else self.time_col
        start_str = self.start_entry.get().strip() or None
        end_str = self.end_entry.get().strip() or None

        try:
            result = self.rh_calculator.calculate(
                self.df,
                time_column=time_column,
                temperature_column=temp_col,
                dewpoint_column=dewpoint_col,
                start_time=start_str,
                end_time=end_str,
            )
        except RHCalculationError as exc:
            message = str(exc)
            print(f"[RH Calc] Error: {message}")
            if "No data" in message:
                messagebox.showwarning("Calculation Error", message)
            else:
                messagebox.showerror("Calculation Error", message)
            return

        # Format detailed result for display
        result_text = (
            f"Average RH: {result.average_rh_percent:.1f}%\n"
            f"Range: {result.min_rh_percent:.1f}% - {result.max_rh_percent:.1f}%\n"
            f"Data points: {result.data_points}"
        )
        self.rh_result_var.set(result_text)

        print(f"\n[RH Calc] ========================================")
        print(f"[RH Calc] Temperature: {temp_col}")
        print(f"[RH Calc] Dew Point: {dewpoint_col}")
        print(f"[RH Calc] Time span: {result.time_span_minutes:.2f} min")
        print(f"[RH Calc] Data points: {result.data_points}")
        print(f"[RH Calc] Avg temperature: {result.average_temperature_c:.1f}°C")
        print(f"[RH Calc] Avg dew point: {result.average_dewpoint_c:.1f}°C")
        print(f"[RH Calc] AVERAGE RH: {result.average_rh_percent:.1f}%")
        print(f"[RH Calc] Min RH: {result.min_rh_percent:.1f}%")
        print(f"[RH Calc] Max RH: {result.max_rh_percent:.1f}%")
        print(f"[RH Calc] ========================================\n")

        messagebox.showinfo(
            "Calculation Complete",
            (
                f"Relative Humidity Calculated\n\n"
                f"Average RH: {result.average_rh_percent:.1f}%\n"
                f"Range: {result.min_rh_percent:.1f}% - {result.max_rh_percent:.1f}%\n\n"
                f"Based on {result.data_points} data points over {result.time_span_minutes:.1f} minutes\n\n"
                f"Check console for detailed breakdown."
            ),
        )
    
    def toggle_time_selection(self):
        """Toggle time selection mode for graph clicking."""
        self.time_selector.toggle_mode()
    
    # on_graph_click is now handled by TimeSelectionHandler (connected in __init__)
    
    # _draw_time_selection_lines is now handled by TimeSelectionHandler
    
    # on_graph_hover and _clear_hover_elements are now handled by HoverTooltipHandler (connected in __init__)
    
    def clear_time_selection(self):
        """Clear the time selection and remove visual indicators."""
        self.time_selector.clear_selection()
    
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
        self.selection_mgr.clear_selections()
        
        # Add CO2 sensors to left axis (comparing actual column names)
        left_count = 0
        for i in range(self.left_list.size()):
            display_name = self.left_list.get(i)
            actual_col = self.column_display_map.get(display_name, display_name)
            if actual_col in [inlet_co2_col, outlet_co2_col] and actual_col:
                self.left_list.selection_set(i)
                self.selection_mgr.left_selected.add(display_name)
                left_count += 1
        
        # Add flow sensor to right axis (comparing actual column names)
        right_count = 0
        for i in range(self.right_list.size()):
            display_name = self.right_list.get(i)
            actual_col = self.column_display_map.get(display_name, display_name)
            if actual_col == inlet_flow_col and actual_col:
                self.right_list.selection_set(i)
                self.selection_mgr.right_selected.add(display_name)
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

        time_column = "_plot_time" if "_plot_time" in self.df.columns else self.time_col
        start_str = self.start_entry.get().strip() or None
        end_str = self.end_entry.get().strip() or None

        try:
            result = self.co2_calculator.calculate(
                self.df,
                time_column=time_column,
                inlet_co2_column=inlet_co2_col,
                outlet_co2_column=outlet_co2_col,
                inlet_flow_column=inlet_flow_col,
                molar_volume=Vm,
                start_time=start_str,
                end_time=end_str,
            )
        except CO2CalculationError as exc:
            message = str(exc)
            print(f"[CO2 Calc] Error: {message}")
            if "No data" in message:
                messagebox.showwarning("Calculation Error", message)
            else:
                messagebox.showerror("Calculation Error", message)
            return

        self.co2_result_var.set(result.summary())

        print(f"\n[CO2 Calc] ========================================")
        print(f"[CO2 Calc] Assumption: No leaks (F_out = F_in)")
        print(f"[CO2 Calc] Inlet CO2: {inlet_co2_col}")
        print(f"[CO2 Calc] Outlet CO2: {outlet_co2_col}")
        print(f"[CO2 Calc] Flow Rate: {inlet_flow_col}")
        print(f"[CO2 Calc] Vm: {Vm} L/mol")
        print(
            f"[CO2 Calc] Time span: {result.time_span_minutes:.2f} min ({result.time_span_hours:.2f} hr)"
        )
        print(f"[CO2 Calc] Data points: {result.data_points}")
        print(f"[CO2 Calc] Avg inlet CO2: {result.average_inlet_ppm:.1f} ppm")
        print(f"[CO2 Calc] Avg outlet CO2: {result.average_outlet_ppm:.1f} ppm")
        print(
            f"[CO2 Calc] Avg CO2 difference: {result.average_inlet_ppm - result.average_outlet_ppm:.1f} ppm"
        )
        print(f"[CO2 Calc] Avg flow rate: {result.average_flow_slpm:.1f} SLPM")
        print(
            f"[CO2 Calc] CO2 CAPTURED: {result.mass_grams:.2f} g ({result.mass_kilograms:.4f} kg)"
        )
        print(f"[CO2 Calc] Capture rate: {result.capture_rate_g_per_hr:.2f} g/hr")
        print(f"[CO2 Calc] ========================================\n")

        messagebox.showinfo(
            "Calculation Complete",
            (
                f"CO₂ Captured: {result.mass_grams:.2f} g ({result.mass_kilograms:.4f} kg)\n\n"
                f"Time span: {result.time_span_minutes:.1f} min ({result.time_span_hours:.2f} hr)\n"
                f"Capture rate: {result.capture_rate_g_per_hr:.2f} g/hr\n\n"
                "Check console for detailed breakdown."
            ),
        )
    
    # _add_cycle_backgrounds is now handled by CycleBackgroundRenderer in the SensorPlotter
    
    def plot(self):
        """Generate the plot based on current selections."""
        if self.df is None:
            messagebox.showwarning("No data", "Please load a CSV file first.")
            return
        
        left_cols = self.get_selected(self.left_list, "left")
        right_cols = self.get_selected(self.right_list, "right")
        
        if not left_cols and not right_cols:
            messagebox.showwarning("No selection", "Please select at least one series to plot.")
            return
        
        # Get smoothing parameters
        smoothing_window = 21
        if self.smooth_var.get():
            try:
                smoothing_window = int(self.window_entry.get())
            except ValueError:
                messagebox.showerror("Invalid window", "Smoothing window must be a valid integer.")
                return
        
        # Get legend parameters
        try:
            legend_fontsize = int(self.legend_fontsize.get())
        except ValueError:
            legend_fontsize = 8
        
        try:
            legend_columns = int(self.legend_columns.get())
        except ValueError:
            legend_columns = 1
        
        # Build plot options from UI state
        options = PlotOptions(
            show_grid=self.grid_var.get(),
            apply_smoothing=self.smooth_var.get(),
            smoothing_window=smoothing_window,
            show_legend=self.show_legend_var.get(),
            legend_position=self.legend_position.get(),
            legend_fontsize=legend_fontsize,
            legend_columns=legend_columns,
            legend_framealpha=0.7 if self.legend_framealpha_var.get() else 1.0,
            graph_title=self.graph_title.get().strip() or "Sensor Time Series",
            x_label=self.xlabel.get().strip() or self.time_col or "Time",
            left_y_label=self.left_ylabel.get().strip() or "Left axis",
            right_y_label=self.right_ylabel.get().strip() or "Right axis",
            show_watermark=self.watermark_var.get(),
            start_time=self.start_entry.get().strip() or None,
            end_time=self.end_entry.get().strip() or None,
        )
        
        # Call the plotter
        try:
            self.ax_left = self.plotter.plot(
                self.df,
                self.time_col,
                left_cols,
                right_cols,
                options,
                self.series_properties,
                self.column_to_display,
            )
            
            # Copy the last series lines reference for the customize dialog
            self.last_series_lines = self.plotter.last_series_lines
            
            # Update hover handler and time selector with new axes
            self.hover_handler.ax_left = self.ax_left
            self.hover_handler.time_selection_lines = self.time_selector.get_selection_lines()
            self.time_selector.ax_left = self.ax_left
            
            # Draw the canvas
            self.canvas.draw()
            
            # Update status
            df_filtered = self.df.copy()
            if options.start_time or options.end_time:
                time_col_to_filter = '_plot_time' if '_plot_time' in df_filtered.columns else self.time_col
                if options.start_time:
                    start_time = pd.to_datetime(options.start_time)
                    if start_time.tzinfo is None:
                        start_time = start_time.tz_localize(self.display_tz)
                    df_filtered = df_filtered[df_filtered[time_col_to_filter] >= start_time]
                if options.end_time:
                    end_time = pd.to_datetime(options.end_time)
                    if end_time.tzinfo is None:
                        end_time = end_time.tz_localize(self.display_tz)
                    df_filtered = df_filtered[df_filtered[time_col_to_filter] <= end_time]
            
            self.status.set(f"Plotted {len(left_cols)} left + {len(right_cols)} right series ({len(df_filtered)} points)")
            
        except ValueError as e:
            messagebox.showerror("Plot Error", str(e))
        except Exception as e:
            messagebox.showerror("Plot Error", f"An error occurred while plotting:\n{str(e)}")
            import traceback
            traceback.print_exc()

def main() -> None:
    app = SensorDashboardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
