"""Main plotting orchestration for sensor data visualization.

Coordinates data preparation, series plotting, legend creation, and
watermark placement for the sensor dashboard.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image

from .cycle_backgrounds import CycleBackgroundRenderer

if TYPE_CHECKING:
    import matplotlib.axes
    import matplotlib.figure


class PlotOptions:
    """Configuration options for plotting."""
    
    def __init__(
        self,
        *,
        # Grid and smoothing
        show_grid: bool = True,
        apply_smoothing: bool = False,
        smoothing_window: int = 21,
        
        # Legend options
        show_legend: bool = True,
        legend_position: str = "Upper Left",
        legend_fontsize: int = 8,
        legend_columns: int = 1,
        legend_framealpha: float = 0.7,
        
        # Labels
        graph_title: str = "Sensor Time Series",
        x_label: str = "Time",
        left_y_label: str = "Left axis",
        right_y_label: str = "Right axis",
        
        # Watermark and mode labels
        show_watermark: bool = True,
        show_mode_labels: bool = True,
        
        # Time window (timezone-aware timestamps or strings)
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ):
        """Initialize plot options.
        
        Args:
            show_grid: Whether to show grid lines
            apply_smoothing: Whether to apply moving average smoothing
            smoothing_window: Window size for smoothing (must be odd)
            show_legend: Whether to show legend
            legend_position: Legend position name
            legend_fontsize: Legend font size in points
            legend_columns: Number of legend columns
            legend_framealpha: Legend background transparency (0-1)
            graph_title: Graph title text
            x_label: X-axis label
            left_y_label: Left Y-axis label
            right_y_label: Right Y-axis label
            show_watermark: Whether to show watermark
            show_mode_labels: Whether to show mode/cycle labels on cycle backgrounds
            start_time: Start time for filtering (optional)
            end_time: End time for filtering (optional)
        """
        self.show_grid = show_grid
        self.apply_smoothing = apply_smoothing
        self.smoothing_window = smoothing_window
        self.show_legend = show_legend
        self.legend_position = legend_position
        self.legend_fontsize = legend_fontsize
        self.legend_columns = legend_columns
        self.legend_framealpha = legend_framealpha
        self.graph_title = graph_title
        self.x_label = x_label
        self.left_y_label = left_y_label
        self.right_y_label = right_y_label
        self.show_watermark = show_watermark
        self.show_mode_labels = show_mode_labels
        self.start_time = start_time
        self.end_time = end_time


class SensorPlotter:
    """Orchestrates sensor data plotting with customization."""
    
    def __init__(
        self,
        fig: matplotlib.figure.Figure,
        display_tz: Any,
        watermark_image: Optional[Image.Image] = None,
    ):
        """Initialize the sensor plotter.
        
        Args:
            fig: Matplotlib figure to plot on
            display_tz: Timezone for time axis formatting
            watermark_image: Optional watermark image (PIL Image)
        """
        self.fig = fig
        self.display_tz = display_tz
        self.watermark_image = watermark_image
        self.watermark_artist: Optional[Any] = None
        
        # Create cycle background renderer
        self.cycle_renderer = CycleBackgroundRenderer()
        
        # Track last plotted lines for each axis
        self.last_series_lines: Dict[str, Dict[str, Any]] = {"left": {}, "right": {}}
    
    def plot(
        self,
        df: pd.DataFrame,
        time_column: str,
        left_columns: List[str],
        right_columns: List[str],
        options: PlotOptions,
        series_properties: Optional[Dict[str, Dict[str, Any]]] = None,
        column_to_display: Optional[Dict[str, str]] = None,
    ) -> matplotlib.axes.Axes:
        """Plot sensor data with the given configuration.
        
        Args:
            df: DataFrame containing the data
            time_column: Name of the time column
            left_columns: List of column names for left Y-axis
            right_columns: List of column names for right Y-axis
            options: PlotOptions configuration object
            series_properties: Optional dict of custom series properties (color, style, etc.)
            column_to_display: Optional mapping from column names to display names
        
        Returns:
            The left axis (primary axis)
        """
        series_properties = series_properties or {}
        column_to_display = column_to_display or {}
        
        print(f"[Plot] Selected {len(left_columns)} left axis columns: {left_columns}")
        print(f"[Plot] Selected {len(right_columns)} right axis columns: {right_columns}")
        
        # Prepare data (filter time window, apply smoothing)
        df_plot = self._prepare_data(df, time_column, left_columns, right_columns, options)
        
        if df_plot.empty:
            raise ValueError("No data in the selected time window.")
        
        # Clear previous plot
        self.fig.clear()
        ax_left = self.fig.add_subplot(111)
        
        # Use timezone-adjusted time column if available
        x_series = df_plot['_plot_time'] if '_plot_time' in df_plot.columns else df_plot[time_column]
        
        # Add cycle backgrounds if "Time (s)" column exists
        # This returns cycle info for adding labels after layout is finalized
        cycle_info_list = self.cycle_renderer.add_cycle_backgrounds(ax_left, df_plot, x_series, options.show_mode_labels)
        
        # Reset last-plotted lines tracking
        self.last_series_lines = {"left": {}, "right": {}}
        
        # Plot left axis series
        for column in left_columns:
            self._plot_series(
                ax_left,
                x_series,
                df_plot,
                column,
                series_properties.get(column, {}),
                column_to_display.get(column, column),
            )
        
        # Configure left axis
        ax_left.set_xlabel(options.x_label)
        ax_left.set_ylabel(options.left_y_label)
        
        if options.show_grid:
            ax_left.grid(True, which="both", linestyle=":")
        
        # Configure x-axis formatter for 12-hour time with timezone
        try:
            locator = mdates.AutoDateLocator()
            ax_left.xaxis.set_major_locator(locator)
            ax_left.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %I:%M %p', tz=self.display_tz))
        except Exception as e:
            print(f"[Time TZ] Could not set 12-hour time formatter: {e}")
        
        # Plot right axis series
        ax_right = None
        if right_columns:
            ax_right = ax_left.twinx()
            for column in right_columns:
                # Default to dashed line for right axis if not customized
                props = series_properties.get(column, {})
                if 'linestyle' not in props:
                    props = dict(props)
                    props['linestyle'] = '--'
                
                self._plot_series(
                    ax_right,
                    x_series,
                    df_plot,
                    column,
                    props,
                    column_to_display.get(column, column),
                    axis='right',
                )
            
            ax_right.set_ylabel(options.right_y_label)
        
        # Add legend
        if options.show_legend:
            self._add_legend(ax_left, ax_right, options)
        else:
            print(f"[Plot] Legend hidden")
        
        # Set graph title
        self.fig.suptitle(options.graph_title)
        print(f"[Plot] Graph title: '{options.graph_title}'")
        
        # Add watermark
        if options.show_watermark:
            self._add_watermark(ax_left)
        else:
            self._remove_watermark()
        
        # Apply tight layout
        self.fig.tight_layout()
        
        # Add mode labels after layout is finalized
        # This ensures labels are positioned correctly based on final axis limits
        if cycle_info_list:
            self.cycle_renderer.add_mode_labels(ax_left, cycle_info_list)
        
        print(f"[Plot] Plotted {len(left_columns)} left + {len(right_columns)} right series ({len(df_plot)} points)")
        
        return ax_left
    
    def _prepare_data(
        self,
        df: pd.DataFrame,
        time_column: str,
        left_columns: List[str],
        right_columns: List[str],
        options: PlotOptions,
    ) -> pd.DataFrame:
        """Prepare data for plotting (filter time window, apply smoothing).
        
        Args:
            df: Source DataFrame
            time_column: Name of the time column
            left_columns: Columns for left axis
            right_columns: Columns for right axis
            options: Plot options
        
        Returns:
            Prepared DataFrame
        """
        df_plot = df.copy()
        
        # Use _plot_time for filtering (which is in display timezone)
        time_col_to_filter = '_plot_time' if '_plot_time' in df_plot.columns else time_column
        
        # Apply time window filtering
        if options.start_time:
            try:
                start_time = pd.to_datetime(options.start_time)
                # Ensure timezone-aware comparison
                if start_time.tzinfo is None:
                    start_time = start_time.tz_localize(self.display_tz)
                print(f"[Plot Filter] Start time: {start_time}")
                df_plot = df_plot[df_plot[time_col_to_filter] >= start_time]
            except Exception as e:
                print(f"[Plot Filter] Error parsing start time: {e}")
                raise ValueError(f"Could not parse start time: {str(e)}")
        
        if options.end_time:
            try:
                end_time = pd.to_datetime(options.end_time)
                # Ensure timezone-aware comparison
                if end_time.tzinfo is None:
                    end_time = end_time.tz_localize(self.display_tz)
                print(f"[Plot Filter] End time: {end_time}")
                df_plot = df_plot[df_plot[time_col_to_filter] <= end_time]
            except Exception as e:
                print(f"[Plot Filter] Error parsing end time: {e}")
                raise ValueError(f"Could not parse end time: {str(e)}")
        
        # Apply smoothing if requested
        if options.apply_smoothing:
            window = options.smoothing_window
            if window % 2 == 0:
                window += 1  # Make it odd
            
            for column in [*left_columns, *right_columns]:
                if column in df_plot.columns:
                    df_plot[column] = pd.to_numeric(df_plot[column], errors="coerce").rolling(
                        window, min_periods=1, center=True
                    ).mean()
            
            print(f"[Plot] Applied smoothing with window={window}")
        
        return df_plot
    
    def _plot_series(
        self,
        ax: matplotlib.axes.Axes,
        x_series: pd.Series,
        df_plot: pd.DataFrame,
        column: str,
        properties: Dict[str, Any],
        display_label: str,
        axis: str = 'left',
    ) -> None:
        """Plot a single series with custom properties.
        
        Args:
            ax: Matplotlib axes
            x_series: X-axis data (time series)
            df_plot: DataFrame with plot data
            column: Column name to plot
            properties: Custom series properties (color, linestyle, etc.)
            display_label: Display name for legend
            axis: 'left' or 'right' for tracking
        """
        y = pd.to_numeric(df_plot[column], errors="coerce")
        
        # Build plot kwargs from properties
        plot_kwargs = {'label': display_label}
        
        if properties.get('color'):
            plot_kwargs['color'] = properties['color']
        if 'linestyle' in properties:
            plot_kwargs['linestyle'] = properties['linestyle']
        if 'linewidth' in properties:
            plot_kwargs['linewidth'] = properties['linewidth']
        if properties.get('marker'):
            plot_kwargs['marker'] = properties['marker']
        if 'markersize' in properties:
            plot_kwargs['markersize'] = properties['markersize']
        
        # Plot the line
        line, = ax.plot(x_series, y, **plot_kwargs)
        
        # Record last-plotted line for introspection
        self.last_series_lines[axis][column] = line
        
        if properties:
            print(f"[Plot] Applied custom properties to '{column}': {properties}")
    
    def _add_legend(
        self,
        ax_left: matplotlib.axes.Axes,
        ax_right: Optional[matplotlib.axes.Axes],
        options: PlotOptions,
    ) -> None:
        """Add legend to the plot with custom formatting.
        
        Args:
            ax_left: Left axis
            ax_right: Right axis (optional)
            options: Plot options with legend configuration
        """
        handles_left, labels_left = ax_left.get_legend_handles_labels()
        handles_right, labels_right = (ax_right.get_legend_handles_labels() if ax_right else ([], []))
        handles = handles_left + handles_right
        labels = labels_left + labels_right
        
        if not handles:
            return
        
        # Map position names to matplotlib location codes
        position_map = {
            "Upper Left": "upper left",
            "Upper Right": "upper right",
            "Lower Left": "lower left",
            "Lower Right": "lower right",
            "Best": "best",
            "Outside Right": "center left",
            "Outside Bottom": "upper center"
        }
        
        loc = position_map.get(options.legend_position, "upper left")
        
        # Handle "outside" positions with bbox_to_anchor
        if options.legend_position == "Outside Right":
            legend = ax_left.legend(
                handles, labels, loc=loc, bbox_to_anchor=(1.05, 0.5),
                fontsize=options.legend_fontsize,
                ncol=options.legend_columns,
                framealpha=options.legend_framealpha
            )
        elif options.legend_position == "Outside Bottom":
            legend = ax_left.legend(
                handles, labels, loc=loc, bbox_to_anchor=(0.5, -0.15),
                fontsize=options.legend_fontsize,
                ncol=options.legend_columns,
                framealpha=options.legend_framealpha
            )
        else:
            legend = ax_left.legend(
                handles, labels, loc=loc,
                fontsize=options.legend_fontsize,
                ncol=options.legend_columns,
                framealpha=options.legend_framealpha
            )
        
        print(f"[Plot] Legend: position={options.legend_position}, "
              f"fontsize={options.legend_fontsize}, columns={options.legend_columns}, "
              f"alpha={options.legend_framealpha}")
    
    def _add_watermark(self, ax: matplotlib.axes.Axes) -> None:
        """Add watermark to the plot.
        
        Args:
            ax: Matplotlib axes
        """
        try:
            if self.watermark_image is None:
                return
            
            # Scale watermark relative to figure size
            fig_w, fig_h = self.fig.get_size_inches()
            dpi = self.fig.get_dpi()
            target_width_px = int(fig_w * dpi * 0.1375)  # ~13.75% of figure width
            ratio = target_width_px / max(self.watermark_image.width, 1)
            target_height_px = max(int(self.watermark_image.height * ratio), 1)
            wm_resized = self.watermark_image.resize((max(target_width_px, 1), target_height_px), Image.LANCZOS)
            
            # Convert to numpy array and modify alpha channel
            wm_array = np.array(wm_resized, dtype=float) / 255.0
            if wm_array.shape[-1] == 4:  # Has alpha channel
                wm_array[:, :, 3] = wm_array[:, :, 3] * 0.15  # 15% opacity
            else:
                # Add alpha channel if not present
                alpha = np.ones((wm_array.shape[0], wm_array.shape[1], 1)) * 0.15
                wm_array = np.concatenate([wm_array, alpha], axis=2)
            
            # Create OffsetImage and annotation box
            imagebox = OffsetImage(wm_array, zoom=1.0)
            ab = AnnotationBbox(
                imagebox, 
                (0.82, 0.88),  # Top-right position
                xycoords='axes fraction', 
                frameon=False,
                box_alignment=(1.0, 1.0),
                zorder=0  # Behind data lines
            )
            
            # Remove previous watermark if exists
            if self.watermark_artist is not None:
                try:
                    self.watermark_artist.remove()
                except Exception:
                    pass
            
            self.watermark_artist = ax.add_artist(ab)
            print(f"[Watermark] Placed watermark: {target_width_px}x{target_height_px}px, alpha=0.15, zorder=0")
            
        except Exception as e:
            print(f"[Watermark] Failed to place watermark: {e}")
            import traceback
            traceback.print_exc()
    
    def _remove_watermark(self) -> None:
        """Remove watermark from the plot."""
        if self.watermark_artist is not None:
            try:
                self.watermark_artist.remove()
                self.watermark_artist = None
                print(f"[Watermark] Watermark disabled")
            except Exception:
                pass

