
# Testing

## Test runners

This project originally used the nose and py.test test-runners, but these third-party
tools stopped having any advantages over Django's built-in test-runner after Django 1.8.
In fact, the built-in test runner seems to have better support for parallel tests than 
the external tools. Hence, we have switched to using just:

* the built-in test runner, 
* the unittest framework from the python standard library, 
* Django's built-in testing tools,
* The Selenium web-browsing framework.

In keeping with this policy, write tests that could run under the plain `unittest` 
framework. This means:
 
* Using `unittest.TestCase` or subclasses,
* Giving your test-methods names that start with `test_`,
* Using `setUp` and `tearDown`, and
* Using the 'mixin' strategy to create base classes of tests that are not
  themselves tests. (The mixin strategy: make the base class a mixin class
  that inherits from `object` and not `TestCase`, and then have your actual
  test-case classes inherit from both the mixin and `TestCase`. Since
  order of inheritence matters, the mixin should come first:
  
     class FooTest(MixinClass, TestCase):
     
  Otherwise, `TestCase.setUp()` will shadow `MixinClass.setUp()`.)


## Test tags


We use two tags:


* 'slow' for those test that are extremely time-consuming. (Currently unusued.)

* 'selenium' for those tests that use the selenium browser-automation framework.



A note on Selenium: at the time of this writing (Feb 2016) we have selenium tests in the
code but many are being skipped for being broken. They were added by a
former member of the team, but none of the remaining members knew how to 
maintain them. They eventually grew stale and we just put @skip statements
in to shut them up. So, here's where we are:

* Mark all selenium-using tests with the 'selenium' tag. Be
sure to do so at the level where the selenium driver is instantiated 
(usually the class level, but maybe sometimes the method level). That 
way, we will be able to turn selenium tests on locally and off as needed.

* If we are going to skip a class of selenium tests, be sure that there are
we don't instantiate a webdriver in the classSetUp method. That method 
is run before the @skip applies, and so it *will* pop up a Firefox 
window even if there are no tests run.
    
    
* Note: In keeping with our desire to use 'standard' `unittest`-style test
cases, Selenium tests need to be in a `TestCase` class or sub-class. 
And since selenium needs to interact with a live server, this should
almost certainly be Django's `LiveServerTestCase`.
        

## Running tests

To speed up tests, consider the following command-line flags:

* --keepdb
* --parallel, or --parallel N for some integer N (note: a high value of N will cause weird problems. On CircleCI, for 
  example, a high value of N causes the system to exhaust the open-file limit.)
* --exclude-tag=slow



If you're having trouble running the tests, check two issues:

* Database: Do you have Postgres up and running? Is it running where specified in the file named in your 
DJANGO_SETTINGS_FILE environment variable? Does the database actually exist? 

* If the tests run but LOTS of them fail, check that you have redis-server working and that you've started a celery 
worker. Again, see `.circleci/config.yml`, under `jobs:test:` for sample commands. 

## Factories:

We use FactoryBoy extensively in these tests, and all new models should come with FactoryBoy-based
factories for them. FactoryBoy is awesomeness on a stick covered in awesome sauce, and comes with a number
of very useful ways to control/define the ways to create test instances. See the factories in 
`customfit_app/tests/factories.py` for examples. Right now, we're using FactoryBoy 2.8.2, and FactoryBoy 2.9.2
has even more goodness in it. However, we can't switch to that version without a lot of work. Specifically:

* Every time a test-user logs in to the test-server, Django updates the last-logged-in date of the user and saves it.
* This calls the post-save signal for the User model
* DjangoCMS catches this signal and creates a PageUser instance for that user.
* When the test ends and the TestCase wants to roll back the database, it deletes the User but not the PageUser
* This means that when it wants to finish the rollback and test database integrity, we get an IntegrityError from
    DjangoCMS's `cms_pageuser` table (complaining about a link to a non-existant user).
    
To fix this, we would need to add an explicit tearDown to every one of our tests that uses `client.login()` 
or `client.force_login`. Eventually, this will be worth it-- but not today.

(Note: one can also suppress the above problems by adding `CMS_PERMISSION=False` to your settings file, but I think
that leads to too much risk of false negatives.)

