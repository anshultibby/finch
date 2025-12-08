# API Documentation

This directory contains API documentation that is automatically mounted into code execution environments.

The LLM can discover available APIs by:
1. Listing this directory: `os.listdir('/apis')`
2. Reading specific API docs: `open('/apis/fmp.py').read()`

This implements the progressive disclosure pattern from Anthropic's MCP article - APIs are discovered on-demand rather than loaded into context upfront.

