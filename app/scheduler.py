"""Background job scheduler for daily data collection."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import SessionLocal
from app.services import SnapshotService, AIAnalyst, AnalyticsEngine
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DailyJobScheduler:
    """Scheduler for daily data collection and analysis jobs."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self.run_daily_job,
            trigger=CronTrigger(hour=1, minute=0),  # Run at 1:00 AM
            id='daily_snapshot_job',
            name='Daily snapshot and overview generation',
            replace_existing=True
        )
    
    def run_daily_job(self):
        """Execute daily data collection and analysis."""
        logger.info("Starting daily snapshot job")
        db = SessionLocal()
        
        try:
            snapshot_service = SnapshotService(db)
            analyst = AIAnalyst(db)
            
            # Get yesterday's date
            yesterday = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=1)
            
            # Create snapshots
            logger.info(f"Creating snapshot for {yesterday.date()}")
            snapshot = snapshot_service.create_daily_snapshot(yesterday)
            
            logger.info("Creating Events Manager snapshot")
            snapshot_service.create_events_manager_snapshot(yesterday)
            
            # Compute diagnostics
            logger.info("Computing diagnostics")
            analytics = AnalyticsEngine(db)
            diagnostics = analytics.compute_all_diagnostics(snapshot)
            for diag in diagnostics:
                db.add(diag)
            db.commit()
            
            # Generate daily overview
            logger.info("Generating daily overview")
            analyst.generate_daily_overview(yesterday)
            
            logger.info("Daily job completed successfully")
            
        except Exception as e:
            logger.error(f"Error in daily job: {e}")
            db.rollback()
        finally:
            db.close()
    
    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def shutdown(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
