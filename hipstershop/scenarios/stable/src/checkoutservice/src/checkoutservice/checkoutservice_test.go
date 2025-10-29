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

package main

import (
	"context"
	"go.elastic.co/apm"
	"go.elastic.co/apm/module/apmgrpc"
	"google.golang.org/grpc"
	"os"
	"testing"

	pb "github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/genproto"
)

func TestMain(m *testing.M) {
	// call flag.Parse() here if TestMain uses flags
	test_result := m.Run()
	apm.DefaultTracer.Flush(nil);
	os.Exit(test_result);
}

// TestGetQuote is a basic check on the GetQuote RPC service.
func TestPlaceOrder(t *testing.T) {
	addr := run("0")
	conn, err := grpc.Dial(addr,
		grpc.WithInsecure(),
		grpc.WithUnaryInterceptor(apmgrpc.NewUnaryClientInterceptor()))
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	tx := apm.DefaultTracer.StartTransaction("/hipstershop.CheckoutService/PlaceOrder", "request")
	ctx := apm.ContextWithTransaction(context.Background(), tx)
	client := pb.NewCheckoutServiceClient(conn)

	item := &pb.CartItem {
		ProductId: "OLJCESPC7Z",
		Quantity: 2,
	}
	cart_conn, cart_err := grpc.DialContext(ctx, os.Getenv("CART_SERVICE_ADDR"), grpc.WithInsecure(), grpc.WithUnaryInterceptor(apmgrpc.NewUnaryClientInterceptor()))
	if cart_err != nil {
		t.Errorf("could not connect cart service: %+v", cart_err)
		t.Fail()
	}
	//TODO: Clear cart first
	if _, cart_err =  pb.NewCartServiceClient(cart_conn).AddItem(ctx, &pb.AddItemRequest{ UserId: "1", Item: item }); cart_err != nil {
		t.Errorf("failed to add item to cart: %+v", cart_err)
		t.Fail()
	}

	// A basic test case to test logic and protobuf interactions.
	req := &pb.PlaceOrderRequest{
		UserId: "1",
		UserCurrency: "USD",
		Address: &pb.Address{
			StreetAddress: "Muffin Man",
			City:          "London",
			State:         "",
			Country:       "England",
		},
		Email: "dalem@elastic.co",
		CreditCard: &pb.CreditCardInfo{
			CreditCardNumber: "4242-4242-4242-4242",
			CreditCardCvv:          123,
			CreditCardExpirationYear:         2021,
			CreditCardExpirationMonth:       12,
		},
	}
	defer tx.End()
	res, err := client.PlaceOrder(ctx, req)

	if err != nil {
		t.Errorf("TestPlaceOrder (%v) failed", err)
	}
	t.Log(res)
}
