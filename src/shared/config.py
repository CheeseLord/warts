# Intended length of one game tick, in seconds. (Actual length may vary.)
TICK_LENGTH = 0.1

# Side length of a chunk, in unit coordinates.
CHUNK_SIZE = 60

# Side length of a build square, in unit coordinates.
BUILD_SIZE = 10

# Maximum number of units that a single player can control. This is separate
# from any supply/food limits and includes all buildings, overlords, summoned
# units, etc. Everything that has an id. If there are half-supply units, each
# one counts fully toward this limit. So make sure it's (significantly) greater
# than the supply cap.
MAX_PLAYER_UNITS = 256
