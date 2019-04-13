'''
Author: Prasad Pai, Senior Solutions Architect, NA-SD.

The script takes a yaml file as the input and creates the configurations in bulk. The hostnames should be passed in the YAML file, along with the rules.

Disclaimer:
1) Not to be shared with the customers. Currently for internal consumption only.

'''
#!/usr/bin/env python
#Importing the libraries
import requests
import json
from akamai.edgegrid import EdgeGridAuth
from urllib.parse import urljoin
from openpyxl import load_workbook
import re
import openpyxl, pprint
import sys
import argparse
from datetime import datetime
import calendar
import yaml
from papifunctions import createNewConfig,addHostNames,updateConfigRules,creatCertEnrollment,activateConfigStaging,activateConfigProduction,createCPCodes,getCPCodes,createSecureEdgeHostname,checkCertEnrollment,getDVChallenges
import time
import route53
# Main Program
if __name__ == '__main__':
    print("Loading up!!! We are now reading your input, please give us a moment...")
    counthosts=0
    # Step 1: Consume the YAML file
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--config", help="yaml file input")
    args=parser.parse_args()
    inputfilename=args.config
    # Extract the account/contract details from the YAML file.
    yamlhandle=yaml.load(open(inputfilename))
    contractid = yamlhandle['OnboardConfig']['Account'][0]
    groupid=yamlhandle['OnboardConfig']['Account'][1]
    shortcontractid=contractid.split('_')
    shortcontractid=shortcontractid[1]
    shortgroupid=groupid.split('_')
    shortgroupid=shortgroupid[1]
    productid=yamlhandle['OnboardConfig']['ProductId'][0]
    # Extract the Hostnames from the YAML file.
    hostorigincomponent=yamlhandle['OnboardConfig']['Host-Origin']
    #Extract the email id where notification emails should be sent.
    emailnotify=yamlhandle['OnboardConfig']['notify'][0]
    #To create the SSL cert request or not?
    certdecision = yamlhandle['OnboardCertconfig']['Action']
    certcn = yamlhandle['OnboardCertconfig']['CN']
    certaltnames=yamlhandle['OnboardCertconfig']['Altnames']
    # Let us first put in the cert request, as that takes a longer time...
    if certdecision == True:
      print("Step 1: Certificate creation job in progress. Please note that the normal certification creation and deployment ETA is approximately 4 hours.")
      result=creatCertEnrollment(shortcontractid,certcn,certaltnames)
      if "403" not in result.text:
        print("Looks like the DV SSL Certificate was created successfully. In ~5-10 minutes, we should have the DV challenges ready for you.")
        # enrollment ID stored in the below variable.
        enrollmentidcatch=re.search('(.*)\/enrollments\/([0-9]{1,})\/changes\/([0-9]{1,})"(.*)',str(result.text))
        enrollmentID=enrollmentidcatch.group(2)
        changeID=enrollmentidcatch.group(3)
        print("To check the status of your certificate, use this enrollment ID:"+enrollmentID+" and the change ID:"+changeID+"")
        dcv="FALSE"
        while dcv == "FALSE":
          #Waiting for 5 mins for the DV challenges to be ready. 
          time.sleep(30)
          #Now, retrieve the DV challenges.
          retreiveDVchallenges=getDVChallenges(enrollmentID)
          #print(retreiveDVchallenges)
          if retreiveDVchallenges == "success":
            dcv="TRUE";
          else:
            print("Looks like the DCV challenges are not ready yet! We will keep checking every 5 minutes.")
        user_dcv_actions_completed="FALSE"
        while user_dcv_actions_completed == "FALSE":
          #dcv_complete_user=input("Have you setup the DNS entries as per the instructions? Press Y if you have: ")
          dcv_complete_user="Y"
          user_dcv_actions_completed="TRUE";

          if dcv_complete_user == "Y":
            user_dcv_actions_completed="TRUE";
            print("Step 3: Certificate Deployment") 
            certdeploy="FALSE";     
            while certdeploy=="FALSE":
              print("The program will keep checking the status of your certificate every 15 mins, until it gets deployed.We will only go forward with the next steps once certificate is deployed on the platform. This activity might take ~3-4 hours. Appreciate your patience here.")
              #after every 1 hours of wait time , we will check if the cert has been deployed or not.
              time.sleep(900)
              enrollmentstatus=checkCertEnrollment(enrollmentID,changeID)
              #print(enrollmentstatus.text)
              if "All of your requested changes are complete" not in enrollmentstatus.text:
                print("Looks like there is some delay in the certificate deployment. Let us check after an hour...")
              else:
               certdeploy="TRUE";
               print("Looks like the certificate is deployed succesfully.")
          else:
            print("OK, we will check back in 5 minutes")
      else:
        print("something went wrong when creating the ceritificate. Please reach out to Akamai. The program will exit now")
        exit();
    while counthosts < len(hostorigincomponent):
        #Extracting the origin hostnames and digital properties for each hostnames
        host_origin_data = hostorigincomponent[counthosts].split(':')
        hostname=host_origin_data[0]
        origin_dns_ip=host_origin_data[1]
        #origin_dns_ip has origin IP/DNS stored.
        print("Step 4: Creating a new edge hostname and new config. Hostname currently in effect " + hostname + ". Please wait...")
        counthosts+=1
        #Create new config API call.
        result=createNewConfig(productid,hostname,contractid,groupid)
        if result.status_code != 201:
            print("Sorry, something went wrong with the configuration creation! Exiting the program now!")
            #Enable the next line if you want debugging capabilities
            print(result.json())
        else:
            # Extract the property ID after the new config creation is completed
            outputcatch=re.search('(.*)\/properties\/(.*)\?(.*)',str(result.json()))   ### Property ID stored in the below variable.
            propertyid=outputcatch.group(2)
            result=createSecureEdgeHostname(hostname,shortcontractid,shortgroupid,enrollmentID)
            #Waiting for the EdgeHostName requests to come to the pending state.
            time.sleep(800)
            # call the hostname addition PAPI call
            result=addHostNames(productid,hostname,contractid,groupid,propertyid)
            if result.status_code != 200:
                print("Sorry, something went wrong with hostname addition within SPS! Exiting the program now!")
                #Enable the next line if you want debugging capabilities
                print(result.json())
                exit()
            else:
                #Now that host name addition is successful, lets create the CPCODE.
                result=createCPCodes(productid,contractid,groupid,hostname)
                if result.status_code != 201:
                  print("CPCODE creation error! Using the default CPCODE")
                  print(result.json())
                else:
                  print("Step 5: Creating new CP codes for configs") 
                  cpcodeapioutput=re.search('(.*)cpc_(.*)\?(.*)',str(result.json()))   ### Extracting the CPCODE
                  cpcode=int(cpcodeapioutput.group(2))
                  cpcode_status=getCPCodes(str(cpcode),contractid,groupid)
                  #computing the CPCODE creation time for JSON input.
                  ch=re.search('(.*)([0-9]{4}\-[0-9]{2}\-[0-9]{2}T[0-9]{2}\:[0-9]{2}\:[0-9]{2}Z)(.*)',str(cpcode_status.json()))
                  output_cp_code_time_capture=ch.group(2) 
                  utc_time = datetime.strptime(output_cp_code_time_capture, "%Y-%m-%dT%H:%M:%SZ")
                  epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
                  cpcode_time=int(epoch_time)  
                  #End of computing the CPCODE creation time for JSON input.
                  print("CPCODE is created. Updating your configuration...") 
                  result=updateConfigRules(contractid,groupid,propertyid,origin_dns_ip,cpcode,cpcode_time,hostname)
                  if result.status_code != 200:
                    print("Sorry, something went wrong with config update! Exiting the program now!")
                    print(result.json())
                    exit()
                  else:
                    print("Success! Config is now updated!, Activating the configuration to STAGING network now.")
                    result=activateConfigStaging(contractid,groupid,propertyid,emailnotify)
                    if result.status_code != 201:
                        print("There seems to be an error in activating the config on production, please check the Akamai luna portal for error resolution. Error code from API backend below")
                        print(result.json())
                        exit()
                    else:
                        print("Successfully activated the config on staging network. Please give it 15 mins for both the activation to complete.") 
                        #check if staging activation is complete 
                        #activationstagingID=re.search('(.*)atv_(.*)\?(.*)',str(result.json()))
                        result=activateConfigProduction(contractid,groupid,propertyid,emailnotify)
                        if result.status_code != 201:
                          print("There seems to be an error in activating the config on production, please check the Akamai luna portal for error resolution. Error code from API backend below")
                          print(result.json())
                          exit()
                        else:
                          print("Successfully activated the config on staging network. Please give it 90 mins for both the activation to complete.")




