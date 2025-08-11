# -*- coding: utf-8 -*-
import logging
from odoo import models, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        # 1. Validación previa: asegurar que las líneas de arriendo tengan fechas y cantidad coherentes
        for order in self:
            for line in order.order_line:
                if line.product_id.is_vehicle_rental:
                    start = line.rental_start_date
                    end = line.rental_end_date
                    # Fechas obligatorias
                    if not start or not end:
                        raise UserError(_("Faltan fechas de arriendo en la línea '%s'.") % line.name)
                    # Fecha fin posterior a inicio
                    days = (end - start).days
                    if days <= 0:
                        raise UserError(_("La fecha de fin debe ser posterior a la fecha de inicio en la línea '%s'.") % line.name)
                    # Igualdad exacta de días
                    if days != line.product_uom_qty:
                        raise UserError(_(
                            "La cantidad de días vendida (%s) no coincide con la diferencia de fechas (%s días) en la línea '%s'."
                        ) % (line.product_uom_qty, days, line.name))
        
        '''Al confirmar la orden, crear reservas si corresponde, validando solapamientos.'''
        res = super().action_confirm()
        rental_booking = self.env['rental.booking']

        for order in self:
            _logger.info('Procesando orden %s', order.name)
            for line in order.order_line:
                vehicle = self.env['fleet.vehicle'].search(
                    [('rental_product_id', '=', line.product_id.id)],
                    limit=1
                )
                if not (vehicle and vehicle.is_available_for_rent and
                        line.rental_start_date and line.rental_end_date):
                    continue

                # 1) Verificar solapamientos en el rango deseado
                overlapping = rental_booking.search([
                    ('vehicle_id', '=', vehicle.id),
                    ('state', 'in', ['draft', 'confirmed', 'rented']),
                    ('date_end', '>=', line.rental_start_date),
                    ('date_start', '<=', line.rental_end_date),
                ], limit=1)
                if overlapping:
                    raise ValidationError(_(
                        'El vehículo %s ya está reservado entre %s y %s.'
                    ) % (
                        vehicle.display_name,
                        overlapping.date_start.strftime('%Y-%m-%d %H:%M'),
                        overlapping.date_end.strftime('%Y-%m-%d %H:%M'),
                    ))

                # 2) Crear la reserva
                _logger.info('Creando reserva para vehículo %s', vehicle.display_name)
                booking = rental_booking.create({
                    'name':         f'Reserva {order.name}',
                    'customer_id':  order.partner_id.id,
                    'vehicle_id':   vehicle.id,
                    'date_start':   line.rental_start_date,
                    'date_end':     line.rental_end_date,
                    'state':        'confirmed',
                    'sale_order_id': order.id,
                })

        return res
