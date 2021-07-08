import logging
import paramiko
import time
import csv
import hashlib
import requests

#######需要修改的变量########
Dt_ip = '192.168.1.251'
Dt_ssh_port = 10622
Dt_ssh_username = 'root'
Dt_ssh_password = 'TsNac@1006$'

# 要导入的终端所在vlan的vlan id
vlan_id = 20

########不需要修改的变量#######

# 向准入控制端导入数据的terminal.csv文件的文件名
import_terminal_csv_file = 'terminal.csv'
# 执行操作数据库命令的shell脚本文件名
shellfile = 'db.sh'
# 查询数据库中客户端版本是不是1.0.17，不是则修改的shell 脚本
client_version_sh = 'client_version.sh'

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

def put_file_to_dt(ip=Dt_ip, port=Dt_ssh_port, username=Dt_ssh_username, password=Dt_ssh_password, csv_name=import_terminal_csv_file):
    '''
    向准入控制端上传用于生产假终端数据的工具data_init和终端数据csv文件 terminal.csv
    :param ip:
    :param port:
    :param username:
    :param password:
    :param tool_name:
    :param csv_name:
    :return:
    '''
    logger.debug('========================开始向准入控制端上传：终端数据表%s======================'%(import_terminal_csv_file))
    # 连接准入控制端的ssh后台
    try:
        ssh = paramiko.Transport((Dt_ip, Dt_ssh_port))
        ssh.connect(username=Dt_ssh_username, password=Dt_ssh_password)
        sftp = paramiko.SFTPClient.from_transport(ssh)
    except Exception as e:
        logger.error('连接准入控制端%s:%s失败，原因是：%s'%(Dt_ip, Dt_ssh_port, e))
    else:
        logger.info('连接准入控制端%s:%s成功！'%(Dt_ip, Dt_ssh_port))


    # 上传工具terminal.csv文件
    try:
        sftp.put(import_terminal_csv_file, import_terminal_csv_file)
    except Exception as e:
        logger.error('向准入控制端上传文件%s失败，原因是：%s'%(import_terminal_csv_file, e))
    else:
        logger.info('向准入控制端上传文件%s成功！'%import_terminal_csv_file)
    finally:
        ssh.close()
        logger.info('关闭准入控制端%s:%s的ssh连接'%(Dt_ip, Dt_ssh_port))
    logger.debug('========================向准入控制端上传：终端数据表%s结束======================'%(import_terminal_csv_file))
    time.sleep(2)

def import_terminal_to_dt(ip=Dt_ip, port=Dt_ssh_port,username=Dt_ssh_username,password=Dt_ssh_password):
    '''
    1. 赋予工具data_init可执行权限
    2. 执行命令./data_init -t terminal -f terminal.csv来导入终端信息
    :param ip:
    :param port:
    :param username:
    :param password:
    :return:
    '''

    logger.debug('========================开始向准入控制端导入终端数据======================')
    # 连接准入控制系统的ssh后台
    try:
        # 创建一个ssh对象
        client = paramiko.SSHClient()
        # 如果之前没有连接过的ip，会出现 Are you sure you want to continue connecting (yes/no)? yes
        # 自动选择yes
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # 连接服务器
        client.connect(ip,
                       port,
                       username,
                       password)
    except Exception as e:
        logger.error('连接准入控制端%s:%s的ssh后台失败，原因是：%s'%(ip, port, e))
        exit()
    else:
        logger.info('连接准入控制端%s:%s的ssh后台成功'%(ip, port))
    # 从/data目录移动terminal.csv文件到/dt/curr/middleware目录
    cmd = 'mv -f /data/terminal.csv /dt/curr/middleware'
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
    except Exception as e:
        logger.error('从/data目录移动terminal.csv文件到/dt/curr/middleware目录失败，原因是：%s' % e)
        exit()
    else:
        logger.info('从/data目录移动terminal.csv文件到/dt/curr/middleware目录成功')
    # 把工作目录从/data目录转到/dt/curr/middleware目录
    cmd = 'cd /dt/curr/middleware'
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
    except Exception as e:
        logger.error('把工作目录从/data目录转到/dt/curr/middleware目录失败，原因是：%s' % e)
        exit()
    else:
        logger.info('把工作目录从/data目录转到/dt/curr/middleware目录成功')
    # 执行赋予data_init文件执行权限的命令
    cmd = 'chmod +x data_init'
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
    except Exception as e:
        logger.error('赋予文件data_init可执行权限失败，原因是：%s' % e)
        exit()
    else:
        logger.info('赋予文件data_init可执行权限成功!' )


    # 执行增量导入终端的命令
    cmd = 'cd /dt/curr/middleware ; ./data_init  -t terminal -term_type 2 -f %s'%import_terminal_csv_file
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
    except Exception as e:
        logger.error('执行导入终端命令失败，原因是：%s'%e)
        exit()
    else:
        stdout,stderr = stdout.read().decode(),stderr.read().decode()
        if  stderr:
            logger.error('执行导入终端命令失败，原因是：%s' % stderr)
            exit()
        else:
            if 'error' in stdout.lower():
                logger.error('执行导入终端命令失败，原因是：%s文件有错误：%s'%(import_terminal_csv_file,stdout))
                exit()
            else:
                logger.info('导入终端成功!')

    client.close()
    logger.info('关闭准入控制端%s:%s的ssh连接'%(ip, port))
    logger.debug('========================向准入控制端导入终端数据结束======================')
    time.sleep(2)

