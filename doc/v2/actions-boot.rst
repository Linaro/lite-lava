.. _boot_action:

Boot Action Reference
#####################

The ``boot`` action is used to cause the device to boot using the deployed
files. Depending on the parameters in the job definition, this could be by
executing a command on the dispatcher (for example
``/usr/bin/qemu-system-x86_64``) or by connecting to the device over serial or
ssh. Depending on the power state of the device and the device configuration,
the device may be powered up or reset to provoke the boot.

Every ``boot`` action **must** specify a method which is used to determine how
to boot the deployed files on the device. Depending on the method, other
parameters will be required.

Boot actions which result in a POSIX type login or shell must specify a list of
expected prompts which will be matched against the output to determine the
endpoint of the boot process. There are no default prompts, the test writer is
responsible for providing a list of all possible prompts.

.. seealso:: :ref:`boot_prompts`

.. contents::
   :backlinks: top

.. index:: auto login, boot auto login

.. _boot_auto_login:

auto_login
**********

Some systems require the test job to specify a username and optionally a
password to login. These values must be specified in the test job submission.
If the system boots directly to a prompt without needing a login, the
``auto_login`` details can be omitted from the test job submission.

.. note:: The test job submission uses ``auto_login`` with underscore.

.. index:: auto login prompt, boot auto login prompt

.. _boot_auto_login_login_prompt:

login_prompt
============

The prompt to match when the system requires a login. This prompt needs to be
unique across the entire boot sequence, so typically includes ``:`` and should
be quoted. If the hostname of the device is included in the prompt, this can be
included in the ``login_prompt``:

.. code-block:: yaml

  auto_login:
    login_prompt: 'login:'
    username: root

.. note:: If login_prompt is not matched during boot LAVA will send control
   characters to the shell "thinking" that the kernel alert happened
   which may result in incorrect login but after it recognizes the
   ``Login incorrect`` message it will automatically try to log in
   using provided credentials.

.. index:: auto login username, boot auto login username

.. _boot_auto_login_username:

username
========

Whenever a ``login_prompt`` is specified, a ``username`` will also be required.
The username should either be ``root`` or a user with ``sudo`` access without
needing a password.

.. index:: auto login password prompt, boot auto login password prompt

.. _boot_auto_login_password_prompt:

password_prompt
===============

If the login requires a password as well as a username, the ``password_prompt``
must be specified:

.. code-block:: yaml

  auto_login:
    login_prompt: 'login:'
    username: root
    password_prompt: 'Password:'
    password: rootme

.. note:: If password_prompt is not matched during login or password is
   required but not provided LAVA will recognize the ``Login timed out``
   message, stop the execution of the job and log the error.

.. index:: auto login password, boot auto login password

.. _boot_auto_login_password:

password
========

Whenever a ``password_prompt`` is specified, a ``password`` will also be
required.

.. index:: auto login login commands, boot auto login login commands

.. _boot_auto_login_login_commands:

login_commands
==============

A list of arbitrary ``login_commands`` can be run after the initial login and
before setting the shell prompt. This is typically used to make a regular user
become root with su. For example:

.. code-block:: yaml

  auto_login:
    login_prompt: 'login:'
    username: user
    password_prompt: 'Password:'
    password: pass
    login_commands:
    - sudo su

.. note:: No interactive input such as a password can be provided with the list
   of ``login_commands``.

.. index:: prompt list, prompts - test jobs, boot prompt list, boot prompts

.. _boot_prompts:

prompts
*******

After login (or directly from boot if no login is required), LAVA needs to
match the first prompt offered by the booted system. The full list of possible
prompts **must** be specified by the test writer in the test job submission.

Each prompt needs to be unique across the entire boot sequence, so typically
includes ``:`` and needs to be quoted. If the hostname of the device is
included in the prompt, this can be included in the ``prompt``:

.. caution:: Take care with the specified prompts. Prompt strings which do not
   include enough characters can match early, resulting in a failed login.
   Prompt strings which include extraneous characters may fail to match for all
   test jobs. Avoid prompt elements which are user-specific, e.g. ``$``
   indicates an unprivileged user in some shells and ``#`` indicates the
   superuser. ``~`` indicates the home directory in some shells. In general,
   the prompt string should **include and usually end with** a colon ``:`` or a
   colon and space.

