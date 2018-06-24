import collections
import datetime
import logging
import re
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


_RepositoryConfig = collections.namedtuple(
    'RepositoryConfig',
    ['name', 'location', 'eclass_overrides', 'masters', 'priority'],
)


class RepositoryConfig(_RepositoryConfig):
    @classmethod
    def from_section(cls, name, config):
        section = config.get_section('repository:%s' % name)
        return cls(
            name=name,
            location=section['location'],
            eclass_overrides=section['eclass-overrides'],
            masters=section['masters'],
            priority=section['priority'],
        )

    def as_repos_conf_dict(self):
        return {
            'location': self.location,
            'eclass-overrides': self.eclass_overrides,
            'masters': self.masters,
            'priority': self.priority,
        }

    def as_repos_conf_lines(self):
        def make_line(option_name, value):
            if value:
                return '{} = {}'.format(option_name, value)
            else:
                return '# {} ='.format(option_name)

        return [
            '[{}]'.format(self.name),
        ] + [
            make_line(option, value)
            for option, value in self.as_repos_conf_dict().items()
        ]


class Config:

    def __init__(self, getter, namespace):
        self.getconf_namespace = namespace
        self.now = datetime.datetime.utcnow()

        # Portage setup
        repo_names = getter.getlist('portage.repositories',
            doc="Comma-separated list of repository:xxx sections to load")

        if repo_names:
            self.repositories = [
                RepositoryConfig.from_section(repo_name, getter)
                for repo_name in repo_names
            ]
        else:
            self.repositories = [
                RepositoryConfig(
                    name='gentoo',
                    location='/usr/portage',
                    eclass_overrides='',
                    masters='',
                    priority='',
                ),
            ]

        self.binhost = getter.getstr('portage.binhost',
            doc="Space-separated list of binary package hosts")
        self.distfiles_dir = getter.getstr('portage.distfiles',
            doc="Path to distfiles")
        self.binpkg_dir = getter.getstr('portage.binpkg', doc="Path where binpkgs should be written")
        self.autofix_portage = getter.getbool('portage.autofix', False, doc="Point system /usr/portage at main repository")
        self.debug_workdir = getter.getstr('portage.debug_workdir', doc="Store failed build workspaces")

        # Build profile
        self.unblocker_profile = getter.getstr('build.unblocker_profile', doc="Portage profile to break blockers (merged to host)")
        self.profile = getter.getstr('build.profile', doc="Portage profile to use")
        self.baselayout_atoms = getter.getlist('build.baselayout_atoms', "sys-apps/baselayout", doc="Atoms to install to the image before any other package")
        self.outdir = getter.getstr('build.outdir', doc="Folder where the generated will be written")
        self.forced_image_name = getter.getstr('build.image_name', doc="Force generated image name (with .tar.gz suffix)")
        self.keep_failed = getter.getbool('build.keep_failed', True, doc="Keep build environment of failed builds")

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
        self.docker_workdir_storage = getter.getstr(
            'docker.workdir_storage',
            'tmpfs:200M',
            doc="Backing storage for the working dir; tmpfs:xxM or file:/path/to/folder",
        )

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

            if not re.match(r'^(tmpfs:\d+[MG]|file:/.*)$', self.docker_workdir_storage):
                raise ImproperlyConfigured(
                    "docker.workdir_storage should be either tmpfs:xxxM or file:/path/to/file; got %s"
                    % self.docker_workdir_storage,
                )

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
    def portage_configroot(self):
        return os.path.join('/', 'etc', 'portage')

    @property
    def portage_configroot_backup(self):
        return '%s.quern-backup-%s' % (self.portage_configroot, self.now.isoformat())

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

    def make_repos_conf_lines(self):
        """Generate the lines for /etc/portage/repos.conf."""
        for i, repo in enumerate(self.repositories):
            if i == 0:
                yield '[DEFAULT]'
                yield 'main-repo = {}'.format(repo.name)

            yield ''
            yield from repo.as_repos_conf_lines()

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
        yield extendline('EMERGE_DEFAULT_OPTS', '--tree')
        yield extendline('EMERGE_DEFAULT_OPTS', '--verbose-conflicts')

        if self.strip:
            yield extendline('FEATURES', "nodoc noinfo noman")

        if self.binhost:
            yield extendline('FEATURES', "getbinpkg")
        if self.binpkg_dir:
            yield extendline('FEATURES', "buildpkg")
            yield extendline('FEATURES', "binpkg-multi-instance")
            yield extendline('EMERGE_DEFAULT_OPTS', '--usepkg')
            yield extendline('EMERGE_DEFAULT_OPTS', '--binpkg-respect-use=y')
            yield extendline('EMERGE_DEFAULT_OPTS', '--binpkg-changed-deps=y')

        # Ensure build-time deps are updated as well
        yield extendline('EMERGE_DEFAULT_OPTS', '--changed-deps=y')
        yield extendline('EMERGE_DEFAULT_OPTS', '--with-bdeps=y')
