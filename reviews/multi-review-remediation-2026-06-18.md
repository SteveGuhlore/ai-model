# Remediation Plan — Avatar Studio Safety & Provider Hardening

The 10 findings collapse into **4 distinct defects** across 3 files (several are duplicate reports of the same root cause at different severities). Prioritized by validated blast radius.

---

## P0 — Blocked NSFW media + audio left on disk in public `work_dir`
**Severity:** Critical (consolidates the critical pipeline finding + the two medium "blocked output" / "exception leaves artifacts" findings)

**Risk:** When the media safety gate (`pipeline.py:104`) blocks a rendered video, `handle_turn` returns a blocked `TurnResult` **without deleting `video_path` or `audio_path`**. The unsafe `.mp4` and its `.wav` remain in `work_dir` (default `"outputs"`, line 66 — a servable directory). Filenames are a 12-hex token, but anything that lists or serves the directory exposes the exact NSFW content the gate was meant to suppress. The same leak occurs if `tts.synthesize` or `head.render` raises mid-turn, leaving partial artifacts behind on the 500 path.

**Files:** `avatar_studio/pipeline.py`

**Fix:**
1. Add a private helper to best-effort remove any generated artifacts:
   ```python
   @staticmethod
   def _discard(*paths: str | None) -> None:
       for p in paths:
           if p:
               try:
                   os.remove(p)
               except OSError:
                   pass
   ```
2. In the media-gate block (lines 104–109), discard both paths **before** returning:
   ```python
   if not self.media_safety.is_sfw(video_path):
       self._discard(video_path, audio_path)
       return TurnResult(text=SAFE_FALLBACK, blocked=True,
                         block_reason="output:media_nsfw")
   ```
3. Wrap synthesis + render (lines 97–109) in `try/except`; on any exception call `self._discard(audio_path, video_path)` and re-raise, so the 500 path never leaves partial media.
4. Confirm `os` is already imported (it is, line 18) — no new import needed.

**Verification:**
```bash
python -m pytest avatar_studio/tests/ -k "pipeline and (block or media or cleanup)" -q
# Regression assertion to add: after a forced is_sfw()->False turn,
#   assert not os.path.exists(video_path) and not os.path.exists(audio_path)
```

---

## P1 — Temp-dir + file-descriptor leak on every video safety check
**Severity:** High (consolidates the high, medium, and two low `image_filter._frames` findings — all the same root cause)

**Risk:** `_frames` (`image_filter.py:48`) calls `tempfile.mkdtemp()` to hold extracted PNG frames and **never removes it**. Every video screened leaks one temp directory full of full-resolution PNGs → unbounded disk growth → disk exhaustion → the fail-closed gate eventually denies all media (DoS). Additionally, the `Image.open(...).convert("RGB")` handles (lines 46, 56) are never closed, leaking a file descriptor per frame.

**Files:** `avatar_studio/safety/image_filter.py`

**Fix:**
1. `import shutil` at the top.
2. Have `_frames` **return decoded, in-memory copies and close the on-disk handles**, then delete the temp dir in `finally`. Use `Image.open(p).copy()` (or load then close) so no handle outlives the directory:
   ```python
   tmp = tempfile.mkdtemp()
   try:
       subprocess.run([...], check=True, timeout=120,  # see P2
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
       frames = []
       for p in sorted(glob.glob(os.path.join(tmp, "*.png"))):
           with Image.open(p) as im:
               frames.append(im.convert("RGB").copy())
       return frames
   finally:
       shutil.rmtree(tmp, ignore_errors=True)
   ```
3. For the single-image branch (line 46), likewise load into memory and close: `with Image.open(media_path) as im: return [im.convert("RGB").copy()]`.
4. `is_sfw` already wraps `_frames` in `try/except` returning `False` — the `finally` guarantees cleanup even on the fail-closed path.

**Verification:**
```bash
python -m pytest avatar_studio/tests/ -k "image_filter or sfw" -q
# Leak assertion to add: capture len(os.listdir(tempfile.gettempdir())) before/after
#   is_sfw(sample.mp4); assert equal. Confirm no leftover mkdtemp dirs.
```

