import collections
import os.path

class BaseDriver:
    """Manage a quern builder (configure, launch, collect image)"""

    PREFIX = '/quern'

    INNER_IMAGE = os.path.join(PREFIX, 'image')
    INNER_BINPKG = os.path.join(PREFIX, 'binpkg')
    INNER_DISTFILES = os.path.join(PREFIX, 'distfiles')
    INNER_REPOSITORIES = os.path.join(PREFIX, 'repositories')

    def __init__(self, config):
        self.config = config
        self.repository_map = collections.OrderedDict()
        for repo_path in self.config.repositories:
            self.repository_map[repo_path] = os.path.join(
                    self.INNER_REPOSITORIES, repo_path.strip('/').replace('/', '-'))

    def setup(self):
        pass

    def build(self):
        pass
