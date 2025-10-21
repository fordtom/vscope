import json
import os
import shutil
import time
from typing import Dict, List, Optional

import numpy as np
from platformdirs import user_cache_dir

storage: Dict[float, "Snapshot"] = {}


def _get_cache_root_directory() -> str:
    """Return the platform-specific cache root for the application.

    Layout is: <user_cache_dir("vscope")>/<uid>/{metadata.json,data.npz}
    """
    return user_cache_dir("vscope")


class Snapshot:
    def __init__(
        self,
        uid: float,
        description: str,
        channels: int,
        buffer_length: int,
        acquisition_time: Optional[float],
        pretrigger_time: Optional[float],
        channel_labels: List[str],
        data: Optional[Dict[str, np.ndarray]] = None,
    ) -> None:
        """Represents a captured snapshot of device data.

        Data is lazily loaded from cache when first accessed via get_data().
        """
        self.uid = uid
        self.description = description
        self.channels = channels
        self.buffer_length = buffer_length
        self.acquisition_time = acquisition_time
        self.pretrigger_time = pretrigger_time
        self.channel_labels = channel_labels
        # When loaded from cache-only, this remains None and is populated on first get_data()
        self.data: Optional[Dict[str, np.ndarray]] = data

    def _get_snapshot_cache_dir(self) -> str:
        cache_root = _get_cache_root_directory()
        return os.path.join(cache_root, str(self.uid))

    def _get_metadata_path(self) -> str:
        return os.path.join(self._get_snapshot_cache_dir(), "metadata.json")

    def _get_npz_path(self) -> str:
        return os.path.join(self._get_snapshot_cache_dir(), "data.npz")

    def set_data(self, device_id: str, data: np.ndarray) -> None:
        """Append device data to this snapshot, validating shape.

        The data array must be shaped as [channels, buffer_length].
        If a duplicate device_id is provided, a unique key will be created by
        appending an underscore.
        """
        expected_shape = (self.channels, self.buffer_length)
        if data.shape != expected_shape:
            raise ValueError(
                f"Data shape {data.shape} does not match expected shape {expected_shape}"
            )

        if self.data is None:
            self.data = {}

        if device_id not in self.data:
            self.data[device_id] = data
        else:
            # Ensure uniqueness if the same device key is used repeatedly
            suffix_index = 1
            new_key = f"{device_id}_"
            while new_key in self.data:
                suffix_index += 1
                new_key = f"{device_id}_{suffix_index}"
            self.data[new_key] = data

    def get_data(self) -> Dict[str, np.ndarray]:
        """Return all device data for this snapshot, loading from cache if needed."""
        if self.data is None:
            npz_path = self._get_npz_path()
            if os.path.exists(npz_path):
                with np.load(npz_path) as npz_file:
                    self.data = {}
                    for key in npz_file.files:
                        self.set_data(key, npz_file[key])
            else:
                # No data available on disk; initialize to empty dict
                self.data = {}
        return self.data

    def cache(self) -> None:
        """Persist this snapshot to the platform cache directory.

        Writes metadata.json (all fields except data) and data.npz (device arrays).
        """
        snapshot_dir = self._get_snapshot_cache_dir()
        os.makedirs(snapshot_dir, exist_ok=True)

        # Write metadata
        metadata = {
            "uid": self.uid,
            "description": self.description,
            "channels": self.channels,
            "buffer_length": self.buffer_length,
            "acquisition_time": self.acquisition_time,
            "pretrigger_time": self.pretrigger_time,
            "channel_labels": self.channel_labels,
        }
        with open(self._get_metadata_path(), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # Write data arrays
        data = self.get_data()
        if data and len(data) > 0:
            np.savez(self._get_npz_path(), **data)

    def delete(self) -> None:
        """Remove the persisted cache entry for this snapshot, if present."""
        snapshot_dir = self._get_snapshot_cache_dir()
        if os.path.isdir(snapshot_dir):
            shutil.rmtree(snapshot_dir, ignore_errors=True)

    def get_device_ids(self) -> List[str]:
        """Return list of device IDs recorded in this snapshot without forcing full data load."""
        if self.data is not None:
            return list(self.data.keys())
        npz_path = self._get_npz_path()
        if os.path.exists(npz_path):
            with np.load(npz_path) as npz_file:
                return list(npz_file.files)
        return []

    def get_device_count(self) -> int:
        """Return number of devices recorded in this snapshot without loading arrays."""
        return len(self.get_device_ids())


def new(
    description: str,
    channels: int,
    buffer_length: int,
    acquisition_time: float,
    pretrigger_time: float,
    channel_labels: List[str],
) -> float:
    """Create a new in-memory snapshot and return its UID."""
    uid = time.time()
    storage[uid] = Snapshot(
        uid,
        description,
        channels,
        buffer_length,
        acquisition_time,
        pretrigger_time,
        channel_labels,
        data={},
    )
    return uid


def load_from_cache(retention_days: Optional[int] = None) -> None:
    """Populate storage with snapshot metadata from cache without loading data arrays.

    Args:
        retention_days: Number of days to retain snapshots. Older entries are
            deleted during load. If None, defaults to 31 days.

    Only metadata.json is read for each snapshot; data remains lazily loaded.
    """
    cache_root = _get_cache_root_directory()
    if not os.path.isdir(cache_root):
        return

    # Compute cutoff timestamp for garbage collection based on retention
    if retention_days is None:
        retention_days = 31
    try:
        retention_days_int = int(retention_days)
    except Exception:
        retention_days_int = 31
    now_ts = time.time()
    cutoff_ts = now_ts - (retention_days_int * 24 * 60 * 60)

    for entry in os.listdir(cache_root):
        snapshot_dir = os.path.join(cache_root, entry)
        if not os.path.isdir(snapshot_dir):
            continue
        metadata_path = os.path.join(snapshot_dir, "metadata.json")

        # Garbage collect old snapshots based on UID (folder name or metadata)
        try:
            uid_from_name = float(entry)
            uid_value_for_gc = uid_from_name
        except Exception:
            uid_value_for_gc = None

        if uid_value_for_gc is None and os.path.isfile(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    meta_gc = json.load(f)
                uid_meta = meta_gc.get("uid")
                if uid_meta is not None:
                    uid_value_for_gc = float(uid_meta)
            except Exception:
                uid_value_for_gc = None

        if uid_value_for_gc is not None and uid_value_for_gc <= cutoff_ts:
            shutil.rmtree(snapshot_dir, ignore_errors=True)
            continue
        if not os.path.isfile(metadata_path):
            continue
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            uid_value = float(meta.get("uid", entry))
            description = meta["description"]
            channels = int(meta["channels"])
            buffer_length = int(meta["buffer_length"])
            acquisition_time = (
                float(meta["acquisition_time"])
                if meta["acquisition_time"] is not None
                else None
            )
            pretrigger_time = (
                float(meta["pretrigger_time"])
                if meta["pretrigger_time"] is not None
                else None
            )
            channel_labels = list(meta.get("channel_labels", []))

            # Create snapshot with data left as None for lazy load
            snapshot = Snapshot(
                uid=uid_value,
                description=description,
                channels=channels,
                buffer_length=buffer_length,
                acquisition_time=acquisition_time,
                pretrigger_time=pretrigger_time,
                channel_labels=channel_labels,
                data=None,
            )
            storage[uid_value] = snapshot
        except Exception:
            # Skip malformed entries silently to avoid crashing GUI startup
            continue


def can_be_compared(snapshots: List[float]) -> bool:
    """Check if snapshots can be compared by verifying all critical fields match exactly.

    Args:
        snapshots: List of snapshot UIDs to check

    Returns:
        bool: True if all snapshots have matching channels, buffer_length,
              acquisition_time, pretrigger_time, and channel_labels
    """
    if len(snapshots) < 2:
        return False

    # Check if all snapshots exist in storage
    for uid in snapshots:
        if uid not in storage:
            return False

    # Get first snapshot as reference
    first_snapshot = storage[snapshots[0]]

    # Check if first snapshot has all required attributes
    required_attrs = [
        "channels",
        "buffer_length",
        "acquisition_time",
        "pretrigger_time",
        "channel_labels",
    ]
    for attr in required_attrs:
        if not hasattr(first_snapshot, attr) or getattr(first_snapshot, attr) is None:
            return False

    # Compare all other snapshots against the first one - require exact matches for precision
    for uid in snapshots[1:]:
        snapshot = storage[uid]

        # Check if snapshot has all required attributes
        for attr in required_attrs:
            if not hasattr(snapshot, attr) or getattr(snapshot, attr) is None:
                return False

        # Check exact matches for all fields - no tolerance for timing precision
        if (
            snapshot.channels != first_snapshot.channels
            or snapshot.buffer_length != first_snapshot.buffer_length
            or snapshot.acquisition_time != first_snapshot.acquisition_time
            or snapshot.pretrigger_time != first_snapshot.pretrigger_time
            or snapshot.channel_labels != first_snapshot.channel_labels
        ):
            return False

    return True
