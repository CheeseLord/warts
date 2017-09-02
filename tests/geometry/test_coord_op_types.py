import pytest

from src.shared.geometry import Coord, Distance, coordFromUnit, coordFromCBU

def test_coord_op_types():
    # Create two chunks and two distances.
    c1 = coordFromUnit((1, 2))
    c2 = coordFromCBU((3, 5), (8, 13), (21, 35))
    d1 = Distance((88, 72))
    d2 = Distance((84, 41))

    # Check that their types are what we expect. This part really shouldn't
    # fail.
    assert type(c1) == Coord
    assert type(c2) == Coord
    assert type(d1) == Distance
    assert type(d2) == Distance

    # Check that the types of all possible combinations of sums, differences,
    # and negations are correct (and that the appropriate ones give errors).
    #
    #     Coord + Coord = err
    #     Coord + Dist  = Coord
    #     Dist  + Coord = Coord
    #     Dist  + Dist  = Dist
    #
    #     Coord - Coord = Dist
    #     Coord - Dist  = Coord
    #     Dist  - Coord = err
    #     Dist  - Dist  = Dist
    #
    #           - Coord = err
    #           - Dist  = Dist

    with pytest.raises(TypeError):
        c1 + c2
    assert type(c1 + d2) == Coord
    assert type(d1 + c2) == Coord
    assert type(d1 + d2) == Distance

    assert type(c1 - c2) == Distance
    assert type(c1 - d2) == Coord
    with pytest.raises(TypeError):
        d1 - c2
    assert type(d1 - d2) == Distance

    with pytest.raises(TypeError):
        -c1
    assert type(-d1) == Distance

