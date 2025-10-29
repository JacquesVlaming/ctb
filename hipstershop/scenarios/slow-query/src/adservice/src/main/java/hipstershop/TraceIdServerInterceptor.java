package hipstershop;

import io.grpc.*;

import java.util.Map;

public class TraceIdServerInterceptor implements ServerInterceptor {
  @Override
  public <ReqT, RespT> ServerCall.Listener<ReqT> interceptCall(
      ServerCall<ReqT, RespT> serverCall,
      Metadata metadata,
      ServerCallHandler<ReqT, RespT> serverCallHandler) {
    String traceId = metadata.get(Constant.TRACE_ID_METADATA_KEY);
    Context ctx = Context.current().withValue(Constant.TRACE_ID_CTX_KEY, traceId);
    return Contexts.interceptCall(ctx, serverCall, metadata, serverCallHandler);
  }
}
