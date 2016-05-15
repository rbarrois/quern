#!/usr/bin/env python3

import getconf
import sys

from . import core
from . import drivers
from . import postbuild


def main(argv=sys.argv):
    core.setup_logging()

    display_help = False
    if len(argv) == 1 or argv[1] in ('-h', '--help'):
        display_help = True
        config_files = []

    else:
        config_files = argv[1:]

    getter = getconf.ConfigGetter('quern', config_files)
    config = core.Config(getter)

    if display_help:
        # Help requested
        print("Usage: %s path/to/example.conf" % argv[0])
        print("\nExample configuration file:\n\n")
        print(getter.get_ini_template())
        return

    config.check()

    driver = drivers.load(config.driver, config)

    driver.setup()
    driver.build()

    for engine_name in config.postbuild_engines:
        engine = postbuild.load(engine_name, config)
        engine.run()


if __name__ == '__main__':
    main(sys.argv)

