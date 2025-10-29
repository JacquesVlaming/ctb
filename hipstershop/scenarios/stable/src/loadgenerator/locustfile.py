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
import json

from locust import HttpLocust, TaskSet
from faker import Faker

import random
from random import randint


def generate_card(type=None):
    """
    Prefill some values based on the card type
    """
    card_types = ["visa", "mastercard", "discover"]

    def prefill(t):
        # typical number of digits in credit card
        def_length = 16

        """
        Prefill with initial numbers and return it including the total number of digits
        remaining to fill
        """
        if t == card_types[0]:
            return [4], def_length - 1

        elif t == card_types[1]:
            # master card start with 5 and is 16 digits long
            return [5, randint(1, 5)], def_length - 2

        else:
            # this section probably not even needed here
            return [], def_length

    def finalize(nums):
        """
        Make the current generated list pass the Luhn check by checking and adding
        the last digit appropriately bia calculating the check sum
        """
        check_sum = 0

        # is_even = True if (len(nums) + 1 % 2) == 0 else False

        """
        Reason for this check offset is to figure out whther the final list is going
        to be even or odd which will affect calculating the check_sum.
        This is mainly also to avoid reversing the list back and forth which is specified
        on the Luhn algorithm.
        """
        check_offset = (len(nums) + 1) % 2

        for i, n in enumerate(nums):
            if (i + check_offset) % 2 == 0:
                n_ = n * 2
                check_sum += n_ - 9 if n_ > 9 else n_
            else:
                check_sum += n
        return nums + [10 - (check_sum % 10)]

    # main body
    if type:
        t = type.lower()
    else:
        t = random.choice(card_types)
    if t not in card_types:
        print
        "Unknown type: '%s'" % type
        print
        "Please pick one of these supported types: %s" % card_types
        return
    initial, rem = prefill(t)
    so_far = initial + [randint(1, 9) for x in range(rem - 1)]
    card =  "".join(map(str, finalize(so_far)))
    return '-'.join(card[i:i + 4] for i in range(0, len(card), 4))[0:19]

fake = Faker()

class UserBehavior(TaskSet):

    headers = {}

    def on_start(self):
        self.index()

    products = [
        '0PUK6V6EV0',
        '1YMWWN1N4O',
        '2ZYFJ3GM2N',
        '66VCHSJNUP',
        '6E92ZMYYFZ',
        '9SIQT8TOJO',
        'L9ECAV7KIM',
        'LS4PSXUNUM',
        'OLJCESPC7Z']

    def index(self):
        self.headers = {
            "X-Forwarded-For": fake.ipv4_public(),
            "User-Agent": fake.user_agent(),
        }
        return self.client.get("/", headers=self.headers)

    def setCurrency(self):
        currencies = ['EUR', 'USD', 'JPY', 'CAD']
        return self.client.post("/setCurrency",
                      {'currency_code': random.choice(currencies)}, headers=self.headers)

    def browseProduct(self):
        return self.client.get("/product/" + random.choice(self.products), headers=self.headers)

    def viewCart(self):
        return self.client.get("/cart", headers=self.headers)

    def addToCart(self):
        product = random.choice(self.products)
        response = self.client.get("/product/" + product, headers=self.headers, allow_redirects=True)
        if response and response.status_code in range (200, 299):
            return self.client.post("/cart", {
                'product_id': product,
                'quantity': random.choice([1, 2, 3, 4, 5, 10])}, headers=self.headers)

    def checkout(self):
        response = self.addToCart()
        if response and response.status_code in range(200, 299):
            body = {
                'email': fake.email(),
                'street_address': fake.street_address(),
                'zip_code': fake.postalcode(),
                'city': fake.city(),
                'state': fake.state(),
                'country': fake.country(),
                'credit_card_number': generate_card(type=random.choice(["visa", "mastercard"])),
                'credit_card_expiration_month': fake.credit_card_expire(start="now", end="+10y", date_format="%m"),
                'credit_card_expiration_year': fake.credit_card_expire(start="now", end="+10y", date_format="%Y"),
                'credit_card_cvv': fake.credit_card_security_code(),
            }
            return self.client.post("/cart/checkout", body, headers=self.headers)

    tasks = {
        index: 1,
        setCurrency: 1,
        browseProduct: 10,
        addToCart: 1,
        viewCart: 3,
        checkout: 1}

class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 500
    max_wait = 10000
