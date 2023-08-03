from pyfstab import Fstab
import sys
import psutil
import subprocess
import argparse

##
# Shrinks a Linux file system, eg. ext4. Note that XFS is not supported. 
##

SHRINK_TAG = 'x-systemd.shrinkfs'

def init_arguments():
    parser = argparse.ArgumentParser(description='Shrinks an unmounted partition to a given size defined with option '+SHRINK_TAG+' in the /etc/fstab entry of the device')
    parser.add_argument('device_name', type=str,
                    help='name of the device as found in the first column in the /etc/fstab')
    return parser

def main():
    # init arguments
    parser = init_arguments()
    # process arguments
    args = parser.parse_args()
    if len(args.device_name)==0:
        print("Missing device name argument")
        sys.exit(1)
    fstab = Fstab()
    with open("/etc/fstab","r") as f:
        fstab.read_file(f)
    found = False
    #try:
    for entry in fstab.entries:
        if entry.device== args.device_name:
            found = True
            process_entry(entry)
    #except ValueError as e:
     #   print(repr(e))
    if not found:
        print('device '+args.device_name+' not found')


def process_entry(entry):
    if contains_tag(entry):
        current_size_in_bytes=get_current_partition_size(entry.dir)
        expected_size,expected_size_in_bytes=parse_tag(entry)
        print(str(current_size_in_bytes)+'?='+str(expected_size_in_bytes))
        if current_size_in_bytes > expected_size_in_bytes:
            if is_device_mounted(entry.dir):
                raise ValueError('device '+entry.device+' is mounted')
            shrink_volume(entry.device,expected_size)
        elif current_size_in_bytes < expected_size_in_bytes:
            print("volume "+entry.device+" is already smaller than the expected size")


def get_tag_value(entry):
    for tag in entry.options.split(','):
        if tag.startswith(SHRINK_TAG+'='):
            return tag[len(SHRINK_TAG+'='):]
    raise ValueError("tag "+SHRINK_TAG+' not found for device '+entry.device+' in /etc/fstab')
       
def contains_tag(entry):
    return get_tag_value(entry)!=''
      

def parse_tag(entry):
    value = get_tag_value(entry)
    return value,int(format_bytes(value[:len(value)-1],value[len(value)-1:])) # expect the unit to be the last char

        
def is_device_mounted(mount_point):
    for dp in psutil.disk_partitions(True):
        if dp.mountpoint==mount_point:
            return True
    return False


def get_current_partition_size(mount_point):
    mount_device(mount_point)
    size=psutil.disk_usage(mount_point).total
    umount_device(mount_point)
    return size

def format_bytes(ssize,unit):
    isize=int(ssize)
    # 2**10 = 1024
    power = 2**10
    power_labels = {'' : 0, 'K': 1, 'M': 2, 'G': 3, 'T': 4}
    n = power_labels[unit]
    while n>0:
        isize *= power
        n -= 1
    return isize

def mount_device(mount_point):
    if not is_device_mounted(mount_point):
        ret = subprocess.run(["/usr/bin/mount",mount_point])
        if ret.returncode!=0:
            raise ValueError("failed to mount "+mount_point)

def umount_device(mount_point):
    if is_device_mounted(mount_point):
        ret = subprocess.run(["/usr/bin/umount",mount_point])
        if ret.returncode!=0:
            raise ValueError("failed to unmount "+mount_point)


def shrink_volume(device_name,new_size):
    # Execute the file system check before resizing
    ret = subprocess.run(["/usr/sbin/e2fsck","-f",device_name])
    if ret.returncode!=0:
        raise ValueError("failed to run the file system check in device "+device_name)
    # Resize the file system
    ret = subprocess.run(["/usr/sbin/resize2fs",device_name,new_size])
    if ret.returncode!=0:
        raise ValueError("failed to shrink the file system in device "+device_name)


if __name__ == "__main__":
    main()