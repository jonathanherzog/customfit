
==================================================
Knitting patterns for non-knitters
==================================================

In this section, we briefly explain some important concepts about
knitting patterns. This was written for the non-knitter, so as to help
future developers get up to speed on what this code is making, how it
is made, and why it is made this way.

Sweaters can be categorized a number of ways:

* First, a sweater can be a *pullover* or a *cardigan*. A pullover
  sweater is an unbroken cylinder with sleeves--what you normally
  think of when you think 'sweater'. A cardigan has a
  'cut' from neck to waist, usually with a zipper or buttons along the
  front. (Short form: a pullover is what Bill Cosby wears, and a
  cardigan is what Mister Rogers wore.) 

* A sweater can be a *vest* or be *sleeved*.

* Also, there are different sweater *constructions*: the way in which
  built from pieces. A *pieced* construction is one in which the back
  piece, front piece (or pieces, in the case of a cardigan) and
  sleeves are knit separately and *seamed* together. A *seamless*
  construction is one in which the entire sweater is knit as one
  piece.

  .. note::
    Right now, we only have pieced constructions implemented, but we
    plan to add seamless constructions soon.

* There are several different kinds of *necklines*: the way in which
  the neck-hole is shaped. Technically, the neckline was two parts:
  the front part and the back part. The back part is always the same,
  but the front part could be:
  
  * a *vee-neck*,

  * a *crew* neck,

  * a *scoop* neck, etc.


  .. note::
    Right now, we only have vee-necks implemented, but we plan to
    implement many more.

* For those sweaters that have sleeves, there are three different
  kinds of them:

  * A *tapered* sleeve, where it is larger at the bicep than at the
    wrist,

  * A *straight* sleeve, which is the same size all the way down, and

  * A *bell* sleeve, which gets bigger from bicep to wrist.

Not only can sleeves get larger or smaller, but the torso-portions of
the sweater can too. Generally, a sweater will get more narrow as it
goes from hip to waist and then wider as it goes from waist to
bust. How do knitters make this happen? To explain that, a little bit
about how knitting actually works:

Basically, the knitter is knotting together little loops of yarn,
called *stitches*, which go side-to-side across a garment in
*rows*. These loops will all be the same size in a given garment, but
will differ from garment to garment. That is, each garment will have
its own *gauge*: loop-size, measured in both stitches per inch and
rows per inch. (Remember, stitches go from side-to-side across a
garment, and rows go up and down. So 'stitches per inch' measures
horizontal density of stitches, while 'rows per inch' measures
vertical density.) The gauge of a garment depends on the size of the
needles (yes, they come in different sizes) and the size of the
yarn. However, it is also highly individual to each knitter. Even
given the same yarn and needles, two different knitters will produce
two different gauges. The only way for a knitter to accurately
estimate the gauge they will produce is to knit a *swatch*: a
rectangular handkerchief-sized piece of cloth from which they can
actually measure their gauge.


Okay. So back to *shaping* the pieces: to make a piece of knitting
taller, the knitter simply knits more rows. (The way you make a piece
shorter is to *rip out* rows, and knitters hate doing so.) To make a
garment wider or narrower, the knitter has to add stitches (called
*increasing*) or remove stitches (*decreasing*) as they progress up
the piece. The easiest way to do this is to increase or decrease at
the edges, and this is sometimes what is done. However, it is often
better to increase or decrease in the middle of the piece. When this
happens, knitters often like for the increases or decreases of
different rows to be aligned vertically in *darts*. Therefore, they will often
add *markers* (little plastic rings) to their knitting. These rings
will climb from row to row, just like the needles do, but stay in
place horizontally. Therefore, they make it convenient to keep track
of where your piece-interior increases and decreases all happen and
ensure that you get a nice, vertical dart. 

In torso pieces, there are usually two darts in the front and two in
the back. However, there are limits to how quickly a dart can *shape*
the garment: a given dart can only add or subtract one stitch per row,
and there should be at least three rows between successive
additions/deletions on a given dart. Therefore, knitters will often
add *double darts* (a second pair of darts, making four darts total)
to a piece to get a higher rate of shaping, or even *triple darts*
(yet another pair, making six in total). 

