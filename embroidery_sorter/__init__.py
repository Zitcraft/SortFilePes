"""
Embroidery Sorter Library

A modular library for sorting, analyzing, and managing embroidery PES files.
Provides functionality for hashing, time estimation, workload assignment, and export.
"""

__version__ = "1.0.0"
__author__ = "Embroidery Sorter"

# Core imports for easy access
from .embroidery_core import EmbroideryCore
from .time_estimator import TimeEstimator
from .workload_assignment import WorkloadAssignment
from .file_operations import FileOperations
from .exporters import Exporters
from .config import Config

__all__ = [
    "EmbroideryCore",
    "TimeEstimator", 
    "WorkloadAssignment",
    "FileOperations",
    "Exporters",
    "Config"
]