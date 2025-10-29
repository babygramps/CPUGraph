"""Time window control panel.

Contains controls for selecting time range, time selection mode, and mode filtering.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable, List, Dict, Tuple
import pandas as pd

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
        
        # Track available modes
        self.available_modes: List[str] = []
        self.mode_time_ranges: Dict[str, List[Tuple[pd.Timestamp, pd.Timestamp]]] = {}
        
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
        
        # Mode Filter Section (initially hidden, shown when Mode column exists)
        self.mode_frame = ttk.LabelFrame(self.frame, text="Filter by Mode")
        self.mode_frame.grid(row=3, column=0, columnspan=2, padx=4, pady=6, sticky="ew")
        self.mode_frame.grid_remove()  # Hide initially
        
        # Mode selection listbox with scrollbar
        mode_list_frame = ttk.Frame(self.mode_frame)
        mode_list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        
        mode_scrollbar = ttk.Scrollbar(mode_list_frame)
        mode_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.mode_listbox = tk.Listbox(
            mode_list_frame,
            selectmode=tk.MULTIPLE,
            height=6,
            width=label_entry_width,
            yscrollcommand=mode_scrollbar.set,
            exportselection=False
        )
        self.mode_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mode_scrollbar.config(command=self.mode_listbox.yview)
        
        # Bind selection change to update time ranges
        self.mode_listbox.bind('<<ListboxSelect>>', self._on_mode_selection_changed)
        
        # Mode action buttons
        mode_btn_frame = ttk.Frame(self.mode_frame)
        mode_btn_frame.pack(fill=tk.X, padx=4, pady=4)
        
        ttk.Button(
            mode_btn_frame,
            text="Select All",
            command=self._select_all_modes
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            mode_btn_frame,
            text="Clear All",
            command=self._clear_all_modes
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            mode_btn_frame,
            text="Apply Mode Filter",
            command=self._apply_mode_filter
        ).pack(side=tk.LEFT, padx=2)
        
        # Time ranges info label (shows when modes are selected)
        self.time_ranges_label = tk.Text(
            self.mode_frame,
            height=4,
            width=label_entry_width,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("TkDefaultFont", 8)
        )
        self.time_ranges_label.pack(fill=tk.X, padx=4, pady=4)
    
    def update_available_modes(self, df: pd.DataFrame, time_column: str, mode_column: str = "Mode") -> None:
        """Update the available modes based on loaded data.
        
        Args:
            df: DataFrame containing the data
            time_column: Name of the time column
            mode_column: Name of the mode column (default: "Mode")
        """
        if mode_column not in df.columns:
            # No mode column, hide mode filtering UI
            self.mode_frame.grid_remove()
            self.available_modes = []
            self.mode_time_ranges = {}
            print("[Mode Filter] No 'Mode' column found, mode filtering disabled")
            return
        
        # Get time column to use (prefer _plot_time if available)
        time_col = "_plot_time" if "_plot_time" in df.columns else time_column
        
        # Extract unique modes
        unique_modes = df[mode_column].dropna().unique().tolist()
        unique_modes = [str(m).strip() for m in unique_modes if str(m).strip()]
        unique_modes.sort()
        
        self.available_modes = unique_modes
        
        # Calculate time ranges for each mode
        self.mode_time_ranges = {}
        for mode in unique_modes:
            mode_df = df[df[mode_column] == mode]
            if not mode_df.empty:
                # Find continuous time ranges for this mode
                time_ranges = []
                current_start = None
                prev_time = None
                
                for idx, row in mode_df.iterrows():
                    curr_time = row[time_col]
                    
                    if current_start is None:
                        # Start of a new range
                        current_start = curr_time
                        prev_time = curr_time
                    elif prev_time is not None:
                        # Check if there's a gap (>5 minutes indicates separate occurrences)
                        time_diff = (curr_time - prev_time).total_seconds() / 60
                        if time_diff > 5:  # 5 minute gap threshold
                            # End previous range and start new one
                            time_ranges.append((current_start, prev_time))
                            current_start = curr_time
                    
                    prev_time = curr_time
                
                # Add the last range
                if current_start is not None and prev_time is not None:
                    time_ranges.append((current_start, prev_time))
                
                self.mode_time_ranges[mode] = time_ranges
        
        # Update listbox
        self.mode_listbox.delete(0, tk.END)
        for mode in self.available_modes:
            num_occurrences = len(self.mode_time_ranges.get(mode, []))
            display_text = f"{mode} ({num_occurrences} occurrence{'s' if num_occurrences != 1 else ''})"
            self.mode_listbox.insert(tk.END, display_text)
        
        # Show mode filtering UI
        self.mode_frame.grid()
        
        print(f"[Mode Filter] Found {len(unique_modes)} unique modes: {', '.join(unique_modes)}")
        for mode in unique_modes:
            ranges = self.mode_time_ranges.get(mode, [])
            print(f"[Mode Filter]   {mode}: {len(ranges)} occurrence(s)")
    
    def _on_mode_selection_changed(self, event=None) -> None:
        """Update time ranges display when mode selection changes."""
        selected_indices = self.mode_listbox.curselection()
        if not selected_indices:
            self._update_time_ranges_display("")
            return
        
        # Get selected modes
        selected_modes = [self.available_modes[i] for i in selected_indices]
        
        # Build time ranges text
        info_lines = []
        info_lines.append(f"Selected {len(selected_modes)} mode(s):\n")
        
        for mode in selected_modes:
            ranges = self.mode_time_ranges.get(mode, [])
            if len(ranges) == 1:
                start, end = ranges[0]
                info_lines.append(f"• {mode}:")
                info_lines.append(f"  {start.strftime('%m/%d %I:%M %p')} - {end.strftime('%I:%M %p')}")
            else:
                info_lines.append(f"• {mode} ({len(ranges)} occurrences):")
                for i, (start, end) in enumerate(ranges[:3], 1):  # Show first 3
                    info_lines.append(f"  #{i}: {start.strftime('%m/%d %I:%M %p')} - {end.strftime('%I:%M %p')}")
                if len(ranges) > 3:
                    info_lines.append(f"  ... and {len(ranges) - 3} more")
        
        self._update_time_ranges_display("\n".join(info_lines))
    
    def _update_time_ranges_display(self, text: str) -> None:
        """Update the time ranges information display.
        
        Args:
            text: Text to display
        """
        self.time_ranges_label.config(state=tk.NORMAL)
        self.time_ranges_label.delete(1.0, tk.END)
        self.time_ranges_label.insert(1.0, text)
        self.time_ranges_label.config(state=tk.DISABLED)
    
    def _select_all_modes(self) -> None:
        """Select all modes in the listbox."""
        self.mode_listbox.select_set(0, tk.END)
        self._on_mode_selection_changed()
    
    def _clear_all_modes(self) -> None:
        """Clear all mode selections."""
        self.mode_listbox.selection_clear(0, tk.END)
        self._on_mode_selection_changed()
    
    def _apply_mode_filter(self) -> None:
        """Apply the selected mode filter to update time window."""
        selected_indices = self.mode_listbox.curselection()
        if not selected_indices:
            print("[Mode Filter] No modes selected")
            return
        
        # Get selected modes
        selected_modes = [self.available_modes[i] for i in selected_indices]
        
        # Collect all time ranges for selected modes
        all_ranges = []
        for mode in selected_modes:
            all_ranges.extend(self.mode_time_ranges.get(mode, []))
        
        if not all_ranges:
            print("[Mode Filter] No time ranges found for selected modes")
            return
        
        # Sort ranges by start time
        all_ranges.sort(key=lambda x: x[0])
        
        # Set start time to earliest range
        earliest_start = min(r[0] for r in all_ranges)
        latest_end = max(r[1] for r in all_ranges)
        
        # Update start/end entry fields
        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(0, earliest_start.strftime('%m/%d/%Y %I:%M:%S %p'))
        
        self.end_entry.delete(0, tk.END)
        self.end_entry.insert(0, latest_end.strftime('%m/%d/%Y %I:%M:%S %p'))
        
        # Log the filtering
        print(f"[Mode Filter] Applied filter for modes: {', '.join(selected_modes)}")
        print(f"[Mode Filter] Time range: {earliest_start.strftime('%m/%d/%Y %I:%M %p')} - {latest_end.strftime('%I:%M %p')}")
        
        if len(all_ranges) > 1:
            print(f"[Mode Filter] Note: Selected modes have {len(all_ranges)} separate time ranges")
            print(f"[Mode Filter] Showing full span. Use 'Plot' to visualize (gaps will be visible)")
    
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

