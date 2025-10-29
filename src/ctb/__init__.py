#!/usr/bin/python
# coding: utf-8
"""
================================================================================

Capture the Bug (CTB) - Instructor CLI

Before the event:

  ctb validate            Validate ./ctb dependencies and configuration.
  ctb setup [ess|gke]     Deploy ESS and GKE clusters, services, and agents.
    [-d|--dev]              -d  Deploy a smaller ESS cluster.
  ctb endpoints           List deployed endpoints and credentials.

During the event:

  ctb scenarios           List scenarios that are available.
  ctb start SCENARIO      Redeploy services for a given scenario.
    [-q|--quiet]            -q  Suppress "scenario start" message on Slack.
  ctb stabilize           Revert the services to the "stable" scenario.
    [-q|--quiet]            -q  Suppress "scenario done" message on Slack.

After the event:

  ctb destroy [ess|gke]   Remove ESS and GKE clusters.

Dev usage:

  ctb diff SCENARIO [SCENARIO]  Compare the code of a scenario to the "stable"
                                scenario or to another scenario.

Before using this tool, you must set the required variables in your .env file,
which is located here:

  {ENVFILE}

--------------------------------------------------------------------------------
"""

# Standard packages
import os
import re
import sys

# Proprietary packages
from ctb.commands import destroy
from ctb.commands import diff
from ctb.commands import endpoints
from ctb.commands import scenarios
from ctb.commands import setup
from ctb.commands import stabilize
from ctb.commands import start
from ctb.commands import stop
from ctb.commands import validate
from ctb.utils import env

# Find and source the .env file before doing anything.
#
# Set BASEDIR as the directory of the current executing script, unless the user
# overrides BASEDIR. If the user overrides BASEDIR with a relative path, assume
# the parent directory is the current working directory of the user.
if not os.environ.get("BASEDIR"):
    os.environ["BASEDIR"] = os.path.dirname(os.path.realpath(__file__))
elif not os.path.isabs(os.environ.get("BASEDIR")):
    os.environ["BASEDIR"] = os.path.join(os.getcwd(), env("BASEDIR"))
# Assume ENVFILE is .env on BASEDIR, unless the user overrides ENVFILE.
# If the user overrides ENVFILE with a relative path, assume the path is the
# current working directory of the user.
if not os.environ.get("ENVFILE"):
    os.environ["ENVFILE"] = os.path.join(env("BASEDIR"), ".env")
elif not os.path.isabs(os.environ.get("ENVFILE")):
    os.environ["ENVFILE"] = os.path.join(os.getcwd(), env("ENVFILE"))
if not os.path.isfile(env("ENVFILE")):
    print("Warning: .env file not found: {}".format(env("ENVFILE")))
    sys.exit(1)
with open(env("ENVFILE"), "r") as file:
    for line in file:
        matches = re.findall(patterns.ENV_VAR, line)
        if len(matches) > 0:
            variable, value = matches[0]
            os.environ[variable] = value

def help():
    """Print CLI usage."""
    print(__doc__.format(ENVFILE=env("ENVFILE")))


####  Main  ####################################################################

def run():

    # Validate arguments
    if len(sys.argv) < 2:
        help()
        sys.exit(1)

    # Parse command
    command = sys.argv[1]
    args = []
    flags = []
    for arg in sys.argv[2:]:
        if arg.startswith("-"):
            flags.append(arg)
        else:
            args.append(arg)

    # Run command
    if command == "validate":
        commands.validate.run()
        sys.exit(0)

    elif command == "setup":
        ess = True
        gke = True
        if "ess" in args or "gke" in args:
            ess = "ess" in args
            gke = "gke" in args
        dev = "-d" in flags or "--dev" in flags
        commands.setup.run(ess, gke, dev)
        sys.exit(0)

    elif command == "endpoints":
        commands.endpoints.run()
        sys.exit(0)

    elif command == "scenarios":
        commands.scenarios.run()
        sys.exit(0)

    elif command == "start":
        scenario = "stable"
        if len(args) > 0:
            scenario = args[0]
        quiet = "-q" in flags or "--quiet" in flags
        commands.start.run(scenario, quiet)
        sys.exit(0)

    elif command == "stabilize":
        quiet = "-q" in flags or "--quiet" in flags
        commands.stabilize.run(quiet)
        sys.exit(0)

    elif command == "stop":
        commands.stop.run()
        sys.exit(0)

    elif command == "destroy":
        ess = True
        gke = True
        if "ess" in args or "gke" in args:
            ess = "ess" in args
            gke = "gke" in args
        commands.destroy.run(ess, gke)
        sys.exit(0)

    elif command == "diff":
        scenario_from = ""
        scenario_to = "stable"
        if len(args) > 0:
            scenario_from = args[0]
            if len(args) > 1:
                scenario_to = args[1]
            commands.diff.run(scenario_from, scenario_to)
            sys.exit(0)

    help()
    sys.exit(1)


if __name__ == "__main__":
    run()
