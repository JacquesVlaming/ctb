#!/usr/bin/python
#
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import random
import time
import elasticapm
from concurrent import futures
import grpc
import sys
from elasticapm import Client
from elasticapm.conf import constants
from elasticapm.conf.constants import TRACEPARENT_HEADER_NAME
from elasticapm.utils.disttracing import TracingOptions, TraceParent
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc
import logging
import ecs_logging

from google.protobuf.json_format import MessageToDict

import demo_pb2
import demo_pb2_grpc

logger = logging.getLogger('emailService')
logHandler = logging.StreamHandler(stream=sys.stdout)
logHandler.setFormatter(ecs_logging.StdlibFormatter())
logger.addHandler(logHandler)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))
elasticapm.instrument()

event_dataset = None

def get_methods(object, spacing=20):
  methodList = []
  for method_name in dir(object):
    try:
        if callable(getattr(object, method_name)):
            methodList.append(str(method_name))
    except:
        methodList.append(str(method_name))
  processFunc = (lambda s: ' '.join(s.split())) or (lambda s: s)
  for method in methodList:
    try:
        print(str(method.ljust(spacing)) + ' ' +
              processFunc(str(getattr(object, method).__doc__)[0:90]))
    except:
        print(method.ljust(spacing) + ' ' + ' getattr() failed')

class RecommendationService(demo_pb2_grpc.RecommendationServiceServicer):


    def extract_trace_parent(self, context):
        trace_parent = None
        for key, value in context.invocation_metadata():
            if key.lower() == TRACEPARENT_HEADER_NAME:
                trace_parent = TraceParent.from_string(value)
        return trace_parent

    def ListRecommendations(self, request, context):
        # manually populate service map
        # this can be removed once 7.8 is out and the python agent adds this by itself
        product_catalog_destination_info = {
            "address": os.environ.get('PRODUCT_CATALOG_SERVICE_ADDR', ''),
            "port": int(os.environ.get('PORT', 8080)),
            "service": {
                "name": "grpc",
                "resource": os.environ.get('PRODUCT_CATALOG_SERVICE_ADDR', ''),
                "type": "external"
            },
        }

        trace_parent = self.extract_trace_parent(context)
        transaction = client.begin_transaction('request', trace_parent=trace_parent)
        request_dict = MessageToDict(request)
        elasticapm.label(**{'request': request_dict})
        max_responses = 5
        # fetch list of products from product catalog stub
        list_product_req = demo_pb2.Empty()
        with elasticapm.capture_span(
                '/hipstershop.ProductCatalogService/ListProducts',
                labels=MessageToDict(list_product_req),
                extra={"destination": product_catalog_destination_info}
        ) as span:
            trace_parent = transaction.trace_parent.copy_from(span_id=span.id, trace_options=TracingOptions(recorded=True))
            cat_response, call = product_catalog_stub.ListProducts.with_call(
                list_product_req,
                metadata=[
                    (constants.TRACEPARENT_HEADER_NAME, trace_parent.to_string())
                ]
            )
        with elasticapm.capture_span('CalculateRecommendations', span_subtype='grpc', span_action='calculate') as span:
            product_ids = [x.id for x in cat_response.products]
            filtered_products = list(set(product_ids)-set(request.product_ids))
            num_products = len(filtered_products)
            num_return = min(max_responses, num_products)
            # sample list of indicies to return
            indices = random.sample(range(num_products), num_return)
            # fetch product ids from indices
            prod_list = [filtered_products[i] for i in indices]
            logger.info('[Recv ListRecommendations] product_ids={}'.format(prod_list), extra= get_extra_logging_payload())
            # build and return response
        response = demo_pb2.ListRecommendationsResponse()
        response.product_ids.extend(prod_list)
        elasticapm.label(**{'response': MessageToDict(response) })
        elasticapm.set_custom_context({'request': request_dict, 'response': MessageToDict(response) })
        client.end_transaction('/hipstershop.RecommendationService/ListRecommendations', 'success')
        return response

    def Check(self, request, context):
        trace_parent = self.extract_trace_parent(context)
        client.begin_transaction('request', trace_parent=trace_parent)
        response = health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING)
        client.end_transaction('/hipstershop.RecommendationService/Check', 'success')
        return response

def get_extra_logging_payload():
  payload = { "transaction.id" : elasticapm.get_transaction_id(), "span.id" : elasticapm.get_span_id(), "trace.id" : elasticapm.get_trace_id(), "event.dataset": event_dataset}
  return payload

if __name__ == '__main__':
    defaults = { 'SERVICE_NAME': 'RecommendationServer' }
    event_dataset = defaults['SERVICE_NAME'] + ".log"
    logger.info('initializing recommendationservice', extra= get_extra_logging_payload())
    env = dict(os.environ)
    client = Client({apm_key.replace('ELASTIC_APM_', ''): env[apm_key] for apm_key in env if apm_key.startswith('ELASTIC_APM')}, **defaults)

    port = os.environ.get('PORT', '8080')
    catalog_addr = os.environ.get('PRODUCT_CATALOG_SERVICE_ADDR', '')
    if catalog_addr == '':
        raise Exception('PRODUCT_CATALOG_SERVICE_ADDR environment variable not set')
    logger.info('product catalog address: ' + catalog_addr, extra= get_extra_logging_payload())
    channel = grpc.insecure_channel(catalog_addr)
    product_catalog_stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)

    # create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # add class to gRPC server
    service = RecommendationService()
    demo_pb2_grpc.add_RecommendationServiceServicer_to_server(service, server)
    health_pb2_grpc.add_HealthServicer_to_server(service, server)

    # start server
    logger.info('listening on 0.0.0.0:' + port, extra= get_extra_logging_payload())
    server.add_insecure_port('[::]:'+port)
    server.start()

    server.wait_for_termination()
