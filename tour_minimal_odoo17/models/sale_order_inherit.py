from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tour_id = fields.Many2one('tour.minimal', string='Tour Relacionado')
