"""
Plot module for VScope - provides plotting windows for snapshots and live data.

This module is organized into:
- styling.py: Colors, line styles, and legend widget
- core_plotting.py: Shared plotting utilities
- snapshot_plot.py: Single and comparison snapshot plots
- live_plot.py: Live data plotting
"""

from .snapshot_plot import plot_single_snapshot, plot_multiple_snapshots
from .live_plot import create_live_plot

__all__ = [
    "plot_single_snapshot",
    "plot_multiple_snapshots",
    "create_live_plot",
]
