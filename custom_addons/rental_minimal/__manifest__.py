# rental_minimal/__manifest__.py
{
    "name": "Vehicle Rental (Minimal)",
    "version": "17.0.1.0.0",
    "author": "Mahinatur · Isla de Pascua",
    "website": "https://mahinatur.cl",
    "license": "LGPL-3",
    "depends": ["base", "fleet", "sale_management"],
    "data": [
        'data/product_category_data.xml',
        "security/rental_minimal_security.xml",
        "security/ir.model.access.csv",
        "views/fleet_vehicle_views.xml",
        "views/rental_booking_views.xml",
        "views/rental_return_wizard.xml",
        'views/sale_order_view.xml',
        'views/product_template_views.xml',
    ],
    "installable": True,
    "application": True,
}