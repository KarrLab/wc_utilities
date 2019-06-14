""" Configuration

:Author: Jonathan Karr <jonrkarr@gmail.com>
:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2019-05-13
:Copyright: 2019, Karr Lab
:License: MIT
"""

import configobj
import os
import pkg_resources
import wc_utils.config.core


def get_config(extra=None):
    """ Get configuration

    Args:
        extra (:obj:`dict`, optional): additional configuration to override

    Returns:
        :obj:`configobj.ConfigObj`: nested dictionary with the configuration settings loaded from the configuration source(s).
    """
    paths = wc_utils.config.core.ConfigPaths(
        default=pkg_resources.resource_filename('wc_utils', 'util/config/core.default.cfg'),
        schema=pkg_resources.resource_filename('wc_utils', 'util/config/core.schema.cfg'),
        user=(
            'wc_utils.cfg',
            os.path.expanduser('~/.wc/wc_utils.util.cfg'),
        ),
    )

    return wc_utils.config.core.ConfigManager(paths).get_config(extra=extra)
