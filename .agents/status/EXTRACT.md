# Status: EXTRACT Agent

## Progress
- `ProductionPreFilter` implemented in `app/pipeline/prefilter.py`:
  - Zero-LLM filter dropping noise: greetings, empty messages, convocations, fundraising, academic surveys, matrimonial ads, and alumni job hunt requests.
- `ProductionLinkFetcher` implemented in `app/pipeline/linkfetch.py`:
  - Strict SSRF defense: DNS resolution check against loopback, private subnets, link-local IPs.
  - Redirect safety check.
  - Tracking parameter cleaner (strips `utm_*`, `fbclid`, `gclid`).
  - Blocks walled gardens (`linkedin.com`, `lnkd.in`) with manual review directive.
  - Clean HTML body extraction.
- `ProductionLLMProvider` implemented in `app/llm/provider.py`:
  - Google Gemini free-tier REST integration (`gemini-2.5-flash`) with multimodal poster support.
  - Groq free-tier fallback integration (`llama-3.3-70b-versatile`).
  - Quota meter, content-hash caching, rate limiting, and exponential backoff.
  - Mandatory privacy guard raising `PrivacyViolationError` if profile phone/email/CNIC appears in prompts.
- `ProductionExtractor` implemented in `app/pipeline/extract.py`:
  - Validates extraction against Pydantic models.
  - Retries once on invalid schema.
  - Multi-role parsing support.
- Unit tests written and green: `tests/extract/test_extract.py` (4 passed).
- Requirements listed in `requirements/extract.txt`.
- Env vars declared in `contracts/env/extract.yaml`.

## Interfaces Implemented
- `PreFilter` (from `contracts.protocols`)
- `LinkFetcher` (from `contracts.protocols`)
- `LLMProvider` (from `contracts.protocols`)
- `Extractor` (from `contracts.protocols`)

## Open Issues / Notes
- None. Ready for integration.
