''' This is a simple monitoring script that checks the CPU, RAM, Disk and ports of the machine it's running on.'''
import psutil
import json
import os
import datetime
import socket
import logging
from logging.handlers import RotatingFileHandler
import requests
from pymongo import MongoClient
from bson import json_util
import hashlib

client = MongoClient("mongodb://localhost:27017/")
db = client["monit_db"]

LOG_DIR = "/var/monit"
CONFIG_FILE_PATH = "/etc/monit/monit_config.json"


def setup_logging():
    log_file = os.path.join(LOG_DIR, "monit.log")

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logging.basicConfig(
        handlers=[RotatingFileHandler(log_file, maxBytes=102400, backupCount=5)],
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )


def load_config():
    if not os.path.exists(CONFIG_FILE_PATH):
        os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
        with open(CONFIG_FILE_PATH, "w") as config_file:
            json.dump(
                {
                    "ports": [],
                    "alert_thresholds": {"cpu": 90, "ram": 20, "disk": 95},
                    "discord_webhook_url": "YOUR_DISCORD_WEBHOOK_URL",
                },
                config_file,
                indent=2,
            )

    with open(CONFIG_FILE_PATH, "r") as config_file:
        return json.load(config_file)


def check_resources():
    cpu_percent = psutil.cpu_percent()
    ram_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage("/").percent

    config = load_config()
    ports_to_monitor = config.get("ports", [])
    alert_thresholds = config.get("alert_thresholds", {})

    alert_values = {
        resource: locals()[f"{resource}_percent"]
        for resource, threshold in alert_thresholds.items()
        if locals()[f"{resource}_percent"] > threshold
    }

    ports_status = {port: is_port_open("127.0.0.1", port) for port in ports_to_monitor}

    date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report = {
        "timestamp": date,
        "id": hashlib.sha256(date.encode()).hexdigest(),
        "cpu_percent": cpu_percent,
        "ram_percent": ram_percent,
        "disk_percent": disk_percent,
        "ports_status": ports_status,
    }

    clean_report = {
        "timestamp": date,
        "id": hashlib.sha256(date.encode()).hexdigest(),
        "cpu_percent": cpu_percent,
        "ram_percent": ram_percent,
        "disk_percent": disk_percent,
        "ports_status": ports_status,
    }

    db["reports"].insert_one(report)

    if alert_values:
        send_alert(alert_values)

    logging.info("Check completed and report generated.")
    return clean_report


def send_alert(alert_values):
    config = load_config()
    discord_webhook_url = config.get("discord_webhook_url")

    if discord_webhook_url:
        alert_message = (
            "Alert! The following thresholds have been exceeded:\n"
            + "\n".join(
                f"{resource}: {value}%" for resource, value in alert_values.items()
            )
        )

        payload = {"content": alert_message}
        requests.post(discord_webhook_url, json=payload)
        logging.info("Alert sent to Discord.")
    else:
        logging.warning("Discord webhook URL not configured. Unable to send alerts.")


def get_average_report(last_x_hours):
    reports = list(db["reports"].find({}, {"_id": False}))
    recent_reports = [
        report
        for report in reports
        if (
            datetime.datetime.now()
            - datetime.datetime.strptime(report["timestamp"], "%Y-%m-%d_%H-%M-%S")
        ).total_seconds()
        / 3600
        <= last_x_hours
    ]

    if recent_reports:
        average_report = {
            "cpu_percent": sum(report["cpu_percent"] for report in recent_reports)
            / len(recent_reports),
            "ram_percent": sum(report["ram_percent"] for report in recent_reports)
            / len(recent_reports),
            "disk_percent": sum(report["disk_percent"] for report in recent_reports)
            / len(recent_reports),
        }

        logging.info(
            "Calculated the average report for the last %d hours.", last_x_hours
        )
        return average_report
    else:
        logging.warning("No reports available in the specified time range.")
        return None


def is_port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False


if __name__ == "__main__":
    setup_logging()
