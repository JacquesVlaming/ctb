#!/usr/bin/python
# coding: utf-8
"""
List the scenarios that are available to deploy.
"""

# Standard packages
import os
import yaml

# Proprietary packages
import ctb.constants as constants
import ctb.utils as utils
import ctb.validate as validate
from ctb.utils import env


def run():
    scenarios = []
    conf = yaml.load(utils.load_file(os.path.join(env("BASEDIR"), "skaffold.yaml")), Loader=yaml.FullLoader)
    for profile in conf["profiles"]:
        scenarios.append(profile["name"])
    scenarios.sort()
    print("")
    for scenario in scenarios:
        print("  {}".format(scenario))
    print("")
