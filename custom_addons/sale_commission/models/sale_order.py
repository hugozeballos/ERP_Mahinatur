from odoo import models, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_default_commission_percent(self):
        """
        Porcentaje de comisión predeterminado. 
        Podrías reemplazarlo luego con configuración por usuario o producto.
        """
        return 0.05  # 5%

    def action_confirm(self):
        """
        Sobrescribe el método de confirmación para calcular comisión automáticamente.
        """
        res = super().action_confirm()
        commission_model = self.env['sales.commission']

        for order in self:
            # Evita duplicados si ya existe comisión para esta orden
            existing = commission_model.search([
                ('sale_order_id', '=', order.id)
            ])
            if existing:
                continue

            commission_percent = self._get_default_commission_percent()
            commission_model.create_from_order(order, commission_percent)

        return res
