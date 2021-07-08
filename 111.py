import logging
import paramiko
import time
import csv
import hashlib
import requests
import os
import os.path

#######需要修改的变量########
Dt_ip = '192.168.1.251'
Dt_ssh_port = 10622
Dt_ssh_username = 'root'
Dt_ssh_password = 'TsNac@1006$'

# 要导入的终端所在vlan的vlan id
vlan_id = 20

# jmeter docker机的宿主机ip地址, 已经ssh的用户名和密码
docker_host_ip = '192.168.1.223'
docker_host_ssh_username = 'root'
docker_host_ssh_password = 'admin@123'

# 运行jmeter master 的docker容器名
master = 'jmaster'

# jmeter docker宿主机上jmeter master容器中jmeter的bin目录用数据卷映射到宿主机上的目录路径
jmeter_master_bin_path = r'/var/jmeter-5.1.1/jmaster/apache-jmeter-5.1.1/bin'

# jmeter压力测试并发用户数，注意实际并发用户数是这个值乘以slave机的个数
user_threads = 110
# 压力测试执行时间  单位是秒
duration = 500
########不需要修改的变量#######
# 向准入控制端导入数据的导入工具名
tool = 'data_init'
# 向准入控制端导入数据的terminal.csv文件的文件名
import_terminal_csv_file = 'terminal.csv'
# 执行操作数据库命令的shell脚本文件名
shellfile = 'db.sh'
# 压力测试脚本模板名
scriptdemo_file = 'performance_test_demo.jmx'
# 压力测试脚本名
script_file = 'performance_test.jmx'
# 用工具data_init导入的用户都有一个默认密码abc@123, 这个密码用于性能测试脚本中用户登录的密码
user_init_password = 'abc@123'
# 定义计算终端指纹用的CPU序列号的base值，所有假终端的CPU序列号值在这个值的基础上依次+1
BASE_CPU_SERIAL = 1000000000000000
# 用于计算终端指纹用的产品序列号
PRODUCT_ID = "76481-OEM-0011903-01819"
# 用于计算终端指纹用的主板SN号
BASEBOARD_SERIAL = ".7R8MH2X.CN1296187H3038."
# 用于计算终端指纹用的Bios SN号
BIOS_SERIAL = "7R8MH2X"
# 定义一个全局变量来存放最后得到的测试脚本参数化用的参数csv文档中的数据
SCRIPT_PARMS = []
# 终端注册post请求的body
body = {
	"host_name":"andytest1",
	"os_info":{

	   "os_name": "Microsoft Windows 2020 Professional",
        "os_version": "5.1.2600",
        "os_manufacturer": "Microsoft Corporation",
        "os_configure": "Standalone Workstation",
        "os_component_type": "Multiprocessor Free"
	},
	"register_owner": "zhangsan",
    "register_group": "zhangsan",
    "product_id": "76481-OEM-0011903-01819",
    "install_time": "20120405124659.000000+480",
    "start_up_time": "20080620000023.375000+480",
    "manufacturer": "tangseng",
    "model": "TS D630                   ",
    "system_type": "X86-based PC",
    "baseboard_serial": ".7R8MH2X.CN1296187H3038.",
    "bios_serial": "7R8MH2X",
    "mem_serial": ",",
    "harddisk_serial": "",
    "nic_model": "[00000009] Broadcom NetXtreme 57xx Gigabit Controller,[00000014] Intel(R) Wireless WiFi Link 4965AGN",
    "display_model": "Mobile Intel(R) 965 Express Chipset Family,Mobile Intel(R) 965 Express Chipset Family",
    "mac": ",00:11:22:33:44:11",
    "cpu_model": "x86 Family 6 Model 15 Stepping 13",
    "cpu_serial": "BFEBFBFF000006111",
    "cpus": [
        {
            "cpu_id": "BFEBFBFF000006FD"
        }
    ],
    "bios_version": "Dell Inc. Phoenix ROM BIOS PLUS Version 1.10 A12, 20080620000000.000000+000",
    "window_dir": "C:\\WINDOWS",
    "system_dir": "C:\\WINDOWS\\system32",
    "startup_device": "\\Device\\HarddiskVolume2",
    "local": "0804",
    "time_zone": "",
    "mem": {
        "total": 2037,
        "free": 1319,
        "max_virtual_memory": 2047,
        "free_virtual_memory": 1991,
        "used_virtual_memory": 56
    },
    "page_position": "c:\\pagefile.sys",
    "region": "WORKGROUP",
    "patch": [
       "File 1",
       "File 1"
       ],
     "network_cards": [
        {
            "name": "Broadcom NetXtreme 57xx Gigabit Controller",
            "link_name": "",
            "status": "enabled",
            "nic_model": "[00000009] Broadcom NetXtreme 57xx Gigabit Controller",
            "mac": "00:11:22:33:44:11",
            "ip": "192.168.20.11"
        }
    ],
    "hyperV_info": "false",
    "sn": ".7R8MH2X.CN1296187H3038.",
    "device_code": "282ae005e49e11aea42fdaf91f46ee1b",
    "version_code": "1.0.17"
}
Logger_path = 'test.log'
# 文件日志的log级别
File_logger_level = logging.INFO
# 控制台log的级别
Console_logger_level = logging.DEBUG
# 控制paramiko模块本身的日志输出
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
logging.getLogger('terminal_performance_test').setLevel(logging.CRITICAL)

