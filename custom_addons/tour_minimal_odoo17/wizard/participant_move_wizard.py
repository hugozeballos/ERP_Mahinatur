from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class ParticipantMoveWizard(models.TransientModel):
    _name = 'tour.participant.move.wizard'
    _description = 'Mover Participante a Otro Tour'

    participant_id = fields.Many2one('tour.participant', string="Participante", required=True, readonly=True)
    current_tour_id = fields.Many2one(related='participant_id.tour_id', string="Tour Actual", readonly=True)
    new_tour_id = fields.Many2one('tour.minimal', string="Nuevo Tour", domain=[], required=True)
    note = fields.Text(string="Nota")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        participant = self.env['tour.participant'].browse(self.env.context.get('active_id'))
        res['participant_id'] = participant.id
        return res

    @api.onchange('participant_id')
    def _onchange_participant_id(self):
        if not self.participant_id:
            return
        tour_type = self.participant_id.tour_id.tour_type_id
        today = fields.Date.today()
        max_date = today + timedelta(days=30)
        self.new_tour_id = False
        return {
            'domain': {
                'new_tour_id': [
                    ('id', '!=', self.participant_id.tour_id.id),
                    ('tour_type_id', '=', tour_type.id),
                    ('date_start', '>=', today),
                    ('date_start', '<=', max_date),
                    ('state', 'in', ['draft', 'confirmed']),
                ]
            }
        }

    def action_move(self):
        self.ensure_one()
        if not self.new_tour_id:
            raise UserError(_("Debe seleccionar un nuevo tour válido."))

        # Validar cupo
        if len(self.new_tour_id.participants_ids) >= self.new_tour_id.max_capacity:
            raise UserError(_("El tour seleccionado ya no tiene cupos disponibles."))

        # Mover participante
        self.participant_id.tour_id = self.new_tour_id

        if self.note:
            self.participant_id.message_post(body=_("Reubicado manualmente: %s" % self.note))

        return {'type': 'ir.actions.act_window_close'}
