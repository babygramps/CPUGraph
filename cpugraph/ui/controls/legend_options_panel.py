"""Legend options control panel.

Contains controls for legend visibility, position, font size, columns, and transparency.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class LegendOptionsPanel:
    """Panel for legend customization options."""
    
    def __init__(self, parent: ttk.Frame, app: tk.Tk):
        """Initialize the legend options panel.
        
        Args:
            parent: Parent frame to place this panel in
            app: Reference to main app for accessing variables/methods
        """
        self.app = app
        self.frame = ttk.LabelFrame(parent, text="Legend Options")
        
        # Show legend checkbox
        self.show_legend_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.frame, text="Show legend",
            variable=self.show_legend_var
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        
        # Position
        ttk.Label(self.frame, text="Position:").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        self.legend_position = ttk.Combobox(self.frame, width=15, state="readonly")
        self.legend_position['values'] = (
            "Upper Left", "Upper Right", "Lower Left", "Lower Right",
            "Best", "Outside Right", "Outside Bottom"
        )
        self.legend_position.current(0)  # Default to "Upper Left"
        self.legend_position.grid(row=1, column=1, sticky="w", padx=4, pady=2)
        
        # Font size
        ttk.Label(self.frame, text="Font size:").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.legend_fontsize = ttk.Spinbox(self.frame, from_=4, to=20, width=8)
        self.legend_fontsize.set(8)  # Default font size
        self.legend_fontsize.grid(row=2, column=1, sticky="w", padx=4, pady=2)
        
        # Columns
        ttk.Label(self.frame, text="Columns:").grid(row=3, column=0, sticky="w", padx=4, pady=2)
        self.legend_columns = ttk.Spinbox(self.frame, from_=1, to=5, width=8)
        self.legend_columns.set(1)  # Default to single column
        self.legend_columns.grid(row=3, column=1, sticky="w", padx=4, pady=2)
        
        # Semi-transparent checkbox
        self.legend_framealpha_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.frame, text="Semi-transparent",
            variable=self.legend_framealpha_var
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=4, pady=2)
    
    def pack(self, **kwargs) -> None:
        """Pack the frame with given options."""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """Grid the frame with given options."""
        self.frame.grid(**kwargs)

