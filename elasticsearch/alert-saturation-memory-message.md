$ALERT_MESSAGE_HEADER
> SLO: *{{context.threshold.condition0}}%*
> Observed: *{{context.value.condition0}}*
> Investigate: *<$KIBANA_URL/app/apm#/services/$SERVICE_NAME/overview?latencyAggregationType=p95|Service performance>*, *<$KIBANA_URL/app/metrics/explorer?metricsExplorer=(chartOptions:(stack:!f,type:line,yAxisMode:fromZero),options:(aggregation:p95,filterQuery:%27kubernetes.pod.name:$SERVICE_NAME_LOWERCASE*%27,groupBy:!(kubernetes.pod.name),metrics:!((aggregation:p95,color:color0,field:kubernetes.pod.cpu.usage.limit.pct),(aggregation:p95,color:color1,field:kubernetes.pod.memory.usage.limit.pct)),source:default),timerange:(from:now-15m,interval:%3E%3D10s,to:now))|Pod metrics>*