.. code-block:: yaml

     - boot:
         prompts:
         - 'root@debian:'

When using the :term:`lxc` :term:`protocol`, the hostname element of the
prompt will vary:

.. code-block:: yaml

     - boot:
         prompts:
         - 'root@(.*):'

When using a ramdisk, the prompt is likely to need to contain brackets which
will need to be escaped:

.. code-block:: yaml

     - boot:
         prompts:
         # escape the brackets to ensure that the prompt does not match
         # kernel debug lines which may mention initramfs
         - '\(initramfs\)'

.. index:: boot connection

.. _boot_connection:

connection
**********


.. index:: boot connection namespace

.. _boot_connection_namespace:

connection-namespace
********************

When using :term:`namespaces <namespace>` in job definition, you can reuse the
existing serial connection from another namespace via ``connection-namespace``
parameter. Example:

.. code-block:: yaml

   actions:
   - deploy:
       namespace: boot1
   # ...
   - boot:
       namespace: boot1
   # ...
   - test:
       namespace: boot1
   # ...
   - boot:
       namespace: boot2
       connection-namespace: boot1
   # ...
   - test:
       namespace: boot2
   # ...

.. index:: boot commands

.. _boot_commands:

commands
********

One of the key definitions in the :term:`device type` template for
each device is the list(s) of boot ``commands`` that the device
needs. These are sets of specific commands that will be run to boot
the device to start a test. The definitions will typically include
placeholders which LAVA will substitute with dynamic data as
necessary. For example, the full path to a tftp kernel image will be
expanded to include a job-specific temporary directory when a job is
started.

As a simple example from a U-Boot template:

.. code-block:: yaml

  - setenv autoload no
  - setenv initrd_high '0xffffffff'
  - setenv fdt_high '0xffffffff'
  - setenv loadkernel 'tftp {KERNEL_ADDR} {KERNEL}'
  - setenv loadinitrd 'tftp {RAMDISK_ADDR} {RAMDISK}; setenv initrd_size ${filesize}'
  - setenv loadfdt 'tftp {DTB_ADDR} {DTB}'
  - setenv bootcmd 'run loadkernel; run loadinitrd; run loadfdt; {BOOTX}'
  - boot

.. note:: In some cases, the boot commands list in the template may
   not provide **all** of the commands used; lines will also be
   generated from other data in the template. For example: the command
   ``setenv kernel_addr_r '0x82000000'`` might be generated from the
   load addresses which match the type of kernel being deployed.

When a test is started, the appropriate list of commands will be
selected. LAVA then substitutes the placeholders in the list to
generate a complete command list. The final parsed and expanded boot
commands used for a test are reported in the logs for that test job,
e.g.:

.. code-block:: none

 Parsed boot commands: setenv autoload no; setenv initrd_high '0xffffffff';
 setenv fdt_high '0xffffffff'; setenv kernel_addr_r '0x82000000'; setenv
 initrd_addr_r '0x83000000'; setenv fdt_addr_r '0x88000000'; setenv loadkernel
 'tftp ${kernel_addr_r} 158349/tftp-deploy-Fo78o6/vmlinuz'; setenv loadinitrd
 'tftp ${initrd_addr_r} 158349/tftp-deploy-Fo78o6/ramdisk.cpio.gz.uboot; setenv
 initrd_size ${filesize}'; setenv loadfdt 'tftp ${fdt_addr_r}
 158349/tftp-deploy-Fo78o6/am335x-boneblack.dtb'; setenv bootargs
 'console=ttyO0,115200n8 root=/dev/ram0  ip=dhcp'; setenv bootcmd 'dhcp; setenv
 serverip 10.3.1.1; run loadkernel; run loadinitrd; run loadfdt; bootz
 0x82000000 0x83000000 0x88000000'; boot

.. index:: boot commands - full

.. _full_boot_commands:

Specifying commands in full
===========================

During testing and development, it can **sometimes** be useful to use
a different set of boot commands instead of what is listed in the
jinja2 template for the device-type. This allows test writers to
change boot commands beyond the scope of existing overrides. To work
sensibly in the LAVA environment, these commands will still need to
**include the placeholders** such that temporary paths etc. can be
substituted in when the test job is started.

