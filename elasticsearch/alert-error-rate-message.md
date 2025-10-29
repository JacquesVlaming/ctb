$ALERT_MESSAGE_HEADER
> SLO: *$THRESHOLD* errors per min
> Observed: *{{context.triggerValue}}* errors per min
> Investigate: *<$KIBANA_URL/app/apm#/services/$SERVICE_NAME/errors?rangeFrom=now-15m&rangeTo=now|Service errors>*