def get_csvfile_column(csvfile, column_num, start_line):
    '''
    获得一个csv文件的某一列数据，并将这列数据作为list return
    :param csvfile:
    :param column_num:  指定想获取哪列数据，从1开始
    :param start_line:  指定从那行开始获取，从1开始
    :return: 这列数据的一个列表
    '''
    # 打开csv文件
    try:
        csv_file = open(csvfile, mode='r', encoding='utf-8')
    except Exception as e:
        logger.error('打开文件%s时失败，原因是：%s'%(csvfile, e))
        ex = Exception('打开%s时失败'%csvfile)
        raise  ex
        exit()
    else:
        logger.debug('打开文件%s成功'%csvfile)
    # 获得文件句柄
    reader = csv.reader(csv_file)
    start = start_line - 1
    line_num = 1
    value_lst = []
    for eachline in reader:
        if line_num > start:
            value_lst.append(eachline[column_num-1])
        line_num += 1
    csv_file.close()
    return value_lst

def operator_db(csvfile=import_terminal_csv_file, shellfile=shellfile, ip=Dt_ip, port=Dt_ssh_port, username=Dt_ssh_username, password=Dt_ssh_password, client_version_shellfile=client_version_sh):
    '''
    1. 通过shell脚本，清空表dt_client_device中的数据
    2. 通过shell脚本，根据terminal.csv中终端的ip地址，找到dt_device_port表中的所有终端并添加vlan_id字段的值
    :return:
    '''
    logger.debug('========================开始从终端数据表%s中分析出所有导入的终端的ip列表======================'%csvfile)
    # 从terminal.csv文件中获得所有终端的ip的一个列表
    try:
        ip_lst = get_csvfile_column(csvfile,1,2)
    except Exception as e:
        logger.error('从terminal.csv文件中获取所有终端ip地址的列表失败，原因是%s'%e)
        exit()
    else:
        logger.info('从terminal.csv文件中获取所有终端ip地址的列表: %s'%ip_lst)
    logger.debug('========================从终端数据表%s中分析出所有导入的终端的ip列表结束======================'%csvfile)

    # 用变量vlan_id替换db.sh中的{kang}; 用ip_lst中的终端ip替换db.sh中的{kai}
    logger.debug('========================开始替换shell脚本模板文件%s中的数据======================'%shellfile)
    ips_str = ' '.join(ip_lst)
    try:
        with open(shellfile, newline=None, encoding='utf-8') as f1, open('newdb.sh', 'w', newline='\n', encoding='utf-8') as f2:
            for each in f1:
                each1 = each.replace('{kang}', str(vlan_id))
                each2 = each1.replace('{kai}', ips_str)
                f2.write(each2)
            f2.flush()
            f1.close()
            f2.close()
    except Exception as e:
        logger.error('打开操作数据库的shell脚本文件%s并替换vlan_id和终端ip时失败，原因是：%s'%(shellfile, e))
    else:
        logger.info('打开操作数据库的shell脚本文件%s并替换vlan_id和终端ip成功'%shellfile)
    logger.debug('========================替换shell脚本模板文件%s中的数据完毕，并生成正式shell脚本文件%s======================'%(shellfile, 'newdb.sh'))

    # 将修改完的操作数据库shell脚本文件newdb.sh和修改数据库中客户端版本的shell脚本client_version.sh上传到准入控制端
    logger.debug('==============================开始将生成的正式shell脚本%s上传到准入控制端================================='%'newdb.sh')
    # 连接准入控制端的ssh后台
    try:
        ssh = paramiko.Transport((Dt_ip, Dt_ssh_port))
        ssh.connect(username=Dt_ssh_username, password=Dt_ssh_password)
        sftp = paramiko.SFTPClient.from_transport(ssh)
    except Exception as e:
        logger.error('连接准入控制端%s:%s失败，原因是：%s'%(Dt_ip, Dt_ssh_port, e))
    else:
        logger.info('连接准入控制端%s:%s成功！'%(Dt_ip, Dt_ssh_port))

    # 上传工具正式shell脚本文件
    try:
        sftp.put('newdb.sh', 'newdb.sh')
    except Exception as e:
        logger.error('向准入控制端上传文件%s失败，原因是：%s'%('newdb.sh', e))
    else:
        logger.info('向准入控制端上传文件%s成功！'%'newdb.sh')
    # 上传修改客户端版本号的shell脚本文件
    try:
        sftp.put(client_version_sh, client_version_sh)
    except Exception as e:
        logger.error('向准入控制端上传文件%s失败，原因是：%s'%(client_version_sh, e))
    else:
        logger.info('向准入控制端上传文件%s成功！'%client_version_sh)
    finally:
        ssh.close()
        logger.info('关闭准入控制端%s:%s的ssh连接'%(Dt_ip, Dt_ssh_port))
    logger.debug('==============================上传shell脚本%s和%s完毕================================='%('newdb.sh',client_version_sh))
    time.sleep(2)

    logger.debug('========================开始执行shell脚本%s的命令清空表dt_client_device中的数据，向dt_device_port表中的所有终端并添加vlan_id字段的值======================'%'newdb.sh')
    # 连接准入控制系统的ssh后台
    try:
        # 创建一个ssh对象
        client = paramiko.SSHClient()
        # 如果之前没有连接过的ip，会出现 Are you sure you want to continue connecting (yes/no)? yes
        # 自动选择yes
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # 连接服务器
        client.connect(ip,
                       port,
                       username,
                       password)
    except Exception as e:
        logger.error('连接准入控制端%s:%s的ssh后台失败，原因是：%s' % (ip, port, e))
        exit()
    else:
        logger.info('连接准入控制端%s:%s的ssh后台成功' % (ip, port))

    # 执行赋予newdb.sh文件可执行权限的命令
    cmd = 'chmod +x newdb.sh'
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
    except Exception as e:
        logger.error('赋予文件%s可执行权限失败，原因是：%s' %('newdb.sh', e))
        exit()
    else:
        stdout, stderr = stdout.read().decode(), stderr.read().decode()
        if stderr:
            logger.error('赋予文件%s可执行权限失败,原因是：%s' % ('newdb.sh', stderr))
            exit()
        else:
            logger.info('赋予文件%s可执行权限成功!' % 'newdb.sh')

    # 执行newdb.sh脚本来清空表dt_client_device中的数据，向dt_device_port表中的所有终端并添加vlan_id字段的值
        cmd = './newdb.sh'
        try:
            stdin, stdout, stderr = client.exec_command(cmd)
        except Exception as e:
            logger.error('执行脚本%s失败，原因是：%s' %('newdb.sh', e))
            exit()
        else:
            stdout, stderr = stdout.read().decode(), stderr.read().decode()
            if stderr:
                logger.error('执行脚本%s失败,原因是：%s' % ('newdb.sh', stderr))
                exit()
            else:
                logger.info('执行脚本%s成功!' % 'newdb.sh')
    logger.debug('========================shell脚本%s执行完毕！======================'%'newdb.sh')
    time.sleep(1)
    # 执行赋予client_version.sh文件可执行权限的命令
    cmd = 'chmod +x %s'%client_version_sh
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
    except Exception as e:
        logger.error('赋予文件%s可执行权限失败，原因是：%s' % (client_version_sh, e))
        exit()
    else:
        stdout, stderr = stdout.read().decode(), stderr.read().decode()
        if stderr:
            logger.error('赋予文件%s可执行权限失败,原因是：%s' % (client_version_sh, stderr))
            exit()
        else:
            logger.info('赋予文件%s可执行权限成功!' % client_version_sh)

        # 执行client_version.sh脚本来检查数据库中客户端的版本是不是1.0.17
        cmd = './%s'%client_version_sh
        try:
            stdin, stdout, stderr = client.exec_command(cmd)
        except Exception as e:
            logger.error('执行脚本%s失败，原因是：%s' % (client_version_sh, e))
            exit()
        else:
            stdout, stderr = stdout.read().decode(), stderr.read().decode()
            if stderr:
                logger.error('执行脚本%s失败,原因是：%s' % (client_version_sh, stderr))
                exit()
            else:
                logger.info('执行脚本%s成功!' % client_version_sh)
    logger.debug('========================shell脚本%s执行完毕！======================' % client_version_sh)
    time.sleep(2)

