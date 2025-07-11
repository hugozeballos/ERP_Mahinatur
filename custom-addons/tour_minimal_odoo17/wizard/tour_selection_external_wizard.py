# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import models, fields

class TourSelectionExternalWizard(models.TransientModel):
    _name = 'tour.selection.external.wizard'
    _description = 'Wizard para Productos Externos'
    

    order_id = fields.Many2one(
        'sale.order',
        string='Pedido',
        readonly=True,
        required=True,
    )

        # Relación con la línea de pedido desde la que vino
    sale_order_line_id = fields.Many2one(
        'sale.order.line', 
        string='Línea de Pedido', 
        required=True, 
        readonly=True,
        default=lambda self: self.env.context.get('active_id')
    )

    # El nuevo campo de fecha
    reservation_date = fields.Date(
        string='Fecha de Reserva', 
        required=True,
        default=fields.Date.context_today
    )


    def action_confirm_external(self):
        self.ensure_one()
        if not self.reservation_date:
            raise UserError('Debes indicar una fecha de reserva.')

        self.env['tour.external.reservation'].create({
            'product_id': self.sale_order_line_id.product_id.id,
            'sale_order_line_id': self.sale_order_line_id.id,
            'reservation_date': self.reservation_date,
            'name': f"Reserva {self.sale_order_line_id.product_id.name}",
        })
        return {'type': 'ir.actions.act_window_close'}