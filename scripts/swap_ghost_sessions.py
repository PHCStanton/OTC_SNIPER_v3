import argparse
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def swap_sessions(repair_dir: Path, sessions_dir: Path, archive_dir: Path) -> None:
    manifest_path = repair_dir / "manifest.json"
    if not manifest_path.exists():
        logger.error("Manifest not found in repair directory: %s", manifest_path)
        return

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    repaired_sessions = manifest.get("repaired_sessions", [])
    if not repaired_sessions:
        logger.info("No repaired sessions found in manifest.")
        return

    archive_dir.mkdir(parents=True, exist_ok=True)
    repaired_src_dir = repair_dir / "sessions"

    swapped_count = 0
    for entry in repaired_sessions:
        session_name = entry["session_file"]
        src_file = repaired_src_dir / session_name
        dest_file = sessions_dir / session_name
        
        if not src_file.exists():
            logger.warning("Repaired file missing: %s", src_file)
            continue

        # Backup original
        if dest_file.exists():
            backup_path = archive_dir / f"{session_name}.orig.{int(datetime.now(timezone.utc).timestamp())}"
            shutil.copy2(dest_file, backup_path)
            logger.info("Archived original session: %s -> %s", session_name, backup_path.name)

        # Swap in repaired version
        shutil.copy2(src_file, dest_file)
        logger.info("Swapped repaired session: %s", session_name)
        swapped_count += 1

    logger.info("Successfully swapped %d sessions.", swapped_count)

def main():
    parser = argparse.ArgumentParser(description="Swap repaired ghost sessions into the live sessions directory.")
    parser.add_argument("repair_dir", type=Path, help="Path to the repair folder containing manifest.json and sessions/")
    parser.add_argument("--sessions-dir", type=Path, default=Path("app/data/ghost_trades/sessions"), help="Path to live sessions directory.")
    parser.add_argument("--archive-dir", type=Path, default=Path("app/data/ghost_trades/archive"), help="Path to archive original corrupted files.")
    
    args = parser.parse_args()
    swap_sessions(args.repair_dir, args.sessions_dir, args.archive_dir)

if __name__ == "__main__":
    main()
