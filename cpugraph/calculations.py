"""Domain calculations for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from dateutil import tz


class CO2CalculationError(Exception):
    """Raised when the CO₂ capture calculation cannot be completed."""


class RHCalculationError(Exception):
    """Raised when the relative humidity calculation cannot be completed."""


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


@dataclass
class RHCalculationResult:
    """Result of relative humidity calculation from temperature and dew point."""
    average_rh_percent: float
    min_rh_percent: float
    max_rh_percent: float
    data_points: int
    average_temperature_c: float
    average_dewpoint_c: float
    time_span_minutes: float

    def summary(self) -> str:
        return (
            f"Average RH: {self.average_rh_percent:.1f}% "
            f"(Min: {self.min_rh_percent:.1f}%, Max: {self.max_rh_percent:.1f}%)"
        )


class RHCalculator:
    """Calculate relative humidity from temperature and dew point using Magnus-Tetens formula."""

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
        temperature_column: str,
        dewpoint_column: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> RHCalculationResult:
        """Calculate relative humidity from temperature and dew point.
        
        Uses the Magnus-Tetens formula:
        RH = 100 × exp((17.625 × Td) / (243.04 + Td)) / exp((17.625 × T) / (243.04 + T))
        
        Where T is air temperature (°C) and Td is dew point temperature (°C).
        
        Args:
            df: DataFrame containing the data
            time_column: Name of time column
            temperature_column: Name of temperature column (°C)
            dewpoint_column: Name of dew point column (°C)
            start_time: Optional start time for filtering
            end_time: Optional end time for filtering
            
        Returns:
            RHCalculationResult with statistics about the calculated RH
            
        Raises:
            RHCalculationError: If calculation cannot be performed
        """
        if df.empty:
            raise RHCalculationError("No data available for calculation.")

        df_filtered = self._apply_time_window(
            df,
            time_column=time_column,
            start_time=start_time,
            end_time=end_time,
        )

        if df_filtered.empty:
            raise RHCalculationError("No data within the selected time window.")

        # Extract numeric values
        temp_c = pd.to_numeric(df_filtered[temperature_column], errors="coerce").to_numpy()
        dewpoint_c = pd.to_numeric(df_filtered[dewpoint_column], errors="coerce").to_numpy()
        time_values = df_filtered[time_column]

        # Filter out invalid data
        valid_mask = ~(np.isnan(temp_c) | np.isnan(dewpoint_c))
        
        # Additional validation: dew point cannot be higher than temperature
        valid_mask &= (dewpoint_c <= temp_c)
        
        if not np.any(valid_mask):
            raise RHCalculationError("No valid data points for calculation. Check that dew point ≤ temperature.")

        temp_c = temp_c[valid_mask]
        dewpoint_c = dewpoint_c[valid_mask]

        # Calculate relative humidity using Magnus-Tetens formula
        # Constants for Magnus-Tetens formula
        a = 17.625
        b = 243.04  # °C

        # Saturation vapor pressure at dew point (numerator)
        e_dewpoint = np.exp((a * dewpoint_c) / (b + dewpoint_c))
        
        # Saturation vapor pressure at air temperature (denominator)
        e_temp = np.exp((a * temp_c) / (b + temp_c))
        
        # Relative humidity (%)
        rh_percent = 100.0 * (e_dewpoint / e_temp)
        
        # Clamp to valid range [0, 100] to handle any numerical issues
        rh_percent = np.clip(rh_percent, 0.0, 100.0)

        # Calculate time span
        if len(time_values) > 1:
            time_span_seconds = (time_values.iloc[-1] - time_values.iloc[0]).total_seconds()
            time_span_minutes = time_span_seconds / 60.0
        else:
            time_span_minutes = 0.0

        return RHCalculationResult(
            average_rh_percent=float(np.mean(rh_percent)),
            min_rh_percent=float(np.min(rh_percent)),
            max_rh_percent=float(np.max(rh_percent)),
            data_points=len(rh_percent),
            average_temperature_c=float(np.mean(temp_c)),
            average_dewpoint_c=float(np.mean(dewpoint_c)),
            time_span_minutes=time_span_minutes,
        )

    def _apply_time_window(
        self,
        df: pd.DataFrame,
        *,
        time_column: str,
        start_time: Optional[str],
        end_time: Optional[str],
    ) -> pd.DataFrame:
        """Apply time window filtering (same logic as CO2Calculator)."""
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