---

## P2 — `ffmpeg` runs with no timeout (request-worker hang DoS)
**Severity:** Medium

**Risk:** `subprocess.run([...ffmpeg...], check=True)` (`image_filter.py:49`) has **no timeout**. A malformed or pathological media file can make ffmpeg hang indefinitely, pinning a request worker forever. Repeated across uploads this exhausts the worker pool — a denial of service on the safety gate itself.

**Files:** `avatar_studio/safety/image_filter.py`

**Fix:**
1. Add an explicit timeout to the `subprocess.run` call (e.g. `timeout=120`; expose as a dataclass field such as `ffmpeg_timeout_s: int = 120` for tunability).
2. Fail **closed**: `is_sfw`'s existing `except Exception: return False` already catches `subprocess.TimeoutExpired`, but make that intent explicit so a timeout is treated as unsafe rather than swallowed. Ensure the `finally` from P1 still removes the temp dir on timeout.

**Verification:**
```bash
python -m pytest avatar_studio/tests/ -k "ffmpeg or timeout or sfw" -q
# Add a test that monkeypatches subprocess.run to raise TimeoutExpired and
#   asserts is_sfw(...) is False AND the temp dir was cleaned up.
```

---

## P3 — `FalProvider._download` SSRF + unbounded memory read
**Severity:** Low/Medium (security path — two related findings: host allowlist + size limit)

**Risk:** `_download` (`fal_provider.py:56`) fetches **any** `http(s)` URL the provider returns, with only a scheme check. A compromised or spoofed fal response can point the URL at internal endpoints (`http://169.254.169.254/…`, internal services) → **SSRF**. It also reads the full body via `resp.content` with **no size cap**, so an oversized response causes an OOM DoS. Provider responses are explicitly documented as untrusted (module docstring), so this is in scope.

**Files:** `avatar_studio/providers/fal_provider.py`

**Fix:**
1. **Host allowlist:** define the known fal media hosts/CDN (e.g. `_ALLOWED_HOSTS = {"fal.media", "v3.fal.media", "fal.run", ...}` — confirm exact set against fal's CDN docs). Parse the URL with `urllib.parse.urlparse`, lowercase the host, and reject anything whose host is not an exact match or an explicit subdomain of an allowlisted apex. Keep the scheme check; **require `https`** unless `http` is genuinely needed.
2. **Block private targets** as defense-in-depth even within allowlisted hosts: reject literal-IP hosts and resolved addresses in private/link-local/loopback ranges (`ipaddress.ip_address(...).is_private/.is_loopback/.is_link_local`).
3. **Size cap + streaming:** switch to `requests.get(url, timeout=120, stream=True)` and read in chunks up to a configurable max (e.g. `max_bytes: int = 64 * 1024 * 1024`); abort with `ValueError` once the limit is exceeded. Honor a sane `Content-Length` pre-check when present, but still enforce the cap during streaming (Content-Length is attacker-controlled).
4. Surface the cap/allowlist as dataclass fields so production can tune them without code edits.

**Verification:**
```bash
python -m pytest avatar_studio/tests/ -k "fal and (download or ssrf or size)" -q
# Tests to add:
#   - _download("http://169.254.169.254/...")  -> raises ValueError (SSRF block)
#   - _download(non-allowlisted host)          -> raises ValueError
#   - streamed body exceeding max_bytes        -> raises ValueError, no full read
```

---

## Suggested execution order
1. **P0** (critical, content-leak) — ship first.
2. **P1** (high, disk exhaustion) — same file family as P2, do together.
3. **P2** (worker-hang DoS) — fold into the P1 `image_filter.py` change set.
4. **P3** (SSRF + OOM) — independent file; can land in parallel.

**Whole-suite gate before merge:**
```bash
python -m pytest avatar_studio/tests/ -q && python -m pyflakes avatar_studio/
```