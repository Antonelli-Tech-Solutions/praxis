"""The Praxis knowledge loop: ingest -> store -> read.

Three core pieces, each an abstract parent with swappable variants:

- ``knowledge_graph`` — the store (MVP: an in-memory string).
- ``injestion``      — distills raw input into the graph.
- ``graph_reader``   — retrieves knowledge for the agent, given context.
"""
