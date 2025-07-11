{
    "name": "Kitchen Meal Summary",
    "version": "1.0",
    "summary": "Resumen diario de almuerzos para cocina",
    "category": "Operations",
    "depends": ["base", "tour_minimal_odoo17"],
    "data": [
        "security/ir.model.access.csv",
        "views/kitchen_meal_summary_views.xml",
        'views/kitchen_special_event_views.xml'
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}
