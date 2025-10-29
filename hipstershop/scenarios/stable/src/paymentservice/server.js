// Copyright 2018 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

const path = require('path');
const grpc = require('grpc');
const pino = require('pino');
const protoLoader = require('@grpc/proto-loader');

const logger = pino({
  name: 'paymentservice-server',
  timestamp: () => `,"@timestamp":"${Date.now()}"`,
  messageKey: 'message',
  changeLevelName: 'log.level',
  useLevelLabels: true,
  mixin () {
    return {
      "process.pid": process.pid,
      "event.dataset": process.env.ELASTIC_APM_SERVICE_NAME + ".log"
    }
  }
});

var apm = require('elastic-apm-node').start({
  serviceName: process.env.ELASTIC_APM_SERVICE_NAME,
  secretToken: process.env.ELASTIC_APM_SECRET_TOKEN,
  serverUrl: process.env.ELASTIC_APM_SERVER_URL,
})

const charge = require('./charge');

class HipsterShopServer {
  constructor (protoRoot, port = HipsterShopServer.PORT) {
    this.port = port;

    this.packages = {
      hipsterShop: this.loadProto(path.join(protoRoot, 'demo.proto')),
      health: this.loadProto(path.join(protoRoot, 'grpc/health/v1/health.proto'))
    };

    this.server = new grpc.Server();
    this.loadAllProtos(protoRoot);
  }

  /**
   * Handler for PaymentService.Charge.
   * @param {*} call  { ChargeRequest }
   * @param {*} callback  fn(err, ChargeResponse)
   */
  static ChargeServiceHandler (call, callback) {
    try {
      logger.info('Getting supported currencies...');
      const traceparents = call.metadata.get('elastic-apm-traceparent');
      var traceparent = null;
      if (traceparents.length > 0) {
        traceparent = traceparents[0];
      }
      var transaction = apm.startTransaction('/hipstershop.PaymentService/ChargeServiceHandler', 'request', { childOf: traceparent });
      const json_request = JSON.stringify(call.request);
      logger.info(`PaymentService#Charge invoked with request ${json_request}`);

      //apm.setCustomContext(json_request);
      transaction.addLabels({'request': json_request});
      const response = charge(call.request);
      transaction.addLabels({'response': JSON.stringify(response)});
      const { amount, credit_card: creditCard } = call.request;
      transaction.addLabels({'amount': amount.units, 'currency_code': amount.currency_code, 'charged': true });
      var span = transaction.startSpan('send_response', 'channel_write');
      callback(null, response);
      span.end()
      transaction.end('success')
    } catch (err) {
      logger.error(err);
      callback(err);
      apm.captureError(err);
      transaction.end('failure')
    }
  }

  static CheckHandler (call, callback) {
    var transaction = apm.startTransaction('/hipstershop.PaymentService/CheckHandler', 'request');
    callback(null, { status: 'SERVING' });
    transaction.end('success')
  }

  listen () {
    this.server.bind(`0.0.0.0:${this.port}`, grpc.ServerCredentials.createInsecure());
    logger.info(`PaymentService grpc server listening on 0.0.0.0:${this.port}`);
    this.server.start();
  }

  loadProto (path) {
    const packageDefinition = protoLoader.loadSync(
      path,
      {
        keepCase: true,
        longs: String,
        enums: String,
        defaults: true,
        oneofs: true
      }
    );
    return grpc.loadPackageDefinition(packageDefinition);
  }

  loadAllProtos (protoRoot) {
    const hipsterShopPackage = this.packages.hipsterShop.hipstershop;
    const healthPackage = this.packages.health.grpc.health.v1;

    this.server.addService(
      hipsterShopPackage.PaymentService.service,
      {
        charge: HipsterShopServer.ChargeServiceHandler.bind(this)
      }
    );

    this.server.addService(
      healthPackage.Health.service,
      {
        check: HipsterShopServer.CheckHandler.bind(this)
      }
    );
  }
}

HipsterShopServer.PORT = process.env.PORT;

module.exports = HipsterShopServer;
