#!/usr/bin/python
# coding: utf-8
"""
Validate dependencies, configurations, and deployments.
"""

# Standard packages
import os
import re
import sys
import yaml

# Third-party packages
import requests
from termcolor import colored

# Proprietary packages
import ctb.constants as constants
import ctb.patterns as patterns
import ctb.probe as probe
from ctb.utils import cmd, env

def run_validate_slack_webhook_url_valid():
    if not env("SLACK_WEBHOOK_URL"):
        return None
    response = requests.get(url=env("SLACK_WEBHOOK_URL"), timeout=30)
    return response.status_code == 400

def run_validate_ess_api_key_valid():
    if not env("ELASTIC_CLOUD_API_KEY"):
        return None
    response = requests.get(
        url="https://api.elastic-cloud.com/api/v1/deployments",
        headers=constants.ess_api_headers(env("ELASTIC_CLOUD_API_KEY")),
        timeout=30
    )
    return response.status_code in range(200, 299)

def run_validate_env_field_set(field, envfile=env("ENVFILE")):
    with open(env("ENVFILE"), "r") as file:
        for line in file:
            matches = re.findall(patterns.ENV_VAR, line)
            if len(matches) > 0:
                variable, value = matches[0]
                if variable == field and value != "":
                    return True
    return False

def run_validate_env_exists(envfile=env("ENVFILE")):
    try:
        return os.path.isfile(envfile)
    except:
        return False

def run_validate_skaffold_installed():
    try:
        exitcode, out, err = cmd("skaffold version", False)
        return out.startswith("v")
    except:
        return False

def run_validate_gcloud_installed():
    try:
        exitcode, out, err = cmd("gcloud version", False)
        return out.startswith("Google Cloud SDK")
    except:
        return False

def run_validate_kubectl_installed():
    try:
        exitcode, out, err = cmd("kubectl version", False)
        return out.startswith("Client Version")
    except:
        return False

def run_validate_docker_running():
    try:
        exitcode, out, err = cmd("docker ps -q", False)

        # Decode bytes to string if needed
        if isinstance(out, bytes):
            out = out.decode("utf-8").strip()  # strip removes trailing newline

        # Return True if output is empty (no containers) or matches container IDs
        return bool(re.match(r"^[a-f0-9]+$", out)) or out == ""
    except:
        return False

def run_validate_docker_installed():
    try:
        exitcode, out, err = cmd("docker --version", False)
        if isinstance(out, bytes):
            out = out.decode("utf-8")
        return out.startswith("Docker version")
    except:
        return False

