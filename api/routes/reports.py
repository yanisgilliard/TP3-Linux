from flask import jsonify
from monit import get_average_report
from __main__ import app, db, api
from flask_restx import Resource, Api

@api.route('/API_Monit/reports', methods=['GET'])
class reports(Resource):
    def get(self):
        '''
        This endpoint returns all the reports
        '''
        reports_collection = db["reports"]
        reports = list(reports_collection.find({}, {"_id": False}))
        return jsonify(reports)

@api.route('/API_Monit/reports/<string:report_id>', methods=['GET'])
class report(Resource):
    def get(self, report_id):
        '''
        This endpoint returns a specific report
        '''
        reports_collection = db["reports"]
        report = reports_collection.find_one({"id": report_id}, {"_id": False})

        if report:
            return jsonify(report) 
        else:
            return {"error": "Report not found"}, 404

@api.route('/API_Monit/reports/last', methods=['GET'])
class last_report(Resource):
    def get(self):
        '''
        This endpoint returns the last report
        '''
        reports_collection = db["reports"]
        last_report = reports_collection.find_one({}, {"_id": False}, sort=[("timestamp", -1)])

        if last_report:
            return jsonify(last_report)
        else:
            return {"error": "No reports available"}, 404

@api.route('/API_Monit/average_report/<int:last_x_hours>', methods=['GET'])
class average_report(Resource):
    def get(self, last_x_hours):
        '''
        This endpoint returns the average report for the last x hours
        '''
        average_report = get_average_report(last_x_hours)

        if average_report:
            return jsonify(average_report)
        else:
            return {"error": "No reports available in the specified time range."}, 404