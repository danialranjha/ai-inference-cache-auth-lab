import asyncio
import unittest
import experiment as e


class BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {(r['case'], r['method']): r for r in asyncio.run(e.run_all())}

    def pair(self, name):
        return [self.rows[name, m] for m in ('original_route', 'identity_first')]

    def test_missing_identity_returns_marker_only_without_guard(self):
        a,b=self.pair('missing_identity')
        self.assertEqual((a['status'], a['body_hex'], a['backend_calls']),
                         (200, e.MARKER.hex(), [['is_exist','demo'],['get','demo']]))
        self.assertEqual((b['status'],b['backend_calls'],b['marker_returned']),(401,[],False))

    def test_wrong_identity_rejected_before_lookup(self):
        a,b=self.pair('wrong_identity')
        self.assertTrue(a['marker_returned'])
        self.assertEqual((b['status'],b['backend_calls']),(401,[]))

    def test_proxy_header_is_not_identity(self):
        a,b=self.pair('claimed_proxy_identity')
        self.assertTrue(a['marker_returned'])
        self.assertEqual((b['status'],b['backend_calls']),(401,[]))

    def test_authenticated_twin_preserves_bytes_and_calls(self):
        a,b=self.pair('valid_identity')
        for key in ('status','body_hex','backend_calls','content_type'):
            self.assertEqual(a[key],b[key])
        self.assertEqual(b['body_hex'],e.MARKER.hex())

    def test_no_identity_does_not_probe_key_existence(self):
        a,b=self.pair('missing_key_no_identity')
        self.assertEqual((a['status'],a['backend_calls']),(404,[['is_exist','absent']]))
        self.assertEqual((b['status'],b['backend_calls']),(401,[]))

    def test_missing_key_stays_missing_for_authenticated_caller(self):
        a,b=self.pair('missing_key_valid_identity')
        self.assertEqual((a['status'],b['status']),(404,404))
        self.assertEqual(a['backend_calls'],b['backend_calls'])

    def test_empty_value_is_not_missing(self):
        a,b=self.pair('empty_value_valid_identity')
        self.assertEqual((a['status'],b['status'],b['body_hex']),(200,200,''))
        self.assertEqual(b['backend_calls'],[['is_exist','empty'],['get','empty'],['is_exist','empty']])

    def test_backend_failures_are_preserved_after_authentication(self):
        for name in ('exist_error_valid_identity','get_error_valid_identity'):
            a,b=self.pair(name)
            self.assertEqual((a['status'],b['status']),(500,500))
            self.assertEqual(a['body_hex'],b['body_hex'])
            self.assertEqual(a['backend_calls'],b['backend_calls'])

    def test_failed_identity_never_reaches_failing_backend(self):
        a,b=self.pair('exist_error_no_identity')
        self.assertEqual(a['status'],500)
        self.assertEqual((b['status'],b['backend_calls']),(401,[]))

    def test_authentication_is_not_per_key_authorization(self):
        a,b=self.pair('second_key_valid_identity')
        self.assertEqual((a['status'],b['status']),(200,200))
        self.assertEqual(b['body_hex'],b'SECOND_INVENTED_VALUE'.hex())

    def test_repeatability_and_full_denominator(self):
        repeat=asyncio.run(e.run_all())
        self.assertEqual(len(repeat),22)
        self.assertEqual(len(self.rows),22)
        self.assertEqual(repeat,list(self.rows.values()))


if __name__ == '__main__':
    unittest.main()
