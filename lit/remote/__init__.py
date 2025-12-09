"""Remote module for distributed Git operations.

This module handles all remote-related functionality:
- Remote management (add, remove, list)
- Fetch operations
- Push operations  
- Clone operations
- Network protocol (future)
"""

from lit.remote.remote import RemoteManager

__all__ = [
    'RemoteManager',
]
