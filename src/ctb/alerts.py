#!/usr/bin/python
# coding: utf-8
"""
Kibana alerts management utils.
"""

# Standard packages
import base64
import hashlib
import os
import traceback

# Third-party packages
import requests

# Proprietary packages
from ctb import constants
from ctb import utils
from ctb.utils import env


def create_kibana_alert(task):
    """Pickable function to create a Kibana alert.
    Can be executed concurrently with a multiprocessing pool."""
    alert, service = task
    os.environ["SERVICE_NAME"] = service["name"]
    os.environ["SERVICE_NAME_LOWERCASE"] = service["name"].lower()
    alert_id = "7fdcfd30-9309-11eb-a1a7-{}".format(hashlib.sha1("{}-{}".format(alert["id"], service["id"])).hexdigest()[0:12])
    url_get = "{}/.kibana/_search?q=(type:alert+AND+{}+AND+{})".format(env("ELASTICSEARCH_URL"), alert["type"], os.environ["SERVICE_NAME_LOWERCASE"])
    url_post = "{}/api/alerts/alert/{}".format(env("KIBANA_URL"), alert_id)
    attempts = 0
    max_attempts = 4
    verified = False
    response_post = None
    while not verified and attempts < max_attempts:
        try:
            response = requests.get(
                url=url_get,
                auth=(env("ELASTICSEARCH_USERNAME"), env("ELASTICSEARCH_PASSWORD")),
                timeout=30
            )
            update = False
            if response.json().get("hits", {}).get("total", {}).get("value") == 0:
                print("...creating alert: {} - {}".format(alert["name"], service["name"]))
            else:
                update = True
                print("...updating alert: {} - {}".format(alert["name"], service["name"]))
            os.environ["THRESHOLD"] = service["alerts"][alert["id"]]["threshold"]
            os.environ["SEVERITY"] = service["alerts"][alert["id"]]["severity"]
            if alert["id"].startswith("synthetics"):
                os.environ["MONITOR_NAME"] = service["id"]
                os.environ["MONITOR_NAME_BASE64"] = base64.b64encode(service["id"].replace(" ", ""))
            os.environ["ALERT_MESSAGE_HEADER"] = utils.load_template(os.path.join(env("BASEDIR"), "elasticsearch", "alert-message-header.md"))
            os.environ["ALERT_MESSAGE_FOOTER"] = utils.load_template(os.path.join(env("BASEDIR"), "elasticsearch", "alert-message-footer.md"))
            os.environ["ALERT_MESSAGE"] = utils.load_template(os.path.join(env("BASEDIR"), "elasticsearch", "alert-{}-message.md".format(alert["id"]))).replace("\n", "\\n")
            filename = os.path.join(env("BASEDIR"), "elasticsearch", "alert-{}.json".format(alert["id"]))
            payload = utils.load_template_json(filename)
            # Kibana does not want these fields when updating an alert
            if update:
                del payload["alertTypeId"]
                del payload["enabled"]
                del payload["consumer"]
            # Handle typo in Metrics alerts prior to version 7.12.0
            if env("ELASTICSEARCH_VERSION") < "7.12.0" and alert["id"].startswith("saturation-"):
                payload["actions"][0]["group"] = "metrics.invenotry_threshold.fired"
            response_post = requests.request(
                method="post" if not update else "put",
                url=url_post,
                auth=(env("ELASTICSEARCH_USERNAME"), env("ELASTICSEARCH_PASSWORD")),
                headers=constants.kibana_api_headers(),
                json=payload,
                timeout=30
            )
            response_get = requests.get(
                url=url_get,
                auth=(env("ELASTICSEARCH_USERNAME"), env("ELASTICSEARCH_PASSWORD")),
                timeout=30
            )
            if response_post.status_code in range(200, 299) and response_get.json().get("hits", {}).get("total", {}).get("value") > 0:
                if not update:
                    print("......created: {} - {}".format(alert["name"], service["name"]))
                else:
                    print("......updated: {} - {}".format(alert["name"], service["name"]))
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
        print("......failure: {}-{}".format(alert["name"], service["name"]))

