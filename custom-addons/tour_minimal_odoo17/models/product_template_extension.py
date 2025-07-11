# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_tour_ticket = fields.Boolean(string="Es Cupo de Tour")
    tour_id = fields.Many2one('tour.minimal', string="Tour Asociado")

    # Campos requeridos para POS
    available_in_pos = fields.Boolean(string="Disponible en Punto de Venta", default=True)
    pos_categ_id = fields.Many2one('pos.category', string="Categoría POS")
    is_external = fields.Boolean(string='Producto Externo', help='Si está marcado, se usa el wizard vacío')
