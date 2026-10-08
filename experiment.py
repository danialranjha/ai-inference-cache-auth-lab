"""In-process aiohttp read-route assay. No listener, native store, or model."""
import asyncio
import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import aiohttp
from aiohttp import web
from aiohttp.test_utils import make_mocked_request
from upstream_get import handle_get

# Public fixture text, deliberately not a secret or deployable credential.
FIXTURE_AUTH = 'Bearer PUBLIC-LAB-FIXTURE'
MARKER = b'INVENTED_CACHE_BYTES'


class RecordedStore:
    def __init__(self, values, fault=None):
        self.values = dict(values)
        self.fault = fault
        self.calls = []

    def is_exist(self, key):
        self.calls.append(['is_exist', key])
        if self.fault == 'exist_error':
            return -1
        if self.fault == 'exception':
            raise RuntimeError('synthetic backend failure')
        return int(key in self.values)

    def get(self, key):
        self.calls.append(['get', key])
        if self.fault == 'get_error':
            return None
        return self.values[key]


@web.middleware
async def require_fixture_identity(request, handler):
    if request.headers.get('Authorization') != FIXTURE_AUTH:
        return web.Response(status=401, text='fixture identity required')
    return await handler(request)


@dataclass(frozen=True)
class Case:
    name: str
    key: str = 'demo'
    auth: str | None = None
    fault: str | None = None
    proxy_claim: bool = False


CASES = (
    Case('missing_identity'),
    Case('wrong_identity', auth='Bearer WRONG-PUBLIC-FIXTURE'),
    Case('valid_identity', auth=FIXTURE_AUTH),
    Case('claimed_proxy_identity', proxy_claim=True),
    Case('missing_key_no_identity', key='absent'),
    Case('missing_key_valid_identity', key='absent', auth=FIXTURE_AUTH),
    Case('empty_value_valid_identity', key='empty', auth=FIXTURE_AUTH),
    Case('exist_error_no_identity', fault='exist_error'),
    Case('exist_error_valid_identity', auth=FIXTURE_AUTH, fault='exist_error'),
    Case('get_error_valid_identity', auth=FIXTURE_AUTH, fault='get_error'),
    Case('second_key_valid_identity', key='other', auth=FIXTURE_AUTH),
)


async def run_case(case, guarded, mutation=None):
    store = RecordedStore({'demo': MARKER, 'empty': b'', 'other': b'SECOND_INVENTED_VALUE'}, case.fault)
    service = SimpleNamespace(store=store)

    async def route(request):
        return await handle_get(service, request)

    @web.middleware
    async def deny_all(request, handler):
        return web.Response(status=401, text='fixture identity required')

    middlewares = [require_fixture_identity] if guarded else []
    if guarded and mutation == 'bypass':
        middlewares = []
    if guarded and mutation == 'deny_all':
        middlewares = [deny_all]
    app = web.Application(middlewares=middlewares)
    app.router.add_get('/api/get/{key}', route)
    app.freeze()
    headers = {} if case.auth is None else {'Authorization': case.auth}
    if case.proxy_claim:
        headers['X-User'] = 'trusted-looking-fixture'
    request = make_mocked_request('GET', '/api/get/' + case.key, headers=headers, app=app)
    # _handle drives the real aiohttp router and middleware, without opening a socket.
    response = await app._handle(request)
    body = bytes(response.body or b'')
    return {'case': case.name, 'method': 'identity_first' if guarded else 'original_route',
            'status': response.status, 'content_type': response.content_type,
            'body_hex': body.hex(), 'backend_calls': store.calls,
            'marker_returned': MARKER in body}


def forbid_network(*args, **kwargs):
    raise AssertionError('Network use is outside the experiment')


async def run_all(mutation=None):
    rows = []
    with patch('socket.socket', side_effect=forbid_network), patch('socket.getaddrinfo', side_effect=forbid_network):
        for case in CASES:
            for guarded in (False, True):
                rows.append(await run_case(case, guarded, mutation))
    return rows


def main():
    rows = asyncio.run(run_all())
    here = Path(__file__).parent
    result = {'scope': 'fixed in-process aiohttp route tests; dictionary backend; no network/native store/model',
              'python': platform.python_version(), 'aiohttp': aiohttp.__version__,
              'cases': len(CASES), 'method_rows': len(rows), 'rows': rows,
              'source_excerpt_sha256': hashlib.sha256((here/'upstream_get.py').read_bytes()).hexdigest()}
    (here/'artifacts/run.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    lines = ['# Read-route evidence', '',
             'Fixed in-process requests to the real aiohttp router with an extracted Mooncake handler and recorded dictionary backend. No socket, native cache or model ran.', '',
             f'{len(CASES)} deliberately selected fixtures × 2 methods = {len(rows)} rows. These are not attack-rate estimates.', '',
             '| Case | Original status / backend calls | Identity-first status / backend calls |',
             '|---|---|---|']
    for i in range(0, len(rows), 2):
        a,b=rows[i:i+2]
        lines.append(f"| {a['case']} | {a['status']} / {len(a['backend_calls'])} | {b['status']} / {len(b['backend_calls'])} |")
    lines += ['', '## Exact witness', '',
              'Missing identity, key demo: original calls is_exist(demo), get(demo), then returns200 with INVENTED_CACHE_BYTES. Identity-first returns401 with no backend call. Same key with valid fixture identity returns the identical bytes under both methods.', '',
              'The intervention refuses the request. It does not substitute another key or execute an approved replacement.', '',
              '## Boundary limit', '',
              'A valid fixture identity can read the second key under both methods. Authentication alone does not establish per-key or tenant authorization. Empty values remain200; absent keys remain404 and backend failures500 for authenticated callers. The unmodified startup code was inspected separately; this harness never invokes it or tests network reachability.', '']
    (here/'evidence.md').write_text('\n'.join(lines))
    print(f'Wrote {len(rows)} method rows across {len(CASES)} fixtures')


if __name__ == '__main__':
    main()
