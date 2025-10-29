#!/usr/bin/python
#
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import grpc
import logging
import sys
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()
logHandler = logging.StreamHandler(stream=sys.stdout)
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

from observe.docker.emailservice import demo_pb2_grpc, demo_pb2

def send_confirmation_email(email, order):
  channel = grpc.insecure_channel('0.0.0.0:8080')
  stub = demo_pb2_grpc.EmailServiceStub(channel)
  try:
    response = stub.SendOrderConfirmation(demo_pb2.SendOrderConfirmationRequest(
      email = email,
      order = order
    ))
    logger.info('Request sent.')
  except grpc.RpcError as err:
    logger.error(err.details())
    logger.error('{}, {}'.format(err.code().name, err.code().value))



if __name__ == '__main__':
  logger.info('Client for email service.')
  send_confirmation_email('david.moore@elastic.co', {
    'order_id': '1',
    'shipping_tracking_id': '2',
    'shipping_cost': {
      'currency_code':'USD',
      'units': 1,
      'nanos':1
    },
    'shipping_address': {
      'street_address': 'Chamberlain Street',
      'city': 'Wells',
      'state': 'NY',
      'country': 'US',
      'zip_code': 10010
    },
    'items': [
      {
        'cost': {
          'currency_code':'USD',
          'units': 1,
          'nanos':1
        },
        'item': {
          'product_id': '11',
          'quantity': 2
        }
      }
    ]
  })
