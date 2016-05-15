Quern
=====

Quern is powerful image builder, based on the portage package manager.
It allows to finely tune the content of generated images.


Usage::

    quern-builder quern.conf


Configuration
-------------

Quern uses `http://getconf.readthedocs.io/ <getconf>`_ to read its configuration.
All options can be set as environment variables or configuration file entries.

The available options are:

.. code-block:: ini

    [build]
    ; QUERN_BUILD_DRIVER - type=str - Build driver
    ;driver = raw
    ; QUERN_BUILD_OUTDIR - type=str - Folder where the generated will be written
    ;outdir =
    ; QUERN_BUILD_PROFILE - type=str - Portage profile to use
    ;profile =
    ; QUERN_BUILD_WORKDIR - type=str - Working directory for the build process
    ;workdir = /tmp/quern

    [docker]
    ; QUERN_DOCKER_DAEMON - type=str - Address of docker daemon
    ;daemon = unix://var/run/docker.sock
    ; QUERN_DOCKER_IMAGE - type=str - Docker base image for building
    ;image =

    [emerge]
    ; QUERN_EMERGE_ASK - type=bool - Require questions from emerge
    ;ask = off
    ; QUERN_EMERGE_JOBS - type=int - Parallel portage builds
    ;jobs = 0

    [portage]
    ; QUERN_PORTAGE_AUTOFIX - type=bool - Point system /usr/portage at main repository
    ;autofix = off
    ; QUERN_PORTAGE_BINHOST - type=str - Space-separated list of binary package hosts
    ;binhost =
    ; QUERN_PORTAGE_BINPKG - type=str - Path where binpkgs should be written
    ;binpkg =
    ; QUERN_PORTAGE_DISFTILES - type=str - Path to distfiles
    ;disftiles =
    ; QUERN_PORTAGE_REPOSITORIES - type=list - Comma-separated paths of portage repositories; defaults to /usr/portage
    ;repositories =

    [strip]
    ; QUERN_STRIP_DOC - type=bool - Strip simple files (man/info/doc) from the image
    ;doc = off
    ; QUERN_STRIP_PATHS - type=list - Comma-separated list of folders strip from the image
    ;paths =
