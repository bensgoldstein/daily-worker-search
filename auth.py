"""
AI-powered Daily Worker Search Database
Copyright (c) 2025 Benjamin Goldstein
Licensed under the MIT License - see LICENSE file for details

Simple authentication module for access control.
"""

import streamlit as st
import hmac
import hashlib
import os
from datetime import datetime, timedelta

class AuthManager:
    """Manages simple password-based authentication for the application."""
    
    def __init__(self):
        # Get password hash from environment variables or Streamlit secrets
        self.password_hash = os.getenv('APP_PASSWORD_HASH', st.secrets.get('APP_PASSWORD_HASH', ''))
        
        # Session timeout (in minutes)
        self.session_timeout = int(os.getenv('SESSION_TIMEOUT_MINUTES', '60'))
        
        # Rate limiting for failed attempts
        self.max_attempts = 5
        self.lockout_duration = 15  # minutes
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        if not self.password_hash:
            # No password set - deny access
            return False
        
        actual_hash = self.hash_password(password)
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(self.password_hash, actual_hash)
    
    def check_authentication(self) -> bool:
        """Check if user is authenticated."""
        if 'authenticated' not in st.session_state:
            return False
        
        if not st.session_state.authenticated:
            return False
        
        # Check session timeout
        if 'auth_time' in st.session_state:
            auth_time = st.session_state.auth_time
            if datetime.now() - auth_time > timedelta(minutes=self.session_timeout):
                self.logout()
                return False
        
        return True
    
    def login(self, password: str) -> bool:
        """Attempt to log in with a password."""
        # Check rate limiting
        if not self._check_rate_limit():
            st.error(f"Too many failed attempts. Please try again in {self.lockout_duration} minutes.")
            return False
        
        if self.verify_password(password):
            st.session_state.authenticated = True
            st.session_state.auth_time = datetime.now()
            self._reset_failed_attempts()
            return True
        else:
            self._record_failed_attempt()
            return False
    
    def logout(self):
        """Log out the current user."""
        st.session_state.authenticated = False
        if 'auth_time' in st.session_state:
            del st.session_state.auth_time
    
    def _check_rate_limit(self) -> bool:
        """Check if rate limited due to failed attempts."""
        if 'failed_attempts' not in st.session_state:
            return True
        
        attempts, last_attempt = st.session_state.failed_attempts
        
        # Check if lockout period has passed
        if attempts >= self.max_attempts:
            if datetime.now() - last_attempt < timedelta(minutes=self.lockout_duration):
                return False
            else:
                # Reset after lockout period
                del st.session_state.failed_attempts
        
        return True
    
    def _record_failed_attempt(self):
        """Record a failed login attempt."""
        if 'failed_attempts' not in st.session_state:
            st.session_state.failed_attempts = (1, datetime.now())
        else:
            attempts, _ = st.session_state.failed_attempts
            st.session_state.failed_attempts = (attempts + 1, datetime.now())
    
    def _reset_failed_attempts(self):
        """Reset failed attempts counter."""
        if 'failed_attempts' in st.session_state:
            del st.session_state.failed_attempts
    
    def require_authentication(self):
        """Require authentication to access the page."""
        if not self.check_authentication():
            self.show_login_page()
            st.stop()
    
    def show_login_page(self):
        """Display the login page."""
        st.markdown("""
        <div style="max-width: 400px; margin: auto; padding: 2rem;">
            <h1 style="text-align: center;">🔐 Authentication Required</h1>
            <p style="text-align: center; color: #666;">
                This is a private research database. Please enter the access password to continue.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                password = st.text_input("Password", type="password", help="Enter the shared access password")
                
                submit = st.form_submit_button("Login", use_container_width=True)
                
                if submit:
                    if self.login(password):
                        st.success("Successfully authenticated!")
                        st.rerun()
                    else:
                        st.error("Invalid password")
        
        # Show contact info for access requests
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: #666; font-size: 0.9em;">
            <p>To request access, please contact Benjamin Goldstein.</p>
            <p>© 2025 Benjamin Goldstein</p>
        </div>
        """, unsafe_allow_html=True)


# Utility function to generate password hashes
def generate_password_hash(password: str) -> str:
    """Generate a password hash for storage in environment variables."""
    return hashlib.sha256(password.encode()).hexdigest()


if __name__ == "__main__":
    # Command-line utility to generate password hashes
    import sys
    if len(sys.argv) > 1:
        password = sys.argv[1]
        hash_value = generate_password_hash(password)
        print(f"Password hash: {hash_value}")
        print(f"\nAdd this to your .streamlit/secrets.toml file:")
        print(f'APP_PASSWORD_HASH = "{hash_value}"')
    else:
        print("Usage: python auth.py <password>")
        print("This will generate a password hash for secure storage.")