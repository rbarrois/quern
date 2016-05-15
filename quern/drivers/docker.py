import logging
import os.path

import docker

from . import base
from .. import core


logger = logging.getLogger('quern')


class Driver(base.BaseDriver):

    def setup(self):
        for repo_path in self.config.repositories:
            if not os.path.isdir(repo_path):
                raise core.ImproperlyConfigured("Missing repository at %s" % repo_path)

    def build(self):
        ro_volumes = self.repository_map.copy()
        rw_volumes = {}
        rw_volumes[self.config.outdir] = self.INNER_IMAGE
        if self.config.binpkg_dir:
            rw_volumes[self.config.binpkg_dir] = self.INNER_BINPKG
        if self.config.distfiles_dir:
            rw_volumes[self.config.distfiles_dir] = self.INNER_DISTFILES

        env = self._make_runner_env()

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
        ))
        logger.info("Host config: %r", host_config)
        container = client.create_container(
            image=base_image,
            entrypoint=['/usr/bin/quern-builder'],
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
        client.wait(container=container_id)

        logger.info("Removing container")
        client.remove_container(container=container_id, v=True)

        logger.info("Build complete, image is available in %s", self.config.outdir)

    def _make_host_config(self, ro_volumes, rw_volumes):
        binds = {}
        for host_path, image_path in ro_volumes.items():
            binds[host_path] = {'bind': image_path, 'mode': 'ro'}
        for host_path, image_path in rw_volumes.items():
            binds[host_path] = {'bind': image_path, 'mode': 'rw'}

        return {
            'binds': binds,
            'tmpfs': {'/tmp': 'size=200M'},
        }

    def _make_runner_env(self):

        env = {
            # Coming from the host
            'portage.binhost': self.config.binhost,
            'build.profile': self.config.profile,
            'emerge.jobs': self.config.emerge_jobs,
            'strip.doc': self.config.strip,
            'strip.paths': ', '.join(self.config.strip_folders),

            # Forced for our setup
            'build.driver': 'raw',
            'portage.autofix': True,
            'portage.repositories': ', '.join(self.repository_map.values()),
            'build.outdir': os.path.join(self.PREFIX, 'image'),
            'portage.binpkg': os.path.join(self.PREFIX, 'binpkg') if self.config.binpkg_dir else '',
            'portage.distfiles': os.path.join(self.PREFIX, 'distfiles') if self.config.distfiles_dir else '',
        }

        namespace = self.config.getconf_namespace.upper()
        return {
            '{namespace}_{key}'.format(namespace=namespace, key=key.upper().replace('.', '_')): str(value)
            for key, value in env.items()
        }
