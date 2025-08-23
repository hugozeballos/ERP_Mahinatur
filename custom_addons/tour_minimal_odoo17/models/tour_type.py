# -*- coding: utf-8 -*-
from odoo import models, fields

class TourType(models.Model):
    _name = 'tour.type'
    _description = 'Tipo de Tour'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Selection([
        ('full_day', 'Full Day'),
        ('half_day_am', 'Half Day AM'),
        ('half_day_pm', 'Half Day PM'),
        # agrega otros si los necesitas
    ], required=True, string='Código')
    sequence = fields.Integer(default=10, help='Orden de visualización')
