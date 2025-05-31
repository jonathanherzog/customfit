# Pricing

30 December, 2015

## Summary:

Do not change any of the 'price' fields/methods in `Design`,
`PatternSpec`, `Pattern` or `Transaction` before reading this and
understanding the implications of your change.

## Introduction

Our handing of 'prices' is an incoherent mess. It's limping along
adequately, though, and the 'real' fix to the situation is to switch
to an external e-commerce package (such as django-oscar, which looks
awesome). Hence, we're going to let the current situation continue for
time being, until we get enough energy and time to rip it out and
completely replace the `payments` app, the `offers` app, the `credits` 
app, and large parts of the `design_wizard` app. In the meantime, we 
document the current situation here so that we can keep ourselves from 
breaking things further.


## History

To understand why things are the way they are, it helps to understand
some of our previous design mistakes. Those mistakes have been fixed,
but their effects linger on in the database.

When we originally created the site, we did not have 'Designer'
designs. We thought that there would be a site-wide blanket
per-pattern price, and so did not really assign a 'price' concept or
field to any particular model. But then a number of things changed.

* We wanted to give out refunds and discounts, and so we created
  'credits': small codes worth a given amount of money.

* We also wanted to let knitters and yarn stores buy in bulk, and so
  we created 'credits': small codes worth one pattern purchase. Note
  the name-collision with dollar-valued 'credits' above. We've stopped
  giving out/selling the dollar-valued credits, though, and have
  defined credit-codes to be good-for-one-pattern. (Note: users have 
  a 'credit bank' to store their credits, and we mostly deposit credits 
  directly into these banks rather than providing codes. But the codes 
  still exist, and users are free to make crredit-codes using the credits 
  in their bank.)

* In response to consumer demand, we switched our primary offering
  from design-your-own to built-in 'designer' designs. We also decided
  that these designs could be more expensive than the default
  site-wide price. How would this interact with good-for-one-pattern
  credits? We decided that 'good for one pattern' meant 'good for one
  pattern' regardless of price.


So, one big mistake was to not foresee how complex we would make our
payment & pricing mechanisms. We also made a few errors when designing
our Django models.

* Originally, the `customfit_app` app had a `Design` model and an
  `IndividualDesign` model. The intent was that the `Design` model
  would represent pre-designed designs for users that didn't already
  know what they wanted and so stored all of the 'design' aspects of a
  given sweater: sleeve length, neckline style, etc. The
  `IndividualDesign` model, on the other hand, was mean to represent
  the result of a user's build-your-own process: everything in Design
  plus the swatch, the body, etc.

  We originally thought that users would mostly be using the
  build-your-own process, and that very few would be using pre-canned
  `Designs`. Thus we assumed that `Designs` would remain simple and
  that complexity would be added to `IndividualDesign`, and made a
  serious design mistake: we had `IndividualDesign` inherit from
  `Design` using multi-table inheritance. Why was this a mistake?
  Because we were exactly wrong: users loved the pre-designed designs
  and very few went the build-your-own route. This meant we added
  complexity to `Design` *and `IndividualDesign` inherited that
  complexity*-- even though most of it was irrelevant.

  We have since fixed this mistake. `Designs` live in the `design` app
  and `IndividualDesign` has been replaced with
  `PatternSpec`. However, there was a long time in which
  `IndividualDesigns` had to handle complexity that really belonged to
  `Designs`, and part of that complexity was pricing. When we wanted
  to add a 'price' field to `Designs` for 'Designer' designs (see
  above), `IndividualDesign` inherited it as well.

* Having said all that about engine inputs, let's look at the engine's
  output: the `Pattern` model. Because we want to guarantee that the
  user gets a `Pattern` when they pay for one, we actually generate
  the `Pattern` before the user pays for it and only let them see it
  once it's purchased. To make this easy, we gave `Pattern` a 'price'
  method--- two, actually--- so that the review-and-pay views would be
  easy to write. This price is then sent to paypal, and paypal sends a
  signa back. If that signal is 'yup, paid', we create a `Transaction`
  instance for that `Pattern`, and the existence of that `Transaction`
  allows the user to see the pattern. So, why two methods? The method
  `price_float` produces a python float, which is convenient when
  writing python code. But we don't want to show users a price like
  `9.435875234532740`, so we created a `price_string` field that
  enforces that we display exactly two decimal places. The catch is
  that, since this is the price the user sees, this is also the price
  that we send to paypal. Thus the actual amount charged could be
  different than the price we use elsewhere in the code. Does this
  matter? If doing equality tests, yes. But if not, the prices will
  differ by one cent, at most, and we don't care that much.

## Current Intent 


Okay, so there's all that broken-ness above. What is our current
intent?

### Price

* There should be a site-wide default price.

* Admins can set a different price on specific `Design` instances, or
leave it blank.

