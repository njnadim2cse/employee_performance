/** @odoo-module **/

import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

const hierarchyCheckedService = {
    dependencies: ["orm"],
    
    start(env, { orm }) {
        return {
            aggregateForEmployee: (emp_id) => {
                return orm.call("hr.employee", "action_aggregate_subordinates", [[emp_id]]);
            }
        };
    },
};

// Register the service
serviceRegistry.add("hierarchy_checked", hierarchyCheckedService);

// Export for direct use
export function aggregate_for_employee(emp_id) {
    const orm = registry.category("services").get("orm");
    return orm.call("hr.employee", "action_aggregate_subordinates", [[emp_id]]);
}

// Global export for compatibility
window.employee_performance_aggregate_for_employee = aggregate_for_employee;