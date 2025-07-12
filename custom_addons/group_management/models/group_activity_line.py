from odoo import models, fields

class GroupActivityLine(models.Model):
    _name = 'group.activity.line'
    _description = 'Group Activity Line'

    group_id        = fields.Many2one('group.management', string='Group', required=True, ondelete='cascade')
    template_id = fields.Many2one('group.activity.template',
                                  string='Actividad',
                                  required=True,
                                  ondelete='cascade')
    scheduled_from  = fields.Datetime(string='Start', required=True)
    scheduled_to    = fields.Datetime(string='End',   required=True)
#    price           = fields.Monetary(related='template_id.price',   readonly=True)
    duration = fields.Float(
        related='template_id.default_duration',
        readonly=True,
        string='Duración (hrs)'
    )
    state           = fields.Selection([('draft','Draft'),('generated','Generated')], default='draft')
#    seats           = fields.Integer(string='Plazas', default=1, required=True)
    requires_guide      = fields.Boolean(
         related='template_id.requires_guide', readonly=True)
    requires_transport  = fields.Boolean(
         related='template_id.requires_transport', readonly=True)
    requires_cook      = fields.Boolean(
         related='template_id.requires_cook', readonly=True)
    requires_waiter  = fields.Boolean(
         related='template_id.requires_waiter', readonly=True)
    
    price_per_seat = fields.Monetary(
        related='template_id.price_per_seat',
        readonly=True,
        string='Precio por Persona'
    )
    currency_id = fields.Many2one(
        related='template_id.currency_id',
        readonly=True
    )