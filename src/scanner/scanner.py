"""Media file scanner implementation."""

import os
import hashlib
import logging
from pathlib import Path
from typing import List, Generator, Optional
from pymediainfo import MediaInfo
import xxhash

logger = logging.getLogger(__name__)

class MediaScanner:
    def __init__(self, config):
        self.config = config
        self.allowed_extensions = config.get('quality.allowed_extensions', ['.mkv', '.mp4', '.avi', '.m4v'])
        self.ignore_patterns = config.get('scanner.ignore_patterns', [])
    
    def scan_directory(self, path: Path, media_type: str = 'unknown') -> Generator[dict, None, None]:
        """Scan directory for media files."""
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        logger.info(f"Starting scan of {path}")
        for root, dirs, files in os.walk(path):
            for file in files:
                if self._should_process_file(file):
                    file_path = Path(root) / file
                    logger.info(f"Found media file: {file_path.name}")
                    yield self._extract_file_info(file_path, media_type)
    
    def _should_process_file(self, filename: str) -> bool:
        """Check if file should be processed."""
        ext = Path(filename).suffix.lower()
        if ext not in self.allowed_extensions:
            return False
        
        for pattern in self.ignore_patterns:
            if pattern.lower() in filename.lower():
                return False
        
        return True
    
    def _extract_file_info(self, file_path: Path, media_type: str) -> dict:
        """Extract metadata from media file."""
        logger.debug(f"[{file_path.name}] Getting file stats")
        stat = file_path.stat()
        
        info = {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'file_size': stat.st_size,
            'file_hash': self._calculate_hash(file_path),
            'media_type': media_type,
            'title': self._extract_title(file_path),
            'year': self._extract_year(file_path),
            'season': self._extract_season(file_path),
            'episode': self._extract_episode(file_path),
        }
        
        logger.debug(f"[{file_path.name}] Extracting media info with pymediainfo")
        media_info = self._get_media_info(file_path)
        if media_info:
            info.update(media_info)
        
        logger.info(f"[{file_path.name}] Completed extraction - {info.get('resolution_width')}x{info.get('resolution_height')} {info.get('codec')}")
        return info
    
    def _calculate_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """Calculate fast hash of file (first/last chunks + size)."""
        logger.debug(f"[{file_path.name}] Calculating hash")
        hasher = xxhash.xxh64()
        file_size = file_path.stat().st_size
        
        hasher.update(str(file_size).encode())
        
        with open(file_path, 'rb') as f:
            hasher.update(f.read(chunk_size))
            
            if file_size > chunk_size * 2:
                f.seek(-chunk_size, 2)
                hasher.update(f.read(chunk_size))
        
        logger.debug(f"[{file_path.name}] Hash calculated: {hasher.hexdigest()}")
        return hasher.hexdigest()
    
    def _get_media_info(self, file_path: Path) -> Optional[dict]:
        """Extract media information using pymediainfo."""
        try:
            logger.debug(f"[{file_path.name}] Parsing with pymediainfo")
            media_info = MediaInfo.parse(file_path)
            
            video_track = None
            audio_track = None
            
            for track in media_info.tracks:
                if track.track_type == 'Video' and not video_track:
                    video_track = track
                elif track.track_type == 'Audio' and not audio_track:
                    audio_track = track
            
            if not video_track:
                logger.warning(f"[{file_path.name}] No video track found")
                return None
            
            duration = None
            if video_track.duration:
                try:
                    duration = float(video_track.duration) / 1000
                except (ValueError, TypeError):
                    duration = None
            
            result = {
                'resolution_width': video_track.width,
                'resolution_height': video_track.height,
                'codec': video_track.codec_id or video_track.format,
                'bitrate': video_track.bit_rate,
                'duration': duration,
            }
            
            # Extract audio information
            if audio_track:
                result['audio_codec'] = audio_track.format or audio_track.codec_id
                result['audio_channels'] = audio_track.channel_s
                result['audio_language'] = audio_track.language
            
            return result
        except Exception as e:
            logger.error(f"[{file_path.name}] Error extracting media info: {e}")
            print(f"Error extracting media info from {file_path}: {e}")
            return None
    
    def _extract_title(self, file_path: Path) -> str:
        """Extract title from filename."""
        name = file_path.stem
        
        for pattern in [r'\d{4}', r'[Ss]\d{2}[Ee]\d{2}', r'\[.*?\]', r'\(.*?\)']:
            import re
            name = re.split(pattern, name)[0]
        
        return name.replace('.', ' ').replace('_', ' ').strip()
    
    def _extract_year(self, file_path: Path) -> Optional[int]:
        """Extract year from filename."""
        import re
        match = re.search(r'(19|20)\d{2}', file_path.stem)
        return int(match.group()) if match else None
    
    def _extract_season(self, file_path: Path) -> Optional[int]:
        """Extract season number from filename."""
        import re
        match = re.search(r'[Ss](\d{1,2})', file_path.stem)
        return int(match.group(1)) if match else None
    
    def _extract_episode(self, file_path: Path) -> Optional[int]:
        """Extract episode number from filename."""
        import re
        match = re.search(r'[Ee](\d{1,3})', file_path.stem)
        return int(match.group(1)) if match else None
