"""Early process configuration only. Never call after constructing Quick windows."""
import os
import sys


def configure_quick_graphics(backend=None, *, environ=None, platform=None):
    env = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    selected = backend if backend is not None else env.get('FILEWHEEL_UI_BACKEND', 'widgets')
    if platform != 'win32' or selected != 'quick':
        return 'unchanged'
    # Presence, including an empty value, is an explicit user choice. Preserve
    # legacy scenegraph selection and Qt software/OpenGL diagnostic controls too.
    overrides = ('QSG_RHI_BACKEND', 'QT_QUICK_BACKEND', 'QMLSCENE_DEVICE',
                 'QT_OPENGL', 'QSG_RHI_PREFER_SOFTWARE_RENDERER')
    if any(key in env for key in overrides):
        return 'explicit'
    if env.get('FILEWHEEL_QUICK_RHI') == 'default':
        return 'qt-default'
    env['QSG_RHI_BACKEND'] = 'opengl'
    return 'preferred-opengl'
