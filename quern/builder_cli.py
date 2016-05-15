#!/usr/bin/env python3

import getconf
import sys

from . import drivers
from . import core


def main(argv=sys.argv):
    core.setup_logging()

    config_files = ['/etc/quern.conf']
    if len(argv) > 1 and not argv[1].startswith('-'):
        config_files.append(argv[1])

    getter = getconf.ConfigGetter('quern', config_files)
    config = core.Config(getter)
    config.check()

    driver = drivers.load(config.driver, config)

    driver.setup()
    driver.build()


if __name__ == '__main__':
    main(sys.argv)

