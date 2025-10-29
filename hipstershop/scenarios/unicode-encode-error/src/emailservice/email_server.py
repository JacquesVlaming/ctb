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
from concurrent import futures
import os
import sys
import elasticapm
import grpc
import logging
import ecs_logging


import requests
from elasticapm import Client
from elasticapm.conf.constants import TRACEPARENT_HEADER_NAME
from elasticapm.utils.disttracing import TraceParent
from google.protobuf.json_format import MessageToDict
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateError
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc

import demo_pb2
import demo_pb2_grpc

logger = logging.getLogger('emailService')
logHandler = logging.StreamHandler(stream=sys.stdout)
logHandler.setFormatter(ecs_logging.StdlibFormatter())
logger.addHandler(logHandler)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))
elasticapm.instrument()
env = dict(os.environ)
client = Client( {apm_key.replace('ELASTIC_APM_', ''): env[apm_key] for apm_key in env if apm_key.startswith('ELASTIC_APM')}, **{'SERVICE_NAME': 'emailService'})

# Loads confirmation email template from file
env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape(['html', 'xml'])
)
template = env.get_template('confirmation.html')

event_dataset = None

class BaseEmailService(demo_pb2_grpc.EmailServiceServicer):

  def extract_trace_parent(self, context):
    trace_parent = None
    for key, value in context.invocation_metadata():
      if key.lower() == TRACEPARENT_HEADER_NAME:
        trace_parent = TraceParent.from_string(value)
    return trace_parent

  def Check(self, request, context):
      trace_parent = self.extract_trace_parent(context)
      client.begin_transaction('request', trace_parent=trace_parent)
      response = health_pb2.HealthCheckResponse(
          status=health_pb2.HealthCheckResponse.SERVING)
      client.end_transaction('/hipstershop.EmailService/Check', 'success')
      return response


  def send_email(self, email_address, content, send_mail):
    try:
      logger.info('A request to send order confirmation email to {} has been received.'.format(email_address), extra= get_extra_logging_payload())
      if send_mail:
        response = requests.post('https://api.mailgun.net/v3/%s/messages' % self.from_domain,
                                 auth=('api', self.mailgun_api_key),
                                 data={'from': self.from_address, 'to': [email_address], 'subject': 'Purchase confirmation', 'html': content })
        if response.status_code == 200:
          return
      else:
        return
    except Exception as me:
      raise EmailSendException('Mail send failed due to unknown error', me)
    raise EmailSendException(response.text)


  def SendEmail(self, request, context, send_mail=True):
    trace_parent = None
    for key, value in context.invocation_metadata():
      if key.lower() == TRACEPARENT_HEADER_NAME:
        trace_parent = TraceParent.from_string(value)
    tx = client.begin_transaction('request', trace_parent=trace_parent)

    tx.ensure_parent_id()

    request_dict = MessageToDict(request)
    elasticapm.label(**{'request': request_dict})
    elasticapm.set_custom_context({'request': request_dict, 'response': MessageToDict(demo_pb2.Empty())})
    email = request.email
    order = request.order
    parent_id = trace_parent.span_id

    span = tx._begin_span('template.render', None, parent_span_id=parent_id)

    try:
      def encode(value):
        return str(bytes(value, 'ascii'), 'utf8')
      street_address = encode(order.shipping_address.street_address)
      city = encode(order.shipping_address.city)
      state = encode(order.shipping_address.state)
      country = encode(order.shipping_address.country)
      confirmation = template.render(order=order)
      span.end()
    except Exception as err:
      client.capture_exception(context=request_dict, handled=True)
      context.set_details('An error occurred when preparing the confirmation mail.')
      logger.error(err.message, extra= default_fields)
      context.set_code(grpc.StatusCode.INTERNAL)
      span.end()
      client.end_transaction('/hipstershop.EmailService/SendOrderConfirmation', 'failure')
      return demo_pb2.Empty()

    span = tx._begin_span('send_email', None, parent_span_id=parent_id)
    try:
      self.send_email(email, confirmation, send_mail)
      span.end()
    except EmailSendException as err:
      client.capture_exception(context=request_dict, handled=True)
      context.set_details('An error occurred when sending the email.')
      logger.error('Failed to send email to %s' % email, extra= get_extra_logging_payload())
      logger.error(err.message, extra= get_extra_logging_payload())
      context.set_code(grpc.StatusCode.INTERNAL)
      span.end()
      client.end_transaction('/hipstershop.EmailService/SendOrderConfirmation', 'failure')
      return demo_pb2.Empty()
    elasticapm.label(**{'response': MessageToDict(demo_pb2.Empty())})
    client.end_transaction('/hipstershop.EmailService/SendOrderConfirmation', 'success')
    return demo_pb2.Empty()


class EmailSendException(Exception):

    def __init__(self, message, cause=None):
      super(EmailSendException, self).__init__(message)
      self.message = message
      self.cause = cause
      self.error_code = 400

class EmailService(BaseEmailService):

  def __init__(self, from_domain, from_address, mailgun_api_key):
    self.from_domain = from_domain
    self.mailgun_api_key = mailgun_api_key
    self.from_address = from_address
    super().__init__()

  def SendOrderConfirmation(self, request, context):
    return self.SendEmail(request, context)

class DummyEmailService(BaseEmailService):

  def SendOrderConfirmation(self, request, context):
    return self.SendEmail(request, context, send_mail=False)


class HealthCheck():
  def Check(self, request, context):
    return health_pb2.HealthCheckResponse(
      status=health_pb2.HealthCheckResponse.SERVING)

def missing_env_var(var, tx):
  logger.error('Environment variable %s must be been defined' % var, extra = get_extra_logging_payload())
  sys.exit(1)

def get_extra_logging_payload():
  payload = { "transaction.id" : elasticapm.get_transaction_id(), "span.id" : elasticapm.get_span_id(), "trace.id" : elasticapm.get_trace_id(), "event.dataset": event_dataset}
  return payload

def start(dummy_mode):
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
  service_name = os.environ.get('ELASTIC_APM_SERVICE_NAME') or missing_env_var('ELASTIC_APM_SERVICE_NAME')
  event_dataset = os.environ.get('ELASTIC_APM_SERVICE_NAME') + ".log"

  mailgun_domain = os.environ.get('MAILGUN_DOMAIN') or missing_env_var('MAILGUN_DOMAIN')
  mailgun_key = os.environ.get('MAILGUN_API_KEY') or missing_env_var('MAILGUN_API_KEY')
  from_email = os.environ.get('FROM_EMAIL') or missing_env_var('FROM_EMAIL')
  if dummy_mode:
    service = DummyEmailService()
  else:
    service = EmailService(mailgun_domain, from_email, mailgun_key)
  demo_pb2_grpc.add_EmailServiceServicer_to_server(service, server)
  health_pb2_grpc.add_HealthServicer_to_server(service, server)

  port = os.environ.get('PORT', '8080')
  logger.info('listening on 0.0.0.0:'+port, extra= get_extra_logging_payload())
  server.add_insecure_port('[::]:'+port)
  server.start()
  server.wait_for_termination()

if __name__ == '__main__':
  dummy_mode = False if os.environ.get('DUMMY_MODE', 'False').lower() == 'false' else True
  logger.info('starting the email service in %s mode.' % ('dummy' if dummy_mode else 'full' ), extra= get_extra_logging_payload())
  start(dummy_mode)
