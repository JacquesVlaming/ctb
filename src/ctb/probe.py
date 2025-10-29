#!/usr/bin/python
# coding: utf-8
"""
Check the status of various resources.
"""

# Standard packages
import re

# Third-party packages
import requests

# Proprietary packages
from ctb import constants
from ctb import patterns
from ctb.utils import cmd, env

def get_ess_operator_role():
    return requests.get(
        url="{}/api/security/role/operator".format(env("KIBANA_URL")),
        headers=constants.kibana_api_headers(),
        timeout=30
    )

def get_ess_operator_user():
    return requests.get(
        url="{}/internal/security/users/operator".format(env("KIBANA_URL")),
        headers=constants.kibana_api_headers(),
        timeout=30
    )

def get_ess_slack_connector():
    return requests.get(
        url="{}/.kibana/_search?q=(type:action+AND+slack)".format(env("ELASTICSEARCH_URL")),
        auth=(env("ELASTICSEARCH_USERNAME"), env("ELASTICSEARCH_PASSWORD")),
        timeout=30
    )

def status_gke():
    if not env("GCP_PROJECT_NAME") or not env("GCP_REGION_NAME") or not env("DEPLOYMENT_NAME"):
        return None
    exitcode, out, err = cmd("""
    gcloud beta container clusters describe "projects/$GCP_PROJECT_NAME/zones/$GCP_REGION_NAME/clusters/ctb-$DEPLOYMENT_NAME" --region=$GCP_REGION_NAME
    """, stdout=False)
    if err:
        raise Exception(err)
    status = re.findall(patterns.STATUS, out)
    if status:
        return status[0] == "RUNNING"
    return False

def status_ess():
    if not env("ELASTIC_CLOUD_DEPLOYMENT_ID") or not env("ELASTIC_CLOUD_API_KEY"):
        return None
    try:
        response = requests.get(
            url="https://api.elastic-cloud.com/api/v1/deployments/{}".format(env("ELASTIC_CLOUD_DEPLOYMENT_ID")),
            headers=constants.ess_api_headers(),
            timeout=30
        )
        resources = response.json().get("resources", {}).get("elasticsearch", [{}])
        status = resources[0].get("info", {}).get("status") if resources else None
        if response.status_code in range(200, 299) and status != "stopped":
            return True
        if response.status_code in range(400, 599) and response.status_code not in [404, 410]:
            raise Exception(response)
    except requests.exceptions.ReadTimeout:
        return False
    return False

def status_ess_component(component):
    if not env("ELASTIC_CLOUD_DEPLOYMENT_ID") or not env("ELASTIC_CLOUD_API_KEY"):
        return None
    if component == "elasticsearch" and (not env("ELASTICSEARCH_URL") or not env("ELASTICSEARCH_USERNAME") or not env("ELASTICSEARCH_PASSWORD")):
        return None
    elif component == "kibana" and (not env("KIBANA_URL") or not env("ELASTICSEARCH_USERNAME") or not env("ELASTICSEARCH_PASSWORD")):
        return None
    elif component == "apm" and (not env("ELASTIC_APM_SERVER_URL") or not env("ELASTIC_APM_SECRET_TOKEN")):
        return None
    try:
        response = requests.get(
            url="https://api.elastic-cloud.com/api/v1/deployments/{}/{}/main-{}".format(env("ELASTIC_CLOUD_DEPLOYMENT_ID"), component, component),
            headers=constants.ess_api_headers(),
            timeout=30
        )
        if response.status_code in range(400, 599) and response.status_code not in [404, 410]:
            raise Exception(response)
        healthy = response.json().get("info", {}).get("plan_info", {}).get("healthy")
        current = response.json().get("info", {}).get("plan_info", {}).get("current")
        return healthy and current
    except requests.exceptions.ReadTimeout:
        return False

def status_ess_operator_role():
    if not env("ELASTIC_CLOUD_DEPLOYMENT_ID") or not env("ELASTIC_CLOUD_API_KEY") or not env("ELASTICSEARCH_URL") or not env("KIBANA_URL") or not env("ELASTICSEARCH_USERNAME") or not env("ELASTICSEARCH_PASSWORD"):
        return None
    response = get_ess_operator_role()
    if response.status_code in range(400, 599) and response.status_code not in [404, 410]:
        raise Exception(response)
    return response.status_code == 200

def status_ess_operator_user():
    if not env("ELASTIC_CLOUD_DEPLOYMENT_ID") or not env("ELASTIC_CLOUD_API_KEY") or not env("ELASTICSEARCH_URL") or not env("KIBANA_URL") or not env("ELASTICSEARCH_USERNAME") or not env("ELASTICSEARCH_PASSWORD"):
        return None
    response = get_ess_operator_user()
    if response.status_code in range(400, 599) and response.status_code not in [404, 410]:
        raise Exception(response)
    return response.status_code == 200

def status_ess_slack_connector():
    if not env("ELASTIC_CLOUD_DEPLOYMENT_ID") or not env("ELASTIC_CLOUD_API_KEY") or not env("ELASTICSEARCH_URL") or not env("KIBANA_URL") or not env("ELASTICSEARCH_USERNAME") or not env("ELASTICSEARCH_PASSWORD"):
        return None
    response = get_ess_slack_connector()
    if response.status_code in range(400, 599) and response.status_code not in [404, 410]:
        raise Exception(response)
    return response.json().get("hits", {}).get("total", {}).get("value") > 0

def status_frontend():
    if not env("FRONTEND_URL"):
        return None
    try:
        response = requests.get(url=env("FRONTEND_URL"), timeout=30)
        if response.status_code in range(400, 599) and response.status_code not in [404, 410]:
            raise Exception(response)
        return response.status_code in range(200, 299)
    except:
        return False
