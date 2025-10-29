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
	"fmt"
	"go.elastic.co/apm"
	"html/template"
	"math/rand"
	"net/http"
	"net/url"
	"os"
	"strconv"
  "strings"
	"testing"
	"time"

	"github.com/gorilla/mux"
	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"

	pb "github.com/GoogleCloudPlatform/microservices-demo/src/frontend/genproto"
	"github.com/GoogleCloudPlatform/microservices-demo/src/frontend/money"
)

var (
	templates = template.Must(template.New("").
		Funcs(template.FuncMap{
			"renderMoney": renderMoney,
		}).ParseGlob("templates/*.html"))
)

func TestMain(m *testing.M) {
	// call flag.Parse() here if TestMain uses flags
	test_result := m.Run()
	apm.DefaultTracer.Flush(nil);
	os.Exit(test_result);
}

func (fe *frontendServer) homeHandler(w http.ResponseWriter, r *http.Request) {
	tx := apm.DefaultTracer.StartTransaction("homeHandler", "request")
	tx.Context.SetTag("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetCustom("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetTag("user_agent", r.Header.Get("User-Agent"))
	ctx := apm.ContextWithTransaction(r.Context(), tx)
	defer tx.End()
	log := ctx.Value(ctxKeyLog{}).(logrus.FieldLogger)

	span, ctx := apm.StartSpan(ctx, "currentCurrency", "request")
	log.WithField("currency", currentCurrency(r)).Info("home")
	currencies, err := fe.getCurrencies(ctx)
	if err != nil {
		renderHTTPError(log, r, w, errors.Wrap(err, "could not retrieve currencies"), http.StatusInternalServerError)
		e := apm.CaptureError(ctx, err)
		e.SetSpan(span)
		e.Send()
		span.End()
		return
	}
	span.End()
	p_span, ctx := apm.StartSpan(ctx, "getProducts", "request")
	products, err := fe.getProducts(ctx)
	if err != nil {
		renderHTTPError(log, r, w, errors.Wrap(err, "could not retrieve products"), http.StatusInternalServerError)
		e := apm.CaptureError(ctx, err)
		e.SetSpan(p_span)
		e.Send()
		p_span.End()
		return
	}
	p_span.End()

	c_span, ctx := apm.StartSpan(ctx, "getCart", "request")
	cart, err := fe.getCart(ctx, sessionID(r))
	if err != nil {
		e := apm.CaptureError(ctx, err)
		e.SetSpan(c_span)
		e.Send()
		c_span.End()
		renderHTTPError(log, r, w, errors.Wrap(err, "could not retrieve cart"), http.StatusInternalServerError)
		return
	}
	c_span.End()

	type productView struct {
		Item  *pb.Product
		Price *pb.Money
	}
	ps := make([]productView, len(products))
	for i, p := range products {
		pr_span, ctx := apm.StartSpan(ctx, "priceProducts", "request")
		price, err := fe.convertCurrency(ctx, p.GetPriceUsd(), currentCurrency(r))
		if err != nil {
			e := apm.CaptureError(ctx, err)
			e.SetSpan(pr_span)
			e.Send()
			pr_span.End()
			renderHTTPError(log, r, w, errors.Wrapf(err, "failed to do currency conversion for product %s", p.GetId()), http.StatusInternalServerError)
			return
		}
		ps[i] = productView{p, price}
		pr_span.End()
	}
	ads := fe.chooseAd(ctx, []string{}, log)

	re_span, ctx := apm.StartSpan(ctx, "ExecuteTemplate", "request")

	err = templates.ExecuteTemplate(w, "home", map[string]interface{}{
    "elastic_apm_server_url": os.Getenv("ELASTIC_APM_SERVER_URLS"),
		"session_id":    sessionID(r),
		"request_id":    ctx.Value(ctxKeyRequestID{}),
		"user_currency": currentCurrency(r),
		"currencies":    currencies,
		"products":      ps,
		"cart_size":     len(cart),
		"banner_color":  os.Getenv("BANNER_COLOR"), // illustrates canary deployments
		"ad":           ads,
	});
	if err != nil {
		e := apm.CaptureError(ctx, err)
		e.SetSpan(re_span)
		e.Send()
		log.Error(err)
	}
	re_span.End()
}

func (fe *frontendServer) productHandler(w http.ResponseWriter, r *http.Request) {
	tx := apm.DefaultTracer.StartTransaction("productHandler", "request")
	tx.Context.SetTag("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetCustom("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetTag("user_agent", r.Header.Get("User-Agent"))
	ctx := apm.ContextWithTransaction(r.Context(), tx)
	defer tx.End()

	log := ctx.Value(ctxKeyLog{}).(logrus.FieldLogger)
	id := mux.Vars(r)["id"]
	if id == "" {
		err := errors.New("product id not specified")
		renderHTTPError(log, r, w, err, http.StatusBadRequest)
		e := apm.DefaultTracer.NewError(err)
		e.Send()
		return
	}
  if (!strings.Contains(r.URL.String(), "sid=")) {
    newUrl := "/product/" + mux.Vars(r)["id"] + "?#session_id=" + sessionID(r)
    log.Debug("redirecting to session-tracked url: " + newUrl)
    w.Header().Set("Location", newUrl)
    w.WriteHeader(http.StatusFound)
    return
  }
	log.WithField("id", id).WithField("currency", currentCurrency(r)).
		Debug("serving product page")
	span, ctx := apm.StartSpan(ctx, "getProduct", "request")
	p, err := fe.getProduct(ctx, id)
	if err != nil {
		renderHTTPError(log, r, w, errors.Wrap(err, "could not retrieve product"), http.StatusInternalServerError)
		e := apm.CaptureError(ctx, err)
		e.SetSpan(span)
		e.Send()
		span.End()
		return
	}
	span.End()

	c_span, ctx := apm.StartSpan(ctx, "getCurrencies", "request")
	currencies, err := fe.getCurrencies(ctx)
	if err != nil {
		e := apm.CaptureError(ctx, err)
		e.SetSpan(c_span)
		e.Send()
		c_span.End()
		renderHTTPError(log, r, w, errors.Wrap(err, "could not retrieve currencies"), http.StatusInternalServerError)
		return
	}
	c_span.End()

	ca_span, ctx := apm.StartSpan(ctx, "getCart", "request")
	cart, err := fe.getCart(ctx, sessionID(r))
	if err != nil {
		e := apm.CaptureError(ctx, err)
		e.SetSpan(ca_span)
		e.Send()
		ca_span.End()
		renderHTTPError(log, r, w, errors.Wrap(err, "could not retrieve cart"), http.StatusInternalServerError)
		return
	}
	ca_span.End()

	co_span, ctx := apm.StartSpan(ctx, "convertCurrency", "request")
	price, err := fe.convertCurrency(ctx, p.GetPriceUsd(), currentCurrency(r))
	if err != nil {
		e := apm.CaptureError(ctx, err)
		e.SetSpan(co_span)
		e.Send()
		co_span.End()
		renderHTTPError(log, r, w, errors.Wrap(err, "failed to convert currency"), http.StatusInternalServerError)
		return
	}
	co_span.End()

	r_span, ctx := apm.StartSpan(ctx, "convertCurrency", "request")
	recommendations, err := fe.getRecommendations(ctx, sessionID(r), []string{id})
	if err != nil {
		e := apm.CaptureError(ctx, err)
		e.SetSpan(r_span)
		e.Send()
		r_span.End()
		renderHTTPError(log, r, w, errors.Wrap(err, "failed to get product recommendations"), http.StatusInternalServerError)
		return
	}
	r_span.End()

	product := struct {
		Item  *pb.Product
		Price *pb.Money
	}{p, price}

	ads := fe.chooseAd(ctx, p.GetCategories(), log)

	re_span, ctx := apm.StartSpan(ctx, "ExecuteTemplate", "request")
	err = templates.ExecuteTemplate(w, "product", map[string]interface{}{
    "elastic_apm_server_url": os.Getenv("ELASTIC_APM_SERVER_URLS"),
		"session_id":      sessionID(r),
		"request_id":      ctx.Value(ctxKeyRequestID{}),
		"ad":              ads,
		"user_currency":   currentCurrency(r),
		"currencies":      currencies,
		"product":         product,
		"recommendations": recommendations,
		"cart_size":       len(cart),
	});
	if err != nil {
		e := apm.CaptureError(ctx, err)
		e.SetSpan(re_span)
		e.Send()
		log.Error(err)
	}
	re_span.End()
}

func (fe *frontendServer) addToCartHandler(w http.ResponseWriter, r *http.Request) {
	tx := apm.DefaultTracer.StartTransaction("addToCartHandler", "request")
	tx.Context.SetTag("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetCustom("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetTag("user_agent", r.Header.Get("User-Agent"))
	ctx := apm.ContextWithTransaction(r.Context(), tx)
	defer tx.End()
	log := ctx.Value(ctxKeyLog{}).(logrus.FieldLogger)
	quantity, _ := strconv.ParseUint(r.FormValue("quantity"), 10, 32)
	productID := r.FormValue("product_id")
	if productID == "" || quantity == 0 {
		err := errors.New("invalid form input")
		e := apm.DefaultTracer.NewError(err)
		renderHTTPError(log, r, w, err, http.StatusBadRequest)
		e.Send()
		return
	}
	log.WithField("product", productID).WithField("quantity", quantity).Debug("adding to cart")
	span, ctx := apm.StartSpan(ctx, "getProduct", "request")
	p, err := fe.getProduct(ctx, productID)
	if err != nil {
		renderHTTPError(log, r, w, errors.Wrap(err, "could not retrieve product"), http.StatusInternalServerError)
		e := apm.CaptureError(ctx, err)
		e.SetSpan(span)
		e.Send()
		span.End()
		return
	}
	span.End()
	i_span, ctx := apm.StartSpan(ctx, "insertCart", "request")
	if err := fe.insertCart(ctx, sessionID(r), p.GetId(), int32(quantity)); err != nil {
		renderHTTPError(log, r, w, errors.Wrap(err, "failed to add to cart"), http.StatusInternalServerError)
		e := apm.CaptureError(ctx, err)
		e.SetSpan(i_span)
		e.Send()
		i_span.End()
		return
	}
	i_span.End()

	w.Header().Set("location", "/cart")
	w.WriteHeader(http.StatusFound)
}

func (fe *frontendServer) emptyCartHandler(w http.ResponseWriter, r *http.Request) {
	tx := apm.DefaultTracer.StartTransaction("emptyCartHandler", "request")
	tx.Context.SetTag("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetCustom("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetTag("user_agent", r.Header.Get("User-Agent"))
	ctx := apm.ContextWithTransaction(r.Context(), tx)
	log := ctx.Value(ctxKeyLog{}).(logrus.FieldLogger)
	defer tx.End()
	log.Debug("emptying cart")
	span, ctx := apm.StartSpan(ctx, "emptyCart", "request")
	if err := fe.emptyCart(ctx, sessionID(r)); err != nil {
		renderHTTPError(log, r, w, errors.Wrap(err, "failed to empty cart"), http.StatusInternalServerError)
		e := apm.CaptureError(ctx, err)
		e.SetSpan(span)
		e.Send()
		span.End()
		return
	}
	span.End()

	w.Header().Set("location", "/")
	w.WriteHeader(http.StatusFound)
}

func (fe *frontendServer) viewCartHandler(w http.ResponseWriter, r *http.Request) {
	tx := apm.DefaultTracer.StartTransaction("viewCartHandler", "request")
	ctx := apm.ContextWithTransaction(r.Context(), tx)

	log := ctx.Value(ctxKeyLog{}).(logrus.FieldLogger)
	log.Debug("view user cart")
	tx.Context.SetTag("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetCustom("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetTag("user_agent", r.Header.Get("User-Agent"))
	defer tx.End()
	span, ctx := apm.StartSpan(ctx, "getCurrencies", "request")
	currencies, err := fe.getCurrencies(ctx)
	if err != nil {
		renderHTTPError(log, r, w, errors.Wrap(err, "could not retrieve currencies"), http.StatusInternalServerError)
		e := apm.CaptureError(ctx, err)
		e.SetSpan(span)
		e.Send()
		span.End()
		return
	}
	span.End()
	c_span, ctx := apm.StartSpan(ctx, "getCart", "request")
	cart, err := fe.getCart(ctx, sessionID(r))
	if err != nil {
		renderHTTPError(log, r, w, errors.Wrap(err, "could not retrieve cart"), http.StatusInternalServerError)
		e := apm.CaptureError(ctx, err)
		e.SetSpan(c_span)
		e.Send()
		c_span.End()
		return
	}
	c_span.End()
	r_span, ctx := apm.StartSpan(ctx, "getRecommendations", "request")
	recommendations, err := fe.getRecommendations(ctx, sessionID(r), cartIDs(cart))
	if err != nil {
		renderHTTPError(log, r, w, errors.Wrap(err, "failed to get product recommendations"), http.StatusInternalServerError)
		e := apm.CaptureError(ctx, err)
		e.SetSpan(r_span)
		e.Send()
		r_span.End()

		return
	}
	r_span.End()

	s_span, ctx := apm.StartSpan(ctx, "getRecommendations", "request")
	shippingCost, err := fe.getShippingQuote(ctx, cart, currentCurrency(r))
	if err != nil {
		renderHTTPError(log, r, w, errors.Wrap(err, "failed to get shipping quote"), http.StatusInternalServerError)
		e := apm.CaptureError(ctx, err)
		e.SetSpan(s_span)
		e.Send()
		s_span.End()
		return
	}
	s_span.End()

	type cartItemView struct {
		Item	 *pb.Product
		Quantity int32
		Price    *pb.Money
	}
	items := make([]cartItemView, len(cart))
	totalPrice := pb.Money{CurrencyCode: currentCurrency(r)}
	for i, item := range cart {
		p_span, ctx := apm.StartSpan(ctx, "processItem", "external")
		p_span.Subtype = "grpc"
		p_span.Context.SetDestinationService( apm.DestinationServiceSpanContext{ Name: p_span.Subtype, Resource: fe.productCatalogSvcAddr } )
		addr, err := url.Parse(fe.productCatalogSvcAddr)
		port, err := strconv.Atoi(addr.Port())
		p_span.Context.SetDestinationAddress( addr.Host, port)
		p, err := fe.getProduct(ctx, item.GetProductId())
		if err != nil {
			e := apm.CaptureError(ctx, err)
			e.SetSpan(p_span)
			e.Send()
			p_span.End()
			renderHTTPError(log, r, w, errors.Wrapf(err, "could not retrieve product #%s", item.GetProductId()), http.StatusInternalServerError)
			return
		}
		price, err := fe.convertCurrency(ctx, p.GetPriceUsd(), currentCurrency(r))
		if err != nil {
			e := apm.CaptureError(ctx, err)
			e.SetSpan(p_span)
			e.Send()
			p_span.End()
			renderHTTPError(log, r, w, errors.Wrapf(err, "could not convert currency for product #%s", item.GetProductId()), http.StatusInternalServerError)
			return
		}

		multPrice := money.MultiplySlow(*price, uint32(item.GetQuantity()))
		items[i] = cartItemView{
			Item:     p,
			Quantity: item.GetQuantity(),
			Price:    &multPrice}
		totalPrice = money.Must(money.Sum(totalPrice, multPrice))
		p_span.End()
	}
	totalPrice = money.Must(money.Sum(totalPrice, *shippingCost))

	year := time.Now().Year()
	re_span, ctx := apm.StartSpan(ctx, "ExecuteTemplate", "request")
	defer re_span.End()

	if err := templates.ExecuteTemplate(w, "cart", map[string]interface{}{
    "elastic_apm_server_url": os.Getenv("ELASTIC_APM_SERVER_URLS"),
		"session_id":       sessionID(r),
		"request_id":       ctx.Value(ctxKeyRequestID{}),
		"user_currency":    currentCurrency(r),
		"currencies":       currencies,
		"recommendations":  recommendations,
		"cart_size":        len(cart),
		"shipping_cost":    shippingCost,
		"total_cost":       totalPrice,
		"items":            items,
		"expiration_years": []int{year, year + 1, year + 2, year + 3, year + 4},
	}); err != nil {
		e := apm.CaptureError(ctx, err)
		e.SetSpan(re_span)
		e.Send()
		log.Println(err)
	}
}

func (fe *frontendServer) placeOrderHandler(w http.ResponseWriter, r *http.Request) {
	tx := apm.DefaultTracer.StartTransaction("placeOrderHandler", "request")
	ctx := apm.ContextWithTransaction(r.Context(), tx)
	log := ctx.Value(ctxKeyLog{}).(logrus.FieldLogger)
	log.Debug("placing order")
	defer tx.End()
	var (
		email         = r.FormValue("email")
		streetAddress = r.FormValue("street_address")
		zipCode, _    = strconv.ParseInt(r.FormValue("zip_code"), 10, 32)
		city          = r.FormValue("city")
		state         = r.FormValue("state")
		country       = r.FormValue("country")
		ccNumber      = r.FormValue("credit_card_number")
		ccMonth, _    = strconv.ParseInt(r.FormValue("credit_card_expiration_month"), 10, 32)
		ccYear, _     = strconv.ParseInt(r.FormValue("credit_card_expiration_year"), 10, 32)
		ccCVV, _      = strconv.ParseInt(r.FormValue("credit_card_cvv"), 10, 32)
	)

	tx.Context.SetTag("email", email)
	tx.Context.SetTag("city", city)
	tx.Context.SetTag("street_address", streetAddress)
	tx.Context.SetTag("state", state)
	tx.Context.SetTag("country", country)
	tx.Context.SetTag("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetCustom("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetTag("user_agent", r.Header.Get("User-Agent"))

	span, ctx := apm.StartSpan(ctx, "PlaceOrderRequest", "external")
	order, err := pb.NewCheckoutServiceClient(fe.checkoutSvcConn).
		PlaceOrder(ctx, &pb.PlaceOrderRequest{
			Email: email,
			CreditCard: &pb.CreditCardInfo{
				CreditCardNumber:          ccNumber,
				CreditCardExpirationMonth: int32(ccMonth),
				CreditCardExpirationYear:  int32(ccYear),
				CreditCardCvv:             int32(ccCVV)},
			UserId:       sessionID(r),
			UserCurrency: currentCurrency(r),
			Address: &pb.Address{
				StreetAddress: streetAddress,
				City:          city,
				State:         state,
				ZipCode:       int32(zipCode),
				Country:       country},
		})
	if err != nil {
		span.End()
		e := apm.CaptureError(ctx, err)
		e.SetSpan(span)
		e.Send()
		renderHTTPError(log, r, w, errors.Wrap(err, "failed to complete the order"), http.StatusInternalServerError)
		return
	}
	log.WithField("order", order.GetOrder().GetOrderId()).Info("order placed")

	order.GetOrder().GetItems()

	span.End()
	r_span, ctx := apm.StartSpan(ctx, "getRecommendations", "request")
	recommendations, _ := fe.getRecommendations(ctx, sessionID(r), nil)
	r_span.End()
	re_span, ctx := apm.StartSpan(ctx, "ExecuteTemplate", "request")
	totalPaid := *order.GetOrder().GetShippingCost()
	for _, v := range order.GetOrder().GetItems() {
		totalPaid = money.Must(money.Sum(totalPaid, *v.GetCost()))
	}
	defer re_span.End()

	if err := templates.ExecuteTemplate(w, "order", map[string]interface{}{
    "elastic_apm_server_url": os.Getenv("ELASTIC_APM_SERVER_URLS"),
		"session_id":      sessionID(r),
		"request_id":      ctx.Value(ctxKeyRequestID{}),
		"user_currency":   currentCurrency(r),
		"order":           order.GetOrder(),
		"total_paid":      &totalPaid,
		"recommendations": recommendations,
	}); err != nil {
		e := apm.CaptureError(ctx, err)
		e.SetSpan(re_span)
		e.Send()
		log.Println(err)
	}

}

func (fe *frontendServer) logoutHandler(w http.ResponseWriter, r *http.Request) {
	tx := apm.DefaultTracer.StartTransaction("logoutHandler", "request")
	tx.Context.SetTag("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetCustom("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetTag("user_agent", r.Header.Get("User-Agent"))
	ctx := apm.ContextWithTransaction(r.Context(), tx)
	defer tx.End()
	log := ctx.Value(ctxKeyLog{}).(logrus.FieldLogger)
	log.Debug("logging out")
	for _, c := range r.Cookies() {
		c.Expires = time.Now().Add(-time.Hour * 24 * 365)
		c.MaxAge = -1
		http.SetCookie(w, c)
	}
	w.Header().Set("Location", "/")
	w.WriteHeader(http.StatusFound)
}

func (fe *frontendServer) setCurrencyHandler(w http.ResponseWriter, r *http.Request) {
	tx := apm.DefaultTracer.StartTransaction("setCurrencyHandler", "request")
	ctx := apm.ContextWithTransaction(r.Context(), tx)
	defer tx.End()
	log := ctx.Value(ctxKeyLog{}).(logrus.FieldLogger)
	cur := r.FormValue("currency_code")
	tx.Context.SetTag("currency_code", cur)
	tx.Context.SetTag("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetCustom("username", r.Header.Get("X-Forwarded-User"))
	tx.Context.SetTag("user_agent", r.Header.Get("User-Agent"))


	log.WithField("curr.new", cur).WithField("curr.old", currentCurrency(r)).
		Debug("setting currency")

	if cur != "" {
		http.SetCookie(w, &http.Cookie{
			Name:   cookieCurrency,
			Value:  cur,
			MaxAge: cookieMaxAge,
		})
	}
	referer := r.Header.Get("referer")
	if referer == "" {
		referer = "/"
	}
	w.Header().Set("Location", referer)
	w.WriteHeader(http.StatusFound)

}

// chooseAd queries for advertisements available and randomly chooses one, if
// available. It ignores the error retrieving the ad since it is not critical.
func (fe *frontendServer) chooseAd(ctx context.Context, ctxKeys []string, log logrus.FieldLogger) *pb.Ad {
	span, ctx := apm.StartSpan(ctx, "getAd", "request")
	ads, err := fe.getAd(ctx, ctxKeys)
	if err != nil {
		e := apm.CaptureError(ctx, err)
		e.SetSpan(span)
		e.Send()
		log.WithField("error", err).Warn("failed to retrieve ads")
		span.End()
		return nil
	}
	span.End()
	return ads[rand.Intn(len(ads))]
}

func renderHTTPError(log logrus.FieldLogger, r *http.Request, w http.ResponseWriter, err error, code int) {
	log.WithField("error", err).Error("request error")
	errMsg := fmt.Sprintf("%+v", err)

	w.WriteHeader(code)
	templates.ExecuteTemplate(w, "error", map[string]interface{}{
    "elastic_apm_server_url": os.Getenv("ELASTIC_APM_SERVER_URLS"),
		"session_id":  sessionID(r),
		"request_id":  r.Context().Value(ctxKeyRequestID{}),
		"error":       errMsg,
		"status_code": code,
		"status":      http.StatusText(code)})
}

func currentCurrency(r *http.Request) string {
	c, _ := r.Cookie(cookieCurrency)
	if c != nil {
		return c.Value
	}
	return defaultCurrency
}

func sessionID(r *http.Request) string {
	v := r.Context().Value(ctxKeySessionID{})
	if v != nil {
		return v.(string)
	}
	return ""
}

func cartIDs(c []*pb.CartItem) []string {
	out := make([]string, len(c))
	for i, v := range c {
		out[i] = v.GetProductId()
	}
	return out
}

func renderMoney(money pb.Money) string {
	return fmt.Sprintf("%s %d.%02d", money.GetCurrencyCode(), money.GetUnits(), money.GetNanos()/10000000)
}
