import importlib


def load(driver, config):
    pkg = __package__
    name = '{pkg}.{module}'.format(pkg=__package__, module=driver)
    mod = importlib.import_module(name)
    cls = getattr(mod, 'PostBuilder')
    return cls(config)
