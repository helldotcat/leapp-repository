from leapp import reporting
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts, GRUBDevicePartitionLayout

SAFE_OFFSET_BYTES = 1024*1024  # 1MiB


def check_first_partition_offset():
    if architecture.matches_architecture(architecture.ARCH_S390X):
        return

    for fact in api.consume(FirmwareFacts):
        if fact.firmware == 'efi':
            return  # Skip EFI system

    problematic_devices = []
    for grub_dev in api.consume(GRUBDevicePartitionLayout):
        if not grub_dev.partitions:
            # NOTE(pstodulk): In case of empty partition list we have nothing to do.
            # This can could happen when the fdisk output is different then expected.
            # E.g. when GPT partition table is used on the disk. We are right now
            # interested strictly about MBR only, so ignoring these cases.
            # This is seatbelt, as the msg should not be produced for GPT at all.
            continue
        first_partition = min(grub_dev.partitions, key=lambda partition: partition.start_offset)
        if first_partition.start_offset < SAFE_OFFSET_BYTES:
            problematic_devices.append(grub_dev.device)

    if problematic_devices:
        summary = (
            'On the system booting by using BIOS, the in-place upgrade fails '
            'when upgrading the GRUB2 bootloader if the boot disk\'s embedding area '
            'does not contain enough space for the core image installation. '
            'This results in a broken system, and can occur when the disk has been '
            'partitioned manually, for example using the RHEL 6 fdisk utility.\n\n'

            'The list of devices with small embedding area:\n'
            '{0}.'
        )
        problematic_devices_fmt = ['- {0}'.format(dev) for dev in problematic_devices]

        hint = (
            'We recommend to perform a fresh installation of the RHEL 8 system '
            'instead of performing the in-place upgrade.\n'
            'Another possibility is to reformat the devices so that there is '
            'at least {0} kiB space before the first partition. If reformatting the drive is not possible, '
            'consider migrating your /boot folder and grub2 configuration to another drive '
            '(refer to https://cloudlinux.zendesk.com/hc/en-us/articles/14549594244508). '
            'Note that this operation is not supported and does not have to be '
            'always possible.'
        )

        reporting.create_report([
            reporting.Title('Found GRUB devices with too little space reserved before the first partition'),
            reporting.Summary(summary.format('\n'.join(problematic_devices_fmt))),
            reporting.Remediation(hint=hint.format(SAFE_OFFSET_BYTES // 1024)),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.BOOT]),
            reporting.Flags([reporting.Flags.INHIBITOR]),
        ])
