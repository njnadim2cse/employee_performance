/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState, xml } from "@odoo/owl";

class EmployeePerformanceDashboard extends Component {
    setup() {
        // Use the correct service names for Odoo 19
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            loading: true,
            data: null,
            error: null,
        });

        onMounted(() => {
            this.loadData();
        });
    }

    async loadData() {
        try {
            this.state.loading = true;
            // Use orm.call instead of rpc
            const data = await this.orm.call("employee.performance", "get_dashboard_data", []);
            this.state.data = data;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.error = error;
            this.state.data = this.getMockData();
        } finally {
            this.state.loading = false;
        }
    }

    getMockData() {
        return {
            company_revenue: 18,
            company_cs: 92,
            c_level: 94,
            division_tst: 97,
            division_pm: 98,
            individual_quality_val: 4.2,
            individual_quality_pct: 84,
            summary: {
                total_kpis: 87,
                avg_score: 4.2,
                active_kpis: 23,
                employees: 156,
                pending: 8,
            },
            kpis: [
                {
                    name: 'Revenue Target',
                    target: 100,
                    achieved: 85,
                    role: 'CEO',
                    alignment: 'Company',
                    status: 'On Track'
                },
                {
                    name: 'Customer Satisfaction',
                    target: 95,
                    achieved: 92,
                    role: 'COO',
                    alignment: 'Company',
                    status: 'Achieved'
                },
                {
                    name: 'Job Completion Rate',
                    target: 90,
                    achieved: 94,
                    role: 'C-Level',
                    alignment: 'C Level',
                    status: 'Exceeded'
                }
            ]
        };
    }

    onAddKPI() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Add KPI',
            res_model: 'performance.objective',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    onEvaluatePerformance() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Evaluate Performance',
            res_model: 'employee.performance',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    onSubmitAppraisal() {
        this.action.doAction('employee_performance.action_employee_performance_entries');
    }

    onViewReports() {
        console.log('View Reports clicked');
    }

    getStatusBadgeClass(status) {
        const statusMap = {
            'achieved': 'bg-success',
            'on track': 'bg-primary',
            'exceeded': 'bg-info',
            'at risk': 'bg-warning',
            'behind': 'bg-danger',
        };
        return statusMap[status?.toLowerCase()] || 'bg-secondary';
    }

    getCircleStroke(percentage) {
        const circumference = 2 * Math.PI * 40;
        const offset = circumference - (percentage / 100.0) * circumference;
        return {
            strokeDasharray: circumference,
            strokeDashoffset: offset,
        };
    }
}

