"""Series selection state and filtering management.

Handles selection tracking, filtering, and listbox population for the
left and right Y-axis series selectors. Provides a clean API for managing
which series are selected for plotting.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Set


class SeriesSelectionManager:
    """Manages selection state and filtering for series listboxes.
    
    This class encapsulates all logic related to:
    - Tracking selected items across filter changes
    - Filtering listboxes based on search text
    - Select all / deselect all operations
    - Converting between display names and column names
    """
    
    def __init__(
        self,
        all_columns: List[str],
        column_to_display: Dict[str, str],
        column_display_map: Dict[str, str] = None,
    ):
        """Initialize the selection manager.
        
        Args:
            all_columns: List of all available column names
            column_to_display: Mapping from actual column names to display names
            column_display_map: Optional reverse mapping (display to column names)
        """
        self.all_columns = all_columns
        self.column_to_display = column_to_display
        
        # Display name to column name mapping (reverse of column_to_display)
        if column_display_map is not None:
            self.column_display_map = column_display_map
        else:
            self.column_display_map = {v: k for k, v in column_to_display.items()}
        
        # Track selected items (as display names)
        self.left_selected: Set[str] = set()
        self.right_selected: Set[str] = set()
        
        print(f"[Selection Manager] Initialized with {len(all_columns)} columns")
    
    def update_columns(
        self,
        all_columns: List[str],
        column_to_display: Dict[str, str],
        column_display_map: Dict[str, str] = None,
    ) -> None:
        """Update the available columns (called when new file is loaded).
        
        Args:
            all_columns: New list of column names
            column_to_display: New display name mapping
            column_display_map: Optional reverse mapping (display to column names)
        """
        self.all_columns = all_columns
        self.column_to_display = column_to_display
        
        if column_display_map is not None:
            self.column_display_map = column_display_map
        else:
            self.column_display_map = {v: k for k, v in column_to_display.items()}
        
        self.left_selected.clear()
        self.right_selected.clear()
        
        print(f"[Selection Manager] Updated with {len(all_columns)} columns, selections cleared")
    
    def update_tracking(self, side: str, listbox: tk.Listbox) -> None:
        """Update the selection tracking set when user clicks on listbox items.
        
        This ensures selections/deselections are immediately tracked without
        waiting for the filter to refresh.
        
        Args:
            side: 'left' or 'right'
            listbox: The listbox widget to read from
        """
        selected_set = self.left_selected if side == "left" else self.right_selected
        
        # Update tracking with current selections (as display names)
        selected_set.clear()
        indices = listbox.curselection()
        for i in indices:
            item = listbox.get(i)
            # Skip separator lines
            if not item.startswith("─"):
                selected_set.add(item)
        
        # Log selection changes for debugging
        print(f"[Selection] {side.capitalize()} axis: {len(selected_set)} items selected")
    
    def filter_listbox(
        self,
        side: str,
        listbox: tk.Listbox,
        filter_entry: ttk.Entry,
    ) -> None:
        """Filter the listbox based on the search text.
        
        Previously selected items always remain visible and selected,
        even if they don't match the current filter. This provides a better
        UX where selections don't disappear when filtering.
        
        Args:
            side: 'left' or 'right'
            listbox: The listbox widget to populate
            filter_entry: The filter entry widget
        """
        if not self.all_columns:
            return
        
        selected_set = self.left_selected if side == "left" else self.right_selected
        
        # Update selected items tracking before clearing
        for idx in listbox.curselection():
            item = listbox.get(idx)
            if not item.startswith("─"):
                selected_set.add(item)
        
        # Get filter text
        filter_text = filter_entry.get().strip().lower()
        if filter_text == "filter...":
            filter_text = ""
        
        # Clear and repopulate listbox
        listbox.delete(0, tk.END)
        
        # Track items we've already added
        added_items = set()
        selected_count = 0
        matched_count = 0
        
        # FIRST: Add all previously selected items (always visible)
        for col in self.all_columns:
            display_name = self.column_to_display.get(col, col)
            if display_name in selected_set:
                listbox.insert(tk.END, display_name)
                listbox.selection_set(tk.END)
                added_items.add(display_name)
                selected_count += 1
        
        # Add separator if we have selected items and a filter is active
        if selected_count > 0 and filter_text:
            listbox.insert(tk.END, "─" * 40)
            added_items.add("─" * 40)
        
        # SECOND: Add filtered items (that aren't already selected)
        for col in self.all_columns:
            display_name = self.column_to_display.get(col, col)
            # Skip if already added, or if doesn't match filter
            if display_name in added_items:
                continue
            # Filter based on display name (which includes both column name and description)
            if not filter_text or filter_text in display_name.lower():
                listbox.insert(tk.END, display_name)
                matched_count += 1
        
        # Log filtering activity
        if filter_text:
            print(f"[Filter] {side.capitalize()} axis: '{filter_text}' matched {matched_count} new + {selected_count} selected = {matched_count + selected_count} total items")
        else:
            print(f"[Filter] {side.capitalize()} axis: No filter, showing all {len(self.all_columns)} columns ({selected_count} selected)")
    
    def select_all(self, side: str, listbox: tk.Listbox) -> None:
        """Select all visible items in the listbox.
        
        Args:
            side: 'left' or 'right'
            listbox: The listbox widget
        """
        selected_set = self.left_selected if side == "left" else self.right_selected
        
        # Select all visible items (except separator)
        count = 0
        for i in range(listbox.size()):
            item = listbox.get(i)
            if not item.startswith("─"):
                listbox.selection_set(i)
                selected_set.add(item)
                count += 1
        
        print(f"[Select All] {side.capitalize()} axis: Selected {count} visible columns")
    
    def deselect_all(self, side: str, listbox: tk.Listbox) -> None:
        """Deselect all items in the listbox.
        
        Args:
            side: 'left' or 'right'
            listbox: The listbox widget
        """
        selected_set = self.left_selected if side == "left" else self.right_selected
        
        # Get currently visible items to remove from tracking (skip separator)
        visible_items = [listbox.get(i) for i in range(listbox.size()) 
                        if not listbox.get(i).startswith("─")]
        
        # Clear selection
        listbox.selection_clear(0, tk.END)
        
        # Remove only visible items from tracking set
        for item in visible_items:
            selected_set.discard(item)
        
        print(f"[Deselect All] {side.capitalize()} axis: Deselected {len(visible_items)} visible columns")
    
    def get_selected_columns(self, side: str, listbox: tk.Listbox) -> List[str]:
        """Get selected items from a listbox and return actual column names.
        
        Updates tracking and converts display names to actual column names for plotting.
        
        Args:
            side: 'left' or 'right'
            listbox: The listbox widget
            
        Returns:
            List of actual column names (not display names)
        """
        selected_set = self.left_selected if side == "left" else self.right_selected
        
        # Update tracking with current selections (as display names)
        selected_set.clear()
        indices = listbox.curselection()
        for i in indices:
            item = listbox.get(i)
            # Skip separator lines
            if not item.startswith("─"):
                selected_set.add(item)
        
        # Convert display names to actual column names for plotting
        actual_columns = []
        for display_name in selected_set:
            # Skip separator lines (safety check)
            if display_name.startswith("─"):
                continue
            actual_col = self.column_display_map.get(display_name, display_name)
            actual_columns.append(actual_col)
        
        return actual_columns
    
    def on_filter_focus_in(self, entry: ttk.Entry) -> None:
        """Clear placeholder text when filter box is focused.
        
        Args:
            entry: The filter entry widget
        """
        if entry.get() == "Filter...":
            entry.delete(0, tk.END)
            entry.config(foreground="black")
    
    def on_filter_focus_out(self, entry: ttk.Entry) -> None:
        """Restore placeholder text if filter box is empty.
        
        Args:
            entry: The filter entry widget
        """
        if not entry.get():
            entry.insert(0, "Filter...")
            entry.config(foreground="gray")
    
    def clear_selections(self) -> None:
        """Clear all selections on both axes."""
        self.left_selected.clear()
        self.right_selected.clear()
        print("[Selection Manager] All selections cleared")
    
    def get_selection_count(self, side: str) -> int:
        """Get the number of selected items for an axis.
        
        Args:
            side: 'left' or 'right'
            
        Returns:
            Number of selected items
        """
        selected_set = self.left_selected if side == "left" else self.right_selected
        return len(selected_set)
    
    def has_selections(self) -> bool:
        """Check if any items are selected on either axis.
        
        Returns:
            True if any items are selected
        """
        return len(self.left_selected) > 0 or len(self.right_selected) > 0
