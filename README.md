<p align="left">
  <img src="icons/robot_gra.png" alt="Listenwichtel Logo" width="200"/>
</p>


# Claudias Listenwichtel


[![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)](https://github.com/AarchiveSoft/Spec_HTML_Generator/releases)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)](https://pypi.org/project/PySide6/)

A desktop application for creating and managing technical specification tables with rich text formatting, designed for easy HTML export.

## Features

- **Rich Text Editing**: Bold, italic, colors, and bullet lists
- **Category Sections**: Organize specifications with headers
- **HTML Export**: Clean, styled HTML tables ready to paste
- **File Import**: Open and edit existing specification files
- **Auto-Update**: Silent update checking with one-click installation

## Installation

### From Installer (Recommended)

Download the latest installer from the releases page and run it.

### From Source

```powershell
# Clone repository
git clone https://github.com/yourusername/Spec_HTML_Generator.git
cd Spec_HTML_Generator

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

## Development

### Building the Executable

```powershell
# Using build script
.\build.ps1

# Or manually
pyinstaller SpecHTMLGenerator.spec
```

### Creating the Installer

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Open `installer.iss` in Inno Setup Compiler
3. Build → Compile

### Releasing a New Version

```powershell
# Update version number
python update_version.py X.Y.Z

# Build and create installer
.\build.ps1
# Then compile installer.iss with Inno Setup

# Upload to server
python upload_release.py
```

See `Release_Process.md` for detailed instructions.

## Project Structure

```
Spec_HTML_Generator/
├── main.py                 # Main application
├── auto_update.py          # Auto-update system
├── icons/                  # Application icons
├── SpecHTMLGenerator.spec  # PyInstaller config
├── installer.iss           # Inno Setup script
├── build.ps1              # Build script (PowerShell)
├── build.bat              # Build script (Batch)
└── requirements.txt       # Python dependencies
```

## Requirements

- Python 3.9+
- PySide6 6.5+
- Windows 10/11 (for installer)

## License

Copyright (c) 2025 GraphicArt. All rights reserved.
