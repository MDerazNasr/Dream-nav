# 0004 Viewer API Boundary

The viewer loads scene bundles through the FastAPI routes instead of importing local registry files so the frontend, backend, and future processing pipeline share one HTTP contract.
