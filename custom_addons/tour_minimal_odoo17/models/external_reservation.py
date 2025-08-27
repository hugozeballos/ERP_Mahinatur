from odoo import models, fields

class ExternalReservation(models.Model):
    _name = 'tour.external.reservation'
    _description = 'Reservas de Tours Externos'

    name                = fields.Char(string='Descripción', required=True)
    product_id          = fields.Many2one('product.product', string='Producto', required=True)
    sale_order_line_id  = fields.Many2one('sale.order.line', string='Línea de pedido')
    reservation_date    = fields.Date(string='Fecha de Reserva', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta', )
