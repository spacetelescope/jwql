import os

from .monitor_cosmic_rays_bokeh import CosmicRayMonitor

from jwql.utils.constants import ON_GITHUB_ACTIONS, ON_READTHEDOCS

if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    # Need to set up django apps before we can access the models
    import django  # noqa: E402 (module level import not at top of file)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    django.setup()
    from jwql.website.apps.jwql.monitor_models.bad_pixel import FGSBadPixelQueryHistory, FGSBadPixelStats, MIRIBadPixelQueryHistory, MIRIBadPixelStats
    from jwql.website.apps.jwql.monitor_models.bad_pixel import NIRCamBadPixelQueryHistory, NIRCamBadPixelStats, NIRISSBadPixelQueryHistory, NIRISSBadPixelStats
    from jwql.website.apps.jwql.monitor_models.bad_pixel import NIRSpecBadPixelQueryHistory, NIRSpecBadPixelStats

    from jwql.website.apps.jwql.monitor_models.bias import NIRCamBiasQueryHistory

    from jwql.website.apps.jwql.monitor_models.claw import NIRCamClawQueryHistory, NIRCamClawStats

    from jwql.website.apps.jwql.monitor_models.common import Monitor

    from jwql.website.apps.jwql.monitor_models.cosmic_ray import FGSCosmicRayQueryHistory

    from jwql.website.apps.jwql.monitor_models.dark_current import FGSDarkDarkCurrent, FGSDarkPixelStats, FGSDarkQueryHistory
    from jwql.website.apps.jwql.monitor_models.dark_current import MIRIDarkDarkCurrent, MIRIDarkPixelStats, MIRIDarkQueryHistory
    from jwql.website.apps.jwql.monitor_models.dark_current import NIRCamDarkDarkCurrent, NIRCamDarkPixelStats, NIRCamDarkQueryHistory
    from jwql.website.apps.jwql.monitor_models.dark_current import NIRISSDarkDarkCurrent, NIRISSDarkPixelStats, NIRISSDarkQueryHistory
    from jwql.website.apps.jwql.monitor_models.dark_current import NIRSpecDarkDarkCurrent, NIRSpecDarkPixelStats, NIRSpecDarkQueryHistory

    from jwql.website.apps.jwql.monitor_models.edb import FGSEdbBlocksStats, FGSEdbDailyStats, FGSEdbEveryChangeStats, FGSEdbTimeIntervalStats, FGSEdbTimeStats
    from jwql.website.apps.jwql.monitor_models.edb import MIRIEdbBlocksStats, MIRIEdbDailyStats, MIRIEdbEveryChangeStats, MIRIEdbTimeIntervalStats, MIRIEdbTimeStats
    from jwql.website.apps.jwql.monitor_models.edb import NIRCamEdbBlocksStats, NIRCamEdbDailyStats, NIRCamEdbEveryChangeStats, NIRCamEdbTimeIntervalStats, NIRCamEdbTimeStats
    from jwql.website.apps.jwql.monitor_models.edb import NIRISSEdbBlocksStats, NIRISSEdbDailyStats, NIRISSEdbEveryChangeStats, NIRISSEdbTimeIntervalStats, NIRISSEdbTimeStats
    from jwql.website.apps.jwql.monitor_models.edb import NIRSpecEdbBlocksStats, NIRSpecEdbDailyStats, NIRSpecEdbEveryChangeStats, NIRSpecEdbTimeIntervalStats, NIRSpecEdbTimeStats

    from jwql.website.apps.jwql.monitor_models.grating import NIRSpecGratingQueryHistory

    from jwql.website.apps.jwql.monitor_models.readnoise import FGSReadnoiseQueryHistory, FGSReadnoiseStats
    from jwql.website.apps.jwql.monitor_models.readnoise import MIRIReadnoiseQueryHistory, MIRIReadnoiseStats
    from jwql.website.apps.jwql.monitor_models.readnoise import NIRCamReadnoiseQueryHistory, NIRCamReadnoiseStats
    from jwql.website.apps.jwql.monitor_models.readnoise import NIRISSReadnoiseQueryHistory, NIRISSReadnoiseStats
    from jwql.website.apps.jwql.monitor_models.readnoise import NIRSpecReadnoiseQueryHistory, NIRSpecReadnoiseStats

    from jwql.website.apps.jwql.monitor_models.ta import MIRITaQueryHistory