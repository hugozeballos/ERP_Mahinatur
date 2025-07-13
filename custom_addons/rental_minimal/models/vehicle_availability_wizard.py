from odoo import models, fields, api
from datetime import datetime
#Modelo para chekear disponibilidad de vehiculos
class VehicleAvailabilityWizard(models.TransientModel):
    _name = 'vehicle.availability.wizard'
    _description = 'Buscar Disponibilidad de Vehículos'

    date = fields.Date(string='Fecha de búsqueda', required=True)

    def action_check_availability(self):
        self.ensure_one()
        date_only = self.date  # ya es date, pero lo aclaramos
        date_str = date_only.strftime('%Y-%m-%d')

        vehicles = self.env['fleet.vehicle'].search([])

        available_vehicles = vehicles.filtered(lambda v: all(
            booking.state == 'cancelled' or
            booking.state == 'returned' or
            not (
                booking.date_start.date() <= date_only <= booking.date_end.date()
            )
            for booking in v.rental_booking_ids
        ) and v.is_available_for_rent)

        return {
            'type': 'ir.actions.act_window',
            'name': f'Autos disponibles para {date_str}',
            'res_model': 'fleet.vehicle',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', available_vehicles.ids)],
            'context': dict(self.env.context),
            'target': 'new',
        }