from unittest.mock import MagicMock

import pytest
from django.test import Client

from proj.admin_mixins import SuperuserEditMixin


class _Base:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class _Admin(SuperuserEditMixin, _Base):
    pass


def _req(is_superuser):
    req = MagicMock()
    req.user.is_superuser = is_superuser
    return req


def test_superuser_has_add_permission():
    assert _Admin().has_add_permission(_req(True)) is True


def test_superuser_has_change_permission():
    assert _Admin().has_change_permission(_req(True)) is True


def test_superuser_has_delete_permission():
    assert _Admin().has_delete_permission(_req(True)) is True


def test_non_superuser_fallback_to_base_add():
    assert _Admin().has_add_permission(_req(False)) is False


def test_non_superuser_fallback_to_base_change():
    assert _Admin().has_change_permission(_req(False)) is False


def test_non_superuser_fallback_to_base_delete():
    assert _Admin().has_delete_permission(_req(False)) is False


# --- Health checks (k8s probes) ---

def test_healthz_returns_ok():
    r = Client().get('/healthz/')
    assert r.status_code == 200
    assert r.content == b'ok'


def test_healthz_works_without_trailing_slash():
    r = Client().get('/healthz')
    assert r.status_code == 200


def test_healthz_ignores_allowed_hosts(settings):
    settings.ALLOWED_HOSTS = ['example.com']
    r = Client(HTTP_HOST='unknown-pod-ip').get('/healthz/')
    assert r.status_code == 200


@pytest.mark.django_db
def test_readyz_ok_when_deps_up():
    r = Client().get('/readyz/')
    assert r.status_code == 200
    assert r.json() == {'database': 'ok', 'cache': 'ok'}


def test_readyz_returns_503_when_db_down(monkeypatch):
    from proj import health

    def boom(*args, **kwargs):
        raise Exception('db gone')

    monkeypatch.setattr(health.connection, 'cursor', boom)
    r = Client().get('/readyz/')
    assert r.status_code == 503
    assert r.json()['database'].startswith('error:')


def test_readyz_ignores_allowed_hosts(settings):
    settings.ALLOWED_HOSTS = ['example.com']
    r = Client(HTTP_HOST='unknown-pod-ip').get('/readyz')
    assert r.status_code in (200, 503)
