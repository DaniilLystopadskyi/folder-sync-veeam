# Folder Synchronization Program for Veeam

## Table of Contents:

1.  [Overview](#overview)
2.  [Folder Synchronization Logic](#folder-synchronization-logic)
3.  [How to Use the Program](#how-to-use-the-program)
4.  [Test Suite](#test-suite)

## Overview

The **Folder Synchronization Program** is a Python-based tool that synchronizes two directories: the **source** folder and the **replica** folder. The goal is to maintain an identical copy of the source folder in the replica folder. Synchronization is one-way and ensures that the replica matches the source at all times by periodically syncing them.

### Features:

-   One-way synchronization from **source** to **replica**.
-   File creation, modification, and deletion in the **source** are mirrored in the **replica**.
-   Periodic synchronization at a user-defined interval.
-   Logging of file operations (copying, deletion, etc.) to both console and a log file.
-   Exclusion of files based on patterns (e.g., `*.tmp`).
-   Dry-run functionality for testing synchronization without making changes.
-   Automated test suite for testing various scenarios.


## Folder Synchronization Logic

The folder synchronization is implemented using the `sync_folders()` function in the main Python file. This function ensures that:

1.  All files and subdirectories from the source folder are copied or mirrored to the replica folder.
2.  Any files or directories present in the replica but absent from the source are deleted from the replica to ensure the exact match.
3.  Files can be excluded from synchronization using a pattern-matching mechanism (e.g., exclude all `.tmp` files).

Key points in the synchronization process:

-   Files are copied using `shutil.copy2()` to preserve metadata (e.g., timestamps).
-   The function supports periodic execution using a while loop and sleep intervals.


## How to Use the Program

### Command-Line Arguments

The program accepts several command-line arguments:

-   `--source`: Path to the source folder.
-   `--replica`: Path to the replica folder.
-   `--interval`: Synchronization interval in seconds.
-   `--log`: Path to the log file.
-   `--dry-run`: Optional flag to enable dry-run mode (no changes made to the replica).
-   `--exclude`: Optional list of patterns to exclude from synchronization (e.g., `*.tmp`).

### Example Command:

` python main.py --source "path/to/source" --replica "path/to/replica" --interval 60 --log "sync.log" --exclude "*.tmp" --dry-run `

This command will:

-   Synchronize the contents of the **source** folder to the **replica** folder every 60 seconds.
-   Log the operations in `sync.log`.
-   Exclude files that match the pattern `*.tmp`.
-   Execute in dry-run mode without actually modifying the replica.

## Test Suite

The test suite is implemented using the `unittest` framework. It tests various scenarios for folder synchronization to ensure the correctness of the program. The tests include:

1.  **Test file copy**: Verifies that a file created in the source is correctly copied to the replica.
2.  **Test file deletion**: Ensures that files present in the replica but missing in the source are deleted.
3.  **Test exclude patterns**: Validates that excluded files (based on pattern matching) are not copied to the replica.
4.  **Test dry-run**: Checks that no changes are made to the replica when dry-run mode is enabled.
5.  **Test error handling**: Simulates scenarios where files in the replica are read-only and cannot be overwritten, ensuring error handling and logging.

### Running Tests:

To run the test suite, execute the following command from the project root:

` python -m unittest test_sync.py `

This will run all the test cases and output the results, helping you verify the behavior of the synchronization logic.
