# Inference cache read authentication lab

An in-process reproduction of the read boundary in a pinned Mooncake Store REST handler, followed by a proposed authentication middleware comparison. The original handler returns invented cache bytes without an identity check. The proposed middleware refuses missing or wrong fixture credentials before any backend lookup while preserving the valid-credential read.

These are fixed in-process read-route tests with a recorded dictionary backend, not network or model results. No Mooncake native store, listener, real credential, private prompt, external target or AI model is used.

## Hypothesis and threat model

Assume a caller can reach the read route and knows a key. The caller controls headers and the key. Application code, middleware and backend remain trusted. Test whether an identity check placed before routing to the read handler prevents unauthenticated backend access while retaining legitimate reads. Network reachability is an assumption, not a result.

Control: the exact upstream handle_get method with aiohttp route registration and an inert recorded store. Intervention: the same route and method, with one proposed middleware that requires the public fixture Authorization value. This value is deliberately public, not a secret and not a production credential design. No upstream fix is claimed.

## Setup and exact commands

Recorded runtime: Python3.11.6 and aiohttp3.9.1. Use Python3.11 for the recorded dependency; this is a reproducibility pin, not a recommendation for a production deployment. The test uses aiohttp's private in-process application handler and may need adaptation for other versions.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python experiment.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python run_checks.py
```

Package installation is setup only. Experiment/test commands use no network, with socket creation and DNS resolution patched to fail during fixture execution. Run from this repository root. No services or credentials need configuration.

## Results

11 selected fixtures ×2 methods =22 recorded rows. [Full JSON](artifacts/run.json) and [exact case table](evidence.md) include status, response bytes in hex, content type and ordered backend calls.

| Same synthetic key | Original route | Identity first |
|---|---|---|
| No credential |200, invented bytes; is_exist then get |401, no backend call |
| Valid fixture credential |200, same invented bytes |200, same invented bytes |
| Wrong credential |200, invented bytes |401, no backend call |
| Claimed proxy identity without credential |200, invented bytes |401, no backend call |

All5 missing/wrong-identity cases produce401 and zero backend calls under the intervention, including nonexistent-key and failing-backend cases. All6 valid-identity cases preserve original statuses, bytes and backend calls. A missing key stays404; an empty value stays200; simulated backend failures stay500. These are counts of designed fixtures, not estimated attack or defense success rates.

11 tests pass. Two deliberate faults are caught by the same suite: bypassing middleware produces5 assertion failures; refusing every request produces5. Both produce0 test errors. See [checks.json](artifacts/checks.json).

## Technical walkthrough

The [pinned upstream file](https://github.com/kvcache-ai/Mooncake/blob/dcddb56c0cddc96f41eeb8dd82e5bd9f497183a2/mooncake-wheel/mooncake/mooncake_store_service.py) creates the application without authentication middleware at line241, registers the read route at266 and binds its original server at279. That startup code was read but is not included or executed here. No listening socket is opened.

[upstream_get.py](upstream_get.py) contains the exact method from lines731–780, unindented into a standalone function with imports. [provenance.json](provenance.json) records the original Git blob, complete-file byte count and extraction boundaries. The complete upstream file was verified against blob b5bc66b2de32ecf127c7c69cf82d074a6e98c098 before extraction.

The handler checks key existence, reads its value and returns binary bytes. It does not inspect identity. The harness registers only this read route and supplies aiohttp mocked requests through the real router/middleware path. Its replacement store is a dictionary that records is_exist/get calls. This replacement makes access observable without native storage or real data; it does not simulate decoding actual KV tensors.

The proposed middleware checks the fixture Authorization value before calling the handler. On rejection it returns401 immediately. This is a refusal, not execution of another approved request. X-User alone is intentionally ignored. The known-good twin demonstrates that the result is not simply caused by disabling all reads.

The same valid fixture identity can read a second invented key. Therefore the middleware comparison establishes no per-key or tenant authorization. It also does not test credential secrecy, signature validation, transport encryption, expiry, rotation, revocation, proxy configuration, or all routes. Those require separately specified controls and tests.

## Sources and limits

[CVE-2026-106037](https://nvd.nist.gov/vuln/detail/cve-2026-106037) describes missing authentication in Mooncake Store REST through0.3.13.post1. At review time the page shows CNA CVSS4 score9.3 and no NVD assessment. No fixed release is asserted. The examined source is commit dcddb56c0cddc96f41eeb8dd82e5bd9f497183a2; this is a source-component assay, not verification of every binary release listed in the advisory.

The advisory's broader read/write/mount claims are not all reproduced here. Returning invented bytes does not prove recovery of user prompts, model-output manipulation or cache poisoning. No live agent susceptibility, network exposure, production mitigation or broad isolation guarantee follows from this test. Authentication protects this route only when the trusted check itself and the route coverage are correct.

For a cache deployed behind an AI service, require authenticated callers at the cache boundary before any lookup, then separately specify which keys each identity may access. Regression tests should observe backend touches as well as response status, and include both refused and authorized reads.

## Contents and license

Only code, configuration, tests, reproducible run evidence and technical documentation are included. Upstream excerpt attribution is in [NOTICE](NOTICE); Apache2.0 terms are in [LICENSE-APACHE](LICENSE-APACHE). Other lab files are original and distributed under the same terms.
