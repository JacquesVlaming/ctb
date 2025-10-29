#!/usr/bin/python
# coding: utf-8
"""
Constant values.
"""

# Standard packages
import base64
from typing import Optional, Dict
from ctb.utils import env
import re

# Proprietary packages
from ctb import utils


####  Alerts and services definitions  #########################################

ALERTS = {
    "downtime": {
        "id": "downtime",
        "name": "Downtime",
        "type": "xpack.uptime.alerts.monitorStatus"
    },
    "latency": {
        "id": "latency",
        "name": "High Latency",
        "type": "apm.transaction_duration"
    },
    "error-rate": {
        "id": "error-rate",
        "name": "High Error Rate",
        "type": "apm.error_rate"
    },
    "saturation-cpu": {
        "id": "saturation-cpu",
        "name": "CPU Saturation",
        "type": "metrics.alert.inventory.threshold+and+cpu"
    },
    "saturation-memory": {
        "id": "saturation-memory",
        "name": "Memory Saturation",
        "type": "metrics.alert.inventory.threshold+and+memory"
    },
    "synthetics-failures": {
        "id": "synthetics-failures",
        "name": "Synthetics Failures",
        "type": "xpack.uptime.alerts.monitorStatus"
    }
}
SERVICES = {
    "advertservice": {
        "id": "advertservice",
        "name": "advertService",
        "alerts": {
            "downtime": {
                "threshold": "5",
                "severity": "2"
            },
            "latency": {
                "threshold": "2000",
                "severity": "3"
            },
            "error-rate": {
                "threshold": "10",
                "severity": "4"
            },
            "saturation-cpu": {
                "threshold": "80",
                "severity": "4"
            },
            "saturation-memory": {
                "threshold": "80",
                "severity": "4"
            }
        }
    },
    "cartservice": {
        "id": "cartservice",
        "name": "cartService",
        "alerts": {
            "downtime": {
                "threshold": "5",
                "severity": "1"
            },
            "latency": {
                "threshold": "2000",
                "severity": "2"
            },
            "error-rate": {
                "threshold": "10",
                "severity": "3"
            },
            "saturation-cpu": {
                "threshold": "80",
                "severity": "3"
            },
            "saturation-memory": {
                "threshold": "80",
                "severity": "3"
            }
        }
    },
    "checkoutservice": {
        "id": "checkoutservice",
        "name": "checkoutService",
        "alerts": {
            "downtime": {
                "threshold": "5",
                "severity": "1"
            },
            "latency": {
                "threshold": "2000",
                "severity": "2"
            },
            "error-rate": {
                "threshold": "15",
                "severity": "3"
            },
            "saturation-cpu": {
                "threshold": "80",
                "severity": "3"
            },
            "saturation-memory": {
                "threshold": "80",
                "severity": "3"
            }
        }
    },
    "emailservice": {
        "id": "emailservice",
        "name": "emailService",
        "alerts": {
            "downtime": {
                "threshold": "5",
                "severity": "2"
            },
            "latency": {
                "threshold": "2000",
                "severity": "3"
            },
            "error-rate": {
                "threshold": "3",
                "severity": "4"
            },
            "saturation-cpu": {
                "threshold": "80",
                "severity": "4"
            },
            "saturation-memory": {
                "threshold": "80",
                "severity": "4"
            }
        }
    },
    "frontend": {
        "id": "frontend",
        "name": "frontend",
        "alerts": {
            "downtime": {
                "threshold": "5",
                "severity": "1"
            },
            "latency": {
                "threshold": "2000",
                "severity": "2"
            },
            "error-rate": {
                "threshold": "40",
                "severity": "3"
            },
            "saturation-cpu": {
                "threshold": "80",
                "severity": "3"
            },
            "saturation-memory": {
                "threshold": "80",
                "severity": "3"
            }
        }
    },
    "paymentservice": {
        "id": "paymentservice",
        "name": "paymentService",
        "alerts": {
            "downtime": {
                "threshold": "5",
                "severity": "1"
            },
            "latency": {
                "threshold": "2000",
                "severity": "2"
            },
            "error-rate": {
                "threshold": "10",
                "severity": "3"
            },
            "saturation-cpu": {
                "threshold": "80",
                "severity": "3"
            },
            "saturation-memory": {
                "threshold": "80",
                "severity": "3"
            }
        }
    },
    "productcatalogservice": {
        "id": "productcatalogservice",
        "name": "productCatalogService",
        "alerts": {
            "downtime": {
                "threshold": "5",
                "severity": "2"
            },
            "latency": {
                "threshold": "2000",
                "severity": "3"
            },
            "error-rate": {
                "threshold": "10",
                "severity": "3"
            },
            "saturation-cpu": {
                "threshold": "80",
                "severity": "3"
            },
            "saturation-memory": {
                "threshold": "80",
                "severity": "3"
            }
        }
    },
    "recommendationservice": {
        "id": "recommendationservice",
        "name": "recommendationService",
        "alerts": {
            "downtime": {
                "threshold": "5",
                "severity": "3"
            },
            "latency": {
                "threshold": "2000",
                "severity": "3"
            },
            "error-rate": {
                "threshold": "10",
                "severity": "4"
            },
            "saturation-cpu": {
                "threshold": "80",
                "severity": "4"
            },
            "saturation-memory": {
                "threshold": "80",
                "severity": "4"
            }
        }
    },
    "shippingservice": {
        "id": "shippingservice",
        "name": "shippingService",
        "alerts": {
            "downtime": {
                "threshold": "5",
                "severity": "1"
            },
            "latency": {
                "threshold": "2000",
                "severity": "2"
            },
            "error-rate": {
                "threshold": "10",
                "severity": "3"
            },
            "saturation-cpu": {
                "threshold": "80",
                "severity": "3"
            },
            "saturation-memory": {
                "threshold": "80",
                "severity": "3"
            }
        }
    },
    "synthetics-click-ad - inline": {
        "id": "synthetics-click-ad - inline",
        "name": "Click Ad",
        "alerts": {
            "synthetics-failures": {
                "threshold": "3",
                "severity": "2"
            }
        }
    },
    "synthetics-checkout - inline": {
        "id": "synthetics-checkout - inline",
        "name": "Checkout",
        "alerts": {
            "synthetics-failures": {
                "threshold": "3",
                "severity": "1"
            }
        }
    },
    "synthetics-view-home - inline": {
        "id": "synthetics-view-home - inline",
        "name": "View Home",
        "alerts": {
            "synthetics-failures": {
                "threshold": "3",
                "severity": "2"
            }
        }
    }
}


