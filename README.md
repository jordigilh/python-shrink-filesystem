# python-shrink-filesystem

## Description
This python script shrinks a file system to a given size. The size is retrieved from the value of the `x-systemd.shrinkfs` option in the file system's entry in `/etc/fstab`:

```
/dev/vdb1 /mnt ext4 defaults,x-systemd.shrinkfs=3G 1 2
```

In this case, the FS will be shrunk to 3G.

The scripts expects the name of the device to be provided as argument to the command:

```python
$>python main.py /dev/vdb1
e2fsck 1.46.5 (30-Dec-2021)
Pass 1: Checking inodes, blocks, and sizes
Pass 2: Checking directory structure
Pass 3: Checking directory connectivity
Pass 4: Checking reference counts
Pass 5: Checking group summary information
/dev/vdb1: 11/294912 files (0.0% non-contiguous), 40022/1152000 blocks
resize2fs 1.46.5 (30-Dec-2021)
Resizing the filesystem on /dev/vdb1 to 786432 (4k) blocks.
The filesystem on /dev/vdb1 is now 786432 (4k) blocks long.
```
