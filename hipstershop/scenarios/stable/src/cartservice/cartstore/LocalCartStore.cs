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

using System;
using System.Collections.Concurrent;
using System.Threading.Tasks;
using System.Linq;
using cartservice.interfaces;
using Hipstershop;
using Elastic.Apm.Api;
using Serilog;

namespace cartservice.cartstore
{
    internal class LocalCartStore : ICartStore
    {
        // Maps between user and their cart
        private ConcurrentDictionary<string, Hipstershop.Cart> userCartItems = new ConcurrentDictionary<string, Hipstershop.Cart>();
        private readonly Hipstershop.Cart emptyCart = new Hipstershop.Cart();

        public Task InitializeAsync()
        {
            Log.Information("Local Cart Store was initialized");

            return Task.CompletedTask;
        }

        public Task AddItemAsync(string userId, string productId, int quantity)
        {
            var transaction = Elastic.Apm.Agent.Tracer.CurrentTransaction;

            return transaction.CaptureSpan("AddItemAsync", ApiConstants.TypeDb, (s) =>
            {
                s.Labels["userId"] = userId;
                s.Labels["productId"] = productId;
                s.Labels["quantity"] = quantity.ToString();
                Log.Information("AddItemAsync called with userId={userId}, productId={productId}, quantity={quantity}", userId, productId, quantity);
                var newCart = new Hipstershop.Cart
                {
                    UserId = userId,
                    Items = { new Hipstershop.CartItem { ProductId = productId, Quantity = quantity } }
                };
                userCartItems.AddOrUpdate(userId, newCart,
                (k, exVal) =>
                {
                    // If the item exists, we update its quantity
                    var existingItem = exVal.Items.SingleOrDefault(item => item.ProductId == productId);
                    if (existingItem != null)
                    {
                        existingItem.Quantity += quantity;
                    }
                    else
                    {
                        exVal.Items.Add(new Hipstershop.CartItem { ProductId = productId, Quantity = quantity });
                    }

                    return exVal;
                });
                return Task.CompletedTask;
            });
            
        }

        public Task EmptyCartAsync(string userId)
        {
            var transaction = Elastic.Apm.Agent.Tracer.CurrentTransaction;
            return transaction.CaptureSpan("EmptyCartAsync", ApiConstants.TypeDb, (s) => {
                s.Labels["userId"] = userId;
                Log.Information("EmptyCartAsync called with userId={userId}", userId);
                userCartItems[userId] = emptyCart;
                return Task.CompletedTask;
            });
        }

        public Task<Hipstershop.Cart> GetCartAsync(string userId)
        {
            var transaction = Elastic.Apm.Agent.Tracer.CurrentTransaction;
            Hipstershop.Cart cart = null;
            return transaction.CaptureSpan("GetCartAsync", ApiConstants.TypeDb,  (s) => {
                Log.Information("GetCartAsync called with userId={userId}", userId);
                s.Labels["userId"] = userId;
                if (!userCartItems.TryGetValue(userId, out cart))
                {
                    Log.Warning("No carts for user {userId}", userId);
                    return Task.FromResult(emptyCart);
                }
                return Task.FromResult(cart);
            });
        }

        public bool Ping()
        {
            return true;
        }
    }
}