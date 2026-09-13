# RelayDesk LLM Providers

RelayDesk keeps provider-specific SDK code behind a single application interface.

## Why this exists

The portfolio must demonstrate:

- a completely free local path through Ollama
- compatibility with cloud providers when API credentials are available
- business logic that does not depend directly on one vendor
- normalized failure handling

## Contract

All providers implement `LLMProvider.generate_structured(...)` from `base.py`.

Inputs:

- `system_prompt`
- `user_prompt`
- requested Pydantic `response_model`

Output:

- a validated instance of the requested Pydantic model

The provider implementation is responsible for converting vendor output into the requested schema. Application services should never parse arbitrary vendor response objects.

## Planned Providers

### Ollama

Primary zero-cost development provider.

Expected environment:

```text
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:7b
OLLAMA_BASE_URL=http://localhost:11434
```

### OpenAI-compatible

Optional cloud implementation. API credentials are required only when selected.

### Anthropic

Optional cloud implementation.

### Gemini

Optional cloud implementation.

## Failure Normalization

Vendor exceptions should map to:

- `ProviderUnavailableError`
- `ProviderTimeoutError`
- `ProviderOutputError`

This allows the workflow to use the same retry/fallback logic regardless of provider.

## Factory

The next backend implementation step will add a provider factory that selects the concrete adapter from configuration without exposing vendor logic to classification or drafting services.
