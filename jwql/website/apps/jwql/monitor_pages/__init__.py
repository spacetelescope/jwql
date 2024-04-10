import os

from .monitor_cosmic_rays_bokeh import CosmicRayMonitor


from jwql.utils.constants import ON_GITHUB_ACTIONS, ON_READTHEDOCS

if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    # Need to set up django apps before we can access the models
    import django  # noqa: E402 (module level import not at top of file)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    django.setup()
    from jwql.website.apps.jwql.monitor_models.edb import MIRIEdbBlockMeansStats, NIRCamEdbBlockMeansStats
