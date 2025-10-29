"""CO2 capture calculation control panel.

Contains all controls for CO2 capture mass balance calculation including
column selection, thermodynamic parameters, and result display.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    pass


class CO2CalculationPanel:
    """Panel for CO2 capture calculation with no-leak assumption."""
    
    def __init__(
        self,
        parent: ttk.Frame,
        app: tk.Tk,
        combo_width: int = 25,
        on_vm_update: Callable[[], None] = None,
        on_quick_plot: Callable[[], None] = None,
        on_calculate: Callable[[], None] = None,
    ):
        """Initialize the CO2 calculation panel.
        
        Args:
            parent: Parent frame to place this panel in
            app: Reference to main app for accessing variables/methods
            combo_width: Width of combo boxes
            on_vm_update: Callback when Vm parameters change
            on_quick_plot: Callback for quick plot button
            on_calculate: Callback for calculate button
        """
        self.app = app
        self.on_vm_update = on_vm_update
        self.on_quick_plot = on_quick_plot
        self.on_calculate = on_calculate
        
        self.frame = ttk.LabelFrame(
            parent,
            text="CO₂ Capture Calculation (No-leak assumption: F_out = F_in)"
        )
        
        # Column selection section
        col_select = ttk.Frame(self.frame)
        col_select.pack(side=tk.LEFT, padx=6, pady=6)
        
        # Inlet CO2
        ttk.Label(col_select, text="Inlet CO₂ (ppm):").grid(
            row=0, column=0, sticky="e", padx=4, pady=2
        )
        self.inlet_co2_combo = ttk.Combobox(col_select, width=combo_width, state="readonly")
        self.inlet_co2_combo.grid(row=0, column=1, padx=4, pady=2)
        
        # Outlet CO2
        ttk.Label(col_select, text="Outlet CO₂ (ppm):").grid(
            row=1, column=0, sticky="e", padx=4, pady=2
        )
        self.outlet_co2_combo = ttk.Combobox(col_select, width=combo_width, state="readonly")
        self.outlet_co2_combo.grid(row=1, column=1, padx=4, pady=2)
        
        # Flow rate
        ttk.Label(col_select, text="Flow Rate (SLPM):").grid(
            row=2, column=0, sticky="e", padx=4, pady=2
        )
        self.inlet_flow_combo = ttk.Combobox(col_select, width=combo_width, state="readonly")
        self.inlet_flow_combo.grid(row=2, column=1, padx=4, pady=2)
        
        # Parameters section
        param_calc = ttk.Frame(self.frame)
        param_calc.pack(side=tk.LEFT, padx=6, pady=6)
        
        # Temperature
        ttk.Label(param_calc, text="Temperature (°C):").grid(
            row=0, column=0, sticky="e", padx=4, pady=2
        )
        self.temp_entry = ttk.Entry(param_calc, width=8)
        self.temp_entry.insert(0, "25")
        self.temp_entry.grid(row=0, column=1, padx=4, pady=2)
        self.temp_entry.bind("<KeyRelease>", lambda e: self._on_vm_param_changed())
        
        # Pressure
        ttk.Label(param_calc, text="Pressure:").grid(
            row=1, column=0, sticky="e", padx=4, pady=2
        )
        pressure_frame = ttk.Frame(param_calc)
        pressure_frame.grid(row=1, column=1, sticky="w", padx=4, pady=2)
        
        self.pressure_entry = ttk.Entry(pressure_frame, width=8)
        self.pressure_entry.insert(0, "1.0")
        self.pressure_entry.pack(side=tk.LEFT, padx=(0, 2))
        self.pressure_entry.bind("<KeyRelease>", lambda e: self._on_vm_param_changed())
        
        self.pressure_unit_combo = ttk.Combobox(pressure_frame, width=5, state="readonly")
        self.pressure_unit_combo['values'] = ("atm", "psi")
        self.pressure_unit_combo.current(0)  # Default to atm
        self.pressure_unit_combo.pack(side=tk.LEFT)
        self.pressure_unit_combo.bind("<<ComboboxSelected>>", lambda e: self._on_vm_param_changed())
        
        # Compressibility
        ttk.Label(param_calc, text="Compressibility (Z):").grid(
            row=2, column=0, sticky="e", padx=4, pady=2
        )
        self.z_entry = ttk.Entry(param_calc, width=8)
        self.z_entry.insert(0, "1.0")
        self.z_entry.grid(row=2, column=1, padx=4, pady=2)
        ttk.Label(
            param_calc,
            text="(1.0 for air, ideal)",
            font=("TkDefaultFont", 7),
            foreground="gray"
        ).grid(row=2, column=2, sticky="w", padx=4, pady=2)
        self.z_entry.bind("<KeyRelease>", lambda e: self._on_vm_param_changed())
        
        # Vm display
        ttk.Label(
            param_calc,
            text="Vm (L/mol):",
            font=("TkDefaultFont", 9, "bold")
        ).grid(row=3, column=0, sticky="e", padx=4, pady=4)
        self.vm_display = ttk.Label(
            param_calc,
            text="24.465",
            font=("TkDefaultFont", 9, "bold"),
            foreground="darkblue"
        )
        self.vm_display.grid(row=3, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(
            param_calc,
            text="(calculated)",
            font=("TkDefaultFont", 7),
            foreground="gray"
        ).grid(row=3, column=2, sticky="w", padx=4, pady=4)
        
        # Buttons
        btn_frame = ttk.Frame(param_calc)
        btn_frame.grid(row=4, column=0, columnspan=3, padx=4, pady=6)
        ttk.Button(
            btn_frame,
            text="Quick Plot Sensors",
            command=self._on_quick_plot_clicked
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            btn_frame,
            text="Calculate CO₂ Captured",
            command=self._on_calculate_clicked
        ).pack(side=tk.LEFT, padx=2)
        
        # Results section
        result_frame = ttk.Frame(self.frame)
        result_frame.pack(side=tk.LEFT, padx=6, pady=6)
        
        self.co2_result_var = tk.StringVar(value="No calculation yet")
        result_label = ttk.Label(
            result_frame,
            textvariable=self.co2_result_var,
            font=("TkDefaultFont", 10, "bold"),
            foreground="darkgreen"
        )
        result_label.pack(padx=4, pady=4)
    
    def _on_vm_param_changed(self) -> None:
        """Handle Vm parameter change."""
        if self.on_vm_update:
            self.on_vm_update()
    
    def _on_quick_plot_clicked(self) -> None:
        """Handle quick plot button click."""
        if self.on_quick_plot:
            self.on_quick_plot()
    
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

