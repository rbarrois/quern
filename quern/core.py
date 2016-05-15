import datetime
import logging
import os.path


logger = logging.getLogger('quern')


class QuernError(Exception):
    """Base class for quern-related exceptions"""


class ImproperlyConfigured(QuernError):
    """Configuration errors"""


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='>>> %(levelname)s: %(message)s',
    )
    logging.getLogger('getconf').setLevel(logging.WARNING)


class Config:

    def __init__(self, getter):
        self.getconf_namespace = getter.namespace

        # Portage setup
        self.repositories = getter.getlist('portage.repositories',
            doc="Comma-separated paths of portage repositories; defaults to /usr/portage")
        self.binhost = getter.getstr('portage.binhost',
            doc="Space-separated list of binary package hosts")
        self.distfiles_dir = getter.getstr('portage.disftiles',
            doc="Path to distfiles")
        self.binpkg_dir = getter.getstr('portage.binpkg', doc="Path where binpkgs should be written")
        self.autofix_portage = getter.getbool('portage.autofix', False, doc="Point system /usr/portage at main repository")

        # Build profile
        self.profile = getter.getstr('build.profile', doc="Portage profile to use")
        self.outdir = getter.getstr('build.outdir', doc="Folder where the generated will be written")

        # Emerge configuration
        self.emerge_jobs = getter.getint('emerge.jobs', doc="Parallel portage builds")
        self.emerge_ask = getter.getbool('emerge.ask', doc="Require questions from emerge")

        # Optional features
        self.workdir = getter.getstr('build.workdir', '/tmp/quern', doc="Working directory for the build process")
        self.strip = getter.getbool('strip.doc', False, doc="Strip simple files (man/info/doc) from the image")
        self.strip_folders = getter.getlist('strip.paths', doc="Comma-separated list of folders strip from the image")

        # Driver
        self.driver = getter.getstr('build.driver', 'raw', doc="Build driver")

        # Docker driver configuration
        self.docker_image = getter.getstr('docker.image', doc="Docker base image for building")
        self.docker_address = getter.getstr('docker.daemon', 'unix://var/run/docker.sock', doc="Address of docker daemon")

    def check(self):
        if not self.outdir:
            raise ImproperlyConfigured("build.outdir is not set")
        if os.path.exists(self.outdir) and not os.path.isdir(self.outdir):
            raise ImproperlyConfigured("build.outdir: %s is not a directory." % self.outdir)

        if not self.profile:
            raise ImproperlyConfigured("build.profile is not set")

        if self.driver == 'docker':
            if not self.docker_image:
                raise ImproperlyConfigured("docker.image is not set, but using the docker driver")


    @property
    def workdir_image(self):
        return os.path.join(self.workdir, 'image')

    @property
    def workdir_portage(self):
        return os.path.join(self.workdir, 'etc', 'portage')

    @property
    def image_path(self):
        basename = self.profile

        # Remove repository prefix (e.g xelnor:path/to/subprofile -> path/to/subprofile)
        basename = basename.split(':', 1)[-1]
        # Convert slashes to dashes
        basename = basename.replace('/', '-')

        version = datetime.date.today().strftime('%Y-%m-%d')

        name = 'image-{basename}-{version}.tar.gz'.format(basename=basename, version=version)
        return os.path.join(self.outdir, name)

    def make_conf_lines(self):
        def varline(var, value):
            return '{var}="{value}"'.format(var=var, value=value)

        def extendline(var, value):
            return '{var}="${var} {value}"'.format(var=var, value=value)

        yield varline('ROOT', self.workdir_image)

        if self.distfiles_dir:
            yield varline('DISTDIR', self.distfiles_dir)
        if self.binpkg_dir:
            yield varline('PKGDIR', self.binpkg_dir)
        if self.binhost:
            yield varline('BINHOST', self.binhost)

        if self.emerge_jobs:
            yield extendline('EMERGE_DEFAULT_OPTS', "--jobs=%d" % self.emerge_jobs)
        if self.emerge_ask:
            yield extendline('EMERGE_DEFAULT_OPTS', '--ask')

        if self.strip:
            yield extendline('FEATURES', "nodoc noinfo noman")

        if self.binhost:
            yield extendline('FEATURES', "getbinpkg")
        if self.binpkg_dir:
            yield extendline('FEATURES', "buildpkg")
            yield extendline('EMERGE_DEFAULT_OPTS', '--usepkg')


