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
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using cartservice.interfaces;
using Google.Protobuf;
using Grpc.Core;
using Hipstershop;
using StackExchange.Redis;
using Elastic.Apm.Api;
using Serilog;

namespace cartservice.cartstore
{
    public class RedisCartStore : ICartStore
    {
        private const string CART_FIELD_NAME = "cart";
        private const int REDIS_RETRY_NUM = 5;

        private volatile ConnectionMultiplexer redis;
        private volatile bool isRedisConnectionOpened = false;

        private readonly object locker = new object();
        private readonly byte[] emptyCartBytes;
        private readonly string connectionString;

        private readonly ConfigurationOptions redisConnectionOptions;

        public RedisCartStore(string redisAddress)
        {
            // Serialize empty cart into byte array.
            var cart = new Hipstershop.Cart();
            emptyCartBytes = cart.ToByteArray();
            connectionString = $"{redisAddress},ssl=false,allowAdmin=true,connectRetry=5";

            redisConnectionOptions = ConfigurationOptions.Parse(connectionString);

            // Try to reconnect if first retry failed (up to 5 times with exponential backoff)
            redisConnectionOptions.ConnectRetry = REDIS_RETRY_NUM;
            redisConnectionOptions.ReconnectRetryPolicy = new ExponentialRetry(100);

            redisConnectionOptions.KeepAlive = 30;
            redisConnectionOptions.ConnectTimeout = 2500;
        }

        public Task InitializeAsync()
        {
            Elastic.Apm.Agent.Tracer.CaptureTransaction("InitializeAsync", ApiConstants.TypeRequest, (t) => {
                t.CaptureSpan("EnsureRedisConnected", ApiConstants.TypeDb, span => {
                    EnsureRedisConnected();
                    return Task.CompletedTask;
                });
            });
            return Task.CompletedTask;
        }

        private void EnsureRedisConnected()
        {
            if (isRedisConnectionOpened)
            {
                return;
            }
            // Connection is closed or failed - open a new one but only at the first thread
            lock (locker)
            {
                if (isRedisConnectionOpened)
                {
                    return;
                }

                Log.Information("Connecting to Redis: {connectionString}", connectionString);
                redis = ConnectionMultiplexer.Connect(redisConnectionOptions);

                if (redis == null || !redis.IsConnected)
                {
                    Log.Error("Wasn't able to connect to redis");

                    // We weren't able to connect to redis despite 5 retries with exponential backoff
                    throw new ApplicationException("Wasn't able to connect to redis");
                }

                Log.Information("Successfully connected to Redis");
                var cache = redis.GetDatabase();

                Log.Information("Performing small test");
                cache.StringSet("cart", "OK" );
                object res = cache.StringGet("cart");
                Log.Information("Small test result: {res}", res);

                redis.InternalError += (o, e) => { Console.WriteLine(e.Exception); };
                redis.ConnectionRestored += (o, e) =>
                {
                    isRedisConnectionOpened = true;
                    Log.Information("Connection to redis was restored successfully");
                };
                redis.ConnectionFailed += (o, e) =>
                {
                    Log.Information("Connection failed. Disposing the object");
                    isRedisConnectionOpened = false;
                };

                isRedisConnectionOpened = true;
            }
        }

        public async Task AddItemAsync(string userId, string productId, int quantity)
        {
            Log.Information("AddItemAsync called with userId={userId}, productId={productId}, quantity={quantity}", userId, productId, quantity);
            var transaction = Elastic.Apm.Agent.Tracer.CurrentTransaction;
            ISpan span = transaction.StartSpan("AddItemAsync", ApiConstants.TypeDb, ApiConstants.ActionQuery);
            span.Labels["userId"] = userId;
            span.Labels["productId"] = productId;
            span.Labels["quantity"] = quantity.ToString();
            try
            {
                EnsureRedisConnected();

                var db = redis.GetDatabase();

                // Access the cart from the cache
                var value = await db.HashGetAsync(userId, CART_FIELD_NAME);

                Hipstershop.Cart cart;
                if (value.IsNull)
                {
                    cart = new Hipstershop.Cart();
                    cart.UserId = userId;
                    cart.Items.Add(new Hipstershop.CartItem { ProductId = productId, Quantity = quantity });
                }
                else
                {
                    cart = Hipstershop.Cart.Parser.ParseFrom(value);
                    var existingItem = cart.Items.SingleOrDefault(i => i.ProductId == productId);
                    if (existingItem == null)
                    {
                        cart.Items.Add(new Hipstershop.CartItem { ProductId = productId, Quantity = quantity });
                    }
                    else
                    {
                        existingItem.Quantity += quantity;
                    }
                }

                await db.HashSetAsync(userId, new[]{ new HashEntry(CART_FIELD_NAME, cart.ToByteArray()) });
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Can't access cart storage");
                span.CaptureException(ex);
                throw new RpcException(new Status(StatusCode.FailedPrecondition, $"Can't access cart storage. {ex}"));
            }
            finally {
                span.End();
            }
        }

        public async Task EmptyCartAsync(string userId)
        {
            Log.Information("EmptyCartAsync called with userId={userId}", userId);
            var transaction = Elastic.Apm.Agent.Tracer.CurrentTransaction;
            ISpan span = transaction.StartSpan("EmptyCartAsync", ApiConstants.TypeDb, ApiConstants.ActionQuery);
            span.Labels["userId"] = userId;
            try
            {
                EnsureRedisConnected();
                var db = redis.GetDatabase();

                // Update the cache with empty cart for given user
                await db.HashSetAsync(userId, new[] { new HashEntry(CART_FIELD_NAME, emptyCartBytes) });
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Can't access cart storage");
                span.CaptureException(ex);
                throw new RpcException(new Status(StatusCode.FailedPrecondition, $"Can't access cart storage. {ex}"));
            }
            finally {
                span.End();
            }
        }

        public async Task<Hipstershop.Cart> GetCartAsync(string userId)
        {
            Log.Information("GetCartAsync called with userId={userId}", userId);
            var transaction = Elastic.Apm.Agent.Tracer.CurrentTransaction;
            ISpan span = transaction.StartSpan("GetCartAsync", ApiConstants.TypeDb, ApiConstants.ActionQuery);
            span.Labels["userId"] = userId;
            try
            {
                EnsureRedisConnected();

                var db = redis.GetDatabase();

                // Access the cart from the cache
                var value = await db.HashGetAsync(userId, CART_FIELD_NAME);

                if (!value.IsNull)
                {
                    return Hipstershop.Cart.Parser.ParseFrom(value);
                }

                // We decided to return empty cart in cases when user wasn't in the cache before
                return new Hipstershop.Cart();
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Can't access cart storage");
                span.CaptureException(ex);
                throw new RpcException(new Status(StatusCode.FailedPrecondition, $"Can't access cart storage. {ex}"));
            }
            finally {
                span.End();
            }
        }

        public bool Ping()
        {
            var transaction = Elastic.Apm.Agent.Tracer.CurrentTransaction;
            ISpan span = transaction.StartSpan("GetCartAsync", ApiConstants.TypeDb, ApiConstants.ActionQuery);
            try
            {
                var cache = redis.GetDatabase();
                var res = cache.Ping();
                return res != TimeSpan.Zero;
            }
            catch (Exception ex)
            {
                span.CaptureException(ex);
                return false;
            }
            finally {
                span.End();
            }
        }
    }
}
