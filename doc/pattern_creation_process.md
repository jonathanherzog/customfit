# Pattern creation overview

## Models

There are 5 models involved in the pattern creation process. Data flows through 
them in this order:

	Design ->
	PatternSpec ->
	IndividualGarmentParameters ->
	IndividualPiecedSchematic ->
	IndividualPattern


### Design

Basic parameters of a sweater type: neckline style and depth, sleeve length and 
shape, etc.

### PatternSpec


A PatternSpec (PS) holds the original inputs to the engine. That is, it holds
both the 'design' aspects of the pattern to be made, plus all the user-specific
inputs and customizations. It is created from a Body, a Swatch, and either:

* A Design, or
* A set of choices entered into the UI by the user.

It is hard to express the purpose of the PS other than 'all of the inputs to 
later steps, held in on model for convenience.' 

Because a PatternSpec and a Design overlap so much in their content, they
have many of the same fields. But suppose that we create a PatternSpec from a 
design. As we do so, should we copy values from these fields in Design into the
analagous fields in PatternSpec? The DRY and one-source-of-truth principles 
might tell is not to, and that a blank value in the PatternSpec should cause
the engine to examine the source Design for the value. But there's a non-obvious
workflow requirement that sometimes contradicts this. Designers often change 
their Designs after Patterns have been made from them. If we've adopted
the one-source-of-truth approach, then changes in the Design would automatically
propogate out to existing patterns. Sometimes, this is the right thing:
If the designer fixes a bug in a Design- specific template, for example, the 
bug-fix *should* propogate out to existing patterns. Other changes should not. 
If the designer changes the sleeve-length of the design, for example, this 
change should *not* cause existing patterns to change or users get upset. 
Thus, the placement of fields into {Design, PatternSpec, or both}, and whether
to copy values from Design to PatternSpec, is not an obvious choice.  
(For more details, see comments in designs.models.DesignBase.)

### IndividualGarmentParameters

The PS is used to create an IndividualGarmentParameters (IGP): a
single model holding all of the 'interesting' dimensions of the finished
garment, in inches. That is, design-relevant descriptors such as 'elbow
sleeve' have been turned into an inch-denominated 'sleeve length'. More
generally, all garment-descriptors that can be turned into inches are, in
fact, turned into inch-lengths. (Other descriptors, such as stitches to use
and neck-shapes remain in their original form. Usually the IGP merely
passes requests for these descriptors on to the PS from which it was made.)
Note that the IGP is parsimonious with truth-- it holds all the descriptors
for the garment in a compact and normalized form. (That is, no descriptors
are repeated.) This is as opposed to Schematic models, below.

Also note that the dimensions of the IGP will often *not* be exactly those
in the underlying Body instance. The IGP will compute its values using the
Body instance, a set of 'eases', and a collection of checks and adjustments
called our 'secret sauce'. Thus, the silhouette of the IGP might *not* be
the silhouette of the PS. More on this below.

The user has a chance to 'tweak' the fit of the garment by changing the
values in the IGP. Those changes are saved back to the same IGP. That
model is versioned, however, so that we can go back and see the tweaks made
by the user if necessary. (Also note that the tweak step must undo a step of
the secret sauce before showing values to the user. The secret sauce will
add length to the garment in the case of 'negative ease': the garment has
a smaller circumference than the underlying Body. This is often desirable
and flattering, and knitted fabric can stretch to accomodate. But the
secret sauce must make the garment longer to match the desired 'as-worn'
lengths. When showing the IGP to the user, therefore, the site must
'unadjust' for negative ease to get the original desired as-worn lengths
back, and then re-adjust for negative ease after the user tweaks the as-worn
values.)

Note that the user might attempt to 'tweak' the garment into a new
silhouette, one which may or may not be the one of the PS. More on this
below.


### IndividualPiecedSchematic


The IGP is turned into an IndividualPiecedSchematic (IPS) instance, which is
merely a container for Schematic instances that represent indivdual pieces
(CardiganFrontSchematic, SleeveSchematic, etc.) These piece-schematic models
hold all the descriptors relevant to a given piece. Although these values
are mostly copied verbatim from the IGP, the IPS is a verbose, de-normalized
representation of the garment. A given piece of truth may be repeated many
times. ('Armpit height', for example, will we present on both the front-piece
and the back-piece.) The purpose of the IPS is to make it easy for the
engine to compute pieces by gathering in one place the parameters needed for
each piece. (It is arguable that the IPS and other Schematic models are
unneeded and probably unwise. This is probably true, but we're stuck with
them for now.)

