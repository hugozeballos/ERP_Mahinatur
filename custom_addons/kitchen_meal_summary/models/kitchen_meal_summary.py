from odoo import models, api, fields
from dateutil.relativedelta import relativedelta

class KitchenMealSummary(models.Model):
    _name = 'kitchen.meal.summary'
    _description = 'Resumen Diario de Participantes'

    date = fields.Date(string='Fecha', required=True)
    participant_ids = fields.Many2many('tour.participant', string='Participantes')

    participant_count = fields.Integer(
        string='Cantidad de Participantes',
        compute='_compute_participant_count',
        store=True
    )

    almuerzo_count = fields.Integer(
    string='Con Almuerzo',
    compute='_compute_almuerzo_count',
    store=True
    )

    normal_count = fields.Integer(string='Normal', compute='_compute_tipo_almuerzo_counts', store=True)
    vegetariano_count = fields.Integer(string='Vegetariano', compute='_compute_tipo_almuerzo_counts', store=True)
    pescado_count = fields.Integer(string='Pescado', compute='_compute_tipo_almuerzo_counts', store=True)
    sin_tipo_count = fields.Integer(string='Sin Tipo', compute='_compute_tipo_almuerzo_counts', store=True)

    @api.depends('participant_ids.tipo_almuerzo', 'participant_ids.almuerzo')
    def _compute_tipo_almuerzo_counts(self):
        for record in self:
            normal = vegetariano = pescado = sin_tipo = 0
            for p in record.participant_ids:
                if not p.almuerzo:
                    continue
                if p.tipo_almuerzo == 'normal':
                    normal += 1
                elif p.tipo_almuerzo == 'vegetariano':
                    vegetariano += 1
                elif p.tipo_almuerzo == 'pescado':
                    pescado += 1
                else:
                    sin_tipo += 1
            record.normal_count = normal
            record.vegetariano_count = vegetariano
            record.pescado_count = pescado
            record.sin_tipo_count = sin_tipo
    
    
    @api.depends('participant_ids')
    def _compute_participant_count(self):
        for record in self:
            record.participant_count = len(record.participant_ids)



    @api.depends('participant_ids.almuerzo')
    def _compute_almuerzo_count(self):
        for record in self:
            record.almuerzo_count = sum(1 for p in record.participant_ids if p.almuerzo)

    @api.model
    def action_actualizar_todos_los_resumenes(self):
        tours = self.env['tour.minimal'].search([('date_start', '!=', False)])
        fechas = set(tour.date_start.date() for tour in tours if tour.date_start)

        for fecha in fechas:
            participantes = self.env['tour.participant'].search([
                ('tour_id.date_start', '>=', fecha),
                ('tour_id.date_start', '<', fecha + relativedelta(days=1)),
                ('tour_id.requires_cook', '=', False),
            ])
            resumen = self.search([('date', '=', fecha)], limit=1)
            if not resumen:
                self.create({
                    'date': fecha,
                    'participant_ids': [(6, 0, participantes.ids)],
                })
            else:
                resumen.participant_ids = [(6, 0, participantes.ids)]
