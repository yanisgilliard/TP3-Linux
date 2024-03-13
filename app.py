from flask import Flask, jsonify
from flask_restx import Api, Resource, reqparse
from flask_restx import Namespace
from flask_cors import CORS
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
from monit import check_resources

client = MongoClient("mongodb://localhost:27017/")
db = client["monit_db"]

def save_report(report):
    reports_collection = db["reports"]
    reports_collection.insert_one(report)


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
            json.dump({"ports": [],"alert_thresholds": {"cpu": 90,"ram": 20,"disk": 95},"discord_webhook_url": "YOUR_DISCORD_WEBHOOK_URL"}, config_file, indent=2)

    with open(CONFIG_FILE_PATH, "r") as config_file:
        return json.load(config_file)

def get_report(report_id):
    reports_collection = db["reports"]
    report = reports_collection.find_one({"id": report_id}, {"_id": 0})

    if report:
        return report
    else:
        return {"error": "Report not found"}, 404

def send_alert(alert_values):
    config = load_config()
    discord_webhook_url = config.get("discord_webhook_url")

    if discord_webhook_url:
        alert_message = "Alert! The following thresholds have been exceeded:\n"
        for resource, value in alert_values.items():
            alert_message += f"{resource}: {value}%\n"

        payload = {"content": alert_message}
        requests.post(discord_webhook_url, json=payload)
        logging.info("Alert sent to Discord.")
    else:
        logging.warning("Discord webhook URL not configured. Unable to send alerts.")

def get_last_report():
    reports_collection = db["reports"]
    last_report = reports_collection.find_one({}, {"_id": 0}, sort=[("timestamp", -1)])

    if last_report:
        return last_report
    else:
        return {"error": "No reports available"}, 404


def get_average_report(last_x_hours):
    reports = list_reports()
    recent_reports = []
    for report in reports:
        report_time = datetime.datetime.strptime(report["timestamp"], "%Y-%m-%d_%H-%M-%S")
        time_difference = datetime.datetime.now() - report_time

        if time_difference.total_seconds() / 3600 <= last_x_hours:
            recent_reports.append(report)

    if recent_reports:
        average_report = {"cpu_percent": 0, "ram_percent": 0, "disk_percent": 0}

        for report in recent_reports:

            average_report["cpu_percent"] += report["cpu_percent"]
            average_report["ram_percent"] += report["ram_percent"]
            average_report["disk_percent"] += report["disk_percent"]

        total_reports = len(recent_reports)
        average_report["cpu_percent"] /= total_reports
        average_report["ram_percent"] /= total_reports
        average_report["disk_percent"] /= total_reports

        logging.info("Calculated the average report for the last %d hours.", last_x_hours)
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

app = Flask(__name__)
CORS(app) 
api = Api(app, version='1.0', title='API_Monit', description='API pour la surveillance des ressources système')

namespace = Namespace('API_Monit', description='API pour la surveillance des ressources système')
api.add_namespace(namespace)

parser = reqparse.RequestParser()
parser.add_argument('last_x_hours', type=int, help='Nombre d\'heures pour le calcul de la moyenne')



if __name__ == "__main__":
    setup_logging()

    app.run(debug=True, port=3000)