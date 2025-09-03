from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'
    is_hotel = fields.Boolean('Es hotel', required=False)
