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
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using cartservice.interfaces;
using Grpc.Core;
using Hipstershop;
using Elastic.Apm;
using Elastic.Apm.Api;
using static Hipstershop.CartService;
using Serilog;

namespace cartservice
{
    // Cart wrapper to deal with grpc communication
    internal class CartServiceImpl : CartServiceBase
    {
        private ICartStore cartStore;
        private readonly static Empty Empty = new Empty();

        public CartServiceImpl(ICartStore cartStore)
        {
            this.cartStore = cartStore;
        }
        private DistributedTracingData getDistributedTracingData(ServerCallContext context) {
            Metadata.Entry metadataEntry = context.RequestHeaders.FirstOrDefault(m => String.Equals(m.Key.ToLower(), "elastic-apm-traceparent", StringComparison.Ordinal));
            DistributedTracingData distributedTracingData = null;
            if (metadataEntry != null && !metadataEntry.Equals(default(Metadata.Entry)) && metadataEntry.Value != null) {
                distributedTracingData = DistributedTracingData.TryDeserializeFromString(metadataEntry.Value);
            }
            return distributedTracingData;
        }

        public async override Task<Empty> AddItem(AddItemRequest request, Grpc.Core.ServerCallContext context)
        {
            DistributedTracingData distributedTracingData = getDistributedTracingData(context);
            await Agent.Tracer.CaptureTransaction("AddItem", ApiConstants.TypeRequest, async (t) => {
                t.Labels["userId"] = request.UserId;
                t.Labels["productId"] = request.Item.ProductId;
                t.Labels["quantity"] = request.Item.Quantity.ToString();
                await cartStore.AddItemAsync(request.UserId, request.Item.ProductId, request.Item.Quantity);
            }, distributedTracingData);
            return Empty;
        }

        public async override Task<Empty> EmptyCart(EmptyCartRequest request, ServerCallContext context)
        {
            DistributedTracingData distributedTracingData = getDistributedTracingData(context);

            await Agent.Tracer.CaptureTransaction("EmptyCart", ApiConstants.TypeRequest, async (t) => {
                t.Labels["userId"] = request.UserId;
                await cartStore.EmptyCartAsync(request.UserId);
            }, distributedTracingData);
            return Empty;
        }

        public override Task<Hipstershop.Cart> GetCart(GetCartRequest request, ServerCallContext context)
        {
            DistributedTracingData distributedTracingData = getDistributedTracingData(context);

            return Agent.Tracer.CaptureTransaction("GetCart", ApiConstants.TypeRequest, (t) => {
                t.Labels["userId"] = request.UserId;
                return cartStore.GetCartAsync(request.UserId);
            }, distributedTracingData);
        }
    }
}