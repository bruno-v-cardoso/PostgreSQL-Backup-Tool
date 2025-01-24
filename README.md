# PostgreSQL Backup Tool

This repository contains a Python-based tool for backing up PostgreSQL databases, applying a retention policy for old backups, and pushing metrics to Prometheus Pushgateway.

## Features

- Back up all PostgreSQL databases (excluding templates).
- Apply a retention policy to remove backups older than a specified number of days.
- Push metrics to Prometheus Pushgateway to monitor the backup and retention processes.
- Log events in a structured JSON format for better observability.

## Prerequisites

- Docker
- A running instance of Prometheus Pushgateway
- PostgreSQL 15 client installed (handled by the Dockerfile)

## Setup and Usage

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### Step 2: Prepare the Environment Variables

Update the following environment variables in the `Dockerfile` or pass them at runtime:

- `POSTGRESQL__SERVER`: PostgreSQL server hostname or IP (default: `postgres`)
- `POSTGRESQL__USER`: Your PostgreSQL username
- `POSTGRESQL__PASSWORD`: Your PostgreSQL password
- `RETAIN__BACKUP__IN__DAYS`: Number of days to retain backups (default: `5`)
- `BACKUP__FOLDER`: Directory to store backups
- `PROMETHEUS__PUSHGATEWAY__SERVER`: URL of the Prometheus Pushgateway (default: `prometheus_pushgateway:9091`)

### Step 3: Build and Run the Docker Container

1. Build the Docker image:
   ```bash
   docker build -t postgresql-backup-tool .
   ```

2. Run the container:
   ```bash
   docker run -e POSTGRESQL__SERVER=<your_postgres_server> \
              -e POSTGRESQL__USER=<your_postgres_user> \
              -e POSTGRESQL__PASSWORD=<your_postgres_password> \
              -e RETAIN__BACKUP__IN__DAYS=<your_value> \
              -e BACKUP__FOLDER=<you_backup_folder_in_container> \
              -e PROMETHEUS__PUSHGATEWAY__SERVER=<your_prometheus_pushgateway_endpoint> \
              -v $(pwd)/<you_backup_folder_in_host>:<you_backup_folder_in_container> \
              postgresql-backup-tool
   ```

### Step 4: Check Logs and Monitor Metrics

- Logs will be printed in structured JSON format for easy parsing.
- Metrics can be monitored using Prometheus Pushgateway.

## How It Works

1. **Backup Databases:**
   - The script lists all non-template databases using `psql`.
   - Each database is backed up using `pg_dump` in tar format.
   - Backups are stored in a folder structure by database name.

2. **Retention Policy:**
   - Files older than the specified number of days are deleted.

3. **Prometheus Integration:**
   - Metrics for backup success/failure and retention policy execution are pushed to Prometheus Pushgateway.

## Logging

- Logs are output in JSON format with fields like `@timestamp`, `event`, `database`, `file`, and `message`.

## Troubleshooting

- **Missing Environment Variables:** Ensure all required environment variables are set before running the container.
- **Permissions Issues:** Ensure the backup directory is writable by the container.
- **Prometheus Pushgateway Errors:** Verify the Pushgateway URL and ensure it is accessible.


