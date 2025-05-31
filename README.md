customfit
=========

### To set up local development environment
When in doubt, consult [_Two Scoops of Django_](https://daniel.feldroy.com/books/tech).

####Install/make sure you have:
* pip
* `pip install virtualenv`
* `pip install virtualenvwrapper`
* the [Heroku CLI](https://toolbelt.heroku.com/)
* postgres -- if you don't have it working already and you're on a Mac, 
  use [postgres.app](http://postgresapp.com/)

####Set stuff up
Go to your preferred directory and...

* Clone the customfit repo
* `cd customfit`
* `mkvirtualenv customfit`
* `pip install -r requirements.txt`
	* You may also need libmemcached (on mac os, `sudo port install libmemcached`)
* add a settings file for yourself to src/customfit/settings/dev/YOUR_SETTINGS_FILE, by analogy with existing.  Update:
	* EMAIL_HOST_USER & EMAIL_HOST_PASSWORD (authorization to use EMAIL_HOST for sending mail) 
* ``echo 'export DJANGO_SETTINGS_MODULE=customfit.settings.dev.YOUR_SETTINGS_FILE' >> ~/$WORKON_HOME/customfit/bin/postactivate``
* see also src/customfit/settings/README.md
* source any .bashrc changes (e.g. email passwd), then `deactivate ; workon customfit`
* in psql: `create database customfit_django;`
* instantiate the data model: `python src/manage.py migrate`
* copy static files: `python src/manage.py collectstatic`
* load domain data into your db: designs at least, maybe other things?
* in database customfit_django, `update django_site set domain='localhost:8000', name='yourname dev site';`
* associate images with the designs via django admin (site/makewearsudo)

* Now start your server: `python src/manage.py runserver`



### To deploy to staging and production servers
* see [doc/jenkins.md](doc/jenkins.md)

### Git flow
#### Branching and merging
* `master` is deployable.
* Branch off `master`.
* Branches named `feature_*` or `bugfix_*` will be automatically tested
  when pushed to github; if tests pass, they will be merged to `develop` and
  deployed to customfit-testing. If you want code review without automatic 
  merging, use a different name.
* Hence `develop` is a dirty branch used for testing.
* Merges are via pull request, so that they will be seen by at least one 
  other person.
  * Pull-request your branch into `master`.
  * Assign your pull requests to someone logical.
  * Reviewer should merge into the appropriate branch(es) to `master` as 
  soon as satisfied.
  * Branches should be deleted once merged.
  * When code is committed to `master`, Jenkins will run tests and, if 
    they pass, deploy to staging.
* Migrations must get to all developers as soon as possible.
  * When you believe your code will require a migration, discuss it with
    the other developers ASAP.
  * Issue a PR to merge your migrations (and just your migrations) to 
    `master` as soon as they are stable.
  * You can revise and blow away migrations on localhost to your heart's
    content, but once you've pushed them to github, you're committed - any
    revisions must be forward migrations.
* If you forget to merge your migrations and have committed a migration to a 
  branch you don't expect to merge to master soon, you can [cherry-pick that 
  commit](http://blogs.law.harvard.edu/acts/2012/07/10/github-pull-request-for-just-one-commit/)


#### Naming
Branches named `feature_*` or `bugfix_*` will be automatically tested when 
pushed and merged to develop if tests pass.  (See `doc/jenkins.md`.)

Therefore, use any other descriptive name if you want to push a branch up to be
code-reviewed; rename to `feature_*` when deployable.  Branches not needing code
review (e.g. new HTML-only pages, copy-editing) can be feature_*-named from the
outset.

If you're code-reviewing a branch with a feature or bugfix prefix, check
that its tests have passed.  If the branch has a different name, you're
responsible for confirming that tests pass manually.



### Pep 8
* Follow pep 8 mostly.  We'll keep notes here of any places we are purposely breaking pep 8.


### TESTING
* Nose will automatically run most of our tests when you run ./manage.py test.  
* You can configure Nose in your settings file.
* There are also Selenium tests you can run with ./manage.py test customfit.js_tests.tests




