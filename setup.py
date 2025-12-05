# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Setup configuration for Agent Registry Package Signing System
"""

from setuptools import setup, find_packages

setup(
    name="agent-registry-signing",
    version="1.0.0",
    description="GPG package signing system for AI agent registry",
    author="Jason Cafarelli",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "python-gnupg>=0.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
        ]
    },
)
