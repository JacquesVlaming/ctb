#!/usr/bin/python
# coding: utf-8
"""
Destroy ESS deployment and/or GKE cluster.
"""

# Standard packages
import os
import sys

# Third-party packages
import requests

# Proprietary packages
import ctb.constants as constants
import ctb.utils as utils
import ctb.validate as validate
from ctb.utils import cmd, env


####  Validation  ##############################################################

def validate_destroy():
    """Check for DEPLOYMENT_NAME for any setup command."""
    if not os.environ.get("DEPLOYMENT_NAME"):
        print("You must set DEPLOYMENT_NAME in {}".format(env("ENVFILE")))
        sys.exit(1)

    # Ensure that this action is done on your cluster and not someone else's.
    validate.kubectl_context()

def validate_destroy_gke():
    validate_destroy()
    required = ( "GCP_PROJECT_NAME", "GCP_REGION_NAME" )
    for variable in required:
        if not env(variable):
            print("")
            print("You must set these variables in {} to destroy GKE:".format(env("ENVFILE")))
            print("")
            for variable in required:
                print("  {}".format(variable))
            print("")
            sys.exit(1)

def validate_destroy_ess():
    validate_destroy()
    required = ( "ELASTIC_CLOUD_DEPLOYMENT_ID", )
    for variable in required:
        if not env(variable):
            print("")
            print("You must set these variables in {} to destroy ESS:".format(env("ENVFILE")))
            print("")
            for variable in required:
                print("  {}".format(variable))
            print("")
            sys.exit(1)


####  Execution  ###############################################################

def run_destroy_ess():
    validate_destroy_ess()
    print("")
    print("Removing ESS deployment...")
    response = requests.post(
        url="https://api.elastic-cloud.com/api/v1/deployments/{}/_shutdown".format(env("ELASTIC_CLOUD_DEPLOYMENT_ID")),
        headers=constants.ess_api_headers(env("ELASTIC_CLOUD_API_KEY")),
        timeout=30
    )
    if response.json().get("orphaned"):
        print("")
        print("Updating .env file...")
        os.environ["ELASTIC_CLOUD_DEPLOYMENT_ID"] = "{}-deleted".format(env("ELASTIC_CLOUD_DEPLOYMENT_ID"))
        utils.update_envfile()
    else:
        print(response.content)

def run_destroy_gke():
    validate_destroy_gke()
    print("")
    print("Removing GKE cluster...")
    cmd("""
    gcloud beta container clusters delete "ctb-$DEPLOYMENT_NAME" \
    --project "$GCP_PROJECT_NAME" \
    --region "$GCP_REGION_NAME" \
    --quiet
    """)

def run(ess=True, gke=True):
    if ess:
        run_destroy_ess()
    if gke:
        run_destroy_gke()
    print("")
    print("Done.")
