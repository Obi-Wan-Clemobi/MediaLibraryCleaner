# GitHub Copilot Instructions for MediaLibraryCleaner

## Project Overview
MediaLibraryCleaner is a Python-based tool for managing media libraries - scanning, analyzing, and cleaning movie/TV collections with SABnzbd integration.

## Development Best Practices

### 1. Configuration-Driven Development
**ALWAYS follow a config-driven approach:**

- **All configurable values MUST be in `config.yaml`**
  - Thread counts, batch sizes, timeouts
  - File extensions, quality thresholds
  - Paths, URLs, API keys
  - Feature flags and toggles

- **Never hardcode values that might change**
  - Use `config.get('path.to.setting', default_value)`
  - Document all config options in `config.example.yaml`
  - Update README.md when adding new config options

- **CLI arguments should override config values**
  ```python
  threads = threads or config.get('scanner.threads', 4)
  ```

### 2. Code Organization
- Keep business logic in `src/` modules
- CLI commands in `cli.py` should be thin wrappers
- Database models in `src/database.py`
- All scanning logic in `src/scanner/`

### 3. Performance
- Use multithreading for I/O-bound operations (file scanning)
- Batch database commits (configurable batch size)
- Log performance metrics for optimization

### 4. Logging
- Use structured logging with `logging` module
- Include file names in log context: `[filename] message`
- Support debug mode via `--debug` flag
- Use Rich for beautiful console output

### 5. Error Handling
- Catch and log exceptions during file processing
- Continue processing other files on individual failures
- Provide clear error messages to users

### 6. Testing
- Test with small file sets before full scans
- Support test directories with symlinks
- Provide progress indicators for long operations

## Configuration Example

When adding new features, follow this pattern:

```python
# 1. Add to config.yaml
new_feature:
  enabled: true
  parameter: 42

# 2. Access in code
if config.get('new_feature.enabled', False):
    param = config.get('new_feature.parameter', 10)
    
# 3. Allow CLI override
@click.option('--parameter', default=None)
def command(parameter):
    param = parameter or config.get('new_feature.parameter', 10)

# 4. Update README.md with new config option
```

## Database Schema Changes
- Use SQLAlchemy ORM
- Specify `foreign_keys` and `overlaps` for complex relationships
- Test schema changes by deleting `data/medialibrary.db` and rescanning

## Key Technologies
- Python 3.13+
- SQLAlchemy (ORM)
- Click (CLI framework)
- Rich (terminal UI)
- Flask + SocketIO (web UI)
- pymediainfo (video metadata)
- xxhash (fast hashing)

## Common Patterns

### Multithreaded File Processing
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

threads = config.get('scanner.threads', 4)
with ThreadPoolExecutor(max_workers=threads) as executor:
    futures = {executor.submit(process, f): f for f in files}
    for future in as_completed(futures):
        result = future.result()
```

### Batch Database Commits
```python
batch_size = config.get('scanner.batch_size', 5)
batch = []
for item in items:
    batch.append(item)
    if len(batch) >= batch_size:
        session.add_all(batch)
        session.commit()
        batch = []
```

## Remember
- Configuration > Hardcoded values
- Documentation is part of the feature
- Test with real network shares (AFP/SMB)
- Performance matters for large libraries (1000+ files)

## Git Workflow
- Always initialize git repository for version control
- Commit changes regularly with descriptive messages
- Database files (*.db, data/) are already in .gitignore
- Config files (config.yaml) are ignored - use config.example.yaml for templates
- Before pushing to GitHub:
  ```bash
  git init
  git add -A
  git commit -m "Descriptive message"
  git remote add origin <repo-url>
  git push -u origin main
  ```
