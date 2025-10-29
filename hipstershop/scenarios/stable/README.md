# Scenario: **stable**


This is the base scenario for Capture the Bug. It represents the stable state of the production environment, where everything runs as expected and desired. All other scenarios are modifications of this scenario.

This stable scenario starts automatically after creating the environment with the `./ctb setup` command.

After completing a scenario, the `./ctb stabilize` command will return the environment to this stable scenario.
