"""Database models and management."""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from pathlib import Path

Base = declarative_base()

class MediaFile(Base):
    __tablename__ = 'media_files'
    
    id = Column(Integer, primary_key=True)
    file_path = Column(String, unique=True, nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer)
    file_hash = Column(String, index=True)
    
    media_type = Column(String)
    title = Column(String)
    year = Column(Integer)
    season = Column(Integer)
    episode = Column(Integer)
    
    resolution_width = Column(Integer)
    resolution_height = Column(Integer)
    codec = Column(String)
    bitrate = Column(Integer)
    duration = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    scanned_at = Column(DateTime, default=datetime.utcnow)
    
    issues = relationship("MediaIssue", back_populates="media_file", cascade="all, delete-orphan", foreign_keys="MediaIssue.media_file_id")
    
    @property
    def resolution(self) -> str:
        if self.resolution_height >= 2160:
            return "4K"
        elif self.resolution_height >= 1080:
            return "1080p"
        elif self.resolution_height >= 720:
            return "720p"
        elif self.resolution_height >= 480:
            return "480p"
        return "SD"

class MediaIssue(Base):
    __tablename__ = 'media_issues'
    
    id = Column(Integer, primary_key=True)
    media_file_id = Column(Integer, ForeignKey('media_files.id'), nullable=False)
    
    issue_type = Column(String, nullable=False)
    severity = Column(String)
    description = Column(Text)
    
    duplicate_of_id = Column(Integer, ForeignKey('media_files.id'))
    
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolution_action = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    media_file = relationship("MediaFile", back_populates="issues", foreign_keys=[media_file_id], overlaps="duplicate_of")
    duplicate_of = relationship("MediaFile", foreign_keys=[duplicate_of_id], overlaps="media_file")

class DownloadJob(Base):
    __tablename__ = 'download_jobs'
    
    id = Column(Integer, primary_key=True)
    media_file_id = Column(Integer, ForeignKey('media_files.id'))
    
    title = Column(String, nullable=False)
    search_term = Column(String)
    nzb_id = Column(String)
    sabnzbd_id = Column(String)
    
    status = Column(String, default='pending')
    progress = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    media_file = relationship("MediaFile")

class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.Session()
