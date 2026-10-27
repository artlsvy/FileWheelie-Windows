import pytest

from filewheel.ui.graphics_config import configure_quick_graphics


def test_windows_quick_prefers_opengl_early():
    env = {}
    assert configure_quick_graphics('quick', environ=env, platform='win32') == 'preferred-opengl'
    assert env == {'QSG_RHI_BACKEND': 'opengl'}
    assert configure_quick_graphics('quick', environ=env, platform='win32') == 'explicit'


@pytest.mark.parametrize('key,value', [
    ('QSG_RHI_BACKEND', 'd3d11'), ('QSG_RHI_BACKEND', ''),
    ('QT_QUICK_BACKEND', 'software'), ('QMLSCENE_DEVICE', 'software'),
    ('QT_OPENGL', 'software'), ('QSG_RHI_PREFER_SOFTWARE_RENDERER', '1')])
def test_explicit_qt_controls_are_never_overwritten(key, value):
    env = {key: value}
    before = dict(env)
    assert configure_quick_graphics('quick', environ=env, platform='win32') == 'explicit'
    assert env == before


def test_diagnostic_default_and_nonquick_platforms():
    for backend, platform, env in [('widgets', 'win32', {}), ('quick', 'linux', {}),
                                   ('quick', 'win32', {'FILEWHEEL_QUICK_RHI': 'default'})]:
        before = dict(env)
        configure_quick_graphics(backend, environ=env, platform=platform)
        assert env == before
    env = {'FILEWHEEL_UI_BACKEND': 'quick'}
    configure_quick_graphics(environ=env, platform='win32')
    assert env['QSG_RHI_BACKEND'] == 'opengl'
