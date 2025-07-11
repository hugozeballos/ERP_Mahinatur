# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_vehicle_rental = fields.Boolean(related='vehicle_id.is_available_for_rent', store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehículo asociado")