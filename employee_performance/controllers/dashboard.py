from odoo import http
from odoo.http import request
import json

class EmployeePerformanceDashboard(http.Controller):

    @http.route('/employee_performance/get_dashboard_data', type='json', auth='user')
    def get_dashboard_data(self):
        return request.env['employee.performance'].get_dashboard_data()