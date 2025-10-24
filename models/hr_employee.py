from odoo import models, fields, api
from datetime import date

class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    # show Supervisor instead of Manager label (field remains parent_id)
    parent_id = fields.Many2one('hr.employee', string='Supervisor', index=True, ondelete='set null')

    employee_code = fields.Char(string='Employee ID')
    grade = fields.Char(string='Grade')
    division_title = fields.Char(string='Division')
    location = fields.Char(string='Location')
    review_date_from = fields.Date(string='Review Date From')
    review_date_to = fields.Date(string='Review Date To')
    assessment_last_year = fields.Text(string='Assessment of Last Year')
    last_promotion_year = fields.Char(string='Last Promotion Year')
    highest_education = fields.Char(string='Highest Education')
    joining_date = fields.Date(string='Date of Joining')
    length_of_service = fields.Char(string='Length of Service', compute='_compute_length_of_service', store=True)

    employee_is = fields.Selection([
        ('appraisee', 'Appraisee'),
        ('appraiser', 'Appraiser'),
        ('hr', 'HR'),
        ('other', 'Other'),
    ], string='Employee Is', default='appraisee')

    @api.depends('joining_date')
    def _compute_length_of_service(self):
        for rec in self:
            if rec.joining_date:
                delta = date.today() - rec.joining_date
                years = delta.days // 365
                days = delta.days % 365
                rec.length_of_service = f"{years} years {days} days"
            else:
                rec.length_of_service = ''

    def action_aggregate_subordinates(self):
        """Called when Supervisor clicks 'Checked' button on their form.
           For each of this supervisor's EmployeePerformance records, aggregate from children.
        """
        Perf = self.env['employee.performance']
        for emp in self:
            # find performance records where employee_id == emp
            parent_perfs = Perf.search([('employee_id', '=', emp.id)])
            # for each parent perf, call aggregate_from_children
            for p in parent_perfs:
                p.aggregate_from_children()
        return True
