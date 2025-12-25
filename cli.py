#!/usr/bin/env python3
"""CLI interface for MediaLibraryCleaner."""

import click
import logging
import sys
import os
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich.logging import RichHandler
from pathlib import Path

from src.config import config
from src.database import Database, MediaFile
from src.scanner import MediaScanner
from src.analyzer import MediaAnalyzer

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, show_time=True, show_path=False)]
)

@click.group()
@click.version_option(version='0.1.0')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(debug):
    """MediaLibraryCleaner - Manage your media library."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

@cli.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True))
@click.option('--type', 'media_type', type=click.Choice(['tv', 'movie', 'auto']), default='auto')
@click.option('--threads', default=None, type=int, help='Number of worker threads (default: from config)')
def scan(paths, media_type, threads):
    """Scan directories for media files."""
    if not paths:
        paths = [config.tv_path, config.movies_path]
        console.print(f"[yellow]No paths specified, using configured paths:[/yellow]")
        for p in paths:
            console.print(f"  • {p}")
    
    # Use config value if not specified
    if threads is None:
        threads = config.get('scanner.threads', 4)
    
    batch_size = config.get('scanner.batch_size', 5)
    
    db = Database(str(config.database_path))
    scanner = MediaScanner(config)
    
    for path_str in paths:
        path = Path(path_str)
        
        if media_type == 'auto':
            detected_type = 'tv' if 'tv' in path.name.lower() else 'movie'
        else:
            detected_type = media_type
        
        console.print(f"\n[cyan]Scanning {path} ({detected_type})...[/cyan]")
        console.print(f"[cyan]Using {threads} worker threads, batch size: {batch_size}[/cyan]")
        
        # Collect all file paths first
        file_paths = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if scanner._should_process_file(file):
                    file_paths.append(Path(root) / file)
        
        console.print(f"[yellow]Found {len(file_paths)} media files to process[/yellow]")
        
        # Process files with multithreading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import logging
        
        total_files = 0
        batch = []
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(scanner._extract_file_info, fp, detected_type): fp 
                for fp in file_paths
            }
            
            with db.get_session() as session:
                for future in track(as_completed(future_to_path), total=len(file_paths), description="Processing files..."):
                    try:
                        file_info = future.result()
                        batch.append(file_info)
                        
                        # Commit every batch_size files
                        if len(batch) >= batch_size:
                            for info in batch:
                                existing = session.query(MediaFile).filter_by(
                                    file_path=info['file_path']
                                ).first()
                                
                                if existing:
                                    for key, value in info.items():
                                        setattr(existing, key, value)
                                else:
                                    media_file = MediaFile(**info)
                                    session.add(media_file)
                                
                                total_files += 1
                            
                            session.commit()
                            logging.info(f"Committed {len(batch)} files to database (total: {total_files})")
                            batch = []
                    
                    except Exception as e:
                        file_path = future_to_path[future]
                        logging.error(f"Error processing {file_path}: {e}")
                
                # Commit remaining files
                if batch:
                    for info in batch:
                        existing = session.query(MediaFile).filter_by(
                            file_path=info['file_path']
                        ).first()
                        
                        if existing:
                            for key, value in info.items():
                                setattr(existing, key, value)
                        else:
                            media_file = MediaFile(**info)
                            session.add(media_file)
                        
                        total_files += 1
                    
                    session.commit()
                    logging.info(f"Committed final {len(batch)} files to database")
        
        console.print(f"\n[green]✓ Scanned {total_files} files[/green]")

@cli.command()
@click.option('--duplicates', is_flag=True, help='Check for duplicates')
@click.option('--low-res', is_flag=True, help='Check for low resolution files')
@click.option('--missing', is_flag=True, help='Check for missing episodes')
@click.option('--all', 'check_all', is_flag=True, help='Run all checks')
def analyze(duplicates, low_res, missing, check_all):
    """Analyze media library for issues."""
    db = Database(str(config.database_path))
    
    with db.get_session() as session:
        analyzer = MediaAnalyzer(config, session)
        
        console.print("[cyan]Running analysis...[/cyan]\n")
        
        if check_all:
            results = analyzer.analyze_all()
        else:
            results = {}
            if duplicates:
                results['duplicates'] = analyzer.find_duplicates()
            if low_res:
                results['low_resolution'] = analyzer.find_low_resolution()
            if missing:
                results['missing_episodes'] = analyzer.find_missing_episodes()
        
        _display_results(results)

def _display_results(results):
    """Display analysis results."""
    for issue_type, issues in results.items():
        if not issues:
            continue
        
        console.print(f"\n[yellow]━━━ {issue_type.upper().replace('_', ' ')} ━━━[/yellow]")
        
        if issue_type == 'missing_episodes':
            for item in issues:
                console.print(f"  • {item['series']} S{item['season']:02d}: Missing episodes {item['missing_episodes']}")
        else:
            table = Table()
            table.add_column("File")
            table.add_column("Issue")
            table.add_column("Severity")
            
            for issue in issues[:20]:
                table.add_row(
                    issue.media_file.file_name,
                    issue.description,
                    issue.severity
                )
            
            console.print(table)
            
            if len(issues) > 20:
                console.print(f"\n[dim]... and {len(issues) - 20} more[/dim]")

@cli.command()
def status():
    """Show library statistics."""
    db = Database(str(config.database_path))
    
    with db.get_session() as session:
        total_files = session.query(MediaFile).count()
        tv_files = session.query(MediaFile).filter_by(media_type='tv').count()
        movie_files = session.query(MediaFile).filter_by(media_type='movie').count()
        
        table = Table(title="Library Statistics")
        table.add_column("Category")
        table.add_column("Count", justify="right")
        
        table.add_row("Total Files", str(total_files))
        table.add_row("TV Shows", str(tv_files))
        table.add_row("Movies", str(movie_files))
        
        console.print(table)

@cli.command()
def ui():
    """Start web UI."""
    console.print("[cyan]Starting web UI...[/cyan]")
    console.print(f"[green]Open http://localhost:{config.get('ui.port', 5000)}[/green]")
    
    from src.web.app import app
    app.run(
        host=config.get('ui.host', '0.0.0.0'),
        port=config.get('ui.port', 5000),
        debug=config.get('ui.debug', False)
    )

if __name__ == '__main__':
    cli()
