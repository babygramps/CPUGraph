"""Cycle background rendering for sensor measurements.

Detects measurement cycles by analyzing the 'Time (s)' column and adds
semi-transparent colored backgrounds for visual separation of cycles.
If a 'Mode' column is present, cycle names are displayed on each background.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    import matplotlib.axes


class CycleBackgroundRenderer:
    """Renders colored backgrounds for detected measurement cycles."""
    
    def __init__(self, time_s_column: str = "Time (s)", mode_column: str = "Mode"):
        """Initialize the cycle background renderer.
        
        Args:
            time_s_column: Name of the column containing cycle time in seconds
            mode_column: Name of the column containing cycle/mode names
        """
        self.time_s_column = time_s_column
        self.mode_column = mode_column
    
    def add_cycle_backgrounds(
        self,
        ax: matplotlib.axes.Axes,
        df_plot: pd.DataFrame,
        x_series: pd.Series,
        show_backgrounds: bool = True,
        show_mode_labels: bool = True,
    ) -> list:
        """Detect measurement cycles and add semi-transparent colored backgrounds.
        
        A cycle reset is detected when the time decreases (resets to near zero).
        This method adds the background spans but returns cycle information for
        later label addition (after axes are finalized).
        
        Args:
            ax: Matplotlib axes to draw on
            df_plot: DataFrame containing the data to plot
            x_series: Series to use for x-axis values (typically time)
            show_backgrounds: Whether to show colored background spans
            show_mode_labels: Whether mode labels should be added (passed to label method)
            
        Returns:
            List of cycle information dicts for adding labels later, or empty list
        """
        # Check if backgrounds are disabled
        if not show_backgrounds:
            print(f"[Cycle Backgrounds] Cycle backgrounds disabled by user")
            return []
        
        # Check if "Time (s)" column exists
        if self.time_s_column not in df_plot.columns:
            print(f"[Cycle Backgrounds] '{self.time_s_column}' column not found, skipping cycle backgrounds")
            return []
        
        try:
            # Get the time column and convert to numeric
            time_values = pd.to_numeric(df_plot[self.time_s_column], errors='coerce')
            
            # Detect cycle boundaries by finding where time decreases
            cycle_starts = [0]  # First row is always a cycle start
            
            for i in range(1, len(time_values)):
                # If time decreased or reset to a small value, it's a new cycle
                if pd.notna(time_values.iloc[i]) and pd.notna(time_values.iloc[i-1]):
                    if time_values.iloc[i] < time_values.iloc[i-1]:
                        cycle_starts.append(i)
            
            # Add the end of the last cycle
            cycle_starts.append(len(df_plot))
            
            print(f"[Cycle Backgrounds] Detected {len(cycle_starts)-1} measurement cycles")
            
            # Generate random colors for each cycle with 15% opacity
            np.random.seed(42)  # For reproducible colors
            colors_list = []
            for i in range(len(cycle_starts) - 1):
                # Generate random RGB values
                r = np.random.uniform(0.2, 0.9)
                g = np.random.uniform(0.2, 0.9)
                b = np.random.uniform(0.2, 0.9)
                # Create color with 15% opacity (alpha = 0.15)
                color = (r, g, b, 0.15)
                colors_list.append(color)
            
            # Check if Mode column exists for labeling cycles
            mode_column_exists = self.mode_column in df_plot.columns
            if mode_column_exists and show_mode_labels:
                print(f"[Cycle Backgrounds] '{self.mode_column}' column found - will display cycle names after layout is finalized")
            elif mode_column_exists and not show_mode_labels:
                print(f"[Cycle Backgrounds] '{self.mode_column}' column found - mode labels disabled by user")
            
            # Collect cycle information for later label addition
            cycle_info_list = []
            
            # Add background spans for each cycle
            for i in range(len(cycle_starts) - 1):
                start_idx = cycle_starts[i]
                end_idx = cycle_starts[i + 1] - 1
                
                # Get x-values for this cycle
                x_start = x_series.iloc[start_idx]
                x_end = x_series.iloc[end_idx]
                
                # Add vertical span for this cycle
                ax.axvspan(x_start, x_end, 
                          facecolor=colors_list[i], 
                          edgecolor='none',
                          zorder=0)  # Behind everything
                
                # Collect cycle information for later label addition
                if mode_column_exists and show_mode_labels:
                    # Get the mode name for this cycle (use first non-null value)
                    mode_name = None
                    for idx in range(start_idx, end_idx + 1):
                        if idx < len(df_plot):
                            value = df_plot[self.mode_column].iloc[idx]
                            if pd.notna(value) and str(value).strip():
                                mode_name = str(value).strip()
                                break
                    
                    if mode_name:
                        # Calculate center position for label
                        x_center = x_series.iloc[(start_idx + end_idx) // 2]
                        
                        cycle_info_list.append({
                            'x_center': x_center,
                            'mode_name': mode_name,
                            'cycle_num': i + 1,
                        })
                        
                        # Log mode name for first few cycles
                        if i < 3:
                            print(f"[Cycle Backgrounds] Cycle {i+1}: Mode '{mode_name}' (label will be added after layout)")
                
                # Log first few cycles for debugging
                if i < 3:
                    print(f"[Cycle Backgrounds] Cycle {i+1}: rows {start_idx}-{end_idx}, "
                          f"time {time_values.iloc[start_idx]:.1f}s to {time_values.iloc[end_idx]:.1f}s, "
                          f"color RGB({colors_list[i][0]:.2f}, {colors_list[i][1]:.2f}, {colors_list[i][2]:.2f})")
            
            if mode_column_exists and show_mode_labels:
                print(f"[Cycle Backgrounds] Added {len(colors_list)} cycle backgrounds, {len(cycle_info_list)} mode labels pending")
            else:
                print(f"[Cycle Backgrounds] Added {len(colors_list)} cycle backgrounds with 15% opacity")
            
            return cycle_info_list
            
        except Exception as e:
            print(f"[Cycle Backgrounds] Failed to add cycle backgrounds: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def add_mode_labels(
        self,
        ax: matplotlib.axes.Axes,
        cycle_info_list: list,
    ) -> None:
        """Add mode labels to cycle backgrounds after axes are finalized.
        
        This should be called after all data is plotted and tight_layout is applied,
        to ensure the y-axis limits are final and labels are positioned correctly.
        
        Args:
            ax: Matplotlib axes to draw on
            cycle_info_list: List of cycle info dicts from add_cycle_backgrounds()
        """
        if not cycle_info_list:
            return
        
        try:
            # Get y-axis limits (should be finalized at this point)
            ylim = ax.get_ylim()
            y_position = ylim[0] + (ylim[1] - ylim[0]) * 0.98  # Near top of plot
            
            # Add text annotations for each cycle
            for cycle_info in cycle_info_list:
                x_center = cycle_info['x_center']
                mode_name = cycle_info['mode_name']
                cycle_num = cycle_info['cycle_num']
                
                # Add text annotation with mode name
                # Use a contrasting color for readability
                text_color = (0.2, 0.2, 0.2, 0.7)  # Dark gray with transparency
                ax.text(
                    x_center, y_position,
                    mode_name,
                    fontsize=10,
                    fontweight='bold',
                    color=text_color,
                    ha='center',
                    va='top',
                    bbox=dict(
                        boxstyle='round,pad=0.5',
                        facecolor='white',
                        edgecolor='none',
                        alpha=0.7
                    ),
                    zorder=1  # Just above background, below data
                )
            
            print(f"[Cycle Backgrounds] Added {len(cycle_info_list)} mode labels at y={y_position:.2f}")
            
        except Exception as e:
            print(f"[Cycle Backgrounds] Failed to add mode labels: {e}")
            import traceback
            traceback.print_exc()

