from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    # (Asegúrate de tener los campos si vas a guardar el tour ahí)
    tour_id = fields.Many2one('tour.minimal', string='Tour')

    def open_configure_tour_wizard(self):
        if not self.order_id or not self.order_id.exists():
            raise UserError("La orden de venta asociada no existe o fue eliminada.")
            # 🚀 Buscar el tour desde la línea O el pedido
        tour = self.tour_id or self.order_id.tour_id  # 🔥 aquí tomamos el tour
        
        _logger.info(f"[DEBUG] Abrir wizard. Line ID: {self.id}, Order ID: {self.order_id.id}, Tour ID: {tour.id if tour else 'None'}")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configurar Tour',
            'res_model': 'tour.selection.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('tour_minimal_odoo17.tour_selection_wizard_form').id,
            'target': 'new',
            'context': {
                'default_order_id': self.order_id.id,
                'default_line_id': self.id,
                'default_price_unit_base': self.price_unit,
                'default_tour_id': tour.id if tour else False,  # <--- aquí ahora está bien
                'active_id': self.id,
            }
        }