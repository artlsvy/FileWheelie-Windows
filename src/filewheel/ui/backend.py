"""Startup-only renderer choice; default and load-failure fallback stay QWidget."""
import os

from filewheel.converters.debugging import record_failure


def create_popup(registry, *, backend=None, **options):
    selected = backend if backend is not None else os.getenv('FILEWHEEL_UI_BACKEND', 'widgets')
    if selected not in ('widgets', 'quick'):
        record_failure('ui', 'select_backend', ValueError('Unknown renderer; using widgets'))
        selected = 'widgets'
    if selected == 'quick':
        try:
            from filewheel.ui.quick_popup import GlassPopup
            return GlassPopup(registry, **options)
        except (ImportError, RuntimeError, OSError) as error:
            # Constructor explicitly deletes a failed Quick view before raising.
            # Native driver fatal errors cannot be recovered by Python; the
            # widgets startup choice remains available on the next launch.
            record_failure('quick', 'create_popup', error)
    from filewheel.ui.popup import RadialPopup
    return RadialPopup(registry, **options)
