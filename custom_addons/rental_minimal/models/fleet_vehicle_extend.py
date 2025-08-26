# models/fleet_vehicle_extend.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    # --- Campos de arriendo ---
    is_available_for_rent = fields.Boolean(
        string="Disponible para arriendo", default=True
    )

    state_id = fields.Many2one('fleet.vehicle.state', string="Estado del vehículo")

    rental_status = fields.Selection(
        selection=[
            ("available", "Disponible"),
            ("reserved", "Reservado"),
            ("rented", "Arrendado"),
            ("returned", "Devuelto"),
            ("maintenance", "Mantención"),
        ],
        string="Estado de arriendo",
        default="available",
        tracking=True,
    )
    price_per_day = fields.Monetary(string="Precio por día", currency_field="currency_id")

    # models/fleet_vehicle_extend.py  (añade el campo al bloque de definición)
    price_per_extra_hour = fields.Monetary(
        string="Precio por hora extra", currency_field="currency_id"
    )

    
    # --- Producto asociado ---
    rental_product_id = fields.Many2one(
        "product.product", string="Producto de venta", readonly=True, ondelete="restrict"
    )

    rental_booking_ids = fields.One2many(
        'rental.booking',
        'vehicle_id',
        string="Reservas de Arriendo"
    )

    @api.model
    def create(self, vals):
        vehicle = super().create(vals)
        vehicle._ensure_rental_product()
        return vehicle

    def write(self, vals):
        res = super().write(vals)
        if {"name", "price_per_day"} & vals.keys():
            self._ensure_rental_product(update=True)
        return res

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------
    def _ensure_rental_product(self, update=False):
        """Crea o actualiza un product.template único por vehículo."""
        ProductTemplate = self.env["product.template"]
        for veh in self:
            if not veh.rental_product_id:
                tmpl = ProductTemplate.create(
                    {
                        "name": f"[{veh.license_plate}] {veh.model_id.name}",
                        "type": "service",
                        "list_price": veh.price_per_day or 0.0,
                        "sale_ok": True,
                        "purchase_ok": False,
                        "is_tour_addon": False,
                        "taxes_id": [(6, 0, self.env.company.sale_tax_ids.ids)],
                    }
                )
                veh.rental_product_id = tmpl.product_variant_id.id
            elif update:
                veh.rental_product_id.name = f"[{veh.license_plate}] {veh.model_id.name}"
                if veh.price_per_day:
                    veh.rental_product_id.list_price = veh.price_per_day

    def action_open_calendar_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Calendario - {self.name}',
            'res_model': 'rental.booking',
            'view_mode': 'calendar,tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }
        

     # rediririge a la accion que crea la orden de venta   
    @api.model
    def action_add_to_sale_order(self):
        return self.env['sale.order.line'].create_from_vehicle_action(self)