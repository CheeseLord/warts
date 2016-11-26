"""
Functions for doing geometry calculations in the various types of coordinates
shared between client and server.
"""

from src.shared.config import CHUNK_SIZE

def chunkToWorld(chunkPos):
    """
    Return the world coordinates of the origin corner of chunkPos.
    """
    return map(lambda x: x * CHUNK_SIZE, chunkPos)

def worldToChunk(worldPos):
    """
    Return the chunk coordinates of the chunk containing worldPos.
    """
    return map(lambda x: x / CHUNK_SIZE, chunkPos)
