# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

app_include_js = [
    "/assets/rpanel/js/hosting_branding.js",
    "/assets/rpanel/js/control_branding.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/rpanel/css/rpanel.css"
# web_include_js = "/assets/rpanel/js/rpanel.js"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "app"

# website user home page (by Role)
# role_home_page = {
#     "Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

after_install = "rpanel.install.after_install"
on_migrate = "rpanel.install.after_migrate"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "rpanel.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#     "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#     "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#     "ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#     "*": {
#         "on_update": "method",
#         "on_cancel": "method",
#         "on_trash": "method"
#     }
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily": [
        "rpanel.hosting.tasks.renew_expiring_ssl_certificates",
        "rpanel.hosting.tasks.send_ssl_expiry_alerts",
        "rpanel.hosting.tasks.cleanup_old_backups",
        "rpanel.hosting.tasks.check_site_health"
    ],
    "hourly": [
        "rpanel.hosting.tasks.run_scheduled_cron_jobs"
    ]
}

# Testing
# -------

# before_tests = "rpanel.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#     "frappe.desk.doctype.event.event.get_events": "rpanel.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#     "Task": "rpanel.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]


# User Data Protection
# --------------------

# user_data_fields = [
#     {
#         "doctype": "{doctype_1}",
#         "filter_by": "{filter_by}",
#         "redact_fields": ["{field_1}", "{field_2}"],
#         "partial": 1,
#     },
#     {
#         "doctype": "{doctype_2}",
#         "filter_by": "{filter_by}",
#         "partial": 1,
#     },
#     {
#         "doctype": "{doctype_3}",
#         "strict": False,
#     },
#     {
#         "doctype": "{doctype_4}"
#     }
# ]

# Authentication and authorization
# -----------------------------------

# auth_hooks = [
#     "rpanel.auth.validate"
# ]

# Fixtures
# --------

fixtures = [
    {
        "dt": "Workspace",
        "filters": [["name", "in", ["Hosting"]]]
    }
]
