from flask import Flask
from flask_cors import CORS
from flask_restx import Api
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)  
api = Api(app)

client = MongoClient("mongodb://localhost:27017/")
db = client["monit_db"]

from routes.check import check
from routes.reports import reports, report, last_report

app.run(debug=True, port=3000)
