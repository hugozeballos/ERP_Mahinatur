# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from datetime import timedelta, time
import logging
_logger = logging.getLogger(__name__)



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    rental_start_date = fields.Datetime(string="Fecha inicio arriendo")
    rental_end_date = fields.Datetime(string="Fecha fin arriendo")

    service_date = fields.Datetime(string='Fecha y hora del servicio (renta)', help='Usado para calcular inicio y fin del arriendo')


    @api.onchange('service_date', 'product_uom_qty')
    def _onchange_service_fields(self):
        for line in self:
            if line.service_date and line.product_uom_qty:
                # si tienes hora base, ya viene en service_date; si no, normaliza:
                base_dt = line.service_date
                line.rental_start_date = base_dt
                line.rental_end_date = base_dt + timedelta(days=int(line.product_uom_qty or 1))

    @api.model
    def create_from_vehicle_action(self, vehicles):
        sale_order_id = self.env.context.get("default_sale_order_id")
        start = self.env.context.get("default_rental_start_date")
        end = self.env.context.get("default_rental_end_date")

        print("=== CONTEXTO RECIBIDO ===")
        print("Sale Order ID:", sale_order_id)
        print("Start:", start)
        print("End:", end)
        print("Vehicles:", vehicles.ids)

        sale_order = self.env["sale.order"].browse(sale_order_id)
        if not sale_order.exists():
            raise UserError("La orden de venta no existe.")

        qty_days = 1
        if start and end:
            start_dt = fields.Datetime.from_string(start)
            end_dt = fields.Datetime.from_string(end)
            delta = end_dt - start_dt
            qty_days = max(delta.days or 1, 1)
        else:
            start_dt = False
            end_dt = False

        print("=== CALCULOS ===")
        print("Start_dt:", start_dt)
        print("End_dt:", end_dt)
        print("Qty_days:", qty_days)

        for vehicle in vehicles:
            product = vehicle.rental_product_id
            print(f"Procesando vehículo {vehicle.name} con producto {product.display_name if product else 'None'}")

            if not product:
                raise UserError(f"El vehículo {vehicle.name} no tiene producto de arriendo asociado.")

            existing = sale_order.order_line.filtered(
                lambda l: l.product_id == product
                and l.rental_start_date == start_dt
                and l.rental_end_date == end_dt
            )
            if existing:
                print(f"Ya existe línea para {vehicle.name}, saltando...")
                continue

            print(f"Creando línea: SO={sale_order.id}, Producto={product.id}, Qty={qty_days}")
            self.create({
                "order_id": sale_order.id,
                "product_id": product.id,
                "rental_start_date": start_dt,
                "rental_end_date": end_dt,
                "product_uom_qty": qty_days,
                "price_unit": vehicle.price_per_day or 0.0,
                "service_date": start_dt,
            })

        print("=== FIN DEL PROCESO ===")
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": sale_order.id,
            "view_mode": "form",
            "target": "current",
        }

