"""XMP sidecar writer module for non-destructive metadata tagging."""

from .exiftool_wrapper import ExifToolWrapper
from .metadata_builder import MetadataBuilder

__all__ = [
    'ExifToolWrapper',
    'MetadataBuilder'
]
