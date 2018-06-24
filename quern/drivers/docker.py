import logging
import os.path

import docker

from . import base
from .. import core


logger = logging.getLogger('quern')


class Driver(base.BaseDriver):

    def setup(self):
        for repo in self.config.repositories:
            if not os.path.isdir(repo.location):
                raise core.ImproperlyConfigured("Missing repository at %s" % repo.location)

    def build(self):
        ro_volumes = self.repository_map.copy()
        rw_volumes = {}
        rw_volumes[self.config.outdir] = self.INNER_IMAGE
        tmpfs_volumes = {}

        if self.config.binpkg_dir:
            rw_volumes[self.config.binpkg_dir] = self.INNER_BINPKG
        if self.config.distfiles_dir:
            rw_volumes[self.config.distfiles_dir] = self.INNER_DISTFILES
        if self.config.debug_workdir:
            rw_volumes[self.config.debug_workdir] = self.INNER_PORTAGE_WORKDIR

        workdir_engine, workdir_param = self.config.docker_workdir_storage.split(':', 1)
        if workdir_engine == 'tmpfs':
            # Expected format: tmpfs:200M
            tmpfs_volumes['/tmp'] = workdir_param
        else:
            # Expected format: file:/path/to/host/dir
            assert workdir_engine == 'file'
            rw_volumes['/tmp'] = workdir_param

        logger.info("Connecting to docker")
        client = docker.Client(self.config.docker_address)

        base_image = self.config.docker_image
        container_name = 'quern-%s-%d' % (
            self.config.profile.replace(':', '-').replace('/', '-'),
            os.getpid(),
        )

        logger.info("Creating container from %s, name=%s", base_image, container_name)
        host_config = client.create_host_config(**self._make_host_config(
            ro_volumes=ro_volumes,
            rw_volumes=rw_volumes,
            tmpfs_volumes=tmpfs_volumes,
        ))
        logger.info("Container config: %r", host_config)

        env = self._make_runner_env()
        logger.info("Container environment: %s", '  '.join('%s=%r' % (k, v) for (k, v) in sorted(env.items())))

        container = client.create_container(
            image=base_image,
            entrypoint=['/usr/bin/quern-builder', '/etc/quern.conf'],
            environment=env,
            volumes=list(ro_volumes.values()) + list(rw_volumes.values()),
            name=container_name,
            host_config = host_config,
        )

        container_id = container.get('Id')
        logger.info("Starting container (id=%s, name=%s)", container_id, container_name)
        response = client.start(container=container_id)
        if response is not None:
            logger.error("Error starting container: %s", response)
            return

        logs = client.logs(container=container_id, stdout=True, stderr=True, stream=True, follow=True)
        for log in logs:
            logger.info("  logs: %s", log.decode('utf-8').strip())

        logger.info("Waiting for container to disappear")
        retcode = client.wait(container=container_id)

        if retcode:
            logger.error("Container exited with code %d", retcode)

            if self.config.keep_failed:
                logger.info("Failed container kept: id=%s, name=%s", container_id, container_name)
                logger.info("Container environment: %s", '  '.join('%s=%r' % (k, v) for (k, v) in sorted(env.items())))
                return

        logger.info("Removing container")
        client.remove_container(container=container_id, v=True)

        if retcode == 0:
            logger.info("Build complete, image is available at %s", self.config.image_path)

    def _make_host_config(self, ro_volumes, rw_volumes, tmpfs_volumes):
        binds = {}
        tmpfs = {}
        for host_path, image_path in ro_volumes.items():
            binds[host_path] = {'bind': image_path, 'mode': 'ro'}
        for host_path, image_path in rw_volumes.items():
            binds[host_path] = {'bind': image_path, 'mode': 'rw'}
        for mountpoint, size in tmpfs_volumes.items():
            tmpfs[mountpoint] = 'size=%s' % size

        return {
            'binds': binds,
            'tmpfs': tmpfs,

            # Enable 'ptrace' capability, used by portage's sandbox.
            'cap_add': ['SYS_PTRACE'],
            'security_opt': ['apparmor:unconfined', 'seccomp:unconfined'],
        }

    def _make_runner_env(self):

        env = {
            # Coming from the host
            'portage.binhost': self.config.binhost,
            'build.unblocker_profile': self.config.unblocker_profile,
            'build.profile': self.config.profile,
            'build.baselayout_atoms': ', '.join(self.config.baselayout_atoms),
            'emerge.jobs': self.config.emerge_jobs,
            'strip.doc': self.config.strip,
            'strip.paths': ', '.join(self.config.strip_folders),

            # Forced for our setup
            # Build
            'build.driver': 'raw',
            'build.outdir': os.path.join(self.PREFIX, 'image'),
            'build.image_name': self.config.image_name,

            # Portage
            'portage.binpkg': os.path.join(self.PREFIX, 'binpkg') if self.config.binpkg_dir else '',
            'portage.distfiles': os.path.join(self.PREFIX, 'distfiles') if self.config.distfiles_dir else '',
            'portage.autofix': True,
        }

        # Add repository sections
        env['portage.repositories'] = ','.join(repo.name for repo in self.config.repositories)
        for repo in self.config.repositories:
            moved_repo = repo._replace(location=self.repository_map[repo.location])
            fields = moved_repo.as_repos_conf_dict()

            # Strip empty fields
            fields = {key: value for key, value in fields.items() if value}
            env.update({
                'repository:{}.{}'.format(repo.name, field): value
                for field, value in fields.items()
            })

        # Build a getconf-compatible environment
        namespace = self.config.getconf_namespace.upper()
        return {
            '{namespace}_{key}'.format(namespace=namespace, key=key.upper().replace('.', '_')): str(value)
            for key, value in env.items()
        }
