# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Registry Module - YUM-Style Package Management

Modular package management system following Unix philosophy:
- Each module does one thing well
- Modules compose to form complete system
- Text-based configuration throughout
"""

from .config import RegistryConfigLoader
from .index import PackageIndexManager
from .resolver import DependencyResolver
from .transactions import TransactionLogger
from .operations import PackageOperations
from .service import RegistryService

__all__ = [
    "RegistryConfigLoader",
    "PackageIndexManager",
    "DependencyResolver",
    "TransactionLogger",
    "PackageOperations",
    "RegistryService",
]
