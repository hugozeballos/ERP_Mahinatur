from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

class TourMinimal(models.Model):
    _name = 'tour.minimal'
    _description = 'Tour Minimal'

    name = fields.Char(string='Nombre del Tour', required=True)
    date_start = fields.Datetime(string='Fecha/Hora de Inicio', required=True)
    date_end = fields.Datetime(string='Fecha/Hora de Fin')
    max_capacity = fields.Integer(string='Capacidad Máxima', default=10)
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

    @api.constrains('participants_ids', 'max_capacity')
    def _check_capacity(self):
        for tour in self:
            if len(tour.participants_ids) > tour.max_capacity:
                raise ValidationError("El número de participantes excede la capacidad máxima.")
            
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
            if rec.state != 'draft':
                raise UserError("Solo se puede confirmar desde Borrador.")
            if rec.template_id.requires_guide and not rec.guide_id:
                raise UserError("Debes asignar un guía antes de confirmar.")
            if rec.template_id.requires_transport and (not rec.driver_id or not rec.vehicle_id):
                raise UserError("Debes asignar chofer y vehículo antes de confirmar.")
            rec.state = 'confirmed'

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