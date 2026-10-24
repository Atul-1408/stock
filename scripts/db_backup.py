"""Database Backup & Disaster Recovery Utility for Sovereign Intelligence.

Performs online, non-blocking SQLite backups using the SQLite Online Backup API,
verifies data integrity with PRAGMA integrity_check, compresses archives,
and manages backup retention.
"""

import argparse
import gzip
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "src"))

from config import Config


def backup_database(destination_dir: Path = None, retain_count: int = 14) -> Path:
    """Create a compressed, online backup of the SQLite database.

    Args:
        destination_dir: Directory where backups are written. Defaults to BASE_DIR / "backups".
        retain_count: Number of recent backups to keep before rotating out older ones.

    Returns:
        Path to the created compressed backup file.
    """
    source_db = Path(Config.DB_PATH)
    if not source_db.exists():
        raise FileNotFoundError(f"Source database not found at: {source_db}")

    if destination_dir is None:
        destination_dir = BASE_DIR / "backups"
    destination_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_backup_path = destination_dir / f"backup_{timestamp}.db"
    compressed_backup_path = destination_dir / f"backup_{timestamp}.db.gz"

    print(f"[*] Initiating online SQLite backup from: {source_db}")

    # Use SQLite online backup API to ensure WAL consistency without locking writers
    src_conn = sqlite3.connect(source_db)
    dst_conn = sqlite3.connect(raw_backup_path)

    try:
        with dst_conn:
            src_conn.backup(dst_conn, pages=250, sleep=0.01)
    finally:
        dst_conn.close()
        src_conn.close()

    # Verify integrity of the newly created backup snapshot
    print("[*] Verifying integrity of the backup snapshot...")
    verify_conn = sqlite3.connect(raw_backup_path)
    try:
        integrity_result = verify_conn.execute("PRAGMA integrity_check;").fetchone()
        if not integrity_result or integrity_result[0] != "ok":
            raise RuntimeError(f"Integrity check failed on backup snapshot: {integrity_result}")
        print("[+] Integrity check PASSED: OK")
    finally:
        verify_conn.close()

    # Gzip compress the verified snapshot
    print(f"[*] Compressing backup snapshot to: {compressed_backup_path.name}")
    with open(raw_backup_path, "rb") as f_in, gzip.open(compressed_backup_path, "wb", compresslevel=9) as f_out:
        shutil.copyfileobj(f_in, f_out)

    # Remove uncompressed raw snapshot
    raw_backup_path.unlink()

    raw_size_mb = source_db.stat().st_size / (1024 * 1024)
    comp_size_mb = compressed_backup_path.stat().st_size / (1024 * 1024)
    print(f"[+] Backup completed successfully: {compressed_backup_path} ({comp_size_mb:.2f} MB compressed, from {raw_size_mb:.2f} MB)")

    # Manage retention
    rotate_backups(destination_dir, retain_count)

    return compressed_backup_path


def restore_database(backup_archive: Path, target_db: Path = None, force: bool = False) -> None:
    """Restore database from a compressed backup archive.

    Args:
        backup_archive: Path to the .gz backup file.
        target_db: Destination path for restored DB. Defaults to Config.DB_PATH.
        force: Overwrite existing target DB without interactive confirmation.
    """
    backup_archive = Path(backup_archive)
    if not backup_archive.exists():
        raise FileNotFoundError(f"Backup archive not found: {backup_archive}")

    if target_db is None:
        target_db = Path(Config.DB_PATH)

    if target_db.exists() and not force:
        raise RuntimeError(f"Target DB {target_db} already exists. Specify force=True or provide an empty path.")

    target_db.parent.mkdir(parents=True, exist_ok=True)
    temp_restored = target_db.with_suffix(".tmp_restore")

    print(f"[*] Decompressing {backup_archive} to temporary staging: {temp_restored}")
    with gzip.open(backup_archive, "rb") as f_in, open(temp_restored, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

    # Verify integrity of restored file before replacing target
    print("[*] Verifying integrity of decompressed file...")
    conn = sqlite3.connect(temp_restored)
    try:
        result = conn.execute("PRAGMA integrity_check;").fetchone()
        if not result or result[0] != "ok":
            temp_restored.unlink(missing_ok=True)
            raise RuntimeError(f"Integrity check failed on restored database: {result}")
        print("[+] Restored integrity check PASSED: OK")
    finally:
        conn.close()

    # Move into final location
    if target_db.exists():
        backup_current = target_db.with_suffix(f".pre_restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
        target_db.rename(backup_current)
        print(f"[*] Preserved existing database to: {backup_current}")

    temp_restored.rename(target_db)
    print(f"[+] Database successfully restored to: {target_db}")


def rotate_backups(destination_dir: Path, retain_count: int) -> None:
    """Remove older backups exceeding the retention threshold."""
    backups = sorted(destination_dir.glob("backup_*.db.gz"), key=os.path.getmtime, reverse=True)
    if len(backups) > retain_count:
        for old_backup in backups[retain_count:]:
            print(f"[*] Purging expired backup: {old_backup.name}")
            old_backup.unlink()


def parse_args():
    parser = argparse.ArgumentParser(description="Sovereign Intelligence Database Backup & Recovery")
    parser.add_argument("--action", choices=["backup", "restore"], default="backup", help="Action to perform")
    parser.add_argument("--file", type=str, help="Archive path for restore action")
    parser.add_argument("--retain", type=int, default=14, help="Number of backups to retain")
    parser.add_argument("--force", action="store_true", help="Force restore without prompting")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.action == "backup":
        backup_database(retain_count=args.retain)
    elif args.action == "restore":
        if not args.file:
            print("Error: --file argument is required for restore action.")
            sys.exit(1)
        restore_database(Path(args.file), force=args.force)
