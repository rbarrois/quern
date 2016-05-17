Quern
=====

Quern is powerful image builder, based on the portage package manager.
It allows to finely tune the content of generated images.


Concepts
--------

quern uses portage to build custom images.

The overall process is:

1. Setup a build environment:

   * Contains a working portage installation and toolchain
   * Configure portage to use the user-selected repositories
   * Activate the user-selected portage profile

2. Build the profile-selected packages in a temporary image root
3. Apply optional cleanup steps (remove docs, portage data, ...)
4. Compress the temporary image root to a ``tar.gz`` archive
5. Optionally, build upon that archive (e.g a Docker image)


*Notes:*

    * The current version is able to build images either directly (for instance on a gentoo instance)
      or within a docker image
    * It is strongly advised to use the main Gentoo portage tree as a base


Detailed example
----------------

In this example, we'll look at the steps to build a minimal Python3 Docker image, using an alternate libc (musl).

We'll use:

- A gentoo musl image as a source (based on a stage3 from http://distfiles.gentoo.org/experimental/amd64/musl/),
  where we've installed quern manually
- The musl overlay for gentoo (to install musl)
- Our own overlay, containing a "musl-python3" profile


The profile configuration is rather simple, even if split over a few files:

.. code-block:: sh

    # file: overlay/profiles/musl-python3/make.defaults
    # Install only Python3.4
    PYTHON_TARGETS="-python2_7 python3_4"

    # file: overlay/profiles/musl-python3/package.provided
    # Don't install python3 post-install packages
    app-admin/python-updater-0.11
    app-eselect/eselect-python-20111108

    # file: overlay/profiles/musl-python3/packages
    virtual/libc
    dev-lang/python:3.4

    # file: overlay/profiles/musl-python3/use.force
    # Disable glibc, use musl instead
    -glibc
    musl

    # file: overlay/profiles/musl-python3/use.mask
    # Disable glibc, use musl instead
    glibc
    -musl

    # file: overlay/profiles/musl-python3/parent
    # Reuse the musl profile from Gentoo
    gentoo:hardened/linux/musl/amd64


With the following configuration file:

.. code-block:: ini

    [portage]
    ; Load main portage tree + our overlays
    repositories = /home/user/dev/portage, /home/user/dev/musl-overlay, /home/user/dev/test-overlay

    ; Write generated binary packages for faster runs
    binpkg = /home/user/dev/binpkg/amd64-musl-hardened


    [build]
    ; Write the image to /home/user/dev/image
    outdir = /home/user/dev/image

    ; Use our new profile
    profile = test-overlay:musl-python3

    ; Build through docker
    driver = docker


    [docker]
    ; Use que quern-amd64-musl-hardened image
    image = quern-amd64-musl-hardened:20160404


    [emerge]
    ; We've got a big machine, tell emerge to run fast
    jobs = 6


    [strip]
    ; We want a small image, remove docs
    doc = yes
    ; Also, remove portage packaging info, and Python test suite
    paths = /var/db/pkg, /usr/lib/python3.4/test


    [postbuild]
    ; Once built, generate a docker image
    engines = docker


    [dockergen]
    ; Name of the image
    name = musl-python3

    ; Use YYYYMMDD as the image tag
    tag = $$DATE$$

    ; Extra info for the generated image
    maintainer = Raphaël Barrois <raphael.barrois+quern@polytechnique.org>
    entrypoint = /usr/bin/python3


Now, we'll run:

.. code-block:: sh

    quern-builder musl-python3.conf

    >>> INFO: Connecting to docker
    >>> INFO: Creating container from quern-amd64-musl-hardened:20160404, name=quern-quern-test-musl-python3-19967
    >>> INFO: Starting container (id=ff3182d878fef10d6c5eaafad0c18d0c58a9a990b894fe3e6d1a67f6262e0b30, name=quern-quern-test-musl-python3-19967)
    >>> INFO:   logs: >>> INFO: Successfully loaded configuration from files [] (searching in ['/etc/quern.conf'])
    >>> INFO:   logs: >>> INFO: Configuring build portage at /tmp/quern/etc/portage
    >>> INFO:   logs: >>> INFO: Configuring build repositories
    >>> INFO:   logs: >>> INFO: Configuring repository /quern/repositories/usr-portage
    >>> INFO:   logs: >>> INFO: Fixed main portage: pointing /usr/portage at /quern/repositories/usr-portage
    >>> INFO:   logs: >>> INFO: Configuring repository /quern/repositories/home-xelnor-dev-quern-test-musl-overlay
    >>> INFO:   logs: >>> INFO: Configuring repository /quern/repositories/home-xelnor-dev-quern-test-overlay
    >>> INFO:   logs: >>> INFO: Enabling profile quern-test:musl-python3
    >>> INFO:   logs: >>> INFO: Calling PORTAGE_CONFIGROOT="/tmp/quern" eselect profile set quern-test:musl-python3
    >>> INFO:   logs: >>> INFO: Starting compilation
    >>> INFO:   logs: >>> INFO: Calling PORTAGE_CONFIGROOT="/tmp/quern" emerge @profile
    >>> INFO:   logs:
    >>> INFO:   logs: * IMPORTANT: 4 news items need reading for repository 'gentoo'.
    >>> INFO:   logs: * Use eselect news read to view new items.
    >>> INFO:   logs:
    >>> INFO:   logs: Calculating dependencies  ... done!
    >>> INFO:   logs: >>> Emerging binary (1 of 19) sys-libs/musl-1.1.14::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (2 of 19) app-arch/bzip2-1.0.6-r6::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (3 of 19) app-arch/xz-utils-5.2.2::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (4 of 19) sys-apps/busybox-1.24.2-r99::musl for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (5 of 19) sys-libs/ncurses-5.9-r5::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (6 of 19) app-misc/c_rehash-1.7-r1::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (7 of 19) sys-libs/zlib-1.2.8-r1::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (8 of 19) app-misc/mime-types-9::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (9 of 19) dev-libs/expat-2.1.0-r5::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (10 of 19) sys-apps/debianutils-4.4::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (11 of 19) virtual/libintl-0-r2::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (5 of 19) sys-libs/ncurses-5.9-r5::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (12 of 19) dev-libs/libffi-3.0.13-r1::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (13 of 19) sys-libs/ncurses-5.9-r99::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (6 of 19) app-misc/c_rehash-1.7-r1::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (7 of 19) sys-libs/zlib-1.2.8-r1::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (8 of 19) app-misc/mime-types-9::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (9 of 19) dev-libs/expat-2.1.0-r5::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (10 of 19) sys-apps/debianutils-4.4::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (11 of 19) virtual/libintl-0-r2::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (14 of 19) app-misc/ca-certificates-20151214.3.21::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (12 of 19) dev-libs/libffi-3.0.13-r1::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (13 of 19) sys-libs/ncurses-5.9-r99::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (15 of 19) virtual/libffi-3.0.13-r1::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (16 of 19) sys-libs/readline-6.3_p8-r2::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (14 of 19) app-misc/ca-certificates-20151214.3.21::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (15 of 19) virtual/libffi-3.0.13-r1::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (17 of 19) dev-libs/openssl-1.0.2h::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (16 of 19) sys-libs/readline-6.3_p8-r2::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (17 of 19) dev-libs/openssl-1.0.2h::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (3 of 19) app-arch/xz-utils-5.2.2::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (2 of 19) app-arch/bzip2-1.0.6-r6::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (4 of 19) sys-apps/busybox-1.24.2-r99::musl to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (1 of 19) sys-libs/musl-1.1.14::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (18 of 19) virtual/libc-0::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Emerging binary (19 of 19) dev-lang/python-3.4.3-r1::gentoo for /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (19 of 19) dev-lang/python-3.4.3-r1::gentoo to /tmp/quern/image/
    >>> INFO:   logs: >>> Installing (18 of 19) virtual/libc-0::gentoo to /tmp/quern/image/
    >>> INFO:   logs:
    >>> INFO:   logs: >>> Auto-cleaning packages...
    >>> INFO:   logs:
    >>> INFO:   logs: >>> Using system located in ROOT tree /tmp/quern/image/
    >>> INFO:   logs:
    >>> INFO:   logs: >>> No outdated packages were found on your system.
    >>> INFO:   logs:
    >>> INFO:   logs: * IMPORTANT: 5 news items need reading for repository 'gentoo'.
    >>> INFO:   logs: * Use eselect news read to view new items.
    >>> INFO:   logs:
    >>> INFO:   logs: >>> INFO: Pruning /tmp/quern/image/var/db/pkg
    >>> INFO:   logs: >>> INFO: Pruning /tmp/quern/image/usr/lib/python3.4/test
    >>> INFO:   logs: >>> INFO: Collecting image at /quern/image/image-musl-python3-2016-05-16.tar.gz
    >>> INFO:   logs: >>> INFO: Calling  tar --directory /tmp/quern/image --create --gzip --file /quern/image/image-musl-python3-2016-05-16.tar.gz .
    >>> INFO:   logs: >>> INFO: Done
    >>> INFO: Waiting for container to disappear
    >>> INFO: Removing container
    >>> INFO: Build complete, image is available at /tmp/image/quern/image-musl-python3-2016-05-16.tar.gz
    >>> INFO: Connecting to docker
    >>> INFO: Building raw image quern-musl-python3:20160516152300
    >>> INFO: Raw image quern-musl-python3:20160516152300 built: sha256:c766eda393c0e398d197c8c389fbdfe892dfe01dc0593e57c5b297d2e7b1b1fd
    >>> INFO: Building full image musl-python3:20160516 from raw quern-musl-python3:20160516152300
    >>> INFO:   build: Step 1 : FROM quern-musl-python3:20160516152300
    >>> INFO:   build: ---> c766eda393c0
    >>> INFO:   build: Step 2 : MAINTAINER Raphaël Barrois <raphael.barrois+quern@polytechnique.org>
    >>> INFO:   build: ---> Running in 22ae531c0fa9
    >>> INFO:   build: ---> 8cf7da532efb
    >>> INFO:   build: Removing intermediate container 22ae531c0fa9
    >>> INFO:   build: Step 3 : ENTRYPOINT /usr/bin/python3
    >>> INFO:   build: ---> Running in d57e85f1612e
    >>> INFO:   build: ---> 734824943e97
    >>> INFO:   build: Removing intermediate container d57e85f1612e
    >>> INFO:   build: Step 4 : LABEL quern-version "0.0.1" quern-profile "quern-test:musl-python3"
    >>> INFO:   build: ---> Running in 3f9c5083e5a7
    >>> INFO:   build: ---> b9c386856df0
    >>> INFO:   build: Removing intermediate container 3f9c5083e5a7
    >>> INFO:   build: Successfully built b9c386856df0
    >>> INFO: Image musl-python3:20160516 successfully built.


And the image is here:

.. code-block:: sh

    % docker images musl-python3
    REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
    musl-python3        20160516            b9c386856df0        3 minutes ago       58.06 MB





Configuration
-------------

Quern uses `getconf <http://getconf.readthedocs.io/>`_ to read its configuration.
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