Because the IPS is mostly a copy of values from the IGP, it will be the
case that the garment described by the IPS will have the same silhouette
as that described by the IGP. However, that does not mean that every *piece*
will have this silhouette. If the original design specified 'back waist
shaping only' (which is only valid for hourglass designs) then the back
piece will have an hourglass shape but the front piece will have no shaping.
More on this below.


Note 1: The IPS currently represents a single constuction: 'set-in sleeve'. If/when
we want to support other constructions, we would be able to use the IGP without change
but need to write now IPS models for those new constructions.

Note 2: The above description describes only those PieceSchematic instances 
that are associated with an IndividualPiecedSchematic instance/container. This
describes most instances-- but not all. Cardigan schematics, for example, have a 
'double_into_pullover' method (used during pattern-genereation, below) which 
will  generate a temporary SweaterFront/VestFront schematic that is *not* 
associated with an IndividualPiecedSchematic.


### IndividualPattern

The IPS is then used to compute an IndividualPattern, which is itself a
collection of piece-models. These piece models hold the number that will go 
into the actual patterntext. Note that the dimensions of the piece might
not be the same as that of the underlying schematic. This is because
the piece must respect the gauge of the underlying swatch and must respect
the stitch-repeat counts of the swatch and the stitches in the PS.
Therefore, the shape of any given piece might not match the shape of the
underlying schematic. More on this, below.

Also, the IndivdiualPattern keeps track of facts about its user-workflow state:
whether it has been paid for ('approved'), whether it has been archived, etc.

An IndividualPattern will not link to its pieces directly, but through an 
IndividualPatternPieces model. This is so that it is possible to 'redo' a pattern 
(see below). In that case, it will hold its current (redone) pieces in one 
IndividualPatternPieces, but the original pieces in another IndividualPatternPieces 
for reference.


## Redoing patterns

We allow users to 'redo' a pattern a certain number of times (currently once) under 
certain conditions (currently: within a certain window of time after making the pattern).
This process starts with the creation of a Redo instance, which holds a small-subset of the
fields of a PatternSpec. Then an IGP is made from the Redo (using values from the original
PatternSpec when needed and not present in the Redo), and the pattern-creation process
continues as before. However, instead of making a new IndividualPattern, the original 
IndividualPattern is modified. The original IndividualPatternPieces is moved from 
`pieces` to `original_pieces` and the new pieces are inserted into `pieces`.

## Valid transitions

As mentioned, the shape of a garment/piece might change several times
during the process described above. The valid/legal transitons are as follows.
(Note that these do not describe the views/pages that allow the user to walk 
through these transitions, but only the transitions themselves. Generally,
the transitions are implemented as model-methods and the pages/views call these
methods on behalf of the user.)

* Source to PS:

    * Phase 2: Designs have a shape, and the PS must
        copy that shape. If the user uses the custom-design form, they generate
        an PS directly and therefore set the PS's shape directly.

    * Phase 3: Designs have a set of allowed shapes,
    * Phase 3: Designs have a set of allowed shapes,
        and the PS must be given a shape in the set. If the user uses the
        custom-design form, they generate a 'custom-made' design and
        set its shape. The PS copies that shape.

