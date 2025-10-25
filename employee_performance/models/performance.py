from odoo import models, fields, api
from odoo.exceptions import UserError

class EmployeePerformance(models.Model):
    _name = 'employee.performance'
    _description = 'Employee Performance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # Name field with employee name format
    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    
    # Basic references
    employee_id = fields.Many2one('hr.employee', string='Employee Name', required=True, tracking=True)
    supervisor_id = fields.Many2one('hr.employee', string='Supervisor', compute='_compute_supervisor', store=True)
    level_id = fields.Many2one('performance.level', string='Level Name', required=True, tracking=True)
    
    # State
    state = fields.Selection([
        ('draft','Draft'),
        ('checked','Checked'),
        ('confirmed','Confirmed'),
        ('done','Done')
    ], default='draft', string='Status', tracking=True)
    
    # Performance lines (one per objective)
    performance_line_ids = fields.One2many('employee.performance.line', 'performance_id', string='Performance Lines')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Get employee name
                employee_id = vals.get('employee_id')
                if employee_id:
                    employee = self.env['hr.employee'].browse(employee_id)
                    vals['name'] = f"Perf/{employee.name}"
                else:
                    vals['name'] = "Perf/New"
        return super().create(vals_list)

    @api.depends('employee_id.parent_id')
    def _compute_supervisor(self):
        for rec in self:
            rec.supervisor_id = rec.employee_id.parent_id

    @api.onchange('level_id')
    def _onchange_level_id(self):
        """Auto-create performance lines based on level objectives"""
        if self.level_id and self.level_id.objective_line_ids:
            # Clear existing lines
            self.performance_line_ids = [(5, 0, 0)]
            
            # Create new lines from level objectives
            lines = []
            for objective_line in self.level_id.objective_line_ids:
                lines.append((0, 0, {
                    'objective_id': objective_line.objective_id.id,
                    'target_percentage': objective_line.target_percentage,
                    'timeline_from': objective_line.timeline_from,
                    'timeline_to': objective_line.timeline_to,
                }))
            self.performance_line_ids = lines

    def aggregate_from_children(self):
        """Bottom-up aggregation from child employees"""
        for rec in self:
            employee = rec.employee_id
            child_emps = self.env['hr.employee'].search([('parent_id', '=', employee.id)])
            
            if not child_emps:
                continue
                
            for perf_line in rec.performance_line_ids:
                # Find matching child performance records
                child_perf_lines = self.env['employee.performance.line'].search([
                    ('performance_id.employee_id', 'in', child_emps.ids),
                    ('objective_id', '=', perf_line.objective_id.id),
                    ('achieved_percentage', '>', 0)
                ])
                
                if child_perf_lines:
                    # Calculate average achieved percentage
                    total_achieved = sum(line.achieved_percentage for line in child_perf_lines)
                    avg_achieved = total_achieved / len(child_perf_lines)
                    perf_line.achieved_percentage = round(avg_achieved, 2)
            
            # Mark as checked
            rec.state = 'checked'

    def action_mark_checked(self):
        """Manual check button"""
        self.aggregate_from_children()
        self.state = 'checked'
    
    @api.model
    def get_dashboard_data(self):
        """Return summarized metrics for the JS dashboard"""
        env = self.env
        
        # Get all levels and their performance
        levels = env['performance.level'].search([])
        level_data = {}
        
        for level in levels:
            # Get performance records for this level
            perfs = self.search([('level_id', '=', level.id)])
            if perfs:
                total_achieved = sum(perfs.performance_line_ids.mapped('achieved_percentage'))
                avg_achieved = total_achieved / len(perfs.performance_line_ids) if perfs.performance_line_ids else 0
                level_data[level.name.lower().replace(' ', '_')] = round(avg_achieved, 2)
        
        # Calculate TST Overall Rating
        tst_kpis = env['employee.kpi'].search([('level_id.name', 'ilike', 'TST Individual')])
        tst_overall_rating = 0.0
        if tst_kpis:
            tst_overall_rating = round(sum(tst_kpis.mapped('overall_rating')) / len(tst_kpis), 1)
        
        # Calculate PM Overall Rating
        pm_kpis = env['employee.kpi'].search([('level_id.name', 'ilike', 'PM Individual')])
        pm_overall_rating = 0.0
        if pm_kpis:
            pm_overall_rating = round(sum(pm_kpis.mapped('overall_rating')) / len(pm_kpis), 1)
        
        # Get KPI data for dashboard
        kpi_data = []
        kpi_records = env['employee.kpi'].search([], limit=10)
        for kpi in kpi_records:
            kpi_data.append({
                'employee_name': kpi.employee_id.name,
                'responsible_role': kpi.employee_id.job_title or kpi.employee_id.job_id.name or '',
                'level_name': kpi.level_id.name,
                'overall_rating': kpi.overall_rating,
                'status': 'Done' if kpi.state == 'done' else ('Draft' if kpi.state == 'draft' else 'Confirmed')
            })
        
        # Sample data structure
        data = {
            'company_revenue': level_data.get('company_level', 0),
            'company_cs': level_data.get('company_level', 0),
            'c_level': level_data.get('c_level', 0),
            'division_tst': level_data.get('tst_division_level', 0),
            'division_pm': level_data.get('pm_division_level', 0),
            'tst_overall_rating': tst_overall_rating,
            'pm_overall_rating': pm_overall_rating,
            'summary': {
                'total_kpis': len(self.search([])),
                'avg_score': 0.0,
                'active_kpis': len(self.search([('state', '!=', 'done')])),
                'employees': len(env['hr.employee'].search([])),
                'pending': len(self.search([('state', '=', 'draft')])),
            },
            'performance_details': kpi_data
        }
        
        return data


