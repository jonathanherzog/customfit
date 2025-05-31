# Celery

We use Celery for scheduling asynchronous tasks. 
[Celery docs](http://docs.celeryproject.org/)

Rationale: long-running tasks tie up our main dyno and sometimes make it
overload/restart. We need to shuffle these off to the background so our
dyno is available and responsive to the users.

## Celery tasks
### Currently
* sending mail (via django-celery-email)

### Future work?
* picture uploading (via `django-queued-storage` or something)
* PDF conversion

## Yak shaving on localhost
You will need to install some stuff manually (it's not available via pip). 
I use [homebrew](http://brew.sh/).  You might have macports or fink or
something.

Order matters in these steps.

* `brew install memcached`

* `brew install libmemcached`

* `LIBMEMCACHED=/opt/local pip install pylibmc`

* You will need to install redis-server: [see the Quickstart](http://redis.io/topics/quickstart) or use 
    `brew install redis`

* `pip install -r requirements.txt`.

* `python manage.py migrate djcelery`

* Then start the redis server and the celery worker: `redis-server &`

* `python src/manage.py celery worker --loglevel=info &` (If you haven't run celery in a 
    while, you will probably want to purge its queue so it doesn't run through every background task you might 
    have created; `python src/manage.py celery worker --loglevel=info --purge &`

__Now__ you may start the Django runserver.

## Running on Heroku

* Requires memcachier (currently provisioned at developer level on testing, staging, & production)

* Requires redis_to_go (currently provisioned at nano level on testing & staging, and mini on production)

* Make sure the celery worker is turned on (check the dashboard) -- this is not free so it's only turned on on 
    production, in general

## Troubleshooting/lessons learned

* You can't just delegate the image upload to a celery task without 
    `django-queued-storage` or some other workaround; you can't pass the Image
    to the celery task, so the upload fails.

* `django-queued-storage` is failing because the image file isn't writing to
    Heroku; have deferred image upload queuing for now.

* If you change tasks.py (including by adding something with tasks to `INSTALLED_APPS`), 
    you need to restart the celery worker so it can notice and register the new tasks.

* If you try to get a "No handler was found" error when uploading pictures, you need
    to enable S3
