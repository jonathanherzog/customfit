from ..models import SweaterPattern, SweaterPatternPieces, SweaterSchematic

# TODO: replace the following, or move somewhere better


def _make_IPS_from_IGP(user, igp):
    ips = SweaterSchematic.make_from_garment_parameters(user, igp)
    ips.clean()
    ips.save()
    return ips


def _make_IPP_from_IPS(ips):
    ipp = SweaterPatternPieces.make_from_individual_pieced_schematic(ips)
    ipp.full_clean()
    ipp.save()
    return ipp


def _make_pattern_from_IPP(user, ipp):
    pattern = SweaterPattern.make_from_individual_pattern_pieces(user, ipp)
    pattern.clean()
    pattern.save()
    return pattern
