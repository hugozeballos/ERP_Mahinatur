# models/kitchen_special_event.py
from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)
from dateutil.relativedelta import relativedelta


class KitchenSpecialEvent(models.Model):
    _name = 'kitchen.special.event'
    _description = 'Evento Especial de Cocina'

    name = fields.Char(string='Nombre del Evento')
    date = fields.Date(string='Fecha', required=True)
    location = fields.Char(string='Ubicación')
    expected_people = fields.Integer(string='Nº de Personas Esperadas')
    notes = fields.Text(string='Notas')

    tour_ids = fields.Many2many('tour.minimal', string='Tours Relacionados', compute='_compute_tour_ids', store=True)
    participant_ids = fields.Many2many('tour.participant', string='Participantes', compute='_compute_participant_ids', store=True)

    cooks_ids = fields.Many2many(
        'res.partner', 
        'kitchen_special_event_cook_rel', 
        'event_id', 'partner_id',
        string='Cocineros'
    )

    waiters_ids = fields.Many2many(
        'res.partner', 
        'kitchen_special_event_waiter_rel', 
        'event_id', 'partner_id',
        string='Garzones'
    )

    
    participant_count = fields.Integer(
        string='Cantidad de Participantes',
        compute='_compute_participant_count',
        store=True
    )

    # @api.depends('date')
    # def _compute_tour_ids(self):
    #     for record in self:
    #         if record.date:
    #             tours = self.env['tour.minimal'].search([
    #                 ('date_start', '>=', record.date),
    #                 ('date_start', '<', record.date + fields.Date.delta(days=1)),
    #             ])
    #             record.tour_ids = tours

    @api.model
    def action_actualizar_todos_eventos(self):
        tours = self.env['tour.minimal'].search([
            ('date_start', '!=', False),
            ('requires_cook', '=', True)
        ])

        for tour in tours:
            # Evitar duplicados si ya existe un evento con este tour
            if not self.search([('tour_ids', 'in', [tour.id])]):
                self.create({
                    'name': tour.name,
                    'date': tour.date_start.date(),
                    'expected_people': len(tour.participants_ids),
                    'tour_ids': [(6, 0, [tour.id])],
                    'participant_ids': [(6, 0, tour.participants_ids.ids)],
                    'cooks_ids': [(6, 0, tour.cook_id.ids)],
                    'waiters_ids': [(6, 0, tour.waiters_id.ids)],
                })

    @api.depends('tour_ids')
    def _compute_participant_ids(self):
        for record in self:
            participants = self.env['tour.participant'].search([
                ('tour_id', 'in', record.tour_ids.ids)
            ])
            record.participant_ids = participants

    @api.depends('participant_ids')
    def _compute_participant_count(self):
        for record in self:
            record.participant_count = len(record.participant_ids)
