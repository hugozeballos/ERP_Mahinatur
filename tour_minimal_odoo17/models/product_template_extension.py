# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_tour_ticket = fields.Boolean(string="Es Cupo de Tour")
    tour_id = fields.Many2one('tour.minimal', string="Tour Asociado")
