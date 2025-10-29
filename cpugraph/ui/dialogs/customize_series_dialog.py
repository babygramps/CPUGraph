"""Dialog for customizing series visual properties.

Allows users to customize colors, line styles, markers, and other visual
properties for selected data series.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, messagebox, ttk
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    pass


class SeriesCustomizeDialog:
    """Dialog for customizing series properties (colors, line styles, markers)."""
    
    def __init__(
        self,
        parent: tk.Tk,
        all_series: List[str],
        series_properties: Dict[str, Dict[str, Any]],
        last_series_lines: Dict[str, Dict[str, Any]],
    ):
        """Initialize the series customization dialog.
        
        Args:
            parent: Parent Tk window
            all_series: List of series names to customize
            series_properties: Existing series properties dict
            last_series_lines: Last plotted line objects for reading current properties
        """
        self.parent = parent
        self.all_series = all_series
        self.series_properties = series_properties
        self.last_series_lines = last_series_lines
        
        self.result: Optional[Dict[str, Dict[str, Any]]] = None
        self.series_widgets: Dict[str, Dict[str, Any]] = {}
        
        # Line style and marker options
        self.linestyles = ['-', '--', '-.', ':', 'None']
        self.markers = ['None', 'o', 's', '^', 'v', '<', '>', 'd', 'p', '*', 'h', 'H', '+', 'x', 'D', '|', '_']
    
    def show(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Show the dialog and return updated properties, or None if cancelled.
        
        Returns:
            Updated series_properties dict if applied, None if cancelled
        """
        self._create_dialog()
        self._create_controls()
        self._create_buttons()
        
        # Wait for dialog to close
        self.parent.wait_window(self.dialog)
        
        return self.result
    
    def _create_dialog(self) -> None:
        """Create the main dialog window."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Customize Series")
        self.dialog.geometry("700x600")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        print(f"[Customize] Opening dialog for {len(self.all_series)} series")
    
    def _create_controls(self) -> None:
        """Create the scrollable frame with customization controls."""
        # Main frame with scrollbar
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create customization controls for each series
        for idx, col in enumerate(self.all_series):
            self._create_series_controls(scrollable_frame, col)
        
        # Enable mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Cleanup binding when dialog closes
        def on_close():
            canvas.unbind_all("<MouseWheel>")
            self.dialog.destroy()
        
        self.dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        # Store canvas for cleanup
        self._canvas = canvas
    
    def _create_series_controls(self, parent: ttk.Frame, col: str) -> None:
        """Create customization controls for a single series.
        
        Args:
            parent: Parent frame to place controls in
            col: Column name for this series
        """
        # Get current properties
        props = self._get_current_properties(col)
        
        current_color = props.get('color', None)
        current_linestyle = props.get('linestyle', '-')
        current_linewidth = props.get('linewidth', 1.5)
        current_marker = props.get('marker') or 'None'
        current_markersize = props.get('markersize', 6)
        
        # Series frame
        series_frame = ttk.LabelFrame(parent, text=col)
        series_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Color selection
        color_frame = ttk.Frame(series_frame)
        color_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=3)
        
        ttk.Label(color_frame, text="Color:").pack(side=tk.LEFT, padx=5)
        
        color_display = tk.Canvas(
            color_frame, width=40, height=20,
            bg=current_color if current_color else "white",
            relief=tk.SUNKEN, bd=1
        )
        color_display.pack(side=tk.LEFT, padx=5)
        
        color_var = tk.StringVar(value=current_color if current_color else "")
        
        def make_choose_color(col_name, color_var, color_display):
            def choose_color():
                color = colorchooser.askcolor(title=f"Choose color for {col_name}")
                if color[1]:  # color[1] is hex string
                    color_var.set(color[1])
                    color_display.config(bg=color[1])
                    print(f"[Customize] {col_name}: color set to {color[1]}")
            return choose_color
        
        ttk.Button(
            color_frame, text="Choose Color",
            command=make_choose_color(col, color_var, color_display)
        ).pack(side=tk.LEFT, padx=5)
        
        def make_reset_color(col_name, color_var, color_display):
            def reset_color():
                color_var.set("")
                color_display.config(bg="white")
                print(f"[Customize] {col_name}: color reset to default")
            return reset_color
        
        ttk.Button(
            color_frame, text="Auto",
            command=make_reset_color(col, color_var, color_display)
        ).pack(side=tk.LEFT, padx=5)
        
        # Line style
        ttk.Label(series_frame, text="Line Style:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        linestyle_combo = ttk.Combobox(series_frame, values=self.linestyles, width=10, state="readonly")
        linestyle_combo.set(current_linestyle)
        linestyle_combo.grid(row=1, column=1, sticky="w", padx=5, pady=3)
        
        # Line width
        ttk.Label(series_frame, text="Line Width:").grid(row=1, column=2, sticky="e", padx=5, pady=3)
        linewidth_spinbox = ttk.Spinbox(series_frame, from_=0.5, to=10.0, increment=0.5, width=8)
        linewidth_spinbox.set(current_linewidth)
        linewidth_spinbox.grid(row=1, column=3, sticky="w", padx=5, pady=3)
        
        # Marker style
        ttk.Label(series_frame, text="Marker:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        marker_combo = ttk.Combobox(series_frame, values=self.markers, width=10, state="readonly")
        try:
            marker_combo.set(str(current_marker))
        except Exception:
            marker_combo.set('None')
        marker_combo.grid(row=2, column=1, sticky="w", padx=5, pady=3)
        
        # Marker size
        ttk.Label(series_frame, text="Marker Size:").grid(row=2, column=2, sticky="e", padx=5, pady=3)
        markersize_spinbox = ttk.Spinbox(series_frame, from_=1, to=20, increment=1, width=8)
        markersize_spinbox.set(current_markersize)
        markersize_spinbox.grid(row=2, column=3, sticky="w", padx=5, pady=3)
        
        # Store widgets
        self.series_widgets[col] = {
            'color_var': color_var,
            'linestyle': linestyle_combo,
            'linewidth': linewidth_spinbox,
            'marker': marker_combo,
            'markersize': markersize_spinbox
        }
    
    def _get_current_properties(self, col: str) -> Dict[str, Any]:
        """Get current properties for a series.
        
        Args:
            col: Column name
            
        Returns:
            Dictionary of current properties
        """
        # Start with explicit custom properties if user set any previously
        props = dict(self.series_properties.get(col, {}))
        
        # If no explicit customization, try to read from last plotted line
        if not props:
            line = None
            if col in self.last_series_lines.get("left", {}):
                line = self.last_series_lines["left"].get(col)
            if line is None and col in self.last_series_lines.get("right", {}):
                line = self.last_series_lines["right"].get(col)
            if line is not None:
                try:
                    # Extract live properties from the matplotlib Line2D
                    props = {
                        'color': line.get_color(),
                        'linestyle': line.get_linestyle() or '-',
                        'linewidth': float(line.get_linewidth()),
                        'marker': line.get_marker() if line.get_marker() not in [None, 'None'] else None,
                        'markersize': float(line.get_markersize()),
                    }
                except Exception:
                    props = {}
        
        return props
    
    def _create_buttons(self) -> None:
        """Create the button frame at the bottom of the dialog."""
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Apply", command=self._apply_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset All", command=self._reset_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _apply_changes(self) -> None:
        """Apply customizations to series_properties."""
        updated_properties = {}
        
        for col, widgets in self.series_widgets.items():
            color = widgets['color_var'].get()
            linestyle = widgets['linestyle'].get()
            linewidth = float(widgets['linewidth'].get())
            marker = widgets['marker'].get()
            markersize = float(widgets['markersize'].get())
            
            # Store properties
            updated_properties[col] = {
                'color': color if color else None,
                'linestyle': linestyle,
                'linewidth': linewidth,
                'marker': marker if marker != 'None' else None,
                'markersize': markersize
            }
            
            print(f"[Customize] {col}: color={color if color else 'auto'}, "
                  f"linestyle={linestyle}, linewidth={linewidth}, "
                  f"marker={marker}, markersize={markersize}")
        
        # Merge with existing properties
        self.result = dict(self.series_properties)
        self.result.update(updated_properties)
        
        messagebox.showinfo(
            "Success",
            f"Customizations applied to {len(self.series_widgets)} series.\nClick 'Plot' to see changes."
        )
        self.dialog.destroy()
    
    def _reset_all(self) -> None:
        """Reset all customizations for selected series."""
        # Create result with customizations removed for these series
        self.result = {k: v for k, v in self.series_properties.items() 
                       if k not in self.series_widgets}
        
        print(f"[Customize] Reset all customizations for {len(self.series_widgets)} series")
        messagebox.showinfo("Reset", "All customizations cleared. Click 'Plot' to see changes.")
        self.dialog.destroy()