In this example (for an x86 test machine using iPXE), the commands
change the ``root`` argument to the kernel to boot from a SATA drive
which has been configured separately. (For example, by the admins or
by test writers from a hacking session.)

.. literalinclude:: examples/test-jobs/x86-sata-commands.yaml
   :language: yaml
   :lines: 32, 36-42

.. caution:: This support is **only** recommended for use for corner
   cases and administrator-level debugging. Accordingly, LAVA will
   raise a warning each time this support is used. Abuse of this
   support can potentially stop devices from working in subsequent
   tests, or maybe even damage them permanently - be careful!

   If the commands are to be used regularly, `ask on the lava-users mailing
   list <https://lists.lavasoftware.org/mailman/listinfo/lava-users>`_ requesting
   that a label is created in the templates for this set of commands.
   Alternatively, you can request a new override to make the existing labels
   more flexible.

.. index:: kernel command line, extra kernel arguments, boot commands - kernel

.. _appending_kernel_command_line:

Appending to the kernel command line
====================================

A test job may require extra kernel command line options to enable or disable
particular functionality. The :term:`job context` can be used to append
strings to the kernel command line:

.. code-block:: jinja

  context:
      extra_kernel_args: vsyscall=native

Values need to be separated by whitespace and will be added to the command
line with a prefix of a single space and a suffix of a single space.

The possible values which can be used are determined solely by the support
available within the kernel provided to the :term:`DUT`.

Depending on the boot method, it may also be possible to add specific options,
for example to append values to the NFS options using ``extra_nfsroot_args``:

.. code-block:: jinja

  context:
      extra_nfsroot_args: ,rsize=4096 nfsrootdebug

.. note:: ``extra_nfsroot_args`` are appended directly to the existing NFS
   flags ``nfsroot={NFS_SERVER_IP}:{NFSROOTFS},tcp,hard,intr`` so if the
   appended string contains an extra flag, this must be put first and the
   string must start with a comma. Other options can then be separated by a
   space or can use ``extra_kernel_args``. The example above would result in
   the string ``nfsroot={NFS_SERVER_IP}:{NFSROOTFS},tcp,hard,intr,rsize=4096
   nfsrootdebug``. (Whether that makes sense to any particular test job is out
   of scope for this documentation.)

.. seealso:: `Kernel documentation for NFSROOT
   <https://www.kernel.org/doc/Documentation/filesystems/nfs/nfsroot.txt>`_ ,
   :ref:`override_variables_context` and :ref:`override_support`

.. index:: boot failure_message

.. _boot_failure_message:

failure_message
***************

Some devices deploy the boot commands inside the boot image which is
then deployed using ``fastboot``. To boot the device after deployment,
LAVA does not interrupt the bootloader (e.g. U-Boot or Grub) and lets
the configured boot arguments control the boot.

In some situations, a test kernel can fail and cause the device to
reset to the bootloader. The presence of configured boot commands leads
to the device booting into an environment which is not necessarily the
one required by the test writer and the failure of the test kernel can
then be hidden. To handle this issue, a ``failure_message`` can be
specified to match a string output by the bootloader after the device
has reset. The test job will then fail after the reset and tracking the
kernel errors.

.. seealso:: :ref:`boot_method_fastboot`

.. index:: boot method

.. _boot_method:

method
******

The boot ``method`` determines how the device is booted and which commands and
prompts are used to determine a successful boot.

.. index:: boot method bootloader

.. _boot_method_bootloader:

bootloader
==========

The ``bootloader`` method is used to power-on the :term:`DUT`, interrupt the
bootloader, and wait for the bootloader prompt.

In order to interrupt the bootloader, the bootloader type should be specified
in the ``bootloader`` parameter:

.. code-block:: yaml

    method: bootloader
    bootloader: u-boot
    commands: []
    prompts: ['=>']

.. note:: the bootloader method type should match a boot method supported by
          the give device-type.
          For example ``fastboot``, ``minimal``, ``pyocd``, ``u-boot``, ...

The ``commands`` parameter is required but can be kept empty.
If some commands should be sent to the bootloader before the end of the action,
give the list in the ``commands`` parameter.

.. index:: boot method cmsis-dap

.. _boot_method_cmsis_dap:

cmsis-dap
=========

The ``cmsis-dap`` boot method takes no arguments or parameters.

.. code-block:: yaml

    method: cmsis-dap
    timeout:
      minutes: 10

