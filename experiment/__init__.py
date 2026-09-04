"""
experiment package — AppScout Experiment Pipeline

Modules
-------
models                  Lightweight dataclasses (RawResponse, InspectionReport, AppData, ExtractionMeta, DiscoveryResult, CategoryTraversalResult, MasterFrontierResult, FrontierAppEntry).
acquire                 Make one HTTP GET request and persist the raw response (with offline snapshot reuse).
inspect_response        Read a saved raw response and produce a human-readable report.
extract                 Extract 8 core fields from an app listing snapshot.
validate                Validate extracted data against sanity checks and ground truth.
discover                Discover, normalize, filter, and deduplicate app URLs from listing/category pages.
investigate_categories  Investigate category directory hierarchy and pagination behavior.
discover_categories    Discover category taxonomy and classify root vs crawlable leaf categories.
traverse_category       Traverse all pagination pages of a category via rel="next" links.
build_frontier          Orchestrate multi-category traversal and build Master App URL Frontier.
db                      PostgreSQL persistence package (models, engine, sessions, repositories).
ingest                  Validate and persist extraction results into PostgreSQL.
run_ingestion           Automated database-aware ingestion orchestrator from Master Frontier.
verify_database         Audit and report PostgreSQL database metrics, tables, and sample records.
run_experiment          Single-app pipeline engine and CLI.
run_batch               Sequential controlled batch orchestrator.
"""
