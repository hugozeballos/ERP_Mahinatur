from odoo import models, fields, api

class TourParticipantWizardLine(models.TransientModel):
    _name = 'tour.participant.wizard.line'
    _description = 'Participante Temporal del Wizard de Tour'

    wizard_id = fields.Many2one(
        'tour.selection.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(string='Nombre del Participante', required=True)
    is_child = fields.Boolean(string='¿Es niño?', default=False)
    almuerzo = fields.Boolean(string='¿Incluir almuerzo?')
    tipo_almuerzo = fields.Selection([
        ('normal', 'Normal'),
        ('vegetariano', 'Vegetariano'),
        ('pescado', 'Pescado (costo extra)'),
    ], string='Tipo de Almuerzo')
    price_total = fields.Float(string='Precio Total', compute='_compute_price_total', store=True)

    @api.depends('is_child', 'almuerzo', 'tipo_almuerzo')
    def _compute_price_total(self):
        """Calcula el precio total según si es niño, incluye almuerzo y tipo."""
        for participant in self:
            price = participant.wizard_id.price_unit_base or 0.0  # Precio base del tour

            if participant.almuerzo:
                price += 30000  # Valor fijo del almuerzo

                if participant.tipo_almuerzo in ['vegetariano', 'pescado']:
                    price += 10000  # Recargo extra por vegetariano o pescado

                # Nota: 'pollo' no tiene recargo adicional

            if participant.is_child:
                price = price * 0.5  # 🚀 TODO el precio final a la mitad si es niño

            participant.price_total = price


    @api.onchange('almuerzo')
    def _onchange_almuerzo(self):
        """Borra el tipo de almuerzo si no quiere almuerzo."""
        for participant in self:
            if not participant.almuerzo:
                participant.tipo_almuerzo = False
