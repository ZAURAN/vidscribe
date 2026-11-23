# ADR-0012: Scribe requests follow no redirects, and the key is checked before sending

## Status
Accepted

## Date
2026-11-23

## Context
The `scribe` engine sends the user's audio and the ElevenLabs key to the API in one POST. The key travels in a request header and each request is paid. Python's default HTTP client follows redirects and would carry the headers and the body to whatever address the answer names. There is no reason for the speech-to-text API to redirect, so a redirect would only mean something unexpected is happening, and by then the key and the audio would already have gone to a host the user did not choose. Handing the user's media and key to a different host is the harm [ADR-0010](0010-cross-platform-engines.md) says the cloud must never do silently.

## Decision
- A redirect from the API is not followed. It is reported as an error and the run stops with exit code 1.
- The key is checked before anything is sent: a key with characters outside the printable ASCII range is rejected with an error, and no request is made. The key's value is not printed in that error.
- Both build on [ADR-0010](0010-cross-platform-engines.md): no automatic retries, and the key is never requested, printed or written.

## Alternatives considered
- **Let the default client follow redirects.** Rejected: Python's `urllib` re-sends the request to whatever host the 301/302/303 answer names, as a GET without the body but with the `xi-api-key` header, so the key would leave for a host the answer chooses (checked with two local servers in `tests/test_scribe.py`).
- **Follow redirects only to the same host.** Rejected: the API has no legitimate redirect to support, so this adds a rule to maintain and still leaves the redirected request paid and unseen.
- **Send the key as is and let the server reject a malformed one.** Rejected: the audio would be uploaded and the user would wait for an error a local check gives at once; a key with stray characters (for example a pasted newline) is a common mistake and the server's answer does not tell the user what was wrong with it.

## Consequences
- If ElevenLabs ever redirects its endpoint, scribe stops working until the endpoint in the code is updated; that is the intended failure.
- A bad key fails in the first moment, with no upload and no cost.
- The test seam is the opener's `open` call, not `urlopen` alone, because the request goes through a custom opener.
