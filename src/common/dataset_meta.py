"""Single source of truth for synthetic-property metadata, shared by the
dataset prep script and every workload runner (so filtered-lookup queries
always filter on a department that actually exists in the loaded data)."""

DEPARTMENTS = [
    "trading", "legal", "finance", "engineering", "operations",
    "hr", "executive", "regulatory", "sales", "it",
]
