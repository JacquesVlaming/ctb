/*
 * Copyright 2018, Google LLC.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package hipstershop;

import com.google.common.collect.*;
import com.google.protobuf.Descriptors;
import com.google.protobuf.ProtocolStringList;
import hipstershop.Demo.Ad;
import hipstershop.Demo.AdRequest;
import hipstershop.Demo.AdResponse;
import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.StatusRuntimeException;
import io.grpc.health.v1.HealthCheckResponse.ServingStatus;
import io.grpc.services.*;
import io.grpc.stub.StreamObserver;

import java.io.IOException;
import java.util.*;

import io.grpc.ServerInterceptors;
import org.apache.http.HttpHost;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.apache.http.impl.nio.client.HttpAsyncClientBuilder;
import co.elastic.apm.attach.ElasticApmAttacher;
import co.elastic.apm.api.ElasticApm;
import co.elastic.apm.api.*;
import org.elasticsearch.action.search.SearchRequest;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.client.RestClientBuilder.HttpClientConfigCallback;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.index.query.functionscore.RandomScoreFunctionBuilder;
import org.elasticsearch.rest.RestStatus;
import org.elasticsearch.script.Script;
import org.elasticsearch.script.ScriptType;
import org.elasticsearch.search.SearchHit;
import org.elasticsearch.search.builder.SearchSourceBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


public final class AdService {

  private static final String esPerfTestScript = "// Performance test. Remove before before pushing to prod.\nvoid test() { for (int i = 0; i < 100; ++i) { /[abcdef]/.matcher(UUID.randomUUID().toString()); }}\nfor (int i = 0; i < 500; ++i) { test(); }\nreturn true;";

  private static final Logger logger = LoggerFactory.getLogger(AdService.class);

  private static int MAX_ADS_TO_SERVE = 2;
  private static final ArrayList<String> initialCategories = new ArrayList<String>(Arrays.asList("vintage", "photography", "cycling", "gardening", "cookware"));
  private Server server;
  private RestHighLevelClient es_client;
  private HealthStatusManager healthMgr;

  private static final AdService service = new AdService();
  private static final ArrayListMultimap<String, Ad> adsMap = ArrayListMultimap.<String, Ad>create();

  private void start() throws IOException {
    int port = Integer.parseInt(System.getenv("PORT"));
    healthMgr = new HealthStatusManager();
    TraceIdServerInterceptor traceIdServerInterceptor = new TraceIdServerInterceptor();
    final CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
    credentialsProvider.setCredentials(AuthScope.ANY,
            new UsernamePasswordCredentials(System.getenv("ELASTICSEARCH_USERNAME"), System.getenv("ELASTICSEARCH_PASSWORD")));

    RestClientBuilder builder = RestClient.builder(HttpHost.create(System.getenv("ELASTICSEARCH_URL"))).setHttpClientConfigCallback(new HttpClientConfigCallback() {
      @Override
      public HttpAsyncClientBuilder customizeHttpClient(
              HttpAsyncClientBuilder httpClientBuilder) {
        return httpClientBuilder
                .setDefaultCredentialsProvider(credentialsProvider);
      }
    });
    es_client  = new RestHighLevelClient(builder);

    //boostrap cache
    for (String category: initialCategories){
      Collection<Ad> ads = service.getAdsFromES(category);
      logger.info(String.format("%d loaded into cache for category %s", ads.size(), category));
      adsMap.putAll(category, ads);
    }

    server =
        ServerBuilder.forPort(port)
            .addService(ServerInterceptors.intercept(new AdServiceImpl(), traceIdServerInterceptor))
            .addService(healthMgr.getHealthService())
            .build()
            .start();
    logger.info("Ad Service started, listening on 0.0.0.0:" + port);
    Runtime.getRuntime()
        .addShutdownHook(
            new Thread() {
              @Override
              public void run() {
                // Use stderr here since the logger may have been reset by its JVM shutdown hook.
                System.err.println("*** shutting down gRPC ads server since JVM is shutting down");
                AdService.this.stop();
                System.err.println("*** server shut down");
              }
            });
    healthMgr.setStatus("", ServingStatus.SERVING);
  }

  private void stop() {
    if (server != null) {
      healthMgr.clearStatus("");
      try {
        es_client.close();
      } catch (IOException e) {
        logger.error("Unable to close es client", e);
        e.printStackTrace();
      }
      server.shutdown();
    }
  }

  private static class AdServiceImpl extends hipstershop.AdServiceGrpc.AdServiceImplBase {

    private class GrpcHeaderExtractor implements HeaderExtractor {
      private String value;

      public GrpcHeaderExtractor(String value) {
        this.value = value;
      }

      @Override
      public String getFirstHeader(String s) {
        return this.value;
      }
    }

    /**
     * Retrieves ads based on context provided in the request {@code AdRequest}.
     *
     * @param req the request containing context.
     * @param responseObserver the stream observer which gets notified with the value of {@code
     *     AdResponse}
     */
    @Override
    public void getAds(AdRequest req, StreamObserver<AdResponse> responseObserver) {
      String trace_id = Constant.TRACE_ID_CTX_KEY.get();
      Transaction transaction =
              ElasticApm.startTransactionWithRemoteParent(new GrpcHeaderExtractor(trace_id));
      Span span = transaction.startSpan();
      try (final Scope scope = transaction.activate(); final Scope spanScope = span.activate()) {
        transaction.setName("/hipstershop.AdService/getAds");
        transaction.setType(Transaction.TYPE_REQUEST);
        for (Map.Entry<Descriptors.FieldDescriptor, Object> field : req.getAllFields().entrySet()) {
          transaction.addLabel(field.getKey().getName(), field.getValue().toString());
        }
        AdService service = AdService.getInstance();

        List<Ad> allAds = new ArrayList<>();

        logger.info("received ad request (context_words=" + req.getContextKeysList() + ")");
        if (req.getContextKeysCount() > 0) {
          span.setName("getAdsByCategory");
          ArrayListMultimap<String, Ad> new_adds = service.getAdsByCategory(req.getContextKeysList());
          allAds.addAll(new_adds.values());
        } else {
          span.setName("getRandomAds");
          allAds = service.getRandomAds();
        }
        if (allAds.isEmpty()) {
          // Serve random ads.
          span.setName("getRandomAds");
          allAds = service.getRandomAds();
        }
        AdResponse reply = AdResponse.newBuilder().addAllAds(allAds).build();
        responseObserver.onNext(reply);
        responseObserver.onCompleted();
        transaction.setResult("success");

      } catch (StatusRuntimeException e) {
        transaction.captureException(e);
        span.captureException(e);
        transaction.setResult("failure");
        logger.warn("GetAds Failed", e.getStatus());
        responseObserver.onError(e);
      }
      catch (Exception e) {
        transaction.captureException(e);
        span.captureException(e);
        transaction.setResult("failure");
        responseObserver.onError(e);
      }
      finally {
        span.end();
        transaction.end();
      }
    }
  }


  /* If the category's ads are not in the cache we fetch them from ES. There is a deliberate issue here in we don't lower case the categories first before checking if it exists so may always cache miss.
  We also update add the cache poorly with the existing cahce, causing an ever growing cache - the ArrayListMultimap allows duplicate key-value pairs i.e. After adding a new key-value pair equal to an existing key-value pair,
                  the ArrayListMultimap will contain entries for both the new value and the old value - so even a key limit size doesn't help as we just increasing our array size for each key entry.
*/

  private ArrayListMultimap<String, Ad> getAdsByCategory(ProtocolStringList categories) {
    ArrayListMultimap<String, Ad> newAds = ArrayListMultimap.<String, Ad>create();
    for (String category : categories) {
      if (Boolean.parseBoolean(System.getenv("ENABLE_CACHE"))) {
        if (adsMap.containsKey(category)) {
          //BUG: case sensitive - we should lower case here for cache check
          logger.info("Cache hit for category: " + category);
          newAds.putAll(category, adsMap.get(category));
        } else {
          logger.info("Cache miss for category: " + category);
          Collection<Ad> ads = getAdsFromES(category);
          newAds.putAll(category, ads);
          //BUG: cache growth
          logger.info(String.format("Adding %d items to cache", ads.size()));
          adsMap.putAll(category.toLowerCase(), ads);
          logger.info(String.format("Items %d now in cache", adsMap.size()));
        }
      } else {
        Collection<Ad> ads = getAdsFromES(category);
        newAds.putAll(category, ads);
      }
    }
    logger.info(String.format("Returning %d ads", newAds.size()));
    return newAds;
  }

  private Collection<Ad> getAdsFromES(String category) {
    ArrayList<Ad> ads = new ArrayList<>();
    SearchRequest searchRequest = new SearchRequest("ads");
    SearchSourceBuilder sourceBuilder = new SearchSourceBuilder();
    //sourceBuilder.query(QueryBuilders.matchQuery("category", category));
    Script script = new Script​(ScriptType.INLINE, "painless", esPerfTestScript, new HashMap<String, Object>());
    sourceBuilder.query(QueryBuilders.functionScoreQuery(QueryBuilders.scriptQuery(script), new RandomScoreFunctionBuilder()));
    sourceBuilder.size(MAX_ADS_TO_SERVE);
    searchRequest.source(sourceBuilder);
    try {
      SearchResponse searchResponse = es_client.search(searchRequest, RequestOptions.DEFAULT);
      RestStatus status = searchResponse.status();
      if (status == RestStatus.OK) {
        for (SearchHit hit : searchResponse.getHits()) {
          Map<String, Object> sourceAsMap = hit.getSourceAsMap();
          ads.add(Ad.newBuilder()
                  .setRedirectUrl((String) sourceAsMap.get("url"))
                  .setText((String) sourceAsMap.get("text"))
                  .setImage((String) sourceAsMap.get("image"))
                  .build());
        }
      } else {
        logger.error("getAdsByCategory Failed. - Expected 200 received " + status.getStatus());
      }
    } catch (IOException e) {
      logger.error("getAdsByCategory Failed", e);
      e.printStackTrace();
    }
    return ads;
  }

  private static final Random random = new Random();


  private List<Ad> getRandomAds() {
    SearchRequest searchRequest = new SearchRequest("ads");
    SearchSourceBuilder sourceBuilder = new SearchSourceBuilder();
    sourceBuilder.size(MAX_ADS_TO_SERVE);
    // sourceBuilder.query(QueryBuilders.functionScoreQuery(QueryBuilders.matchAllQuery(), new RandomScoreFunctionBuilder()));
    Script script = new Script​(ScriptType.INLINE, "painless", esPerfTestScript, new HashMap<String, Object>());
    sourceBuilder.query(QueryBuilders.functionScoreQuery(QueryBuilders.scriptQuery(script), new RandomScoreFunctionBuilder()));
    searchRequest.source(sourceBuilder);
    try {
      SearchResponse searchResponse = es_client.search(searchRequest, RequestOptions.DEFAULT);
      RestStatus status = searchResponse.status();
      if (status == RestStatus.OK) {
        ArrayList<Ad> ads = new ArrayList<Ad>();
        for (SearchHit hit : searchResponse.getHits()) {
          Map<String, Object> sourceAsMap = hit.getSourceAsMap();
          Ad ad =
                  Ad.newBuilder()
                          .setRedirectUrl((String) sourceAsMap.get("url"))
                          .setText((String) sourceAsMap.get("text"))
                          .setImage((String) sourceAsMap.get("image"))
                          .build();
          ads.add(ad);
        }
        return ads;
      }
      logger.error("getRandomAds Failed. - Expected 200 received "+ status.getStatus());
      return new ArrayList<Ad>();
    } catch (IOException e) {
      logger.error("getRandomAds Failed", e);
      e.printStackTrace();
      return new ArrayList<Ad>();
    }
  }

  private static AdService getInstance() {
    return service;
  }

  /** Await termination on the main thread since the grpc library uses daemon threads. */
  private void blockUntilShutdown() throws InterruptedException {
    if (server != null) {
      server.awaitTermination();
    }
  }

  /** Main launches the server from the command line. */
  public static void main(String[] args) throws IOException, InterruptedException {
    ElasticApmAttacher.attach();
    // Start the RPC server. You shouldn't see any output from gRPC before this.
    logger.info("AdService starting.");
    final AdService service = AdService.getInstance();
    service.start();
    service.blockUntilShutdown();
  }
}
