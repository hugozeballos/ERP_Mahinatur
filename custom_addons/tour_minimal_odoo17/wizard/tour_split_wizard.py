from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TourSplitWizard(models.TransientModel):
    _name = 'tour.split.wizard'
    _description = 'Dividir Tour'

    tour_id = fields.Many2one('tour.minimal', required=True, ondelete='cascade', readonly=True)
    capacity_snapshot = fields.Integer(string='Capacidad tomada al confirmar', readonly=True)

    def action_split(self):
        self.ensure_one()
        tour = self.tour_id

        def add_dividido(name: str) -> str:
            n = (name or "").strip()
            lower = n.lower()
            if lower.endswith(" (dividido)") or lower.endswith(" - dividido") or lower.endswith(" dividido"):
                return n
            return f"{n} (Dividido)"

        if not tour:
            raise ValidationError(_("No hay tour asociado."))

        # Corte por snapshot; si viene vacío, cae a max_capacity guardado
        cap = int(self.capacity_snapshot or tour.max_capacity or 0)
        if cap <= 0:
            raise ValidationError(_("Capacidad inválida para dividir."))

        # Ordena y mueve el excedente respecto a 'cap'
        participants = tour.participants_ids.sorted(lambda p: p.id)
        if len(participants) <= cap:
            raise ValidationError(_("No hay participantes excedentes para mover."))

        to_move = participants[cap:]

        # Clonar tour sin recursos y en borrador
        new_tour = tour.copy(default={
            'name': add_dividido(tour.name),
            'vehicle_id': False,
            'driver_id': False,
            'guide_id': False,
            'state': 'draft',
        })

        # Mover excedentes
        to_move.write({'tour_id': new_tour.id})

        # Mensajes opcionales
        if hasattr(tour, 'message_post'):
            tour.message_post(body=_("Se dividió el tour. %s participantes movidos al Tour %s.")
                                   % (len(to_move), new_tour.display_name))
            new_tour.message_post(body=_("Tour creado al dividir. Recibió %s participantes desde %s.")
                                       % (len(to_move), tour.display_name))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tour.minimal',
            'res_id': new_tour.id,
            'view_mode': 'form',
            'target': 'current',
        }