class EmployeePerformanceLine(models.Model):
    _name = 'employee.performance.line'
    _description = 'Employee Performance Line'

    performance_id = fields.Many2one('employee.performance', string='Performance', required=True, ondelete='cascade')
    objective_id = fields.Many2one('performance.objective', string='Objective', required=True)
    target_percentage = fields.Float(string='Target Percentage')
    achieved_percentage = fields.Float(string='Achieved Percentage', compute='_compute_achieved_percentage', store=True)
    
    # Timeline
    timeline_from = fields.Date(string='Timeline From')
    timeline_to = fields.Date(string='Timeline To')
    
    # Objective-specific fields
    number_of_job_completed = fields.Integer(string='Number of Job Completed')
    number_of_wo = fields.Integer(string='Number of WO')
    number_of_job_fixed_single_visit = fields.Integer(string='Number of Jobs Fixed in Single Visit')
    number_of_job_attend = fields.Integer(string='Number of Job Attended')
    number_of_job_scheduled = fields.Integer(string='Number of Job Scheduled')
    number_of_job_submitted = fields.Integer(string='Number of Job Submitted')
    number_of_job_opportunities = fields.Integer(string='Number of Job Opportunities')
    number_of_incidents = fields.Integer(string='Number of Incidents')
    achieve_rating = fields.Float(string='Achieve Rating (out of 5)')
    
    # Revenue fields for Company Level
    previous_year_revenue = fields.Float(string='Previous Year Revenue')
    current_year_revenue = fields.Float(string='Current Year Revenue')
    revenue_increased = fields.Float(string='Revenue Increased %', compute='_compute_revenue_increased', store=True)

    # UI visibility
    show_job_completed = fields.Boolean(compute='_compute_visibility')
    show_job_fixed = fields.Boolean(compute='_compute_visibility')
    show_presence_schedule = fields.Boolean(compute='_compute_visibility')
    show_service_reports = fields.Boolean(compute='_compute_visibility')
    show_safety_incidents = fields.Boolean(compute='_compute_visibility')
    show_quality_score = fields.Boolean(compute='_compute_visibility')
    show_revenue = fields.Boolean(compute='_compute_visibility')

    @api.depends('objective_id')
    def _compute_visibility(self):
        for rec in self:
            objective = rec.objective_id
            rec.show_job_completed = objective.show_job_completed
            rec.show_job_fixed = objective.show_job_fixed
            rec.show_presence_schedule = objective.show_presence_schedule
            rec.show_service_reports = objective.show_service_reports
            rec.show_safety_incidents = objective.show_safety_incidents
            rec.show_quality_score = objective.show_quality_score
            rec.show_revenue = objective.show_revenue

    @api.depends('number_of_job_completed', 'number_of_wo', 'number_of_job_fixed_single_visit',
                 'number_of_job_attend', 'number_of_job_scheduled', 'number_of_job_submitted',
                 'number_of_job_opportunities', 'number_of_incidents', 'achieve_rating',
                 'previous_year_revenue', 'current_year_revenue', 'objective_id')
    def _compute_achieved_percentage(self):
        for rec in self:
            achieved = 0.0
            
            if rec.show_job_completed and rec.number_of_wo > 0:
                achieved = (rec.number_of_job_completed / float(rec.number_of_wo)) * 100.0
            elif rec.show_job_fixed and rec.number_of_wo > 0:
                achieved = (rec.number_of_job_fixed_single_visit / float(rec.number_of_wo)) * 100.0
            elif rec.show_presence_schedule and rec.number_of_job_scheduled > 0:
                achieved = (rec.number_of_job_attend / float(rec.number_of_job_scheduled)) * 100.0
            elif rec.show_service_reports and rec.number_of_job_completed > 0:
                achieved = (rec.number_of_job_submitted / float(rec.number_of_job_completed)) * 100.0
            elif rec.show_safety_incidents and rec.number_of_job_opportunities > 0:
                achieved = ((rec.number_of_job_opportunities - rec.number_of_incidents) / float(rec.number_of_job_opportunities)) * 100.0
            elif rec.show_quality_score and rec.achieve_rating is not None:
                achieved = (rec.achieve_rating / 5.0) * 100.0
            elif rec.show_revenue and rec.previous_year_revenue > 0:
                achieved = rec.revenue_increased
            
            rec.achieved_percentage = round(achieved, 2)

    @api.depends('previous_year_revenue', 'current_year_revenue')
    def _compute_revenue_increased(self):
        for rec in self:
            if rec.previous_year_revenue and rec.current_year_revenue and rec.previous_year_revenue > 0:
                rec.revenue_increased = ((rec.current_year_revenue - rec.previous_year_revenue) / rec.previous_year_revenue) * 100
            else:
                rec.revenue_increased = 0.0