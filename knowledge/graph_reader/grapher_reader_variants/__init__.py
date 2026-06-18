"""Concrete ``GraphReader`` implementations."""

from knowledge.graph_reader.grapher_reader_variants.whole_file_reader import (
    WholeFileReader,
    as_claude_tool,
)

__all__ = ["WholeFileReader", "as_claude_tool"]
