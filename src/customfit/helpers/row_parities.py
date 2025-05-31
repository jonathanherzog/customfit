RS = "RS"
WS = "WS"
ANY = "ANY"


def to_string(parity):
    assert parity in [RS, WS, ANY]
    return parity


def from_string(parity):
    assert parity in [RS, WS, ANY]
    return parity


def reverse_parity(parity):
    assert parity in [RS, WS, ANY]
    if parity == RS:
        return WS
    elif parity == WS:
        return RS
    else:
        return ANY
