"""Series selector control panel.

Contains left and right axis listboxes with filtering and selection controls.
Delegates all selection state management to SelectionManager.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.selection import SeriesSelectionManager


class SeriesSelector:
    """Panel for selecting series for left and right Y-axes.
    
    This is a pure UI component that delegates all selection logic
    to a SelectionManager instance.
    """
    
    def __init__(
        self,
        parent: ttk.Frame,
        app: tk.Tk,
        selection_manager: 'SeriesSelectionManager',
        listbox_width: int = 40,
    ):
        """Initialize the series selector panel.
        
        Args:
            parent: Parent frame to place this panel in
            app: Reference to main app for accessing variables/methods
            selection_manager: Selection state manager instance
            listbox_width: Width of listboxes in characters
        """
        self.app = app
        self.selection_mgr = selection_manager
        
        self.frame = ttk.LabelFrame(parent, text="Series Selection")
        
        # Left axis controls
        ttk.Label(self.frame, text="Left Y-axis").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        
        # Left filter
        self.left_filter = ttk.Entry(self.frame, width=listbox_width)
        self.left_filter.grid(row=1, column=0, padx=4, pady=2)
        self.left_filter.insert(0, "Filter...")
        self.left_filter.bind("<FocusIn>", lambda e: self.selection_mgr.on_filter_focus_in(self.left_filter))
        self.left_filter.bind("<FocusOut>", lambda e: self.selection_mgr.on_filter_focus_out(self.left_filter))
        self.left_filter.bind("<KeyRelease>", lambda e: self.selection_mgr.filter_listbox("left", self.left_list, self.left_filter))
        
        # Left buttons
        left_btn_frame = ttk.Frame(self.frame)
        left_btn_frame.grid(row=2, column=0, sticky="w", padx=4, pady=2)
        ttk.Button(
            left_btn_frame, text="Select All",
            command=lambda: self.selection_mgr.select_all("left", self.left_list),
            width=12
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            left_btn_frame, text="Deselect All",
            command=lambda: self.selection_mgr.deselect_all("left", self.left_list),
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
        self.left_list.bind("<<ListboxSelect>>", lambda e: self.selection_mgr.update_selection_tracking("left", self.left_list))
        
        # Right axis controls
        ttk.Label(self.frame, text="Right Y-axis").grid(row=0, column=1, sticky="w", padx=4, pady=2)
        
        # Right filter
        self.right_filter = ttk.Entry(self.frame, width=listbox_width)
        self.right_filter.grid(row=1, column=1, padx=4, pady=2)
        self.right_filter.insert(0, "Filter...")
        self.right_filter.bind("<FocusIn>", lambda e: self.selection_mgr.on_filter_focus_in(self.right_filter))
        self.right_filter.bind("<FocusOut>", lambda e: self.selection_mgr.on_filter_focus_out(self.right_filter))
        self.right_filter.bind("<KeyRelease>", lambda e: self.selection_mgr.filter_listbox("right", self.right_list, self.right_filter))
        
        # Right buttons
        right_btn_frame = ttk.Frame(self.frame)
        right_btn_frame.grid(row=2, column=1, sticky="w", padx=4, pady=2)
        ttk.Button(
            right_btn_frame, text="Select All",
            command=lambda: self.selection_mgr.select_all("right", self.right_list),
            width=12
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            right_btn_frame, text="Deselect All",
            command=lambda: self.selection_mgr.deselect_all("right", self.right_list),
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
        self.right_list.bind("<<ListboxSelect>>", lambda e: self.selection_mgr.update_selection_tracking("right", self.right_list))
    
    def pack(self, **kwargs) -> None:
        """Pack the frame with given options."""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """Grid the frame with given options."""
        self.frame.grid(**kwargs)

