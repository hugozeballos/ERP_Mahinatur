from odoo import models, fields, api, _
from datetime import datetime, time
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


#Modelo para chekear disponibilidad de vehiculos
class VehicleAvailabilityWizard(models.TransientModel):
    _name = 'vehicle.availability.wizard'
    _description = 'Buscar Disponibilidad de Vehículos'

    start_date = fields.Datetime(string='Fecha inicio', required=True)
    end_date = fields.Datetime(string='Fecha término', required=True)
    available_vehicle_ids = fields.Many2many('fleet.vehicle', string='Vehículos Disponibles')

    @api.model
    def default_get(self, fields_list):
        """Aplica el dominio dinámico del contexto al campo Many2many al abrir el wizard."""
        res = super().default_get(fields_list)
        domain = self.env.context.get('available_vehicle_domain')
        if domain:
            self = self.with_context(domain_for_available=domain)
        return res

    @api.onchange('available_vehicle_ids')
    def _onchange_available_vehicle_ids(self):
        """Aplica el dominio del contexto cuando se abre el selector de vehículos."""
        domain = self.env.context.get('domain_for_available')
        if domain:
            return {'domain': {'available_vehicle_ids': domain}}



    def create_from_vehicle_action(self):
        """Proxy para crear líneas de venta desde los vehículos seleccionados."""
        sale_order_id = self.env.context.get("default_sale_order_id") or self.sale_order_id.id
        if not sale_order_id:
            raise UserError(_("No se encontró la orden de venta activa."))

        vehicles = self.available_vehicle_ids
        if not vehicles:
            raise UserError(_("No se seleccionaron vehículos."))

        # Construir contexto con fechas y orden
        ctx = {
            "default_sale_order_id": sale_order_id,
            "default_rental_start_date": self.env.context.get("default_rental_start_date"),
            "default_rental_end_date": self.env.context.get("default_rental_end_date"),
        }

        # Llamar al método del modelo sale.order.line con contexto extendido
        self.env["sale.order.line"].with_context(ctx).create_from_vehicle_action(vehicles)
        return {"type": "ir.actions.act_window_close"}

    def action_check_availability(self):
        self.ensure_one()
        start_date = self.start_date
        end_date = self.end_date

        if end_date < start_date:
            raise ValidationError("La fecha de término debe ser igual o posterior a la fecha de inicio.")

        vehicles = self.env['fleet.vehicle'].search([('is_available_for_rent','=',True)])
        print("🔹 Vehículos:", vehicles.ids)


         # 2️⃣ Buscar reservas activas que se solapen con el rango
        #    Regla: hay solape si (start < dt_end) y (end > start_date)
        conflicting_bookings = self.env['rental.booking'].search([
            ('state', 'not in', ['cancelled', 'returned']),
            ('date_start', '<', end_date),
            ('date_end', '>', start_date),
        ])

        # 3️⃣ Obtener los IDs de vehículos en conflicto
        conflicted_vehicle_ids = conflicting_bookings.mapped('vehicle_id.id')
        print("🔹 Vehículos conflictivos:", conflicted_vehicle_ids)


        # 4️⃣ Filtrar disponibles: arrendables - conflictivos
        available_vehicles = vehicles.filtered(lambda v: v.id not in conflicted_vehicle_ids)

        print("🔹 Vehículos disponibles 2:", [(v.id, v.license_plate) for v in available_vehicles])

    
    # 5️⃣ Asignar dominio directamente al campo del wizard
        self.write({'available_vehicle_ids': [(5, 0, 0)]})  # Limpia el campo
        self.write({'available_vehicle_ids': [(6, 0, available_vehicles.ids)]})  # Carga los disponibles


        return {
            'type': 'ir.actions.act_window',
            'name': f'Autos disponibles del {start_date} al {end_date}',
            'res_model': 'vehicle.availability.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'domain': [('id', 'in', available_vehicles.ids)],
            'view_id': self.env.ref('rental_minimal.view_vehicle_availability_results_form').id,
            'context': {
                'available_vehicle_domain': [('id', 'in', available_vehicles.ids)],
                'default_rental_start_date': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                'default_rental_end_date': end_date.strftime('%Y-%m-%d %H:%M:%S'),
                'default_sale_order_id': self.env.context.get('active_id'),
            },
            'target': 'new',
        }