* The price of a pattern should depend on where that pattern came from:

    * If the pattern was derived from a `Design` instance and that
      instance had a price set on it, the price of the pattern should
      be the price in the `Design` instance.

    * Otherwise, the price of the pattern should be the current
      site-wide default.

* Both the site-wide default and the price in the `Design` instance
  can change at any time.

### Payment

* Independent of price, some users (alpha testers, Maker Plus
  subscribers, etc.) get patterns for free. They should be able to get
  any pattern of any price without paying.

* If a user does not get free patterns but does have credits in their
credit bank, they can redeem the credit to get the pattern for free.

* All other users must pay the price of the pattern. If the prices
  change while the user is generating the pattern, it should be the
  price displayed to the user in the 'review and pay' screen.

* If the user has a valid, unused credit-code, they can enter that
  at payment time to get the pattern for free directly (as opposed
  to depositing it into their bank first).

### Record Keeping

* Every pattern purchase should have an associated `Transaction`
  instance showing the amount actually paid. (Note: The django-paypal
  package also generates an `IPN` instance with a lot more
  information, but we haven't really incorporated that into our
  thinking yet. Alas, neither the `Transaction` model nor the `IPN`
  model record the discount applied, only the gross payment. Also,
  there should be a `Transaction` instance for free patterns / credit
  purchases, but there will be no `IPN` instance).

* Since we now allow users to use credits in their bank to credit-codes,
  and to give those codes away, we have started keeping track of which 
  user created a credit code and which user redeemed it (either for a 
  pattern, or deposited into their bank).

## Current design

Well, 'design' might be a grandiose term for what we have:

* `Design` instances have a `price` field, which can be set by admins
   or it can be left blank (`None`).

* `PatternSpec` instances also have a `price` field. This price will
   be set to the price of the underlying `Design` by the
   `PersonalizeDesign` view, but this is implicit. (The view uses some
   Django magic to simply copy over all fields in common.) Also,
   remember that `Design.price` might be `None`. Lastly, the
   build-your-own form (`CustomDesignCreateView`) leaves
   `PatternSpec.price` blank anyway.

* We deal with this complexity in `Pattern`. `Pattern.price_string` is
  a formatting wrapper around
  `Pattern.price_float`. `Pattern.price_float`, in turn, applied a
  very simple algorithm. All `Pattern` instances must come from (and
  link to) an underlying `PatternSpec` instance. If that `PatternSpec`
  instance has a price, use that. Otherwise, apply the site-wide
  default.

* The review-and-pay view, fortunately, both displays the price to the
  user and provides the form that will be sent to paypal to execute
  payment. This means that the price sent to paypal will always be the
  price displayed. Or rather, back-end changes to the `Design` price
  or the site-wide default will not produce an inconsistency between
  the displayed price and the price sent to paypal. It does mean,
  however, that a dishonest user has a chance to *change* the price
  in the form before sending it on to paypal.

* When paypal sends a 'payment successful' signal back to us, we
  create a `Transaction` instance. Although paypal tells us how much
  they charged the user, we do not actually compare that against the
  pattern's price. (Perhaps we should, but the pattern's price is
  dynamically computed from settings that might change. If we do want
  to make this comparison, we'd need to worry about how back-end
  changes might change a pattern's apparent price after the user paid
  for it but before we do this post-purchase price-comparison.)

* When the user gets the pattern for free, or uses a credit, we also
  create a `Transaction` instance (for the amount `0.00`). This does
  not go through PayPal, but the Transaction instance will keep track
  of *why* the pattern was free (for record-keeping purposes).

## Future development


There's a lot of badness here:

* It's not clear what the 'source of truth' is for a Pattern's
price. Is it the `price` field in the `Design`? The `PatternSpec`?
Should `PatternSpec` even have a `price` field?

* Right now, those two values will be the same, but that's very
  implicit in the `PersonalizeDesign` view. I think we've gotten lucky
  so far, and that this invariant should be much clearer.

* Why are we dealing with the pricing complexity in `Pattern`? But on
the other hand, is there a better place to put it?

* It's not clear that we've thought out which values/methods *should*
  change when the modify the site-wide default price or the price in
  particular `Design`.

* We really should check that the amount of money received from paypal
  is actually the price of the pattern (before fees and taxes, of
  course).

* Our `Transaction` model is far too simple. Right now, we can look at
  a `Transaction` and determine wether it went to Paypal and how much
  we charged. But we don't know how much of a discount we
  applied. 


So what to do? For the moment, this system works adequately well and
it's less of a pain-point than other things. But when we finally get
around to fixing it, we can either:

* Patch our home-grown system and make it more coherent/robust, or

* Switch to a 'real' e-commerce package like django-oscar.

I have a strong preference for the later, and vote that our (barely)
working system should not receive further time/effort until we're
willing to do the Right Thing. Of course, that assumes that we really
can leave this so-called system alone until then, or we don't make
changes to any one of these models without thinking through the
implications on the entire system....
