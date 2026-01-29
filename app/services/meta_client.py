"""Meta Marketing API Client for fetching ad account data."""

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights
from facebook_business.adobjects.adspixel import AdsPixel
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class MetaAPIClient:
    """Client for interacting with Meta's Marketing API (read-only)."""
    
    def __init__(self):
        FacebookAdsApi.init(
            settings.meta_app_id,
            settings.meta_app_secret,
            settings.meta_access_token
        )
        self.ad_account_id = settings.meta_ad_account_id
        self.account = AdAccount(self.ad_account_id)
    
    def get_account_insights(
        self,
        date_start: datetime,
        date_end: datetime,
        level: str = "account",
        breakdowns: Optional[List[str]] = None
    ) -> Dict:
        """
        Fetch account-level insights for a date range.
        
        Args:
            date_start: Start date
            date_end: End date
            level: Aggregation level (account, campaign, adset, ad)
            breakdowns: Optional breakdowns (age, gender, placement, etc.)
        
        Returns:
            Dictionary of metrics
        """
        try:
            params = {
                'time_range': {
                    'since': date_start.strftime('%Y-%m-%d'),
                    'until': date_end.strftime('%Y-%m-%d')
                },
                'level': level,
                'fields': [
                    'spend',
                    'impressions',
                    'clicks',
                    'reach',
                    'frequency',
                    'cpm',
                    'cpc',
                    'ctr',
                    'actions',
                    'action_values',
                    'cost_per_action_type',
                    'conversions',
                    'conversion_values',
                ],
            }
            
            if breakdowns:
                params['breakdowns'] = breakdowns
            
            insights = self.account.get_insights(params=params)
            
            if not insights:
                return {}
            
            result = {}
            for insight in insights:
                result = {
                    'spend': float(insight.get('spend', 0)),
                    'impressions': int(insight.get('impressions', 0)),
                    'clicks': int(insight.get('clicks', 0)),
                    'reach': int(insight.get('reach', 0)),
                    'frequency': float(insight.get('frequency', 0)),
                    'cpm': float(insight.get('cpm', 0)) if insight.get('cpm') else None,
                    'cpc': float(insight.get('cpc', 0)) if insight.get('cpc') else None,
                    'ctr': float(insight.get('ctr', 0)) if insight.get('ctr') else None,
                    'actions': insight.get('actions', []),
                    'action_values': insight.get('action_values', []),
                    'cost_per_action_type': insight.get('cost_per_action_type', []),
                    'conversions': insight.get('conversions', []),
                    'conversion_values': insight.get('conversion_values', []),
                }
                break
            
            return result
        except Exception as e:
            logger.error(f"Error fetching account insights: {e}")
            raise
    
    def get_incremental_attribution(
        self,
        date_start: datetime,
        date_end: datetime
    ) -> Optional[Dict]:
        """
        Fetch incremental attribution data (28-day click/view windows).
        
        Returns:
            Attribution data or None if unavailable
        """
        try:
            params = {
                'time_range': {
                    'since': date_start.strftime('%Y-%m-%d'),
                    'until': date_end.strftime('%Y-%m-%d')
                },
                'attribution_windows': ['28d_click', '28d_view'],
                'level': 'account',
            }
            
            insights = self.account.get_insights(
                params=params,
                fields=[
                    'spend',
                    'impressions',
                    'clicks',
                    'conversions',
                    'conversion_values',
                ]
            )
            
            if not insights:
                return None
            
            result = {}
            for insight in insights:
                result = {
                    'spend': float(insight.get('spend', 0)),
                    'impressions': int(insight.get('impressions', 0)),
                    'clicks': int(insight.get('clicks', 0)),
                    'conversions': insight.get('conversions', []),
                    'conversion_values': insight.get('conversion_values', []),
                }
                break
            
            return result
        except Exception as e:
            logger.warning(f"Incremental attribution not available: {e}")
            return None
    
    def get_events_manager_data(
        self,
        pixel_id: Optional[str] = None
    ) -> Dict:
        """
        Fetch Events Manager / Pixel tracking data.
        
        Returns:
            Pixel health and event statistics
        """
        try:
            pixels = self.account.get_ads_pixels()
            pixel_data = []
            
            for pixel in pixels:
                pixel_id = pixel.get('id')
                pixel_name = pixel.get('name')
                
                try:
                    stats = pixel.get_insights(params={
                        'date_preset': 'last_7d',
                    })
                    
                    pixel_info = {
                        'pixel_id': pixel_id,
                        'pixel_name': pixel_name,
                        'stats': stats,
                    }
                    pixel_data.append(pixel_info)
                except Exception as e:
                    logger.warning(f"Could not fetch stats for pixel {pixel_id}: {e}")
                    pixel_info = {
                        'pixel_id': pixel_id,
                        'pixel_name': pixel_name,
                        'stats': None,
                    }
                    pixel_data.append(pixel_info)
            
            return {
                'pixels': pixel_data,
                'total_pixels': len(pixel_data),
            }
        except Exception as e:
            logger.error(f"Error fetching Events Manager data: {e}")
            return {'pixels': [], 'total_pixels': 0}
    
    def get_campaign_insights(
        self,
        date_start: datetime,
        date_end: datetime
    ) -> List[Dict]:
        """
        Fetch campaign-level insights.
        
        Returns:
            List of campaign metrics
        """
        try:
            params = {
                'time_range': {
                    'since': date_start.strftime('%Y-%m-%d'),
                    'until': date_end.strftime('%Y-%m-%d')
                },
                'level': 'campaign',
                'fields': [
                    'campaign_id',
                    'campaign_name',
                    'spend',
                    'impressions',
                    'clicks',
                    'reach',
                    'frequency',
                    'cpm',
                    'cpc',
                    'ctr',
                    'actions',
                    'conversions',
                ],
            }
            
            insights = self.account.get_insights(params=params)
            
            campaigns = []
            for insight in insights:
                campaigns.append({
                    'campaign_id': insight.get('campaign_id'),
                    'campaign_name': insight.get('campaign_name'),
                    'spend': float(insight.get('spend', 0)),
                    'impressions': int(insight.get('impressions', 0)),
                    'clicks': int(insight.get('clicks', 0)),
                    'reach': int(insight.get('reach', 0)),
                    'frequency': float(insight.get('frequency', 0)),
                    'cpm': float(insight.get('cpm', 0)) if insight.get('cpm') else None,
                    'cpc': float(insight.get('cpc', 0)) if insight.get('cpc') else None,
                    'ctr': float(insight.get('ctr', 0)) if insight.get('ctr') else None,
                    'actions': insight.get('actions', []),
                    'conversions': insight.get('conversions', []),
                })
            
            return campaigns
        except Exception as e:
            logger.error(f"Error fetching campaign insights: {e}")
            return []
