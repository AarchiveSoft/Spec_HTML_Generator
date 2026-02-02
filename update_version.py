#!/usr/bin/env python3
"""
Version Update Helper for Claudias Spezifikationen Assistent

Updates version number in all locations:
- auto_update.py (CURRENT_VERSION)
- installer.iss (MyAppVersion)
- README.md (version badge)

Usage: python update_version.py X.Y.Z

Example: python update_version.py 1.2.0
"""

import sys
import re
import os
from pathlib import Path


def validate_semver(version_str: str) -> bool:
    """
    Validate semantic versioning format (X.Y.Z).
    Allows optional pre-release suffix (e.g., 1.0.0-beta).
    """
    pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$'
    return bool(re.match(pattern, version_str))


def update_auto_update_py(file_path: Path, new_version: str) -> bool:
    """Update CURRENT_VERSION in auto_update.py."""
    try:
        content = file_path.read_text(encoding='utf-8')

        # Pattern: CURRENT_VERSION = "X.Y.Z"
        pattern = r'(CURRENT_VERSION\s*=\s*["\'])[\d.]+(-[a-zA-Z0-9.]+)?(["\'])'
        replacement = rf'\g<1>{new_version}\g<3>'

        new_content, count = re.subn(pattern, replacement, content)

        if count == 0:
            print(f"  ERROR: CURRENT_VERSION not found in {file_path.name}")
            return False

        file_path.write_text(new_content, encoding='utf-8')
        print(f"  OK: Updated {file_path.name} -> {new_version}")
        return True

    except Exception as e:
        print(f"  ERROR: Failed to update {file_path.name}: {e}")
        return False


def update_installer_iss(file_path: Path, new_version: str) -> bool:
    """Update MyAppVersion in installer.iss."""
    try:
        content = file_path.read_text(encoding='utf-8')

        # Pattern: #define MyAppVersion "X.Y.Z"
        pattern = r'(#define\s+MyAppVersion\s+["\'])[\d.]+(-[a-zA-Z0-9.]+)?(["\'])'
        replacement = rf'\g<1>{new_version}\g<3>'

        new_content, count = re.subn(pattern, replacement, content)

        if count == 0:
            print(f"  ERROR: MyAppVersion not found in {file_path.name}")
            return False

        file_path.write_text(new_content, encoding='utf-8')
        print(f"  OK: Updated {file_path.name} -> {new_version}")
        return True

    except Exception as e:
        print(f"  ERROR: Failed to update {file_path.name}: {e}")
        return False


def update_readme_badge(file_path: Path, new_version: str) -> bool:
    """Update version badge in README.md."""
    try:
        content = file_path.read_text(encoding='utf-8')

        # Pattern: badge/version-X.Y.Z-blue.svg
        pattern = r'(badge/version-)[\d.]+(-[a-zA-Z0-9.]+)?(-blue\.svg)'
        replacement = rf'\g<1>{new_version}\g<3>'

        new_content, count = re.subn(pattern, replacement, content)

        if count == 0:
            print(f"  WARNING: Version badge not found in {file_path.name}")
            print(f"           Expected pattern: badge/version-X.Y.Z-blue.svg")
            return False

        file_path.write_text(new_content, encoding='utf-8')
        print(f"  OK: Updated {file_path.name} badge -> {new_version}")
        return True

    except Exception as e:
        print(f"  ERROR: Failed to update {file_path.name}: {e}")
        return False


def get_current_version(auto_update_path: Path) -> str:
    """Read current version from auto_update.py."""
    try:
        content = auto_update_path.read_text(encoding='utf-8')
        match = re.search(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    except Exception:
        pass
    return "unknown"


def main():
    """Main entry point."""
    # Check arguments
    if len(sys.argv) != 2:
        print("Usage: python update_version.py X.Y.Z")
        print()
        print("Example: python update_version.py 1.2.0")
        print()
        print("This script updates the version in:")
        print("  - auto_update.py (CURRENT_VERSION)")
        print("  - installer.iss (MyAppVersion)")
        print("  - README.md (version badge)")
        sys.exit(1)

    new_version = sys.argv[1]

    # Validate version format
    if not validate_semver(new_version):
        print(f"ERROR: Invalid version format: {new_version}")
        print("       Expected semantic versioning: X.Y.Z (e.g., 1.2.0)")
        sys.exit(1)

    # Get project root (directory containing this script)
    project_root = Path(__file__).parent.resolve()

    # Define file paths
    files = {
        'auto_update.py': project_root / 'auto_update.py',
        'installer.iss': project_root / 'installer.iss',
        'README.md': project_root / 'README.md',
    }

    # Get current version
    current_version = get_current_version(files['auto_update.py'])

    print("=" * 50)
    print("Version Update Helper")
    print("=" * 50)
    print()
    print(f"Current version: {current_version}")
    print(f"New version:     {new_version}")
    print()

    if current_version == new_version:
        print("WARNING: New version is the same as current version.")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted.")
            sys.exit(0)
        print()

    # Update each file
    print("Updating files...")
    print()

    success_count = 0
    total_count = 0

    # Update auto_update.py
    if files['auto_update.py'].exists():
        total_count += 1
        if update_auto_update_py(files['auto_update.py'], new_version):
            success_count += 1
    else:
        print(f"  SKIP: auto_update.py not found")

    # Update installer.iss
    if files['installer.iss'].exists():
        total_count += 1
        if update_installer_iss(files['installer.iss'], new_version):
            success_count += 1
    else:
        print(f"  SKIP: installer.iss not found")

    # Update README.md
    if files['README.md'].exists():
        total_count += 1
        if update_readme_badge(files['README.md'], new_version):
            success_count += 1
    else:
        print(f"  SKIP: README.md not found")

    print()
    print("=" * 50)
    print(f"Results: {success_count}/{total_count} files updated successfully")
    print("=" * 50)

    if success_count < total_count:
        print()
        print("WARNING: Not all files were updated!")
        print("         Check the errors above and fix manually if needed.")
        sys.exit(1)

    print()
    print("Next steps:")
    print("  1. Review changes: git diff")
    print("  2. Build executable: .\\build.ps1 or build.bat")
    print("  3. Create installer: Run Inno Setup with installer.iss")
    print("  4. Test the installer")
    print("  5. Upload release: python upload_release.py")
    print("  6. Commit and tag: git commit -am 'Release vX.Y.Z'")
    print("                     git tag vX.Y.Z")


if __name__ == "__main__":
    main()
