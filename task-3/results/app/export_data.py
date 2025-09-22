#!/usr/bin/env python3
"""
Data Export Script for Transportation Analytics
Exports daily shipment data from PostgreSQL to CSV files
"""

import os
import sys
import csv
import json
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataExporter:
    def __init__(self):
        """Initialize exporter with environment configurations"""
        self.db_config = {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'port': os.environ.get('DB_PORT', '5432'),
            'database': os.environ.get('DB_NAME', 'transportation'),
            'user': os.environ.get('DB_USER', 'postgres'),
            'password': os.environ.get('DB_PASSWORD', 'postgres')
        }

        self.s3_config = {
            'endpoint': os.environ.get('S3_ENDPOINT', 'http://minio:9000'),
            'access_key': os.environ.get('S3_ACCESS_KEY', 'minioadmin'),
            'secret_key': os.environ.get('S3_SECRET_KEY', 'minioadmin'),
            'bucket': os.environ.get('S3_BUCKET', 'analytics-data')
        }

        self.export_date = datetime.now().date()
        self.export_path = f"/tmp/export_{self.export_date}"

        # Create export directory
        os.makedirs(self.export_path, exist_ok=True)

    def connect_db(self):
        """Establish database connection"""
        try:
            conn = psycopg2.connect(**self.db_config)
            logger.info("Database connection established")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def export_table(self, conn, table_name, query=None):
        """Export single table to CSV"""
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Use custom query or default to full table
            if query:
                cursor.execute(query)
            else:
                # For daily export, get only yesterday's data where applicable
                yesterday = (datetime.now() - timedelta(days=1)).date()

                if table_name in ['shipments', 'shipment_events']:
                    query = f"""
                        SELECT * FROM {table_name}
                        WHERE DATE(created_at) = '{yesterday}'
                    """
                else:
                    query = f"SELECT * FROM {table_name}"

                cursor.execute(query)

            # Fetch data
            rows = cursor.fetchall()
            row_count = len(rows)

            if row_count == 0:
                logger.warning(f"No data found for table {table_name}")
                return 0

            # Write to CSV
            filename = f"{self.export_path}/{table_name}_{self.export_date}.csv"

            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if rows:
                    fieldnames = rows[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

            logger.info(f"Exported {row_count} rows from {table_name} to {filename}")
            cursor.close()

            return row_count

        except Exception as e:
            logger.error(f"Failed to export table {table_name}: {e}")
            raise

    def upload_to_s3(self, filename):
        """Upload file to S3/MinIO"""
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=self.s3_config['endpoint'],
                aws_access_key_id=self.s3_config['access_key'],
                aws_secret_access_key=self.s3_config['secret_key'],
                use_ssl=False
            )

            # Create bucket if it doesn't exist
            try:
                s3_client.create_bucket(Bucket=self.s3_config['bucket'])
            except ClientError as e:
                if e.response['Error']['Code'] != 'BucketAlreadyOwnedByYou':
                    logger.warning(f"Bucket creation warning: {e}")

            # Upload file
            file_basename = os.path.basename(filename)
            s3_key = f"daily-exports/{self.export_date}/{file_basename}"

            s3_client.upload_file(
                filename,
                self.s3_config['bucket'],
                s3_key
            )

            logger.info(f"Uploaded {file_basename} to s3://{self.s3_config['bucket']}/{s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"Failed to upload {filename} to S3: {e}")
            raise

    def export_all_tables(self):
        """Export all required tables"""
        tables = [
            {
                'name': 'shipments',
                'query': """
                    SELECT
                        shipment_id,
                        client_id,
                        driver_id,
                        vehicle_id,
                        origin_city,
                        destination_city,
                        status,
                        total_distance_km,
                        total_cost,
                        created_at,
                        updated_at
                    FROM shipments
                    WHERE DATE(created_at) = CURRENT_DATE - INTERVAL '1 day'
                """
            },
            {
                'name': 'shipment_events',
                'query': """
                    SELECT
                        event_id,
                        shipment_id,
                        event_type,
                        event_timestamp,
                        location,
                        description
                    FROM shipment_events
                    WHERE DATE(event_timestamp) = CURRENT_DATE - INTERVAL '1 day'
                """
            },
            {
                'name': 'drivers',
                'query': "SELECT * FROM drivers WHERE active = true"
            },
            {
                'name': 'vehicles',
                'query': "SELECT * FROM vehicles WHERE active = true"
            },
            {
                'name': 'clients',
                'query': "SELECT * FROM clients WHERE active = true"
            }
        ]

        conn = self.connect_db()
        export_summary = {
            'export_date': str(self.export_date),
            'tables': {},
            'total_rows': 0,
            'status': 'SUCCESS'
        }

        try:
            for table in tables:
                logger.info(f"Exporting table: {table['name']}")
                row_count = self.export_table(
                    conn,
                    table['name'],
                    table.get('query')
                )

                # Upload to S3
                csv_filename = f"{self.export_path}/{table['name']}_{self.export_date}.csv"
                if os.path.exists(csv_filename):
                    s3_path = self.upload_to_s3(csv_filename)
                    export_summary['tables'][table['name']] = {
                        'rows': row_count,
                        's3_path': s3_path
                    }
                    export_summary['total_rows'] += row_count

        except Exception as e:
            logger.error(f"Export failed: {e}")
            export_summary['status'] = 'FAILED'
            export_summary['error'] = str(e)
            raise
        finally:
            conn.close()

            # Write summary
            summary_file = f"{self.export_path}/export_summary_{self.export_date}.json"
            with open(summary_file, 'w') as f:
                json.dump(export_summary, f, indent=2)

            # Upload summary to S3
            self.upload_to_s3(summary_file)

            logger.info(f"Export completed. Summary: {export_summary}")

        return export_summary

def main():
    """Main execution function"""
    try:
        logger.info("Starting daily data export job")
        exporter = DataExporter()
        result = exporter.export_all_tables()

        if result['status'] == 'SUCCESS':
            logger.info(f"Export successful: {result['total_rows']} rows exported")
            sys.exit(0)
        else:
            logger.error(f"Export failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error in export job: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()