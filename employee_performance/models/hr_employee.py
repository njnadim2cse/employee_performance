from odoo import models, fields, api
from datetime import date

class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    # Change label from Manager to Supervisor
    parent_id = fields.Many2one('hr.employee', string='Supervisor', index=True, ondelete='set null')
    
    # New field for team members
    team_member_ids = fields.One2many(
        'hr.employee', 
        'parent_id', 
        string='Team Members',
        compute='_compute_team_members'
    )
    
    # New fields
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

    # Overall rating from KPI
    overall_rating = fields.Float(string='Overall Rating', compute='_compute_overall_rating', store=True)

    @api.depends('joining_date')
    def _compute_length_of_service(self):
        for rec in self:
            if rec.joining_date:
                delta = date.today() - rec.joining_date
                years = delta.days // 365
                months = (delta.days % 365) // 30
                days = (delta.days % 365) % 30
                if years > 0:
                    rec.length_of_service = f"{years} years {months} months {days} days"
                elif months > 0:
                    rec.length_of_service = f"{months} months {days} days"
                else:
                    rec.length_of_service = f"{days} days"
            else:
                rec.length_of_service = ''

    @api.depends()
    def _compute_overall_rating(self):
        """Compute overall rating from KPI records"""
        for rec in self:
            # Search for the latest KPI record for this employee
            kpi_record = self.env['employee.kpi'].search([
                ('employee_id', '=', rec.id)
            ], order='create_date desc', limit=1)
            
            if kpi_record and kpi_record.overall_rating > 0:
                rec.overall_rating = kpi_record.overall_rating
            else:
                rec.overall_rating = 0.0
                
    def _compute_team_members(self):
        """Auto compute team members from child_ids"""
        for rec in self:
            rec.team_member_ids = rec.child_ids

    def action_aggregate_subordinates(self):
        """Called when Supervisor clicks 'Checked' button to aggregate from children"""
        Performance = self.env['employee.performance']
        KPI = self.env['employee.kpi']
        
        for emp in self:
            # Aggregate performance records
            parent_perfs = Performance.search([('employee_id', '=', emp.id)])
            for p in parent_perfs:
                p.aggregate_from_children()
            
            # Aggregate KPI records
            parent_kpis = KPI.search([('employee_id', '=', emp.id)])
            for k in parent_kpis:
                k.aggregate_from_children()
                
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Aggregation Complete',
                'message': 'Subordinates data has been aggregated successfully.',
                'type': 'success',
                'sticky': False,
            }
        }