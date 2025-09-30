"""
AI-powered Daily Worker Search Database
Copyright (c) 2025 Benjamin Goldstein
Licensed under the MIT License - see LICENSE file for details

Usage monitoring and cost control module.
"""

import streamlit as st
import os
from datetime import datetime, date, timedelta
from typing import Dict, Optional
import json
from pathlib import Path

class UsageMonitor:
    """Monitor and limit usage to control costs."""
    
    def __init__(self):
        # Load limits from environment/secrets
        self.max_searches_per_hour = int(os.getenv('MAX_SEARCHES_PER_HOUR', 
                                                   st.secrets.get('MAX_SEARCHES_PER_HOUR', 100)))
        self.max_searches_per_day = int(os.getenv('MAX_SEARCHES_PER_DAY', 
                                                  st.secrets.get('MAX_SEARCHES_PER_DAY', 500)))
        self.max_pdf_downloads_per_day = int(os.getenv('MAX_PDF_DOWNLOADS_PER_DAY', 
                                                       st.secrets.get('MAX_PDF_DOWNLOADS_PER_DAY', 50)))
        
        # Cost estimates (adjust based on your actual costs)
        self.cost_per_search = 0.001  # Estimated Pinecone cost per search
        self.cost_per_ai_summary = 0.01  # Estimated Gemini cost per summary
        self.cost_per_pdf = 0.005  # Estimated compute cost per PDF
        
        # Initialize usage tracking in session state
        self._init_usage_tracking()
    
    def _init_usage_tracking(self):
        """Initialize usage tracking in session state."""
        if 'usage_stats' not in st.session_state:
            st.session_state.usage_stats = {
                'searches_today': 0,
                'searches_this_hour': 0,
                'pdfs_today': 0,
                'ai_summaries_today': 0,
                'last_reset_date': date.today().isoformat(),
                'last_hour_reset': datetime.now().hour,
                'estimated_cost_today': 0.0
            }
        
        # Check if we need to reset daily/hourly counters
        self._check_reset_counters()
    
    def _check_reset_counters(self):
        """Reset counters if needed."""
        stats = st.session_state.usage_stats
        current_date = date.today()
        current_hour = datetime.now().hour
        
        # Reset daily counters
        if stats['last_reset_date'] != current_date.isoformat():
            stats['searches_today'] = 0
            stats['pdfs_today'] = 0
            stats['ai_summaries_today'] = 0
            stats['estimated_cost_today'] = 0.0
            stats['last_reset_date'] = current_date.isoformat()
            
            # Log daily usage before reset (optional - you could save this)
            self._log_daily_usage(stats)
        
        # Reset hourly counter
        if stats['last_hour_reset'] != current_hour:
            stats['searches_this_hour'] = 0
            stats['last_hour_reset'] = current_hour
    
    def check_search_limit(self) -> bool:
        """Check if user can perform a search."""
        stats = st.session_state.usage_stats
        
        # Check hourly limit
        if stats['searches_this_hour'] >= self.max_searches_per_hour:
            remaining_minutes = 60 - datetime.now().minute
            st.error(f"Hourly search limit reached ({self.max_searches_per_hour} searches). "
                    f"Please wait {remaining_minutes} minutes.")
            return False
        
        # Check daily limit
        if stats['searches_today'] >= self.max_searches_per_day:
            st.error(f"Daily search limit reached ({self.max_searches_per_day} searches). "
                    f"Please try again tomorrow.")
            return False
        
        return True
    
    def record_search(self, used_ai: bool = False):
        """Record a search and update costs."""
        stats = st.session_state.usage_stats
        stats['searches_today'] += 1
        stats['searches_this_hour'] += 1
        stats['estimated_cost_today'] += self.cost_per_search
        
        if used_ai:
            stats['ai_summaries_today'] += 1
            stats['estimated_cost_today'] += self.cost_per_ai_summary
    
    def check_pdf_limit(self) -> bool:
        """Check if user can download a PDF."""
        stats = st.session_state.usage_stats
        
        if stats['pdfs_today'] >= self.max_pdf_downloads_per_day:
            st.error(f"Daily PDF download limit reached ({self.max_pdf_downloads_per_day} PDFs). "
                    f"Please try again tomorrow.")
            return False
        
        return True
    
    def record_pdf_download(self):
        """Record a PDF download."""
        stats = st.session_state.usage_stats
        stats['pdfs_today'] += 1
        stats['estimated_cost_today'] += self.cost_per_pdf
    
    def get_usage_summary(self) -> Dict:
        """Get current usage summary."""
        stats = st.session_state.usage_stats
        
        return {
            'searches_today': stats['searches_today'],
            'searches_remaining_today': max(0, self.max_searches_per_day - stats['searches_today']),
            'searches_remaining_hour': max(0, self.max_searches_per_hour - stats['searches_this_hour']),
            'pdfs_remaining': max(0, self.max_pdf_downloads_per_day - stats['pdfs_today']),
            'estimated_cost_today': stats['estimated_cost_today'],
            'ai_summaries_today': stats['ai_summaries_today']
        }
    
    def display_usage_sidebar(self):
        """Display usage information in sidebar."""
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 📊 Usage Today")
            
            summary = self.get_usage_summary()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Searches", 
                         f"{summary['searches_today']}/{self.max_searches_per_day}",
                         f"{summary['searches_remaining_today']} left")
            with col2:
                st.metric("PDFs", 
                         f"{st.session_state.usage_stats['pdfs_today']}/{self.max_pdf_downloads_per_day}",
                         f"{summary['pdfs_remaining']} left")
            
            # Show hourly limit if getting close
            if summary['searches_remaining_hour'] < 10:
                st.warning(f"⚠️ {summary['searches_remaining_hour']} searches left this hour")
            
            # Show estimated cost
            if summary['estimated_cost_today'] > 0:
                st.metric("Est. Cost Today", f"${summary['estimated_cost_today']:.2f}")
    
    def _log_daily_usage(self, stats: Dict):
        """Log daily usage (optional - implement if you want to track long-term)."""
        # You could save this to a file or database
        # For now, just log to console
        log_entry = {
            'date': stats['last_reset_date'],
            'searches': stats['searches_today'],
            'pdfs': stats['pdfs_today'],
            'ai_summaries': stats['ai_summaries_today'],
            'estimated_cost': stats['estimated_cost_today']
        }
        print(f"Daily usage log: {json.dumps(log_entry)}")
    
    def check_cost_threshold(self) -> bool:
        """Check if daily cost is approaching limit."""
        daily_cost_limit = float(os.getenv('DAILY_COST_LIMIT', 
                                          st.secrets.get('DAILY_COST_LIMIT', 5.0)))
        
        current_cost = st.session_state.usage_stats['estimated_cost_today']
        
        if current_cost >= daily_cost_limit:
            st.error(f"Daily cost limit reached (${daily_cost_limit:.2f}). "
                    f"Service paused until tomorrow.")
            return False
        elif current_cost >= daily_cost_limit * 0.8:
            st.warning(f"Approaching daily cost limit: ${current_cost:.2f} of ${daily_cost_limit:.2f}")
        
        return True