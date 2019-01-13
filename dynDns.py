import boto3
import configparser
import logging
import requests
from time import sleep

# Intialize script logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Create a log file handler
FileHandler = logging.FileHandler('dyn.log')
FileHandler.setLevel(logging.INFO)

# Create a logger format
formatter = logging.Formatter('%(module)s:%(levelname)s:%(asctime)s - %(message)s')
FileHandler.setFormatter(formatter)

logger.addHandler(FileHandler)


# Intialize Config and Grab AWS ZoneID and Domain to Manage the file
Config = configparser.ConfigParser()
Config.read("dynConfig")

ZONEID = Config["Settings"]["ZoneId"]
DOMAIN = Config["Settings"]["Domain"]

Session = boto3.Session(profile_name="dev")
route53 = Session.client("route53")

def GetWanIp(Service="https://ifconfig.me/ip"):
    """
        Sends requests to the specified service for Wan IP information
    """
    Response = requests.get(Service)
    Response.raise_for_status()

    return Response.text


# Begin Route53 Functions
def CheckStatus(ChangeRequest, ExpectedStatus, FailCount=30):
    """
        This function checks the status of a change every 2 seconds until the status changes from PENDING.
        :FailCount: Is the allowed number of checks before breaking the while loopself.
            - Default is 30 tries which means the change exceeded 1 minute to take effect
    """
    # Counting mechanism for the amount of attempted change status checks.
    CheckCount = 0
    while True:
        # break if CheckCount >= FailCount
        if CheckCount >= FailCount:
            logger.error()
            raise Exception("Change exceeded maximum check count")

        Response = route53.get_change(Id=ChangeRequest["ChangeInfo"]["Id"])
        Status = Response["ChangeInfo"]["Status"]

        if Status == ExpectedStatus:
            logger.info("Change status {}".format(Status))
            break
        else:
            logger.debug("Change Status {}, checking again in 2 seconds.".format(Status))
            CheckCount += 1
            sleep(2)



def GetRecordInfo(Record):
    """
        This function will get a specific record set based on request
        Pass a dictionary with Name and Type and get the AWS record set details in return
        :Record: Dict - Should contain a record type and name. \
            Record = {"Type": "A", "Name": "example.com"}
    """
    Response = route53.list_resource_record_sets(HostedZoneId=ZONEID)

    # Loop through record sets for the requested record.
    for AwsRecord in Response["ResourceRecordSets"]:
        # :rType: Record Type
        # :rName: Record Name
        rType = AwsRecord["Type"]
        rName = AwsRecord["Name"]

        # Look for the Requested record set by Name and Type(Default="A")
        if rType == Record.get("Type", "A").upper() and "{}.".format(Record["Name"]) == rName:
            return AwsRecord
    else:
        Name = Record.get("Type", "A").upper()
        Type = Record["Name"]
        logger.error("No {} record found for {} in the specified zone.".format(Name, Type))


def UpdateRecord(Record):
    """
        This function will update an A record  in route53
        :Record: Dict - Should contain a record type and name. \
            Record = {"Name": "example.com", "TTL": 300, "IP": "127.0.0.1"}
    """
    Template = {
        "Comment": Record.get("Comment", "Automatic DNS update"),
                "Changes": [
                    {
                        "Action": "UPSERT",
                        "ResourceRecordSet": {
                            "Name": "{}.".format(Record.get("Name")),
                            "Type": "A",
                            "TTL": Record.get("TTL", 300),
                            "ResourceRecords": [
                                {
                                    "Value": "{}".format(Record.get("IP"))
                                },
                            ],
                        }
                    },
                ]
            }

    # Send update requests to AWS
    Response = route53.change_resource_record_sets(HostedZoneId=ZONEID, ChangeBatch=Template)

    # Check status of requested update
    CheckStatus(Response, ExpectedStatus="INSYNC")


def run():

    try:
        WanIp = GetWanIp()
        DomainRecord = GetRecordInfo({"Name": DOMAIN})
        DomainIp = DomainRecord["ResourceRecords"][0]["Value"]

        # If the domain A record and the public IP do not match call update, else log no change and exit.
        if WanIp != DomainIp:
            UpdateRecord({"Name": DOMAIN, "IP": WanIp})
            logger.info("Updated {}-->{}".format(WanIp, DomainIp))
        else:
            logger.info("No Update Required {}".format(WanIp))

    except Exception as e:
         logger.critical("An exception has occured! {}".format(e))

    exit()

if __name__ == "__main__":
    run()
