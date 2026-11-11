dev_cost_rub = 30000
monthly_fixed_rub = 3000
minutes_saved_per_incident = 8
hourly_labor_rub = 900
llm_cost_rub_per_incident = 0
value_per_incident = minutes_saved_per_incident / 60 * hourly_labor_rub
net_per_incident = value_per_incident - llm_cost_rub_per_incident
monthly_break_even = monthly_fixed_rub / net_per_incident
print(f"Estimated gross savings per incident: {value_per_incident:.2f} RUB")
print(f"Monthly operating break-even: {monthly_break_even:.1f} incidents")
print(f"First-month break-even including development: {(dev_cost_rub+monthly_fixed_rub)/net_per_incident:.1f} incidents")
