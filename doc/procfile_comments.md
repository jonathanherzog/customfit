Unfortunately, Heroku doesn't have a standard, supported notation for comments in their Procfiles,
so let's collect comments on our Procfile here. If you open our procfile, you'll see that we have
two process types: one web, one celery-worker. Some notes on each:

Web:

*  We artifically set the timeout to 20 seconds. Why? This is to avoid a problem with long-lived jobs. The
    default time-out for both gunicorn and Heroku is 30 seconds, but Heroku's timer starts first. This means
    that a long-lived job / infinite loop would be killed by Heroku and not gunicorn, and we don't get
    as much useful information from Heroku's logging as we would from gunicorn's logging. Thus, we
    set gunicorn's timeout to 20 seconds to make it time-out first, ensuring that we get (via Sentry)
    a more useful message.

* We set the internal concurrency of gunicorn to that of an environment variable, $WEB_CONCURRENCY. This
    allows us to change the concurrency without pushing code. Yes, Heroku will re-start the dynos when we
    change an environment variable, so this will actually take effect. At the moment, though, this is pretty
    moot: the end-user experience is bottlenecked by DOM processing, not our server's response time. And
    we're processing something like 1 to 4 pages per *minute*, so requests are not spending much time
    waiting for workers. (And we're no where *near* the resource limits of a Heroku machine.) More concurrency
    won't affect the end-user experience as much as DOM-optimization for a long time.

Worker:

* The `-B` flag is a gotcha waiting to happen. From the docs:

        Also run the celery beat periodic task scheduler.
        Please note that there must only be one instance of
        this service.

    On the one hand, we *want* this: this is what allows celery to to cron-jobs like clearing caches and
    distributing credits. But on the other hand, it sounds like we will run into problems if we ever
    start more than one dyno of this type. This means that if/when we get big enough to need more than
    one celery worker, we will need to define a process-type that is celery *without* this flag.

* I have to confess what exactly the `--loglevel=INFO` flag does. Or rather, I'm not sure if celery's logging
    is controlled by the `LOGGING` dict in the settings files.