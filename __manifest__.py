{
    "name": "Employee Performance",
    "version": "1.0.0",
    "summary": "Employee performance, KPI, hierarchy observation, bottom-up aggregation (Odoo 19)",
    "category": "Human Resources",
    "author": "yours",
    "depends": ["hr", "hr_org_chart", "mail", "web"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/dashboard_view.xml",        # Load dashboard XML FIRST
        "views/performance_views.xml",     
        "views/config_views.xml",
        "views/employee_extension_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "employee_performance/static/src/js/employee_performance_dashboard.js",
            "employee_performance/static/src/js/hierarchy_checked.js"
        ]
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}