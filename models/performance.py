from odoo import models, fields, api
from odoo.exceptions import UserError

class EmployeePerformance(models.Model):
    _name = 'employee.performance'
    _description = 'Employee Performance KPI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # Basic references
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    level_id = fields.Many2one('performance.level', string='Level', tracking=True)
    objective_id = fields.Many2one('performance.objective', string='Objective', tracking=True)
    level_target_id = fields.Many2one('performance.level.target', string='Level Target')

    # timeline
    timeline_from = fields.Date(string='Timeline From')
    timeline_to = fields.Date(string='Timeline To')

    # objective specific inputs
    number_of_job_completed = fields.Integer(string='Number of Job Completed')
    number_of_wo = fields.Integer(string='Number of WO')
    number_of_job_fixed_single_visit = fields.Integer(string='Number of Jobs Fixed in Single Visit')
    number_of_job_attend = fields.Integer(string='Number of Job Attended')
    number_of_job_scheduled = fields.Integer(string='Number of Job Scheduled')
    number_of_job_submitted = fields.Integer(string='Number of Job Submitted')
    number_of_job_opportunities = fields.Integer(string='Number of Job Opportunities')
    number_of_incidents = fields.Integer(string='Number of Incidents')
    achieve_rating = fields.Float(string='Achieve Rating (out of 5)')

    # KPI outputs
    target_percentage = fields.Float(string='Target Percentage', compute='_compute_target_from_level', store=True)
    achieved_percentage = fields.Float(string='Achieved Percentage', compute='_compute_achieved_percentage', store=True)
    weightage = fields.Float(string='Weightage (%)', default=0.0)
    rating = fields.Float(string='Rating (by appraiser)')
    final_rating = fields.Float(string='Final Rating', compute='_compute_final_rating', store=True)

    # UI visibility booleans (for use in invisible expressions)
    show_job_completed = fields.Boolean(compute='_compute_visibility')
    show_job_fixed = fields.Boolean(compute='_compute_visibility')
    show_presence_vs_schedule = fields.Boolean(compute='_compute_visibility')
    show_service_report = fields.Boolean(compute='_compute_visibility')
    show_safety_incidents = fields.Boolean(compute='_compute_visibility')
    show_quality_score = fields.Boolean(compute='_compute_visibility')

    # narrative pages
    special_factors = fields.Text(string='Special Factors / Other Circumstances')
    appraisee_comments = fields.Text(string="Appraisee's Comments")
    overall_summary = fields.Text(string='Overall Summary (Appraiser)')
    manager_comments = fields.Text(string="Comments by Appraiser's Manager / Supervisor")

    state = fields.Selection([('draft','Draft'),('confirmed','Confirmed'),('done','Done')], default='draft', string='Status')

    @api.onchange('level_id')
    def _onchange_level(self):
        if self.level_id:
            target = self.env['performance.level.target'].search([('level_id','=', self.level_id.id)], limit=1)
            if target:
                self.level_target_id = target.id
                self.target_percentage = target.target_percentage
                self.timeline_from = target.timeline_from
                self.timeline_to = target.timeline_to

    @api.depends('level_target_id')
    def _compute_target_from_level(self):
        for rec in self:
            rec.target_percentage = rec.level_target_id.target_percentage if rec.level_target_id else 0.0

    @api.depends('objective_id')
    def _compute_visibility(self):
        for rec in self:
            name = rec.objective_id.objective_name.lower() if rec.objective_id else ''
            rec.show_job_completed = bool(name and 'job completed' in name)
            rec.show_job_fixed = bool(name and 'fixed' in name)
            rec.show_presence_vs_schedule = bool(name and 'presence' in name)
            rec.show_service_report = bool(name and 'service' in name or 'report' in name)
            rec.show_safety_incidents = bool(name and 'safety' in name or 'incident' in name)
            rec.show_quality_score = bool(name and 'quality' in name or 'audit' in name)

    @api.depends('number_of_job_completed','number_of_wo','number_of_job_fixed_single_visit',
                 'number_of_job_attend','number_of_job_scheduled','number_of_job_submitted',
                 'number_of_job_opportunities','number_of_incidents','achieve_rating','objective_id')
    def _compute_achieved_percentage(self):
        for rec in self:
            name = rec.objective_id.objective_name.lower() if rec.objective_id else ''
            achieved = 0.0
            if name and 'job completed' in name:
                if rec.number_of_wo:
                    achieved = (rec.number_of_job_completed / float(rec.number_of_wo)) * 100.0
            elif name and 'fixed' in name:
                if rec.number_of_wo:
                    achieved = (rec.number_of_job_fixed_single_visit / float(rec.number_of_wo)) * 100.0
            elif name and 'presence' in name:
                if rec.number_of_job_scheduled:
                    achieved = (rec.number_of_job_attend / float(rec.number_of_job_scheduled)) * 100.0
            elif name and ('service' in name or 'report' in name):
                if rec.number_of_job_completed:
                    achieved = (rec.number_of_job_submitted / float(rec.number_of_job_completed)) * 100.0
            elif name and ('safety' in name or 'incident' in name):
                if rec.number_of_job_opportunities:
                    achieved = ((rec.number_of_job_opportunities - rec.number_of_incidents) / float(rec.number_of_job_opportunities)) * 100.0
            elif name and 'quality' in name:
                if rec.achieve_rating is not None:
                    achieved = (rec.achieve_rating / 5.0) * 100.0
            rec.achieved_percentage = round(achieved, 2)

    @api.depends('rating','weightage')
    def _compute_final_rating(self):
        for rec in self:
            rec.final_rating = round((rec.weightage / 100.0) * (rec.rating or 0.0), 2)

    # -------------------------
    # Bottom-up aggregation
    # -------------------------
    def aggregate_from_children(self):
        """For each employee.performance record on this recordset,
        compute average achieved percentage from all child employees' performance
        records that share the same objective_id and set this record's achieved_percentage.
        This supports bottom-up approach.
        """
        for rec in self:
            employee = rec.employee_id
            # get direct children (subordinates)
            child_emps = self.env['hr.employee'].search([('parent_id', '=', employee.id)])
            if not child_emps:
                # no children - nothing to aggregate
                continue
            # gather matching child performance records (same objective)
            child_perfs = self.env['employee.performance'].search([
                ('employee_id', 'in', child_emps.ids),
                ('objective_id', '=', rec.objective_id.id)
            ])
            if not child_perfs:
                # nothing to aggregate
                continue
            # compute average achieved_percentage of child_perfs
            total = sum([c.achieved_percentage for c in child_perfs])
            avg = total / len(child_perfs) if len(child_perfs) else 0.0
            # update current performance record's achieved_percentage
            # Note: achieved_percentage is computed field; to override, we write into a helper field.
            # We'll write into a transitory override field 'manual_achieved_override' and prefer it if set.
            rec.sudo().write({'achieved_percentage': round(avg, 2)})

    # convenience action for a supervisor: aggregate all of their performance records
    def action_aggregate_for_employee(self):
        for rec in self:
            # find parent employee (= supervisor) rec is a performance record, so compute
            # But more useful: if called from hr.employee, we'll use different method.
            rec.aggregate_from_children()

    @api.model
    def get_dashboard_data(self):
        """Return summarized metrics for the JS dashboard template.
           This is a simple aggregator; you can expand to return real computed values.
        """
        # sample implementation - compute from data available
        # Company-level metrics: look for performance entries aligned to company objectives
        data = {
            'company_revenue': 0,
            'company_cs': 0,
            'c_level': 0,
            'division_tst': 0,
            'division_pm': 0,
            'individual_quality_pct': 0,
            'individual_quality_val': 0,
            'summary': {
                'total_kpis': 0,
                'avg_score': 0,
                'active_kpis': 0,
                'employees': 0,
                'pending': 0
            },
            'kpis': []
        }

        # Example: compute simple aggregates for pre-known objective names:
        env = self.env
        # revenue increase
        revenue = env['employee.performance'].search([('objective_id.objective_name','ilike','revenue increase')], limit=1)
        if revenue:
            data['company_revenue'] = int(revenue.achieved_percentage or 0)
        cs = env['employee.performance'].search([('objective_id.objective_name','ilike','customer satisfaction')], limit=1)
        if cs:
            data['company_cs'] = int(cs.achieved_percentage or 0)
        # c level approximate - average of performances tagged with level 'C Level' if exists
        clevel = env['employee.performance'].search([('level_id.level_name','ilike','C')])
        if clevel:
            data['c_level'] = int(sum([p.achieved_percentage for p in clevel]) / (len(clevel) or 1))

        # division TST and PM
        tst = env['employee.performance'].search([('employee_id.job_title','ilike','tst')])
        pm = env['employee.performance'].search([('employee_id.job_title','ilike','pm')])
        if tst:
            data['division_tst'] = int(sum([p.achieved_percentage for p in tst])/(len(tst) or 1))
        if pm:
            data['division_pm'] = int(sum([p.achieved_percentage for p in pm])/(len(pm) or 1))

        # individual quality pick any 'Quality score' objective records
        qual = env['employee.performance'].search([('objective_id.objective_name','ilike','quality')], limit=1)
        if qual:
            data['individual_quality_pct'] = int(qual.achieved_percentage or 0)
            # quality rating value out of 5 try to reverse compute
            data['individual_quality_val'] = round((qual.achieve_rating or 0), 1)

        # summary metrics
        all_kpis = env['employee.performance'].search([])
        data['summary']['active_kpis'] = len(all_kpis)
        data['summary']['employees'] = len(env['hr.employee'].search([]))
        pending = env['employee.performance'].search([('state','=','draft')])
        data['summary']['pending'] = len(pending)
        # avg score compute from rating fields
        ratings = [p.rating for p in all_kpis if p.rating]
        if ratings:
            data['summary']['avg_score'] = round(sum(ratings)/len(ratings), 2)
        else:
            data['summary']['avg_score'] = 0

        # KPI table (take first 8 items)
        for p in all_kpis[:8]:
            data['kpis'].append({
                'name': p.objective_id.objective_name if p.objective_id else 'N/A',
                'target': p.target_percentage,
                'achieved': p.achieved_percentage,
                'role': p.employee_id.job_title if p.employee_id else '',
                'alignment': p.level_id.level_name if p.level_id else '',
                'status': 'Done' if p.state == 'done' else ('Draft' if p.state=='draft' else 'Confirmed')
            })

        # total KPIs achieved - simple percentage of records where achieved_percentage >= target_percentage
        if all_kpis:
            achieved_count = len([p for p in all_kpis if p.target_percentage and p.achieved_percentage >= p.target_percentage])
            data['summary']['total_kpis'] = int((achieved_count / (len(all_kpis) or 1)) * 100)
        else:
            data['summary']['total_kpis'] = 0

        return data