The point of all this shaping is control how the sweater will fit on a
body, but it is often not ideal to have the garment's measurements
exactly fit the body's measurements.  The *ease* of a garment, at a
point along the body like the waist, is the difference between the
circumference of the garment and the circumference of the *body* at
that point. If a sweater has a 35-inch waist circumference, for
example, and it is being worn by someone with a 33-inch waist, it has
two inches of ease in the waist. **Eases can be negative.** Yes,
someone with a 35-inch waist can wear a sweater with a 33-inch waist
(making two inches of *negative ease*). Knitted sweaters stretch, and
small amounts of negative ease can be easily tolerated. (Stretching
the fabric horizontally will shrink the fabric vertically, however, so
a garment with negative ease should be knit longer than would
otherwise be appropriate.) The presence or absence of ease, and how
much to add when appropriate, is **supremely important** to how
flattering the garment will be on a given person. The 'right' amounts
of ease to add will vary depending on the woman's shape, and this
process is generally not well understood by either knitters or
designers. Our process for calculating ease (from a woman's shape) is
a significant part of our 'secret sauce.'

For extremely busty women, however, eases and shaping will not be
enough. In addition, something called *bust darts* are needed.  In a
'standard' sweater (by way of contrast) the front and the back of the
sweater will have the same widths. If you were to lay the front piece
and the back piece of a standard sweater (pieced construction) on top
of each other, they would have the same silhouette (aside from
necklines). However, this neither fits nor flatters women with large
busts. Therefore, such women use bust darts to produce larger busts in
the front than in the back. 

There are two ways of doing this, *vertical* bust darts or
*horizontal* bust darts:

* Vertical bust darts are very simple: the front of the garment is
  shaped to have a wider bust than the back (and the front neckline is
  widened accordingly).

* Horizontal bust darts, on the other hand, are achieved using
  something called *short rows*. Generally, a row either goes all the
  way from one edge of the piece to the other (in a pieced
  construction) or all the way around the garment (seamless
  construction). A short row, on the other hand, does not. The knitter
  starts at an edge, yes, but then only knits part of the way across
  before stopping and knitting the next row on top of that first short
  row and going back the opposite way. That row usually stops before
  the edge, and the knitter start another row on top of that one going
  back the first way. The knitter can do this any number of times,
  building a stack of rows in the middle of the piece. Usually each
  short row is slightly shorter than the one below it, and the
  resulting stack is trapazoidal-shaped. The knitter then resumes
  knitting edge-to-edge, except that the new rows attach to the top of
  the stack of short rows. The effect to add three-dimensional shaping
  to the garment, where the short rows make the bottom of a 'pocket'
  to go over the bust.

That's it for body shaping, but there are still a few concepts left to
explain. Let's start with sleeves, arms, and shoulders: 

* The *armhole* is the hole left in the body piece(s) for the arm. 

* The *shoulder stitches* or *shoulder bindoffs* are the stitches on
  the top of the body pieces between the neckline and the armhole.

* The *armcap* is the top of the sleeve (if the garment is sleeved)
  and has a bell-curve-like shape called the *armscye*. 

It turns out that there are a **lot** of contraints regarding these
parts of the garment:

* The shoulder bindoffs and armhole shaping must be exactly the same
  in the front and back of the garment.

* The armhole shaping (particularly the bottom of the armhole) must
  provide the right amount of space for the arm, and must 'curve' the
  edge of the body-pieces at right rate.

* The edge of the armcap must be the same length as the perimeter of
  the armhole, and must be neither too tall-and-narrow nor too
  wide-and-squat. Furthermore, parts of the armcap must exactly match
  parts of the armhole. (Specifically, the outer edges of the armscye
  must match the shaping at the bottom of the armhole.)

The computation of armholes and armcaps are regarded as black magic in
the knitting community, and our algorithm for doing so is another
piece of our secret sauce.

Lastly, there are a few other concepts that will be useful to know for
the rest of the document:

* While there is one type of knitting (*stockinette* stitch) where
  every stitch is formed exactly the same way, this doesn't have to be
  the case. There are lots of different ways to make the loops, and
  knitters often like to repeatedly knit short sequences of these
  loop-types over and over again along a row. As they do, these
  *repeats* (sequences) will stack on top of each other and make nice
  vertical decorations.

  If a knitter wants to use repeats, one of two things can happen:

  * The garment can be constructed so that all garment-edges
    (cast-ons, waists, busts, etc.) fall at the edge of a
    repeat. This may prevent the garment from achieving exactly the
    right eases for the body in question, however.

  * The garment can be constructed to achieve exactly the right eases,
    even if that means the garment edge may fall in the middle of a
    repeat. 

  (Technically, some repeats require a stitch or two of
  stockinette at the edge for seaming purposes, but that doesn't
  fundamentally change any of the previous discussion.)

  .. note::
     We have not really ironed out exactly how we want to handle
     repeats. The current thinking is that we should have piece-edges
     line up with repeats if they are 'close', where 'close' means 'a
     half inch or so apart'. But this isn't in the code yet, and our
     thinking could change in the near future.

* A *panel* is a repeat on steroids. It is a very long repeat that
  actually changes (in a repeating way) from row to row. Those
  braids/twists/vines/etc. that you see climbing up a sweater? Those
  are panels. 

  .. note::
    We do not handle panels yet, and don't have any clear ideas about
    how to do so in the near future. It will be something the knitters
    demand, though, so it will happen sooner or later.



* The *schematic* of a garment is a blueprint of the finished
  pieces. It will contain a silhouette of each piece--not necessarily
  to scale, but labelled with the actual dimensions of the piece (in
  inches and/or cm). Also, the silhouettes will display the same
  necklines, sleeve-shaping, etc. as the finished garment. Schematics
  found in knitting books and magazines will often have *charts*
  showing the repeats or panels used in the garment, but our
  schematics will not. (The user will be expected to pick them out
  themselves, from other sources, before using our software.

  .. note::
    Is it worth building in a library of popular repeats, so that the
    user can choose one without needing to go find one of their own?

* A *pattern* is the full set of instructions for how to knit a
  garment. In addition to the schematic for a garment, a pattern will
  contain the row-by-row instructions for knitting the garment
  (expressed in terms of stitches, rows, or inches/cm, as appropriate).


