Settings files inherit from each other; base, local, and server are designed to be inherited from.

Inheritance tree:

base
 - local
 	- local/[developer_name]
 - server
 	- staging
 	- production

Each server or dev box should point to its appropriate settings file by setting the DJANGO_SETTINGS_MODULE environment variable.

e.g.
export DJANGO_SETTINGS_MODULE=customfit.settings.staging
export DJANGO_SETTINGS_MODULE=customfit.settings.dev.dev_name`