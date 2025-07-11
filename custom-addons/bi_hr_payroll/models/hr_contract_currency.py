from odoo import models, fields

class HrContract(models.Model):
    _inherit = 'hr.contract'

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda del Contrato',
        default=lambda self: self.env.company.currency_id,
        domain=[('active', '=', True)],
        help="Elige en qué moneda se pagará este contrato."
    )