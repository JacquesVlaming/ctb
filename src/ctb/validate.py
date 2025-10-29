#!/usr/bin/python
# coding: utf-8
"""
General validation functions.
"""

# Standard packages
import sys

# Third-party packages
from termcolor import colored

# Proprietary packages
from ctb.utils import cmd, env


def kubectl_context():
    exitcode, out, err = cmd("kubectl config current-context", False)
    current_context = out.strip()
    required_context = "gke_{}_{}_ctb-{}".format(env("GCP_PROJECT_NAME"), env("GCP_REGION_NAME"), env("DEPLOYMENT_NAME"))
    if not current_context.startswith("gke_"):
        print("")
        print(colored("Error: kubectl doesn't appear to be set up correctly.", "yellow", attrs=["bold",]))
        print("")
        print(colored("Ran this command:", "yellow", attrs=["bold",]))
        print("")
        print(colored("  kubectl config current-context", "yellow"))
        print("")
        print(colored("Expected this response:", "yellow", attrs=["bold",]))
        print("")
        print(colored("  {}".format(required_context), "yellow"))
        print("")
        print(colored("Received this instead:", "yellow", attrs=["bold",]))
        print("")
        print(colored(current_context if out else err, "yellow"))
        sys.exit(1)
    if current_context != required_context:
        print("")
        print(colored("Error: Your current kubectl context does not match your .env file configuration.", "yellow", attrs=["bold",]))
        print("")
        print(colored("  Current context:  {}".format(current_context), "yellow"))
        print(colored("  Required context: {}".format(required_context), "yellow"))
        print("")
        print(colored("To confirm that you want to switch to the required context, run this command before running ctb:", "yellow"))
        print("")
        print(colored("  gcloud container clusters get-credentials ctb-{} --region={} --project={}".format(env("DEPLOYMENT_NAME"), env("GCP_REGION_NAME"), env("GCP_PROJECT_NAME")), "yellow", attrs=["bold",]))
        print("")
        sys.exit(0)
    return True
