#!/usr/bin/python
# coding: utf-8
"""
Deploy updates to the microservices for a given scenario.
"""

# Standard packages
import json
import os
import uuid

# Third-party packages
import requests

# Proprietary packages
import ctb.alerts as alerts
import ctb.constants as constants
import ctb.utils as utils
import ctb.validate as validate
from ctb.utils import cmd, env

def run(scenario="stable", quiet=False):
    # Ensure that this action is done on your cluster and not someone else's.
    validate.kubectl_context()

    # Set the APM service version to a random hash value.
    # This new version will only apply to the services that have changed since
    # the prior scenario.
    os.environ["ELASTIC_APM_SERVICE_VERSION"] = str(uuid.uuid4())[:7]
    utils.update_envfile()

    print("")
    print("Starting the '{}' scenario...".format(scenario))

    # Disable alerts when starting the "stable" scenario
    if scenario == "stable":
        print("")
        print("Disabling alerts...")
        alerts.toggle_all("disable")

    if scenario == "stable" and not quiet:
        print("")
        print("Sending notification to Slack...")
        requests.post(
            url=env("SLACK_WEBHOOK_URL"),
            json={ "text": "Great work, SREs! We're resolving the issue, and we'll be done in a moment.\n    _— Hipster Shop Dev Team_ :coffee:" },
            timeout=30
        )

    print("")
    print("Recreating secrets...")
    cmd("kubectl delete secret ctb-secrets --namespace=default")
    cmd("kubectl delete secret ctb-secrets --namespace=kube-system")
    cmd("kubectl create secret generic ctb-secrets --from-env-file='{}' --namespace=default".format(env("ENVFILE")))
    cmd("kubectl create secret generic ctb-secrets --from-env-file='{}' --namespace=kube-system".format(env("ENVFILE")))

    print("")
    print("Running skaffold using the '{}' profile...".format(scenario))
    cmd("skaffold run --default-repo=gcr.io/$GCP_PROJECT_NAME -l skaffold.dev/run-id=ctb-$DEPLOYMENT_NAME -p {}".format(scenario))

    # Store the frontend external IP
    exitcode, out, err = cmd("kubectl get service frontend-external -o json", stdout=False)
    if err:
        raise Exception(err)
    ingress = json.loads(out).get("status", {}).get("loadBalancer", {}).get("ingress", [{}])
    frontend_ip = ingress[0].get("ip") if ingress else ""
    os.environ["FRONTEND_URL"] = "http://{}".format(frontend_ip)
    utils.update_envfile()

    if scenario != "stable" and not quiet:
        print("")
        print("Sending notification to Slack...")
        response = requests.post(
            url=env("SLACK_WEBHOOK_URL"),
            json={ "text": constants.SLACK_SCENARIO_START_MESSAGE },
            timeout=30
        )

    # Enable alerts when starting any scenario that is not "stable"
    if scenario != "stable":
        print("")
        print("Enabling alerts...")
        alerts.toggle_all("enable")

    if scenario == "stable" and not quiet:
        print("")
        print("Sending confirmation message to Slack...")
        response = requests.post(
            url=env("SLACK_WEBHOOK_URL"),
            json={ "text": constants.SLACK_SCENARIO_END_MESSAGE },
            timeout=30
        )

    print("")
    print("Done.")

    if scenario != "stable":
        print("")
        print("Don't forget to run \033[1m./ctb stabilize\033[0m before running the next scenario.")
        print("")
