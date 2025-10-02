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
import threading
import time
from loguru import logger

class UsageMonitor:
    """Monitor and limit usage to control costs."""
    
    # Class-level storage for cross-session usage tracking
    _global_usage = {
        'searches_today': 0,
        'searches_total': 0,
        'last_reset_date': date.today().isoformat(),
        'lock': threading.Lock()
    }
    
    # File path for persistent storage
    _usage_file = Path(__file__).parent / '.usage_stats.json'
    _loaded = False
    
    def __init__(self):
        # Load limits from environment/secrets
        self.max_searches_per_day = int(os.getenv('MAX_SEARCHES_PER_DAY', 
                                                  st.secrets.get('MAX_SEARCHES_PER_DAY', 500)))
        
        # Cost estimates (adjust based on your actual costs)
        self.cost_per_search = 0.001  # Estimated Pinecone cost per search
        self.cost_per_ai_summary = 0.01  # Estimated Gemini cost per summary
        
        # Initialize or load usage tracking
        self._init_usage_tracking()
    
    @classmethod
    def _load_global_usage(cls):
        """Load usage stats from file (thread-safe)."""
        with cls._global_usage['lock']:
            if not cls._loaded:
                try:
                    if cls._usage_file.exists():
                        with open(cls._usage_file, 'r') as f:
                            data = json.load(f)
                            cls._global_usage.update(data)
                            logger.info(f"Loaded usage stats: {data}")
                    cls._loaded = True
                except Exception as e:
                    logger.error(f"Error loading usage stats: {e}")
    
    @classmethod
    def _save_global_usage(cls):
        """Save usage stats to file (thread-safe)."""
        with cls._global_usage['lock']:
            try:
                data = {
                    'searches_today': cls._global_usage['searches_today'],
                    'searches_total': cls._global_usage['searches_total'],
                    'last_reset_date': cls._global_usage['last_reset_date']
                }
                with open(cls._usage_file, 'w') as f:
                    json.dump(data, f)
                logger.info(f"Saved usage stats: {data}")
            except Exception as e:
                logger.error(f"Error saving usage stats: {e}")
    
    def _init_usage_tracking(self):
        """Initialize usage tracking."""
        # Load global usage stats
        self._load_global_usage()
        
        # Check if we need to reset daily counter
        self._check_reset_daily_counter()
        
        # Initialize session state for user display
        if 'user_searches_today' not in st.session_state:
            st.session_state.user_searches_today = 0
    
    def _check_reset_daily_counter(self):
        """Reset daily counter if needed (thread-safe)."""
        current_date = date.today()
        
        with self._global_usage['lock']:
            last_reset = date.fromisoformat(self._global_usage['last_reset_date'])
            
            if current_date > last_reset:
                # Log daily usage before reset
                logger.info(f"Daily reset: {self._global_usage['last_reset_date']} had {self._global_usage['searches_today']} searches")
                
                # Reset daily counter
                self._global_usage['searches_today'] = 0
                self._global_usage['last_reset_date'] = current_date.isoformat()
                
                # Save immediately
                self._save_global_usage()
    
    def check_search_limit(self) -> bool:
        """Check if search can be performed (global limit)."""
        self._check_reset_daily_counter()
        
        with self._global_usage['lock']:
            if self._global_usage['searches_today'] >= self.max_searches_per_day:
                st.error(f"Daily search limit reached ({self.max_searches_per_day} searches across all users). "
                        f"Please try again tomorrow.")
                return False
        
        return True
    
    def record_search(self, used_ai: bool = False):
        """Record a search and update costs."""
        with self._global_usage['lock']:
            self._global_usage['searches_today'] += 1
            self._global_usage['searches_total'] += 1
            
            # Save to file
            self._save_global_usage()
        
        # Update session state for display
        st.session_state.user_searches_today += 1
        
        # Log the search
        logger.info(f"Search recorded. Today: {self._global_usage['searches_today']}, Total: {self._global_usage['searches_total']}")
    
    def get_usage_summary(self) -> Dict:
        """Get current usage summary."""
        with self._global_usage['lock']:
            searches_today = self._global_usage['searches_today']
            searches_total = self._global_usage['searches_total']
        
        return {
            'searches_today': searches_today,
            'searches_remaining_today': max(0, self.max_searches_per_day - searches_today),
            'searches_total': searches_total,
            'user_searches_today': st.session_state.get('user_searches_today', 0),
            'estimated_cost_today': searches_today * (self.cost_per_search + self.cost_per_ai_summary)
        }
    
    def display_usage_sidebar(self):
        """Display usage information in sidebar."""
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 📊 Usage Statistics")
            
            summary = self.get_usage_summary()
            
            # Global usage across all users
            st.metric("Global Searches Today", 
                     f"{summary['searches_today']}/{self.max_searches_per_day}",
                     f"{summary['searches_remaining_today']} remaining")
            
            # User's personal session count
            st.metric("Your Searches Today", 
                     summary['user_searches_today'])
            
            # Total searches all-time
            st.metric("Total Searches All-Time", 
                     f"{summary['searches_total']:,}")
            
            # Show warning if approaching limit
            if summary['searches_remaining_today'] < 50:
                st.warning(f"⚠️ Only {summary['searches_remaining_today']} searches remaining today!")
            
            # Estimated cost (optional)
            if st.checkbox("Show estimated costs", value=False):
                st.metric("Est. Cost Today", f"${summary['estimated_cost_today']:.2f}")
    
    def check_cost_threshold(self) -> bool:
        """Check if daily cost is approaching limit."""
        # This is now simplified since we're mainly tracking searches
        daily_cost_limit = float(os.getenv('DAILY_COST_LIMIT', 
                                          st.secrets.get('DAILY_COST_LIMIT', 10.0)))
        
        with self._global_usage['lock']:
            searches_today = self._global_usage['searches_today']
        
        current_cost = searches_today * (self.cost_per_search + self.cost_per_ai_summary)
        
        if current_cost >= daily_cost_limit:
            st.error(f"Daily cost limit reached (${daily_cost_limit:.2f}). "
                    f"Service paused until tomorrow.")
            return False
        elif current_cost >= daily_cost_limit * 0.8:
            st.warning(f"Approaching daily cost limit: ${current_cost:.2f} of ${daily_cost_limit:.2f}")
        
        return True
    
    # Remove PDF-related methods since we're not tracking PDFs
    def check_pdf_limit(self) -> bool:
        """Deprecated - PDF downloads are not limited."""
        return True
    
    def record_pdf_download(self):
        """Deprecated - PDF downloads are not tracked."""
        pass