import collections
import os.path

class BaseDriver:
    """Manage a quern builder (configure, launch, collect image)"""

    PREFIX = '/quern'

    INNER_IMAGE = os.path.join(PREFIX, 'image')
    INNER_BINPKG = os.path.join(PREFIX, 'binpkg')
    INNER_DISTFILES = os.path.join(PREFIX, 'distfiles')
    INNER_REPOSITORIES = os.path.join(PREFIX, 'repositories')
    INNER_PORTAGE_WORKDIR = '/var/tmp/portage'

    def __init__(self, config):
        self.config = config
        self.repository_map = collections.OrderedDict()
        for repo in self.config.repositories:
            self.repository_map[repo.location] = os.path.join(
                    self.INNER_REPOSITORIES, repo.location.strip('/').replace('/', '-'))

    def setup(self):
        pass

    def build(self):
        pass