* PS to IGP: Hourglass PSs can generate hourglass IGPs or straight IGPs. No
    other transitions are allowed. More explicitly, the set of valid
    tranformations that the secret sauce should automatically make are:

    | Design    | Front piece | Back piece |
    | --------  | ----------- | ---------- |
    | Hourglass | Hourglass   | Hourglass  |
    | Hourglass | Straight    | Hourglass  |
    | Hourglass | Straight    | Straight   |
    | Straight  | Straight    | Straight   |
    | A-line    | A-line      | A-line     |
    | Tapered   | Tapered     | Tapered    |

    (Yes, this table includes A-line and Tapered, but that's for phase 3.)


* Tweaking IGP: The 'phase 3' plan is still up in the air, so let's focus on
    phase 2. In this phase, there are two possible scenarios

    * Scenario 1 (threshold goal):

        * If the PS was for 'hourglass', then the user must be able to tweak
        waist, bust, and hip separately-- even if the IGP turned out straight.
        The user can tweak them into an hourglass or straight but nothing else.
        (The waist-circ cannot be bigger than hip or bust, for example.)

        * If the PS is straight then the user sees only fields for two torso
        width, front and back, and the form will copy that into the
        waist/hip/bust widths.

    * Scenario 2 (stretch goal): Same as scenario 1, but the user should be
        able to toggle between the 'full hourglass' form and 'straight' form
        when tweaking an IGP derived from an 'hourglass' PS.

    In either case, the valid results depend on the silhouette of the PS:

    | Design    | Front piece | Back piece |
    | --------  | ----------- | ---------- |
    | Hourglass | Hourglass   | Hourglass  |
    | Hourglass | Straight    | Hourglass  |
    | Hourglass | Straight    | Straight   |
    | Straight  | Straight    | Straight   |
    | A-line    | A-line      | A-line     |
    | A-line    | Straight    | Straight   |
    | Tapered   | Tapered     | Tapered    |
    | Tapered   | Straight    | Straight   |

    (Yes, this table includes A-line and Tapered, but that's for phase 3.)


* IGP to IPS: the shape of the front/back should not change.

    * IGP describes hourglass piece -> hourglass schematic
    * IGP describes straight piece -> straight schematic
    * IGP describes A-line piece -> A-line schematic
    * IGP describes tapered piece -> tapered schematic

* IPS to IndivdiualPatternPieces: Any schematic can result in a straight
    piece, but no other transitions are allows

    * Hourglass schematic -> Hourglass or straight piece
    * A-line schematic -> A-line or straight piece
    * Tapered schematic -> Tapered or straight piece
    * Straight schematic -> Straight piece.

* IndivdiualPatternPieces to IndivdiualPattern

* IndividualPattern to Redo

* Redo to IGP

* IGP to IPS

* IPS to IndivdualPatternPieces

* The new IndivdualPatternPieces is added to the original IndivdualPattern under `pieces`,
and the original pieces moved to `original_pieces`

## Views

There are 5 views that users may encounter in pattern creation:

### Personalize design page

_Requires_: Design    
_Produces_: PatternSpec and (if possible) IGP    
_Redirects on valid post to_: Add Missing, Tweak or Summary    

This is used for all Designs.

It has two action buttons, allowing users to go to Tweak or Summary (their choice). It will route through Body measurement addition instead if it is missing measurements.

_Optional_ (if not used, custom design must be used)

### Custom design page

_Requires_: Nothing    
_Produces_: PatternSpec and (if possible) IGP (does _not_ produce a Design)
_Redirects on valid post to_: Add Missing, Tweak or Summary   

This is used by users who would like to enter all their design parameters from scratch.

It has two action buttons, allowing users to go to Tweak or Summary (their choice). It will route through Body measurement addition instead if it is missing measurements.

The custom design logic around missing measurements and validation is complex (see below).

_Optional_ (if not used, personalize design must be used)

### Redo Pattern page

### Add missing measurements page

_Requires_: Body, PatternSpec    
_Produces_: Updated Body _or_ PatternSpec instance (not both), IGP    
_Redirects on valid post to_: Tweak or Summary, as requested by user on prior page in workflow    

If the body does not have all of the _extra_ measurements that it needs to support a garment with the desired design choices, the user is given a choice between:
* continue with defaults; or
* add missing measurements.

(We can't produce IGPs until we have those measurements, so this page takes PatternSpec rather than IGP.)

We will not use this page to solicit hourglass measurements (there are too many; this page is intended for adding just one or two quick things). Hourglass measurements are enforced as all-or-nothing by the main measurement entry pages (BodyCreateView, BodyUpdateView, BodyCopyView, and their LYS equivalents). PersonalizeClassic and Custom are responsible for ensuring that users may not select both an hourglass silhouette and a non-hourglass body.

_Optional_ (Users will only be routed through this page if we cannot make their pattern otherwise; this page is not linked or otherwise exposed from anywhere in the site)

### Tweak page

_Requires_: IGP    
_Produces_: IGP    
_Redirects on valid post to_: Summary & payment    

This is used by users who would like to alter CF's fit recommendations before producing a pattern.

We will not let users customize an IPS because we believe that significant customer service load has come from customers who have gone through multiple rounds of customization and are unhappy with the result.

Customers who would like to re-tweak will be presented with the _initial_ IGP again.

_Optional_ (users may skip this page entirely, going straight from design to payment, or may consult it and not make changes)

### Summary & payment page

_Requires_: IGP    
_Produces_: IPS, Pattern (approved=False)    
_Redirects on valid post to_: Paypal (if paying with cash) or pattern page (if paying with credits/maker status)    

This page should produce a pattern _before_ taking anyone's money. We don't present that pattern to users, but we do want to confirm that it's doable. We will mark the pattern as approved when we receive payment.

_Required_

## Bodies

### Measurement categories
Body measurements fall into 3 categories:
* Essentials;
* Hourglass;
* Extras.

_Essential_ measurements are required for all sweater silhouettes and body genders. (Examples: full bust circumference, full sleeve length, medium hip length.)

_Hourglass_ measurements are required for all hourglass silhouettes, but none are required for any non-hourglass silhouettes. In particular, we don't generally anticipate people using them for men's or children's sweaters. (Examples: upper torso circ, waist circ.)

_Extras_ are measurements that are not required for any silhouette, but which provide additional flexibility, and may be required to make particular patterns as originally designed. (Examples: elbow sleeve length, tunic length, cross-chest.)

### User experience
Users are only _required_ to enter the essentials in creating a measurement set, to reduce the burden on them.

When users attempt to make a sweater with a body that is missing _extras_ expected by that pattern, they are given a choice of:
* add missing measurements (usually only about 2); or
* use defaults.

If users add missing measurements, we will update the measurement set accordingly and proceed with pattern validation and sale. If users use defaults, the PatternSpec will reflect default hem and/or sleeve lengths, and not the hem and/or sleeve lengths in the Design.

We do not allow users to make hourglass sweaters with bodies that are missing hourglass measurements, because of the large number of measurements they would need to enter.

Therefore, the drop-down menu on a design personalization page offers
* all bodies (non-hourglass-silhouette sweaters)
* only bodies with complete hourglass measurements (hourglass-silhouette sweaters)

The drop-down menu on the custom design page offers:
* all bodies (on pageload)
* only bodies with hourglass measurements (when an hourglass silhouette is selected)
* only non-hourglass silhouette options (when a body missing hourglass measurements is selected)
It will therefore erase the user's body choice if they select an incompatible silhouette, or vice versa.

## Validation

### Special concerns for custom designs
On the personalize design page, we can guarantee three important things:
* Bodies missing hourglass measurements are not available for hourglass designs.
* We haven't done anything super dumb with Design creation (e.g. we didn't specify five-inch sleeve edging for a short-sleeved sweater).
* We have all the information we need to validate the PatternSpec as soon as users submit the form.

For the custom design page, none of these guarantees holds:
* We have no foreknowledge of the user's silhouette, so all bodies are available.
* Users may select design elements that are internally incompatible.
* We may be missing body measurements, so we may not be able to tell if the design and the measurements together yield a valid pattern (e.g. if the design's edging is longer than the body's sleeve length will allow).

Therefore there are three places we need to perform validation:
* on the custom design page (through JavaScript), to prevent choices that we know in advance will be invalid;
* on the custom design page (after form submit), via the usual form validation;
* after the add missing page (if users have added missing measurements), to ensure that they have not introduced an incompatibility with their design choices.

The possible cases are enumerated below.

__On the custom design page__

| Body            | Silhouette    | Result                          |
| ----------------|---------------|---------------------------------|
| _has hourglass and ..._ | | |
| has any needed extras | any | proceed to form validation and then tweak/pay |
| is missing needed extras | any | proceed to form validation and then add missing |
| _does not have hourglass, and..._ | | |
| has any needed extras | hourglass | disallowed by JS on custom page |
| has any needed extras | non-hourglass | proceed to form validation and then tweak/pay |
| is missing needed extras | hourglass | disallowed by JS on custom page |
| is missing needed extras | non-hourglass | proceed to form validation and then add missing |

## Special concerns for missing measurements

When users add missing measurements (in either the personalize or the custom design process), there are three things that need to be validated:

* The body
    * _Example_: armpit-to-elbow-sleeve must be longer than armpit-to-short-sleeve.
    * This validation is performed on Body.
    * Bodies are valid before entering the custom design process (or they would not have been saved in the database in the first place), but they must be revalidated iff missing measurements are added.
* The design
    * _Example_: a garment with an hourglass fit must also have an hourglass  silhouette
    * This validation is performed on PatternSpec.
* The body/design combination
    * _Example:_ the body's sleeve length must be sufficient to accommodate the sleeve edging height
    * This validation is performed on IGP.

Here are the validation steps that each view is responsible for performing, and their outcomes:

* __Personalize__
    * Assumes Body is already valid (otherwise it would not have been in the database)
    * Validates PatternSpec
    * If body has all needed measurements: creates and validates IGP
    * If not: proceeds to AddMissing
* __Custom__
    * Assumes Body is already valid (otherwise it would not have been in the database)
    * Validates PatternSpec
    * If body has all needed measurements: creates and validates IGP
    * If not: proceeds to AddMissing
* __AddMissing__
    * If measurements are added:
        * updates and validates Body
        * leaves PatternSpec alone (it was guaranteed valid by previous steps)
    * If defaults are used:
        * updates and validates PatternSpec
        * leaves Body alone (it was guaranteed valid by previous steps)
    * Creates and validates IGP
        * On success: proceeds forward to tweak or pay
        * On failure: proceeds back to personalize or custom, with informative error
* __Tweak__
    * Has no responsibility for Body or PatternSpec
    * Validates IGP

The possible options are:
* _Body does not validate_: return user to AddMissing page, with errors
* _Body validates, body/design combo does not_: add new measurements to Body; return user to CustomDesign page, with errors
* _Both validate_: hooray! Continue to tweak or pay, as desired.

