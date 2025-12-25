"""Flask web application."""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import config
from src.database import Database, MediaFile, MediaIssue
from src.scanner import MediaScanner
from src.analyzer import MediaAnalyzer

app = Flask(__name__, 
            template_folder='../../templates',
            static_folder='../../static')
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

db = Database(str(config.database_path))

@app.route('/')
def index():
    """Main dashboard."""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """Get library statistics."""
    with db.get_session() as session:
        stats = {
            'total_files': session.query(MediaFile).count(),
            'tv_files': session.query(MediaFile).filter_by(media_type='tv').count(),
            'movie_files': session.query(MediaFile).filter_by(media_type='movie').count(),
            'total_issues': session.query(MediaIssue).filter_by(resolved=False).count(),
            'duplicates': session.query(MediaIssue).filter_by(issue_type='duplicate', resolved=False).count(),
            'low_res': session.query(MediaIssue).filter_by(issue_type='low_res', resolved=False).count(),
        }
        return jsonify(stats)

@app.route('/api/files')
def get_files():
    """Get all media files."""
    with db.get_session() as session:
        files = session.query(MediaFile).limit(100).all()
        
        return jsonify([{
            'id': f.id,
            'file_name': f.file_name,
            'file_path': f.file_path,
            'media_type': f.media_type,
            'resolution': f.resolution,
            'file_size': f.file_size,
            'codec': f.codec,
            'issues': len([i for i in f.issues if not i.resolved])
        } for f in files])

@app.route('/api/issues')
def get_issues():
    """Get all unresolved issues."""
    issue_type = request.args.get('type')
    
    with db.get_session() as session:
        query = session.query(MediaIssue).filter_by(resolved=False)
        
        if issue_type:
            query = query.filter_by(issue_type=issue_type)
        
        issues = query.all()
        
        return jsonify([{
            'id': i.id,
            'file_name': i.media_file.file_name,
            'file_path': i.media_file.file_path,
            'issue_type': i.issue_type,
            'severity': i.severity,
            'description': i.description,
            'resolution': i.media_file.resolution if i.media_file else None,
        } for i in issues])

@app.route('/api/scan', methods=['POST'])
def trigger_scan():
    """Trigger a scan operation."""
    data = request.json
    paths = data.get('paths', [config.tv_path, config.movies_path])
    
    socketio.start_background_task(background_scan, paths)
    
    return jsonify({'status': 'started'})

@app.route('/api/analyze', methods=['POST'])
def trigger_analyze():
    """Trigger analysis."""
    socketio.start_background_task(background_analyze)
    return jsonify({'status': 'started'})

def background_scan(paths):
    """Background task for scanning."""
    scanner = MediaScanner(config)
    
    with db.get_session() as session:
        total = 0
        for path in paths:
            socketio.emit('scan_progress', {'status': f'Scanning {path}', 'progress': 0})
            
            for file_info in scanner.scan_directory(Path(path), 'auto'):
                existing = session.query(MediaFile).filter_by(
                    file_path=file_info['file_path']
                ).first()
                
                if existing:
                    for key, value in file_info.items():
                        setattr(existing, key, value)
                else:
                    media_file = MediaFile(**file_info)
                    session.add(media_file)
                
                total += 1
                if total % 10 == 0:
                    socketio.emit('scan_progress', {'status': f'Processed {total} files', 'progress': total})
            
            session.commit()
        
        socketio.emit('scan_complete', {'total': total})

def background_analyze():
    """Background task for analysis."""
    with db.get_session() as session:
        analyzer = MediaAnalyzer(config, session)
        
        socketio.emit('analyze_progress', {'status': 'Finding duplicates...', 'progress': 0})
        results = analyzer.analyze_all()
        
        total_issues = sum(len(issues) for issues in results.values() if isinstance(issues, list))
        
        socketio.emit('analyze_complete', {'total_issues': total_issues, 'results': {
            k: len(v) if isinstance(v, list) else 0 for k, v in results.items()
        }})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
