// Copyright (c) 2025, ROKCT Holdings and contributors
// For license information, please see license.txt

frappe.query_reports["SSL Expiry Report"] = {
    "filters": [
        {
            "fieldname": "domain",
            "label": __("Domain"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "expiring_within_days",
            "label": __("Expiring Within Days"),
            "fieldtype": "Int",
            "default": 30,
            "width": 100
        },
        {
            "fieldname": "status",
            "label": __("Site Status"),
            "fieldtype": "Select",
            "options": "\nActive\nPending\nSuspended\nError",
            "width": 100
        }
    ],

    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname == "days_until_expiry") {
            if (data.days_until_expiry <= 7) {
                value = `<span class="indicator-pill red">${data.days_until_expiry} days</span>`;
            } else if (data.days_until_expiry <= 30) {
                value = `<span class="indicator-pill orange">${data.days_until_expiry} days</span>`;
            } else {
                value = `<span class="indicator-pill green">${data.days_until_expiry} days</span>`;
            }
        }

        if (column.fieldname == "ssl_status") {
            if (data.ssl_status === "Active") {
                value = `<span class="indicator-pill green">Active</span>`;
            } else {
                value = `<span class="indicator-pill red">${data.ssl_status}</span>`;
            }
        }

        return value;
    }
};
