import binascii
import struct

sector = 512

# little endian
def little4(hex4): return struct.unpack('<L', hex4)[0] # 4byte
def little2(hex2): return struct.unpack('<H', hex2)[0] # 2byte
def little1(hex1): return struct.unpack('<B', hex1)[0] # 1byte


# MBR
def MBR():
    f.seek(454)
    LBA_str = f.read(4) # b'\x00\x08\x00\x00'
    LBA = little4(LBA_str) # 2048

    return LBA


# Super Block
def Superblock(Superblock_addr):   
    f.seek(Superblock_addr * sector) # 2050 * 512
    sb = f.read(sector)

    # 4byte씩 나누기
    sb_str = binascii.b2a_hex(sb).decode()
    sb_list = [sb_str[i:i+8] for i in range(0, sector*2, 8)]
    
    # log block size
    log_block_hex = binascii.unhexlify(sb_list[7])
    log_block = little4(log_block_hex)
    
    if log_block == 0:
        log_block_size = 1 # 1kb
    elif log_block == 1:
        log_block_size = 2 # 2kb
    elif log_block == 2:
        log_block_size = 4 # 4kb

    # Inode_Per_Group
    Inode_Per_Group_hex = binascii.unhexlify(sb_list[10])
    Inode_Per_Group = little4(Inode_Per_Group_hex)
    
    return log_block_size, Inode_Per_Group


# Group Descriptor Table
def GDT(GDT_addr, bg_num):
    bg_size = 32

    f.seek(GDT_addr * sector + bg_size * bg_num)
    GDT = f.read(bg_size)

    GDT_str = binascii.b2a_hex(GDT).decode() 
    GDT_list = [GDT_str[i:i+8] for i in range(0, sector*2, 8)]

    # Inode Table Address
    Inode_Table_hex = binascii.unhexlify(GDT_list[2])
    Inode_Table_dec = little4(Inode_Table_hex) 
    
    return Inode_Table_dec

# Inode Table
def Inode_Table(Inode_Table_addr, Inode_num):
    Inode_size = 256
    f.seek(Inode_Table_addr * sector + Inode_size * (Inode_num - 1))
    Inode = f.read(Inode_size)

    Inode_str = binascii.b2a_hex(Inode).decode() 
    Inode_list = [Inode_str[i:i+8] for i in range(0, Inode_size*2, 8)]

    # Directory Pointer
    DP_list = Inode_list[10:22]
    
    for a in reversed(DP_list):
        if a != '00000000':
            DP = a
            break
    
    DP_hex = binascii.unhexlify(DP)
    DP_dec = little4(DP_hex)
    
    return DP_dec

# Directory Entry
def Directory_Entry(DP_addr):
    DE_size = 256
    f.seek(DP_addr * sector)
    DE = f.read(DE_size)
    
    # 1byte씩 나누기
    DE_str = binascii.b2a_hex(DE).decode()
    DE_list = [DE_str[i:i+2] for i in range(0, DE_size*2, 2)]

    File_name, Dir_name, Block_Group_num = [], [], []
    i = 24
    while(i < DE_size):
        # Inode_num
        I_num_hex = binascii.unhexlify(DE_list[i] + DE_list[i+1] + DE_list[i+2] + DE_list[i+3])
        Inode_num = little4(I_num_hex)
        
        # record length
        r_len_hex = binascii.unhexlify(DE_list[i+4] + DE_list[i+5])
        record_len = little2(r_len_hex)
        
        # file name length
        n_len_hex = binascii.unhexlify(DE_list[i+6])
        name_len = little1(n_len_hex)

        # file type
        FT_hex = binascii.unhexlify(DE_list[i+7])
        FT_dec = little1(FT_hex)

        if FT_dec == 0:
            file_type = 'unknown'
        elif FT_dec == 1:
            file_type = 'Regular'
        elif FT_dec == 2:
            file_type = 'Directory'

        # file name
        name = []
        for k in range(8, 8 + name_len):
            name.append(DE_list[i+k])

        name_hex = binascii.unhexlify(''.join(name))
        name = name_hex.decode()
        File_name.append(name)


        if file_type == 'Directory' and name != 'lost+found':
            Dir_name.append(name_hex.decode())
            Block_Group_num.append(int((Inode_num-1)/Inode_Per_Group))
        
        i += record_len

    return File_name, Dir_name, Block_Group_num



#========= 실습이미지 =========
image_name = input('Input the ext4 image name (ex. ext4_image1.txt) : ')
f = open(image_name, 'rb+')

LBA = MBR()
Superblock_addr = LBA + 2

log_block_size, Inode_Per_Group = Superblock(Superblock_addr)
GDT_addr = Superblock_addr - 2 + log_block_size * 2

Inode_Table_dec = GDT(GDT_addr, 0)
Inode_Table_addr = (Inode_Table_dec * log_block_size * 2) + LBA

DP_dec = Inode_Table(Inode_Table_addr, 2) # root directory
DP_addr = (DP_dec * log_block_size * 2) + LBA

File_name, Dir_name, Block_Group_num = [], [], []
File_name, Dir_name, Block_Group_num = Directory_Entry(DP_addr)

print('root -->', File_name)

while(len(Dir_name) != 0):
    i=0
    for bg_num in Block_Group_num:
        f_Inode_Table_dec = GDT(GDT_addr, bg_num)
        f_Inode_Table_addr = (f_Inode_Table_dec * log_block_size * 2) + LBA

        f_DP_dec = Inode_Table(f_Inode_Table_addr, 1)
        f_DP_addr = (f_DP_dec * log_block_size * 2) + LBA

        f_File_name, f_Dir_name, f_Block_Group_num = [], [], []
        f_File_name, f_Dir_name, f_Block_Group_num = Directory_Entry(f_DP_addr)

        print(Dir_name[i], '-->', f_File_name)
        i+=1

    Block_Group_num, Dir_name = f_Block_Group_num, f_Dir_name