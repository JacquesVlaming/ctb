#!/usr/bin/python
# coding: utf-8
"""
Setup the ESS deployment and/or GKE cluster and microservices.
"""

# Standard packages
import hashlib
import json
import os
import sys
import time
import traceback

# Third-party packages
import requests

# Proprietary packages
import ctb.alerts as alerts
import ctb.commands.start
import ctb.constants as constants
import ctb.probe as probe
import ctb.utils as utils
from ctb.utils import cmd, env


####  Validation  ##############################################################

def validate_setup():
    """Check for DEPLOYMENT_NAME for any setup command."""
    if not os.environ.get("DEPLOYMENT_NAME"):
        print("You must set DEPLOYMENT_NAME in {}".format(env("ENVFILE")))
        sys.exit(1)

def validate_setup_gke():
    validate_setup()
    required = (
        "GCP_PROJECT_NAME",
        "GCP_REGION_NAME",
        "GCP_NETWORK_NAME",
        "GCP_SUBNETWORK_NAME",
        "GCP_SERVICE_ACCOUNT_NAME"
    )
    for variable in required:
        if not env(variable):
            print("")
            print("You must set these variables in {} to setup GKE:".format(env("ENVFILE")))
            print("")
            for variable in required:
                print("  {}".format(variable))
            print("")
            sys.exit(1)

def validate_setup_ess():
    validate_setup()
    required = (
        "ELASTIC_CLOUD_API_KEY",
        "ELASTIC_CLOUD_REGION",
        "ELASTICSEARCH_VERSION"
    )
    for variable in required:
        if not env(variable):
            print("")
            print("You must set these variables in {} to setup ESS:".format(env("ENVFILE")))
            print("")
            for variable in required:
                print("  {}".format(variable))
            print("")
            sys.exit(1)

def run_setup_gke(dev=False):
    validate_setup_gke()
    print("")
    print("Creating GKE cluster...")
    cmd("""
    gcloud beta container clusters create 'ctb-$DEPLOYMENT_NAME' \
        --project "$GCP_PROJECT_NAME" \
        --region "$GCP_REGION_NAME" \
        --cluster-version 1.21.11-gke.1100 \
        --enable-ip-alias \
        --network "projects/$GCP_PROJECT_NAME/global/networks/$GCP_NETWORK_NAME" \
        --subnetwork "projects/$GCP_PROJECT_NAME/regions/$GCP_REGION_NAME/subnetworks/$GCP_SUBNETWORK_NAME" \
        --machine-type "e2-highcpu-8" \
        --image-type "COS" \
        --disk-size "32" \
        --disk-type "pd-ssd" \
        --metadata disable-legacy-endpoints=true \
        --service-account "$GCP_SERVICE_ACCOUNT_NAME" \
        --enable-autorepair \
        --enable-autoscaling \
        --no-enable-autoupgrade \
        --no-enable-basic-auth \
        --no-enable-master-authorized-networks \
        --num-nodes "1" \
        --min-nodes "1" \
        --max-nodes "1" \
        --default-max-pods-per-node "110" \
        --addons HorizontalPodAutoscaling,HttpLoadBalancing
    """)

    # Verify that the GKE cluster was created
    print("")
    print("Waiting for GKE cluster to be available...")
    sys.stdout.write("...")
    sys.stdout.flush()
    verified = False
    ready = False
    while not verified:
        if probe.status_gke():
            sys.stdout.write("ready.\n")
            sys.stdout.flush()
            ready = True
            verified = True
        else:
            time.sleep(4)
            sys.stdout.write(".")
            sys.stdout.flush()
    if not ready:
        sys.exit(1)

    # Install ECK
    print("")
    print("Installing ECK on GKE...")
    cmd("kubectl apply -f '{}/elasticsearch/all-in-one.yml'".format(env("BASEDIR")))

    # Deploy Elasticsearch for advertService
    print("")
    print("Deploying Elastisearch ads cluster on GKE...")
    cmd("kubectl apply -f '{}/elasticsearch/elasticsearch.yml'".format(env("BASEDIR")))

    # Wait for Elasticsearch to be available...
    print("")
    print("Waiting for Elasticsearch ads cluster external IP...")
    sys.stdout.write("...")
    sys.stdout.flush()
    ready = False
    es_ads_ip = ""
    while not ready:
        exitcode, out, err = cmd("kubectl get service elasticsearch-es-http -o json", stdout=False)
        if (err):
            # This error message is expected and will appear until the service is ready.
            if "NotFound" in err:
                time.sleep(4)
                sys.stdout.write(".")
                sys.stdout.flush()
                continue
            raise Exception(err)
        try:
            response = json.loads(out)
        except ValueError:
            time.sleep(4)
            sys.stdout.write(".")
            sys.stdout.flush()
            continue
        ingress = response.get("status", {}).get("loadBalancer", {}).get("ingress", [{}])
        ip = ingress[0].get("ip") if ingress else None
        if not ip:
            time.sleep(4)
            sys.stdout.write(".")
            sys.stdout.flush()
        else:
            es_ads_ip = ip
            sys.stdout.write("ready: {}\n".format(es_ads_ip))
            sys.stdout.flush()
            ready = True
    print("")
    print("Waiting for Elasticsearch ads cluster to be available in ~3 minutes...")
    sys.stdout.write("...")
    sys.stdout.flush()
    es_ads_url = "http://{}:9200".format(es_ads_ip)
    ready = False
    while not ready:
        try:
            response = requests.get(
                url="{}/_cat/health".format(es_ads_url),
                auth=("advertservice", "advertservice"),
                timeout=30
            )
            if "green 3" in response.content:
                print("ready.")
                ready = True
            else:
                time.sleep(4)
                sys.stdout.write(".")
                sys.stdout.flush()
        except Exception as e:
            time.sleep(4)
            sys.stdout.write(".")
            sys.stdout.flush()

    # Ensure ad data is indexed in Elasticsearch
    print("")
    print("Checking if data exists in Elasticsearch ads cluster...")
    response = requests.get(
        url="{}/ads/_search".format(es_ads_url),
        auth=("advertservice", "advertservice"),
        timeout=30
    )
    if response.json().get("hits", {}).get("total", {}).get("value") != 7:
        # Load ad data into Elasticsearch
        print("...ad data does not exist.")
        print("")
        print("Indexing ad data...")
        payload = utils.load_file(os.path.join(env("BASEDIR"), "elasticsearch", "bulk-ads.ndjson"))
        response = requests.post(
            url="{}/_bulk".format(es_ads_url),
            params={ "refresh": "true" },
            auth=("advertservice", "advertservice"),
            headers={ "Content-Type": "application/json" },
            data=payload,
            timeout=30
        )
        if response.json().get("errors") is False:
            print("...success.")
        else:
            print("...failure.")
            if response.status_code in range(400, 499):
                raise Exception(response.content)
            else:
                print(response.content)
    else:
        print("...exists.")

    # Start the stable scenario
    print("")
    print("Deploying the stable scenario on GKE.")
    ctb.commands.start.run("stable", quiet=True)

    print("")
    print("Finished setting up GKE.")


