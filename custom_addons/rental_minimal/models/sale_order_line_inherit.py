# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    rental_start_date = fields.Datetime(string="Fecha inicio arriendo")
    rental_end_date = fields.Datetime(string="Fecha fin arriendo")

    @api.constrains('rental_start_date', 'rental_end_date', 'product_uom_qty')
    def _check_rental_dates_and_qty(self):
        for line in self:
            if line.product_id and line.product_id.is_vehicle_rental:
                if not line.rental_start_date or not line.rental_end_date:
                    raise ValidationError("Debe especificar fechas de inicio y fin para vehículos en arriendo.")
                rental_days = (line.rental_end_date - line.rental_start_date).days + \
                            (1 if (line.rental_end_date - line.rental_start_date).seconds else 0)
                if rental_days <= 0:
                    raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio.")
                if rental_days != int(line.product_uom_qty):
                    raise ValidationError(
                        f"La cantidad ({int(line.product_uom_qty)}) debe ser igual "
                        f"a los días de arriendo ({rental_days} días)."
                    )
                
    @api.onchange('rental_start_date', 'rental_end_date')
    def _onchange_rental_dates(self):
        for line in self:
            if line.rental_start_date and line.rental_end_date:
                delta = line.rental_end_date - line.rental_start_date
                days = max(int(delta.days) + (1 if delta.seconds else 0), 1)
                line.product_uom_qty = days


    @api.model
    def create_from_vehicle_action(self, vehicles):
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        if not sale_order:
            return

        for vehicle in vehicles:
            product = vehicle.rental_product_id
            if not product:
                continue

            start = self.env.context.get('default_rental_start_date')
            end = self.env.context.get('default_rental_end_date')

            # evitar duplicados
            existing = sale_order.order_line.filtered(
                lambda l: l.product_id == product and l.rental_start_date == start and l.rental_end_date == end)
            if existing:
                continue

            self.create({
                'order_id': sale_order.id,
                'product_id': product.id,
                'rental_start_date': start,
                'rental_end_date': end,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }
