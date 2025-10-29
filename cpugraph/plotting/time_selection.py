"""Time range selection via interactive graph clicks.

Allows users to click on the graph to select start and end times,
with visual indicators showing the selected range.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, List, Optional

import pandas as pd
import tkinter as tk
from matplotlib.dates import num2date

if TYPE_CHECKING:
    import matplotlib.axes
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class TimeSelectionHandler:
    """Manages time range selection via graph clicks."""
    
    def __init__(
        self,
        ax_left: matplotlib.axes.Axes,
        canvas: FigureCanvasTkAgg,
        display_tz: Any,
        df: Optional[pd.DataFrame] = None,
        time_col: Optional[str] = None,
    ):
        """Initialize the time selection handler.
        
        Args:
            ax_left: Left axis (primary)
            canvas: Tkinter canvas widget
            display_tz: Timezone for display formatting
            df: DataFrame with data (can be None initially)
            time_col: Name of time column (can be None initially)
        """
        self.ax_left = ax_left
        self.canvas = canvas
        self.display_tz = display_tz
        self.df = df
        self.time_col = time_col
        
        # Selection state
        self.time_selection_mode = False
        self.selected_time_start: Optional[pd.Timestamp] = None
        self.selected_time_end: Optional[pd.Timestamp] = None
        self.time_selection_lines: List[Any] = []
        
        # Callbacks for UI updates
        self.on_mode_changed: Optional[Callable[[bool], None]] = None
        self.on_time_selected: Optional[Callable[[Optional[str], Optional[str]], None]] = None
        self.on_status_update: Optional[Callable[[str], None]] = None
        
        # Connect mouse click event
        self.canvas.mpl_connect('button_press_event', self.on_graph_click)
    
    def set_data(self, df: pd.DataFrame, time_col: str) -> None:
        """Update the data and time column.
        
        Args:
            df: DataFrame with data
            time_col: Name of time column
        """
        self.df = df
        self.time_col = time_col
    
    def toggle_mode(self) -> None:
        """Toggle time selection mode on/off."""
        self.time_selection_mode = not self.time_selection_mode
        
        if self.on_mode_changed:
            self.on_mode_changed(self.time_selection_mode)
        
        if self.time_selection_mode:
            if self.on_status_update:
                self.on_status_update("Click on graph to select start time, then click again for end time")
            print("[Time Selection] Mode ENABLED - Click on graph to select start and end times")
        else:
            if self.on_status_update:
                self.on_status_update("Time selection mode disabled")
            print("[Time Selection] Mode DISABLED")
    
    def is_active(self) -> bool:
        """Check if time selection mode is currently active.
        
        Returns:
            True if selection mode is active
        """
        return self.time_selection_mode
    
    def get_selection_lines(self) -> List[Any]:
        """Get the list of selection line artists for filtering.
        
        Returns:
            List of matplotlib artists representing selection lines
        """
        return self.time_selection_lines
    
    def on_graph_click(self, event: Any) -> None:
        """Handle mouse clicks on the graph for time selection.
        
        Args:
            event: Matplotlib mouse button press event
        """
        print(f"[Time Selection DEBUG] Click detected! Event: {event}")
        print(f"[Time Selection DEBUG] - time_selection_mode: {self.time_selection_mode}")
        print(f"[Time Selection DEBUG] - event.inaxes: {event.inaxes}")
        print(f"[Time Selection DEBUG] - self.ax_left: {self.ax_left}")
        
        if not self.time_selection_mode:
            print("[Time Selection DEBUG] Mode is OFF - ignoring click")
            return
        
        # Check if click is inside the plot area
        if event.inaxes is None:
            print(f"[Time Selection DEBUG] Click outside plot area - ignoring")
            return
        
        if self.df is None or self.time_col is None:
            print(f"[Time Selection DEBUG] No data loaded - df: {self.df is not None}, time_col: {self.time_col}")
            return
        
        # Get the x-coordinate (time) of the click
        clicked_time = event.xdata
        print(f"[Time Selection DEBUG] - clicked_time (xdata): {clicked_time}")
        print(f"[Time Selection DEBUG] - clicked_time type: {type(clicked_time)}")
        
        # Convert matplotlib date to datetime if needed (this will be in PST since x-axis uses _plot_time)
        clicked_timestamp = None
        if isinstance(clicked_time, (int, float)):
            # If x-axis is datetime, convert from matplotlib date number
            try:
                clicked_datetime = num2date(clicked_time)
                print(f"[Time Selection DEBUG] - Converted to datetime: {clicked_datetime}")
                # Convert to pandas timestamp and ensure it's timezone-aware (PST)
                clicked_timestamp = pd.Timestamp(clicked_datetime)
                # Localize to PST if naive, or convert to PST if already aware
                if clicked_timestamp.tzinfo is None:
                    clicked_timestamp = clicked_timestamp.tz_localize(self.display_tz)
                else:
                    clicked_timestamp = clicked_timestamp.tz_convert(self.display_tz)
                print(f"[Time Selection DEBUG] - Pandas timestamp (PST): {clicked_timestamp}")
            except Exception as e:
                print(f"[Time Selection DEBUG] - Conversion error: {e}")
                import traceback
                traceback.print_exc()
                clicked_timestamp = None
        else:
            # May already be a datetime object
            try:
                clicked_timestamp = pd.Timestamp(clicked_time)
                if clicked_timestamp.tzinfo is None:
                    clicked_timestamp = clicked_timestamp.tz_localize(self.display_tz)
                else:
                    clicked_timestamp = clicked_timestamp.tz_convert(self.display_tz)
                print(f"[Time Selection DEBUG] - Direct timestamp conversion (PST): {clicked_timestamp}")
            except Exception as e:
                print(f"[Time Selection DEBUG] - Direct conversion error: {e}")
        
        if clicked_timestamp is None:
            print("[Time Selection] ERROR: Could not determine time from click")
            return
        
        # Set start or end time
        print(f"[Time Selection DEBUG] - selected_time_start: {self.selected_time_start}")
        print(f"[Time Selection DEBUG] - selected_time_end: {self.selected_time_end}")
        
        if self.selected_time_start is None:
            # First click - set start time
            print("[Time Selection DEBUG] Setting START time...")
            self.selected_time_start = clicked_timestamp
            time_str = clicked_timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
            
            if self.on_time_selected:
                self.on_time_selected(time_str, None)
            if self.on_status_update:
                self.on_status_update("Start time set (PST). Now click to select end time.")
            
            print(f"[Time Selection] ✓ Start time (PST): {clicked_timestamp}")
            
            # Draw vertical line at start
            self._draw_time_selection_lines()
            
        elif self.selected_time_end is None:
            # Second click - set end time
            print("[Time Selection DEBUG] Setting END time...")
            self.selected_time_end = clicked_timestamp
            time_str = clicked_timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
            
            start_str = self.selected_time_start.strftime("%Y-%m-%d %H:%M:%S %Z")
            if self.on_time_selected:
                self.on_time_selected(start_str, time_str)
            if self.on_status_update:
                self.on_status_update("Time range selected (PST). Click 'Calculate CO₂ Captured' to use this range.")
            
            print(f"[Time Selection] ✓ End time (PST): {clicked_timestamp}")
            print(f"[Time Selection] ✓ Range ready (PST): {self.selected_time_start} to {self.selected_time_end}")
            
            # Draw both lines and shaded region
            self._draw_time_selection_lines()
            
            # Auto-disable selection mode after both points are selected
            self.time_selection_mode = False
            if self.on_mode_changed:
                self.on_mode_changed(False)
            print("[Time Selection] Mode auto-disabled after selecting both times")
        else:
            # Both already selected - reset and start over
            print("[Time Selection DEBUG] RESETTING - both times already set")
            self.selected_time_start = clicked_timestamp
            self.selected_time_end = None
            time_str = clicked_timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
            
            if self.on_time_selected:
                self.on_time_selected(time_str, None)
            if self.on_status_update:
                self.on_status_update("Start time reset (PST). Now click to select end time.")
            
            print(f"[Time Selection] ✓ Reset - New start time (PST): {clicked_timestamp}")
            
            self._draw_time_selection_lines()
    
    def _draw_time_selection_lines(self) -> None:
        """Draw vertical lines and shaded region showing selected time range."""
        print(f"[Time Selection DEBUG] _draw_time_selection_lines called")
        print(f"[Time Selection DEBUG] - start: {self.selected_time_start}")
        print(f"[Time Selection DEBUG] - end: {self.selected_time_end}")
        
        # Remove old lines
        for line in self.time_selection_lines:
            try:
                line.remove()
                print(f"[Time Selection DEBUG] - Removed old line/span")
            except Exception as e:
                print(f"[Time Selection DEBUG] - Error removing line: {e}")
        self.time_selection_lines.clear()
        
        # Draw new lines
        try:
            if self.selected_time_start:
                print(f"[Time Selection DEBUG] Drawing START line at {self.selected_time_start}")
                line1 = self.ax_left.axvline(self.selected_time_start, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Start')
                self.time_selection_lines.append(line1)
                print(f"[Time Selection DEBUG] ✓ START line drawn")
            
            if self.selected_time_end:
                print(f"[Time Selection DEBUG] Drawing END line at {self.selected_time_end}")
                line2 = self.ax_left.axvline(self.selected_time_end, color='red', linestyle='--', linewidth=2, alpha=0.7, label='End')
                self.time_selection_lines.append(line2)
                print(f"[Time Selection DEBUG] ✓ END line drawn")
                
                # Draw shaded region between start and end
                if self.selected_time_start:
                    print(f"[Time Selection DEBUG] Drawing SHADED region from {self.selected_time_start} to {self.selected_time_end}")
                    span = self.ax_left.axvspan(self.selected_time_start, self.selected_time_end, 
                                              alpha=0.2, color='yellow', label='Selected Range')
                    self.time_selection_lines.append(span)
                    print(f"[Time Selection DEBUG] ✓ SHADED region drawn")
            
            print(f"[Time Selection DEBUG] Calling canvas.draw()...")
            self.canvas.draw()
            print(f"[Time Selection DEBUG] ✓ Canvas redrawn successfully")
            
        except Exception as e:
            print(f"[Time Selection DEBUG] ERROR drawing lines: {e}")
            import traceback
            traceback.print_exc()
    
    def clear_selection(self) -> None:
        """Clear the time selection and remove visual indicators."""
        self.selected_time_start = None
        self.selected_time_end = None
        
        if self.on_time_selected:
            self.on_time_selected(None, None)
        
        # Remove visual indicators
        for line in self.time_selection_lines:
            try:
                line.remove()
            except:
                pass
        self.time_selection_lines.clear()
        
        self.canvas.draw()
        
        if self.on_status_update:
            self.on_status_update("Time selection cleared")
        print("[Time Selection] Cleared")

