"""API route definitions."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AdAccountSnapshot, DiagnosticResult
from app.services import SnapshotService, AIAnalyst, AnalyticsEngine
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class QuestionRequest(BaseModel):
    question: str
    date: Optional[str] = None


class QuestionResponse(BaseModel):
    answer: str
    context_used: dict
    model: Optional[str]


# Health Check
@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Question Answering
@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest, db: Session = Depends(get_db)):
    """Ask a question about ad account performance."""
    try:
        target_date = None
        if request.date:
            target_date = datetime.fromisoformat(request.date.replace('Z', '+00:00'))
            target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        analyst = AIAnalyst(db)
        result = analyst.answer_question(request.question, target_date)
        
        return QuestionResponse(
            answer=result['answer'],
            context_used=result.get('context_used', {}),
            model=result.get('model')
        )
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Daily Overview
@router.get("/overview")
async def get_overview(
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get or generate daily overview."""
    try:
        target_date = None
        if date:
            target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        analyst = AIAnalyst(db)
        overview = analyst.generate_daily_overview(target_date)
        
        return overview
    except Exception as e:
        logger.error(f"Error generating overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Snapshot Management
@router.post("/snapshot")
async def create_snapshot(
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Manually trigger a data snapshot."""
    try:
        target_date = None
        if date:
            target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        snapshot_service = SnapshotService(db)
        snapshot = snapshot_service.create_daily_snapshot(target_date)
        events_health = snapshot_service.create_events_manager_snapshot(target_date)
        
        # Compute diagnostics
        analytics = AnalyticsEngine(db)
        diagnostics = analytics.compute_all_diagnostics(snapshot)
        for diag in diagnostics:
            db.add(diag)
        db.commit()
        
        return {
            "snapshot_id": snapshot.id,
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "events_health_id": events_health.id if events_health else None,
            "diagnostics_count": len(diagnostics)
        }
    except Exception as e:
        logger.error(f"Error creating snapshot: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots")
async def list_snapshots(
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """List historical snapshots."""
    snapshots = db.query(AdAccountSnapshot).order_by(
        AdAccountSnapshot.snapshot_date.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": s.id,
            "date": s.snapshot_date.isoformat(),
            "spend": s.spend,
            "impressions": s.impressions,
            "clicks": s.clicks,
            "reach": s.reach,
            "frequency": s.frequency,
            "cpm": s.cpm,
            "cpc": s.cpc,
            "ctr": s.ctr,
        }
        for s in snapshots
    ]


# Diagnostics
@router.get("/diagnostics")
async def get_diagnostics(
    date: Optional[str] = None,
    diagnostic_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get diagnostic results."""
    query = db.query(DiagnosticResult)
    
    if date:
        target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(DiagnosticResult.snapshot_date == target_date)
    
    if diagnostic_type:
        query = query.filter(DiagnosticResult.diagnostic_type == diagnostic_type)
    
    diagnostics = query.order_by(DiagnosticResult.snapshot_date.desc()).limit(50).all()
    
    return [
        {
            "id": d.id,
            "date": d.snapshot_date.isoformat(),
            "type": d.diagnostic_type,
            "metric": d.metric_name,
            "current_value": d.current_value,
            "previous_value": d.previous_value,
            "change_percentage": d.change_percentage,
            "severity": d.severity,
            "confidence": d.confidence,
            "explanation": d.explanation,
            "recommendation": d.recommendation,
        }
        for d in diagnostics
    ]
