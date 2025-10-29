"""Reusable control panels for the sensor dashboard.

This package contains modular UI control panels that can be composed
to build the application interface.
"""

from .series_selector import SeriesSelector
from .plot_options_panel import PlotOptionsPanel
from .legend_options_panel import LegendOptionsPanel
from .graph_labels_panel import GraphLabelsPanel
from .time_window_panel import TimeWindowPanel
from .co2_calculation_panel import CO2CalculationPanel
from .rh_calculation_panel import RHCalculationPanel

__all__ = [
    "SeriesSelector",
    "PlotOptionsPanel",
    "LegendOptionsPanel",
    "GraphLabelsPanel",
    "TimeWindowPanel",
    "CO2CalculationPanel",
    "RHCalculationPanel",
]

