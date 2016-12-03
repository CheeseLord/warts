"""
Functions for doing geometry calculations in the various types of coordinates
shared between client and server.
"""

from src.shared.config import CHUNK_SIZE

def chunkToUnit(chunkPos):
    """
    Return the unit coordinates of the origin corner of chunkPos.
    """
    return map(lambda x: x * CHUNK_SIZE, chunkPos)

def unitToChunk(unitPos):
    """
    Return the chunk coordinates of the chunk containing unitPos.
    """
    return map(lambda x: x / CHUNK_SIZE, chunkPos)
