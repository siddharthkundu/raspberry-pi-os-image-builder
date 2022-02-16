#!/bin/sh
############################################################
# Help                                                     #
############################################################
Help()
{
   # Display Help
   echo "Shell script for installing AWS cloudwatch on Rpi devices."
   echo "Please run this script wiht admin rights"
   echo
   echo "Syntax: installAgent.sh [-u|g|d|a|s]"
   echo "options:"
   echo "u     Robot user (default pi)."
   echo "g     Log group name"
   echo "h     Print this Help."
   echo "d     Device name (ie R6923) (mandatory)"   
   echo "a     AWS user access key (mandatory)"
   echo "s     AWS user secret key (mandatory)"
   echo
}

############################################################
############################################################
# Main program                                             #
############################################################
############################################################

unset DeviceName
unset AccessKey
unset SecretKey
unset LogGroupName
# Set variables
User="pi"

############################################################
# Process the input options.                               #
############################################################
# Get the options
while getopts h:d:u:a:s:g: option; do

   case $option in
      h) # display Help
         Help
         exit;;
      u) # Enter a user name
         User=$OPTARG;;
      g) # Enter a user name
         LogGroupName=$OPTARG;;
      d) # Enter the device name
         DeviceName=$OPTARG;;
      a) # Enter the access key
         AccessKey=$OPTARG;;
      s) # Enter the secret key
         SecretKey=$OPTARG;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done


shift "$(( OPTIND - 1 ))"

if [ -z "$LogGroupName" ] ; then
        echo 'Missing -g' >&2
        exit 1
fi
if [ -z "$DeviceName" ] ; then
        echo 'Missing -d' >&2
        exit 1
fi

if [ -z "$AccessKey" ] ; then
        echo 'Missing -a' >&2
        exit 1
fi

if [ -z "$SecretKey" ] ; then
        echo 'Missing -s' >&2
        exit 1
fi




apt-get update --allow-releaseinfo-change
apt-get install unzip  -y
apt-get install collectd -y
apt-get install procps -y
apt-get install python3 -y
apt-get install python3-venv -y
apt-get install wget -y

mkdir temp
cp amazon-cloudwatch-agent.deb temp/
cd temp
#wget https://s3.amazonaws.com/aws-cli/awscli-bundle.zip
#unzip awscli-bundle.zip
#./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws

dpkg -i amazon-cloudwatch-agent.deb

cat <<EOF >/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.toml
[agent]
  collection_jitter = "0s"
  debug = false
  flush_interval = "1s"
  flush_jitter = "0s"
  hostname = ""
  interval = "60s"
  logfile = "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
  logtarget = "lumberjack"
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  omit_hostname = false
  precision = ""
  quiet = false
  round_interval = false

[inputs]

  [[inputs.cpu]]
    fieldpass = ["usage_idle"]
    interval = "60s"
    percpu = true
    totalcpu = true
    [inputs.cpu.tags]
      metricPath = "metrics"

  [[inputs.disk]]
    fieldpass = ["used_percent"]
    interval = "60s"
    tagexclude = ["mode"]
    [inputs.disk.tags]
      metricPath = "metrics"

  [[inputs.diskio]]
    fieldpass = ["write_bytes", "read_bytes", "writes", "reads"]
    interval = "60s"
    [inputs.diskio.tags]
      metricPath = "metrics"
      report_deltas = "true"

  [[inputs.logfile]]
    destination = "cloudwatchlogs"
    file_state_folder = "/opt/aws/amazon-cloudwatch-agent/logs/state"

    [[inputs.logfile.file_config]]
      file_path = "/home/pi/brain/logs/robot.log"
      from_beginning = true
      log_group_name = "${LogGroupName}"
      log_stream_name = "${DeviceName}_PiLogs"
      pipe = false
    [inputs.logfile.tags]
      metricPath = "logs"

  [[inputs.mem]]
    fieldpass = ["used_percent"]
    interval = "60s"
    [inputs.mem.tags]
      metricPath = "metrics"

  [[inputs.net]]
    fieldpass = ["bytes_sent", "bytes_recv", "packets_sent", "packets_recv"]
    interval = "60s"
    [inputs.net.tags]
      metricPath = "metrics"
      report_deltas = "true"

  [[inputs.socket_listener]]
    collectd_auth_file = "/etc/collectd/auth_file"
    collectd_security_level = "encrypt"
    collectd_typesdb = ["/usr/share/collectd/types.db"]
    data_format = "collectd"
    name_prefix = "collectd_"
    service_address = "udp://127.0.0.1:25826"
    [inputs.socket_listener.tags]
      "aws:AggregationInterval" = "60s"
      metricPath = "metrics"

  [[inputs.statsd]]
    interval = "10s"
    parse_data_dog_tags = true
    service_address = ":8125"
    [inputs.statsd.tags]
      "aws:AggregationInterval" = "60s"
      metricPath = "metrics"

  [[inputs.swap]]
    fieldpass = ["used_percent"]
    interval = "60s"
    [inputs.swap.tags]
      metricPath = "metrics"

