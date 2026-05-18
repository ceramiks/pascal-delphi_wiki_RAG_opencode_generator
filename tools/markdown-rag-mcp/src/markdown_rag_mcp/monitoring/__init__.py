"""
Monitoring package for file system change detection.

This package provides components for monitoring file system changes
and automatically updating the document index when files are added,
modified, or deleted.
"""

from markdown_rag_mcp.monitoring.file_watcher import FileChangeEvent, MarkdownFileWatcher
from markdown_rag_mcp.monitoring.monitoring_coordinator import MonitoringCoordinator

__all__ = [
    "FileChangeEvent",
    "MarkdownFileWatcher",
    "MonitoringCoordinator",
]
