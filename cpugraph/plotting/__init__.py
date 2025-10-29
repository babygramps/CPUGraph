"""Plotting components for the sensor dashboard.

This package contains modular plotting functionality extracted from the main app:
- plotter: Main plotting orchestration
- cycle_backgrounds: Measurement cycle detection and visualization
- hover_tooltip: Interactive hover tooltips with data point information
- time_selection: Time range selection via graph clicks
"""

from .plotter import SensorPlotter
from .cycle_backgrounds import CycleBackgroundRenderer
from .hover_tooltip import HoverTooltipHandler
from .time_selection import TimeSelectionHandler

__all__ = [
    "SensorPlotter",
    "CycleBackgroundRenderer",
    "HoverTooltipHandler",
    "TimeSelectionHandler",
]

