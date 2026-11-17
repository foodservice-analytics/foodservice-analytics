"""Contracts and credential protections for the user-facing DataLens HTTP adapter."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from src.datalens import DataLensError, DataLensHTTP, WorkbookImporter, check_spec, dataset_for_api, resolve_refs

ROOT = Path(__file__).resolve().parents[1]


class DataLensTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT/'bi/datalens/workbook/dashboard_spec.json').read_text())

    def test_schema_conversion_preserves_source_identity_and_is_not_storage_schema(self):
        original = self.spec['dataset_definitions']['structure']['data']
        before = copy.deepcopy(original)
        converted = dataset_for_api(original)
        self.assertEqual(original, before)
        self.assertNotIn('revision_id', converted)
        self.assertNotIn('source_collections', converted)
        self.assertEqual(converted['sources'][0]['id'], original['source_collections'][0]['id'])
        self.assertEqual(converted['source_avatars'][0]['source_id'], converted['sources'][0]['id'])
        self.assertIn('user_type', converted['sources'][0]['raw_schema'][0])

    def test_spec_cannot_use_same_id_for_a_tab_and_widget(self):
        self.assertEqual(check_spec(self.spec)['views'], 13)
        self.spec['dashboard']['data']['tabs'][0]['items'][0]['id'] = 'structure'
        with self.assertRaisesRegex(ValueError, 'globally unique'):
            check_spec(self.spec)

    def test_private_gateway_actions_are_not_called(self):
        api = DataLensHTTP.__new__(DataLensHTTP)
        api._request = Mock()
        with self.assertRaises(ValueError):
            api.call('us', '_createEntry', {})
        api._request.assert_not_called()

    def test_http_errors_do_not_echo_server_body_or_submitted_secrets(self):
        api = DataLensHTTP.__new__(DataLensHTTP)
        api.url = 'https://example.org'
        api.session = Mock()
        response = Mock(status_code=400, text='submitted password: do-not-echo')
        api.session.request.return_value = response
        with self.assertRaises(DataLensError) as caught:
            api._request('POST', '/gateway/root/bi/createConnection', {'token': 'do-not-echo'})
        self.assertNotIn('do-not-echo', str(caught.exception))
        self.assertFalse(api.session.request.call_args.kwargs['allow_redirects'])

    def test_saved_state_cannot_be_reused_for_another_server(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)/'state.json'
            state.write_text(json.dumps({'url': 'https://old.example.org'}))
            api = Mock(url='https://new.example.org')
            with self.assertRaisesRegex(ValueError, 'another DataLens'):
                WorkbookImporter(api, self.spec, state, '//home/team/foodservice_analytics/a', '//home/team/foodservice_analytics/b')
            api.call.assert_not_called()

    def test_ref_resolution_does_not_modify_original_configuration(self):
        value = {'sources': ['__ANALYSIS_ROOT__/table', 'dataset:one']}
        refs = {'__ANALYSIS_ROOT__': '//home/team/foodservice_analytics/a', '__HISTORY_ROOT__': '//home/team/foodservice_analytics/b', 'dataset:one': 'created-id'}
        self.assertEqual(resolve_refs(value, refs)['sources'], ['//home/team/foodservice_analytics/a/table', 'created-id'])
        self.assertEqual(value['sources'][1], 'dataset:one')
