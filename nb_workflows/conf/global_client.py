import os

from nb_workflows.secrets import nbvars

# Main settings
WORKFLOW_SERVICE = os.getenv("NB_WORKFLOW_SERVICE", "http://localhost:8000")

PROJECTID = ""
PROJECT_NAME = ""

AGENT_TOKEN = nbvars.get("AGENT_TOKEN", "")
AGENT_REFRESH_TOKEN = nbvars.get("AGENT_REFRESH", "")

CLIENT_TOKEN = nbvars.get("NB_CLIENT_TOKEN", "")
CLIENT_REFRESH_TOKEN = nbvars.get("NB_CLIENT_REFRESH", "")

# Log
LOGLEVEL = nbvars.get("NB_LOG", "INFO")
# If None it will be false, anything else true
DEBUG = bool(nbvars.get("NB_DEBUG", None))


# Folders
BASE_PATH = nbvars.get("NB_BASEPATH", os.getcwd())

# Options to build the docker image used as runtime of
# this project.
DOCKER_IMAGE = {
    "maintener": "NB Workflows <package@nbworkflows.com>",
    "image": "python:3.8.10-slim",
    # TODO:
    # Should be managed in the server
    # Would it have to be based on the id of the user?
    "user": {"uid": 1089, "gid": 1090},
    "build_packages": "build-essential libopenblas-dev git",
    "final_packages": "vim-tiny",
}

DOCKER_COMPOSE = {
    "postgres": {"image": "postgres:14-alpine", "listen_addr": "5432"},
    "redis": {"image": "redis:6-alpine", "listen_addr": "6379"},
    "web": {"listen_addr": "8000"},
    "jupyter": {"listen_addr": "127.0.0.1:8888"},
}