[outputs]

  [[outputs.cloudwatch]]
    force_flush_interval = "60s"
    namespace = "CWAgent"
    profile = "AmazonCloudWatchAgent"
    region = "eu-west-1"
    shared_credential_file = "/home/cwagent/.aws/credentials"
    tagexclude = ["metricPath"]
    [outputs.cloudwatch.tagpass]
      metricPath = ["metrics"]

  [[outputs.cloudwatchlogs]]
    force_flush_interval = "5s"
    log_stream_name = "$HOSTNAME"
    profile = "AmazonCloudWatchAgent"
    region = "eu-west-1"
    shared_credential_file = "/home/cwagent/.aws/credentials"
    tagexclude = ["metricPath"]
    [outputs.cloudwatchlogs.tagpass]
      metricPath = ["logs"]

[processors]

  [[processors.delta]]
EOF



cat <<EOF >/etc/systemd/system/amazon-cloudwatch-agent.service
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT

# Location: /etc/systemd/system/amazon-cloudwatch-agent.service
# systemctl enable amazon-cloudwatch-agent
# systemctl start amazon-cloudwatch-agent
# systemctl | grep amazon-cloudwatch-agent
# https://www.freedesktop.org/software/systemd/man/systemd.unit.html

[Unit]
Description=Amazon CloudWatch Agent
After=network.target

[Service]
Type=simple
User=cwagent
Group=cwagent
ExecStart=/opt/aws/amazon-cloudwatch-agent/bin/start-amazon-cloudwatch-agent
KillMode=process
Restart=on-failure
RestartSec=60s

[Install]
WantedBy=multi-user.target

EOF
cat <<EOF >/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
        "agent": {
                "metrics_collection_interval": 60,
                "run_as_user": "root"
        },
        "logs": {
                "logs_collected": {
                        "files": {
                                "collect_list": [
                                        {
                                                "file_path": "/home/${User}/brain/logs/robot.log",
                                                "log_group_name": "${LogGroupName}",
                                                "log_stream_name": "${DeviceName}_PiLogs"
                                        }
                                ]
                        }
                },
                "metrics_collected": {
                         "emf": {}
                }
        },
        "metrics": {
                "metrics_collected": {
                        "collectd": {
                                "metrics_aggregation_interval": 60
                        },
                        "cpu": {
                                "measurement": [
                                        "cpu_usage_idle"
                                ],
                                "metrics_collection_interval": 60,
                                "resources": [
                                        "*"
                                ],
                                "totalcpu": true
                        },
                        "disk": {
                                "measurement": [
                                        "used_percent"
                                ],
                                "metrics_collection_interval": 60,
                                "resources": [
                                        "*"
                                ]
                        },
                        "diskio": {
                                "measurement": [
                                        "write_bytes",
                                        "read_bytes",
                                        "writes",
                                        "reads"
                                ],
                                "metrics_collection_interval": 60,
                                "resources": [
                                        "*"
                                ]
                        },
                        "mem": {
                                "measurement": [
                                        "mem_used_percent"
                                ],
                                "metrics_collection_interval": 60
                        },
                        "net": {
                                "measurement": [
                                        "bytes_sent",
                                        "bytes_recv",
                                        "packets_sent",
                                        "packets_recv"
                                ],
                                "metrics_collection_interval": 60,
                                "resources": [
                                        "*"
                                ]
                        },
                        "statsd": {
                                "metrics_aggregation_interval": 60,
                                "metrics_collection_interval": 10,
                                "service_address": ":8125"
                        },
                        "swap": {
                                "measurement": [
                                        "swap_used_percent"
                                ],
                                "metrics_collection_interval": 60
                        }
                }
        }
}
EOF


cat <<EOF >/var/lib/polkit-1/localauthority/50-local.d/10-cloud-agent.pkla
[Let ${User} to restart services]
Identity=unix-user:${User}
Action=org.freedesktop.systemd1.*
ResultAny=yes
ResultInactive=yes
ResultActive=yes


[Let cloud agent to restart services]
Identity=unix-user:cwagent
Action=org.freedesktop.systemd1.*
ResultAny=yes
ResultInactive=yes
ResultActive=yes
EOF

invoke-rc.d dbus restart
usermod -a -G $User cwagent

install -o cwagent -g cwagent -m 700 -d /home/cwagent
install -o cwagent -g cwagent -m 700 -d /home/cwagent/.aws

cat <<EOF >/home/cwagent/.aws/config
[profile AmazonCloudWatchAgent]
region = eu-west-1
output = json
EOF

cat <<EOF >/home/cwagent/.aws/credentials
[AmazonCloudWatchAgent]
aws_access_key_id = ${AccessKey}
aws_secret_access_key = ${SecretKey}
EOF


chown -R cwagent:cwagent /home/cwagent/.aws/
chmod 600 /home/cwagent/.aws/credentials
chown -R cwagent:cwagent /opt/aws
chsh -s /bin/bash cwagent



systemctl daemon-reload
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent
cd ..
rm -rf temp