# Scenarios

This directory contains scenarios for Capture the Bug.

A **scenario** is simulated issue that can be observed and solved with Elastic Observability. The issue could be a software bug, an infrastructure misconfiguration, a capacity deficiency, or anything else that could create problems in a production microservices application.

The **[stable](stable)** scenario has every service and monitoring agent used by the application (Hipster Shop). It was forked from the [Elastic Observability demo](https://github.com/elastic/demos/tree/master/observe) and is nearly identical to it.

All other scenarios introduce changes to the stable scenario. For example, the [traffic-spike](traffic-spike) scenario deploys a modified version of the loadgenerator service, and nothing else.


## Creating a new scenario

Directory structure:

```sh
/scenarios
  /SCENARIO_NAME
    /kubernetes-manifests
      /*.yaml
      /...
    /src
      /SERVICE_NAME
        /...
      /...
```

## Calling the new scenario

Scenarios are invoked by the `./ctb start SCENARIO_NAME` command. This command invokes a `./skaffold run` command that references a profile in `./skaffold.yaml`. To make a scenario callable, you must define a profile in `./skaffold.yaml`:

Here is an example of the `traffic-spike` scenario from `./skaffold.yaml`:

```yaml
- name: traffic-spike
  build:
    artifacts:
    - image: ctb-loadgenerator
      context: hipstershop/scenarios/stable/src/loadgenerator
  deploy:
    kubectl:
      manifests:
      - ./hipstershop/scenarios/traffic-spike/kubernetes-manifests/loadgenerator.yaml
```

The `name` field is what you invoke with `./ctb start SCENARIO_NAME`. Each build artifact points to a directory containing the complete source code for a service. These artifacts are build into Docker images and pushed to GCP. Image names should be prefixed with `ctb-` to prevent conflicts with other images on GCP.

The [traffic-spike](traffic-spike) example above uses the source code of loadgenerator from the [stable](stable) scenario, but it uses a new Kubernetes manifest file.
