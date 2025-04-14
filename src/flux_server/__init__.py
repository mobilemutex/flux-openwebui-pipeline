"""
__init__.py for Flux Server

This module initializes the Flux server for Open-WebUI integration.
"""

from .server import create_app, main, ServerConfig, ModelManager, TaskQueue, TaskStatus

__all__ = ["create_app", "main", "ServerConfig", "ModelManager", "TaskQueue", "TaskStatus"]
