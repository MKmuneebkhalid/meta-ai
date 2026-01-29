"""Service for creating and managing daily data snapshots."""

from sqlalchemy.orm import Session
from app.models import AdAccountSnapshot, EventsManagerHealth
from app.services.meta_client import MetaAPIClient
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SnapshotService:
    """Service for creating daily snapshots of ad account data."""
    
    def __init__(self, db: Session):
        self.db = db
        self.meta_client = MetaAPIClient()
    
    def create_daily_snapshot(
        self, 
        snapshot_date: Optional[datetime] = None
    ) -> AdAccountSnapshot:
        """
        Create a daily snapshot of ad account performance.
        
        Args:
            snapshot_date: Date for the snapshot (defaults to today)
        
        Returns:
            Created AdAccountSnapshot object
        """
        if snapshot_date is None:
            snapshot_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        date_start = snapshot_date - timedelta(days=1)
        date_end = snapshot_date
        
        # Check if snapshot already exists
        existing = self.db.query(AdAccountSnapshot).filter(
            AdAccountSnapshot.snapshot_date == snapshot_date,
            AdAccountSnapshot.ad_account_id == self.meta_client.ad_account_id
        ).first()
        
        if existing:
            logger.info(f"Snapshot for {snapshot_date.date()} already exists")
            return existing
        
        try:
            # Fetch data from Meta API
            insights = self.meta_client.get_account_insights(date_start, date_end)
            incremental = self.meta_client.get_incremental_attribution(date_start, date_end)
            
            # Create snapshot record
            snapshot = AdAccountSnapshot(
                snapshot_date=snapshot_date,
                ad_account_id=self.meta_client.ad_account_id,
                spend=insights.get('spend', 0),
                impressions=insights.get('impressions', 0),
                clicks=insights.get('clicks', 0),
                reach=insights.get('reach', 0),
                frequency=insights.get('frequency', 0),
                cpm=insights.get('cpm'),
                cpc=insights.get('cpc'),
                ctr=insights.get('ctr'),
                standard_attribution_data=insights,
                incremental_attribution_data=incremental,
                raw_data=insights
            )
            
            self.db.add(snapshot)
            self.db.commit()
            self.db.refresh(snapshot)
            
            logger.info(f"Created snapshot for {snapshot_date.date()}")
            return snapshot
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating snapshot: {e}")
            raise
    
    def create_events_manager_snapshot(
        self, 
        snapshot_date: Optional[datetime] = None
    ) -> Optional[EventsManagerHealth]:
        """
        Create a snapshot of Events Manager / Pixel health.
        
        Args:
            snapshot_date: Date for the snapshot (defaults to today)
        
        Returns:
            Created EventsManagerHealth object or None
        """
        if snapshot_date is None:
            snapshot_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if snapshot already exists
        existing = self.db.query(EventsManagerHealth).filter(
            EventsManagerHealth.snapshot_date == snapshot_date
        ).first()
        
        if existing:
            logger.info(f"Events Manager snapshot for {snapshot_date.date()} already exists")
            return existing
        
        try:
            # Fetch Events Manager data
            events_data = self.meta_client.get_events_manager_data()
            
            if not events_data or events_data.get('total_pixels', 0) == 0:
                logger.warning("No Events Manager data available")
                return None
            
            # Aggregate pixel stats
            total_received = 0
            total_dropped = 0
            total_duplicate = 0
            total_matched = 0
            
            for pixel in events_data.get('pixels', []):
                stats = pixel.get('stats')
                if stats:
                    for stat in stats:
                        total_received += int(stat.get('events_received', 0))
                        total_dropped += int(stat.get('events_dropped', 0))
                        total_duplicate += int(stat.get('events_duplicate', 0))
                        total_matched += int(stat.get('events_matched', 0))
            
            # Calculate quality score
            total_events = total_received
            quality_score = (total_matched / total_events) if total_events > 0 else 0.0
            
            # Create health record
            health = EventsManagerHealth(
                snapshot_date=snapshot_date,
                pixel_id=events_data.get('pixels', [{}])[0].get('pixel_id') if events_data.get('pixels') else None,
                events_received=total_received,
                events_dropped=total_dropped,
                events_duplicate=total_duplicate,
                events_matched=total_matched,
                tracking_quality_score=quality_score,
                diagnostics_data={
                    'match_rate': (total_matched / total_events) if total_events > 0 else 0,
                    'drop_rate': (total_dropped / total_events) if total_events > 0 else 0,
                    'duplicate_rate': (total_duplicate / total_events) if total_events > 0 else 0,
                },
                raw_data=events_data
            )
            
            self.db.add(health)
            self.db.commit()
            self.db.refresh(health)
            
            logger.info(f"Created Events Manager snapshot for {snapshot_date.date()}")
            return health
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating Events Manager snapshot: {e}")
            return None