// INLINE TEMPLATE
EmployeePerformanceDashboard.template = xml`
<div class="o_employee_performance_dashboard p-3">
    <!-- Loading State -->
    <t t-if="state.loading">
        <div class="text-center p-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div class="mt-2">Loading dashboard data...</div>
        </div>
    </t>

    <!-- Error State -->
    <t t-elif="state.error">
        <div class="alert alert-danger">
            <h4>Error Loading Dashboard</h4>
            <p>Failed to load dashboard data. Showing sample data instead.</p>
        </div>
    </t>

    <!-- Main Dashboard Content -->
    <div t-if="!state.loading and state.data">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <div>
                <h1 class="mb-0">Appraisal KPI Dashboard</h1>
                <div class="text-muted small">Monitor Performance Across All Levels</div>
            </div>
            <div>
                <button type="button" class="btn btn-primary me-2" t-on-click="onAddKPI">Add KPI</button>
                <button type="button" class="btn btn-outline-secondary me-2" t-on-click="onEvaluatePerformance">Evaluate Performance</button>
                <button type="button" class="btn btn-success me-2" t-on-click="onSubmitAppraisal">Submit Appraisal</button>
                <button type="button" class="btn btn-light" t-on-click="onViewReports">View Reports</button>
            </div>
        </div>

        <div class="row g-3">
            <div class="col-md-6">
                <div class="card p-3">
                    <h6 class="text-muted">Company Level</h6>
                    <div class="d-flex justify-content-between">
                        <span>Revenue Increase</span>
                        <span class="fw-bold" t-esc="state.data.company_revenue + '%'"/>
                    </div>
                    <div class="progress mb-2" style="height:6px;">
                        <div class="progress-bar" role="progressbar" t-att-style="'width: ' + state.data.company_revenue + '%'"/>
                    </div>

                    <div class="d-flex justify-content-between">
                        <span>Customer Satisfaction</span>
                        <span class="fw-bold" t-esc="state.data.company_cs + '%'"/>
                    </div>
                    <div class="progress" style="height:6px;">
                        <div class="progress-bar" role="progressbar" t-att-style="'width: ' + state.data.company_cs + '%'"/>
                    </div>
                </div>
            </div>

            <div class="col-md-3">
                <div class="card p-3 text-center">
                    <h6 class="text-muted">C Level</h6>
                    <div class="my-2">
                        <svg width="90" height="90">
                            <circle cx="45" cy="45" r="40" stroke="#eee" stroke-width="8" fill="none"/>
                            <circle cx="45" cy="45" r="40" stroke="#7c4dff" stroke-width="8" fill="none" 
                                    stroke-linecap="round"
                                    t-att-stroke-dasharray="getCircleStroke(state.data.c_level).strokeDasharray"
                                    t-att-stroke-dashoffset="getCircleStroke(state.data.c_level).strokeDashoffset"/>
                        </svg>
                        <div class="mt-2 fw-bold" t-esc="state.data.c_level + '%'"/>
                        <div class="small text-muted">Job Completion</div>
                    </div>
                </div>
            </div>

            <div class="col-md-3">
                <div class="card p-3">
                    <h6 class="text-muted">Performance Summary</h6>
                    <div class="d-flex justify-content-between">
                        <div>
                            <div class="fw-bold fs-4" t-esc="state.data.summary.total_kpis + '%'"/>
                            <div class="small text-muted">Total KPIs Achieved</div>
                        </div>
                        <div>
                            <div class="fw-bold fs-4" t-esc="state.data.summary.avg_score + '/5'"/>
                            <div class="small text-muted">Average Score</div>
                        </div>
                    </div>

                    <div class="mt-3 small">
                        <div>Active KPIs: <span class="fw-bold" t-esc="state.data.summary.active_kpis"/></div>
                        <div>Employees Evaluated: <span class="fw-bold" t-esc="state.data.summary.employees"/></div>
                        <div>Pending Reviews: <span class="fw-bold text-warning" t-esc="state.data.summary.pending"/></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Division & Individual -->
        <div class="row g-3 mt-1">
            <div class="col-md-6">
                <div class="card p-3">
                    <h6 class="text-muted">Division Level</h6>
                    <div class="d-flex gap-3">
                        <div class="text-center">
                            <div class="rounded-circle border border-primary d-flex align-items-center justify-content-center" style="width:90px;height:90px;">
                                <div class="fw-bold fs-5" t-esc="state.data.division_tst + '%'"/>
                            </div>
                            <div class="small text-muted mt-1">TST Performance</div>
                        </div>
                        <div class="text-center">
                            <div class="rounded-circle border border-info d-flex align-items-center justify-content-center" style="width:90px;height:90px;">
                                <div class="fw-bold fs-5" t-esc="state.data.division_pm + '%'"/>
                            </div>
                            <div class="small text-muted mt-1">PM Performance</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card p-3">
                    <h6 class="text-muted">Individual Level</h6>
                    <div class="d-flex justify-content-between">
                        <span>Quality Score</span>
                        <span class="fw-bold" t-esc="state.data.individual_quality_val + '/5'"/>
                    </div>
                    <div class="progress mt-2" style="height:6px;">
                        <div class="progress-bar" role="progressbar" t-att-style="'width: ' + state.data.individual_quality_pct + '%'"/>
                    </div>
                </div>
            </div>
        </div>

        <!-- KPI Performance Details table -->
        <div class="card p-3 mt-3">
            <h6 class="text-muted">KPI Performance Details</h6>
            <table class="table table-sm mt-2">
                <thead class="table-light">
                    <tr>
                        <th>KPI Name</th>
                        <th>Target %</th>
                        <th>Achieved %</th>
                        <th>Responsible Role</th>
                        <th>Alignment</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr t-foreach="state.data.kpis" t-as="kpi" t-key="kpi_index">
                        <td t-esc="kpi.name"/>
                        <td t-esc="kpi.target + '%'"/>
                        <td t-esc="kpi.achieved + '%'"/>
                        <td t-esc="kpi.role"/>
                        <td t-esc="kpi.alignment"/>
                        <td>
                            <span t-att-class="'badge ' + getStatusBadgeClass(kpi.status)" t-esc="kpi.status"/>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</div>`;

registry.category("actions").add("employee_performance_dashboard", EmployeePerformanceDashboard);

export default EmployeePerformanceDashboard;