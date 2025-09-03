from odoo import models, fields

class TourFlight(models.Model):
    _name = 'tour.flight'
    _description = 'Vuelo (Catálogo)'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'El nombre del vuelo ya existe.')
    ]
