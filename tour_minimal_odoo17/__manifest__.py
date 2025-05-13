{
    "name": "Tour Minimal Odoo 17",
    "version": "1.0",
    "summary": "Módulo mínimo para Odoo 17",
    "author": "ChatGPT",
    "depends": ["base",'hr_contract',"hr","fleet",'sale','hr_expense'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/tour_minimal_views.xml',
        'views/tour_minimal_modifiers.xml',
        'views/product_template_view.xml',
        'views/tour_participant_views.xml',
        'views/sale_order_inherit_views.xml',
        'views/wizard/tour_selection_wizard_views.xml',
        'views/sale_order_form_inherit_tour.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_currency_readonly.xml',
        'security/ir.model.access.csv', # <--- agrega aquí tu nueva vista
    ],
    "images": ['static/description/icon.png'],
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}