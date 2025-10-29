"""Domain calculations for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from dateutil import tz


class CO2CalculationError(Exception):
    """Raised when the CO₂ capture calculation cannot be completed."""


@dataclass
class CO2CalculationResult:
    mass_grams: float
    mass_kilograms: float
    time_span_minutes: float
    time_span_hours: float
    capture_rate_g_per_hr: float
    data_points: int
    average_inlet_ppm: float
    average_outlet_ppm: float
    average_flow_slpm: float

    def summary(self) -> str:
        return (
            f"CO₂ Captured: {self.mass_grams:.2f} g ({self.mass_kilograms:.4f} kg) over "
            f"{self.time_span_minutes:.1f} min"
        )


class CO2CaptureCalculator:
    """Perform CO₂ capture calculations under a no-leak assumption."""

    def __init__(self, *, display_timezone: tz.tzfile | str | None = None) -> None:
        if display_timezone is None:
            self.display_timezone = None
        elif isinstance(display_timezone, str):
            self.display_timezone = tz.gettz(display_timezone)
        else:
            self.display_timezone = display_timezone

    def calculate(
        self,
        df: pd.DataFrame,
        *,
        time_column: str,
        inlet_co2_column: str,
        outlet_co2_column: str,
        inlet_flow_column: str,
        molar_volume: float,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> CO2CalculationResult:
        if df.empty:
            raise CO2CalculationError("No data available for calculation.")

        if molar_volume <= 0:
            raise CO2CalculationError("Molar volume must be positive.")

        df_filtered = self._apply_time_window(
            df,
            time_column=time_column,
            start_time=start_time,
            end_time=end_time,
        )

        if df_filtered.empty:
            raise CO2CalculationError("No data within the selected time window.")

        time_seconds = self._time_seconds(df_filtered[time_column])
        inlet_ppm = pd.to_numeric(df_filtered[inlet_co2_column], errors="coerce").to_numpy()
        outlet_ppm = pd.to_numeric(df_filtered[outlet_co2_column], errors="coerce").to_numpy()
        flow_slpm = pd.to_numeric(df_filtered[inlet_flow_column], errors="coerce").to_numpy()

        valid_mask = ~(np.isnan(inlet_ppm) | np.isnan(outlet_ppm) | np.isnan(flow_slpm))
        if not np.any(valid_mask):
            raise CO2CalculationError("No valid data points for calculation.")

        time_seconds = time_seconds[valid_mask]
        inlet_ppm = inlet_ppm[valid_mask]
        outlet_ppm = outlet_ppm[valid_mask]
        flow_slpm = flow_slpm[valid_mask]

        x_in = inlet_ppm / 1e6
        x_out = outlet_ppm / 1e6
        mol_per_second = flow_slpm * (x_in - x_out) / 60.0 / molar_volume

        molar_mass_co2 = 44.01
        mass_grams = molar_mass_co2 * np.trapezoid(mol_per_second, time_seconds)

        time_span_seconds = float(time_seconds[-1] - time_seconds[0])
        time_span_minutes = time_span_seconds / 60.0
        time_span_hours = time_span_minutes / 60.0 if time_span_minutes else 0.0

        if time_span_hours <= 0:
            raise CO2CalculationError("The selected data does not cover a positive time span.")

        return CO2CalculationResult(
            mass_grams=mass_grams,
            mass_kilograms=mass_grams / 1000.0,
            time_span_minutes=time_span_minutes,
            time_span_hours=time_span_hours,
            capture_rate_g_per_hr=mass_grams / time_span_hours,
            data_points=len(time_seconds),
            average_inlet_ppm=float(np.mean(inlet_ppm)),
            average_outlet_ppm=float(np.mean(outlet_ppm)),
            average_flow_slpm=float(np.mean(flow_slpm)),
        )

    def _apply_time_window(
        self,
        df: pd.DataFrame,
        *,
        time_column: str,
        start_time: Optional[str],
        end_time: Optional[str],
    ) -> pd.DataFrame:
        if not start_time and not end_time:
            return df.copy()

        working_df = df.copy()
        tzinfo = self.display_timezone

        def _parse(value: str) -> pd.Timestamp:
            timestamp = pd.to_datetime(value)
            if tzinfo and timestamp.tzinfo is None:
                return timestamp.tz_localize(tzinfo)
            if tzinfo and timestamp.tzinfo is not None:
                return timestamp.tz_convert(tzinfo)
            return timestamp

        if start_time:
            start_ts = _parse(start_time)
            working_df = working_df[working_df[time_column] >= start_ts]

        if end_time:
            end_ts = _parse(end_time)
            working_df = working_df[working_df[time_column] <= end_ts]

        return working_df

    def _time_seconds(self, series: pd.Series) -> np.ndarray:
        if pd.api.types.is_datetime64_any_dtype(series):
            return (series - series.iloc[0]).dt.total_seconds().to_numpy()
        values = pd.to_numeric(series, errors="coerce").to_numpy()
        return values - values[0]
