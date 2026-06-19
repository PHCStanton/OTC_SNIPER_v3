import os
import sys
import shutil
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("installer")

def get_paths():
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent.parent
    return script_dir, workspace_root

def run_install(script_dir, workspace_root):
    manifest_path = script_dir / "manifest.json"
    if not manifest_path.exists():
        logger.error("manifest.json not found at %s", manifest_path)
        sys.exit(1)
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    logger.info("Installing plugin: %s v%s", manifest["name"], manifest["version"])
    
    # 1. Copy backend files
    for f_info in manifest.get("backend_files", []):
        src = script_dir / f_info["src"]
        dest = workspace_root / f_info["dest"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        logger.info("Copied backend file: %s -> %s", src.name, f_info["dest"])
        
    # 2. Copy frontend files
    for f_info in manifest.get("frontend_files", []):
        src = script_dir / f_info["src"]
        dest = workspace_root / f_info["dest"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        logger.info("Copied frontend file: %s -> %s", src.name, f_info["dest"])
        
    # 3. Apply injection points
    for inj in manifest.get("injection_points", []):
        target = workspace_root / inj["target_file"]
        if not target.exists():
            logger.error("Target file for injection not found: %s", target)
            rollback(manifest, script_dir, workspace_root)
            sys.exit(1)
            
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Create a backup before making any changes (if not already backed up by premium)
        bak_file = target.with_suffix(target.suffix + ".bak2")
        if not bak_file.exists():
            shutil.copy2(target, bak_file)
            logger.info("Created backup: %s", bak_file.name)
            
        find_pattern = inj["find_pattern"]
        repl_code = inj["replacement_code"]
        
        if find_pattern not in content:
            if repl_code in content:
                logger.info("Pattern already injected in %s", target.name)
                continue
            logger.error("Could not find pattern in %s: %s", target.name, find_pattern[:50] + "...")
            rollback(manifest, script_dir, workspace_root)
            sys.exit(1)
            
        new_content = content.replace(find_pattern, repl_code)
        with open(target, "w", encoding="utf-8") as f:
            f.write(new_content)
        logger.info("Successfully injected code into %s", target.name)
        
    logger.info("Installation completed successfully!")

def rollback(manifest, script_dir, workspace_root):
    logger.warning("Rolling back installation due to failure...")
    
    # Remove backend files
    for f_info in manifest.get("backend_files", []):
        dest = workspace_root / f_info["dest"]
        if dest.exists():
            dest.unlink()
            logger.info("Removed: %s", f_info["dest"])
            
    # Remove frontend files
    for f_info in manifest.get("frontend_files", []):
        dest = workspace_root / f_info["dest"]
        if dest.exists():
            dest.unlink()
            logger.info("Removed: %s", f_info["dest"])
            
    # Restore target backups
    for inj in manifest.get("injection_points", []):
        target = workspace_root / inj["target_file"]
        bak_file = target.with_suffix(target.suffix + ".bak2")
        if bak_file.exists():
            shutil.copy2(bak_file, target)
            bak_file.unlink()
            logger.info("Restored target backup for %s", target.name)

def run_uninstall(script_dir, workspace_root):
    manifest_path = script_dir / "manifest.json"
    if not manifest_path.exists():
        logger.error("manifest.json not found at %s", manifest_path)
        sys.exit(1)
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    logger.info("Uninstalling plugin: %s v%s", manifest["name"], manifest["version"])
    
    # 1. Revert injection points
    for inj in manifest.get("injection_points", []):
        target = workspace_root / inj["target_file"]
        if not target.exists():
            continue
            
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
            
        find_pattern = inj["find_pattern"]
        repl_code = inj["replacement_code"]
        
        if repl_code in content:
            new_content = content.replace(repl_code, find_pattern)
            with open(target, "w", encoding="utf-8") as f:
                f.write(new_content)
            logger.info("Reverted injection in %s", target.name)
            
        # Clean up backup files
        bak_file = target.with_suffix(target.suffix + ".bak2")
        if bak_file.exists():
            bak_file.unlink()
            logger.info("Cleaned up backup file %s", bak_file.name)
            
    # 2. Delete frontend files
    for f_info in manifest.get("frontend_files", []):
        dest = workspace_root / f_info["dest"]
        if dest.exists():
            dest.unlink()
            logger.info("Deleted: %s", f_info["dest"])
            
    # 3. Delete backend files
    for f_info in manifest.get("backend_files", []):
        dest = workspace_root / f_info["dest"]
        if dest.exists():
            dest.unlink()
            logger.info("Deleted: %s", f_info["dest"])
            
    logger.info("Uninstallation completed successfully!")

if __name__ == "__main__":
    script_dir, workspace_root = get_paths()
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        run_uninstall(script_dir, workspace_root)
    else:
        run_install(script_dir, workspace_root)
