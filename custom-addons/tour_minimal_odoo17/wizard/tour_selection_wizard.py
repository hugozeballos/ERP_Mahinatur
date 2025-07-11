from odoo import models, fields, api, _
from odoo.exceptions import UserError

class TourSelectionWizard(models.TransientModel):
    _name = 'tour.selection.wizard'
    _description = 'Wizard to Configure Tour with Lunch'

    order_id = fields.Many2one('sale.order', string='Pedido', required=True)
    line_id = fields.Many2one('sale.order.line', string='Línea del Pedido')
    tour_id = fields.Many2one('tour.minimal', string='Tour', required=True)
    price_unit_base = fields.Float(string='Precio Base')
    price_extra = fields.Float(string='Recargo Almuerzo')
    tour_id_readonly = fields.Boolean(string='¿Tour preasignado?', default=False)

    almuerzo = fields.Boolean(string='¿Incluir almuerzo?')
    tipo_almuerzo = fields.Selection([
        ('normal', 'Normal'),
        ('vegetariano', 'Vegetariano'),
        ('pescado', 'Pescado (costo extra)'),
    ], string='Tipo de Almuerzo')

    participant_ids = fields.One2many(
        'tour.participant.wizard.line',
        'wizard_id',
        string='Participantes'
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        
        default_line_id = self.env.context.get('default_line_id')
        if default_line_id:
            line = self.env['sale.order.line'].browse(default_line_id)
            res.update({
                'line_id': line.id,
                'order_id': line.order_id.id,
                'price_unit_base': line.price_unit,
                'tour_id': line.tour_id.id or False,
                'tour_id_readonly': bool(line.tour_id),
                'participant_ids': [(0, 0, {
                    'name': p.name,
                    'almuerzo': p.almuerzo,
                    'tipo_almuerzo': p.tipo_almuerzo,
                }) for p in self.env['tour.participant'].search([
                    ('sale_order_line_id', '=', line.id)
                ])]
            })
        return res

    @api.onchange('almuerzo', 'tipo_almuerzo')
    def _onchange_almuerzo(self):
        """Actualizar recargo cuando se selecciona almuerzo o tipo de almuerzo."""
        recargo = 0.0
        if self.almuerzo:
            recargo += 10.0
            if self.tipo_almuerzo == 'pescado':
                recargo += 5.0
        self.price_extra = recargo

    def action_confirm_wizard(self):
        """Crear o actualizar los participantes para el tour."""
        self.ensure_one()

        if not self.tour_id:
            raise UserError(_('Debe seleccionar un tour.'))

        # Validar cupos
        cupos_vendidos = self.line_id.product_uom_qty
        if len(self.participant_ids) > cupos_vendidos:
            raise UserError(_('No puede agregar más participantes que los cupos vendidos.'))

        # Eliminar participantes anteriores asociados a esta línea de venta
        participantes_anteriores = self.env['tour.participant'].search([
            ('sale_order_line_id', '=', self.line_id.id)
        ])
        participantes_anteriores.unlink()

        # Crear nuevos participantes
        for wizard_line in self.participant_ids:
            self.env['tour.participant'].create({
                'name': wizard_line.name,
                'almuerzo': wizard_line.almuerzo,
                'tipo_almuerzo': wizard_line.tipo_almuerzo,
                'tour_id': self.tour_id.id,
                'sale_order_line_id': self.line_id.id,
                'sale_order_id': self.order_id.id,
            })

            # 🚀 NUEVO: Guardar el Tour en el Pedido (sale.order)
        self.order_id.tour_id = self.tour_id

        # 🚀 OPCIONAL: guardar también en la línea si quiere
        self.line_id.tour_id = self.tour_id

        # 🚀 Añadir registro en el log
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"📝 Pedido {self.order_id.name} actualizado al nuevo Tour: {self.tour_id.name}")