def run_setup_ess(dev=False):
    validate_setup_ess()

    # Check if deployment in .env file exists on ESS
    deployment_exists = False
    if env("ELASTIC_CLOUD_DEPLOYMENT_ID"):
        print("")
        print("Deployment ID found in .env file: '{}'".format(env("ELASTIC_CLOUD_DEPLOYMENT_ID")))
        print("")
        print("Checking if the deployment exists on ESS...")
        deployment_exists = probe.status_ess()
        if deployment_exists:
            print("...deployment exists on ESS: 'ctb-{}' [id={}]".format(env("DEPLOYMENT_NAME"), env("ELASTIC_CLOUD_DEPLOYMENT_ID")))
        else:
            print("...deployment does not exist on ESS. A new one will be created, and the .env file will be updated.")

    # Create deployment if it doesn't exist on ESS
    if not deployment_exists:
        print("")
        print("Creating ESS deployment...")
        filepath = os.path.join(env("BASEDIR"), "elasticsearch", "ess_template_create_deployment{}.json".format("_dev" if dev else ""))
        deployment_template = utils.load_template_json(filepath)
        response = requests.post(
            url="https://api.elastic-cloud.com/api/v1/deployments",
            headers=constants.ess_api_headers(),
            json=deployment_template,
            timeout=30
        )

        # Get deployment info
        if response.json().get("created") is True:
            print("...created: 'ctb-{}' [id={}]".format(env("DEPLOYMENT_NAME"), response.json().get("id")))

            # Get deployment info and update .env file
            os.environ["ELASTIC_CLOUD_DEPLOYMENT_ID"] = response.json().get("id")
            for resource in response.json().get("resources"):
                if resource.get("kind") == "elasticsearch":
                    os.environ["ELASTIC_CLOUD_ID"] = resource.get("cloud_id")
                    os.environ["ELASTICSEARCH_USERNAME"] = resource.get("credentials").get("username")
                    os.environ["ELASTICSEARCH_PASSWORD"] = resource.get("credentials").get("password")
                if resource.get("kind") == "apm":
                    os.environ["ELASTIC_APM_SECRET_TOKEN"] = resource.get("secret_token")
            utils.update_envfile()

            # Get endpoints and update .env file
            for component in ( "elasticsearch", "kibana", "apm" ):
                print("")
                print("Finding endpoint for {}...".format(component))
                found = False
                while not found:
                    response = requests.get(
                        url="https://api.elastic-cloud.com/api/v1/deployments/{}/{}/main-{}".format(env("ELASTIC_CLOUD_DEPLOYMENT_ID"), component, component),
                        headers=constants.ess_api_headers(),
                        timeout=30
                    )
                    url = response.json().get("info", {}).get("metadata", {}).get("service_url")
                    if url:
                        if component == "elasticsearch":
                            if not url[-1].isdigit():
                                url = url + ":443"
                            os.environ["ELASTICSEARCH_URL"] = url
                        elif component == "kibana":
                            os.environ["KIBANA_URL"] = url
                        elif component == "apm":
                            os.environ["ELASTIC_APM_SERVER_URL"] = url
                        print("...found: {}".format(url))
                        utils.update_envfile()
                        found = True
                    else:
                        time.sleep(1)

            print("")
            print("Your Elastic deployment will be ready in ~3 minutes.")
            print("")
            print("Kibana URL:         {}".format(env("KIBANA_URL")))
            print("Elasticsearch URL:  {}".format(env("ELASTICSEARCH_URL")))
            print("  - Username:       {}".format(env("ELASTICSEARCH_USERNAME")))
            print("  - Password:       {}".format(env("ELASTICSEARCH_PASSWORD")))
        else:
            print("...failure:")
            print(json.dumps(response.json(), indent=2, sort_keys=True))
            sys.exit(1)

    # Wait for Elasticsearch and Kibana to be available before
    # loading assets into Elasticsearch via Kibana.
    for component in ( "elasticsearch", "kibana" ):
        print("")
        print("Waiting for {} to be available...".format(component))
        sys.stdout.write("...")
        sys.stdout.flush()
        ready = False
        while not ready:
            is_available = probe.status_ess_component(component)
            if is_available:
                sys.stdout.write("ready.\n")
                sys.stdout.flush()
                ready = True
            else:
                time.sleep(4)
                sys.stdout.write(".")
                sys.stdout.flush()

    # Ensure operator role is indexed in Elasticsearch
    print("")
    print("Checking if operator role exists in Elasticsearch...")
    if not probe.status_ess_operator_role():
        print("...does not exist.")
        print("")
        print("Creating operator role...")
        payload = utils.load_template_json(os.path.join(env("BASEDIR"), "elasticsearch", "role-operator.json"))
        response_put = requests.put(
            url="{}/api/security/role/operator".format(env("KIBANA_URL")),
            headers=constants.kibana_api_headers(),
            json=payload,
            timeout=30
        )
        response_get = requests.get(
            url="{}/api/security/role/operator".format(env("KIBANA_URL")),
            headers=constants.kibana_api_headers(),
            timeout=30
        )
        if response_get.status_code == 200:
            print("...success.")
        else:
            print("...failure.")
            if response_put.status_code in range(400, 499):
                raise Exception(response_post.content)
            else:
                print(response_post.content)
    else:
        print("...exists.")

    # Ensure operator user is indexed in Elasticsearch
    print("")
    print("Checking if operator user exists in Elasticsearch...")
    if not probe.status_ess_operator_user():
        print("...does not exist.")
        print("")
        print("Creating operator user...")
        payload = utils.load_template_json(os.path.join(env("BASEDIR"), "elasticsearch", "user-operator.json"))
        response_post = requests.post(
            url="{}/internal/security/users/operator".format(env("KIBANA_URL")),
            headers=constants.kibana_api_headers(),
            json=payload,
            timeout=30
        )
        response_get = requests.get(
            url="{}/internal/security/users/operator".format(env("KIBANA_URL")),
            headers=constants.kibana_api_headers(),
            timeout=30
        )
        if response_get.status_code == 200:
            print("...success.")
        else:
            print("...failure.")
            if response_post.status_code in range(400, 499):
                raise Exception(response_post.content)
            else:
                print(response_post.content)
    else:
        print("...exists.")

    # Ensure Slack connector is indexed in Elasticsearch
    print("")
    print("Checking if Slack connector exists in Elasticsearch...")
    update = False
    if not probe.status_ess_slack_connector():
        print("...does not exist.")
        print("")
        print("Creating Slack connector...")
    else:
        update = True
        response = probe.get_ess_slack_connector()
        os.environ["SLACK_ACTION_ID"] = response.json()["hits"]["hits"][0]["_id"].split(":", 1)[1]
        print("...exists.")
        print("")
        print("Updating Slack connector...")
    payload = utils.load_template_json(os.path.join(env("BASEDIR"), "elasticsearch", "action-slack.json"))
    # Kibana does not want these fields when updating an alert
    if update:
        del payload["actionTypeId"]
    response_post = requests.request(
        method="post" if not update else "put",
        url="{}/api/actions/action{}".format(env("KIBANA_URL"), "" if not update else "/{}".format(os.environ["SLACK_ACTION_ID"])),
        headers=constants.kibana_api_headers(),
        json=payload,
        timeout=30
    )
    response_get = probe.get_ess_slack_connector()
    if response_post.status_code in range(200, 299) and response_get.json().get("hits", {}).get("total", {}).get("value") > 0:
        if not update:
            print("...created.")
        else:
            print("...updated.")
        os.environ["SLACK_ACTION_ID"] = response_get.json()["hits"]["hits"][0]["_id"].split(":", 1)[1]
    else:
        print("...failure.")
        if response_post.status_code in range(400, 499):
            raise Exception(response_post.content)
    if not update:
        response = probe.get_ess_slack_connector()
        os.environ["SLACK_ACTION_ID"] = response.json()["hits"]["hits"][0]["_id"].split(":", 1)[1]

    # Ensure Kibana alerts are indexed in Elasticsearch
    print("")
    print("Checking if Kibana alerts exist in Elasticsearch...")
    tasks = []
    num_processes = 0
    for service_id, service in constants.SERVICES.items():
        for alert_id in service["alerts"].keys():
            # TODO: There are duplicate monitors for downtime alerts.
            # TODO: Wait for throttling to work in synthetics alerts.
            if alert_id in ( "downtime", "synthetics-failures" ):
                continue
            tasks.append(( constants.ALERTS[alert_id], service ))
            num_processes += 1
    utils.parallel_tasks(alerts.create_kibana_alert, tasks, num_processes)

    # Ensure Watcher alerts are indexed in Elasticsearch
    print("")
    print("Checking if Watcher alerts exist in Elasticsearch...")
    attempts = 0
    max_attempts = 4
    verified = False
    response_put = None
    while not verified and attempts < max_attempts:
        try:
            response = requests.get(
                url="{}/_watcher/watch/no-purchases".format(env("ELASTICSEARCH_URL")),
                auth=(env("ELASTICSEARCH_USERNAME"), env("ELASTICSEARCH_PASSWORD")),
                timeout=30
            )
            update = False
            if response.json().get("found") is False:
                print("...creating alert: No Purchases")
            else:
                update = True
                print("...updating alert: No Purchases")
            os.environ["SERVICE_NAME"] = "frontend"
            os.environ["SERVICE_NAME_LOWERCASE"] = "frontend"
            os.environ["ALERT_MESSAGE_HEADER"] = utils.load_template(os.path.join(env("BASEDIR"), "elasticsearch", "alert-message-header.md"))
            os.environ["ALERT_MESSAGE_FOOTER"] = utils.load_template(os.path.join(env("BASEDIR"), "elasticsearch", "alert-message-footer.md"))
            os.environ["ALERT_MESSAGE"] = utils.load_template(os.path.join(env("BASEDIR"), "elasticsearch", "watcher-no-purchases-message.md")).replace("\n", "\\n")
            filename = os.path.join(env("BASEDIR"), "elasticsearch", "watcher-no-purchases.json")
            payload = utils.load_template_json(filename)
            response_put = requests.put(
                url="{}/_watcher/watch/no-purchases".format(env("ELASTICSEARCH_URL")),
                params={ "active": "false" },
                auth=(env("ELASTICSEARCH_USERNAME"), env("ELASTICSEARCH_PASSWORD")),
                json=payload,
                timeout=30
            )
            response_get = requests.get(
                url="{}/_watcher/watch/no-purchases".format(env("ELASTICSEARCH_URL")),
                auth=(env("ELASTICSEARCH_USERNAME"), env("ELASTICSEARCH_PASSWORD")),
                timeout=30
            )
            if response_put.status_code in range(200, 299) and response_get.json().get("found"):
                if not update:
                    print("......created: No Purchases")
                else:
                    print("......updated: No Purchases")
                verified = True
            else:
                print(response_post.content)
        except requests.exceptions.ReadTimeout:
            pass
        except Exception as e:
            print(e)
            traceback.print_exc()
        finally:
            attempts += 1
    if attempts >= max_attempts:
        print("......failure: No Purchases")
        if response_put and response_put.status_code in range(400, 499):
            print(response_put.content)

    print("")
    print("Finished setting up ESS.")

def run(ess=True, gke=True, dev=False):
    if ess:
        run_setup_ess(dev)
    if gke:
        run_setup_gke(dev)
    ctb.commands.endpoints.run()
