"""Plot options control panel.

Contains controls for grid, smoothing, and watermark options.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class PlotOptionsPanel:
    """Panel for plot display options (grid, smoothing, watermark)."""
    
    def __init__(self, parent: ttk.Frame, app: tk.Tk):
        """Initialize the plot options panel.
        
        Args:
            parent: Parent frame to place this panel in
            app: Reference to main app for accessing variables/methods
        """
        self.app = app
        self.frame = ttk.LabelFrame(parent, text="Plot Options")
        
        # Grid checkbox
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.frame, text="Show grid",
            variable=self.grid_var
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        
        # Smoothing checkbox
        self.smooth_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.frame, text="Moving-average smoothing",
            variable=self.smooth_var,
            command=self._toggle_smooth
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        
        # Smoothing window entry
        ttk.Label(self.frame, text="Window (samples):").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.window_entry = ttk.Entry(self.frame, width=8)
        self.window_entry.insert(0, "21")
        self.window_entry.grid(row=2, column=1, sticky="w", padx=4, pady=2)
        self.window_entry.state(["disabled"])
        
        # Watermark checkbox
        self.watermark_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.frame, text="Show watermark",
            variable=self.watermark_var
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=2)
    
    def _toggle_smooth(self) -> None:
        """Enable/disable smoothing window entry based on checkbox."""
        if self.smooth_var.get():
            self.window_entry.state(["!disabled"])
        else:
            self.window_entry.state(["disabled"])
    
    def pack(self, **kwargs) -> None:
        """Pack the frame with given options."""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """Grid the frame with given options."""
        self.frame.grid(**kwargs)

