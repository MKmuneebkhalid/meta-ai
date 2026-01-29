"""Analytics engine for computing deterministic diagnostics."""

from sqlalchemy.orm import Session
from app.models import AdAccountSnapshot, DiagnosticResult, EventsManagerHealth
from datetime import datetime, timedelta
from typing import List, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Engine for computing ad performance diagnostics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_fatigue(
        self, 
        current_snapshot: AdAccountSnapshot
    ) -> Optional[DiagnosticResult]:
        """
        Compute ad fatigue based on frequency trends.
        
        High frequency increase indicates audience is seeing ads too often.
        """
        try:
            date_7d_ago = current_snapshot.snapshot_date - timedelta(days=7)
            
            snapshots_7d = self.db.query(AdAccountSnapshot).filter(
                AdAccountSnapshot.ad_account_id == current_snapshot.ad_account_id,
                AdAccountSnapshot.snapshot_date >= date_7d_ago,
                AdAccountSnapshot.snapshot_date < current_snapshot.snapshot_date
            ).order_by(AdAccountSnapshot.snapshot_date.desc()).limit(7).all()
            
            if len(snapshots_7d) < 3:
                return None
            
            recent_frequency = current_snapshot.frequency
            avg_frequency_7d = sum(s.frequency for s in snapshots_7d) / len(snapshots_7d)
            
            if avg_frequency_7d == 0:
                return None
            
            frequency_increase = ((recent_frequency - avg_frequency_7d) / avg_frequency_7d) * 100
            
            # Determine severity
            severity = "low"
            if frequency_increase > 30:
                severity = "high"
            elif frequency_increase > 15:
                severity = "medium"
            
            confidence = min(0.95, 0.6 + (len(snapshots_7d) / 10))
            
            explanation = f"Frequency increased by {frequency_increase:.1f}% compared to 7-day average. "
            explanation += f"Current frequency: {recent_frequency:.2f}, 7-day average: {avg_frequency_7d:.2f}."
            
            recommendation = "Consider refreshing creative assets or adjusting audience targeting to reduce ad fatigue."
            if severity == "high":
                recommendation = "High ad fatigue detected. Urgent action recommended: refresh creatives, expand audiences, or reduce frequency caps."
            
            return DiagnosticResult(
                snapshot_date=current_snapshot.snapshot_date,
                diagnostic_type="fatigue",
                metric_name="frequency",
                current_value=recent_frequency,
                previous_value=avg_frequency_7d,
                change_percentage=frequency_increase,
                severity=severity,
                confidence=confidence,
                explanation=explanation,
                recommendation=recommendation,
                diagnostic_metadata={"snapshots_analyzed": len(snapshots_7d)}
            )
        except Exception as e:
            logger.error(f"Error computing fatigue: {e}")
            return None
    
    def compute_saturation(
        self, 
        current_snapshot: AdAccountSnapshot
    ) -> Optional[DiagnosticResult]:
        """
        Compute market saturation based on reach efficiency.
        
        Declining reach per dollar spent indicates market saturation.
        """
        try:
            date_7d_ago = current_snapshot.snapshot_date - timedelta(days=7)
            
            snapshots_7d = self.db.query(AdAccountSnapshot).filter(
                AdAccountSnapshot.ad_account_id == current_snapshot.ad_account_id,
                AdAccountSnapshot.snapshot_date >= date_7d_ago,
                AdAccountSnapshot.snapshot_date < current_snapshot.snapshot_date
            ).order_by(AdAccountSnapshot.snapshot_date.desc()).limit(7).all()
            
            if len(snapshots_7d) < 3:
                return None
            
            recent_reach = current_snapshot.reach
            recent_spend = current_snapshot.spend
            
            avg_reach_7d = sum(s.reach for s in snapshots_7d) / len(snapshots_7d)
            avg_spend_7d = sum(s.spend for s in snapshots_7d) / len(snapshots_7d)
            
            if avg_reach_7d == 0 or avg_spend_7d == 0:
                return None
            
            reach_change = ((recent_reach - avg_reach_7d) / avg_reach_7d) * 100
            spend_change = ((recent_spend - avg_spend_7d) / avg_spend_7d) * 100
            
            reach_per_dollar = recent_reach / recent_spend if recent_spend > 0 else 0
            avg_reach_per_dollar = avg_reach_7d / avg_spend_7d if avg_spend_7d > 0 else 0
            
            efficiency_decline = ((reach_per_dollar - avg_reach_per_dollar) / avg_reach_per_dollar) * 100 if avg_reach_per_dollar > 0 else 0
            
            # Determine severity
            severity = "low"
            if efficiency_decline < -20:
                severity = "high"
            elif efficiency_decline < -10:
                severity = "medium"
            
            confidence = min(0.95, 0.65 + (len(snapshots_7d) / 10))
            
            explanation = f"Reach efficiency declined by {abs(efficiency_decline):.1f}%. "
            explanation += f"Current reach per dollar: ${reach_per_dollar:.2f}, 7-day average: ${avg_reach_per_dollar:.2f}."
            
            recommendation = "Market may be reaching saturation. Consider testing new audiences, expanding to new placements, or adjusting bid strategies."
            if severity == "high":
                recommendation = "High saturation detected. Consider significant audience expansion, new creative angles, or exploring new markets/placements."
            
            return DiagnosticResult(
                snapshot_date=current_snapshot.snapshot_date,
                diagnostic_type="saturation",
                metric_name="reach_efficiency",
                current_value=reach_per_dollar,
                previous_value=avg_reach_per_dollar,
                change_percentage=efficiency_decline,
                severity=severity,
                confidence=confidence,
                explanation=explanation,
                recommendation=recommendation,
                diagnostic_metadata={
                    "reach_change": reach_change,
                    "spend_change": spend_change,
                    "snapshots_analyzed": len(snapshots_7d)
                }
            )
        except Exception as e:
            logger.error(f"Error computing saturation: {e}")
            return None
    
    def compute_delivery_concentration(
        self, 
        current_snapshot: AdAccountSnapshot
    ) -> Optional[DiagnosticResult]:
        """
        Compute delivery concentration across campaigns.
        
        High concentration in few campaigns increases risk.
        """
        try:
            from app.services.meta_client import MetaAPIClient
            
            client = MetaAPIClient()
            date_start = current_snapshot.snapshot_date - timedelta(days=1)
            date_end = current_snapshot.snapshot_date
            
            campaigns = client.get_campaign_insights(date_start, date_end)
            
            if len(campaigns) < 2:
                return None
            
            total_spend = sum(c['spend'] for c in campaigns)
            if total_spend == 0:
                return None
            
            # Calculate concentration metrics
            spend_shares = [c['spend'] / total_spend for c in campaigns]
            herfindahl_index = sum(share ** 2 for share in spend_shares)
            concentration_ratio = max(spend_shares)
            
            # Determine severity
            severity = "low"
            if concentration_ratio > 0.7 or herfindahl_index > 0.5:
                severity = "high"
            elif concentration_ratio > 0.5 or herfindahl_index > 0.3:
                severity = "medium"
            
            confidence = 0.8
            
            explanation = f"Spend concentration: {concentration_ratio*100:.1f}% in top campaign. "
            explanation += f"Herfindahl index: {herfindahl_index:.3f} (higher = more concentrated)."
            
            recommendation = "High delivery concentration detected. Consider diversifying spend across more campaigns to reduce risk."
            if severity == "low":
                recommendation = "Delivery is well-distributed across campaigns."
            
            return DiagnosticResult(
                snapshot_date=current_snapshot.snapshot_date,
                diagnostic_type="delivery_concentration",
                metric_name="concentration_ratio",
                current_value=concentration_ratio,
                previous_value=None,
                change_percentage=None,
                severity=severity,
                confidence=confidence,
                explanation=explanation,
                recommendation=recommendation,
                diagnostic_metadata={
                    "herfindahl_index": herfindahl_index,
                    "total_campaigns": len(campaigns),
                    "top_campaign_spend_share": concentration_ratio
                }
            )
        except Exception as e:
            logger.error(f"Error computing delivery concentration: {e}")
            return None
    
    def compute_auction_shifts(
        self, 
        current_snapshot: AdAccountSnapshot
    ) -> Optional[DiagnosticResult]:
        """
        Compute auction/CPM shifts over time.
        
        High CPM volatility indicates competitive landscape changes.
        """
        try:
            date_7d_ago = current_snapshot.snapshot_date - timedelta(days=7)
            
            snapshots_7d = self.db.query(AdAccountSnapshot).filter(
                AdAccountSnapshot.ad_account_id == current_snapshot.ad_account_id,
                AdAccountSnapshot.snapshot_date >= date_7d_ago,
                AdAccountSnapshot.snapshot_date < current_snapshot.snapshot_date
            ).order_by(AdAccountSnapshot.snapshot_date.desc()).limit(7).all()
            
            if len(snapshots_7d) < 3:
                return None
            
            recent_cpm = current_snapshot.cpm
            if recent_cpm is None:
                return None
            
            cpm_values = [s.cpm for s in snapshots_7d if s.cpm is not None]
            if len(cpm_values) < 2:
                return None
            
            avg_cpm_7d = sum(cpm_values) / len(cpm_values)
            cpm_change = ((recent_cpm - avg_cpm_7d) / avg_cpm_7d) * 100 if avg_cpm_7d > 0 else 0
            
            # Calculate volatility
            cpm_std = np.std(cpm_values) if len(cpm_values) > 1 else 0
            cpm_volatility = (cpm_std / avg_cpm_7d) * 100 if avg_cpm_7d > 0 else 0
            
            # Determine severity
            severity = "low"
            if abs(cpm_change) > 25 or cpm_volatility > 20:
                severity = "high"
            elif abs(cpm_change) > 15 or cpm_volatility > 15:
                severity = "medium"
            
            confidence = min(0.95, 0.7 + (len(cpm_values) / 10))
            
            explanation = f"CPM changed by {cpm_change:.1f}% vs 7-day average. "
            explanation += f"Current CPM: ${recent_cpm:.2f}, 7-day average: ${avg_cpm_7d:.2f}. "
            explanation += f"Volatility: {cpm_volatility:.1f}%."
            
            recommendation = "Significant auction shifts detected. Monitor competitive landscape and consider bid adjustments."
            if severity == "low":
                recommendation = "Auction dynamics are relatively stable."
            
            return DiagnosticResult(
                snapshot_date=current_snapshot.snapshot_date,
                diagnostic_type="auction_shifts",
                metric_name="cpm",
                current_value=recent_cpm,
                previous_value=avg_cpm_7d,
                change_percentage=cpm_change,
                severity=severity,
                confidence=confidence,
                explanation=explanation,
                recommendation=recommendation,
                diagnostic_metadata={
                    "cpm_volatility": cpm_volatility,
                    "snapshots_analyzed": len(cpm_values)
                }
            )
        except Exception as e:
            logger.error(f"Error computing auction shifts: {e}")
            return None
    
    def compute_tracking_degradation(
        self, 
        current_snapshot: AdAccountSnapshot
    ) -> Optional[DiagnosticResult]:
        """
        Compute tracking/pixel quality degradation.
        
        Declining tracking quality affects attribution accuracy.
        """
        try:
            date_7d_ago = current_snapshot.snapshot_date - timedelta(days=7)
            
            recent_health = self.db.query(EventsManagerHealth).filter(
                EventsManagerHealth.snapshot_date >= current_snapshot.snapshot_date - timedelta(days=1),
                EventsManagerHealth.snapshot_date <= current_snapshot.snapshot_date
            ).first()
            
            if not recent_health:
                return None
            
            historical_health = self.db.query(EventsManagerHealth).filter(
                EventsManagerHealth.snapshot_date >= date_7d_ago,
                EventsManagerHealth.snapshot_date < current_snapshot.snapshot_date
            ).order_by(EventsManagerHealth.snapshot_date.desc()).limit(7).all()
            
            if len(historical_health) < 2:
                return None
            
            recent_score = recent_health.tracking_quality_score
            if recent_score is None:
                return None
            
            scores = [h.tracking_quality_score for h in historical_health if h.tracking_quality_score is not None]
            if not scores:
                return None
                
            avg_score = sum(scores) / len(scores)
            score_decline = avg_score - recent_score
            
            # Determine severity
            severity = "low"
            if score_decline > 0.15:
                severity = "high"
            elif score_decline > 0.08:
                severity = "medium"
            
            confidence = 0.85
            
            explanation = f"Tracking quality score declined by {score_decline:.3f}. "
            explanation += f"Current score: {recent_score:.3f}, 7-day average: {avg_score:.3f}."
            
            recommendation = "Tracking degradation detected. Review Events Manager setup, check for iOS 14.5+ impacts, verify pixel implementation."
            if severity == "high":
                recommendation = "Significant tracking degradation. Urgent review of tracking setup required. Check pixel health, iOS attribution, and server-side tracking."
            
            return DiagnosticResult(
                snapshot_date=current_snapshot.snapshot_date,
                diagnostic_type="tracking_degradation",
                metric_name="tracking_quality_score",
                current_value=recent_score,
                previous_value=avg_score,
                change_percentage=-score_decline * 100,
                severity=severity,
                confidence=confidence,
                explanation=explanation,
                recommendation=recommendation,
                diagnostic_metadata={
                    "events_received": recent_health.events_received,
                    "events_dropped": recent_health.events_dropped,
                    "snapshots_analyzed": len(historical_health)
                }
            )
        except Exception as e:
            logger.error(f"Error computing tracking degradation: {e}")
            return None
    
    def compute_all_diagnostics(
        self, 
        snapshot: AdAccountSnapshot
    ) -> List[DiagnosticResult]:
        """
        Compute all diagnostics for a snapshot.
        
        Returns:
            List of DiagnosticResult objects
        """
        diagnostics = []
        
        fatigue = self.compute_fatigue(snapshot)
        if fatigue:
            diagnostics.append(fatigue)
        
        saturation = self.compute_saturation(snapshot)
        if saturation:
            diagnostics.append(saturation)
        
        concentration = self.compute_delivery_concentration(snapshot)
        if concentration:
            diagnostics.append(concentration)
        
        auction_shifts = self.compute_auction_shifts(snapshot)
        if auction_shifts:
            diagnostics.append(auction_shifts)
        
        tracking = self.compute_tracking_degradation(snapshot)
        if tracking:
            diagnostics.append(tracking)
        
        return diagnostics
