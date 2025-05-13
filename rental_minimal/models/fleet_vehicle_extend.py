# models/fleet_vehicle_extend.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    # --- Campos de arriendo ---
    is_available_for_rent = fields.Boolean(
        string="Disponible para arriendo", default=True
    )
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
                    }
                )
                veh.rental_product_id = tmpl.product_variant_id.id
            elif update:
                veh.rental_product_id.name = f"[{veh.license_plate}] {veh.model_id.name}"
                if veh.price_per_day:
                    veh.rental_product_id.list_price = veh.price_per_day
