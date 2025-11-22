// Copyright (c) 2025, ROKCT Holdings and contributors
// For license information, please see license.txt

frappe.query_reports["Website Status Report"] = {
    "filters": [
        {
            "fieldname": "domain",
            "label": __("Domain"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": "\nActive\nPending\nSuspended\nError",
            "width": 100
        },
        {
            "fieldname": "site_type",
            "label": __("Site Type"),
            "fieldtype": "Select",
            "options": "\nManual\nCMS",
            "width": 100
        },
        {
            "fieldname": "ssl_status",
            "label": __("SSL Status"),
            "fieldtype": "Select",
            "options": "\nActive\nFailed\nPending",
            "width": 100
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "width": 100
        }
    ],

    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname == "status") {
            if (data.status === "Active") {
                value = `<span class="indicator-pill green">Active</span>`;
            } else if (data.status === "Pending") {
                value = `<span class="indicator-pill orange">Pending</span>`;
            } else if (data.status === "Error") {
                value = `<span class="indicator-pill red">Error</span>`;
            } else if (data.status === "Suspended") {
                value = `<span class="indicator-pill red">Suspended</span>`;
            }
        }

        if (column.fieldname == "ssl_status") {
            if (data.ssl_status === "Active") {
                value = `<span class="indicator-pill green"><i class="fa fa-lock"></i> Active</span>`;
            } else if (data.ssl_status === "Failed") {
                value = `<span class="indicator-pill red">Failed</span>`;
            } else {
                value = `<span class="indicator-pill gray">${data.ssl_status || 'None'}</span>`;
            }
        }

        if (column.fieldname == "domain") {
            const protocol = data.ssl_status === "Active" ? "https" : "http";
            value = `<a href="${protocol}://${data.domain}" target="_blank">${data.domain}</a>`;
        }

        return value;
    }
};
