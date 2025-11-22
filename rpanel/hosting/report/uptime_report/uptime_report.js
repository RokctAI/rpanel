frappe.query_reports["Uptime Report"] = {
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
    ],

    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname == "is_up") {
            if (data.is_up == "Up") {
                value = `<span class="indicator-pill green">${value}</span>`;
            } else {
                value = `<span class="indicator-pill red">${value}</span>`;
            }
        }

        if (column.fieldname == "status_code") {
            if (data.status_code >= 200 && data.status_code < 300) {
                value = `<span style="color: green;">${value}</span>`;
            } else if (data.status_code >= 400) {
                value = `<span style="color: red;">${value}</span>`;
            }
        }

        return value;
    }
};
