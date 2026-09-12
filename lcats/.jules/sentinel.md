## 2026-08-24 - SSRF / Local File Read in urlopen
**Vulnerability:** `urllib.request.urlopen` used in `download_raw_text` was not validating URL schemes, allowing arbitrary schemes like `file://` which can lead to Local File Read or SSRF.
**Learning:** `urlopen` handles `file://` scheme out-of-the-box, introducing risks if URLs are user-influenced.
**Prevention:** Always validate URL schemes before passing them to URL loaders like `urlopen` to restrict to safe protocols (e.g., `http://` or `https://`).
