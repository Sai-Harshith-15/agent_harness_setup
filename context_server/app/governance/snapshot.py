"""Snapshot and restore subsystem for crash rollback (Add-on 3.1)."""
import os
import sqlite3
import shutil

from ..db import CONTROL_DB, TOKEN_DB, _path, connect


def _ignore_large_dirs(dir_path, contents):
    """Ignore large or unnecessary directories for workspace snapshots."""
    return [c for c in contents if c in (
        '.git', 'node_modules', '__pycache__', '.pytest_cache',
        '.ruff_cache', 'hooks', 'test_hooks', '.next'
    )]


def create_snapshot(task_id: str) -> None:
    """Take a backup of the state for a specific task."""
    for db_name in (CONTROL_DB, TOKEN_DB):
        snapshot_name = f"snapshot_{task_id}_{db_name}"
        with connect(db_name) as src_conn:
            dst_conn = sqlite3.connect(_path(snapshot_name))
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()

    # Create workspace snapshot
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    snapshot_dir = _path(f"snapshot_{task_id}_workspace")
    if os.path.exists(snapshot_dir):
        shutil.rmtree(snapshot_dir)
    shutil.copytree(workspace_root, snapshot_dir, ignore=_ignore_large_dirs, dirs_exist_ok=True)


def restore_snapshot(task_id: str) -> None:
    """Restore the backup of the state for a specific task."""
    for db_name in (CONTROL_DB, TOKEN_DB):
        snapshot_name = f"snapshot_{task_id}_{db_name}"
        snap_path = _path(snapshot_name)
        if os.path.exists(snap_path):
            with sqlite3.connect(snap_path) as src_conn:
                with connect(db_name) as dst_conn:
                    src_conn.backup(dst_conn)

    # Restore workspace snapshot
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    snapshot_dir = _path(f"snapshot_{task_id}_workspace")
    if os.path.exists(snapshot_dir):
        # We need to copy files back, but avoid deleting ignored directories like .git or node_modules.
        # We use dirs_exist_ok=True to overlay the backup back onto the workspace.
        shutil.copytree(snapshot_dir, workspace_root, dirs_exist_ok=True)
