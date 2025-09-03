from odoo import models, fields, _ ,api
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
    
    # NUEVOS: mismos modelos que en participante
    flight_in_id = fields.Many2one('tour.flight', string='Vuelo In')
    flight_out_id = fields.Many2one('tour.flight', string='Vuelo Out')
    hotel_id = fields.Many2one('res.partner', string='Hotel', domain=[('is_hotel', '=', True)], required=False)
    
    #BORRAR ESTAN POR SI ACASO NO FUNCIONAN LOS NUEVOS
    #flight_in = fields.Char(string='Vuelo In')
    #flight_out = fields.Char(string='Vuelo Out')
    #hotel = fields.Char(string='Hotel')

    # Entero, no m2m: cuántos líderes aplican
    tour_leader_count = fields.Integer(string="Tour Líderes", default=0)

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

# ---------------------------
    # Helpers para descuento Tour Líder
    # ---------------------------
    def _get_discount_product(self):
        """Obtiene el product.product del template XMLID product_tour_leader_discount."""
        # product.template -> product.product
        tmpl = self.env.ref('tour_minimal_odoo17.product_tour_leader_discount', raise_if_not_found=False)
        if not tmpl:
            raise UserError(_("No se encontró el producto 'Descuento Tour Líder' "
                              "(XMLID tour_minimal_odoo17.product_tour_leader_discount)."))
        # Usar la variante principal
        return tmpl.product_variant_id

    def _compute_tour_leader_discount_amount(self):
        """Calcula el monto total a descontar (positivo) sumando todas las líneas paquete.
        Regla especial: si la lista de precios contiene 'Joy Travel' en el nombre,
        el descuento es SIEMPRE 1 persona (no 0.5), manteniendo el mínimo de 5 pax.
        """
        self.ensure_one()
        order = self
        tlc = max(0, order.tour_leader_count or 0)
        if not tlc:
            return 0.0

        total_disc = 0.0
        currency = order.currency_id or self.env.company.currency_id

        # Detectar lista de precios "Joy Travel" (insensible a mayúsculas)
        is_joy_travel = bool(order.pricelist_id and 'joy travel' in (order.pricelist_id.name or '').lower())

        # (opcional) si prefieres que aplique sin mínimo para Joy Travel, elimina el check qty<5 más abajo.

        # Obtener (si existe) el producto de descuento para excluir su línea del cálculo
        discount_product = None
        try:
            discount_product = self._get_discount_product()
        except Exception:
            pass

        for line in order.order_line:
            # Excluir la línea de descuento si ya existe
            if discount_product and line.product_id == discount_product:
                continue

            # Solo líneas paquete
            tmpl = line.product_id and line.product_id.product_tmpl_id
            if not (tmpl and getattr(tmpl, 'is_tour_package', False)):
                continue

            qty = int(line.product_uom_qty or 0)
            
            #####SI QUISIERA APLICAR A PARTIR DE % EL DESCUENTO A JOY TRAVEL DEBO DESCOMENTAR #####################
            
            #if qty < 5:
                # Mantengo el mínimo de 5 pax también para Joy Travel (si quieres que no aplique mínimo, quita esta línea)
            #    continue

            # ---- REGLA DE PERSONAS GRATIS ----
            if is_joy_travel:
                free_units = 1.0              # siempre 1 para Joy Travel
            else:
                free_units = 0.5 if 5 <= qty <= 9 else 1.0  # lógica original para otras listas

            # Precio unitario efectivo (post descuento de línea, pre impuestos)
            unit_price_effective = (line.price_unit or 0.0) * (1.0 - (line.discount or 0.0) / 100.0)

            line_disc = unit_price_effective * free_units * tlc

            # Seguridad: no exceder el subtotal sin impuestos de la línea
            max_line_disc = line.price_subtotal or 0.0
            if max_line_disc > 0:
                line_disc = min(line_disc, max_line_disc)
            else:
                line_disc = 0.0

            total_disc += currency.round(line_disc)

        return currency.round(total_disc)

    def _ensure_tour_leader_discount_line(self):
        """Crea/actualiza/elimina la ÚNICA línea 'Descuento Tour Líder' al final del pedido.
           - Sin impuestos
           - Siempre qty=1 y price_unit NEGATIVO por el monto total a descontar
           - Idempotente
        """
        for order in self:
            product = order._get_discount_product()  # product.product de tu XML
            # Calcular monto positivo a descontar
            amount = order._compute_tour_leader_discount_amount()

            # Filtrar líneas de descuento existentes por PRODUCTO (no por flag)
            disc_lines = order.order_line.filtered(lambda l: l.product_id == product)

            if not order.id:
                # ===== CASO A: Orden sin guardar (onchange) =====
                # Borrar en memoria cualquier línea de descuento previa
                if disc_lines:
                    order.order_line -= disc_lines

                if amount <= 0:
                    # No corresponde mostrar línea
                    continue

                # Crear UNA línea en memoria, al final
                newline_vals = {
                    'name': _("Descuento Tour Líder"),
                    'product_id': product.id,
                    'product_uom_qty': 1.0,
                    'product_uom': product.uom_id.id,  # asegurar UoM
                    'price_unit': -amount,              # negativo = descuento
                    'discount': 0.0,
                    'tax_id': False,                    # sin impuestos
                    'display_type': False,
                    # Nota: 'order_id' NO se pone en new()
                }
                newline = self.env['sale.order.line'].new(newline_vals)
                # Append al final
                order.order_line += newline

            else:
                # ===== CASO B: Orden guardada (con id) =====
                # Si no hay monto, eliminar línea si existe
                if amount <= 0:
                    if disc_lines:
                        disc_lines.unlink()
                    continue

                # Preparar vals persistentes
                vals = {
                    'order_id': order.id,
                    'product_id': product.id,
                    'name': _("Descuento Tour Líder"),
                    'product_uom_qty': 1.0,
                    'product_uom': product.uom_id.id,
                    'price_unit': -amount,
                    'discount': 0.0,
                    'tax_id': [(5, 0, 0)],  # sin impuestos
                    # Ponerla al final con una secuencia mayor
                    'sequence': (max(order.order_line.mapped('sequence') or [10]) + 10),
                    'display_type': False,
                }

                if disc_lines:
                    # Actualizar la primera y eliminar duplicadas si las hubiera
                    main = disc_lines[0]
                    main.write(vals)
                    (disc_lines - main).unlink()
                else:
                    self.env['sale.order.line'].create(vals)

    # ---------------------------
    # Enganches para recalcular
    # ---------------------------
    @api.onchange('pricelist_id','tour_leader_count', 'order_line')
    def _onchange_tour_leader_discount_line(self):
        # Nota: onchange en líneas puede disparar varias veces; mantenerlo idempotente
        for order in self:
            # Asegurarse de que el precio de líneas está ya calculado por Odoo antes de ajustar
            order._ensure_tour_leader_discount_line()

    def write(self, vals):
        res = super().write(vals)
        # Recalcular si cambian campos relevantes
        fields_touch = {'order_line', 'tour_leader_count', 'pricelist_id'}
        if fields_touch.intersection(vals.keys()):
            self._ensure_tour_leader_discount_line()
        return res

    def action_update_tour_leader_discount(self):
        """Acción manual opcional (botón) por si quieres re-aplicar bajo demanda."""
        self._ensure_tour_leader_discount_line()