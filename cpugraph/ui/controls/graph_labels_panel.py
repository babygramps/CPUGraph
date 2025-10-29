"""Graph labels control panel.

Contains controls for graph title and axis labels.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class GraphLabelsPanel:
    """Panel for graph title and axis label customization."""
    
    def __init__(self, parent: ttk.Frame, app: tk.Tk, label_entry_width: int = 20):
        """Initialize the graph labels panel.
        
        Args:
            parent: Parent frame to place this panel in
            app: Reference to main app for accessing variables/methods
            label_entry_width: Width of entry fields
        """
        self.app = app
        self.frame = ttk.LabelFrame(parent, text="Graph Labels")
        
        # Graph title
        ttk.Label(self.frame, text="Graph Title:").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.graph_title = ttk.Entry(self.frame, width=label_entry_width)
        self.graph_title.insert(0, "Sensor Time Series")
        self.graph_title.grid(row=1, column=0, padx=4, pady=2)
        
        # Left Y-axis label
        ttk.Label(self.frame, text="Left Y-axis label:").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.left_ylabel = ttk.Entry(self.frame, width=label_entry_width)
        self.left_ylabel.insert(0, "Left axis")
        self.left_ylabel.grid(row=3, column=0, padx=4, pady=2)
        
        # Right Y-axis label
        ttk.Label(self.frame, text="Right Y-axis label:").grid(row=4, column=0, sticky="w", padx=4, pady=2)
        self.right_ylabel = ttk.Entry(self.frame, width=label_entry_width)
        self.right_ylabel.insert(0, "Right axis")
        self.right_ylabel.grid(row=5, column=0, padx=4, pady=2)
        
        # X-axis label
        ttk.Label(self.frame, text="X-axis label:").grid(row=6, column=0, sticky="w", padx=4, pady=2)
        self.xlabel = ttk.Entry(self.frame, width=label_entry_width)
        self.xlabel.insert(0, "Time")
        self.xlabel.grid(row=7, column=0, padx=4, pady=2)
    
    def pack(self, **kwargs) -> None:
        """Pack the frame with given options."""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """Grid the frame with given options."""
        self.frame.grid(**kwargs)

