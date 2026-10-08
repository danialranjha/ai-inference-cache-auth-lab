# Read-route evidence

Fixed in-process requests to the real aiohttp router with an extracted Mooncake handler and recorded dictionary backend. No socket, native cache or model ran.

11 deliberately selected fixtures × 2 methods = 22 rows. These are not attack-rate estimates.

| Case | Original status / backend calls | Identity-first status / backend calls |
|---|---|---|
| missing_identity | 200 / 2 | 401 / 0 |
| wrong_identity | 200 / 2 | 401 / 0 |
| valid_identity | 200 / 2 | 200 / 2 |
| claimed_proxy_identity | 200 / 2 | 401 / 0 |
| missing_key_no_identity | 404 / 1 | 401 / 0 |
| missing_key_valid_identity | 404 / 1 | 404 / 1 |
| empty_value_valid_identity | 200 / 3 | 200 / 3 |
| exist_error_no_identity | 500 / 1 | 401 / 0 |
| exist_error_valid_identity | 500 / 1 | 500 / 1 |
| get_error_valid_identity | 500 / 2 | 500 / 2 |
| second_key_valid_identity | 200 / 2 | 200 / 2 |

## Exact witness

Missing identity, key demo: original calls is_exist(demo), get(demo), then returns200 with INVENTED_CACHE_BYTES. Identity-first returns401 with no backend call. Same key with valid fixture identity returns the identical bytes under both methods.

The intervention refuses the request. It does not substitute another key or execute an approved replacement.

## Boundary limit

A valid fixture identity can read the second key under both methods. Authentication alone does not establish per-key or tenant authorization. Empty values remain200; absent keys remain404 and backend failures500 for authenticated callers. The unmodified startup code was inspected separately; this harness never invokes it or tests network reachability.
