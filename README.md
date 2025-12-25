# MediaLibraryCleaner

A comprehensive media library management tool for identifying duplicates, low-resolution files, and incomplete series with automatic re-downloading via SABnzbd.

## Features

- 🔍 **Scanner**: Recursively scan TV and Movie directories with multithreaded processing
- 🧮 **Analyzer**: Detect duplicates, low-res files, incomplete series
- 📊 **Reporter**: Generate detailed reports with actionable insights
- 🗑️ **Cleaner**: Safe deletion with backup options
- 📥 **SABnzbd Integration**: Automatic re-downloading of removed content
- 🖥️ **Web UI**: Modern interface for managing your media library
- 🔧 **CLI**: Command-line interface for automation
- ⚙️ **Config-Driven**: All settings centralized in YAML configuration

## Architecture

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐
│ Scanner │───▶│ Analyzer │───▶│ Reporter │───▶│ Cleaner │───▶│ SABnzbd  │
└─────────┘    └──────────┘    └──────────┘    └─────────┘    └──────────┘
     │              │                │               │               │
     └──────────────┴────────────────┴───────────────┴───────────────┘
                                     │
                              ┌──────▼──────┐
                              │  SQLite DB  │
                              └─────────────┘
                                     ▲
                              ┌──────┴──────┐
                              │   Web UI    │
                              │   (Flask)   │
                              └─────────────┘
```

## Tech Stack

- **Backend**: Python 3.11+
- **Web Framework**: Flask + Flask-SocketIO (real-time updates)
- **Frontend**: HTML/CSS/JavaScript (Alpine.js for reactivity)
- **Database**: SQLite
- **CLI**: Click + Rich (beautiful terminal output)

## Quick Start

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your settings

# Scan your library (multithreaded)
python cli.py scan /path/to/movies --type movie

# Check status
python cli.py status

# Start web UI
python app.py

# Or use CLI for analysis
python cli.py analyze --duplicates --low-res
python cli.py clean --dry-run
```

## Configuration

All application settings are centralized in `config.yaml`:

```yaml
sabnzbd:
  api_key: "your-api-key"
  url: "http://localhost:8080"
  
quality:
  min_resolution: 1080
  preferred_codec: "h265"
  min_bitrate_1080p: 2000  # kbps
  allowed_extensions:
    - ".mkv"
    - ".mp4"
    - ".avi"
    - ".m4v"
    - ".VOB"
    - ".ts"
    - ".iso"
  
scanner:
  threads: 8  # Parallel worker threads for faster scanning
  batch_size: 5  # Database commit batch size
  ignore_patterns:
    - "*.nfo"
    - "*.srt"
    - "sample"
    
indexers:
  - name: "NZBGeek"
    api_key: "your-key"
    
paths:
  tv_shows: "/Volumes/Drobo/TV"
  movies: "/Volumes/Drobo/Movies"
  backup: "/Volumes/Drobo/.backup"
  database: "./data/medialibrary.db"
```

## CLI Commands

### Scan
Recursively scan directories for media files with multithreaded processing:

```bash
# Scan with default config (8 threads)
python cli.py scan /Volumes/Movies --type movie

# Override thread count
python cli.py scan /Volumes/Movies --type movie --threads 16

# Enable debug logging
python cli.py --debug scan /Volumes/Movies --type movie

# Monitor progress
tail -f scan_log.txt
```

### Status
View library statistics:

```bash
python cli.py status
```

### Analyze
Run quality and duplicate analysis:

```bash
python cli.py analyze --all
python cli.py analyze --duplicates
python cli.py analyze --low-res
python cli.py analyze --missing
```

## License

MIT