def device_register(terminal_ip, terminal_mac, username, product_id, cpu_serial, baseboard_serial, bios_serial):
    '''
    根据参数给定的数据拼接终端注册api请求的请求body来注册终端；
    注册时的device_code指纹时根据product_id, cpu_serial, baseboard_serial, bios_serial这个四个值拼接字符串的md5值算出来的
    :param terminal_ip:
    :param terminal_mac:
    :param username:
    :param product_id:
    :param cpu_serial:
    :param baseboard_serial:
    :param bios_serial:
    :return: 返回cpu序列号和终端指纹的字段      {'cpu_sn':cpu_serial, 'device_code':device_code}
    '''
    # 终端注册请求路径
    path = '/client/terminal_info'
    # 拼接url
    url = 'https://{ip}:{port}{path}'.format(ip=Dt_ip, port='443', path=path)
    logger.debug('终端注册请求的url为：%s'%url)
    headers = {'Content-Type': 'application/json'}
    body['register_owner'] = username
    body["register_group"] = username
    logger.debug('替换请求body中的用户名为：%s'%username)
    body["network_cards"][0]["mac"] = terminal_mac
    logger.debug('替换请求body中的mac地址为：%s'%terminal_mac)
    body["network_cards"][0]["ip"] = terminal_ip
    logger.debug('替换请求body中的ip地址为：%s'%terminal_ip)
    body["product_id"] = product_id
    logger.debug('替换请求body中的产品序列号为：%s' % product_id)
    body["cpu_serial"] = cpu_serial
    logger.debug('替换请求body中的CPU序列号为：%s'%cpu_serial)
    body["baseboard_serial"] = baseboard_serial
    logger.debug('替换请求body中的主板SN号为：%s'%baseboard_serial)
    body["bios_serial"] = bios_serial
    logger.debug('替换请求body中的bios SN号为：%s'%bios_serial)
    # 根据产品序列号，CPU序列号，主板SN，bios SN来计算终端设备的device_code
    md5 = hashlib.md5()
    # 拼接这个四个值
    device_str = product_id + cpu_serial + baseboard_serial + bios_serial
    device_byte = device_str.encode("utf-8")
    # 用md5计算设备指纹
    md5.update(device_byte)
    device_code = md5.hexdigest()
    logger.debug('md5计算出来的设备指纹为--->%s'%device_code)
    body["device_code"] = device_code
    logger.debug('替换请求body中的device_code为：%s' % device_code)
    json = body
    logger.debug('请求的body为  -------->  %s'%json)
    requests.adapters.DEFAULT_RETRIES = 5  # 增加重连次数
    s = requests.session()
    logger.debug('开始发送终端注册请求来注册终端%s'%terminal_ip)
    try:
        response = s.post(url=url, headers=headers, json=json,verify=False)
    except Exception as e:
        logger.error('发送终端注册请求失败，原因是：%s'%e)
        exit()
    else:
        logger.info('发送终端注册请求成功！')
        logger.debug('返回码为：%s'%response.status_code)
        logger.debug('返回的json为：%s'%response.json())
        # 当返回码为500时，说明请求中带的device_code和计算出的device_code不一致，需要修改并记录这个device_code后再发一次终端注册请求
        if response.status_code == 200  :
            logger.info('终端%s注册成功！'%terminal_ip)
        else:
            logger.error('终端%s注册失败'%terminal_ip)
            exit()
    logger.debug('返回%s给调用函数'%{'cpu_sn':cpu_serial, 'device_code':device_code})
    return {'cpu_serial':cpu_serial, 'device_code':device_code}

