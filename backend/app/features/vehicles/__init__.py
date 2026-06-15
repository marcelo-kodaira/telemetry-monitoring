"""Public surface of the vehicles slice — the one sanctioned cross-slice edge (telemetry delegates
the fault invariant here) imports from this package, not from internal modules."""
from app.features.vehicles.status_update import apply_fault, apply_status

__all__ = ["apply_fault", "apply_status"]