.. index:: boot method depthcharge

.. _boot_method_depthcharge:

depthcharge
===========

The ``depthcharge`` boot method takes no arguments or parameters.  It is used
to boot the downloaded kernel image, and optionally a device tree and a
ramdisk.  The files are converted into an FIT (U-Boot Flattened Image Tree
format) image suitable to be booted by Coreboot using the Depthcharge payload,
typically used by Chrome OS devices.  It also creates a separate text file with
the kernel command line which is made available to the :term:`DUT` over TFTP
alongside the FIT image.

.. code-block:: yaml

  - boot:
      method: depthcharge
      commands: nfs

.. note:: Unlike some other boot methods such as ``u-boot``, the
          ``depthcharge`` boot method always expects the kernel image to be in
          the same standard format (zImage for arm, Image for arm64...).  So
          there should not be any ``type`` attribute for the kernel image in
          the ``deploy`` section as shown in the example below:

.. code-block:: yaml

  - deploy:
      kernel:
        url: http://storage.kernelci.org/mainline/master/v4.18-1283-g10f3e23f07cb/arm/multi_v7_defconfig/zImage
      ramdisk:
        url: http://storage.kernelci.org/images/rootfs/debian/stretchtests/20180627.0/armhf/rootfs.cpio.gz
        compression: gz

.. index:: boot method fastboot

.. _boot_method_fastboot:

fastboot
========

The ``fastboot`` boot method takes no arguments or parameters.

.. code-block:: yaml

  - boot:
      method: fastboot
      namespace: droid
      prompts:
        - 'root@(.*):/#'
        - 'hikey:/'
      timeout:
        minutes: 15

.. note:: Since all fastboot :term:`DUT` depend on LXC to run jobs, it is
          mandatory to have the namespace specified.

.. index:: boot method fastboot commands

.. _boot_method_fastboot_commands:

fastboot boot commands
----------------------

Some test jobs may need to add a ``fastboot`` command prior to boot, for
example to specify whether the ``_a`` or ``_b`` partitions are to be
active.

If the test job specifies the ``images`` labels as ``boot_a`` instead
of ``boot``, then a fastboot boot command will be required to make sure
that the device boots from ``boot_a`` instead of ``boot_b`` (which may
contain an old deployment from a previous test job or may contain nothing
at all).

.. code-block:: yaml

  - boot:
      method: fastboot
      commands:
      - --set-active=_a

.. index:: boot method grub

.. _boot_method_grub:

grub
====

The ``grub`` boot method takes no arguments or parameters.

.. code-block:: yaml

  - boot:
      method: grub
      commands: ramdisk

.. index:: boot method grub-efi

.. _boot_method_grub_efi:

grub-efi
========

The ``grub-efi`` boot method takes no arguments or parameters. **However**, in
most cases, starting Grub from UEFI requires using the
:ref:`boot_method_uefi_menu` as well.

.. literalinclude:: examples/test-jobs/mustang-grub-efi.yaml
   :language: yaml
   :lines: 42, 47, 48

Download or view the complete example:
`examples/test-jobs/mustang-grub-efi.yaml
<examples/test-jobs/mustang-grub-efi.yaml>`_

.. note:: Admins can refer to the ``mustang-grub-efi.jinja2`` template for an
   example of how to make selections from a UEFI menu to load Grub. See
   :ref:`device_type_templates`.

.. index:: boot method ipxe

.. _boot_method_ipxe:

ipxe
====

The ``ipxe`` boot method takes no arguments or parameters.

.. code-block:: yaml

 - boot:
    method: ipxe
    commands: ramdisk
    prompts:
    - 'root@debian:~#'
    - '/ #'

.. index:: boot method lxc

.. _boot_method_lxc:

lxc
===

.. seealso:: :ref:`lxc_protocol_reference`

.. code-block:: yaml

 - boot:
    method: lxc
    prompts:
    - 'root@(.*):/#'
    timeout:
      minutes: 5

.. index:: boot method openocd

.. _boot_method_openocd:

openocd
=======

The ``openocd`` boot method takes no arguments or parameters.

The method works by passing through the command line options for the
openocd command. It downloads and runs the executable specified by ``binary``
in the job definition. It also allows an openocd script file to be downloaded
from the location specified by ``openocd_script`` in the job definition, if
a custom script file should be used instead of the one specified by the
device type.

