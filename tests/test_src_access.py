from src.shared import config

def test_answer():
    assert type(config.CHUNK_SIZE) == int
