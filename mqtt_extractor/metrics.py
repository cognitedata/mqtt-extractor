from prometheus_client import Gauge, Info, Summary

messages = Gauge("messages", "Number of messages received")
cdf_requests = Gauge("requests", "Number of data point requests to CDF")
cdf_requests_failed = Gauge(
    "requests_failed", "Number of data point requests to CDF failing"
)
cdf_data_points = Gauge("data_points", "Number of data points to CDF")
cdf_time_stamp = Gauge("cdf_time_stamp", "Largest time stamp inserted into CDF")
message_time_stamp = Gauge(
    "message_time_stamp", "Largest time stamp observed on incoming messages"
)

# queries = Summary("queries", "Queries made to IP21", ["process"])
# info = Info("extractor_details", "Information about running extractor")
