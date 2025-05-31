
===============================
Site internals: the Big Picture
===============================

In this section, we try to provide the Big Picture for this site: what
the moving pieces are, how they fit together, etc. Although this site
is build on Django and uses the model-view-template paradigm of that
framework, each of these three components can get very complex:

* The core models of this site can be broken into two parts: those
  that describe user inputs (bodies, swatches, designs, etc) and those
  which describe sweaters, patterns, and their components
  (sweaterbacks, sleeves, etc.) The models in the first category are
  not super-complex, but it still helps to have the big picture
  explained. The models in the second category, however, can get a
  little hairy. They tend to be variations on the same, core
  underlying parameters and logic, and so are defined using a
  somewhat-complex object inheritance heirarchy.

  These two categories are very different, and so we will break them
  out into individual sections below.


* On the other hand, building the instruction-text for a given piece
  is best modelled as picking lots of sub-instruction chunks and
  concatenating them together. The chunks picked out can vary a lot
  from sweaterback to sweaterback, for example, and both a sweaterback
  and a sweaterfront might use the same chunk. Therefore, the
  templates for patterntexts are small and very specific-- but may not
  be tied to any one type of piece.

* Given this, the views needed to generate patterntext for a given
  piece can be pretty complicated. However, most of the work is given
  over to renderers: view-like functions which take a model and return
  the patterntext. (As opposed to a view, though, they return a String
  and not a Response.) These functions pick out the necessary
  templates, render them, and concatenate the results
  together. However, the logic for picking out the necessary templates
  can get a little complex. 



--------------------
User-workflow models
--------------------


"""""""""""""""""""""""""
BodyMeasurements
"""""""""""""""""""""""""

The :mod:`body_measurements` model holds the dimensions of a
body. It's pretty striaightforward: a number of circumferences (hips,
waist, bicep, wrist, etc.) and a number of lengths (waist to armpit,
waist to hips, shoulder to wrist, etc.).




----------------------
Pattern-component models
----------------------


See pattern_creation_process.md

---------
Templates
---------


text goes here

-----
Views
-----

See pattern_creation_process.md
