from odoo import models, fields, _ 
from odoo.exceptions import UserError
import logging, inspect, os
from datetime import datetime,  time
_logger = logging.getLogger(__name__)
_logger.warning(">> tour_minimal_odoo17 loaded from: %s", __file__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tour_id = fields.Many2one('tour.minimal', string='Tour Relacionado')
    external_agency_code = fields.Char(string="Código Agencia Externa")
    check_in = fields.Date(string='Check-in')
    check_out = fields.Date(string='Check-out')
    flight_in = fields.Char(string='Vuelo In')
    flight_out = fields.Char(string='Vuelo Out')
    hotel = fields.Char(string='Hotel')


    def action_expand_packages(self):
        """Botón manual para desglosar paquetes (útil para probar Fase 2 sin confirmar)."""
        for order in self:
            order.order_line._expand_tour_package()
        return True
    
    def action_confirm(self):

        for order in self:
            order.order_line._expand_tour_package()

        # 2) Confirmación estándar
        res = super().action_confirm()
        _logger.info("=== [DEBUG] Entrando a action_confirm personalizado ===")


        for order in self:
            #comprueba si hay tickets y actualiza el contador
            order.order_line._update_ticket_counter()
            # SIB: ahora TODAS las líneas con service_kind == 'sib'
            sib_lines = order.order_line.filtered(lambda l: not l.display_type and getattr(l.product_id.product_tmpl_id, 'is_tour_ticket', False) and l.service_kind == 'sib')
            sib_lines._assign_sib_to_existing_tour_by_date_and_type()

            # PRIVADOS: ahora TODAS las líneas con service_kind == 'private'
            prv_lines = order.order_line.filtered(lambda l: not l.display_type and getattr(l.product_id.product_tmpl_id, 'is_tour_ticket', False) and l.service_kind == 'private')
            prv_lines._ensure_private_tour_created()

            external_lines = order.order_line.filtered(lambda l: not l.display_type and getattr(l.product_id.product_tmpl_id, 'is_tour_ticket', False) and l.service_kind in ('external'))
            external_lines._ensure_activity_tours_created()

            # Add-ons (almuerzos) siguen aplicando solo a SIB (por fecha)
            order._apply_addons_by_date_to_full_day_sib()

        return res
    
    def action_cancel(self):
        for order in self:
            order.order_line._rollback_ticket_counter()
            # 1. Borrar participantes relacionados
            self.env['tour.participant'].search([
                ('sale_order_id', '=', order.id)
            ]).unlink()

            # 2. Borrar tours (privados o externos) asociados directamente
            self.env['tour.minimal'].search([
                ('sale_order_ids', 'in', order.id)
            ]).unlink()

            # 3. Borrar reservas externas
            self.env['tour.external.reservation'].search([
                ('sale_order_id', '=', order.id)
            ]).unlink()

        return super().action_cancel()
    

        # === NUEVO: aplica almuerzos buscando la línea Full Day SIB por FECHA ===
    def _apply_addons_by_date_to_full_day_sib(self):
        
        Participant = self.env['tour.participant']
        for order in self:
            addon_lines = order.order_line.filtered(lambda l: l.is_tour_addon and l.product_uom_qty > 0)

            for al in addon_lines:
                if not al.service_date:
                    raise UserError(_("La línea de add-on '%s' requiere Fecha de servicio.") % al.product_id.display_name)
                if not al.addon_code:
                    raise UserError(_("El producto add-on '%s' no tiene 'Tipo de add-on' configurado.") % al.product_id.display_name)

                # Candidatos: línea hija de paquete, SIB, tipo de tour = full_day, misma fecha
                candidates = order.order_line.filtered(
                    lambda tl: not tl.display_type
                    and getattr(tl.product_id.product_tmpl_id, 'is_tour_ticket', False)
                    and tl.service_date == al.service_date
                    and getattr(tl.product_id.product_tmpl_id.tour_type_id, 'code', False) == 'full_day'
                )

                if not candidates:
                    raise UserError(_(
                        "No se encontró una actividad Full Day SIB en la fecha %s para aplicar el add-on '%s'."
                    ) % (fields.Date.to_string(al.service_date), al.product_id.display_name))

                if len(candidates) > 1:
                    raise UserError(_(
                        "Se encontraron varias actividades Full Day SIB el %s. "
                        "Debes dividir los add-ons por fecha/actividad."
                    ) % fields.Date.to_string(al.service_date))

                target_line = candidates[0]
                if not target_line.tour_id:
                    raise UserError(_(
                        "La actividad Full Day SIB del %s aún no tiene tour asignado. "
                        "Revisa disponibilidad o asignación primero."
                    ) % fields.Date.to_string(al.service_date))

                # Participantes de la línea destino
                participants = Participant.search([('sale_order_line_id', '=', target_line.id)], order='id asc')
                pax = len(participants)
                qty = int(al.product_uom_qty)

                if qty > pax:
                    raise UserError(_("Hay más almuerzos (%d) que pasajeros (%d) en '%s' (%s).")
                                    % (qty, pax, target_line.product_id.display_name, fields.Date.to_string(al.service_date)))

                # Asignar a los primeros 'qty' SIN almuerzo aún
                free = participants.filtered(lambda p: not p.tipo_almuerzo)
                if qty > len(free):
                    raise UserError(_("No hay suficientes participantes sin almuerzo para asignar %d '%s' en %s.")
                                    % (qty, dict(Participant._fields['tipo_almuerzo'].selection).get(al.addon_code, al.addon_code),
                                       fields.Date.to_string(al.service_date)))

                for p in free[:qty]:
                    p.tipo_almuerzo = al.addon_code
                    p.almuerzo = True


