# models/rental_booking.py
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class RentalBooking(models.Model):
    _name = "rental.booking"
    _description = "Reserva de Vehículo"
    _order = "date_start desc"

    # ---------------------------------------------------------------- #
    name = fields.Char(string="Referencia", default="New", copy=False, readonly=True)
    customer_id = fields.Many2one("res.partner", required=True, string="Cliente")
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        required=True,
        string="Vehículo",
        domain="[('rental_status', 'not in', ['maintenance'])]",
    )

    no_charge_delay = fields.Boolean(
        string="Atraso no cobrado",
        readonly=True,
        help="Marca cuando el usuario decidió no cobrar el retraso"
    )
    delay_hours = fields.Float(
        string="Horas de atraso",
        readonly=True,
        help="Horas de retraso registradas si no se cobró"
    )
    no_charge_reason = fields.Text(
        string="Motivo no cobro",
        readonly=True,
        help="Motivo indicado para no cobrar"
    )

    user_id = fields.Many2one(
        'res.users', string='Responsable',
        default=lambda self: self.env.user,
        readonly=True,
        help='Usuario que creó la reserva'
    )
    late_reason = fields.Text(string="Motivo de no cobro por atraso")
    date_start = fields.Datetime(required=True, string="Fecha inicio")
    date_end = fields.Datetime(required=True, string="Fecha fin")
    days_qty = fields.Integer(string="Días", compute="_compute_days_qty", store=True)
    price_total = fields.Monetary(
        currency_field="currency_id", string="Total", compute="_compute_price_total", store=True
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("confirmed", "Confirmada"),
            ("rented", "Entregada"),
            ("returned", "Devuelta"),
            ("cancelled", "Cancelada"),
        ],
        default="draft",
        string="Estado",
        tracking=True,
    )
    sale_order_id = fields.Many2one("sale.order", string="Pedido de Venta", readonly=True)

    # ---------------------------------------------------------------- #
    # Cómputos y restricciones
    # ---------------------------------------------------------------- #
    @api.depends("date_start", "date_end")
    def _compute_days_qty(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                delta = rec.date_end - rec.date_start
                rec.days_qty = max(int(delta.days) + (1 if delta.seconds else 0), 1)
            else:
                rec.days_qty = 0

    @api.depends("days_qty", "vehicle_id.price_per_day")
    def _compute_price_total(self):
        for rec in self:
            rec.price_total = rec.days_qty * rec.vehicle_id.price_per_day

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_end <= rec.date_start:
                raise ValidationError(_("La fecha de fin debe ser posterior a la de inicio."))

    # ---------------------------------------------------------------- #
    # Estados / acciones
    # ---------------------------------------------------------------- #
    def action_confirm(self):
        for rec in self:
            if rec.vehicle_id.rental_status != "available":
                raise UserError(_("El vehículo no está disponible."))
            # 1) Cambiar estados
            rec.vehicle_id.rental_status = "reserved"
            rec.state = "confirmed"
            # 2) Crear SO en borrador
            rec._create_sale_order()

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_rented(self):
        self.ensure_one()
        self.vehicle_id.rental_status = "rented"
        self.state = "rented"

    def action_returned(self):
        self.ensure_one()
        grace = timedelta(hours=1)
        now = fields.Datetime.now()
        extra_hours = max((now - self.date_end) - grace, timedelta()).total_seconds() / 3600
        return {
            "type": "ir.actions.act_window",
            "name": _("Devolver Vehículo"),
            "res_model": "rental.return.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_booking_id": self.id,
                "default_extra_hours": round(extra_hours, 2),
            },
        }
    
    def action_finalize_return(self, extra_hours=0.0, charge_late=True, reason_no_charge=None):
        self.ensure_one()
        if self.state != 'rented':
            raise UserError(_("La reserva debe estar en estado 'Arrendado' para devolver el vehículo."))

        if charge_late and extra_hours > 0:
            hours_to_charge = int(extra_hours) if extra_hours.is_integer() else int(extra_hours) + 1
            self._create_late_charge_so(hours_to_charge)
        elif not charge_late and reason_no_charge:
            self._create_late_charge_so(hours_to_charge=0, force_reason=reason_no_charge)

        self.vehicle_id.rental_status = "available"
        self.state = "returned"


    def _create_late_charge_so(self, hours_to_charge, force_reason=None):
        self.ensure_one()
        product = self.vehicle_id.rental_product_id
        if not product:
            raise UserError(_("El vehículo no tiene un producto de venta asociado."))

        # Calcular precio
        price_unit = self.vehicle_id.price_per_extra_hour or 0.0
        total_price = price_unit * hours_to_charge

        # Descripción según si cobramos o no
        if hours_to_charge > 0:
            description = _(
                "Cobro por atraso vehículo %s (%s horas)"
            ) % (self.vehicle_id.display_name, hours_to_charge)
        else:
            description = _(
                "No cobro por atraso: %s"
            ) % (force_reason or _("Sin motivo"))

        # Log para debug
        _logger.info(
            "Creando orden de venta por atraso: booking=%s, horas=%s, precio_unit=%.2f, total=%.2f",
            self.id, hours_to_charge, price_unit, total_price
        )

        # Valores de la sale.order
        so_vals = {
            "partner_id": self.customer_id.id,
            "order_line": [
                (
                    0, 0,
                    {
                        "product_id": product.id,
                        "name": description,
                        "product_uom_qty": hours_to_charge or 1,
                        "price_unit": price_unit,
                    }
                )
            ],
        }
        sale_order = self.env["sale.order"].sudo().create(so_vals)
        sale_order.sudo().action_confirm()
        _logger.info("Orden de venta creada: %s", sale_order.name)
        return sale_order

    @api.model_create_multi
    def create(self, vals_list):
        bookings = super().create(vals_list)
        bookings._validate_vehicle_state()
        return bookings

    def write(self, vals):
        res = super().write(vals)
        if {"vehicle_id"} & vals.keys():
            self._validate_vehicle_state()
        return res

    # helper
    def _validate_vehicle_state(self):
        for rec in self:
            if rec.vehicle_id.rental_status == "maintenance":
                raise UserError(_("El vehículo está en mantención y no puede reservarse."))

