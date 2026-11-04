## 2024-05-24 - Tiktoken O(N^2) Chunking Bottleneck
**Learning:** In `lcats/chunking.py`, calculating the character offset of chunks using `len(enc.decode(tokens[:start_token]))` is an O(N^2) operation because it repeatedly decodes increasing prefixes of the entire story. For a 100,000 token text, this takes around 60 seconds.
**Action:** Use piecemeal decoding by accumulating the decoded bytes with `enc.decode_bytes()` (since tokens might span characters, making piecemeal string decoding unsafe) or by keeping a running string of `enc.decode_bytes(chunk).decode("utf-8", errors="replace")`. This drops the time to ~6 seconds, making chunking O(N) instead of O(N^2).

## 2024-06-15 - Tiktoken encoding initialization is slow
**Learning:** `tiktoken.encoding_for_model` and `tiktoken.get_encoding` take significant time to initialize (e.g. ~240ms for 10000 calls vs ~1ms when cached). Repeatedly calling them in utility functions (like `count_tokens`) adds up quickly and becomes a bottleneck.
**Action:** Use `functools.lru_cache` to cache the encoding instance. Since `tiktoken.Encoding` instances are thread-safe and stateless, they are safe to cache. Remember to clear the cache in tests to maintain isolation when patching.
