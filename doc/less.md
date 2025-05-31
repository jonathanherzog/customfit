# Less and CustomFit

CustomFit stylesheets are written in less and compiled to css.

This has several advantages:
* We can incorporate and modify Bootstrap classes directly in their precompiled form, rather than needing to find and selectively override the CSS (which is both challenging and error-prone);
* We can write our own stylesheets in an extremely modular form, full of reusable components.

It does require that less files be compiled to CSS, so that they can be used by the browser. We have different ways of handling this in development and production.

## Development less pipeline

In development, we compile all our less files on the fly, in the browser, using less.js (specifically, `src/customfit/static/js/less-2.5.1.min.js`). This has the advantage that changes to our less files are instantly reflected upon reload.

## Production less pipeline

less.js is not fast enough for production; we want to compile our less into CSS asynchronously so that users only need to fetch the CSS file and not wait for it to be compiled. 

If there is a shell script at `bin/post_compile`, Heroku runs it automatically when we push code. Our post-compile hook does three things:
* Installs npm (which is not part of the Python buildpack)
* Uses npm to install less
* Uses less to compile `static/customfit.less` to `src/customfit/static/css/customfit.css`.

When `PRECOMPESS_LESS` is true (see below), `base.html` looks for its stylesheet at `{% static 'customfit.css' %}`.

__If you link additional less files beyond customfit.less and tiles.css from the stylesheets, you must make sure to add a compilation step for them in `bin/run_less` or they will not be available to templates.__


## Settings

`settings.COMPRESS_OFFLINE=False`

See below on why we don't use django_compressor's offline compression.

__For ease of development__, use:
`PRECOMPRESS_LESS=False`

This is the setting in `settings/base.py`.

__On production__ and environments mimicking it, use:
`PRECOMPRESS_LESS=True`

This is the setting in `settings/server.py`.

A context processor uses the value of this variable to set the value of the `precompress_less` template variable; `base.html` in turn uses that to decide whether to look for a precompiled CSS stylesheet or to use less.js to compile less on the fly.


## Why aren't we using django_compressor to handle less?
django_compressor (which we are using for our other static assets already) has built-in support for precompiling less files to CSS (before and outside of the request/response loop), but it does not work for our purposes. Why?
* You can either precompile _both_ the CSS and the JS or neither.
* If you precompile the JS, you don't have template context available. This means, in particular, you don't have (and cannot have) any information from `request.user`. However, we have numerous instances where `request.user` is required to set user-specific JS variable values.

You could try to rewrite the django_compressor `compress` management command to do only the less->css step, and then handle that CSS file and all JS synchronously, but you would find yourself standing atop a mighty pile of yak hair, and it would blow away in a stiff breeze the moment django_compressor changed its internals.


## For more information

To learn about less and what it offers: http://lesscss.org/

For Bootstrap's less files: http://getbootstrap.com/customize/#less