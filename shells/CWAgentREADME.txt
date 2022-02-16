Add both deb file and shell script to a new directory.

Run
ls -al installCloudWatchAgent.sh

to look at the permissions of the shell script.

If the permissions are like this 
-rw-r--r-- 1 pi pi 11267 Jan 7 10:03 installCloudWatchAgent.sh

then run
chmod +x installCloudWatchAgent.sh 

Then 
ls -al installCloudWatchAgent.sh 
should return
-rwxr-xr-x 1 pi pi 11267 Jan 7 10:03 installCloudWatchAgent.sh

Install CW agent with
sudo ./installCloudWatchAgent.sh -g growx-robots-horizontal -d R69XX -a xxxxxxx -s yyyyy

where xxxx is the access_key and yyyy is the secret key.

Then run
ps -ef | grep agent

to check if there is a new user added.

Confirm if the CW agent is running by checking the logs with
tail -f /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log



