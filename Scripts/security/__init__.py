"""
NOAH Security Module
Provides security initialization and management utilities
"""

from .security_initializer import ensure_security_initialized, get_security_config

__all__ = ['ensure_security_initialized', 'get_security_config']