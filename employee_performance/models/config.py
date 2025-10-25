from odoo import models, fields, api

class PerformanceLevel(models.Model):
    _name = 'performance.level'
    _description = 'Performance Level'
    _rec_name = 'name'

    name = fields.Char(string='Level Name', required=True)
    parent_level_id = fields.Many2one('performance.level', string='Parent Level')
    res_employee_ids = fields.Many2many('hr.employee', string='Responsible Employees')
    number_of_res_employees = fields.Integer(string='Number of Responsible Employees', compute='_compute_res_employees_count', store=True)
    
    # Objectives lines
    objective_line_ids = fields.One2many('performance.level.objective.line', 'level_id', string='Objectives')

    @api.depends('res_employee_ids')
    def _compute_res_employees_count(self):
        for rec in self:
            rec.number_of_res_employees = len(rec.res_employee_ids)


class PerformanceLevelObjectiveLine(models.Model):
    _name = 'performance.level.objective.line'
    _description = 'Level Objective Line'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default=1)
    level_id = fields.Many2one('performance.level', string='Level', required=True, ondelete='cascade')
    objective_id = fields.Many2one('performance.objective', string='Objective', required=True)
    target_percentage = fields.Float(string='Target Percentage')
    timeline_from = fields.Date(string='From')
    timeline_to = fields.Date(string='To')
    timeline_duration = fields.Char(string='Timeline', compute='_compute_timeline_duration', store=True)

    @api.depends('timeline_from', 'timeline_to')
    def _compute_timeline_duration(self):
        for rec in self:
            if rec.timeline_from and rec.timeline_to:
                delta = rec.timeline_to - rec.timeline_from
                years = delta.days // 365
                months = (delta.days % 365) // 30
                days = (delta.days % 365) % 30
                
                if years > 0:
                    rec.timeline_duration = f"{years} years {months} months {days} days"
                elif months > 0:
                    rec.timeline_duration = f"{months} months {days} days"
                else:
                    rec.timeline_duration = f"{days} days"
            else:
                rec.timeline_duration = ''


class PerformanceObjective(models.Model):
    _name = 'performance.objective'
    _description = 'Performance Objective'
    _rec_name = 'name'

    name = fields.Char(string='Objective Name', required=True)
    description = fields.Text(string='Description')
    
    # Field visibility control - set defaults manually for now
    show_job_completed = fields.Boolean(string='Show Job Completed Fields', default=False)
    show_job_fixed = fields.Boolean(string='Show Job Fixed Fields', default=False)
    show_presence_schedule = fields.Boolean(string='Show Presence vs Schedule', default=False)
    show_service_reports = fields.Boolean(string='Show Service Reports', default=False)
    show_safety_incidents = fields.Boolean(string='Show Safety Incidents', default=False)
    show_quality_score = fields.Boolean(string='Show Quality Score', default=False)
    show_revenue = fields.Boolean(string='Show Revenue Fields', default=False)