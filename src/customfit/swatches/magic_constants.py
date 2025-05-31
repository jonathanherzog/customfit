gauge_to_yardage_estimates = {
    # The number of yards of yarn required to knit a square inch of fabric at the
    # specified stitch gauge. Based on data-mining patterns and sanity
    # checked with stashbot
    # The way to read the dictionary is that if the stitch gauge is between
    # 3 stitches per inch and 4 stitches per inch, then the yardage will be
    # the entry for 3 (in yards per square inch). Each key in the dict
    # represents the bottom value of a range, measured in stitches per inches
    # and bounded above by the next-highest key. The value represents
    # the approximate inches of yarn required to make a square inch of fabric.
    8: 1.408099021,  # L Fingering
    7: 1.320310424,  # H Fingering
    6: 1.123234064,  # Sport
    5.5: 1.048041077,  # DK
    5: 0.992295485,  # Worsted
    4.5: 0.854785418,  # Aran
    4: 0.814770339,  # Chunky
    3: 0.562421981,  # Bulky
    0: 0.5,  # Estimateto handle corner-cases we allowed into the DB by accident
}
