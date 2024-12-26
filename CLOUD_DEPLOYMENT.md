# OKX WebSocket Relay - Google Cloud Deployment Guide

## Prerequisites

1. **Google Cloud Account**
   - Active Google Cloud Platform (GCP) account
   - Project created with billing enabled

2. **Local Setup**
   - Google Cloud SDK installed
   - Docker installed
   - Python 3.9+
   - gcloud CLI configured

## Deployment Steps

### 1. Enable Required Google Cloud Services

```bash
# Enable necessary APIs
gcloud services enable \
  run.googleapis.com \
  containerregistry.googleapis.com \
  pubsub.googleapis.com \
  logging.googleapis.com
```

### 2. Set Environment Variables

```bash
# Set your GCP project ID
export PROJECT_ID=$(gcloud config get-value project)

# Configure gcloud to use your project
gcloud config set project $PROJECT_ID
```

### 3. Create Pub/Sub Topic (Optional)

```bash
# Create a Pub/Sub topic for trading data
gcloud pubsub topics create trading-data-stream
```

### 4. Build and Deploy

```bash
# Authenticate Docker with Google Cloud
gcloud auth configure-docker

# Build and deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml
```

## Configuration Options

### Environment Variables

- `OKX_WSS_URL`: WebSocket endpoint for OKX (default: wss://ws.okx.com:8443/ws/v5/public)
- `PUBSUB_TOPIC`: Pub/Sub topic name for streaming data
- `MAX_CONNECTIONS`: Maximum WebSocket client connections
- `PAIRS_FILE`: Path to trading pairs configuration file

### Customizing Deployment

Edit `cloudbuild.yaml` to modify:
- Deployment region
- Instance scaling
- Memory and CPU allocation

## Monitoring and Logging

- **Cloud Logging**: Automatically logs application events
- **Cloud Monitoring**: Provides performance metrics
- **Pub/Sub**: Streams trading data for further processing

## Security Considerations

1. Use Cloud Run's built-in authentication
2. Configure VPC Service Controls
3. Implement least-privilege IAM roles

## Scaling and Performance

- Cloud Run automatically scales based on traffic
- Configurable max instances in `cloudbuild.yaml`
- Supports high-concurrency WebSocket connections

## Troubleshooting

1. Check deployment logs:
   ```bash
   gcloud run logs read --service okx-websocket-relay
   ```

2. Verify service status:
   ```bash
   gcloud run services list
   ```

## Cost Optimization

- Cloud Run charges only for actual compute time
- Set appropriate max/min instances
- Monitor Pub/Sub message volume

## Advanced Configuration

### Custom Domain

1. Verify domain ownership
2. Map custom domain to Cloud Run service
   ```bash
   gcloud run domain-mappings create \
     --service okx-websocket-relay \
     --domain your-domain.com
   ```

## Example Pub/Sub Consumer (Python)

```python
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(
    PROJECT_ID, 'trading-data-stream-subscription'
)

def process_message(message):
    print(f"Received: {message.data}")
    message.ack()

streaming_pull_future = subscriber.subscribe(
    subscription_path, callback=process_message
)
```

## Recommended Next Steps

1. Set up CI/CD pipeline
2. Implement advanced error handling
3. Add monitoring alerts
4. Configure backup and disaster recovery

## Disclaimer

Ensure compliance with OKX's terms of service and data usage policies.