.. code-block:: yaml

 - boot:
    method: openocd
    timeout:
      minutes: 3

.. index:: boot method pyocd

.. _boot_method_pyocd:


.. index:: boot method minimal

.. _boot_method_minimal:

minimal
=======

The ``minimal`` method is used to power-on the :term:`DUT` and to let the
:term:`DUT` boot without any interaction.

.. code-block:: yaml

    method: minimal
    prompts:
    - 'root@debian:~#'
    - '/ #'

.. note:: auto-login and transfer_overlay are both supported for this method.

By default LAVA will reset the board power when executing this action. Users
can skip this step by adding ``reset: false``. This can be useful when testing
bootloader in interactive tests and then booting to the OS.

pyocd
=====

The ``pyocd`` boot method takes no arguments or parameters.

.. code-block:: yaml

 - boot:
    method: pyocd
    timeout:
      minutes: 10

.. index:: boot method jlink

.. _boot_method_jlink:


.. index:: boot method minimal

.. _boot_method_minimal:

minimal
=======

The ``minimal`` method is used to power-on the :term:`DUT` and to let the
:term:`DUT` boot without any interaction.

.. code-block:: yaml

    method: minimal
    prompts:
    - 'root@debian:~#'
    - '/ #'

.. note:: auto-login and transfer_overlay are both supported for this method.

By default LAVA will reset the board power when executing this action. Users
can skip this step by adding ``reset: false``. This can be useful when testing
bootloader in interactive tests and then booting to the OS.

jlink
=====

The ``jlink`` boot method takes no arguments or parameters.

.. code-block:: yaml

 - boot:
    method: jlink
    timeout:
      minutes: 10

.. index:: boot method console

.. _boot_method_console:

new_connection
==============

The ``new_connection`` boot method takes no arguments or
parameters. This method can be used to switch to a new connection,
allowing a test to isolate test and kernel messages (if the kernel and
the device are both appropriately configured).

.. include:: examples/test-jobs/hikey-new-connection.yaml
     :code: yaml
     :start-after: # boot uart0 block
     :end-before: # boot hikey block

.. note:: The ``new_connection`` boot method **must** use a different
   :term:`namespace` to all other actions in the test job. The test
   shell(s) must pass this namespace label as the
   ``connection-namespace``.

.. seealso:: :ref:`boot_connection_namespace`

.. include:: examples/test-jobs/hikey-new-connection.yaml
     :code: yaml
     :start-after: # test isolation block
     :end-before: # test lxc block

.. index:: boot method qemu

.. _boot_method_qemu:

qemu
====

The ``qemu`` method is used to boot the downloaded ``image`` from the
deployment action using QEMU. This runs the QEMU command line on the
dispatcher. Only certain elements of the command line are available for
modification using the :term:`job context`. The available values can vary
depending on local admin configuration. For example, many admins restrict the
available memory of each QEMU device, so the ``memory`` option in the job
context may be ignored.

.. code-block:: yaml

    context:
      arch: aarch64
      memory: 2048
      # comment out or change to user if the dispatcher does not support bridging.
      # netdevice: tap
      extra_options:
      - -smp
      - 1
      - -global
      - virtio-blk-device.scsi=off
      - -device virtio-scsi-device,id=scsi
      - --append "console=ttyAMA0 root=/dev/vda rw"

The version of ``qemu`` installed on the dispatcher is a choice made by the
admin. Generally, this will be the same as the version of ``qemu`` available
from Debian in the same suite as the rest of the packages installed on the
dispatcher, e.g. ``stretch``. Information on the available versions of ``qemu``
in Debian is available at https://tracker.debian.org/pkg/qemu

.. seealso:: :ref:`essential_components` and :ref:`qemu-iso boot method
   <boot_method_qemu_iso>`

.. index:: boot method qemu media tmpfs

.. _boot_method_qemu_media_tmpfs:

media
-----

When booting a QEMU image file directly, the ``media`` needs to be specified as
``tmpfs``.

.. code-block:: yaml

 - boot:
     method: qemu
     media: tmpfs

.. index:: boot method qemu-nfs

.. _boot_method_qemu_nfs:

qemu-nfs
========

