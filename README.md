# Elon Rotation Bot

## Run modes

The CLI supports a couple of runtime modes useful for testing or offline runs:

- `--no-network`
	- Do not attempt any network requests. Elon will return sensible defaults and use any cached indicators if present.
- `--cache-ttl <seconds>`
	- When fetching indicators the loader will use a file-backed TTL cache located at `state/indicators_cache.json`.
	- Set the cache TTL in seconds to force a re-fetch only when data is older than the TTL. The default is 120 seconds.

Example: run a dry-run using only cached data (or defaults) for reproducible results:

```bash
python3 main.py --dry-run --no-network --cache-ttl 0
```
