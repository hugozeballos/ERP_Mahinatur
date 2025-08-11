from odoo import models, fields, api

class SalesCommission(models.Model):
    """
    Modelo para registrar comisiones por venta.
    Cada comisión está ligada a una orden de venta y un vendedor.
    """
    _name = 'sales.commission'
    _description = 'Comisión de Vendedor'
    _order = 'create_date desc'

    user_id = fields.Many2one(
        'res.users',
        string='Vendedor',
        required=True,
        help='Usuario que recibe la comisión'
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Orden de Venta',
        required=True,
        ondelete='cascade',
        help='Orden de venta relacionada con esta comisión'
    )
    amount = fields.Float(
        string='Monto de Comisión',
        digits='Product Price',
        readonly=True,
        help='Monto calculado de la comisión'
    )
    commission_rate = fields.Float(
        string='Porcentaje (%)',
        readonly=True,
        help='Porcentaje de comisión aplicado'
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('paid', 'Pagado')
    ], default='draft', string='Estado', help='Estado del pago de la comisión')

    @api.model
    def create_from_order(self, order, commission_percent):
        """
        Método utilitario para crear una comisión desde una orden de venta.
        :param order: objeto sale.order
        :param commission_percent: porcentaje a aplicar (ej: 0.05 para 5%)
        """
        return self.create({
            'user_id': order.user_id.id,
            'sale_order_id': order.id,
            'commission_rate': commission_percent * 100,
            'amount': order.amount_total * commission_percent,
        })
