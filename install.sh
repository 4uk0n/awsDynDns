#!/bin/bash

# Default Variables
aws_directory=~/.aws/
python_dir=`command -v python3`
user='whoami'
# Check if python3 exists
if [[ ! -z "$pythondir" ]]; then
    # If python exists install requirements.txt
    echo "Python found installing script requirements"
    $python_dir -m pip install -r requirements.txt
else
    echo -e "Unable to find Python >= 3.5.3  \033[0;31mNOT\033[0m installed."
    echo "Install the required Python version and restart the setup."
    echo "Exiting setup."
    exit
fi



# Check if an .aws directory already exists
# If not then create one with a config & credentials file for boto3
if [ ! -e $aws_directory ]; then
  echo "No ~/.aws directory creating directory and appropriate files."
  # Makes hidden directory in users folder
  mkdir $aws_directory

  # Request default AWS region
  read -p "What is your default AWS region(us-east-1)? " region

  # Echo contents into ~/.aws/config file
  cat >> $aws_directory/config <<EOL
[default]
region = $region
output = json
EOL

 echo "Please proved the required AWS keys."
 echo -e "You're encouraged to use a IAM user with \033[0;31mLIMITED\033[0m permissions."

 read -p "AWS Access Key ID: " aws_access_key_id
 read -p "AWS Secret Access Key ID: " aws_secret_access_key

  # Echo contents into ~/.aws/credentials file
 cat >> $aws_directory/credentials <<EOL
[default]
aws_access_key_id = ${aws_access_key_id}
aws_secret_access_key = ${aws_secret_access_key}
EOL
fi

# create dynConfig
read -p "What is the AWS ZoneId for the domain being updated? " zoneid
read -p "What is the domain being updated? " domain

cat >> $(pwd)/dynConfig <<EOL
[Settings]
ZoneId=$zoneid
Domain=$domain
EOL

# Setup cron job
echo "Setting up Cron Job to check hourly."
(crontab -u $(whoami) -l; echo "*/15 * * * * cd $(pwd)/ && $python_dir $(pwd)/dynDns.py" ) | crontab -u $(whoami) -

echo "Setup complete, check the dyn.log file to ensure the script is running without error."
