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

    # Decode bytes → str
    if isinstance(out, bytes):
        current_context = out.decode("utf-8").strip()
    else:
        current_context = out.strip()

    required_context = "gke_{}_{}_ctb-{}".format(
        env("GCP_PROJECT_NAME"),
        env("GCP_REGION_NAME"),
        env("DEPLOYMENT_NAME")
    )

    # Check if current_context is valid
    if not current_context.startswith("gke_"):
        print("\n" + colored("Error: kubectl doesn't appear to be set up correctly.", "yellow", attrs=["bold"]))
        print("\n" + colored("Ran this command:", "yellow", attrs=["bold"]))
        print("\n  " + colored("kubectl config current-context", "yellow"))
        print("\n" + colored("Expected this response:", "yellow", attrs=["bold"]))
        print("\n  " + colored("{}".format(required_context), "yellow"))
        print("\n" + colored("Received this instead:", "yellow", attrs=["bold"]))
        print("\n" + colored(current_context if out else err, "yellow"))
        sys.exit(1)

    # Check if current_context matches required_context
    if current_context != required_context:
        print("\n" + colored("Error: Your current kubectl context does not match your .env file configuration.", "yellow", attrs=["bold"]))
        print("\n  Current context:  {}".format(current_context))
        print("  Required context: {}".format(required_context))
        print("\n" + colored("To confirm that you want to switch to the required context, run this command before running ctb:", "yellow"))
        print("\n  " + colored(
            "gcloud container clusters get-credentials ctb-{} --region={} --project={}".format(
                env("DEPLOYMENT_NAME"), env("GCP_REGION_NAME"), env("GCP_PROJECT_NAME")
            ),
            "yellow",
            attrs=["bold"]
        ))
        print("")
        sys.exit(0)

    return True


# def kubectl_context():
#     exitcode, out, err = cmd("kubectl config current-context", False)
#     current_context = out.strip()
#     required_context = "gke_{}_{}_ctb-{}".format(env("GCP_PROJECT_NAME"), env("GCP_REGION_NAME"), env("DEPLOYMENT_NAME"))
#     if not current_context.startswith("gke_"):
#         print("")
#         print(colored("Error: kubectl doesn't appear to be set up correctly.", "yellow", attrs=["bold",]))
#         print("")
#         print(colored("Ran this command:", "yellow", attrs=["bold",]))
#         print("")
#         print(colored("  kubectl config current-context", "yellow"))
#         print("")
#         print(colored("Expected this response:", "yellow", attrs=["bold",]))
#         print("")
#         print(colored("  {}".format(required_context), "yellow"))
#         print("")
#         print(colored("Received this instead:", "yellow", attrs=["bold",]))
#         print("")
#         print(colored(current_context if out else err, "yellow"))
#         sys.exit(1)
#     if current_context != required_context:
#         print("")
#         print(colored("Error: Your current kubectl context does not match your .env file configuration.", "yellow", attrs=["bold",]))
#         print("")
#         print(colored("  Current context:  {}".format(current_context), "yellow"))
#         print(colored("  Required context: {}".format(required_context), "yellow"))
#         print("")
#         print(colored("To confirm that you want to switch to the required context, run this command before running ctb:", "yellow"))
#         print("")
#         print(colored("  gcloud container clusters get-credentials ctb-{} --region={} --project={}".format(env("DEPLOYMENT_NAME"), env("GCP_REGION_NAME"), env("GCP_PROJECT_NAME")), "yellow", attrs=["bold",]))
#         print("")
#         sys.exit(0)
#     return True
