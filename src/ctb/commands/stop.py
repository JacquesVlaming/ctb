#!/usr/bin/python
# coding: utf-8
"""
Remove microservices from GKE cluster.
"""

# Proprietary packages
import ctb.utils as utils
import ctb.validate as validate
from ctb.utils import cmd, env

def run():
    # Ensure that this action is done on your cluster and not someone else's.
    validate.kubectl_context()

    print("")
    print("Removing microservices and monitoring agents from GKE...")
    print("")

    print("Recreating secrets...")
    cmd("kubectl delete secret ctb-secrets --namespace=default")
    cmd("kubectl delete secret ctb-secrets --namespace=kube-system")
    cmd("kubectl create secret generic ctb-secrets --from-env-file='{}' --namespace=default".format(env("ENVFILE")))
    cmd("kubectl create secret generic ctb-secrets --from-env-file='{}' --namespace=kube-system".format(env("ENVFILE")))

    print("")
    print("Running skaffold...")
    cmd("skaffold delete --default-repo=gcr.io/$GCP_PROJECT_NAME -p stable")

    print("")
    print("Done.")
