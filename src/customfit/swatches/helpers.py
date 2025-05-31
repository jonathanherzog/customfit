from .magic_constants import gauge_to_yardage_estimates


def area_to_yards_of_yarn_estimate(square_inches, gauge):
    lower_bounds = sorted(list(gauge_to_yardage_estimates.keys()), reverse=True)
    stitch_gauge = gauge.stitches
    relevant_range_bound = None
    for lb in lower_bounds:
        if lb <= stitch_gauge:
            relevant_range_bound = lb
            break

    conversion_factor = gauge_to_yardage_estimates[relevant_range_bound]
    yards_needed = square_inches * conversion_factor
    return yards_needed
