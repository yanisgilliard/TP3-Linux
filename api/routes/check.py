from flask import jsonify
from monit import check_resources
from __main__ import app, api
from flask_restx import Resource, Api

@api.route('/API_Monit/check', methods=['GET'])
class check(Resource):
    def get(self):
        '''
        This endpoint checks the resources of the server
        '''
        report = check_resources()
        return jsonify(report)