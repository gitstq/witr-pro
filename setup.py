#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Witr Pro - 安装配置
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="witr-pro",
    version="1.0.0",
    author="Witr Pro Team",
    author_email="witr-pro@example.com",
    description="高级进程监控工具 - Why is this running? Pro Edition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/witr-pro",
    py_modules=["witr_pro"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "witr-pro=witr_pro:cli",
            "witr=witr_pro:cli",
        ],
    },
    keywords="process monitor system tool cli",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/witr-pro/issues",
        "Source": "https://github.com/yourusername/witr-pro",
    },
)
