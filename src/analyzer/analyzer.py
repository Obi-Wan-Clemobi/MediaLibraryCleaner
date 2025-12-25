"""Media analyzer implementation."""

from typing import List, Dict, Tuple
from collections import defaultdict
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from ..database import MediaFile, MediaIssue

class MediaAnalyzer:
    def __init__(self, config, db_session: Session):
        self.config = config
        self.session = db_session
        self.min_resolution = config.get('quality.min_resolution', 1080)
        self.similarity_threshold = config.get('analyzer.duplicate_detection.similarity_threshold', 0.85)
    
    def analyze_all(self) -> Dict[str, List[MediaIssue]]:
        """Run all analysis checks."""
        results = {
            'duplicates': [],
            'low_resolution': [],
            'missing_episodes': [],
            'quality_issues': []
        }
        
        results['duplicates'] = self.find_duplicates()
        results['low_resolution'] = self.find_low_resolution()
        results['quality_issues'] = self.find_quality_issues()
        
        if self.config.get('analyzer.series_detection.check_missing_episodes'):
            results['missing_episodes'] = self.find_missing_episodes()
        
        return results
    
    def find_duplicates(self) -> List[MediaIssue]:
        """Find duplicate files."""
        issues = []
        
        files = self.session.query(MediaFile).all()
        hash_groups = defaultdict(list)
        
        for file in files:
            if file.file_hash:
                hash_groups[file.file_hash].append(file)
        
        for file_hash, duplicates in hash_groups.items():
            if len(duplicates) > 1:
                duplicates.sort(key=lambda f: (
                    -(f.resolution_height or 0),
                    -(f.bitrate or 0),
                    f.file_size
                ), reverse=True)
                
                best_file = duplicates[0]
                
                for dup in duplicates[1:]:
                    issue = MediaIssue(
                        media_file_id=dup.id,
                        issue_type='duplicate',
                        severity='high',
                        description=f'Duplicate of {best_file.file_name}',
                        duplicate_of_id=best_file.id
                    )
                    self.session.add(issue)
                    issues.append(issue)
        
        if self.config.get('analyzer.duplicate_detection.use_filename_similarity'):
            issues.extend(self._find_similar_filenames())
        
        self.session.commit()
        return issues
    
    def _find_similar_filenames(self) -> List[MediaIssue]:
        """Find files with similar names (potential duplicates)."""
        issues = []
        files = self.session.query(MediaFile).all()
        
        checked_pairs = set()
        
        for i, file1 in enumerate(files):
            for file2 in files[i+1:]:
                pair = tuple(sorted([file1.id, file2.id]))
                if pair in checked_pairs:
                    continue
                
                checked_pairs.add(pair)
                
                similarity = SequenceMatcher(None, file1.file_name, file2.file_name).ratio()
                
                if similarity >= self.similarity_threshold:
                    better_file = file1 if (file1.resolution_height or 0) >= (file2.resolution_height or 0) else file2
                    worse_file = file2 if better_file == file1 else file1
                    
                    issue = MediaIssue(
                        media_file_id=worse_file.id,
                        issue_type='duplicate',
                        severity='medium',
                        description=f'Similar to {better_file.file_name} ({similarity:.0%} match)',
                        duplicate_of_id=better_file.id
                    )
                    self.session.add(issue)
                    issues.append(issue)
        
        self.session.commit()
        return issues
    
    def find_low_resolution(self) -> List[MediaIssue]:
        """Find files below minimum resolution."""
        issues = []
        
        files = self.session.query(MediaFile).filter(
            MediaFile.resolution_height < self.min_resolution
        ).all()
        
        for file in files:
            issue = MediaIssue(
                media_file_id=file.id,
                issue_type='low_res',
                severity='high',
                description=f'Resolution {file.resolution_height}p is below minimum {self.min_resolution}p'
            )
            self.session.add(issue)
            issues.append(issue)
        
        self.session.commit()
        return issues
    
    def find_quality_issues(self) -> List[MediaIssue]:
        """Find files with quality issues (old codecs, low bitrate)."""
        issues = []
        
        old_codecs = ['xvid', 'divx', 'mpeg2']
        files = self.session.query(MediaFile).all()
        
        for file in files:
            if file.codec and any(old in file.codec.lower() for old in old_codecs):
                issue = MediaIssue(
                    media_file_id=file.id,
                    issue_type='quality',
                    severity='medium',
                    description=f'Old codec: {file.codec}'
                )
                self.session.add(issue)
                issues.append(issue)
            
            if file.resolution_height == 1080 and file.bitrate:
                min_bitrate = self.config.get('quality.min_bitrate_1080p', 2000) * 1000
                if file.bitrate < min_bitrate:
                    issue = MediaIssue(
                        media_file_id=file.id,
                        issue_type='quality',
                        severity='medium',
                        description=f'Low bitrate: {file.bitrate//1000} kbps'
                    )
                    self.session.add(issue)
                    issues.append(issue)
        
        self.session.commit()
        return issues
    
    def find_missing_episodes(self) -> List[Dict]:
        """Find missing episodes in TV series."""
        missing = []
        
        tv_files = self.session.query(MediaFile).filter(
            MediaFile.media_type == 'tv',
            MediaFile.season.isnot(None),
            MediaFile.episode.isnot(None)
        ).all()
        
        series_episodes = defaultdict(lambda: defaultdict(set))
        for file in tv_files:
            series_episodes[file.title][file.season].add(file.episode)
        
        for series, seasons in series_episodes.items():
            for season, episodes in seasons.items():
                if not episodes:
                    continue
                
                min_ep, max_ep = min(episodes), max(episodes)
                expected = set(range(min_ep, max_ep + 1))
                missing_eps = expected - episodes
                
                if missing_eps:
                    missing.append({
                        'series': series,
                        'season': season,
                        'missing_episodes': sorted(missing_eps)
                    })
        
        return missing
