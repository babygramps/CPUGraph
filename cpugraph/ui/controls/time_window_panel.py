"""Time window control panel.

Contains controls for selecting time range and time selection mode.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    pass


class TimeWindowPanel:
    """Panel for time window filtering and selection."""
    
    def __init__(
        self,
        parent: ttk.Frame,
        app: tk.Tk,
        label_entry_width: int = 20,
        toggle_time_selection_callback: Callable[[], None] = None,
        clear_time_selection_callback: Callable[[], None] = None,
    ):
        """Initialize the time window panel.
        
        Args:
            parent: Parent frame to place this panel in
            app: Reference to main app for accessing variables/methods
            label_entry_width: Width of entry fields
            toggle_time_selection_callback: Callback for toggle time selection button
            clear_time_selection_callback: Callback for clear selection button
        """
        self.app = app
        self.toggle_callback = toggle_time_selection_callback
        self.clear_callback = clear_time_selection_callback
        
        self.frame = ttk.LabelFrame(parent, text="Time Window (optional, PST timezone)")
        
        # Start time
        ttk.Label(self.frame, text="Start:").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        self.start_entry = ttk.Entry(self.frame, width=label_entry_width)
        self.start_entry.grid(row=0, column=1, padx=4, pady=2)
        
        # End time
        ttk.Label(self.frame, text="End:").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        self.end_entry = ttk.Entry(self.frame, width=label_entry_width)
        self.end_entry.grid(row=1, column=1, padx=4, pady=2)
        
        # Time selection buttons
        time_btn_frame = ttk.Frame(self.frame)
        time_btn_frame.grid(row=2, column=0, columnspan=2, padx=4, pady=6)
        
        self.time_select_btn = ttk.Button(
            time_btn_frame,
            text="Select Time Range",
            command=self._on_toggle_selection
        )
        self.time_select_btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            time_btn_frame,
            text="Clear Selection",
            command=self._on_clear_selection
        ).pack(side=tk.LEFT, padx=2)
    
    def _on_toggle_selection(self) -> None:
        """Handle toggle time selection button click."""
        if self.toggle_callback:
            self.toggle_callback()
    
    def _on_clear_selection(self) -> None:
        """Handle clear selection button click."""
        if self.clear_callback:
            self.clear_callback()
    
    def pack(self, **kwargs) -> None:
        """Pack the frame with given options."""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """Grid the frame with given options."""
        self.frame.grid(**kwargs)

