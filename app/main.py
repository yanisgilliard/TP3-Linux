""" Main file for the application. """
from flask import Flask
from routes.check import check

app = Flask(__name__)

app.run(debug=True, port=3000)
