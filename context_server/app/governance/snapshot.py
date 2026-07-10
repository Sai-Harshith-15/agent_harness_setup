"""Snapshot and restore subsystem for crash rollback (Add-on 3.1)."""
import os
import sqlite3

from ..db import CONTROL_DB, TOKEN_DB, connect, _path


def create_snapshot(task_id: str) -> None:
    """Take a backup of the state for a specific task."""
    for db_name in (CONTROL_DB, TOKEN_DB):
        snapshot_name = f"snapshot_{task_id}_{db_name}"
        with connect(db_name) as src_conn:
            dst_conn = sqlite3.connect(_path(snapshot_name))
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()


def restore_snapshot(task_id: str) -> None:
    """Restore the backup of the state for a specific task."""
    for db_name in (CONTROL_DB, TOKEN_DB):
        snapshot_name = f"snapshot_{task_id}_{db_name}"
        snap_path = _path(snapshot_name)
        if os.path.exists(snap_path):
            with sqlite3.connect(snap_path) as src_conn:
                with connect(db_name) as dst_conn:
                    src_conn.backup(dst_conn)