def run():

    def report(message, validation, *validation_args, **validation_kwargs):
        sys.stdout.write("  {}: ".format(message))
        sys.stdout.flush()
        is_valid = validation
        if callable(validation):
            is_valid = validation(*validation_args, **validation_kwargs)
        answer, color = "n/a", "yellow"
        if is_valid:
            answer, color = "yes", "green"
        elif is_valid is False:
            answer, color = "no", "red"
        sys.stdout.write(colored(answer, color, attrs=["bold",]))
        sys.stdout.write("\n")
        sys.stdout.flush()

    print("")
    print("Dependencies:")
    report("docker installed", run_validate_docker_installed)
    report("docker running", run_validate_docker_running)
    report("kubectl installed", run_validate_kubectl_installed)
    exitcode, out, err = cmd("kubectl config current-context", False)
    current_context = out.strip()
    required_context = "gke_{}_{}_ctb-{}".format(env("GCP_PROJECT_NAME"), env("GCP_REGION_NAME"), env("DEPLOYMENT_NAME"))
    sys.stdout.write("  kubectl context: ")
    sys.stdout.flush()
    if isinstance(current_context, bytes):
        current_context = current_context.decode("utf-8")
    if current_context == required_context:
        sys.stdout.write(colored(current_context, "green", attrs=["bold"]))
        sys.stdout.write("\n")
        sys.stdout.flush()
    elif not current_context.startswith("gke_"):
        sys.stdout.write(colored("unknown", "yellow", attrs=["bold"]))
        sys.stdout.write("\n")
        sys.stdout.flush()
    else:
        sys.stdout.write(colored(current_context, "yellow", attrs=["bold"]))
        sys.stdout.write(" (expected: {})".format(colored(required_context, "white", attrs=["bold"])))
        sys.stdout.write("\n")
        sys.stdout.flush()
    report("gcloud installed", run_validate_gcloud_installed)
    report("skaffold installed", run_validate_skaffold_installed)

    print("")
    print(".env configuration:")
    report(".env file exists", run_validate_env_exists, env("ENVFILE"))
    env_fields_required = (
        "DEPLOYMENT_NAME",
        "ELASTIC_CLOUD_API_KEY",
        "ELASTIC_CLOUD_REGION",
        "ELASTICSEARCH_VERSION",
        "GCP_PROJECT_NAME",
        "GCP_REGION_NAME",
        "GCP_NETWORK_NAME",
        "GCP_SUBNETWORK_NAME",
        "GCP_SERVICE_ACCOUNT_NAME",
        "SLACK_WEBHOOK_URL"
    )
    for field in env_fields_required:
        report("{} set".format(field), run_validate_env_field_set, field, env("ENVFILE"))

    print("")
    print("Deployment configuration:")
    report("ELASTIC_CLOUD_API_KEY valid", run_validate_ess_api_key_valid)
    report("SLACK_WEBHOOK_URL valid", run_validate_slack_webhook_url_valid)

    print("")
    print("ESS deployment:")
    status_ess = probe.status_ess()
    report("Deployment available", status_ess)
    status_ess_elasticsearch = probe.status_ess_component("elasticsearch") if status_ess else None
    report("Elasticsearch available", status_ess_elasticsearch)
    status_ess_kibana = probe.status_ess_component("kibana") if status_ess else None
    report("Kibana available", status_ess_kibana)
    status_ess_apm = probe.status_ess_component("apm") if status_ess else None
    report("APM server available", status_ess_apm)
    status_ess_operator_role = probe.status_ess_operator_role() if status_ess_elasticsearch and status_ess_kibana else None
    report("Operator role exists", status_ess_operator_role)
    status_ess_operator_user  = probe.status_ess_operator_user() if status_ess_elasticsearch and status_ess_kibana else None
    report("Operator user exists", status_ess_operator_user)
    status_ess_slack_connector = probe.status_ess_slack_connector() if status_ess_elasticsearch and status_ess_kibana else None
    report("Slack connector exists", status_ess_slack_connector)

    print("")
    print("GKE deployment:")
    status_gke = False
    try:
        status_gke = probe.status_gke()
    except:
        status_gke = False
    report("Cluster available", status_gke)
    if status_gke:
        print("  Microservices status:")
        services = {}

        # Find all deployments and daemonsets from the "stable" scenario
        specs = []
        k8s_manifests_dir = os.path.join(env("BASEDIR"), "hipstershop", "scenarios", "stable", "kubernetes-manifests")
        filenames = os.listdir(k8s_manifests_dir)
        for filename in filenames:
            filepath = os.path.join(k8s_manifests_dir, filename)
            if filename.endswith(".yaml") and os.path.isfile(filepath):
                with open(filepath, "r") as file:
                  lines = []
                  for line in file:
                    line = re.sub(patterns.NEWLINE, "", line)
                    if line == "---":
                        if lines:
                            spec = yaml.load("\n".join(lines), Loader=yaml.FullLoader)
                            specs.append(spec)
                        lines = []
                        continue
                    if not line:
                      continue
                    lines.append(line)
        for spec in specs:
            name = spec.get("metadata", {}).get("name")
            if name and spec.get("kind") in ( "Deployment", "DaemonSet" ):
                services[name] = {
                    "desired": 0,
                    "ready": 0
                }

        # Get statuses of deployments and daemonsets
        lines = []
        exitcode, out, err = cmd("""kubectl get deployments --all-namespaces -o=go-template='{{range .items}}{{.metadata.name}}\t{{.status.replicas}}/{{.status.readyReplicas}}{{printf "\\n"}}{{end}}'""", False)
        for line in out.split("\n"):
            if not line:
                continue
            try:
                name, status = line.split("\t")
                desired, ready = status.split("/")
                if name in services:
                    services[name]["desired"] = desired
                    services[name]["ready"] = ready
            except:
                continue
        exitcode, out, err = cmd("""kubectl get daemonsets --all-namespaces -o=go-template='{{range .items}}{{.metadata.name}}\t{{.status.desiredNumberScheduled}}/{{.status.numberReady}}{{printf "\\n"}}{{end}}'""", False)
        for line in out.split("\n"):
            if not line:
                continue
            try:
                name, status = line.split("\t")
                desired, ready = status.split("/")
                if name in services:
                    services[name]["desired"] = desired
                    services[name]["ready"] = ready
            except:
                continue

        # Display statuses
        names = services.keys()
        names.sort()
        for name in names:
            desired = services[name]["desired"]
            ready = services[name]["ready"]
            color = "white"
            if desired != ready and ready == 0:
                color = "red"
            elif desired != ready:
                color = "yellow"
            elif desired == ready and ready == 0:
                color = "yellow"
            elif desired == ready:
                color = "green"
            print("  - {} {}".format(name, colored("{}/{}".format(ready, desired), color, attrs=["bold",])))

    print("")
    print("Hipster Shop:")
    if status_gke:
        report("Frontend available", probe.status_frontend)
    else:
        report("Frontend available", None)

    print("")
