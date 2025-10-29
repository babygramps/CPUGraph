"""Series selector control panel.

Contains left and right axis listboxes with filtering and selection controls.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable, Dict, List, Set

if TYPE_CHECKING:
    pass


class SeriesSelector:
    """Panel for selecting series for left and right Y-axes."""
    
    def __init__(
        self,
        parent: ttk.Frame,
        app: tk.Tk,
        listbox_width: int = 40,
        on_filter_focus_in: Callable[[ttk.Entry], None] = None,
        on_filter_focus_out: Callable[[ttk.Entry], None] = None,
        on_filter_keyrelease: Callable[[str], None] = None,
        on_selection_changed: Callable[[str], None] = None,
        on_select_all: Callable[[str], None] = None,
        on_deselect_all: Callable[[str], None] = None,
    ):
        """Initialize the series selector panel.
        
        Args:
            parent: Parent frame to place this panel in
            app: Reference to main app for accessing variables/methods
            listbox_width: Width of listboxes in characters
            on_filter_focus_in: Callback when filter gets focus
            on_filter_focus_out: Callback when filter loses focus
            on_filter_keyrelease: Callback when user types in filter
            on_selection_changed: Callback when selection changes
            on_select_all: Callback for select all button
            on_deselect_all: Callback for deselect all button
        """
        self.app = app
        self.on_filter_focus_in = on_filter_focus_in
        self.on_filter_focus_out = on_filter_focus_out
        self.on_filter_keyrelease = on_filter_keyrelease
        self.on_selection_changed = on_selection_changed
        self.on_select_all = on_select_all
        self.on_deselect_all = on_deselect_all
        
        self.frame = ttk.LabelFrame(parent, text="Series Selection")
        
        # Left axis controls
        ttk.Label(self.frame, text="Left Y-axis").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        
        # Left filter
        self.left_filter = ttk.Entry(self.frame, width=listbox_width)
        self.left_filter.grid(row=1, column=0, padx=4, pady=2)
        self.left_filter.insert(0, "Filter...")
        self.left_filter.bind("<FocusIn>", lambda e: self._on_focus_in(self.left_filter))
        self.left_filter.bind("<FocusOut>", lambda e: self._on_focus_out(self.left_filter))
        self.left_filter.bind("<KeyRelease>", lambda e: self._on_keyrelease("left"))
        
        # Left buttons
        left_btn_frame = ttk.Frame(self.frame)
        left_btn_frame.grid(row=2, column=0, sticky="w", padx=4, pady=2)
        ttk.Button(
            left_btn_frame, text="Select All",
            command=lambda: self._on_select_all_clicked("left"),
            width=12
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            left_btn_frame, text="Deselect All",
            command=lambda: self._on_deselect_all_clicked("left"),
            width=12
        ).pack(side=tk.LEFT, padx=2)
        ttk.Label(
            left_btn_frame,
            text="(Ctrl+Click, Shift+Click)",
            font=("TkDefaultFont", 7),
            foreground="gray"
        ).pack(side=tk.LEFT, padx=4)
        
        # Left listbox
        self.left_list = tk.Listbox(
            self.frame,
            selectmode=tk.EXTENDED,
            width=listbox_width,
            height=10,
            exportselection=False
        )
        self.left_list.grid(row=3, column=0, padx=4, pady=2)
        self.left_list.bind("<<ListboxSelect>>", lambda e: self._on_selection_changed("left"))
        
        # Right axis controls
        ttk.Label(self.frame, text="Right Y-axis").grid(row=0, column=1, sticky="w", padx=4, pady=2)
        
        # Right filter
        self.right_filter = ttk.Entry(self.frame, width=listbox_width)
        self.right_filter.grid(row=1, column=1, padx=4, pady=2)
        self.right_filter.insert(0, "Filter...")
        self.right_filter.bind("<FocusIn>", lambda e: self._on_focus_in(self.right_filter))
        self.right_filter.bind("<FocusOut>", lambda e: self._on_focus_out(self.right_filter))
        self.right_filter.bind("<KeyRelease>", lambda e: self._on_keyrelease("right"))
        
        # Right buttons
        right_btn_frame = ttk.Frame(self.frame)
        right_btn_frame.grid(row=2, column=1, sticky="w", padx=4, pady=2)
        ttk.Button(
            right_btn_frame, text="Select All",
            command=lambda: self._on_select_all_clicked("right"),
            width=12
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            right_btn_frame, text="Deselect All",
            command=lambda: self._on_deselect_all_clicked("right"),
            width=12
        ).pack(side=tk.LEFT, padx=2)
        ttk.Label(
            right_btn_frame,
            text="(Ctrl+Click, Shift+Click)",
            font=("TkDefaultFont", 7),
            foreground="gray"
        ).pack(side=tk.LEFT, padx=4)
        
        # Right listbox
        self.right_list = tk.Listbox(
            self.frame,
            selectmode=tk.EXTENDED,
            width=listbox_width,
            height=10,
            exportselection=False
        )
        self.right_list.grid(row=3, column=1, padx=4, pady=2)
        self.right_list.bind("<<ListboxSelect>>", lambda e: self._on_selection_changed("right"))
    
    def _on_focus_in(self, entry: ttk.Entry) -> None:
        """Handle filter entry focus in."""
        if self.on_filter_focus_in:
            self.on_filter_focus_in(entry)
    
    def _on_focus_out(self, entry: ttk.Entry) -> None:
        """Handle filter entry focus out."""
        if self.on_filter_focus_out:
            self.on_filter_focus_out(entry)
    
    def _on_keyrelease(self, side: str) -> None:
        """Handle filter keyrelease."""
        if self.on_filter_keyrelease:
            self.on_filter_keyrelease(side)
    
    def _on_selection_changed(self, side: str) -> None:
        """Handle listbox selection change."""
        if self.on_selection_changed:
            self.on_selection_changed(side)
    
    def _on_select_all_clicked(self, side: str) -> None:
        """Handle select all button click."""
        if self.on_select_all:
            self.on_select_all(side)
    
    def _on_deselect_all_clicked(self, side: str) -> None:
        """Handle deselect all button click."""
        if self.on_deselect_all:
            self.on_deselect_all(side)
    
    def pack(self, **kwargs) -> None:
        """Pack the frame with given options."""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """Grid the frame with given options."""
        self.frame.grid(**kwargs)

