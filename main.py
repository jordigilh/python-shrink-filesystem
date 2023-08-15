"""
 Shrinks a Linux file system, eg. ext4. Note that XFS is not supported.
"""

import os
import sys
import subprocess
import argparse
from collections import namedtuple


SHRINK_TAG = 'x-systemd.shrinkfs'

fstab_entry = namedtuple("fstab_entry",
                         "device mount fs_type options dump passno")


def init_arguments():
    """Init arguments"""
    parser = argparse.ArgumentParser(description='Shrinks an unmounted' +
                                     ' partition to a given size defined' +
                                     ' with option ' + SHRINK_TAG +
                                     ' in the /etc/fstab entry of the device')
    parser.add_argument('device_name', type=str,
                        help='name of the device as found in the first' +
                        ' column in the /etc/fstab')
    return parser


def main():
    """Main funtion"""
    # init arguments
    parser = init_arguments()
    # process arguments
    args = parser.parse_args()
    if len(args.device_name) == 0:
        print("Missing device name argument")
        sys.exit(1)
    with open("/etc/fstab", "r") as file:
        entries = read_fstab(file.readlines())
    found = False
    for entry in entries:
        if entry.device == args.device_name:
            found = True
            process_entry(entry)
    if not found:
        print('device '+args.device_name+' not found')


def process_entry(entry):
    """Process entry from fstab"""
    if contains_tag(entry):
        device_name = get_device_name(entry.device)
        current_size_in_bytes = get_current_volume_size(device_name)
        expected_size, expected_size_in_bytes = parse_tag(entry)
        if current_size_in_bytes > expected_size_in_bytes:
            if not is_block_device(entry.device):
                raise BlockDeviceException('device ' + entry.device +
                                           ' is not a block device')
            if is_device_mounted(entry.device):
                raise MountException('device '+entry.device+' is mounted')
            shrink_volume(device_name, expected_size)
        elif current_size_in_bytes < expected_size_in_bytes:
            print('volume ' + entry.device + ' is already smaller than' +
                  ' the expected size')


def get_device_name(device):
    """Determine device name. This can come handy when the device
    name in the fstab is defined as a UUID instead of a path in /dev"""
    if device.startswith('UUID='):
        device_path = os.readlink("/dev/disk/by-uuid/"+device[len('UUID='):])
        return "/dev"+os.path.realpath(device_path)
    return device


def get_tag_value(entry):
    """Returns the value of the x-systemd.shrinkfs if defined in the options"""
    for tag in entry.options.split(","):
        if tag.startswith(SHRINK_TAG+'='):
            return tag[len(SHRINK_TAG+'='):]
    return ''


def contains_tag(entry):
    """Returns true if the x-systemd.shrinkfs option is defined for
    the device entry in the fstab"""
    return get_tag_value(entry) != ''


def parse_tag(entry):
    """Returns the value as captured in the tag and a representation of
    the value in bytes
    Eg: 1M -> (1M,1048576)"""
    value = get_tag_value(entry)
    # expect the unit to be the last char
    return value, int(format_bytes(value[:len(value)-1], value[len(value)-1:]))


def is_device_mounted(device_name):
    """Returns true if the device is mounted."""
    return subprocess.call(["/usr/bin/findmnt", "--source", device_name]) == 0


def is_block_device(device_name):
    """Returns true if the device is a block device"""
    dev_type = subprocess.check_output(["/usr/bin/lsblk", device_name,
                                        "--noheadings", "-o", "TYPE"])
    return dev_type.strip() == "lvm"


def get_current_volume_size(device_name):
    """Returns the current size of the logical volume as defined by
    the device name"""
    size = subprocess.check_output(["/usr/bin/lsblk", "-b",
                                    device_name, "-o", "SIZE", "--noheadings"])
    return int(size)


def format_bytes(ssize, unit):
    """Converts a given tuple (numbers,units) into bytes:
    Eg: (1,'M')-> 1048576"""
    isize = int(ssize)
    # 2**10 = 1024
    power = 2**10
    power_labels = {'': 0, 'K': 1, 'M': 2, 'G': 3, 'T': 4}
    number = power_labels[unit]
    while number > 0:
        isize *= power
        number -= 1
    return isize


def shrink_volume(device_name, new_size):
    """Calls the lvreduce binary to shrink the logical volume.
    The action includes a fsck, a resize of the file system in the
    volume and last the resize of the LV."""
    # Resize the file system
    ret = subprocess.call(["/usr/sbin/lvreduce",
                           "--resizefs", "-L", new_size, device_name])
    if ret != 0:
        raise ShrinkException('failed to shrink the' +
                              ' file system in device ' + device_name)


def read_fstab(content):
    """Reads the content of the fstab and returns a slice containing
    fstab_entry elements mapping to the entries in the fstab file that
    refer to a filesystem"""
    parsed_content = []
    for line in content:
        if line.startswith('#') or line.startswith('\n'):
            continue
        sliced = line.split()
        parsed_content.append(
            fstab_entry(sliced[0],
                        sliced[1],
                        sliced[2],
                        sliced[3],
                        sliced[4],
                        sliced[5]))
    return parsed_content


class MountException(Exception):
    "Raised when a volume is already mounted"


class ShrinkException(Exception):
    "Raised when there is an error shrinking a volume"


class BlockDeviceException(Exception):
    "Raised when the device is not a block device"


if __name__ == "__main__":
    main()
