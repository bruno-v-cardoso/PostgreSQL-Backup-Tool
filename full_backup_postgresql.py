import json
import os
import subprocess
import sys
from datetime import datetime
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

def log(dataset, action, message, status="success"):
    log_entry = {
        "@timestamp": datetime.now().isoformat(),
        "event": {"dataset": dataset, "action": action, "outcome": status},
        "message": message,
    }
    print(json.dumps(log_entry))

def log_database_backup(databasename, filename, status="success", error=None):
    log_entry = {
        "@timestamp": datetime.now().isoformat(),
        "event": {
            "dataset": "backup",
            "action": "backup_success" if status == "success" else "backup_error",
            "outcome": status
        },
        "database": {
            "name": databasename
        },
        "file": {
            "path": filename
        },
        "message": f"Backup {'successful' if status == 'success' else 'failed'} for database {databasename}: {filename}"
    }
    if error:
        log_entry["error"] = {"message": error}
    print(json.dumps(log_entry))

def register_prometheus(metric, job_name, message, status):
    registry = CollectorRegistry() 
    g = Gauge(metric, message, registry=registry)
    g.set_to_current_time()
    g.set(-1 if status == "failure" else 1)
    push_to_gateway(os.environ['PROMETHEUS__PUSHGATEWAY__SERVER'], job=job_name, registry=registry)

def backup_databases(backup_dir, db_host, db_user):
    log("backup", "backup", "Init Databases backup")
    
    # Get the current date and time for the backup file name
    now = datetime.now()

    # Query to get the list of databases
    list_databases_command = f"psql -h {db_host} -U {db_user} -d postgres -t -c 'SELECT datname FROM pg_database WHERE datistemplate = false;'"

    try:
        # Execute the command to get the list of databases
        result = subprocess.run(list_databases_command, shell=True, check=True, capture_output=True, text=True)
        databases = result.stdout.split()
        
        # Iterate over each database and create a backup
        for db in databases:
            # Verify if database directory exists
            database_backup_dir = os.path.join(backup_dir, db)
            os.makedirs(database_backup_dir, exist_ok=True) 
            os.chdir(database_backup_dir)
            
            # Define the backup file name
            backup_file = os.path.join(database_backup_dir, f"{db}_full_backup_{now.strftime('%Y%m%d_%H%M%S')}.tar")
            dump_command = f"pg_dump -h {db_host} -U {db_user} -d {db} -F tar -f {backup_file}"
            
            try:
                # Execute the dump command
                subprocess.run(dump_command, shell=True, check=True)
                log_database_backup(db, backup_file)
            except subprocess.CalledProcessError as e:
                log_database_backup(db, backup_file, status="failure", error=f"Error during backup: {e}")
                register_prometheus('job_backup_databases_success', 'postgresql_backup_databases', 'Error during Backup databases', 'failure')
                raise
            
            os.chdir(backup_dir)
    except subprocess.CalledProcessError as e:
        log("backup", "CalledProcessError", f"Error during listing databases: {e}", "failure")
        register_prometheus('job_backup_databases_success', 'postgresql_backup_databases', 'Error during Backup databases', 'failure')
        raise
        
    except OSError as e:
        log("backup", "OSError", f"Error in creating directory or changing directory: {e}", "failure")
        register_prometheus('job_backup_databases_success', 'postgresql_backup_databases', 'Error during Backup databases', 'failure')
        raise
        
    log("backup", "backup", "Backup script executed successfully")  
    register_prometheus('job_backup_databases_success', 'postgresql_backup_databases', 'Backup script executed successfully', 'success')
    
def apply_retention_policy(backup_dir, retain_backup_in_days):
    log("RetentionPolicy", "RetentionPolicy", "Init Retention Policy for old database backups")
    
    # Get the current date and time
    now = datetime.now()
    
    try:
        # foreach folder in backup_dir to delete old backup
        for folder in os.listdir(backup_dir):
            folder_path = os.path.join(backup_dir, folder)
            if os.path.isdir(folder_path):
                log("RetentionPolicy", "RetentionPolicy", f"Deleting old backup database for folder: {folder}")
                
                # only delete files in folder past x days
                for file in sorted(os.listdir(folder_path)):
                    if os.path.isfile(os.path.join(folder_path, file)) and file.endswith(".tar"):
                        file_path = os.path.join(folder_path, file)
                        file_time = os.path.getctime(file_path)
                        if (now.timestamp() - file_time) / 60 / 60 / 24 > retain_backup_in_days:
                            os.remove(file_path)
                            log("RetentionPolicy", "RetentionPolicy", f"Deleted file: {file_path}")
                            
            log("RetentionPolicy", "RetentionPolicy", f"Finished validation of retention policy for backup database {folder}")

    except OSError as e:
        log("RetentionPolicy", "RetentionPolicy_error", f"Error during deletion old backup databases: {e}", "failure")
        register_prometheus('job_retainpolicy_databases_sucess', 'postgresql_retainpolicy_databases', 'Error during deletion old backup databases', 'failure')
        raise
        
    log("RetentionPolicy", "RetentionPolicy", "Finished retention policy databases backup")
    register_prometheus('job_retainpolicy_databases_sucess', 'postgresql_retainpolicy_databases', 'Finished retention policy databases backup', 'success')

def main():
    log("backup", "backup", "Init PG Backup Tool")
    
    # Define the PostgreSQL server details
    try:
        db_host = os.environ['POSTGRESQL__SERVER']
        db_user = os.environ['POSTGRESQL__USER']
        db_password = os.environ['POSTGRESQL__PASSWORD']
        backup_dir = os.environ['BACKUP__FOLDER']
        retain_backup_in_days = int(os.environ['RETAIN__BACKUP__IN__DAYS'])
        
        # Set the environment variable for the PostgreSQL password
        os.environ['PGPASSWORD'] = db_password
    except KeyError as e:
        log("backup", "KeyError", f"Missing environment variable: {e}", "failure")
        sys.exit(0)
    
    try: 
        # Backup Databases
        backup_databases(backup_dir, db_host, db_user)
        # Apply Retention Policy
        apply_retention_policy(backup_dir, retain_backup_in_days)
    except Exception as e:
        log("pg-backup-tool", "Exception", f"An error occurred: {e}", "failure")
        sys.exit(0)

    log("backup", "backup", "Finished PG Backup Tool")

if __name__ == "__main__":
    main()
