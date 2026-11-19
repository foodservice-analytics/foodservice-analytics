"""DataLens OSS 2.9 HTTP client and portable workbook importer.

Uses the authenticated UI gateway and chart API. No cluster access is required.
"""
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
import requests


class DataLensError(RuntimeError):
    pass


class DataLensHTTP:
    def __init__(self, url, login, password, session=None):
        parsed = urlsplit(url)
        if parsed.scheme not in {'https', 'http'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Provide a DataLens HTTP(S) URL without credentials or query parameters')
        if parsed.scheme == 'http' and parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('Use HTTPS for remote DataLens')
        self.url = url.rstrip('/')
        self.session = session or requests.Session()
        self.session.headers.update({'Origin': self.url, 'Referer': self.url + '/'})
        self._request('GET', '/auth/signin')
        response = self._request('POST', '/gateway/auth/auth/signin', {'login': login, 'password': password})
        if not response.get('done'):
            raise DataLensError('DataLens authentication failed')

    def _request(self, method, path, data=None):
        try:
            response = self.session.request(method, self.url + path, json=data, timeout=90, allow_redirects=False)
        except requests.RequestException:
            raise DataLensError('DataLens network request failed') from None
        if response.status_code >= 300:
            # Response bodies may contain submitted connection credentials: never echo them.
            raise DataLensError(f'DataLens {path}: HTTP {response.status_code}')
        if method == 'GET' and path == '/auth/signin':
            return {}
        try:
            return response.json()
        except ValueError:
            raise DataLensError('DataLens returned a non-JSON response') from None

    def call(self, service, action, body):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', service) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', action):
            raise ValueError('Only user-facing gateway actions are allowed')
        return self._request('POST', f'/gateway/root/{service}/{action}', body)

    def get_entry(self, entry_id):
        return self.call('us', 'getEntry', {'entryId': entry_id})

    def save_dataset(self, name, dataset, workbook_id, existing=None):
        if existing:
            current = self.call('bi', 'getDatasetByVersion', {'datasetId': existing, 'workbookId': workbook_id})
            dataset['revision_id'] = current['dataset']['revision_id']
            self.call('bi', 'updateDataset', {'datasetId': existing, 'data': {'dataset': dataset}})
            return existing
        result = self.call('bi', 'createDataset', {'name': name, 'workbook_id': workbook_id, 'dataset': dataset})
        return result['id']

    def save_chart(self, name, config, workbook_id, existing=None):
        body = {'template': 'datalens', 'data': config, 'mode': 'publish'}
        path = '/api/charts/v1/charts'
        if existing:
            if not re.fullmatch(r'[A-Za-z0-9_-]+', existing):
                raise ValueError('Invalid chart ID')
            path += '/' + existing
        else:
            body.update(name=name, workbookId=workbook_id)
        result = self._request('POST', path, body)
        return existing or result['entryId']

    def save_dashboard(self, name, data, workbook_id, existing=None):
        data = copy.deepcopy(data)
        entry = {'data': data, 'meta': {}}
        action = 'createDashboardV1'
        if existing:
            action = 'updateDashboardV1'
            entry['entryId'] = existing
        else:
            data.pop('schemeVersion', None)
            entry.update(name=name, workbookId=workbook_id)
        result = self.call('mix', action, {'entry': entry, 'mode': 'publish'})
        return result['entry']['entryId']


def resolve_refs(value, references):
    if isinstance(value, str):
        if value in references:
            return references[value]
        for key in ('__ANALYSIS_ROOT__', '__HISTORY_ROOT__'):
            value = value.replace(key, references[key])
        return value
    if isinstance(value, list):
        return [resolve_refs(item, references) for item in value]
    if isinstance(value, dict):
        return {key: resolve_refs(item, references) for key, item in value.items()}
    return value


def dataset_for_api(stored):
    """Convert the portable storage schema into the user-facing BI API schema."""
    keys = {'avatar_relations', 'description', 'load_preview_by_default', 'result_schema_aux',
            'source_avatars', 'obligatory_filters', 'template_enabled', 'result_schema'}
    result = {key: copy.deepcopy(value) for key, value in stored.items() if key in keys}
    result['sources'] = []
    for collection in stored['source_collections']:
        origin = collection['origin']
        columns = copy.deepcopy(origin['raw_schema'])
        for column in columns:
            column['user_type'] = column.pop('type')
        result['sources'].append({
            'id': collection['id'], 'title': collection['title'], 'managed_by': 'user',
            'source_type': origin['created_from'], 'connection_id': origin['connection_id'],
            'parameters': copy.deepcopy(origin['parameters']), 'raw_schema': columns,
        })
    return result


