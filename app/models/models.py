from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, Index
from sqlalchemy.sql import func
from app.database import Base


class AdAccountSnapshot(Base):
    """Daily snapshot of ad account performance metrics."""
    __tablename__ = "ad_account_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    ad_account_id = Column(String, nullable=False, index=True)
    
    # Core metrics
    spend = Column(Float)
    impressions = Column(Integer)
    clicks = Column(Integer)
    reach = Column(Integer)
    frequency = Column(Float)
    cpm = Column(Float)
    cpc = Column(Float)
    ctr = Column(Float)
    
    # Attribution data
    standard_attribution_data = Column(JSON)
    incremental_attribution_data = Column(JSON, nullable=True)
    
    # Raw API response
    raw_data = Column(JSON)
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_account_date', 'ad_account_id', 'snapshot_date'),
    )


class EventsManagerHealth(Base):
    """Tracking pixel and events manager health data."""
    __tablename__ = "events_manager_health"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    pixel_id = Column(String, nullable=True)
    
    # Event metrics
    events_received = Column(Integer)
    events_dropped = Column(Integer)
    events_duplicate = Column(Integer)
    events_matched = Column(Integer)
    
    # Quality score
    tracking_quality_score = Column(Float, nullable=True)
    diagnostics_data = Column(JSON)
    
    # Raw API response
    raw_data = Column(JSON)
    
    created_at = Column(DateTime, server_default=func.now())


class DiagnosticResult(Base):
    """Computed diagnostic results (fatigue, saturation, etc.)."""
    __tablename__ = "diagnostic_results"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    diagnostic_type = Column(String, nullable=False, index=True)
    
    # Metric details
    metric_name = Column(String, nullable=False)
    current_value = Column(Float)
    previous_value = Column(Float, nullable=True)
    change_percentage = Column(Float, nullable=True)
    
    # Assessment
    severity = Column(String)  # low, medium, high
    confidence = Column(Float)  # 0.0 - 1.0
    explanation = Column(Text)
    recommendation = Column(Text)
    
    # Additional metadata
    diagnostic_metadata = Column(JSON)
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_date_type', 'snapshot_date', 'diagnostic_type'),
    )


class DailyOverview(Base):
    """AI-generated daily overview and recommendations."""
    __tablename__ = "daily_overviews"
    
    id = Column(Integer, primary_key=True, index=True)
    overview_date = Column(DateTime, nullable=False, unique=True, index=True)
    
    # AI-generated content
    summary = Column(Text)
    key_changes = Column(JSON)
    insights = Column(JSON)
    recommendations = Column(JSON)
    
    generated_at = Column(DateTime, server_default=func.now())
