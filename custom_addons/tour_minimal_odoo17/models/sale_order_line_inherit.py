from odoo import models, fields, api, _ 
from odoo.exceptions import UserError
import logging, inspect, os
from datetime import datetime, time
_logger = logging.getLogger(__name__)
_logger.warning(">> tour_minimal_odoo17 loaded from: %s", __file__)

class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    package_parent_id = fields.Many2one(
        'sale.order.line', string='Línea padre (paquete)', ondelete='cascade'
    )
    is_package_component = fields.Boolean(string='Es componente de paquete', default=False)
    service_date = fields.Date(string='Fecha del servicio (línea)')
    # (Asegúrate de tener los campos si vas a guardar el tour ahí)
    tour_id = fields.Many2one('tour.minimal', string='Tour')
    # Heredado del producto tour
    service_kind = fields.Selection(
        [('sib', 'SIB (regular con cupos)'), ('private', 'Privado (crear salida)'), ('external', 'Externo (actividad sin tour)')],
        related='product_id.product_tmpl_id.service_kind',
        store=True, readonly=True
    )

    # Identificación add-on
    is_tour_addon = fields.Boolean(related='product_id.product_tmpl_id.is_tour_addon', store=True, readonly=True)
    addon_code    = fields.Selection(related='product_id.product_tmpl_id.addon_code', store=True, readonly=True)

    def _expand_tour_package(self):
        """Crear líneas hijas para un paquete."""
        for line in self:
            tmpl = line.product_id.product_tmpl_id
            if not tmpl.is_tour_package or line.is_package_component:
                continue

            # Evitar doble creación
            existing_children = self.search([('package_parent_id', '=', line.id)])
            if existing_children:
                continue

            exists = self.search([
                ('order_id', '=', line.order_id.id),
                ('package_parent_id', '=', line.id),
                ('is_package_component', '=', True),
            ], limit=1)
            if exists:
                continue

            # Mapa de etiquetas para service_kind (definido en product.template)
            label_map = dict(self.env['product.template']._fields['service_kind'].selection)
            

            vals_list = []
            for comp in tmpl.package_line_ids:
                sk = comp.product_id.product_tmpl_id.service_kind
                label = label_map.get(sk, '')
                name = comp.product_id.display_name + (f" ({label})" if label else '')
                vals_list.append({
                    'order_id': line.order_id.id,
                    'package_parent_id': line.id,
                    'is_package_component': True,
                    'product_id': comp.product_id.id,
                    'name': name,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': 0.0,
                    'discount': 0.0,
                    'display_type': False,
                })
            if vals_list:
                self.env['sale.order.line'].create(vals_list)

    
    def open_configure_tour_wizard(self):
        if not self.order_id or not self.order_id.exists():
            raise UserError("La orden de venta asociada no existe o fue eliminada.")
        self.ensure_one()

        # 2) Si el producto es externo, abrimos el wizard “vacío”
        # 1) Ramo EXTERNO: abrimos un wizard 'vacío' con context defaults
        if self.product_id.product_tmpl_id.is_external:
            return {
                'name': 'Reservar Tour Externo',
                'type': 'ir.actions.act_window',
                'res_model': 'tour.selection.external.wizard',
                'view_mode': 'form',
                'view_id': self.env.ref(
                    'tour_minimal_odoo17.tour_selection_external_wizard_form'
                ).id,
                'target': 'new',
                'context': {
                    'default_order_id': self.order_id.id,
                    'default_sale_order_line_id': self.id,
                },
            }
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
    
    def _action_confirm(self):
        """Interceptar confirmación para desglosar paquetes."""
        for line in self:
            line._expand_tour_package()
        return super()._action_confirm()
    
    def _prepare_invoice_line(self, **optional_values):
        self.ensure_one()
        if self.is_package_component:
            # No facturar líneas hijas
            return False
        return super()._prepare_invoice_line(**optional_values)
    
            # ====== Fase 3 (SIB): asignar por FECHA (línea) + TIPO DE TOUR ======
    # ====== Fase 3 (SIB): asignar por FECHA (línea) + TIPO DE TOUR ======
    def _assign_sib_to_existing_tour_by_date_and_type(self):
        for line in self:
            if not (line.service_kind == 'sib'):
                continue

            if not line.service_date:
                raise UserError(_("La línea SIB '%s' requiere una Fecha de servicio.") % (line.name,))

            # Derivar tipo de tour desde el producto
            tour_type = line.product_id.product_tmpl_id.tour_type_id
            if not tour_type:
                raise UserError(_("El producto '%s' no tiene asignado un 'Tipo de tour'." % line.product_id.display_name))

            # Buscar tours SIB del mismo tipo y mismo día (ignorando hora)
            # Asumimos que el campo fecha/hora del tour es date_start (Datetime)
            tours = self.env['tour.minimal'].search([
                ('tour_type_id', '=', tour_type.id),
                ('state', 'in', ['draft', 'confirmed']),
            ])
            _logger.warning("[TOUR SIB] Tours disponibles para tipo '%s': %s",
                tour_type.name, tours.mapped('date_start'))
            same_day = tours.filtered(lambda t: t.date_start and t.date_start.date() == line.service_date)
            _logger.warning("[TOUR SIB] Tours el %s: %s", line.service_date,
                            same_day.mapped('date_start'))
            if not same_day:
                raise UserError(_(
                    "No existe un tour SIB de tipo '%s' en la fecha %s."
                ) % (tour_type.name, fields.Date.to_string(line.service_date)))

            qty_needed = int(line.product_uom_qty)
            selected = False
            for tour in same_day:
                available = tour.max_capacity - len(tour.participants_ids)
                if available >= qty_needed:
                    selected = tour
                    break

            if not selected:
                raise UserError(_(
                    "No hay cupos suficientes en los tours SIB del %s para el tipo '%s'. "
                    "Necesitas %d cupos."
                ) % (fields.Date.to_string(line.service_date), tour_type.name, qty_needed))

            # Asignar tour a la línea hija
            line.tour_id = selected.id

            # Crear participantes placeholder si no existen aún para esta línea
            existing = self.env['tour.participant'].search_count([
                ('sale_order_line_id', '=', line.id)
            ])
            to_create = qty_needed - existing
            if to_create > 0:
                vals = []
                base_name = f"{line.order_id.name or 'SO'} - {line.product_id.display_name} -{line.order_id.partner_id.name}"
                for i in range(to_create):
                    vals.append({
                        'name': f"{base_name} - PAX {existing + i + 1}",
                        'tour_id': selected.id,
                        'sale_order_id': line.order_id.id,
                        'sale_order_line_id': line.id,
                    })
                self.env['tour.participant'].create(vals)
            _logger.info("[SIB] %s PAX asignados a tour %s (%s) para línea %s",
                         qty_needed, selected.name, selected.date_start, line.id)
            

    def _ensure_private_tour_created(self):
        """Para CUALQUIER línea tour PRIVATE (hija o no): crear tour y participantes."""
        Tour = self.env['tour.minimal']
        Participant = self.env['tour.participant']

        for line in self:
            tmpl = line.product_id.product_tmpl_id

            if not (getattr(tmpl, 'is_tour_ticket', False)
                    and line.service_kind == 'private'):
                continue

            if tmpl.is_tour_package:
                continue  # 🔥 Saltar líneas que son paquetes

            if not (tmpl.is_tour_ticket and line.service_kind == 'private'):
                continue

            tour_type = line.product_id.product_tmpl_id.tour_type_id
            if not tour_type:
                raise UserError(_("El producto '%s' no tiene asignado un 'Tipo de tour'.") % line.product_id.display_name)

            # Hora por defecto (ajústala si luego agregamos un campo en producto)
            date_start_dt = datetime.combine(line.service_date, time(hour=9, minute=0))

            vals = {
                'name': "%s - %s" % (line.order_id.partner_id.display_name or 'Privado', tour_type.name),
                'tour_type_id': tour_type.id,
                'service_kind': tmpl.service_kind,
                'date_start': date_start_dt,
                'max_capacity': int(line.product_uom_qty),
                'sale_order_ids': [(6, 0, [line.order_id.id])],
                'state': 'draft',
            }
            if 'product_id' in Tour._fields:
                vals['product_id'] = line.product_id.id

            if 'language_id' in Tour._fields and tmpl.language_id:
                vals['language_id'] = tmpl.language_id.id  # <- Aquí se añade el idioma del producto


            tour = Tour.create(vals)
            line.tour_id = tour.id

            # Participantes (uno por PAX) con nombre del cliente
            qty = int(line.product_uom_qty)
            cust = line.order_id.partner_id.display_name or line.order_id.partner_id.name or 'Cliente'
            base = f"{cust} ({line.product_id.display_name})"
            Participant.create([{
                'name': f"{base} - PAX {i+1}",
                'tour_id': tour.id,
                'sale_order_id': line.order_id.id,
            } for i in range(qty)])

    def _ensure_activity_tours_created(self):
        """Crea tours o actividades según service_kind: 'private' o 'external'."""
        Tour = self.env['tour.minimal']
        Participant = self.env['tour.participant']

        for line in self:
            tmpl = line.product_id.product_tmpl_id

            kind = line.service_kind
            if kind not in ('external') or tmpl.is_tour_package:
                continue

            if not line.service_date:
                raise UserError(_(
                    "La línea '%s' requiere Fecha de servicio/actividad."
                ) % line.display_name)


            date_start = datetime.combine(line.service_date, time(hour=9, minute=0))
            vals = {
                'name': f"{line.product_id.display_name or 'Cliente'}",
                'service_kind': tmpl.service_kind,
                'date_start': date_start,
                'max_capacity': int(line.product_uom_qty),
                'sale_order_ids': [(6, 0, [line.order_id.id])],
                'state': 'draft',
            }
            if 'product_id' in Tour._fields:
                vals['product_id'] = line.product_id.id
            if 'language_id' in Tour._fields and tmpl.language_id:
                vals['language_id'] = tmpl.language_id.id
            if 'provider_id' in Tour._fields:
                vals['provider_id'] = tmpl.provider_id.id or False

            _logger.warning("Proveedor del producto %s: %s", tmpl.name, tmpl.provider_id.name)

            tour = Tour.create(vals)
            line.tour_id = tour.id

            if kind == 'external':
                qty = int(line.product_uom_qty)
                cust_name = line.order_id.partner_id.display_name or 'Cliente'
                base = f"{cust_name} ({line.product_id.display_name})"
                Participant.create([{
                    'name': f"{base} - PAX {i+1}",
                    'tour_id': tour.id,
                    'sale_order_id': line.order_id.id,
                } for i in range(qty)])

    
    
    