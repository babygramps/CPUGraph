"""Interactive hover tooltips for data point inspection.

Displays elegant tooltips with crosshairs when hovering over plotted data,
showing timestamp and values for all series at the cursor position.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

import numpy as np
import pandas as pd
from matplotlib.dates import date2num, num2date

if TYPE_CHECKING:
    import matplotlib.axes
    import matplotlib.figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class HoverTooltipHandler:
    """Manages interactive hover tooltips on plot data."""
    
    def __init__(
        self,
        fig: matplotlib.figure.Figure,
        ax_left: matplotlib.axes.Axes,
        canvas: FigureCanvasTkAgg,
        display_tz: Any,
    ):
        """Initialize the hover tooltip handler.
        
        Args:
            fig: Matplotlib figure
            ax_left: Left axis (primary)
            canvas: Tkinter canvas widget
            display_tz: Timezone for display formatting
        """
        self.fig = fig
        self.ax_left = ax_left
        self.canvas = canvas
        self.display_tz = display_tz
        
        # State for visualization elements
        self.hover_annotation: Optional[Any] = None
        self.hover_vline: Optional[Any] = None
        self.hover_hline: Optional[Any] = None
        self.hover_points: List[Any] = []
        
        # For logging throttling
        self._hover_call_count = 0
        
        # Lines to skip (time selection indicators)
        self.time_selection_lines: List[Any] = []
        
        # Connect mouse motion event
        self.canvas.mpl_connect('motion_notify_event', self.on_graph_hover)
        # Connect axes leave event to clear hover when mouse leaves
        self.canvas.mpl_connect('axes_leave_event', self._on_axes_leave)
    
    def set_time_selection_lines(self, lines: List[Any]) -> None:
        """Set which lines should be ignored (time selection indicators).
        
        Args:
            lines: List of matplotlib artists representing time selection
        """
        self.time_selection_lines = lines
    
    def on_graph_hover(self, event: Any) -> None:
        """Handle mouse hover on the graph to display data point values.
        
        Args:
            event: Matplotlib mouse motion event
        """
        # Check if hover is inside the plot area
        if event.inaxes is None:
            self._clear_hover_elements()
            return
        
        # Log hover event occasionally (every 50th call to avoid spam)
        self._hover_call_count += 1
        log_this_call = (self._hover_call_count % 50 == 1)
        
        try:
            # Get all plotted lines from both axes
            left_lines = self.ax_left.get_lines()
            right_lines = []
            
            # Check if right axis exists
            ax_right = None
            for ax in self.fig.get_axes():
                if ax != self.ax_left and hasattr(ax, 'get_ylabel') and ax.get_ylabel():
                    ax_right = ax
                    right_lines = ax.get_lines()
                    break
            
            # Skip time selection lines (dashed green/red lines)
            left_lines = [line for line in left_lines if line not in self.time_selection_lines 
                         and not (hasattr(line, 'get_linestyle') and line.get_linestyle() == '--' 
                         and hasattr(line, 'get_color') and line.get_color() in ['green', 'red', 'g', 'r'])]
            
            if not left_lines and not right_lines:
                self._clear_hover_elements()
                return
            
            # Get cursor position
            cursor_x = event.xdata
            cursor_y = event.ydata
            
            # Convert matplotlib date to pandas timestamp if needed
            cursor_time = None
            if isinstance(cursor_x, (int, float)):
                cursor_datetime = num2date(cursor_x)
                cursor_time = pd.Timestamp(cursor_datetime)
                if cursor_time.tzinfo is None:
                    cursor_time = cursor_time.tz_localize(self.display_tz)
                else:
                    cursor_time = cursor_time.tz_convert(self.display_tz)
            
            # Find nearest data points for all series
            hover_data = []
            nearest_x = None
            min_distance = float('inf')
            
            # Check left axis lines
            for line in left_lines:
                xdata = line.get_xdata()
                ydata = line.get_ydata()
                label = line.get_label()
                color = line.get_color()
                
                if len(xdata) == 0 or label.startswith('_'):
                    continue
                
                # Convert xdata to matplotlib date numbers if needed (handle Timestamp objects)
                xdata_numeric = xdata
                if len(xdata) > 0 and isinstance(xdata[0], (pd.Timestamp, np.datetime64)):
                    xdata_numeric = date2num(xdata)
                
                # Find nearest point
                distances = np.abs(xdata_numeric - cursor_x)
                idx = np.argmin(distances)
                
                if distances[idx] < min_distance:
                    min_distance = distances[idx]
                    nearest_x = xdata[idx]
                
                # Store data for tooltip
                hover_data.append({
                    'label': label,
                    'x': xdata[idx],
                    'y': ydata[idx],
                    'color': color,
                    'axis': 'left'
                })
            
            # Check right axis lines
            for line in right_lines:
                xdata = line.get_xdata()
                ydata = line.get_ydata()
                label = line.get_label()
                color = line.get_color()
                
                if len(xdata) == 0 or label.startswith('_'):
                    continue
                
                # Convert xdata to matplotlib date numbers if needed (handle Timestamp objects)
                xdata_numeric = xdata
                if len(xdata) > 0 and isinstance(xdata[0], (pd.Timestamp, np.datetime64)):
                    xdata_numeric = date2num(xdata)
                
                # Find nearest point
                distances = np.abs(xdata_numeric - cursor_x)
                idx = np.argmin(distances)
                
                if distances[idx] < min_distance:
                    min_distance = distances[idx]
                    nearest_x = xdata[idx]
                
                # Store data for tooltip
                hover_data.append({
                    'label': label,
                    'x': xdata[idx],
                    'y': ydata[idx],
                    'color': color,
                    'axis': 'right'
                })
            
            if not hover_data or nearest_x is None:
                self._clear_hover_elements()
                return
            
            # Convert nearest_x to matplotlib date number for comparison if needed
            nearest_x_numeric = nearest_x
            if isinstance(nearest_x, (pd.Timestamp, np.datetime64)):
                nearest_x_numeric = date2num(nearest_x)
            
            # Only show tooltip if cursor is reasonably close to data
            xlim = self.ax_left.get_xlim()
            x_range = xlim[1] - xlim[0]
            threshold = x_range * 0.02  # Within 2% of x-axis range
            
            if min_distance > threshold:
                self._clear_hover_elements()
                return
            
            # Filter to only show data at the nearest x position
            filtered_data = []
            for d in hover_data:
                x_val_numeric = d['x']
                if isinstance(x_val_numeric, (pd.Timestamp, np.datetime64)):
                    x_val_numeric = date2num(x_val_numeric)
                if abs(x_val_numeric - nearest_x_numeric) < threshold * 0.1:
                    filtered_data.append(d)
            hover_data = filtered_data
            
            # Clear previous hover elements (without redrawing - we'll redraw once after adding new ones)
            self._clear_hover_elements(redraw=False)
            
            # Draw elegant crosshair at nearest x position
            self.hover_vline = self.ax_left.axvline(nearest_x, color='gray', linestyle='-', 
                                                    linewidth=0.8, alpha=0.5, zorder=100)
            
            # Draw marker points on each line at the hover position
            for data in hover_data:
                if data['axis'] == 'left':
                    point = self.ax_left.scatter([data['x']], [data['y']], 
                                                color=data['color'], s=60, zorder=101,
                                                edgecolors='white', linewidths=1.5,
                                                picker=False)  # Disable picking to avoid event conflicts
                    self.hover_points.append(point)
                elif ax_right is not None:
                    point = ax_right.scatter([data['x']], [data['y']], 
                                           color=data['color'], s=60, zorder=101,
                                           edgecolors='white', linewidths=1.5,
                                           picker=False)  # Disable picking to avoid event conflicts
                    self.hover_points.append(point)
            
            # Create beautiful tooltip text
            tooltip_lines = []
            
            # Add timestamp
            if isinstance(nearest_x, (pd.Timestamp, np.datetime64)):
                time_pd = pd.Timestamp(nearest_x)
            else:
                time_obj = num2date(nearest_x)
                time_pd = pd.Timestamp(time_obj)
            
            # Ensure timezone is set correctly
            if time_pd.tzinfo is None:
                time_pd = time_pd.tz_localize(self.display_tz)
            else:
                time_pd = time_pd.tz_convert(self.display_tz)
            
            time_str = time_pd.strftime('%m/%d/%Y %I:%M:%S %p')
            tooltip_lines.append(f"Time: {time_str}")
            tooltip_lines.append("─" * 40)  # Separator
            
            # Add each series value with color coding
            for data in hover_data:
                # Truncate long labels
                label = data['label']
                if len(label) > 45:
                    label = label[:42] + "..."
                
                # Format value with appropriate precision
                value = data['y']
                if abs(value) < 0.01 and value != 0:
                    value_str = f"{value:.6f}"
                elif abs(value) < 1:
                    value_str = f"{value:.4f}"
                elif abs(value) < 100:
                    value_str = f"{value:.3f}"
                else:
                    value_str = f"{value:.2f}"
                
                tooltip_lines.append(f"{label}: {value_str}")
            
            tooltip_text = "\n".join(tooltip_lines)
            
            # Position tooltip smartly (avoid cursor and edge of plot)
            ylim = self.ax_left.get_ylim()
            
            # Determine if cursor is on left or right side of plot
            x_relative = (nearest_x_numeric - xlim[0]) / (xlim[1] - xlim[0])
            y_relative = (cursor_y - ylim[0]) / (ylim[1] - ylim[0])
            
            # Position tooltip on opposite side of cursor
            if x_relative > 0.5:
                box_x = 0.02
                ha = 'left'
            else:
                box_x = 0.98
                ha = 'right'
            
            if y_relative > 0.5:
                box_y = 0.02
                va = 'bottom'
            else:
                box_y = 0.98
                va = 'top'
            
            # Create elegant annotation box
            bbox_props = dict(
                boxstyle='round,pad=0.7',
                facecolor='white',
                edgecolor='#333333',
                alpha=0.95,
                linewidth=1.5
            )
            
            self.hover_annotation = self.ax_left.annotate(
                tooltip_text,
                xy=(nearest_x, cursor_y),
                xytext=(box_x, box_y),
                textcoords='axes fraction',
                fontsize=8,
                fontfamily='monospace',
                bbox=bbox_props,
                ha=ha,
                va=va,
                zorder=102
            )
            
            # Redraw canvas to show new hover elements
            try:
                self.canvas.draw_idle()
            except Exception as e:
                print(f"[Hover] Error redrawing canvas: {e}")
            
            # Log successful tooltip display occasionally
            if log_this_call:
                print(f"[Hover] Tooltip displayed - {len(hover_data)} series, {len(self.hover_points)} points at time {time_str}")
            
        except Exception as e:
            print(f"[Hover] Error displaying tooltip: {e}")
            import traceback
            traceback.print_exc()
            self._clear_hover_elements()
    
    def _clear_hover_elements(self, redraw: bool = True) -> None:
        """Remove all hover visualization elements from the plot.
        
        Args:
            redraw: Whether to redraw the canvas after clearing (default True)
        """
        elements_removed = 0
        
        try:
            # Remove annotation
            if self.hover_annotation is not None:
                try:
                    self.hover_annotation.remove()
                    elements_removed += 1
                except Exception as e:
                    print(f"[Hover Clear] Failed to remove annotation: {e}")
                self.hover_annotation = None
            
            # Remove vertical line
            if self.hover_vline is not None:
                try:
                    self.hover_vline.remove()
                    elements_removed += 1
                except Exception as e:
                    print(f"[Hover Clear] Failed to remove vline: {e}")
                self.hover_vline = None
            
            # Remove horizontal line
            if self.hover_hline is not None:
                try:
                    self.hover_hline.remove()
                    elements_removed += 1
                except Exception as e:
                    print(f"[Hover Clear] Failed to remove hline: {e}")
                self.hover_hline = None
            
            # Remove scatter points - ensure they're actually removed
            points_to_remove = len(self.hover_points)
            if self.hover_points:
                for i, point in enumerate(self.hover_points):
                    try:
                        point.remove()
                        elements_removed += 1
                    except Exception as e:
                        print(f"[Hover Clear] Failed to remove point {i}: {e}")
                self.hover_points.clear()
            
            # Log clearing activity (throttled)
            if elements_removed > 0 and self._hover_call_count % 50 == 1:
                print(f"[Hover Clear] Removed {elements_removed} elements ({points_to_remove} scatter points)")
            
            # Force canvas redraw only if we removed something and redraw is requested
            if redraw and elements_removed > 0 and hasattr(self, 'canvas') and self.canvas is not None:
                try:
                    self.canvas.draw_idle()
                except Exception as e:
                    print(f"[Hover Clear] Failed to redraw canvas: {e}")
        except Exception as e:
            print(f"[Hover Clear] Unexpected error: {e}")
    
    def _on_axes_leave(self, event: Any) -> None:
        """Handle mouse leaving the axes area.
        
        Args:
            event: Matplotlib axes leave event
        """
        self._clear_hover_elements()
    
    def clear(self) -> None:
        """Public method to clear hover elements."""
        self._clear_hover_elements()

