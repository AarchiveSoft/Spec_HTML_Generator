#!/usr/bin/env python3
"""
FTP Upload Script for Claudias Spezifikationen Assistent

Uploads installer to downloads.graphicart.ch/SpecHTMLGenerator/
- Uploads as latest.exe
- Generates version.json
- Archives old versions
- Auto-creates directories if missing

Usage: python upload_release.py [--password PASSWORD]

FTP Credentials:
  Host: graphicart.ch
  User: a.hafner@graphicart.tld
  Password: (prompted or via --password)
"""

import os
import sys
import json
import ftplib
import getpass
import argparse
import re
from datetime import datetime
from pathlib import Path

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
APP_NAME = "ListenWichtel"
FTP_HOST = "graphicart.ch"
FTP_USER = "a.hafner@graphicart.tld"
FTP_REMOTE_DIR = f"/{APP_NAME}"

# Local paths
PROJECT_ROOT = Path(__file__).parent.resolve()
INSTALLER_OUTPUT_DIR = PROJECT_ROOT / "installer_output"
AUTO_UPDATE_FILE = PROJECT_ROOT / "auto_update.py"

# Download URL base (for version.json)
DOWNLOAD_URL_BASE = f"https://downloads.graphicart.ch/{APP_NAME}"


def get_current_version() -> str:
    """Read current version from auto_update.py."""
    try:
        content = AUTO_UPDATE_FILE.read_text(encoding='utf-8')
        match = re.search(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"ERROR: Could not read version from auto_update.py: {e}")
    return "0.0.0"


def find_latest_installer() -> Path:
    """Find the latest installer in installer_output/."""
    if not INSTALLER_OUTPUT_DIR.exists():
        return None

    # Look for setup files
    installers = list(INSTALLER_OUTPUT_DIR.glob(f"{APP_NAME}_Setup_*.exe"))
    if not installers:
        installers = list(INSTALLER_OUTPUT_DIR.glob("*.exe"))

    if not installers:
        return None

    # Return the most recently modified
    return max(installers, key=lambda p: p.stat().st_mtime)


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def ensure_remote_dir(ftp: ftplib.FTP, remote_path: str):
    """
    Ensure remote directory exists, creating it if necessary.
    Handles nested paths by navigating through each part.
    """
    parts = [p for p in remote_path.split('/') if p]

    # Start from root
    try:
        ftp.cwd('/')
    except ftplib.error_perm:
        pass

    current_path = ''
    for part in parts:
        current_path += '/' + part
        try:
            ftp.cwd(current_path)
        except ftplib.error_perm:
            # Directory doesn't exist, try to create it
            try:
                ftp.mkd(current_path)
                print(f"  Created directory: {current_path}")
                ftp.cwd(current_path)
            except ftplib.error_perm as e:
                print(f"  ERROR: Could not create directory {current_path}: {e}")
                raise


def list_remote_files(ftp: ftplib.FTP, pattern: str = None) -> list:
    """List files in current remote directory."""
    try:
        files = ftp.nlst()
        if pattern:
            files = [f for f in files if pattern in f]
        return files
    except ftplib.error_perm:
        return []


def archive_old_version(ftp: ftplib.FTP, current_version: str):
    """
    Archive current latest.exe before uploading new one.
    Renames to {APP_NAME}_v{version}.exe in archive/ subdirectory.
    """
    try:
        # Check if latest.exe exists
        files = list_remote_files(ftp)
        if 'latest.exe' not in files:
            return

        # Ensure archive directory exists
        archive_dir = 'archive'
        try:
            ftp.cwd(archive_dir)
            ftp.cwd('..')
        except ftplib.error_perm:
            ftp.mkd(archive_dir)
            print(f"  Created archive directory")

        # Try to read old version from version.json
        old_version = None
        if 'version.json' in files:
            try:
                lines = []
                ftp.retrlines('RETR version.json', lines.append)
                data = json.loads('\n'.join(lines))
                old_version = data.get('version')
            except Exception:
                pass

        if old_version and old_version != current_version:
            archive_name = f"{archive_dir}/{APP_NAME}_v{old_version}.exe"
            try:
                ftp.rename('latest.exe', archive_name)
                print(f"  Archived old version: {archive_name}")
            except ftplib.error_perm as e:
                print(f"  WARNING: Could not archive old version: {e}")

    except Exception as e:
        print(f"  WARNING: Archive operation failed: {e}")


