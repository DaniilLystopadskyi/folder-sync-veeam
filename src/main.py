import os
import shutil
import time
import argparse
import hashlib
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import fnmatch
import json
from logging.handlers import RotatingFileHandler

# Function to set up logging with rotating handler and console output
# The rotating file handler (using RotatingFileHandler) is implemented to avoid large log files.
def setup_logging(log_file):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Rotating file handler (10 MB max per file, keep 5 backups)
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

# Function to compute MD5 hash for file comparison
def hash_file(file_path):
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logging.error(f"Error hashing file {file_path}: {e}")
        return None

# Function to compare files based on size, modification time, and hash
# First compare file sizes and modification times (both of which are very fast) before computing the hash. 
# Only calculate the hash if the file sizes and modification times are the same.
def files_are_different(source_file, replica_file):
    if source_file.stat().st_size != replica_file.stat().st_size:
        return True
    if source_file.stat().st_mtime > replica_file.stat().st_mtime:
        return True
    return hash_file(source_file) != hash_file(replica_file)

# Function to determine if a file should be excluded based on patterns
def should_exclude(file_name, exclude_patterns):
    return any(fnmatch.fnmatch(file_name, pattern) for pattern in exclude_patterns)

# Function to sync source and replica folders
# Paths are handled using pathlib for better cross-platform compatibility.
def sync_folders(source_folder, replica_folder, dry_run, exclude_patterns):
    source_folder = Path(source_folder)
    replica_folder = Path(replica_folder)

    # Ensure the replica folder exists
    if not replica_folder.exists():
        if not dry_run:
            os.makedirs(replica_folder)
        logging.info(f"{'Would create' if dry_run else 'Created'} replica folder: {replica_folder}")

    # Parallelized file operations
    def copy_or_update_file(source_file, replica_file):
        if not dry_run:
            try:
                shutil.copy2(source_file, replica_file)
                logging.info(f"Copied/Updated file: {source_file} -> {replica_file}")
            except Exception as e:
                logging.error(f"Failed to copy {source_file} to {replica_file}: {e}")
        else:
            logging.info(f"Would copy/update file: {source_file} -> {replica_file}")

    # Copy or update files from source to replica
    source_replica_pairs = []
    for source_root, _, files in os.walk(source_folder):
        relative_path = os.path.relpath(source_root, source_folder)
        replica_root = replica_folder / relative_path

        if not replica_root.exists() and not dry_run:
            os.makedirs(replica_root)
            logging.info(f"Created directory: {replica_root}")

        for file_name in files:
            if should_exclude(file_name, exclude_patterns):
                logging.info(f"Excluding file: {file_name}")
                continue

            source_file = Path(source_root) / file_name
            replica_file = replica_root / file_name

            # Compare files before copying
            if not replica_file.exists() or files_are_different(source_file, replica_file):
                source_replica_pairs.append((source_file, replica_file))

    # Use multithreading to parallelize file copying
    # For local or fast network operations, this can reduce the overall sync time.
    with ThreadPoolExecutor() as executor:
        executor.map(lambda pair: copy_or_update_file(*pair), source_replica_pairs)

    # Remove files from replica that don't exist in the source
    for replica_root, dirs, files in os.walk(replica_folder):
        relative_path = os.path.relpath(replica_root, replica_folder)
        source_root = source_folder / relative_path

        for file_name in files:
            replica_file = Path(replica_root) / file_name
            source_file = source_root / file_name
            if not source_file.exists():
                if not dry_run:
                    os.remove(replica_file)
                    logging.info(f"Removed file: {replica_file}")
                else:
                    logging.info(f"Would remove file: {replica_file}")

        for dir_name in dirs:
            replica_dir = Path(replica_root) / dir_name
            source_dir = source_root / dir_name
            if not source_dir.exists():
                if not dry_run:
                    shutil.rmtree(replica_dir)
                    logging.info(f"Removed directory: {replica_dir}")
                else:
                    logging.info(f"Would remove directory: {replica_dir}")

# Main function
def main():
    parser = argparse.ArgumentParser(description="Synchronize source folder with replica folder.")
    parser.add_argument("--source", type=str, help="Source folder path")
    parser.add_argument("--replica", type=str, help="Replica folder path")
    parser.add_argument("--interval", type=int, help="Synchronization interval in seconds")
    parser.add_argument("--logfile", type=str, help="Log file path")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without making changes")
    parser.add_argument("--exclude", nargs="*", default=[], help="List of file patterns to exclude (e.g., *.tmp, .DS_Store)")
    parser.add_argument("--config", type=str, help="Path to JSON config file")

    args = parser.parse_args()

    # Load configuration from JSON file if provided
    if args.config:
        with open(args.config) as config_file:
            config = json.load(config_file)
            source_folder = config.get("source", args.source)
            replica_folder = config.get("replica", args.replica)
            sync_interval = config.get("interval", args.interval)
            log_file = config.get("logfile", args.logfile)
            exclude_patterns = config.get("exclude", args.exclude)
            dry_run = config.get("dry_run", args.dry_run)
    else:
        source_folder = args.source
        replica_folder = args.replica
        sync_interval = args.interval
        log_file = args.logfile
        exclude_patterns = args.exclude
        dry_run = args.dry_run

    # Setup logging
    setup_logging(log_file)

    # Start the synchronization loop
    logging.info("Starting folder synchronization...")
    while True:
        try:
            sync_folders(source_folder, replica_folder, dry_run, exclude_patterns)
        except Exception as e:
            logging.error(f"Error during synchronization: {e}")
        
        time.sleep(sync_interval)

if __name__ == "__main__":
    main()
