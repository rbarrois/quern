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
        self.now = datetime.datetime.utcnow()

        # Portage setup
        self.repositories = getter.getlist('portage.repositories',
            doc="Comma-separated paths of portage repositories; defaults to /usr/portage")
        self.binhost = getter.getstr('portage.binhost',
            doc="Space-separated list of binary package hosts")
        self.distfiles_dir = getter.getstr('portage.distfiles',
            doc="Path to distfiles")
        self.binpkg_dir = getter.getstr('portage.binpkg', doc="Path where binpkgs should be written")
        self.autofix_portage = getter.getbool('portage.autofix', False, doc="Point system /usr/portage at main repository")
        self.debug_workdir = getter.getstr('portage.debug_workdir', doc="Store failed build workspaces")

        # Build profile
        self.profile = getter.getstr('build.profile', doc="Portage profile to use")
        self.stage1_atoms = getter.getlist('build.stage1_atoms', "sys-apps/baselayout", doc="Atoms to install before @profile")
        self.outdir = getter.getstr('build.outdir', doc="Folder where the generated will be written")
        self.forced_image_name = getter.getstr('build.image_name', doc="Force generated image name (with .tar.gz suffix)")

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

        # Post-generation
        self.postbuild_engines = getter.getlist('postbuild.engines', doc="Engines for post-generation tasks")

        # Docker postgen configuration
        self.dockergen_name = getter.getstr('dockergen.name', doc="Generated image name")
        self.dockergen_tag = getter.getstr('dockergen.tag', doc="Generated image tag; use $$DATE$$ for %Y%m%d format")
        self.dockergen_maintainer = getter.getstr('dockergen.maintainer', doc="Dockerfile' MAINTAINER")
        self.dockergen_entrypoint = self._parse_shell(getter.getstr('dockergen.entrypoint', doc="Dockerfile' ENTRYPOINT"))
        self.dockergen_command = self._parse_shell(getter.getstr('dockergen.command', doc="Dockerfile' CMD"))
        self.dockergen_ports = getter.getlist('dockergen.ports', doc="Dockerfile' EXPOSE")
        self.dockergen_volumes = getter.getlist('dockergen.volumes', doc="Dockerfile' VOLUME")
        self.dockergen_workdir = getter.getstr('dockergen.workdir', doc="Dockerfile' WORKDIR")
        self.dockergen_user = getter.getstr('dockergen.user', doc="Dockerfile' USER")

    @classmethod
    def _parse_shell(cls, text):
        return [part.strip() for part in text.split()]

    def check(self):
        if not self.outdir:
            raise ImproperlyConfigured("build.outdir is not set")
        if os.path.exists(self.outdir) and not os.path.isdir(self.outdir):
            raise ImproperlyConfigured("build.outdir: %s is not a directory." % self.outdir)

        if self.forced_image_name and not self.forced_image_name.endswith('.tar.gz'):
            raise ImproperlyConfigured("When forcing build.image_name, it must end in .tar.gz; got %s" % self.forced_image_name)

        if not self.profile:
            raise ImproperlyConfigured("build.profile is not set")

        if self.driver == 'docker':
            if not self.docker_image:
                raise ImproperlyConfigured("docker.image is not set, but using the docker driver")

        if 'docker' in self.postbuild_engines:
            if not self.dockergen_name:
                raise ImproperlyConfigured("dockergen.name is required when using 'docker' in postbuild.engines.")

    @property
    def profile_safe(self):
        basename = self.profile

        # Remove repository prefix (e.g xelnor:path/to/subprofile -> path/to/subprofile)
        basename = basename.split(':', 1)[-1]
        # Convert slashes to dashes
        basename = basename.replace('/', '-')

        return basename

    @property
    def workdir_image(self):
        return os.path.join(self.workdir, 'image')

    @property
    def workdir_portage(self):
        return os.path.join(self.workdir, 'etc', 'portage')

    @property
    def image_name(self):
        if self.forced_image_name:
            return self.forced_image_name
        else:
            version = self.now.strftime('%Y-%m-%d')

            return 'image-{basename}-{version}.tar.gz'.format(basename=self.profile_safe, version=version)

    @property
    def image_path(self):
        return os.path.join(self.outdir, self.image_name)

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


