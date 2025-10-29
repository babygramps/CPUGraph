"""Data loading and preparation utilities for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd
from dateutil import tz

from config import DISPLAY_TZ_NAME, SENSOR_DESCRIPTIONS


class DataLoadError(Exception):
    """Raised when the input data file cannot be parsed."""


@dataclass
class DataLoadResult:
    """Represents the result of loading a sensor data file."""

    dataframe: pd.DataFrame
    time_column: str
    numeric_columns: List[str]
    display_to_column: Dict[str, str]
    column_to_display: Dict[str, str]
    source_path: Path


class SensorDataLoader:
    """Load CSV/TXT files and prepare them for plotting."""

    def __init__(self, *, sensor_descriptions: Dict[str, str] | None = None, display_timezone: str | tz.tzfile | None = None) -> None:
        self.sensor_descriptions = sensor_descriptions or SENSOR_DESCRIPTIONS
        # Handle both string timezone names and tzfile objects
        if display_timezone is None:
            self.display_timezone = tz.gettz(DISPLAY_TZ_NAME)
            print(f"[DataLoader Init] Using default timezone: {DISPLAY_TZ_NAME}")
        elif isinstance(display_timezone, str):
            self.display_timezone = tz.gettz(display_timezone)
            print(f"[DataLoader Init] Using timezone from string: {display_timezone}")
        else:
            # Already a timezone object
            self.display_timezone = display_timezone
            print(f"[DataLoader Init] Using timezone object: {display_timezone}")

    def load(self, path: str | Path) -> DataLoadResult:
        """Load the given data file and return a structured result."""
        file_path = Path(path)
        if not file_path.exists():
            raise DataLoadError(f"File not found: {file_path}")

        delimiter = "\t" if file_path.suffix.lower() == ".txt" else ","

        df = pd.read_csv(file_path, delimiter=delimiter)
        if df.empty:
            raise DataLoadError("The selected file is empty.")

        time_column = self._infer_time_column(df)
        if time_column is None:
            raise DataLoadError("Could not locate a time-like column (e.g. 'YYMMDD_HHMMSS', 'time', or 'timestamp').")

        dt_series = self._to_datetime(df[time_column])
        if dt_series.notna().sum() == 0:
            raise DataLoadError(f"Could not parse timestamps in column '{time_column}'.")

        df[time_column] = dt_series
        df = df.dropna(subset=[time_column]).sort_values(time_column).reset_index(drop=True)

        df["_plot_time"] = self._to_display_timezone(df[time_column])

        numeric_columns = self._numeric_columns(df, exclude={time_column})
        if not numeric_columns:
            raise DataLoadError("No numeric columns were detected to plot.")

        display_to_column, column_to_display = self._build_display_maps(numeric_columns)

        return DataLoadResult(
            dataframe=df,
            time_column=time_column,
            numeric_columns=numeric_columns,
            display_to_column=display_to_column,
            column_to_display=column_to_display,
            source_path=file_path,
        )

    def _infer_time_column(self, df: pd.DataFrame) -> str | None:
        candidates: List[str] = []
        if "YYMMDD_HHMMSS" in df.columns:
            candidates.append("YYMMDD_HHMMSS")

        for column in df.columns:
            lowered = column.lower()
            if any(keyword in lowered for keyword in ("time", "date", "timestamp")) and column not in candidates:
                candidates.append(column)

        return candidates[0] if candidates else None

    def _to_datetime(self, series: pd.Series) -> pd.Series:
        try:
            return pd.to_datetime(series, format="%y%m%d_%H%M%S", errors="coerce")
        except Exception:
            return pd.to_datetime(series, errors="coerce")

    def _to_display_timezone(self, series: pd.Series) -> pd.Series:
        localized = pd.to_datetime(series, errors="coerce")
        try:
            if getattr(localized.dt, "tz", None) is None:
                localized = localized.dt.tz_localize(self.display_timezone)
            else:
                localized = localized.dt.tz_convert(self.display_timezone)
        except Exception:
            localized = localized.apply(
                lambda value: value.tz_localize(self.display_timezone)
                if pd.notna(value) and value.tzinfo is None
                else (value.tz_convert(self.display_timezone) if pd.notna(value) else value)
            )
        return localized

    def _numeric_columns(self, df: pd.DataFrame, *, exclude: Iterable[str] | None = None) -> List[str]:
        exclude = set(exclude or ())
        numeric_columns: List[str] = []
        for column in df.columns:
            if column in exclude:
                continue
            numeric_series = pd.to_numeric(df[column], errors="coerce")
            if numeric_series.notna().sum() > 0:
                numeric_columns.append(column)
        return numeric_columns

    def _build_display_maps(self, columns: Iterable[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
        display_to_column: Dict[str, str] = {}
        column_to_display: Dict[str, str] = {}

        for column in columns:
            display_name = self._display_name_for(column)
            display_to_column[display_name] = column
            column_to_display[column] = display_name

        return display_to_column, column_to_display

    def _display_name_for(self, column: str) -> str:
        upper_column = column.upper()
        for sensor_id, description in self.sensor_descriptions.items():
            if sensor_id in upper_column:
                return f"{column} - {description}"
        return column