The ``qemu-nfs`` method is used to boot a downloaded ``kernel`` with a root
filesystem deployed on the worker. Only certain elements of the command line
are available for modification using the :term:`job context`. The available
values can vary depending on local admin configuration. For example, many
admins restrict the available memory of each QEMU device, so the ``memory``
option in the job context may be ignored.

The version of ``qemu`` installed on the dispatcher is a choice made by the
admin. Generally, this will be the same as the version of ``qemu`` available
from Debian in the same suite as the rest of the packages installed on the
dispatcher, e.g. ``stretch``. Information on the available versions of ``qemu``
in Debian is available at https://tracker.debian.org/pkg/qemu

QEMU can be used with an NFS using the ``qemu-nfs`` method and the ``nfs``
media:

.. literalinclude:: examples/test-jobs/qemu-nfs.yaml
    :language: yaml
    :lines: 49-54

.. seealso:: :ref:`boot method qemu <boot_method_qemu>`.

When using ``qemu-nfs``, the hostname element of the prompt will vary according
to the worker running QEMU:

.. literalinclude:: examples/test-jobs/qemu-nfs.yaml
    :language: yaml
    :lines: 58-59

.. index:: boot method qemu media nfs

.. _boot_method_qemu_media_nfs:

media
-----

When booting a QEMU image using NFS, the ``media`` needs to be specified as
``nfs``.

.. literalinclude:: examples/test-jobs/qemu-nfs.yaml
    :language: yaml
    :lines: 49-54

.. index:: boot method qemu-iso

.. _boot_method_qemu_iso:

qemu-iso
========

The ``qemu-iso`` method is used to boot the downloaded installer from the
deployment action using QEMU. This runs the QEMU command line on the
dispatcher. Only certain elements of the command line are available for
modification using the :term:`job context`.

The version of ``qemu`` installed on the dispatcher is a choice made by the
admin. Generally, this will be the same as the version of ``qemu`` available
from Debian in the same suite as the rest of the packages installed on the
dispatcher, e.g. ``stretch``. Information on the available versions of ``qemu``
in Debian is available at https://tracker.debian.org/pkg/qemu

.. seealso:: :ref:`essential_components` and :ref:`boot method qemu
   <boot_method_qemu>`

.. code-block:: yaml

 - boot:
    method: qemu-iso
    media: img
    timeout:
      minutes: 20
    connection: serial
    auto_login:
      login_prompt: 'login:'
      username: root
      password_prompt: 'Password:'
      password: root
    prompts:
    - 'root@debian:~#'

.. index:: boot method qemu-iso media

.. _boot_method_qemu_iso_media:

media
-----

When booting an installer using QEMU, the ``media`` needs to be specified as
``img``

.. code-block:: yaml

 - boot:
     method: qemu-iso
     media: img

.. index:: transfer overlay

.. _boot_transfer_overlay:

transfer_overlay
================

An overlay is a tarball of scripts which run the LAVA Test Shell for
the test job. The tarball also includes the git clones of the
repositories specified in the test job submission and the LAVA helper
scripts. Normally, this overlay is integrated into the test job
automatically. In some situations, for example when using a command
list to specify an alternative rootfs, it is necessary to transfer the
overlay from the worker to the device using commands within the booted
system prior to starting to run the test shell.

Some overlay tarballs can be quite large. The LAVA TestShell helpers are tiny
shell scripts but the git repositories cloned for your test shell definitions
can become large over time. Additionally, if your test shell definition clones
the git repo of source code, those clones will also appear in the overlay
tarball.

.. note:: The situations where ``transfer_overlay`` is useful tend to
   also require restricting the test job to specific devices of a
   particular device type. This needs to be arranged with the lab
   admins who can create suitable :term:`device tags <device tag>`
   which will need to be specified in all test job definitions.

.. seealso:: :ref:`secondary_media` which is more flexible but slower.

The overlay is transferred before any test shell operations can occur,
so the method of transferring and then unpacking the overlay **must**
work without any further setup of the rootfs. All dependencies must be
pre-installed and all configuration must be in place (possibly using a
hacking session). This includes the **network** configuration - the
worker offers an apache host to download the overlay and LAVA can
populate the URL but the device **must** automatically configure the
networking immediately upon boot and the network **must** work
straight away.

.. code-block:: yaml

    transfer_overlay:
      download_command: wget -S --progress=dot:giga
      unpack_command: tar -C / -xzf

