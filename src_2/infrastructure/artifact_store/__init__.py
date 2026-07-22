"""JSON and Parquet artifact-store implementations will live here."""
"""Artifact persistence implementations."""

from .file_store import JsonArtifactStore

__all__ = ["JsonArtifactStore"]
