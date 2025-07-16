from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import ValidationError

#Modelo para chekear disponibilidad de vehiculos
class VehicleAvailabilityWizard(models.TransientModel):
    _name = 'vehicle.availability.wizard'
    _description = 'Buscar Disponibilidad de Vehículos'

    start_date = fields.Date(string='Fecha inicio', required=True)
    end_date = fields.Date(string='Fecha término', required=True)

    def action_check_availability(self):
        self.ensure_one()
        start_date = self.start_date
        end_date = self.end_date

        if end_date < start_date:
            raise ValidationError("La fecha de término debe ser igual o posterior a la fecha de inicio.")

        vehicles = self.env['fleet.vehicle'].search([])

        available_vehicles = vehicles.filtered(lambda v: all(
            booking.state in ['cancelled', 'returned'] or
            booking.date_end.date() < start_date or
            booking.date_start.date() > end_date
            for booking in v.rental_booking_ids
        ) and v.is_available_for_rent)

        return {
            'type': 'ir.actions.act_window',
            'name': f'Autos disponibles del {start_date} al {end_date}',
            'res_model': 'fleet.vehicle',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', available_vehicles.ids)],
            'context': dict(self.env.context),
            'target': 'new',
        }