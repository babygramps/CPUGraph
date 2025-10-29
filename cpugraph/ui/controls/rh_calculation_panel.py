"""Relative humidity calculation control panel.

Contains controls for calculating relative humidity from temperature and dew point
transmitters using the Magnus-Tetens formula.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    pass


class RHCalculationPanel:
    """Panel for relative humidity calculation from temperature and dew point."""
    
    def __init__(
        self,
        parent: ttk.Frame,
        app: tk.Tk,
        combo_width: int = 25,
        on_quick_plot: Callable[[], None] = None,
        on_calculate: Callable[[], None] = None,
        on_plot_rh: Callable[[], None] = None,
    ):
        """Initialize the RH calculation panel.
        
        Args:
            parent: Parent frame to place this panel in
            app: Reference to main app for accessing variables/methods
            combo_width: Width of combo boxes
            on_quick_plot: Callback for quick plot button
            on_calculate: Callback for calculate button
            on_plot_rh: Callback for plot RH time series button
        """
        self.app = app
        self.on_quick_plot = on_quick_plot
        self.on_calculate = on_calculate
        self.on_plot_rh = on_plot_rh
        
        self.frame = ttk.LabelFrame(
            parent,
            text="Relative Humidity Calculation (from Temperature & Dew Point)"
        )
        
        # Main container with elegant layout
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Left side: Column selection
        col_select = ttk.Frame(main_container)
        col_select.pack(side=tk.LEFT, padx=6, pady=4)
        
        # Presets dropdown
        ttk.Label(col_select, text="Quick Presets:").grid(
            row=0, column=0, sticky="e", padx=4, pady=4
        )
        self.preset_combo = ttk.Combobox(col_select, width=combo_width, state="readonly")
        self.preset_combo['values'] = ("-- Select Preset --", "Compressed Air", "Contactor")
        self.preset_combo.current(0)
        self.preset_combo.grid(row=0, column=1, padx=4, pady=4)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)
        
        # Temperature transmitter
        ttk.Label(col_select, text="Temperature (°C):").grid(
            row=1, column=0, sticky="e", padx=4, pady=4
        )
        self.temp_combo = ttk.Combobox(col_select, width=combo_width, state="readonly")
        self.temp_combo.grid(row=1, column=1, padx=4, pady=4)
        
        # Dew point transmitter
        ttk.Label(col_select, text="Dew Point (°C):").grid(
            row=2, column=0, sticky="e", padx=4, pady=4
        )
        self.dewpoint_combo = ttk.Combobox(col_select, width=combo_width, state="readonly")
        self.dewpoint_combo.grid(row=2, column=1, padx=4, pady=4)
        
        # Pressure transmitter (optional)
        ttk.Label(col_select, text="Pressure (optional):").grid(
            row=3, column=0, sticky="e", padx=4, pady=4
        )
        self.pressure_combo = ttk.Combobox(col_select, width=combo_width, state="readonly")
        self.pressure_combo.grid(row=3, column=1, padx=4, pady=4)
        ttk.Label(
            col_select,
            text="(for reference/logging)",
            font=("TkDefaultFont", 7),
            foreground="gray"
        ).grid(row=3, column=2, sticky="w", padx=2, pady=4)
        
        # Middle: Buttons
        btn_frame = ttk.Frame(main_container)
        btn_frame.pack(side=tk.LEFT, padx=10, pady=4)
        
        ttk.Button(
            btn_frame,
            text="📊 Quick Plot",
            command=self._on_quick_plot_clicked,
            width=16
        ).pack(pady=3)
        
        ttk.Button(
            btn_frame,
            text="📈 Plot RH Line",
            command=self._on_plot_rh_clicked,
            width=16
        ).pack(pady=3)
        
        ttk.Button(
            btn_frame,
            text="🧮 Calculate Stats",
            command=self._on_calculate_clicked,
            width=16
        ).pack(pady=3)
        
        # Right side: Results display
        result_container = ttk.Frame(main_container)
        result_container.pack(side=tk.LEFT, padx=10, pady=4, fill=tk.BOTH, expand=True)
        
        # Results header
        ttk.Label(
            result_container,
            text="Results:",
            font=("TkDefaultFont", 9, "bold")
        ).pack(anchor="w", pady=(0, 4))
        
        # Results display
        self.rh_result_var = tk.StringVar(value="Select transmitters and calculate")
        result_label = ttk.Label(
            result_container,
            textvariable=self.rh_result_var,
            font=("TkDefaultFont", 10),
            foreground="darkblue",
            wraplength=300,
            justify=tk.LEFT
        )
        result_label.pack(anchor="w", fill=tk.BOTH, expand=True)
        
        # Info label with formula explanation
        info_text = "Magnus-Tetens formula: RH = 100 × e(Td)/e(T)"
        ttk.Label(
            self.frame,
            text=info_text,
            font=("TkDefaultFont", 7),
            foreground="gray"
        ).pack(side=tk.BOTTOM, pady=(0, 4))
    
    def _on_preset_selected(self, event=None) -> None:
        """Handle preset selection."""
        preset = self.preset_combo.get()
        if preset == "-- Select Preset --":
            return
        
        # Notify the app to apply the preset
        if hasattr(self.app, 'apply_rh_preset'):
            self.app.apply_rh_preset(preset)
    
    def _on_quick_plot_clicked(self) -> None:
        """Handle quick plot button click."""
        if self.on_quick_plot:
            self.on_quick_plot()
    
    def _on_plot_rh_clicked(self) -> None:
        """Handle plot RH line button click."""
        if self.on_plot_rh:
            self.on_plot_rh()
    
    def _on_calculate_clicked(self) -> None:
        """Handle calculate button click."""
        if self.on_calculate:
            self.on_calculate()
    
    def pack(self, **kwargs) -> None:
        """Pack the frame with given options."""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """Grid the frame with given options."""
        self.frame.grid(**kwargs)

