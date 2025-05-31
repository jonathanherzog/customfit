import subprocess

HEROKU_APP_NAME = "fill_me_in"
TAGGING_MESSAGE = "Tagging deployed_production"

commands = [
    ("heroku maintenance:on --app {HEROKU_APP_NAME}", True),
    ("heroku pg:backups:capture --app {HEROKU_APP_NAME}", True),
    ("git tag -d deployed_production", False),
    ("git push origin :refs/tags/deployed_production", False),
    ("git push --force heroku master", True),
    ("git tag -a -f -m {TAGGING_MESSAGE} deployed_production", True),
    ("git push origin deployed_production", True),
    (
        "heroku run --exit-code --app {HEROKU_APP_NAME} -- python src/manage.py migrate --noinput",
        True,
    ),
    ("sleep 5", True),
    (
        "heroku run --exit-code --app {HEROKU_APP_NAME} -- python src/manage.py clear_cache",
        True,
    ),
    ("heroku maintenance:off --app {HEROKU_APP_NAME}", True),
    (
        "heroku run --exit-code --app {HEROKU_APP_NAME} -- src/manage.py collectstatic --noinput",
        True,
    ),
    (
        "heroku run --exit-code  --app {HEROKU_APP_NAME} -- src/manage.py set_cors_policy_in_s3",
        True,
    ),
    ("heroku pt --app {HEROKU_APP_NAME}", True),
]


for command, check in commands:
    command_list = command.split(" ")
    substitutions = {
        "HEROKU_APP_NAME": HEROKU_APP_NAME,
        "TAGGING_MESSAGE": TAGGING_MESSAGE,
    }
    formatted_command_list = [s.format(**substitutions) for s in command_list]
    print(formatted_command_list)
    subprocess.run(formatted_command_list, check=check)
