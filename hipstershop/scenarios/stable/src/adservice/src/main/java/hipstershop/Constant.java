package hipstershop;

import io.grpc.Context;
import io.grpc.Metadata;

import static io.grpc.Metadata.ASCII_STRING_MARSHALLER;

public class Constant {
  public static final String TRACE_PARENT_HEADER = "elastic-apm-traceparent";
  public static final Context.Key<String> TRACE_ID_CTX_KEY = Context.key(TRACE_PARENT_HEADER);
  public static final Metadata.Key<String> TRACE_ID_METADATA_KEY =
      Metadata.Key.of(TRACE_PARENT_HEADER, ASCII_STRING_MARSHALLER);
}
