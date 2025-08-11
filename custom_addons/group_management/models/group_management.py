from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
import pytz

class GroupManagement(models.Model):
    _name = 'group.management'
    _description = 'Group Management'

    name = fields.Char(string='Reference', required=True, 
                       default=lambda self: self.env['ir.sequence'].next_by_code('group.management'))
    
        # Fechas del grupo (recomendado usar dos)
    date_start = fields.Datetime(string='Inicio del grupo')
    date_end = fields.Datetime(string='Fin del grupo')

    bundle_id = fields.Many2one('group.activity.bundle', string='Plantilla de actividades')
    #bundle_id = fields.Integer(string='Plantilla de actividades')

    sale_order_id = fields.Many2one('sale.order', string='Pedido de venta', readonly=True, copy=False)


    partner_id        = fields.Many2one('res.partner', string='Customer', required=True)
    state             = fields.Selection([('draft','Draft'),('confirmed','Confirmed')], default='draft')
    activity_line_ids = fields.One2many('group.activity.line', 'group_id', string='Activities')
    group_size = fields.Integer(string='Tamaño del Grupo', required=True,
                                help="Número total de personas en este grupo")
    language_id = fields.Many2one(
        'res.lang',
        string='Idioma del grupo',
        default=lambda self: self.env.lang,
        required=True
    )

    price_per_person_effective = fields.Monetary(string='Precio por persona (efectivo)',
                                                 help='Se congela al confirmar el grupo.')
    pricing_tier_id = fields.Many2one('group.activity.bundle.tier', string='Tramo aplicado', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    # (opcional) total provisional para mostrar (no imprescindible en esta etapa)
    total_provisional = fields.Monetary(string='Total provisional', compute='_compute_total_provisional', store=False)


    last_applied_group_size = fields.Integer(readonly=True, copy=False)
    last_applied_bundle_id = fields.Many2one('group.activity.bundle', readonly=True, copy=False)
    has_pending_changes = fields.Boolean(string='Cambios pendientes', compute='_compute_has_pending_changes',store=False)

    @api.depends('bundle_id', 'group_size')
    def _compute_total_provisional(self):
        for rec in self:
            price = rec._get_provisional_price_per_person()
            rec.total_provisional = (price or 0.0) * (rec.group_size or 0)


    def _float_to_hm(self, val):
        """9.5 -> (9,30). Devuelve (None,None) si val es None/False."""
        if val is None:
            return None, None
        h = int(val)
        m = int(round((val - h) * 60))
        if m == 60:
            h += 1
            m = 0
        return h, m

    # ===== LÓGICA DE CARGA DE ACTIVIDADES (igual que ya teníamos) =====
    def _load_bundle_lines(self):
        for rec in self:
            if not rec.bundle_id:
                continue

            # No generamos líneas si falta la fecha de inicio
            if not rec.date_start:
                rec.activity_line_ids = [(5, 0, 0)]
                return {
                    'warning': {
                        'title': _('Falta fecha'),
                        'message': _('Define la fecha de inicio del grupo para programar las actividades.')
                    }
                }

            # Limpiar y reconstruir
            rec.activity_line_ids = [(5, 0, 0)]
            vals = []

            # TZ del usuario para construir horas en local y luego guardarlas en UTC
            user_tz = rec.env.user.tz or 'UTC'
            tz = pytz.timezone(user_tz)

            # date_start viene almacenada en UTC; la convertimos a hora local del usuario
            base_local_start = fields.Datetime.context_timestamp(rec, rec.date_start)  # aware en TZ del usuario

            for bline in rec.bundle_id.line_ids:
                # Exigir hora de inicio para poder construir scheduled_from
                if bline.start_time is None:
                    raise UserError(
                        _("La plantilla '%s' tiene una actividad '%s' sin hora de inicio.")
                        % (rec.bundle_id.name, bline.template_id.display_name)
                    )

                # Offset de días: usa day_number si existe, si no, day_offset
                if hasattr(bline, 'day_number') and bline.day_number:
                    offset_days = max(0, (bline.day_number or 1) - 1)
                else:
                    offset_days = int(bline.day_offset or 0)

                base_local = base_local_start + timedelta(days=offset_days)

                # start_time / end_time en float -> hh:mm
                sh = int(bline.start_time)
                sm = int(round((bline.start_time - sh) * 60))
                if sm == 60:
                    sh += 1
                    sm = 0

                eh = em = None
                if bline.end_time is not None:
                    eh = int(bline.end_time)
                    em = int(round((bline.end_time - eh) * 60))
                    if em == 60:
                        eh += 1
                        em = 0

                # Construimos datetime en TZ local y luego convertimos a UTC (naive) para guardar
                start_local = base_local.replace(hour=sh, minute=sm, second=0, microsecond=0)
                scheduled_from = start_local.astimezone(pytz.UTC).replace(tzinfo=None)

                scheduled_to = False
                if eh is not None:
                    end_local = base_local.replace(hour=eh, minute=em, second=0, microsecond=0)
                    scheduled_to = end_local.astimezone(pytz.UTC).replace(tzinfo=None)

                vals.append((0, 0, {
                    'template_id': bline.template_id.id,
                    'scheduled_from': scheduled_from,
                    'scheduled_to': scheduled_to,
                }))

            rec.activity_line_ids = vals
    # ===== PRECIO PROVISIONAL (antes de confirmar) =====
    def _get_provisional_price_per_person(self):
        """Busca el tramo aplicable (sin congelar) para mostrar/calcular provisionalmente."""
        self.ensure_one()
        if not self.bundle_id or not self.group_size:
            return 0.0
        size = self.group_size
        # Seleccionar el tramo con min<=size<=max (o max vacío)
        tier = self.env['group.activity.bundle.tier'].search([
            ('bundle_id', '=', self.bundle_id.id),
            ('min_people', '<=', size),
            '|', ('max_people', '>=', size), ('max_people', '=', False),
        ], order='min_people asc', limit=1)
        return tier.price_per_person if tier else 0.0

    # ===== ONCHANGE: cuando cambien plantilla o tamaño, cargar actividades y refrescar provisionales =====
    @api.onchange('bundle_id', 'date_start')
    def _onchange_bundle_id(self):
        self._load_bundle_lines()
        # Nota: el precio provisional se recalcula solo por @api.depends en total_provisional

    @api.onchange('group_size')
    def _onchange_group_size(self):
        # Solo para disparar el compute de total_provisional (nada más)
        pass

    def action_load_bundle_lines(self):
        self._load_bundle_lines()
        return True

    # ===== CONFIRMAR: aquí SÍ congelamos =====
    def action_confirm_group(self):
        for rec in self:
            if not rec.bundle_id:
                raise UserError(_('Debes seleccionar una plantilla.'))
            if not rec.group_size or rec.group_size <= 0:
                raise UserError(_('Debes indicar el tamaño del grupo.'))
            if not rec.language_id:
                raise UserError(_("Debes definir el idioma del grupo antes de crear los tours."))

            size = rec.group_size
            Tier = rec.env['group.activity.bundle.tier']
            tier = Tier.search([
                ('bundle_id', '=', rec.bundle_id.id),
                ('min_people', '<=', size),
                '|', ('max_people', '>=', size), ('max_people', '=', False),
            ], order='min_people asc', limit=1)

            if not tier:
                raise UserError(_('No hay un tramo de precio que cubra %s personas en la plantilla "%s".') % (size, rec.bundle_id.name))

            # Congelar precio y tramo
            rec.price_per_person_effective = tier.price_per_person
            rec.pricing_tier_id = tier.id

            # Calcular total y crear la venta (una sola línea)
            total = (rec.price_per_person_effective or 0.0) * size
            # 3) Armar descripción y total
            description = rec._build_sale_line_description()
            # Busca o crea un producto “Grupo” (igual a como ya lo hacías)
            product = rec._get_or_create_group_product() if hasattr(rec, '_get_or_create_group_product') else rec.env['product.product'].search([('default_code', '=', 'GROUP_SERVICE')], limit=1)
            if not product:
                product = rec.env['product.product'].create({
                    'name': 'Grupo',
                    'detailed_type': 'service',
                    'default_code': 'GROUP_SERVICE',
                })

            order_vals = {
                'partner_id': rec.partner_id.id,
                'order_line': [(0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 1.0,
                    'price_unit': total,  # total del grupo
                    'name': description,
                    'tax_id': [(6, 0, [])],
                })],
            }
            order = rec.env['sale.order'].create(order_vals)
            rec.sale_order_id = order.id

            # Confirmar pedido (si tu flujo lo requiere)
            if hasattr(order, 'action_confirm'):
                order.action_confirm()

            # Cambiar estado del grupo si tienes un workflow
            if 'state' in rec._fields:
                rec.state = 'confirmed'

            Tour = self.env['tour.minimal']

            # --- Crear tours por cada línea de actividad ---
            for line in rec.activity_line_ids:
                # Determinar fechas para el tour
                date_start = line.scheduled_from or rec.date_start
                date_end = line.scheduled_to or rec.date_end
                if not date_start or not date_end:
                    # Si tu operación exige fechas por tour, bloquea con mensaje claro:
                    raise UserError(
                        _("La actividad '%s' no tiene fechas programadas. "
                        "Asigna 'scheduled_from'/'scheduled_to' o define 'date_start/date_end' en el grupo.")
                        % (line.template_id.display_name,)
                    )

                tour_vals = {
                    'name': f"{rec.name} – {line.template_id.name}",
                    'date_start': date_start,
                    'date_end': date_end,
                    'max_capacity': rec.group_size or 0,
                    'group_id': rec.id,                    # si tienes este campo en tour_inherit.py
                    'template_id': line.template_id.id,    # si lo tienes en tour_inherit.py
                    # Campos opcionales según tu modelo de tour:
                    'requires_cook': line.template_id.requires_cook,
                    'language_id': rec.language_id.id,
                    'state': 'draft',
                }
                new_tour = Tour.create(tour_vals)

                # (Opcional) crear participantes dummy como antes
                participants_vals = [(0, 0, {'name': f'Participante {i+1}'}) for i in range(rec.group_size or 0)]
                new_tour.write({'participants_ids': participants_vals})

            rec.last_applied_group_size = rec.group_size
            rec.last_applied_bundle_id = rec.bundle_id.id
        return True


    # ---------------------------
    # Helpers de precio/tramo
    # ---------------------------
    def _get_applicable_tier(self):
        """Devuelve el tramo que aplica (o None). No congela, solo selecciona."""
        self.ensure_one()
        if not self.bundle_id or not self.group_size:
            return None
        size = self.group_size
        return self.env['group.activity.bundle.tier'].search([
            ('bundle_id', '=', self.bundle_id.id),
            ('min_people', '<=', size),
            '|', ('max_people', '>=', size), ('max_people', '=', False),
        ], order='min_people asc', limit=1)

    def _build_sale_line_description(self):
        """Texto de la línea de venta: cabecera con personas/precio/total + actividades con fecha/hora."""
        self.ensure_one()

        # precio por persona: usa el congelado si existe; si no, el provisional
        price_pp = self.price_per_person_effective or self._get_provisional_price_per_person() or 0.0
        ppl = self.group_size or 0
        total = price_pp * ppl

        # cabecera
        title = f"Grupo: {self.name}"
        if self.bundle_id:
            title += f" — Plantilla: {self.bundle_id.name}"

        # helper de formato en TZ del usuario
        def fmt(dt):
            if not dt:
                return ""
            loc = fields.Datetime.context_timestamp(self, dt)
            return loc.strftime('%d/%m/%Y %H:%M')

        # detalle de actividades
        lines = []
        for l in self.activity_line_ids:
            if l.template_id:
                txt = f"- {l.template_id.display_name}"
                if l.scheduled_from:
                    txt += f" ({fmt(l.scheduled_from)}"
                    if l.scheduled_to:
                        txt += f" → {fmt(l.scheduled_to)}"
                    txt += ")"
                lines.append(txt)

        currency = self.currency_id and (self.currency_id.symbol or '') or ''
        header_info = f"Personas: {ppl}  |  Precio por persona: {price_pp:.2f} {currency}  |  Total: {total:.2f} {currency}"
        body = "\n".join(lines) if lines else "- Sin actividades configuradas"

        return f"{title}\n{header_info}\n{body}"


    # ---------------------------
    # Tours: recrear según líneas
    # ---------------------------
    def _sync_tours_from_lines(self):
        """Elimina tours existentes del grupo y crea nuevos a partir de las líneas actuales."""
        Tour = self.env['tour.minimal']

        for rec in self:
            if not rec.group_size or rec.group_size <= 0:
                raise UserError(_('Debes indicar el tamaño del grupo.'))
            if not rec.language_id:
                raise UserError(_("Debes definir el idioma del grupo antes de crear los tours."))
            # Elimina tours existentes del grupo (puedes filtrar por estado si quieres conservar confirmados)
            old_tours = Tour.search([('group_id', '=', rec.id)])
            old_tours.unlink()

            # Crea uno por cada línea
            for line in rec.activity_line_ids:
                date_start = line.scheduled_from or rec.date_start
                date_end = line.scheduled_to or rec.date_end
                if not date_start or not date_end:
                    # Si no quieres bloquear, podrías colocar fechas por defecto
                    raise UserError(
                        _("La actividad '%s' no tiene fechas programadas. "
                          "Define 'scheduled_from/to' o 'date_start/end' en el grupo.")
                        % (line.template_id.display_name,)
                    )
                participants_vals = [(0, 0, {'name': f'Participante {i+1}'})
                                     for i in range(rec.group_size or 0)]
                Tour.create({
                    'name': f"{rec.name} – {line.template_id.name}",
                    'date_start': date_start,
                    'date_end': date_end,
                    'max_capacity': rec.group_size or 0,
                    'group_id': rec.id,
                    'template_id': line.template_id.id,
                    # agrega más campos de tour si son requeridos en tu modelo
                    'state': 'draft',
                    'language_id': rec.language_id.id,
                    'participants_ids': participants_vals,
                })


    # ---------------------------por que new.tour
    # Venta: crear/actualizar cotización
    # ---------------------------
    def _ensure_sale_order(self):
        """Devuelve una sale.order (la crea si no existe)."""
        for rec in self:
            if rec.sale_order_id:
                continue
            product = rec._get_or_create_group_product() if hasattr(rec, '_get_or_create_group_product') \
                      else rec.env['product.product'].search([('default_code', '=', 'GROUP_SERVICE')], limit=1)
            if not product:
                product = rec.env['product.product'].create({
                    'name': 'Grupo',
                    'detailed_type': 'service',
                    'default_code': 'GROUP_SERVICE',
                })
            order = rec.env['sale.order'].create({
                'partner_id': rec.partner_id.id,
                'origin': rec.name,
            })
            rec.sale_order_id = order.id
        return self.mapped('sale_order_id')

    def _get_group_product(self):
        Product = self.env['product.product']
        product = Product.search([('default_code', '=', 'GROUP_SERVICE')], limit=1)
        if not product:
            product = Product.create({
                'name': 'Grupo',
                'detailed_type': 'service',
                'default_code': 'GROUP_SERVICE',
            })
        return product

    def _update_sale_order_line(self):
        """Asegura SO en borrador y actualiza/crea la única línea con total y detalle (sin impuestos)."""
        for rec in self:
            # 1) Asegurar que haya SO
            order = rec.sale_order_id
            if not order:
                rec._ensure_sale_order()
                order = rec.sale_order_id

            # 2) Normalizar estado: queremos editar en 'draft' o 'sent'
            if order.state == 'cancel':
                # Reabrir si existe; si no, duplicar a borrador
                if hasattr(order, 'action_draft'):
                    order.action_draft()
                else:
                    order.write({'state': 'draft'})
            elif order.state not in ('draft', 'sent'):
                # sale/done u otros -> duplicar a borrador
                if hasattr(order, 'action_unlock'):
                    order.action_unlock()

            # 3) Armar descripción y total
            description = rec._build_sale_line_description()
            total = (rec.price_per_person_effective or 0.0) * (rec.group_size or 0)

            # 4) Asegurar producto
            product = rec._get_group_product() if hasattr(rec, '_get_group_product') else self._get_group_product()

            # 5) Actualizar primera línea si existe; si no, crear una
            line = order.order_line[:1]
            if line:
                line.write({
                    'name': description,
                    'product_uom_qty': 1.0,
                    'price_unit': total,
                    'tax_id': [(6, 0, [])],   # sin impuestos
                    'product_id': product.id, # por si tenía otro producto
                })
            else:
                self.env['sale.order.line'].create({
                    'order_id': order.id,
                    'product_id': product.id,
                    'name': description,
                    'product_uom_qty': 1.0,
                    'price_unit': total,
                    'tax_id': [(6, 0, [])],   # sin impuestos
                })

    # ---------------------------
    # Acción: aplicar cambios tras editar
    # ---------------------------
    def action_apply_changes(self):
        """Reaplica tramo y actualiza tours + venta. No confirma el pedido."""
        for rec in self:
            if getattr(rec, 'state', 'draft') != 'confirmed':
                raise UserError(_('Solo puedes aplicar cambios cuando el grupo está confirmado.'))
            if not rec.has_pending_changes:
                raise UserError(_('No hay cambios pendientes que aplicar.'))
            if not rec.bundle_id:
                raise UserError(_('Debes seleccionar una plantilla.'))
            if not rec.group_size or rec.group_size <= 0:
                raise UserError(_('Debes indicar el tamaño del grupo.'))

            tier = rec._get_applicable_tier()
            if not tier:
                raise UserError(
                    _('No hay un tramo de precio que cubra %s personas en la plantilla "%s".')
                    % (rec.group_size, rec.bundle_id.name)
                )

            # Precio por persona PROVISIONAL aquí… pero como nos pediste que al editar se
            # refleje en la orden, actualizamos el efectivo también (sin confirmar el SO).
            rec.price_per_person_effective = tier.price_per_person
            rec.pricing_tier_id = tier.id

            # Rehacer tours según líneas
            rec._sync_tours_from_lines()

            # Actualizar cotización con total y descripción detallada
            rec._ensure_sale_order()
            rec._update_sale_order_line()

            rec.last_applied_group_size = rec.group_size
            rec.last_applied_bundle_id = rec.bundle_id.id

        return True
    
    def _compute_has_pending_changes(self):
        for rec in self:
            # Si no está confirmado, no mostramos el botón igualmente (control en la vista),
            # pero el flag puede calcularse igual.
            pending = False
            # Cambio en plantilla o tamaño vs lo “aplicado” por última vez
            if rec.bundle_id.id != (rec.last_applied_bundle_id.id if rec.last_applied_bundle_id else False):
                pending = True
            if (rec.group_size or 0) != (rec.last_applied_group_size or 0):
                pending = True

            # (Opcional) también podríamos considerar precio vs tramo actual:
            # tier = rec._get_applicable_tier()
            # if tier and rec.price_per_person_effective != tier.price_per_person:
            #     pending = True

            rec.has_pending_changes = pending