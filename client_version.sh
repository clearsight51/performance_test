#!/bin/bash

db="tsdtdb"
table="dt_client_versions"

version=`mysql -uroot -e "select version_code from ${db}.${table} where status=2;"`
if [ -z "${version}" ]; then
	# 数据库中没有可用的客户端版本
	mysql -uroot -e "insert into ${db}.${table} (version_id,version_name,version_code,version_path,md5_sum,status,type,created_at,updated_at) values ('2626d642-a73f-4574-b4a8-d9fccdc5dc9b','tsclient','1.0.17','/data/middleware/uploads/clients/b69c299a88974a0fef5815f2b60f312f.exe','0f1247d7ffffcbac06eacfda3561aaab',2,1,now(),now());"
else
	# 数据库中有可用的客户端版本
	version=`echo ${version} |awk '{print $2}'`
	# 判断版本号是不是1.0.17，如果不是要改成1.0.17
	if [ "${version}" = "1.0.17" ] ; then
		:
	else
		mysql -uroot -e "update ${db}.${table} set version_code='1.0.17' where status=2;"

	fi

fi