####  Message templates  #######################################################

SLACK_SCENARIO_START_MESSAGE = """
▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄

:warning:   *SCENARIO STARTED* - Get ready! We're rolling out a new issue. Expect alerts in a minute.
"""
SLACK_SCENARIO_END_MESSAGE = ":white_check_mark:   *SCENARIO DONE* - Hipster Shop is stable."


####  URLs and HTTP headers  ###################################################

ESS_API_URL_DEPLOYMENTS = "https://api.elastic-cloud.com/api/v1/deployments/{}"

def ess_api_headers(ess_api_key: Optional[str] = None) -> Dict[str, str]:
    """Return standard headers for Elastic Cloud (ESS) API calls."""
    api_key = ess_api_key or env("ELASTIC_CLOUD_API_KEY")
    return {
        "Authorization": f"ApiKey {api_key}"
    }


def kibana_api_headers(username: Optional[str] = None,
                       password: Optional[str] = None) -> Dict[str, str]:
    """Return standard headers for Kibana API calls."""
    user = username or env("ELASTICSEARCH_USERNAME")
    pw = password or env("ELASTICSEARCH_PASSWORD")

    credentials = f"{user}:{pw}".encode("utf-8")
    digest = base64.b64encode(credentials).decode("utf-8")

    return {
        "Authorization": f"Basic {digest}",
        "kbn-xsrf": "true"
    }