def upload_file(ftp: ftplib.FTP, local_path: Path, remote_name: str):
    """Upload a file with progress display."""
    file_size = local_path.stat().st_size
    uploaded = [0]

    def callback(data):
        uploaded[0] += len(data)
        percent = (uploaded[0] / file_size) * 100
        bar_width = 40
        filled = int(bar_width * uploaded[0] / file_size)
        bar = '=' * filled + '-' * (bar_width - filled)
        sys.stdout.write(f"\r  [{bar}] {percent:.1f}% ({format_size(uploaded[0])})")
        sys.stdout.flush()

    print(f"  Uploading: {local_path.name} -> {remote_name}")
    print(f"  Size: {format_size(file_size)}")

    with open(local_path, 'rb') as f:
        ftp.storbinary(f'STOR {remote_name}', f, 8192, callback)

    print()  # New line after progress bar
    print(f"  OK: Upload complete")


def generate_version_json(version: str, installer_path: Path, release_notes: str = None) -> dict:
    """Generate version.json content."""
    file_size = installer_path.stat().st_size

    return {
        "version": version,
        "download_url": f"{DOWNLOAD_URL_BASE}/latest.exe",
        "file_size": file_size,
        "file_size_human": format_size(file_size),
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "release_notes": release_notes or f"Version {version}",
        "minimum_version": "1.0.0",
        "checksum_sha256": "",  # TODO: Add SHA256 checksum
    }


def upload_version_json(ftp: ftplib.FTP, version_data: dict):
    """Upload version.json file."""
    import io

    json_content = json.dumps(version_data, indent=2, ensure_ascii=False)
    json_bytes = json_content.encode('utf-8')

    print(f"  Uploading: version.json")
    ftp.storbinary('STOR version.json', io.BytesIO(json_bytes))
    print(f"  OK: version.json uploaded")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Upload release to FTP server',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--password', '-p', help='FTP password (will prompt if not provided)')
    parser.add_argument('--notes', '-n', help='Release notes for version.json')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without uploading')
    args = parser.parse_args()

    print("=" * 60)
    print("FTP Upload Script for " + APP_NAME)
    print("=" * 60)
    print()

    # Get current version
    version = get_current_version()
    print(f"Version: {version}")
    print()

    # Find installer
    installer_path = find_latest_installer()
    if not installer_path:
        print("ERROR: No installer found in installer_output/")
        print("       Run Inno Setup first to create the installer.")
        sys.exit(1)

    print(f"Installer: {installer_path.name}")
    print(f"Size: {format_size(installer_path.stat().st_size)}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would upload:")
        print(f"  - {installer_path.name} -> latest.exe")
        print(f"  - version.json")
        print(f"  Remote: ftp://{FTP_HOST}{FTP_REMOTE_DIR}/")
        return

    # Get password
    password = args.password
    if not password:
        password = input(f"FTP Password for {FTP_USER}: ")

    if not password:
        print("ERROR: Password required")
        sys.exit(1)

    print()
    print(f"Connecting to {FTP_HOST}...")

    try:
        # Connect to FTP
        ftp = ftplib.FTP(FTP_HOST, encoding='utf-8')
        ftp.login(FTP_USER, password)
        print(f"  OK: Connected as {FTP_USER}")

        # Ensure remote directory exists
        print()
        print(f"Preparing remote directory: {FTP_REMOTE_DIR}")
        ensure_remote_dir(ftp, FTP_REMOTE_DIR)
        print(f"  OK: Remote directory ready")

        # Archive old version
        print()
        print("Archiving old version...")
        archive_old_version(ftp, version)

        # Upload installer as latest.exe
        print()
        print("Uploading installer...")
        upload_file(ftp, installer_path, 'latest.exe')

        # Generate and upload version.json
        print()
        print("Generating version.json...")
        release_notes = args.notes or input("Enter release notes (or press Enter for default): ").strip()
        if not release_notes:
            release_notes = f"Version {version}"

        version_data = generate_version_json(version, installer_path, release_notes)
        upload_version_json(ftp, version_data)

        # Done
        ftp.quit()

        print()
        print("=" * 60)
        print("Upload Complete!")
        print("=" * 60)
        print()
        print(f"Download URL: {DOWNLOAD_URL_BASE}/latest.exe")
        print(f"Version JSON: {DOWNLOAD_URL_BASE}/version.json")
        print()
        print("Next steps:")
        print("  1. Test the download URL in a browser")
        print("  2. Test auto-update from an older version")
        print("  3. Commit and tag the release: git tag v" + version)

    except ftplib.error_perm as e:
        print(f"ERROR: FTP permission error: {e}")
        sys.exit(1)
    except ftplib.error_temp as e:
        print(f"ERROR: FTP temporary error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