def get_logger():
    '''
    创建logger对象，并关联文件日志、控制台日志、日志格式、日志级别等。

    :return: 返回logger对象，在函数外面用这个logger对象的debug，info等方法来写log
    '''
    # 创建一个logger对象
    logger = logging.getLogger()
    # 创建一个handler，用于写入日志文件
    fh = logging.FileHandler(Logger_path,encoding='utf-8')
    # 再创建一个handler，用于输出到控制台
    ch = logging.StreamHandler()
    # 创建两个格式对象
    fh_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s-%(funcName)s-%(message)s')
    ch_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s-%(funcName)s-%(message)s')
    # 把文件操作符和格式关联
    fh.setFormatter(fh_formatter)
    ch.setFormatter(ch_formatter)
    # 把文件操作符和级别关联
    fh.setLevel(File_logger_level)
    logger.setLevel(Console_logger_level)
    # 把文件操作符和logger对象做关联
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
def put_paramsfile_to_host(params_file='params.csv', docker_host_ip = docker_host_ip ,docker_host_ssh_username = docker_host_ssh_username, docker_host_ssh_password = docker_host_ssh_password):
    '''
    上传jmeter参数文件params.csv到docker宿主机的jmeter master的bin数据卷目录，和所有jmeter slave的bin数据卷目录
    :param params_file:
    :param docker_host_ip:
    :param docker_host_ssh_username:
    :param docker_host_ssh_password:
    :return:
    '''
    # 查询docker宿主机数据卷目录/var/jmeter-5.1.1下的所有目录， jmaster是jmeter master的映射目录，jslaveXX是某个jmeter slave的映射目录
    search_path = '/var/jmeter-5.1.1'
    # 连接docker宿主机的ssh后台
    try:
        # 创建一个ssh对象
        client = paramiko.SSHClient()
        # 如果之前没有连接过的ip，会出现 Are you sure you want to continue connecting (yes/no)? yes
        # 自动选择yes
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # 连接服务器
        client.connect(docker_host_ip,
                       22,
                       docker_host_ssh_username,
                       docker_host_ssh_password)
    except Exception as e:
        logger.error('连接docker宿主机%s:%s的ssh后台失败，原因是：%s' % (docker_host_ip, 22, e))
        return
    else:
        logger.info('连接docker宿主机%s:%s的ssh后台成功' % (docker_host_ip, 22))

    # 执行列出宿主机上目录/var/jmeter-5.1.1/下所有目录的命令
    cmd = 'ls -l /var/jmeter-5.1.1/'
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
    except Exception as e:
        logger.error('ls -l /var/jmeter-5.1.1目录执行失败，原因是：%s' % e)
        return
    else:
        stdout, stderr = stdout.read().decode(), stderr.read().decode()
        if stderr:
            logger.error('ls -l /var/jmeter-5.1.1/目录执行失败，原因是：%s' % stderr)
            return
        else:
            logger.info('ls -l /var/jmeter-5.1.1/目录执行成功!')
            folder_lst = stdout.split('\n')
            logger.info('/var/jmeter-5.1.1/目录下的所有文件和目录：%s'%folder_lst)
            # 筛选目录，去除文件
            temp_lst = []
            for each in folder_lst:
                if each.startswith('d'):
                    temp_lst.append(each)
            folder_lst = temp_lst
            temp_lst = []
            # 去除其他字段的数据，只留目录名
            for each in folder_lst:
                temp_lst.append(each.split(' ')[-1])
            folder_lst = temp_lst
            temp_lst = []
            logger.info('/var/jmeter-5.1.1/目录下的所有目录的目录名为：%s'%folder_lst)
            # 筛选出master目录和所有slave目录
            for each in folder_lst:
                if 'master' in each or 'slave' in each:
                    temp_lst.append(each)
            folder_lst = temp_lst
            logger.info('筛选甄别只保留master目录和所有slave目录为：%s' % folder_lst)
    client.close()
    logger.debug('关闭docker宿主机%s:%s的ssh连接'%(docker_host_ip, 22))
    # 依次将paras.csv复制到master和所有slave目录下的apache-jmeter-5.1.1/bin目录
    # 计算slave机器的个数
    slave_num = 0
    for each in folder_lst:
        path = '/var/jmeter-5.1.1/' + each + '/apache-jmeter-5.1.1/bin/' + 'params.csv'
        # 连接docker宿主机的ssh后台
        try:
            ssh = paramiko.Transport((docker_host_ip, 22))
            ssh.connect(username=docker_host_ssh_username, password=docker_host_ssh_password)
            sftp = paramiko.SFTPClient.from_transport(ssh)
        except Exception as e:
            logger.error('连接docker宿主机%s:%s失败，原因是：%s' % (docker_host_ip, 22, e))
        else:
            logger.info('连接docker宿主机%s:%s成功！' % (docker_host_ip, 22))
        logger.debug('params.csv文件将上传到docker宿主机的%s' % path)
        try:
            sftp.put('params.csv', path)
        except Exception as e:
            logger.error('向docker宿主机上传文件params.csv失败，原因是：%s' % e)
            return
        else:
            logger.info('向docker宿主机上传文件params.csv成功！')
            if 'slave' in path:
                slave_num += 1
    ssh.close()
    logger.info('关闭docker宿主机%s:%s的ssh连接' % (docker_host_ip, 22))
    logger.info('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
    logger.info('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
    logger.info('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
    logger.info('@@@@@@@@@@总共有%s台master机和%s台slave机可用@@@@@@@@@@'%(1,slave_num))
    logger.info('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
    logger.info('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
    logger.info('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')






logger = get_logger()
put_paramsfile_to_host()