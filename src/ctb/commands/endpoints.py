#!/usr/bin/python
# coding: utf-8
"""
List the endpoints and credentials that are deployed on ESS and GKE.
"""


# Proprietary packages
from ctb.utils import env

def run():
    print("")
    print("Kibana URL:         {}".format(env("KIBANA_URL")))
    print("Elasticsearch URL:  {}".format(env("ELASTICSEARCH_URL")))
    print("  - Username:       {}".format(env("ELASTICSEARCH_USERNAME")))
    print("  - Password:       {}".format(env("ELASTICSEARCH_PASSWORD")))
    print("Frontend URL:       {}".format(env("FRONTEND_URL")))
    print("")
