#!/user/bin/env python

import lifx_circ.convert as convert


def test_secs_to_day_frac():
    result = convert.secs_to_day_frac(0)
    assert result == 0