.. note:: The ``-C /`` command to tar is **essential** or the test shell will
   not be able to start. The overlay will use ``gzip`` compresssion, so pass
   the ``z`` option to ``tar``.

Deployment differences
----------------------

The ``-S --progress=dot:giga`` options to wget in the example above optimise
the output for serial console logging to avoid wasting line upon line of
progress percentage dots. If the system uses ``busybox``, these options may not
be supported by the version of ``wget`` on the device.

Some systems do not store the current time between boots. The ``--warning
no-timestamp`` option is a useful addition for ``tar`` for those systems but
note that ``busybox tar`` does not support this option.

The ``download_command`` and the ``unpack_command`` can include one or more
shell commands. However, as with the test shell definitions, avoid using
redirects (``>`` or ``>>``) or other complex shell syntax. This example changes
to ``/tmp`` to ensure there is enough writeable space for the download.

.. code-block:: yaml

    transfer_overlay:
       download_command: cd /tmp ; wget
       unpack_command: tar -C / -xzf

.. index:: boot method u-boot

.. _boot_method_u_boot:

u-boot
======

The ``u-boot`` method boots the downloaded files using U-Boot commands.

.. index:: boot method u-boot commands

.. _boot_method_u_boot_commands:

commands
--------

The predefined set of U-Boot commands into which the location of the downloaded
files can be substituted (along with details like the SERVERIP and NFS
location, where relevant). See the device configuration for the complete set of
commands.

Certain elements of the command line are available for modification using the
:term:`job context`. The available values vary by :term:`device type`.

.. index:: boot method u-boot type

.. _boot_method_u_boot_type:

type
----

.. caution:: This support is deprecated and has been replaced by :ref:`kernel
   type in the deploy action <deploy_to_tftp_kernel_type>`.

The type of boot, dependent on the U-Boot configuration. This needs to match
the supported boot types in the device configuration, e.g. it may change the
load addresses passed to U-Boot.

.. code-block:: yaml

 - boot:
   method: u-boot
   commands: nfs
   type: bootz
   prompts:
     - 'root@debian:~#'

.. index:: boot method uefi-menu

.. _boot_method_uefi_menu:

uefi-menu
=========

The ``uefi-menu`` method selects a pre-defined menu in the UEFI configuration
for the device. In most cases, this is used to execute a different bootloader.
For example, a ``fastboot`` device can execute ``fastboot`` from a menu item or
a device could execute an ``PXE`` menu item to download and execute Grub.

.. caution:: Although it *is possible* to create new menu entries in UEFI each
   time a test job starts, this has proven to be unreliable on both of the
   device types tested so far. If the build of UEFI is not able to download a
   bootloader using ``PXE``, then experiment with creating a UEFI menu item
   which is able to execute a local file and have a build of Grub on local
   storage. Build the grub binary using ``grub-mkstandalone`` to ensure that
   all modules are available.

UEFI menus will renumber themselves each time a new item is added or removed,
so LAVA must be able to match the description of the menu item and then
identify the correct selector to be able to send the correct character to
execute that menu option. This means that the admins must create the same menu
structures on each device of the same device type and correlate the text
content of the menu with the :ref:`jinja2 templates
<developing_device_type_templates>`.

To use ``uefi-menu``, the device must offer a menu from which items can be
selected using a standard regular expression: ``'a-zA-Z0-9\s\:'``, for example:

.. code-block:: shell

  [1] bootloader
  [2] boot from eMMC
  [3] Boot Manager
  [4] Reboot

The :term:`device type` template would need to specify the ``separator``
(whitespace in the example) as well as how to identify the **item** matching
the requested selector:

.. code-block:: yaml

          item_markup:
            - "["
            - "]"
          item_class: '0-9'
          separator: ' '

This allows LAVA to match a menu item matching ``\[[0-9]\] ['a-zA-Z0-9\s\:']``
and select the correct selector when the menu item string matches one (and only
one) line output by the UEFI menu. In this example, the selector must be a
digit.

The template must then also specify which menu item to select, according to
the ``commands`` set in the testjob:

.. code-block:: yaml

    method: uefi-menu
    commands: fastboot

The template would then need:

.. code-block:: yaml

        fastboot:
        - select:
            items:
             - 'boot from eMMC'
