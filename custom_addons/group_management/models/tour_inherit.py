from odoo import models, fields

class TourMinimalInherited(models.Model):
    _inherit = 'tour.minimal'

    group_id = fields.Many2one(
        'group.management',
        string='Grupo',
        ondelete='set null',
    )
    template_id = fields.Many2one(
        'group.activity.template',
        string='Plantilla',
        readonly=True,
        ondelete='set null',
    )
