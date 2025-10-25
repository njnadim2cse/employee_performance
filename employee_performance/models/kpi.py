from odoo import models, fields, api

class EmployeeKPI(models.Model):
    _name = 'employee.kpi'
    _description = 'Employee KPI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # Name field with employee name format
    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    
    employee_id = fields.Many2one('hr.employee', string='Employee Name', required=True)
    supervisor_id = fields.Many2one('hr.employee', string='Supervisor', compute='_compute_supervisor', store=True)
    level_id = fields.Many2one('performance.level', string='Level Name', required=True)
    
    # KPI lines
    kpi_line_ids = fields.One2many('employee.kpi.line', 'kpi_id', string='KPI Lines')
    
    # Overall calculations
    total_weightage = fields.Float(string='Total Weightage', compute='_compute_totals', store=True)
    overall_rating = fields.Float(string='Overall Rating', compute='_compute_totals', store=True)
    
    # State
    state = fields.Selection([
        ('draft','Draft'),
        ('checked','Checked'),
        ('confirmed','Confirmed'),
        ('done','Done')
    ], default='draft', string='Status')

    # Comments
    comments_reviews = fields.Html(string='Comments/Reviews')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Get employee name
                employee_id = vals.get('employee_id')
                if employee_id:
                    employee = self.env['hr.employee'].browse(employee_id)
                    vals['name'] = f"KPI/{employee.name}"
                else:
                    vals['name'] = "KPI/New"
        return super().create(vals_list)

    @api.depends('employee_id.parent_id')
    def _compute_supervisor(self):
        for rec in self:
            rec.supervisor_id = rec.employee_id.parent_id

    @api.onchange('level_id')
    def _onchange_level_id(self):
        """Auto-create KPI lines based on level objectives"""
        if self.level_id and self.level_id.objective_line_ids:
            # Clear existing lines
            self.kpi_line_ids = [(5, 0, 0)]
            
            # Create new lines from level objectives
            lines = []
            for objective_line in self.level_id.objective_line_ids:
                # Get achieved percentage from performance records
                achieved_percentage = 0.0
                performance_line = self.env['employee.performance.line'].search([
                    ('performance_id.employee_id', '=', self.employee_id.id),
                    ('objective_id', '=', objective_line.objective_id.id)
                ], limit=1)
                
                if performance_line:
                    achieved_percentage = performance_line.achieved_percentage
                
                lines.append((0, 0, {
                    'objective_id': objective_line.objective_id.id,
                    'achieved_percentage': achieved_percentage,
                    'weightage': 0.0,
                    'rating': 0.0,
                }))
            self.kpi_line_ids = lines

    @api.depends('kpi_line_ids.weightage', 'kpi_line_ids.final_rating')
    def _compute_totals(self):
        for rec in self:
            rec.total_weightage = sum(rec.kpi_line_ids.mapped('weightage'))
            rec.overall_rating = sum(rec.kpi_line_ids.mapped('final_rating'))

    def aggregate_from_children(self):
        """Bottom-up aggregation from child employees"""
        for rec in self:
            employee = rec.employee_id
            child_emps = self.env['hr.employee'].search([('parent_id', '=', employee.id)])
            
            if not child_emps:
                continue
                
            for kpi_line in rec.kpi_line_ids:
                # Find matching child KPI records
                child_kpi_lines = self.env['employee.kpi.line'].search([
                    ('kpi_id.employee_id', 'in', child_emps.ids),
                    ('objective_id', '=', kpi_line.objective_id.id),
                    ('achieved_percentage', '>', 0)
                ])
                
                if child_kpi_lines:
                    # Calculate average achieved percentage
                    total_achieved = sum(line.achieved_percentage for line in child_kpi_lines)
                    avg_achieved = total_achieved / len(child_kpi_lines)
                    kpi_line.achieved_percentage = round(avg_achieved, 2)
            
            # Mark as checked
            rec.state = 'checked'

    def action_mark_checked(self):
        """Manual check button"""
        self.aggregate_from_children()
        self.state = 'checked'


class EmployeeKPILine(models.Model):
    _name = 'employee.kpi.line'
    _description = 'Employee KPI Line'

    kpi_id = fields.Many2one('employee.kpi', string='KPI', required=True, ondelete='cascade')
    objective_id = fields.Many2one('performance.objective', string='Objective', required=True)
    achieved_percentage = fields.Float(string='Achieve Percentage')
    weightage = fields.Float(string='Weightage (%)')
    rating = fields.Float(string='Rating')
    final_rating = fields.Float(string='Final Rating', compute='_compute_final_rating', store=True)

    @api.depends('weightage', 'rating')
    def _compute_final_rating(self):
        for rec in self:
            rec.final_rating = (rec.weightage / 100.0) * rec.rating