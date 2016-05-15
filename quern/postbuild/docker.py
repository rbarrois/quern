import datetime
import io
import json
import logging

import docker

from . import base
from ..version import VERSION


logger = logging.getLogger('quern')


class PostBuilder(base.BasePostBuilder):
    def __init__(self, config):
        super().__init__(config)
        self.raw_image_name = 'quern-%s' % self.config.profile_safe
        self.raw_image_tag = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
        self.raw_image_fullname = '%s:%s' % (self.raw_image_name, self.raw_image_tag)

        # Generate 
        if self.config.dockergen_tag == '$$DATE$$':
            tag = datetime.date.today().strftime('%Y%m%d')
        else:
            tag = self.config.dockergen_tag

        if tag:
            self.target_image_name = '%s:%s' % (self.config.dockergen_name, tag)
        else:
            self.target_image_name = self.config.dockergen_name

    def run(self):
        logger.info("Connecting to docker")
        client = docker.Client(self.config.docker_address)

        logger.info("Building raw image %s", self.raw_image_fullname)
        res_raw = client.import_image_from_file(
            filename=self.config.image_path,
            repository=self.raw_image_name,
            tag=self.raw_image_tag,
        )
        res = json.loads(res_raw)
        logger.info("Raw image %s built: %s", self.raw_image_fullname, res['status'].strip())

        logger.info("Building full image %s from raw %s", self.target_image_name, self.raw_image_fullname)
        dockerfile_lines = '\n'.join(self._dockerfile_template())
        dockerfile = io.BytesIO(dockerfile_lines.encode('utf-8'))
        output = client.build(
            fileobj=dockerfile,
            rm=True,
            tag=self.target_image_name,
            decode=True,
        )
        for line in output:
            if 'stream' in line:
                logger.info("  build: %s", line['stream'].strip())
            else:
                logger.warn("  build: error: %r", line)

        logger.info("Image %s successfully built.", self.target_image_name)

    def _dockerfile_template(self):
        def line(text, **context):
            return text.format(**context)

        yield line("FROM {raw_image}", raw_image=self.raw_image_fullname)
        yield line("MAINTAINER {maintainer}", maintainer=self.config.dockergen_maintainer)

        if self.config.dockergen_entrypoint:
            yield line(
                    "ENTRYPOINT [{entrypoint}]",
                    entrypoint=", ".join('"%s"' % part for part in self.config.dockergen_entrypoint),
            )

        if self.config.dockergen_command:
            yield line("CMD [{cmd}]", cmd=", ".join('"%s"' % part for part in self.config.dockergen_command))

        for port in self.config.dockergen_ports:
            yield line("EXPOSE {port}", port=port)

        for volume in self.config.dockergen_volumes:
            yield line("VOLUME {volume}", volume=volume)

        if self.config.dockergen_workdir:
            yield line("WORKDIR {workdir}", workdir=self.config.dockergen_workdir)

        if self.config.dockergen_user:
            yield line("USER {user}", user=self.config.dockergen_user)

        yield line(
            """LABEL quern-version="{version}" quern-profile="{profile}" """,
            version=VERSION, profile=self.config.profile,
        )
