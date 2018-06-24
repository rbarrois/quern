import logging
import os
import os.path
import shutil
import subprocess

from . import base


logger = logging.getLogger('quern')


def run_command(args, **environ):
    logger.info("Calling %s %s",
        ' '.join('%s="%s"' % item for item in sorted(environ.items())),
        ' '.join(args),
    )

    env = dict(os.environ)
    env.update(environ)
    return subprocess.check_call(args, env=env)


class Driver(base.BaseDriver):
    def _fix_portage(self, main_repo):
        """Fix the portage setup: point /usr/portage at the main repo path."""
        if not self.config.autofix_portage:
            return

        import portage
        import portage.util
        old_noiselimit = portage.util.noiselimit
        portage.util.noiselimit = -10  # Disable all warnings from portage

        try:
            trees = portage.db['/']['vartree'].settings.repositories.treemap
        finally:
            portage.util.noiselimit = old_noiselimit

        if main_repo.name in trees:
            expected_path = trees[main_repo.name]
            if not os.path.isdir(expected_path):
                logger.info("Fixed main portage: pointing %s at %s", expected_path, main_repo.location)
                os.symlink(main_repo.location, expected_path)

    def setup(self):
        if os.path.exists(self.config.portage_configroot):
            logger.info("Existing portage configuration found at %s, moving to %s",
                    self.config.portage_configroot,
                    self.config.portage_configroot_backup,
            )
            os.rename(self.config.portage_configroot, self.config.portage_configroot_backup)

        logger.info("Configuring build portage at %s", self.config.portage_configroot)
        os.makedirs(self.config.portage_configroot, exist_ok=True)

        make_conf = os.path.join(self.config.portage_configroot, 'make.conf')
        with open(make_conf, 'w', encoding='UTF-8') as f:
            for line in self.config.make_conf_lines():
                f.write(line + '\n')

        logger.info("Configuring build repositories")
        repos_conf = os.path.join(self.config.portage_configroot, 'repos.conf')
        with open(repos_conf, 'w', encoding='UTF-8') as f:
            f.write('\n'.join(self.config.make_repos_conf_lines()))

        self._fix_portage(self.config.repositories[0])

    def build(self):
        logger.info("Starting compilation")

        if self.config.unblocker_profile:
            # Specific profile that helps fixing USE conflicts (e.g when USE flags
            # trigger circular dependencies on the builder system)
            logger.info("Breaking host blocks: using profile %s", self.config.unblocker_profile)
            run_command(['eselect', 'profile', 'set', self.config.unblocker_profile])

            logger.info("Merging unblocking packages to main system")
            run_command(['emerge', '--oneshot', '--newuse', '@world'], ROOT='/')

        logger.info("Enabling profile %s", self.config.profile)
        run_command(['eselect', 'profile', 'set', self.config.profile])

        if self.config.baselayout_atoms:
            # Merge baselayout atoms first - they should setup common system files
            logger.info("Building baselayout atoms: %s", ', '.join(self.config.baselayout_atoms))
            run_command(['emerge', '--jobs=1'] + self.config.baselayout_atoms)

        logger.info("Building @profile packages")
        run_command(['emerge', '@profile'])

        # Cleanup
        for d in self.config.strip_folders:
            folder = os.path.join(self.config.workdir_image, d.lstrip('/'))
            logger.info("Pruning %s", folder)
            shutil.rmtree(folder)

        logger.info("Collecting image at %s", self.config.image_path)
        run_command(['tar', '--directory', self.config.workdir_image, '--create', '--gzip', '--file', self.config.image_path, '.'])

        logger.info("Done")
