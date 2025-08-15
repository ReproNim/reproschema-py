# reproschema-py - Documentation

## Inherits From
→ Parent: ../../internal/CLAUDE.md (all shared practices apply)

## Repository Purpose
Python library for ReproSchema validation, conversion, and manipulation

## Local Overrides
- **Python**: 3.8+ (parent: 3.7+) - Need dataclasses and typing features
- **Testing**: 90% coverage (parent: 80%) - Critical library requiring high reliability
- **Type hints**: Required for all public APIs - Better IDE support and documentation

## Tech Stack
- Language: Python 3.8+
- Validation: Pydantic
- CLI: Click
- Testing: pytest, pytest-cov

## Key Commands
```bash
# Development
pip install -e .
pytest --cov=reproschema

# CLI usage
reproschema validate <path>
reproschema redcap2reproschema <input> <output>
```

## Dependencies
- **Depends on**: reproschema (core definitions)
- **Used by**: reproschema-agents, reproschema-server
- **External**: pydantic, click, jsonld

## Current Focus
- Active: FHIR converter implementation
- Next: Optimize validation performance
- Blocked: None

## Recent Changes (Last 5)
- 2025-01-29: Memory optimization → ./learnings/2025-01-memory.md
- 2025-01-28: Added FHIR support → ./changes/2025-01-fhir.md

## Local Patterns
- CLI design → ./patterns/cli-architecture.md
- Converter pattern → ./patterns/converter-design.md
- Validation pipeline → ./patterns/validation-flow.md

## Quick Links
- PyPI: https://pypi.org/project/reproschema
- CI: .github/workflows/test.yml
- Issues: /issues?label=reproschema-py

---
*Line count: ~65 (target: < 100)*