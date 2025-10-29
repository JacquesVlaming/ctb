const path = require('path');
const grpc = require('grpc');
const pino = require('pino');

const PROTO_PATH = path.join(__dirname, './proto/demo.proto');
const PORT = 7000;

const shopProto = grpc.load(PROTO_PATH).hipstershop;
const client = new shopProto.PaymentService(`localhost:${PORT}`,
  grpc.credentials.createInsecure());


const logger = pino({
  name: 'paymentservice-client',
  messageKey: 'message',
  changeLevelName: 'severity',
  useLevelLabels: true
});

const request = {
  amount: {
    currency_code: 'CHF',
    units: 300,
    nanos: 0
  },
  credit_card: {
    credit_card_number: '4242-4242-4242-4242',
    credit_card_cvv: 123,
    credit_card_expiration_year: 2022,
    credit_card_expiration_month: 10
  }
};

client.charge(request, (err, response) => {
  if (err) {
    logger.error(`Error in charge: ${err}`);
  } else {
    logger.info(`Charge applied with transaction id: ${response.transaction_id}`);
  }
});

const invalid_card = {
  amount: {
    currency_code: 'CHF',
    units: 300,
    nanos: 0
  },
  credit_card: {
    credit_card_number: '1234242-4242-4242',
    credit_card_cvv: 123,
    credit_card_expiration_year: 2022,
    credit_card_expiration_month: 10
  }
};


client.charge(invalid_card, (err, response) => {
  if (err) {
    logger.error(`Error in charge: ${err}`);
  } else {
    logger.info(`Charge applied with transaction id: ${response.transaction_id}`);
  }
});

const expired_card = {
  amount: {
    currency_code: 'CHF',
    units: 300,
    nanos: 0
  },
  credit_card: {
    credit_card_number: '4242-4242-4242-4242',
    credit_card_cvv: 123,
    credit_card_expiration_year: 2016,
    credit_card_expiration_month: 10
  }
};


client.charge(expired_card, (err, response) => {
  if (err) {
    logger.error(`Error in charge: ${err}`);
  } else {
    logger.info(`Charge applied with transaction id: ${response.transaction_id}`);
  }
});
