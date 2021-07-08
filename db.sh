#!/bin/bash
echo "Andy start to operator db"
# empty table: dt_client_device
mysql -uroot -e "truncate tsdtdb.dt_client_device"
# get vlan_id
vlanid={kang}
terminal_ips=({kai})
for i in ${terminal_ips[@]}
do
    echo $i
	mysql -uroot -e "use tsdtdb; update dt_device_port set vlan_id=(select vlan_id from dt_vlan where label=$vlanid) where ip='$i';"
done