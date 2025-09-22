#!/usr/bin/env python3
"""
Spring Batch Job Client with Tracing Support

This client application calls the Spring Batch ETL API with distributed tracing.
It generates its own trace IDs and correlates them with server responses.
"""

import requests
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(client_trace_id)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/job_client.log')
    ]
)

class JobClient:
    """Client for triggering Spring Batch jobs with tracing support."""

    def __init__(self, base_url: str = "http://localhost:8082"):
        self.base_url = base_url
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # Add default headers for tracing
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'SpringBatch-JobClient/1.0'
        })

    def generate_trace_id(self) -> str:
        """Generate a unique trace ID for request correlation."""
        return str(uuid.uuid4()).replace('-', '')[:16]

    def generate_span_id(self) -> str:
        """Generate a unique span ID for request correlation."""
        return str(uuid.uuid4()).replace('-', '')[:8]

    def log_with_trace(self, level: str, message: str, trace_id: str, **kwargs):
        """Log message with trace context."""
        extra = {'client_trace_id': trace_id}
        extra.update(kwargs)

        getattr(self.logger, level)(message, extra=extra)

    def trigger_job(self, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger the Spring Batch ETL job.

        Args:
            trace_id: Optional trace ID for correlation

        Returns:
            Dict containing API response and trace information
        """
        if not trace_id:
            trace_id = self.generate_trace_id()

        span_id = self.generate_span_id()
        start_time = time.time()

        # Add tracing headers
        headers = {
            'X-Trace-Id': trace_id,
            'X-Span-Id': span_id,
            'X-Client-Name': 'job-client',
            'X-Request-Timestamp': str(int(time.time() * 1000))
        }

        url = f"{self.base_url}/api/jobs/trigger"

        self.log_with_trace(
            'info',
            f"Triggering Spring Batch job. URL: {url}, TraceId: {trace_id}, SpanId: {span_id}",
            trace_id,
            url=url,
            span_id=span_id,
            operation='trigger_job'
        )

        try:
            response = self.session.post(url, headers=headers, timeout=30)
            duration = time.time() - start_time

            # Log response details
            self.log_with_trace(
                'info',
                f"API response received. Status: {response.status_code}, Duration: {duration:.2f}s",
                trace_id,
                status_code=response.status_code,
                duration=duration,
                response_headers=dict(response.headers)
            )

            # Parse response
            try:
                response_data = response.json()

                # Check if server returned trace information
                server_trace_id = response_data.get('traceId')
                server_span_id = response_data.get('spanId')

                if server_trace_id:
                    self.log_with_trace(
                        'info',
                        f"Server trace correlation: ClientTrace={trace_id}, ServerTrace={server_trace_id}",
                        trace_id,
                        server_trace_id=server_trace_id,
                        server_span_id=server_span_id,
                        correlation_match=(trace_id == server_trace_id)
                    )

                # Log job execution details
                if response.status_code == 200:
                    job_execution_id = response_data.get('jobExecutionId')
                    self.log_with_trace(
                        'info',
                        f"Spring Batch job triggered successfully. JobExecutionId: {job_execution_id}",
                        trace_id,
                        job_execution_id=job_execution_id,
                        success=True
                    )
                else:
                    self.log_with_trace(
                        'error',
                        f"Failed to trigger job. Status: {response.status_code}, Message: {response_data.get('message', 'Unknown error')}",
                        trace_id,
                        error_message=response_data.get('message'),
                        success=False
                    )

                return {
                    'success': response.status_code == 200,
                    'client_trace_id': trace_id,
                    'client_span_id': span_id,
                    'response_data': response_data,
                    'duration': duration,
                    'status_code': response.status_code
                }

            except json.JSONDecodeError as e:
                self.log_with_trace(
                    'error',
                    f"Failed to parse JSON response: {e}",
                    trace_id,
                    error=str(e)
                )
                return {
                    'success': False,
                    'client_trace_id': trace_id,
                    'error': f"JSON decode error: {e}",
                    'raw_response': response.text
                }

        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            self.log_with_trace(
                'error',
                f"Request failed: {e}",
                trace_id,
                error=str(e),
                duration=duration
            )
            return {
                'success': False,
                'client_trace_id': trace_id,
                'error': str(e),
                'duration': duration
            }

    def check_health(self, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Check API health status."""
        if not trace_id:
            trace_id = self.generate_trace_id()

        span_id = self.generate_span_id()
        url = f"{self.base_url}/api/jobs/status"

        headers = {
            'X-Trace-Id': trace_id,
            'X-Span-Id': span_id,
            'X-Client-Name': 'job-client'
        }

        self.log_with_trace(
            'info',
            f"Checking API health. URL: {url}",
            trace_id,
            url=url,
            operation='health_check'
        )

        try:
            response = self.session.get(url, headers=headers, timeout=10)
            response_data = response.json()

            self.log_with_trace(
                'info',
                f"Health check response: {response_data.get('status', 'unknown')}",
                trace_id,
                health_status=response_data.get('status'),
                server_trace_id=response_data.get('traceId')
            )

            return {
                'success': response.status_code == 200,
                'client_trace_id': trace_id,
                'response_data': response_data
            }

        except Exception as e:
            self.log_with_trace(
                'error',
                f"Health check failed: {e}",
                trace_id,
                error=str(e)
            )
            return {
                'success': False,
                'client_trace_id': trace_id,
                'error': str(e)
            }

def main():
    """Main function to run the client."""
    client = JobClient()

    print("Spring Batch Job Client with Tracing")
    print("=" * 40)

    # Check health first
    print("\n1. Checking API health...")
    health_result = client.check_health()
    if not health_result['success']:
        print(f"❌ Health check failed: {health_result.get('error')}")
        return
    else:
        print("✅ API is healthy")

    # Trigger multiple jobs with different trace IDs
    print("\n2. Triggering Spring Batch jobs...")

    for i in range(3):
        print(f"\n--- Job {i+1} ---")

        result = client.trigger_job()

        if result['success']:
            print(f"✅ Job triggered successfully")
            print(f"   Client Trace ID: {result['client_trace_id']}")
            print(f"   Job Execution ID: {result['response_data'].get('jobExecutionId')}")
            print(f"   Server Trace ID: {result['response_data'].get('traceId')}")
            print(f"   Duration: {result['duration']:.2f}s")
        else:
            print(f"❌ Job failed: {result.get('error')}")

        # Wait between requests
        if i < 2:
            print("   Waiting 5 seconds...")
            time.sleep(5)

    print("\n✅ Client execution completed. Check logs for detailed trace information.")
    print("📋 Logs are available at:")
    print("   - Console output above")
    print("   - /tmp/job_client.log")

if __name__ == "__main__":
    main()