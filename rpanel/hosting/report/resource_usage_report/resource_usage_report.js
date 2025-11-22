frappe.query_reports["Resource Usage Report"] = {
    "filters": [
        {
            "fieldname": "website",
            "label": __("Website"),
            "fieldtype": "Link",
            "options": "Hosted Website"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Datetime",
            "default": frappe.datetime.add_days(frappe.datetime.nowdate(), -7)
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Datetime",
            "default": frappe.datetime.now_datetime()
        }
    ]
};