def toggle_kibana_alert(task):
    """Pickable function to enable or disable a Kibana alert.
    Can be executed concurrently with a multiprocessing pool."""
    alert, service, enable_or_disable = task
    os.environ["SERVICE_NAME"] = service["name"]
    os.environ["SERVICE_NAME_LOWERCASE"] = service["name"].lower()
    attempts = 0
    max_attempts = 4
    verified = False
    response_post = None
    while not verified and attempts < max_attempts:
        try:
            url_get = "{}/.kibana/_search?q=(type:alert+AND+{}+AND+{})".format(env("ELASTICSEARCH_URL"), alert["type"], os.environ["SERVICE_NAME_LOWERCASE"])
            response_get = requests.get(
                url=url_get,
                auth=(env("ELASTICSEARCH_USERNAME"), env("ELASTICSEARCH_PASSWORD")),
                timeout=30
            )
            hits = response_get.json().get("hits", {}).get("hits", [{}])
            alert_id = hits[0].get("_id") if hits else None
            if alert_id:
                alert_id = alert_id.split(":", 1)[1]
                verb = "enabling" if enable_or_disable == "enable" else "disabling"
                print("...{} alert: {} - {}".format(verb, alert["name"], service["name"]))
                url_post = "{}/api/alerts/alert/{}/_{}".format(env("KIBANA_URL"), alert_id, enable_or_disable)
                response_post = requests.post(
                    url=url_post,
                    auth=(env("ELASTICSEARCH_USERNAME"), env("ELASTICSEARCH_PASSWORD")),
                    headers=constants.kibana_api_headers(),
                    timeout=30
                )
                if response_post.status_code in range(200, 299):
                    print("......success: {} - {}".format(alert["name"], service["name"]))
                    verified = True
            else:
                print("...does not exist: {} - {}".format(alert["name"], service["name"]))
                verified = True
        except requests.exceptions.ReadTimeout:
            pass
        except Exception as e:
            print(e)
            traceback.print_exc()
        finally:
            attempts += 1
    if attempts >= max_attempts:
        print("......failure: {}-{}".format(alert["name"], service["name"]))
        if response_post and response_post.status_code in range(400, 499):
            print(response_post.content)

def toggle_all(enable_or_disable):

    # Enable or diable Kibana alerts
    tasks = []
    num_processes = 0
    for service_id, service in constants.SERVICES.items():
        for alert_id in service["alerts"].keys():
            # TODO: There are duplicate monitors for downtime alerts.
            # TODO: Wait for throttling to work in synthetics alerts.
            if alert_id in ( "downtime", "synthetics-failures" ):
                continue
            tasks.append(( constants.ALERTS[alert_id], service, enable_or_disable ))
            num_processes += 1
    utils.parallel_tasks(toggle_kibana_alert, tasks, num_processes)

    # Enable or disable Watcher alerts
    attempts = 0
    max_attempts = 4
    verified = False
    response_put = None
    while not verified and attempts < max_attempts:
        try:
            action = "_activate" if enable_or_disable == "enable" else "_deactivate"
            response_put = requests.put(
                url="{}/_watcher/watch/no-purchases/{}".format(env("ELASTICSEARCH_URL"), action),
                auth=(env("ELASTICSEARCH_USERNAME"), env("ELASTICSEARCH_PASSWORD")),
                timeout=30
            )
            if response_put.status_code == 404:
                print("...does not exist: No Purchases")
                verified = True
            else:
                verb = "enabling" if enable_or_disable == "enable" else "disabling"
                print("...{} alert: No Purchases".format(verb))
                status = response_put.json().get("status", {}).get("state", {}).get("active", {})
                if (status is True and enable_or_disable == "enable") or (status is False and enable_or_disable == "disable"):
                    print("......success: No Purchases")
                    verified = True
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