def write_csv(filename, title_lst):
    '''
    向csv文件写数据
    :param filename:
    :param title_lst: csv文件第一行的title的列表
    :return:
    '''
    try:
        csvfile = open(filename, 'w', newline='', encoding="utf-8")
        writer = csv.writer(csvfile)
        logger.info('用w方式打开csv文件%s成功'%filename)
    except Exception as e:
        logger.error('用w方式打开csv文件%s失败，原因是：%s' % (filename, e))
    # 写入csv文件的标题行
    writer.writerow(title_lst)
    logger.debug('向csv文件%s写入标题行%s'%(filename, title_lst))
    # 写入各行数据
    line_num = 1
    for eachline in SCRIPT_PARMS:
        writer.writerow(eachline)
        logger.debug('向csv文件%s写入第%s行数据：%s'%(filename, line_num, eachline))
        line_num += 1

    csvfile.close()
    logger.debug('保存并关闭csv文件%s'%filename)

def get_csv_params_file(csvfile_r=import_terminal_csv_file, csvfile_w='terminal_performance.csv'):
    '''
    1. 先从data_init导入数据用的terminal.csv文件中得到终端的ip、mac、用户名；
    2. 然后根据终端ip、mac、用户名、全局变量PRODUCT_ID 、 BASEBOARD_SERIAL 、BIOS_SERIAL、
    BASE_CPU_SERIAL（用于每个终端自增1来生成每个终端不一样的CPU序列号）作为参数调用函数
    device_register注册终端并计算得到每个终端的device_code指纹；
    3. 最后用终端ip、mac、用户名、全局变量user_init_password、每个终端自增1得到的cpu_sn、device_code  生成性能测试参数化用的csv参数文件terminal_performance.csv
    :return:
    '''

    # 从terminal.csv文件中分析出每个终端的ip、mac、用户名
    # 打开terminal.csv文件
    try:
        datainit_csvfile = open(csvfile_r, mode='r', encoding='utf-8')
    except Exception as e:
        logger.error('打开文件%s时失败，原因是：%s'%(csvfile_r, e))
        exit()
    else:
        logger.debug('打开文件%s成功'%csvfile_r)
    # 获得文件句柄
    reader = csv.reader(datainit_csvfile)
    line_num = 0
    value_lst = []
    for eachline in reader:  # 在terminal.csv文件中的每一行
        if line_num > 0:
            # 跳过csv文件第一行标题行，从第二行开始，每一行取这行的前三列数据(ip,mac,用户名)组成一个列表，然后把这个列表append到value_lst大列表中
            value_lst.append([eachline[0],eachline[1],eachline[2]])
            logger.debug('从%s中读取第%s行数据, 提取出一个列表%s, 将这个列表添加到value_lst大列表中'%(csvfile_r, line_num, [eachline[0],eachline[1],eachline[2]]))
        line_num += 1
    datainit_csvfile.close()
    logger.debug('关闭%s文件'%csvfile_r)
    logger.debug('从%s中分析得到的所有数据为：%s'%(csvfile_r, value_lst))
    # 将value_lst列表中每个子列表中的mac地址加上:格式
    for each in value_lst:
        if ':' not in each[1] :
            logger.debug('mac地址%s不带:，后面的程序将把他修改为:分割格式'%each[1])
            num = 0
            tmp = ''
            for i in each[1]:
                if num % 2 == 0 and num:
                    tmp = tmp + ':'
                tmp = tmp + i
                num += 1
            # each[1]是没有:的mac地址
            # tmp是有:格式的mac地址
            each[1] = tmp
        else:
            logger.debug('mac地址%s已经是:分割格式，不需要修改'%each[1])
    logger.debug('把mac地址格式加上:后的数据为：%s'%value_lst)
    # 工具从terminal.csv文件读取的数据并调用函数device_register来向准入准入控制端注册终端并且将相关参数写入SCRIPT_PARAMS全局列表变量
    logger.info('开始逐个从中读取每个终端的信息，并调用函数device_register来向控制端发注册请求；并且添加终端的其他信息(password,cpu_sn ,device_code)来形成性能测试脚本参数文件的数据'%value_lst)
    terminal_num = 1
    for each_terminal in value_lst:
        terminal_ip = each_terminal[0]
        terminal_mac = each_terminal[1]
        username = each_terminal[2]
        password = user_init_password
        product_id = PRODUCT_ID
        cpu_serial = str(BASE_CPU_SERIAL + terminal_num)
        baseboard_serial = BASEBOARD_SERIAL
        bios_serial = BIOS_SERIAL
        logger.debug('《第%s台终端的ip是%s,  mac是%s,  用户名是%s,  密码是%s,  产品序列号是%s,  CPU序列号是%s,  主板SN号是%s,  bios SN号是%s》'%(terminal_num, terminal_ip, terminal_mac, username, password, product_id, cpu_serial, baseboard_serial, bios_serial))
        logger.debug('调用device_register函数来注册终端')
        cpu_serial_device_code_dic = device_register(terminal_ip=terminal_ip, terminal_mac=terminal_mac, username=username, product_id=product_id, cpu_serial=cpu_serial, baseboard_serial=baseboard_serial, bios_serial=bios_serial)
        cpu_serial = cpu_serial_device_code_dic['cpu_serial']
        device_code = cpu_serial_device_code_dic['device_code']
        logger.debug('这台终端使用的CPU序列号为%s, 计算出的设备指纹为%s'%(cpu_serial, device_code))
        SCRIPT_PARMS.append([terminal_ip, terminal_mac, username, password, cpu_serial, device_code])
        logger.debug('将该终端的信息%s写入全局变量SCRIPT_PARMS'%[terminal_ip, terminal_mac, username, password, cpu_serial, device_code])
        terminal_num += 1
    logger.info('所有%s台终端已经全部注册完毕！！！！！！！！！！！！！！！！！！！！！'%str(terminal_num-1))
    logger.info('测试脚本参数文件待写入的内容为：%s'%SCRIPT_PARMS)
    # 调用函数write_csv将测试脚本的参数写入csv文件
    write_csv('params.csv', ['ip', 'mac', 'username', 'password', 'cpu_serial', 'device_code'])
    logger.info('性能测试脚本使用的参数化文件%s生成完毕，一共%s条数据'%('params.csv', str(terminal_num-1)))


if __name__ == '__main__':
    # 生成配置好的logger实例，之后写log就用logger.debug等
    logger = get_logger()
    # 上传所需文件到控制端
    put_file_to_dt()
    # 用data_init向控制端导入假终端数据
    import_terminal_to_dt()
    # 由于是用工具导入的假终端，需要修改相关数据库中的数据完善终端信息，以使终端注册可以成功，同时把数据库中客户端的版本号改为1.0.17
    operator_db()
    # 执行终端注册请求，并把相关信息收集形成最终性能测试脚本参数化使用的params.csv参数文件
    get_csv_params_file()
