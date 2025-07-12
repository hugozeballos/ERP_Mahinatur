# models/rental_return_wizard.py
from odoo import api, fields, models, _
from datetime import timedelta
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class RentalReturnWizard(models.TransientModel):
    _name = "rental.return.wizard"
    _description = "Wizard Devolver vehículo"

    booking_id = fields.Many2one(
        "rental.booking", required=True, string="Reserva", readonly=True
    )
    extra_hours     = fields.Float(string="Horas de atraso", default=0.0)
    charge_late     = fields.Boolean(string="Cobrar atraso", default=True)
    reason_no_charge = fields.Text(string="Motivo no cobro")


    @api.constrains("charge_late", "reason_no_charge")
    def _check_reason(self):
        for rec in self:
            if not rec.charge_late and not rec.reason_no_charge:
                raise UserError(_("Debe indicar un motivo para no cobrar el atraso."))


    def action_confirm_wizard(self):

        self.ensure_one()
        booking = self.booking_id
        _logger.warning("Wizard de devolución: booking_id=%s, estado previo=%s", booking.id, booking.state)


                # ⚠️ Validar que la reserva esté entregada (rented)
        if booking.state != 'rented':
            raise UserError(
                _("Solo se puede devolver si la reserva está en estado 'Entregada'.")
            )
        vals = {
            'state': 'returned',
        }
        vehicle_vals = {
            'rental_status': 'available',
        }

        if self.charge_late and self.extra_hours > 0:
            hours_to_charge = int(self.extra_hours) if self.extra_hours.is_integer() else int(self.extra_hours) + 1
            booking._create_late_charge_so(hours_to_charge)
        elif not self.charge_late:
            #booking._create_late_charge_so(hours_to_charge=0, force_reason=self.reason_no_charge)
            booking.write({
                'no_charge_delay': True,
                'delay_hours': self.extra_hours,
                'no_charge_reason': self.reason_no_charge or _('(sin motivo)'),
            })

        _logger.warning("Devolviendo reserva %s", booking.id)
        booking.write({'state': 'returned'})
        booking.vehicle_id.write({'rental_status': 'available'})

        return {"type": "ir.actions.act_window_close"}