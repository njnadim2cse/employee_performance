from odoo import models, fields, api

class PerformanceLevel(models.Model):
    _name = 'performance.level'
    _description = 'Level / Role'
    _rec_name = 'level_name'

    level_seq = fields.Char(string='LevelID', readonly=True, copy=False)
    level_name = fields.Char(string='Level Name', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('level_seq'):
                seq = self.env['ir.sequence'].sudo().next_by_code('performance.level') or 'NEW'
                vals['level_seq'] = seq
        return super().create(vals_list)


class PerformanceObjective(models.Model):
    _name = 'performance.objective'
    _description = 'Performance Objective'
    _rec_name = 'objective_name'

    objective_seq = fields.Char(string='ObjectiveID', readonly=True, copy=False)
    objective_name = fields.Char(string='Objective Name', required=True)
    description = fields.Text(string='Description')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('objective_seq'):
                seq = self.env['ir.sequence'].sudo().next_by_code('performance.objective') or 'NEW'
                vals['objective_seq'] = seq
        return super().create(vals_list)


class PerformanceLevelTarget(models.Model):
    _name = 'performance.level.target'
    _description = 'Level wise target'

    level_id = fields.Many2one('performance.level', string='Level', required=True)
    objective_id = fields.Many2one('performance.objective', string='Objective', required=True)
    target_percentage = fields.Float(string='Target Percentage')
    timeline_from = fields.Date(string='Timeline From')
    timeline_to = fields.Date(string='Timeline To')