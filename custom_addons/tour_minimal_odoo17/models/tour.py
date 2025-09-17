from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

class TourMinimal(models.Model):
    _name = 'tour.minimal'
    _description = 'Tour Minimal'
    _inherit = ['mail.thread', 'mail.activity.mixin']   # ← añade esto


    name = fields.Char(string='Nombre del Tour', required=True)
    date_start = fields.Datetime(string='Fecha/Hora de Inicio', required=True)
    date_end = fields.Datetime(string='Fecha/Hora de Fin')
    max_capacity = fields.Integer(string='Capacidad Máxima', default=20)
    participants_ids = fields.One2many('tour.participant', 'tour_id', string='Participantes')
    guide_id = fields.Many2one('hr.employee', string='Guía', ondelete='set null')
    guide_cost = fields.Float(string='Costo del Guía')
    driver_id = fields.Many2one('hr.employee', string='Chofer', ondelete='set null')
    driver_cost = fields.Float(string='Costo del Chofer')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo', ondelete='set null')
    vehicle_cost = fields.Float(string='Costo del Vehículo')
    requires_cook = fields.Boolean(string="Requiere Cocinero", default=False)
    cook_id     = fields.Many2one('hr.employee',   string='Cook', ondelete='set null')
    cook_cost = fields.Float(string='Costo del Cocinero')
    waiters_id    = fields.Many2one('hr.employee',   string='Waiters', ondelete='set null')
    waiters_cost = fields.Float(string='Costo del Garzon')
    total_cost = fields.Float(string='Costo Total', compute='_compute_total_cost', store=True)
    available_seats = fields.Integer(string='Cupos Disponibles', compute='_compute_available_seats', store=True)
    sale_order_ids = fields.One2many('sale.order', 'tour_id', string='Ventas Asociadas')
    product_id = fields.Many2one('product.product', string='Producto del Tour', help='Producto (Half Day, Full Day, etc.) para emparejar ventas SIB.')
    tour_type_id = fields.Many2one('tour.type', string='Tipo de tour', index=True)
    is_overbooked = fields.Boolean(
        string="Sobrevendido",
        compute="_compute_is_overbooked",
        store=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('executed', 'Ejecutado'),
        ('cancel',   'Cancelado'),
    ], default='draft', string="Estado")


    # Reemplaza tu selection anterior por:
    language_id = fields.Many2one(
        'res.lang',
        string="Idioma del tour",
        required=True,
        help="Idioma principal en el que se impartirá este tour"
    )

    service_kind = fields.Selection([
        ('sib', 'SIB (regular con cupos)'),
        ('private', 'Privado (crear salida)'),
        ('external', 'Externo (actividad sin tour)')
    ], string='Tipo de servicio', help="SIB o Privado según origen del producto.")

    provider_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        help="Proveedor responsable del tour, solo aplicable a tours externos."
    )

    include_park_ticket = fields.Boolean(
        string="Incluye ticket de parque",
        default=False,
        help="Si este tour incluye o no el ticket de ingreso al parque"
    )

    booked_seats = fields.Integer(string="Cupos Reservados", compute='_compute_booked_seats', store=True)


    @api.depends('participants_ids')  
    def _compute_booked_seats(self):
        for rec in self:
            # intenta contar participantes; si tu campo se llama distinto, esto evita romperse
            count = 0
            if hasattr(rec, 'participants_ids') and rec.participants_ids:
                count = len(rec.participants_ids)
            elif hasattr(rec, 'participant_ids') and rec.participant_ids:
                count = len(rec.participant_ids)
            elif hasattr(rec, 'booked_qty') and rec.booked_qty:
                count = int(rec.booked_qty)
            rec.booked_seats = count

    # --- (Opcional) advertencia inmediata al cambiar vehículo
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id_capacity(self):
        for rec in self:
            # Sin vehículo: vuelve al default
            if not rec.vehicle_id:
                rec.max_capacity = 20
                continue

            # Lee asientos desde Fleet (seats o seats_count)
            seats = getattr(rec.vehicle_id, 'seats', None)
            if seats is None:
                seats = getattr(rec.vehicle_id, 'seats_count', 0)
            seats = int(seats or 0)

            # Capacidad = asientos - 1 (chofer)
            expected = max(seats - 1, 0)
            rec.max_capacity = expected

            # ADVERTENCIA (no bloquea): participantes vs capacidad
            booked = len(rec.participants_ids or [])
            if expected and booked > expected:
                return {
                    'warning': {
                        'title': _("Capacidad insuficiente"),
                        'message': _("Hay %s participantes y la capacidad máxima es %s.")
                                % (booked, expected)
                    }
                }
    # --- Helper para dominio de solape (start < other_end y end > other_start)
    def _get_overlap_domain(self):
        self.ensure_one()
        return [
            ('id', '!=', self.id),
            ('state', '!=', 'cancel'),
            ('date_start', '<', self.date_end),
            ('date_end',   '>', self.date_start),
        ]
    

    @api.constrains('date_start', 'date_end', 'guide_id', 'driver_id', 'vehicle_id', 'state')
    def _check_resource_overlaps(self):
        for rec in self:
            if not rec.date_start or not rec.date_end:
                continue
            overlap_domain = rec._get_overlap_domain()

            # Guía
            if rec.guide_id:
                clash = self.search(overlap_domain + [('guide_id', '=', rec.guide_id.id)], limit=1)
                if clash:
                    raise ValidationError(_(
                        "El guía %s ya está asignado en otro tour (%s) entre %s y %s."
                    ) % (rec.guide_id.name, clash.name, clash.date_start, clash.date_end))

            # Chofer
            if rec.driver_id:
                clash = self.search(overlap_domain + [('driver_id', '=', rec.driver_id.id)], limit=1)
                if clash:
                    raise ValidationError(_(
                        "El chofer %s ya está asignado en otro tour (%s) entre %s y %s."
                    ) % (rec.driver_id.name, clash.name, clash.date_start, clash.date_end))

            # Vehículo (bus puede estar en tour o arrendado)
            if rec.vehicle_id:
                clash = self.search(overlap_domain + [('vehicle_id', '=', rec.vehicle_id.id)], limit=1)
                if clash:
                    raise ValidationError(_(
                        "El vehículo %s ya está asignado en otro tour (%s) entre %s y %s."
                    ) % (rec.vehicle_id.display_name, clash.name, clash.date_start, clash.date_end))

                # (Opcional) si tienes un modelo de arriendo propio, valida aquí también:
                # rental_model = self.env['vehicle.rental']  # ajusta el nombre si existe
                # rental = rental_model.search([
                #     ('vehicle_id', '=', rec.vehicle_id.id),
                #     ('date_start', '<', rec.date_end),
                #     ('date_end',   '>', rec.date_start),
                #     ('state', '!=', 'cancel'),
                # ], limit=1)
                # if rental:
                #     raise ValidationError(_("El vehículo %s está arrendado en ese rango." ) % rec.vehicle_id.display_name)


    def _has_overbooking(self):
        self.ensure_one()
        cap = int(self.max_capacity or 0)
        return bool(cap and len(self.participants_ids or []) > cap)

    #calcular sobrevendido
    @api.depends('participants_ids', 'max_capacity')
    def _compute_is_overbooked(self):
        for tour in self:
            tour.is_overbooked = (
                tour.max_capacity is not None and
                len(tour.participants_ids) > tour.max_capacity
            )


    @api.depends('guide_cost', 'driver_cost', 'vehicle_cost', 'cook_cost', 'waiters_cost')
    def _compute_total_cost(self):
        for tour in self:
            tour.total_cost = (tour.guide_cost or 0.0) + (tour.driver_cost or 0.0) + (tour.vehicle_cost or 0.0) + (tour.cook_cost or 0.0) + (tour.waiters_cost or 0.0)

    @api.depends('max_capacity', 'participants_ids')
    def _compute_available_seats(self):
        for tour in self:
            tour.available_seats = tour.max_capacity - len(tour.participants_ids)
            
    @api.constrains('guide_id', 'language_id')
    def _check_guide_language(self):
        for tour in self:
            if tour.guide_id and tour.language_id:
                if tour.language_id not in tour.guide_id.languages_spoken:
                    raise ValidationError(_(
                        "El guía %s no habla el idioma %s."
                    ) % (   
                        tour.guide_id.name,
                        tour.language_id.name,
                    ))
    


    def action_confirm(self):
        for rec in self:
            # Reglas (sin template, exigir guía/chofer/vehículo)
            if not rec.guide_id:
                raise ValidationError(_("Debe asignar un Guía para confirmar el tour."))
            if not rec.driver_id:
                raise ValidationError(_("Debe asignar un Chofer para confirmar el tour."))
            if not rec.vehicle_id:
                raise ValidationError(_("Debe asignar un Vehículo para confirmar el tour."))
            
            # Si está sobrevendido, en lugar de error duro -> abrir wizard
            if rec._has_overbooking():
                return rec._action_open_split_wizard()

            # (opcional) vuelve a disparar validaciones de solape/capacidad
            rec._check_resource_overlaps()
            #rec._check_vehicle_capacity()

        # Cambiar estado a confirmado
        self.write({'state': 'confirmed'})
        return True

    def _action_open_split_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tour.split.wizard',
            'name': _('Dividir Tour'),
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_tour_id': self.id},'default_capacity_snapshot': int(self.max_capacity or 0),
        }

    def action_execute(self):
        """Marca el tour como ejecutado y crea gastos para guía y chofer."""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_("Solo se puede ejecutar un tour confirmado."))
        Expense = self.env['hr.expense']
        for role, cost_field in [('guide_id', 'guide_cost'),
                                 ('driver_id', 'driver_cost')]:
            emp = getattr(self, role)
            amount = getattr(self, cost_field) or 0.0
            if emp and amount > 0:
                Expense.create({
                    'name': _('Pago %s: %s') % (role.replace('_id','').capitalize(), self.name),
                    'employee_id': emp.id,
                    'price_unit': amount,
                    'quantity':1.0, 
                    'date': fields.Date.context_today(self),
                    # opcional: 'analytic_account_id': ...
                    # opcional: 'product_id': <id de producto si aplica>
                })
        self.state = 'executed'

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft','confirmed'):
                raise UserError("Solo se puede cancelar en Borrador o Confirmado.")
            rec.state = 'cancel'