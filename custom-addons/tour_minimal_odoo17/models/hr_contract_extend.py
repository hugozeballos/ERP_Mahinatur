from odoo import models, fields

class HrContract(models.Model):
    _inherit = "hr.contract"

    # Añadimos la moneda al contrato en Community
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id.id,
        required=True,
    )