def check_spec(spec):
    if spec.get('schema_version') != 1:
        raise ValueError('Unsupported portable specification version')
    datasets = spec['dataset_definitions']
    charts = spec['chart_definitions']
    assert len(datasets) == 9 and len(charts) == 13 and len(spec['dashboard']['data']['tabs']) == 5
    for dataset in datasets.values():
        titles = {field['title'] for field in dataset['data']['result_schema']}
        for field in dataset['data']['result_schema']:
            if field.get('calc_mode') == 'formula':
                assert all(name in titles for name in re.findall(r'\[([^\]]+)\]', field['formula']))
    def walk(value):
        if isinstance(value, str):
            if value.startswith('dataset:'):
                assert value[8:] in datasets
            if value.startswith('chart:'):
                assert value[6:] in charts
        elif isinstance(value, (dict, list)):
            for item in value.values() if isinstance(value, dict) else value:
                walk(item)
    walk(spec)
    ids = []
    for tab in spec['dashboard']['data']['tabs']:
        ids.append(tab['id'])
        for item in tab['items']:
            ids.append(item['id'])
            if item['type'] == 'widget':
                ids.extend(view['id'] for view in item['data']['tabs'])
    if len(ids) != len(set(ids)):
        raise ValueError('Dashboard tab/widget IDs must be globally unique')
    if re.search(r'ytct-[A-Za-z0-9-]{12,}|-----BEGIN .*PRIVATE KEY-----', json.dumps(spec)):
        raise ValueError('Credential material in portable specification')
    return {'datasets': len(datasets), 'views': len(charts), 'tabs': 5}


