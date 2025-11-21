# -*- coding: utf-8 -*-
import logging
from odoo import models, _, fields
from datetime import timedelta
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        # 1. Validación previa: asegurar que las líneas de arriendo tengan fechas y cantidad 
        _logger.info('confirmando reserva')

        for order in self:
            for line in order.order_line:
                _logger.info(
                    "Rellenando %s: start=%s, end=%s, service_date=%s, qty=%s, is_vehicle_rental=%s",
                    line.id, line.rental_start_date, line.rental_end_date, line.service_date, line.product_uom_qty, line.product_id.is_vehicle_rental
                )
                # 1.a) Seguro: si hay service_date + qty pero no fechas de arriendo, completarlas aquí
                if (not line.rental_start_date or not line.rental_end_date):

                    base_dt = line.service_date
                    line.rental_start_date = base_dt
                    line.rental_end_date = base_dt + timedelta(days=int(line.product_uom_qty or 1))

                    _logger.info(
                        "Rellenando fechas desde service_date en línea %s: start=%s, end=%s",
                        line.id, line.rental_start_date, line.rental_end_date
                    )
                    start = line.rental_start_date
                    end = line.rental_end_date
                    _logger.info(
                        "Rellenando %s: start=%s, end=%s",
                        line.id, start, end
                    )
                    
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
                if not line.product_id.is_vehicle_rental:
                    continue
                vehicle = self.env['fleet.vehicle'].search(
                    [('rental_product_id', '=', line.product_id.id)],
                    limit=1
                )
                _logger.info(
                    "Linea %s -> product=%s, vehicle=%s, is_available_for_rent=%s, start=%s, end=%s",
                    line.id, line.product_id.display_name,
                    vehicle.display_name if vehicle else None,
                    vehicle.is_available_for_rent if vehicle else None,
                    line.rental_start_date, line.rental_end_date
                )
                if not (vehicle and vehicle.is_available_for_rent and
                        line.rental_start_date and line.rental_end_date):
                    continue

                _logger.info('Vehiculo disponible %s', vehicle.display_name)


                # 1) Verificar solapamientos en el rango deseado
                overlapping = rental_booking.search([
                    ('vehicle_id', '=', vehicle.id),
                    ('state', 'in', ['draft', 'confirmed', 'rented']),
                    ('date_end', '>=', line.rental_start_date),
                    ('date_start', '<=', line.rental_end_date),
                ], limit=1)
                _logger.info('Buscando overlap para vehículo %s: %s', vehicle.display_name, overlapping)

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
