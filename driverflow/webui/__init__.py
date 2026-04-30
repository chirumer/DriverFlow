"""Web UI workspace subpackage for DriverFlow.

Boots a FastAPI server that exposes every Pipeline tool through a richer
single-page workspace (raw / processed / exported sidebars, versioned data
workspace, model loader, pluggable tools and exporters).

Top-level entry point lives in :mod:`driverflow._driverflow_new`; this
subpackage owns everything beneath it (server, state, tools, exporters,
static assets).
"""
