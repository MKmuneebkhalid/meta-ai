"""AI-powered analyst for answering questions and generating insights."""

from sqlalchemy.orm import Session
from app.models import AdAccountSnapshot, DiagnosticResult, DailyOverview, EventsManagerHealth
from app.services.analytics import AnalyticsEngine
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from openai import OpenAI
from app.config import settings
import json
import logging

logger = logging.getLogger(__name__)

openai_client = OpenAI(api_key=settings.openai_api_key)


class AIAnalyst:
    """AI-powered analyst for conversational Q&A about ad performance."""
    
    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsEngine(db)
    
    def get_context_for_date(self, target_date: datetime) -> Dict:
        """
        Build context data for AI analysis.
        
        Args:
            target_date: Date to analyze
        
        Returns:
            Dictionary of context data including historical snapshots
        """
        snapshot = self.db.query(AdAccountSnapshot).filter(
            AdAccountSnapshot.snapshot_date == target_date
        ).first()
        
        if not snapshot:
            snapshot = self.db.query(AdAccountSnapshot).filter(
                AdAccountSnapshot.snapshot_date <= target_date
            ).order_by(AdAccountSnapshot.snapshot_date.desc()).first()
        
        if not snapshot:
            return {}
        
        # Get all available snapshots for historical context
        historical_snapshots = self.db.query(AdAccountSnapshot).filter(
            AdAccountSnapshot.ad_account_id == snapshot.ad_account_id,
            AdAccountSnapshot.snapshot_date <= target_date
        ).order_by(AdAccountSnapshot.snapshot_date.desc()).all()
        
        previous_snapshot = self.db.query(AdAccountSnapshot).filter(
            AdAccountSnapshot.ad_account_id == snapshot.ad_account_id,
            AdAccountSnapshot.snapshot_date < snapshot.snapshot_date
        ).order_by(AdAccountSnapshot.snapshot_date.desc()).first()
        
        diagnostics = self.db.query(DiagnosticResult).filter(
            DiagnosticResult.snapshot_date == snapshot.snapshot_date
        ).all()
        
        events_health = self.db.query(EventsManagerHealth).filter(
            EventsManagerHealth.snapshot_date == snapshot.snapshot_date
        ).first()
        
        context = {
            'current_snapshot': {
                'date': snapshot.snapshot_date.isoformat(),
                'spend': snapshot.spend,
                'impressions': snapshot.impressions,
                'clicks': snapshot.clicks,
                'reach': snapshot.reach,
                'frequency': snapshot.frequency,
                'cpm': snapshot.cpm,
                'cpc': snapshot.cpc,
                'ctr': snapshot.ctr,
            },
            'previous_snapshot': None,
            'changes': {},
            'historical_data': [],
            'diagnostics': [],
            'events_health': None,
        }
        
        # Add historical data for all available days
        for hist in historical_snapshots:
            context['historical_data'].append({
                'date': hist.snapshot_date.isoformat(),
                'spend': hist.spend,
                'impressions': hist.impressions,
                'clicks': hist.clicks,
                'reach': hist.reach,
                'frequency': hist.frequency,
                'cpm': hist.cpm,
                'cpc': hist.cpc,
                'ctr': hist.ctr,
            })
        
        if previous_snapshot:
            context['previous_snapshot'] = {
                'date': previous_snapshot.snapshot_date.isoformat(),
                'spend': previous_snapshot.spend,
                'impressions': previous_snapshot.impressions,
                'clicks': previous_snapshot.clicks,
                'reach': previous_snapshot.reach,
                'frequency': previous_snapshot.frequency,
                'cpm': previous_snapshot.cpm,
                'cpc': previous_snapshot.cpc,
                'ctr': previous_snapshot.ctr,
            }
            
            if previous_snapshot.spend > 0:
                context['changes'] = {
                    'spend_change': ((snapshot.spend - previous_snapshot.spend) / previous_snapshot.spend) * 100,
                    'impressions_change': ((snapshot.impressions - previous_snapshot.impressions) / previous_snapshot.impressions) * 100 if previous_snapshot.impressions > 0 else 0,
                    'clicks_change': ((snapshot.clicks - previous_snapshot.clicks) / previous_snapshot.clicks) * 100 if previous_snapshot.clicks > 0 else 0,
                    'cpm_change': ((snapshot.cpm - previous_snapshot.cpm) / previous_snapshot.cpm) * 100 if previous_snapshot.cpm and previous_snapshot.cpm > 0 else None,
                }
        
        for diag in diagnostics:
            context['diagnostics'].append({
                'type': diag.diagnostic_type,
                'metric': diag.metric_name,
                'severity': diag.severity,
                'confidence': diag.confidence,
                'explanation': diag.explanation,
                'recommendation': diag.recommendation,
                'change_percentage': diag.change_percentage,
            })
        
        if events_health:
            context['events_health'] = {
                'tracking_quality_score': events_health.tracking_quality_score,
                'events_received': events_health.events_received,
                'events_dropped': events_health.events_dropped,
                'events_matched': events_health.events_matched,
            }
        
        return context
    
    def answer_question(
        self, 
        question: str, 
        target_date: Optional[datetime] = None
    ) -> Dict:
        """
        Answer a question about ad account performance.
        
        Args:
            question: User's question
            target_date: Date context (defaults to today)
        
        Returns:
            Dictionary with answer and context used
        """
        if target_date is None:
            target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        context = self.get_context_for_date(target_date)
        
        system_prompt = """You are a read-only AI analyst for Meta ad accounts. Your role is to:
1. Analyze ad account performance data and provide evidence-based insights
2. Explain what changed and why based on available metrics
3. Provide recommendations with confidence levels
4. NEVER suggest creating, editing, pausing ads, or changing budgets
5. Only use data that is actually available - never guess or make assumptions
6. Be conversational and clear in your explanations

You have access to:
- Daily ad account snapshots (spend, impressions, clicks, reach, frequency, CPM, CPC, CTR)
- historical_data: All available daily snapshots - USE THIS for questions about trends, comparisons, highest/lowest values
- Attribution data (standard and incremental when available)
- Events Manager health metrics
- Diagnostic results (fatigue, saturation, delivery concentration, auction shifts, tracking degradation)

IMPORTANT: When asked about "highest", "lowest", "best", "worst" days, or weekly trends, always check ALL entries in historical_data to find the correct answer.

Always cite specific metrics and provide confidence levels for your assessments."""

        user_prompt = f"""Based on the following data, answer this question: {question}

Data Context:
{json.dumps(context, indent=2, default=str)}

Provide a clear, evidence-based answer with:
1. Direct answer to the question
2. Relevant metrics cited
3. Confidence level (0-1)
4. Any recommendations (read-only, no ad modifications)"""

        try:
            response = openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            return {
                'answer': answer,
                'context_used': context,
                'model': settings.openai_model,
            }
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                'answer': f"Error generating answer: {str(e)}",
                'context_used': context,
                'model': None,
            }
    
    def generate_daily_overview(
        self, 
        target_date: Optional[datetime] = None
    ) -> Dict:
        """
        Generate an AI-powered daily overview.
        
        Args:
            target_date: Date for overview (defaults to today)
        
        Returns:
            Dictionary with overview data
        """
        if target_date is None:
            target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check for existing overview
        existing = self.db.query(DailyOverview).filter(
            DailyOverview.overview_date == target_date
        ).first()
        
        if existing:
            return {
                'overview_date': existing.overview_date.isoformat(),
                'summary': existing.summary,
                'key_changes': json.loads(existing.key_changes) if isinstance(existing.key_changes, str) else existing.key_changes,
                'insights': json.loads(existing.insights) if isinstance(existing.insights, str) else existing.insights,
                'recommendations': json.loads(existing.recommendations) if isinstance(existing.recommendations, str) else existing.recommendations,
            }
        
        context = self.get_context_for_date(target_date)
        
        # Compute diagnostics if snapshot exists
        snapshot = self.db.query(AdAccountSnapshot).filter(
            AdAccountSnapshot.snapshot_date == target_date
        ).first()
        
        if not snapshot:
            snapshot = self.db.query(AdAccountSnapshot).filter(
                AdAccountSnapshot.snapshot_date <= target_date
            ).order_by(AdAccountSnapshot.snapshot_date.desc()).first()
        
        if snapshot:
            diagnostics = self.analytics.compute_all_diagnostics(snapshot)
            for diag in diagnostics:
                self.db.add(diag)
            self.db.commit()
            context = self.get_context_for_date(target_date)
        
        system_prompt = """You are a read-only AI analyst generating a daily overview for Meta ad account performance.

Generate a comprehensive daily overview that includes:
1. Executive summary of the day's performance
2. Key changes (what changed vs previous day)
3. Insights (why things changed, based on evidence)
4. Recommendations (read-only actions, no ad modifications)

Be specific, cite metrics, and provide confidence levels. Never suggest creating, editing, or pausing ads."""

        user_prompt = f"""Generate a daily overview for {target_date.date()} based on this data:

{json.dumps(context, indent=2, default=str)}

Format your response as JSON with these keys:
- summary: string (executive summary)
- key_changes: array of objects with keys: metric, change, explanation
- insights: array of objects with keys: insight, evidence, confidence
- recommendations: array of objects with keys: recommendation, rationale, confidence

Return ONLY valid JSON, no markdown formatting."""

        try:
            response = openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean up JSON response
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            overview_data = json.loads(content)
            
            # Save to database
            overview = DailyOverview(
                overview_date=target_date,
                summary=overview_data.get('summary', ''),
                key_changes=json.dumps(overview_data.get('key_changes', [])),
                insights=json.dumps(overview_data.get('insights', [])),
                recommendations=json.dumps(overview_data.get('recommendations', []))
            )
            
            self.db.add(overview)
            self.db.commit()
            self.db.refresh(overview)
            
            return {
                'overview_date': overview.overview_date.isoformat(),
                'summary': overview.summary,
                'key_changes': overview_data.get('key_changes', []),
                'insights': overview_data.get('insights', []),
                'recommendations': overview_data.get('recommendations', []),
            }
        except Exception as e:
            logger.error(f"Error generating daily overview: {e}")
            return {
                'error': str(e),
                'overview_date': target_date.isoformat(),
            }
