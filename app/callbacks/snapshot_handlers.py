import csv
import numpy as np
from typing import List

from PyQt6.QtWidgets import QMessageBox, QMenu, QListWidgetItem
from PyQt6.QtCore import Qt, QPoint

from core import snapshots
from app import plot


class SnapshotHandlers:
    """Handlers for snapshot list: plot, compare, export, delete, refresh."""

    def __init__(self, window) -> None:
        self.window = window

    # Selection notifications
    def on_snapshot_selected(self, item: QListWidgetItem) -> None:
        selected_items = self.window.snapshot_panel.snapshot_list.selectedItems()
        if len(selected_items) > 1:
            print(f"Multiple snapshots selected ({len(selected_items)} items):")
            for selected_item in selected_items:
                print(f"  - {selected_item.text()}")
        else:
            print(f"Snapshot selected: {item.text()}")

    def on_snapshot_double_clicked(self, item: QListWidgetItem) -> None:
        print(f"Snapshot double-clicked: {item.text()}")

    # Context menu
    def show_snapshot_context_menu(self, position: QPoint) -> None:
        list_widget = self.window.snapshot_panel.snapshot_list
        selected_items = list_widget.selectedItems()
        if not selected_items:
            return

        context_menu = QMenu(self.window)

        if len(selected_items) == 1:
            plot_action = context_menu.addAction("Plot")
            save_action = context_menu.addAction("Save")
            context_menu.addSeparator()
            delete_action = context_menu.addAction("Delete")

            plot_action.triggered.connect(lambda: self.plot_snapshot(selected_items[0]))
            save_action.triggered.connect(lambda: self.save_snapshot(selected_items[0]))
            delete_action.triggered.connect(
                lambda: self.delete_snapshots(selected_items)
            )
        else:
            if self.can_compare_snapshots(selected_items):
                compare_action = context_menu.addAction(
                    f"Compare {len(selected_items)} Snapshots"
                )
                compare_action.triggered.connect(
                    lambda: self.compare_snapshots(selected_items)
                )
                context_menu.addSeparator()
            delete_action = context_menu.addAction(
                f"Delete {len(selected_items)} Snapshots"
            )
            delete_action.triggered.connect(
                lambda: self.delete_snapshots(selected_items)
            )

        context_menu.exec(list_widget.mapToGlobal(position))

    def can_compare_snapshots(self, items: List[QListWidgetItem]) -> bool:
        if len(items) < 2:
            return False
        snapshot_uids = []
        for item in items:
            uid = item.data(Qt.ItemDataRole.UserRole)
            snapshot_uids.append(uid)
        return snapshots.can_be_compared(snapshot_uids)

    # Actions
    def plot_snapshot(self, item: QListWidgetItem) -> None:
        print(f"Plotting snapshot: {item.text()}")
        uid = item.data(Qt.ItemDataRole.UserRole)
        if uid not in snapshots.storage:
            QMessageBox.warning(
                self.window,
                "Snapshot Not Found",
                "The selected snapshot could not be found.",
            )
            return
        snapshot = snapshots.storage[uid]
        try:
            plot_window = plot.plot_single_snapshot(snapshot)
            if not hasattr(self.window, "plot_windows"):
                self.window.plot_windows = []
            self.window.plot_windows.append(plot_window)
            print(
                f"Successfully created plot window for snapshot: {snapshot.description}"
            )
        except Exception as exc:
            error_msg = f"Failed to create plot:\n{str(exc)}"
            QMessageBox.critical(self.window, "Plot Error", error_msg)
            print(f"Error creating plot: {exc}")

    def compare_snapshots(self, items: List[QListWidgetItem]) -> None:
        print(f"Comparing {len(items)} snapshots:")
        for item in items:
            print(f"  - {item.text()}")

        snapshots_to_compare = {}
        for item in items:
            uid = item.data(Qt.ItemDataRole.UserRole)
            if uid not in snapshots.storage:
                QMessageBox.warning(
                    self.window,
                    "Snapshot Not Found",
                    f"The snapshot '{item.text()}' could not be found.",
                )
                return
            snapshots_to_compare[uid] = snapshots.storage[uid]
        try:
            plot_window = plot.plot_multiple_snapshots(snapshots_to_compare)
            if not hasattr(self.window, "plot_windows"):
                self.window.plot_windows = []
            self.window.plot_windows.append(plot_window)
            print(
                f"Successfully created comparison plot window for {len(snapshots_to_compare)} snapshots"
            )
        except Exception as exc:
            error_msg = f"Failed to create comparison plot:\n{str(exc)}"
            QMessageBox.critical(self.window, "Plot Error", error_msg)
            print(f"Error creating comparison plot: {exc}")

    def save_snapshot(self, item: QListWidgetItem) -> None:
        print(f"Saving snapshot: {item.text()}")
        uid = item.data(Qt.ItemDataRole.UserRole)
        if uid not in snapshots.storage:
            QMessageBox.warning(
                self.window,
                "Snapshot Not Found",
                "The selected snapshot could not be found.",
            )
            return
        snapshot = snapshots.storage[uid]

        import re

        safe_description = re.sub(r'[<>:"/\\|?*]', "_", snapshot.description)
        default_filename = f"{safe_description}.csv"

        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self.window,
            "Save Snapshot as CSV",
            default_filename,
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            print("Save cancelled by user")
            return
        try:
            self.export_snapshot_to_csv(snapshot, file_path)
            QMessageBox.information(
                self.window,
                "Export Successful",
                f"Snapshot exported successfully to:\n{file_path}",
            )
            print(f"Successfully exported snapshot to: {file_path}")
        except Exception as exc:
            error_msg = f"Failed to export snapshot:\n{str(exc)}"
            QMessageBox.critical(self.window, "Export Error", error_msg)
            print(f"Error exporting snapshot: {exc}")

    def export_snapshot_to_csv(self, snapshot, file_path: str) -> None:
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["# VScope Snapshot Export"])
            writer.writerow(["# Description:", snapshot.description])
            writer.writerow(["# Channels:", snapshot.channels])
            writer.writerow(["# Buffer Length:", snapshot.buffer_length])
            data = snapshot.get_data()
            writer.writerow(["# Devices:", len(data)])
            writer.writerow([])
            if not data:
                writer.writerow(["# No data available in this snapshot"])
                return
            time_samples = np.arange(snapshot.buffer_length)
            for device_idx, (device_id, device_data) in enumerate(data.items()):
                if device_idx > 0:
                    writer.writerow([])
                writer.writerow([f"# Device: {device_id}"])
                header = ["Channel"] + [f"Sample_{i}" for i in time_samples]
                writer.writerow(header)
                for channel in range(snapshot.channels):
                    row = [f"Ch{channel}"] + device_data[channel, :].tolist()
                    writer.writerow(row)

    def delete_snapshots(self, items: List[QListWidgetItem]) -> None:
        if len(items) == 1:
            print(f"Deleting snapshot: {items[0].text()}")
        else:
            print(f"Deleting {len(items)} snapshots:")
            for item in items:
                print(f"  - {item.text()}")

        if len(items) == 1:
            msg = f"Are you sure you want to delete this snapshot?\n\n{items[0].text()}"
        else:
            msg = f"Are you sure you want to delete these {len(items)} snapshots?"

        reply = QMessageBox.question(
            self.window,
            "Confirm Delete",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for item in items:
                uid = item.data(Qt.ItemDataRole.UserRole)
                if uid in snapshots.storage:
                    try:
                        snapshots.storage[uid].delete()
                    except Exception as exc:
                        print(f"Warning: failed to delete cache for UID {uid}: {exc}")
                    del snapshots.storage[uid]
                    deleted_count += 1
                    print(f"Deleted snapshot with UID: {uid}")
            self.refresh_snapshot_list()
            print(f"Successfully deleted {deleted_count} snapshot(s)")
        else:
            print("Delete operation cancelled")

    def refresh_snapshot_list(self) -> None:
        list_widget = self.window.snapshot_panel.snapshot_list
        list_widget.clear()
        sorted_snapshots = sorted(
            snapshots.storage.items(), key=lambda x: x[0], reverse=True
        )
        for uid, snapshot in sorted_snapshots:
            if hasattr(snapshot, "get_device_count"):
                device_count = snapshot.get_device_count()
            else:
                device_count = len(snapshot.get_data())
            timing_prefix = ""
            if hasattr(snapshot, "acquisition_time") and hasattr(
                snapshot, "pretrigger_time"
            ):
                if (
                    snapshot.acquisition_time is not None
                    and snapshot.pretrigger_time is not None
                ):
                    timing_prefix = f"{snapshot.acquisition_time:.3g}:{snapshot.pretrigger_time:.3g}s - "
            display_text = f"{timing_prefix}{device_count}x{snapshot.channels}x{snapshot.buffer_length} - {snapshot.description}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, uid)
            list_widget.addItem(item)
        print(f"Snapshot list refreshed with {len(snapshots.storage)} snapshots")
