# Before releasing under open source license

- Check static assets for third-party IP (see static_asset_audit.md in this directory)
    - fonts
    - Javascript
    - images
    - CYCA charts
    - What else?
- Remove all pictures of Amy
- Decide where the open-source repo will live
- Documentation
    - Update existing documentation to be accurate
    - Add missing documentation

# Before code can be usable

- Squash migrations and remove unneeded applications
    - First we need to look through migrations to see if there are any fixtures in there
- Get selenium tests working
- Generate fixtures from production DB of 'public' models (e.g., stiches)
- We need to know how the community will want to deploy this and remove any unneeded code
    - Heroku and its addons (postgres, memcache, redist, etc.)
    - Celery
    - Static assets in S3 buckets
    - Email
    - Static error page
    - What else? Scour the settings files for depoloyment-related settings
- What security will the site need? DDoS protection?

# Longer-term code quality issues / areas of sadness

- The static/ directory has become a junk drawer. How many things in it are actually being used?
- Update dependencies in requirements.txt.
- Switch to pytest, if the community wants it
    - While you're at it, a lot of my tests could be improved
        - Breaking large compound tests into smaller ones
        - REfactoring the ones that loop through test vectors via @pytest.mark.perameterize
- The object relationships are needlessly complext. This is for historical reasons-- we used to need two versions of
  everything: one for individual users and one for LYS users. So we would often have a 'base' model, with 'individual'
  and 'lys' submodels. We removed the LYS users, though, and the 'LYS' submodels. But we really should find some tool to
  graph class relationships, find classes with single subclass, and unify.
- The core workflow still reflects its origin as a commercial site.
    - Most immediately, we need to find any remove an vestiges of transactions, credits, subscriptions, etc.
        - This includes the various kinds of users-- staff, LYS, Makers, Maker-plus, alpha testers, LYS beta-testers,
          anonymous users, friends and family
    - But more generally, the core workflow has steps for tweaking, approving, and redoing. It's not clear that the
- The tests sometimes fail when you run them as the entire suite. Those same tests will pass, though, when run in
  isolation. This means that CircleCI deployments will sometimes (often?) fail the first time through, but will then
  succeed when you try re-running the job. It adds a lot of friction and grit to the process, but hasn’t made it high
  enough on my priority queue to fix. (I suspect the problem is that some test is leaking side-effects into the test DB
  when you run them in parallel, and that’ll be a PITA to isolate.)
- It can take more than 30 seconds to generate a PDF, which means that Heroku will kill the job and the user is unhappy.
  Most of your 500 errors will come from this. We tried to deal with this through speculative execution and caching:
    - We generate the actual patterntext HTML and cache it while the user is looking at the final numbers, and
    - We generate the PDF and cache it when the user is looking at the pattern HTML in their browser.

  This worked adequately, barely, for normal uses. But it fails spectacularly when the user goes through any other
  workflow than the pattern-generation one. In particular, it can fail when users try to download PDFs directly from
  their home page-- which everyone did when we told them the site was going down.

  Ultimately, I think that the Right Solution here is to move to polling-- instead of holding the connection open while
  we try to generate the PDF in 30 seconds, we send the user to a ‘generating pattern’ page and send the actual
  PDF-generation job to a heroku worker. The ‘generating pattern’ page polls Customfit periodically to see if the PDF is
  finished and fetches it / serves it to the user when it is.

  I (Jon) initially avoided this route because (1) I’m bad at Javascript, and (2) wanted to keep everything in the
  backend where I could diagnose problems through logging and instrumenting the code. As soon as we move polling to the
  front-end, I start to worry about sending users into infinite loops or javascript errors that we won’t see until Kate
  gets the tickets. (And then we won’t be able to diagnose them because users are bad at reporting the circumstances
  that led to the error.) But speculation and caching don’t really solve the problem, and I think there’s no choice but
  to move to polling.
- Graded patterns are still very new, and haven’t been battle-tested yet. In particular, I am worried about the
  design-specific templates in the database. We use custom template tags to lay out stitch-counts and inch/cm lengths in
  the patterntext, and we also use template logic to decide whether to include bits of patterntext based on whether or
  not a pattern e.g. had double-darts in the waist. This broke when we moved to graded patterns, and we needed templates
  to gracefully handle getting either individual numbers of lists of numbers. In an individual pattern, the number of
  waist double darts could be a number like 3 or ‘None’ if the pattern didn’t use double-darts. It’s easy to write an
  ‘if’ statement that branched properly for that. But now we come along later and ask the template to handle getting 3
  or None for individuals, or [3,3,4,4,5] or [None, None, None, None, None] for graded patterns. But note that in
  python, both of those lists evaluate to True in a branch. So the ‘if’ statement in the template language starts doing
  the wrong thing by going down the ‘if double dart’ branch for all graded patterns.

  To solve this, you need to go through all templates and modify the branches. You can no longer branch on the same
  variable you’re going to use for the patterntext

  ```
  {% if double_dart_counts %} 
  {{ double_dart_counts | count_fmt }} 
  {% endif %}
  ```
  Instead, you need to branch on a boolean:

  ```
  {% if double_dart_counts.any %} 
  {{ double_dart_counts | count_fmt }} 
  {% endif %}
  ```
  Or:
  ```
  {% if any_double_dart_counts %} 
  {{ double_dart_counts | count_fmt }} 
  {% endif %}
  ```
  (where any_double_dart_counts is computed by the view and added to the context.) I’m pretty sure we did this for all
  the ‘built in’ templates in the codebase, but I suspect we did not catch all

- We never really were able to leverage any sort of analytics on the Django side. Also, our usability is crap and always
  has been. Sometimes, I suspect these two issues are related.
- A lot of the sweater models mix 'inch' fields and 'stitch/row' fields, and I always wanted to refactor them to use
  just 'stitch/row' fields.
- From what I remember, we just stuffed static assets into buckets willy-nilly. Not only our own statics assets, but
  user-uploads too. This made it impossible to look at a bucket a know why a file was there or who it belonged to. We
  should actually plan out the directory structure of static assets in buckets/storage and migrate the code to that.
- The error page (in static/) is a hard-coded static page, intended to live in some bucket somehere. This should be
  updated to reflect the new deployment of the site.

# Before adding another another kind of garment

* Pull waist/sleeve/etc. templates out of stitch model into Sweaters app
    * Waist hem
    * sleeve hem
    * armhole hem
    * buttonband hem
    * buttonband veeneck
    * armhole
    * neckline
    * extra finishing instructions?







    