class WorkbookImporter:
    def __init__(self, api, spec, state_file, analysis_root, history_root):
        self.api = api
        self.spec = spec
        check_spec(spec)
        self.state_file = Path(state_file)
        self.state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {}
        if self.state and self.state.get('url') != api.url:
            raise ValueError('State belongs to another DataLens URL; use a separate state file')
        self.state['url'] = api.url
        self.refs = {'__ANALYSIS_ROOT__': analysis_root, '__HISTORY_ROOT__': history_root}
        for root in (analysis_root, history_root):
            if not re.fullmatch(r'//home/team/foodservice_analytics/[A-Za-z0-9_-]+', root):
                raise ValueError('Expected an immutable published YT run root')
        self.backup = self.state_file.parent / 'backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    def save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.state_file.with_suffix('.tmp'), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(self.state, stream, ensure_ascii=False, indent=2)
        self.state_file.with_suffix('.tmp').replace(self.state_file)

    def bind(self, title, workbook_id=None, connection_id=None, yt_token=None, proxy='yt-api.xsserver.ru', alias='*ch_public'):
        for key, supplied in [('workbook_id', workbook_id), ('connection_id', connection_id)]:
            if supplied and self.state.get(key) and self.state[key] != supplied:
                raise ValueError(f'{key} differs from saved state; use another state file')
            if supplied:
                self.state[key] = supplied
        if not self.state.get('connection_id') and not yt_token:
            raise ValueError('Set YT_TOKEN or provide an existing CHYT connection ID')
        if not self.state.get('workbook_id') and self.state.get('connection_id'):
            raise ValueError('Provide the workbook ID together with the connection ID')
        if not self.state.get('workbook_id'):
            self.state['workbook_id'] = self.api.call('us', 'createWorkbook', {'title': title})['workbookId']
            self.save_state()
        self.api.call('us', 'getWorkbook', {'workbookId': self.state['workbook_id']})
        if not self.state.get('connection_id'):
            if not yt_token:
                raise ValueError('Set YT_TOKEN or provide an existing CHYT connection ID')
            host = urlsplit(proxy if '://' in proxy else 'https://' + proxy).hostname
            result = self.api.call('bi', 'createConnection', {
                'type': 'chyt', 'name': 'YTsaurus CHYT — общепит', 'workbook_id': self.state['workbook_id'],
                'host': host, 'port': 443, 'secure': True, 'alias': alias, 'token': yt_token,
                'raw_sql_level': 'off', 'cache_ttl_sec': 300,
            })
            self.state['connection_id'] = result['id']
            self.save_state()
        connection = self.api.call('bi', 'getConnection', {'connectionId': self.state['connection_id'], 'workbookId': self.state['workbook_id']})
        if connection.get('workbook_id') != self.state['workbook_id'] or connection.get('db_type') != 'chyt':
            raise ValueError('The connection must be CHYT and belong to this workbook')
        self.refs['__CONNECTION__'] = self.state['connection_id']
        self.save_state()

    def _backup_existing(self, entry_id):
        entry = self.api.get_entry(entry_id)
        if entry.get('workbookId') != self.state['workbook_id']:
            raise ValueError('Refusing to update an entry from another workbook')
        self.backup.mkdir(parents=True, exist_ok=True)
        (self.backup / (entry_id + '.json')).write_text(json.dumps(entry, ensure_ascii=False, indent=2))

    def import_all(self, update=False):
        if not update and any(self.state.get(key) and self.state[key] != self.refs[ref] for key, ref in [('analysis_root', '__ANALYSIS_ROOT__'), ('history_root', '__HISTORY_ROOT__')]):
            raise ValueError('Published run roots changed; pass --update to refresh existing objects')
        book = self.state['workbook_id']
        for kind, definitions, prefix in [('datasets', 'dataset_definitions', 'dataset:'), ('charts', 'chart_definitions', 'chart:')]:
            saved = self.state.setdefault(kind, {})
            for key, definition in self.spec[definitions].items():
                existing = saved.get(key)
                if not existing or update:
                    if existing:
                        self._backup_existing(existing)
                    data = resolve_refs(definition['data'], self.refs)
                    if kind == 'datasets':
                        entry_id = self.api.save_dataset(definition['name'], dataset_for_api(data), book, existing)
                    else:
                        entry_id = self.api.save_chart(definition['name'], data['shared_config'], book, existing)
                    saved[key] = entry_id
                    self.save_state()
                self.refs[prefix + key] = saved[key]
        existing = self.state.get('dashboard_id')
        if not existing or update:
            if existing:
                self._backup_existing(existing)
            self.state['dashboard_id'] = self.api.save_dashboard(
                self.spec['dashboard']['name'], resolve_refs(self.spec['dashboard']['data'], self.refs), book, existing)
        self.state['analysis_root'] = self.refs['__ANALYSIS_ROOT__']
        self.state['history_root'] = self.refs['__HISTORY_ROOT__']
        self.save_state()
        return self.api.url + '/' + self.state['dashboard_id']

    def verify(self):
        dataset_ids = set(self.state['datasets'].values())
        chart_ids = set(self.state['charts'].values())
        if len(dataset_ids) != 9 or len(chart_ids) != 13:
            raise ValueError('Unexpected number of saved objects')
        for entry_id in dataset_ids:
            entry = self.api.get_entry(entry_id)
            if entry.get('workbookId') != self.state['workbook_id']:
                raise ValueError('Dataset belongs to another workbook')
            for source in entry['data']['source_collections']:
                origin = source['origin']
                if origin['connection_id'] != self.state['connection_id'] or not any(origin['parameters']['table_name'].startswith(root + '/') for root in (self.refs['__ANALYSIS_ROOT__'], self.refs['__HISTORY_ROOT__'])):
                    raise ValueError('Dataset points to unexpected data')
        for entry_id in chart_ids:
            shared = json.loads(self.api.get_entry(entry_id)['data']['shared'])
            if shared['datasetsIds'][0] not in dataset_ids:
                raise ValueError('Chart points to an unknown dataset')
        dashboard = self.api.get_entry(self.state['dashboard_id'])
        tabs = dashboard['data']['tabs']
        widgets = [view['chartId'] for tab in tabs for item in tab['items'] if item['type'] == 'widget' for view in item['data']['tabs']]
        if len(tabs) != 5 or len(widgets) != 13 or set(widgets) != chart_ids:
            raise ValueError('Dashboard references are inconsistent')
        return {'status': 'passed', 'datasets': 9, 'views': 13, 'tabs': 5}
