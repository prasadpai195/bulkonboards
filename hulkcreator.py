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
from papifunctions import createNewConfig,addHostNames,updateConfigRules,creatCertEnrollment,activateConfigStaging,activateConfigProduction,createCPCodes,getCPCodes,createSecureEdgeHostname,checkCertEnrollment,getDVChallenges,appsecaddhostnames
import time
import route53
# Main Program
if __name__ == '__main__':
    print("\nLoading up!!! We are now reading your input, please give us a moment... \n \n \n")
    counthosts=0
    # Step 1: Consume the YAML file
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--config", help="yaml file input")
    args=parser.parse_args()
    inputfilename=args.config
    # Extract the account/contract details from the YAML file.
    yamlhandle=yaml.load(open(inputfilename))
    #Extracting the contract ID.
    contractid = yamlhandle['OnboardConfig']['Account'][0]
    #Extracting the group ID.
    groupid=yamlhandle['OnboardConfig']['Account'][1]
    #Some APIs need the short contract ID, and hence extracting the contract ID minus the "ctr_".
    shortcontractid=contractid.split('_')
    shortcontractid=shortcontractid[1]
    #Some APIs need the short group ID, and hence extracting the contract ID minus the "grp_".
    shortgroupid=groupid.split('_')
    shortgroupid=shortgroupid[1]
    #Extract the productid
    productid=yamlhandle['OnboardConfig']['ProductId'][0]
    # Extract the Hostnames from the YAML file.
    hostorigincomponent=yamlhandle['OnboardConfig']['Host-Origin']
    #Extract the email id where notification emails should be sent.
    emailnotify=yamlhandle['OnboardConfig']['notify'][0]
    #To create the SSL cert request or not?
    certdecision = yamlhandle['OnboardCertconfig']['Action']
    #Extract the CN of the certificate
    certcn = yamlhandle['OnboardCertconfig']['CN']
    #Extract the cert's Altnames
    certaltnames=yamlhandle['OnboardCertconfig']['Altnames']
    #Extract the WAF policy ID
    pol_id=yamlhandle['OnboardSecurityConfig']['Policy_ID']
    #Extract the WAF policy version number
    pol_version_number=yamlhandle['OnboardSecurityConfig']['Policy_V_No']
    # Let us first put in the cert request, as that takes a longer time...
    if certdecision == True:
      print("Step 1: Certificate creation job in progress. Please note that the normal certificate creation and deployment ETA is approximately 4 hours...\n \n \n")
      result=creatCertEnrollment(shortcontractid,certcn,certaltnames)
      if "202" not in result:
        print("Looks like the DV SSL Certificate was created successfully. In ~5-10 minutes, we should have the DV challenges ready for you.\n \n")
        # enrollment ID and change IDs stored in the below variable.
        enrollmentidcatch=re.search('(.*)\/enrollments\/([0-9]{1,})\/changes\/([0-9]{1,})"(.*)',str(result.text))
        enrollmentID=enrollmentidcatch.group(2)
        changeID=enrollmentidcatch.group(3)
        print("To check the status of your certificate, use this enrollment ID:"+enrollmentID+" and the change ID:"+changeID+"\n \n")
        dcv="FALSE";
        while dcv == "FALSE":
          print("Waiting for the DV challenges from Lets Encrypt!...\n \n")
          #Waiting for 1 mins for the DV challenges to be ready.
          time.sleep(60)
          #Now, retrieve the DV challenges.
          retreiveDVchallenges=getDVChallenges(enrollmentID)
          if retreiveDVchallenges == "success":
            dcv="TRUE";
          else:
            print("Looks like the DCV challenges are not ready yet! We will keep checking every 1 minutes.\n \n")
        user_dcv_actions_completed="FALSE"
        while user_dcv_actions_completed == "FALSE":
          dcv_complete_user=input("Have you setup the DNS entries as per the instructions? ONLY Press Y if you have completed the task: ")
          if dcv_complete_user == "Y":
            user_dcv_actions_completed="TRUE";
            print("Step 2: Certificate Deployment\n \n \n")
            certdeploy="FALSE";
            while certdeploy=="FALSE":
              print("The program will keep checking the status of your certificate every 15 mins, until it gets deployed.We will only go forward with the next steps once certificate is deployed on the platform. This activity might take ~3-4 hours. Appreciate your patience here.\n \n")
              #after every 15 mins of wait time , we will check if the cert has been deployed or not.
              time.sleep(900)
              enrollmentstatus=checkCertEnrollment(enrollmentID,changeID)
              if "All of your requested changes are complete" not in enrollmentstatus.text:
                print("Looks like there is some delay in the certificate deployment. Let us check after 15 mins...\n \n")
              else:
               certdeploy="TRUE";
               print("Looks like the certificate is deployed succesfully.\n \n")
          else:
            print("OK, we will check back in 5 minutes\n \n")
            time.sleep(300)
      else:
        print("Something went wrong when creating the ceritificate. Please reach out to Akamai team as we cannot proceed without the certificate!!! The program will exit now\n \n \n")
        exit();
#******************************CERTIFICATE DEPLOYMENT COMPLETED************************************************************
    while counthosts < len(hostorigincomponent):
        #Extracting the origin hostnames and digital properties for each hostnames
        host_origin_data = hostorigincomponent[counthosts].split(':')
        hostname=host_origin_data[0]
        #origin_dns_ip has origin IP/DNS stored.
        origin_dns_ip=host_origin_data[1]
        print("Step 3: Creating a new edge hostname and new config. Hostname currently in effect " + hostname + ". Please wait...\n \n \n")
        counthosts+=1
        #Create new config API call.
        result=createNewConfig(productid,hostname,contractid,groupid)
        if result.status_code != 201:
            print("Sorry, something went wrong with the configuration creation! Exiting the program now!\n \n")
            print(result.json())
            continue;
        else:
            # Extract the property ID after the new config creation is completed
            outputcatch=re.search('(.*)\/properties\/(.*)\?(.*)',str(result.json()))   ### Property ID stored in the below variable.
            propertyid=outputcatch.group(2)
            # Creating a new edgehostname for this hostname
            result=createSecureEdgeHostname(hostname,shortcontractid,shortgroupid,enrollmentID)
            if result.status_code != 202:
                print("Something went wrong when creating the Edge Host Name.\n"+result.json()+"")
                continue;
            else:
                print("Let us wait for the EdgeHostnames to get created. This approximately takes 15 mins...\n \n")
                #Waiting for the EdgeHostName requests to come to the pending state.
                time.sleep(900)
                # call the hostname addition PAPI call
                result=addHostNames(productid,hostname,contractid,groupid,propertyid)
                if result.status_code != 200:
                    print("Sorry, something went wrong with hostname addition within SPS! Exiting the program now!\n \n")
                    #Enable the next line if you want debugging capabilities
                    print(result.json())
                    continue;
                else:
                    #Now that host name addition is successful, lets create the CPCODE.
                    result=createCPCodes(productid,contractid,groupid,hostname)
                    if result.status_code != 201:
                        print("CPCODE creation error! Using the default CPCODE\n \n")
                        print(result.json())
                        continue;
                    else:
                        print("Step 4: Creating new CP codes for configs\n \n")
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
                            print("Sorry, something went wrong with config update! Exiting the program now!\n \n")
                            print(result.json())
                            continue;
                        else:
                            print("Success! Config is now updated!, Activating the configuration to STAGING network now.\n \n")
                            result=activateConfigStaging(contractid,groupid,propertyid,emailnotify)
                            if result.status_code != 201:
                                print("There seems to be an error in activating the config on staging network, please check the Akamai luna portal for error resolution. Error code from API backend below\n \n")
                                print(result.json())
                                continue;
                            else:
                                print("Successfully activated the config on staging network. Please give it 15 mins for both the activation to complete.\n \n")
                                #check if staging activation is complete
                                #activationstagingID=re.search('(.*)atv_(.*)\?(.*)',str(result.json()))
                                result=activateConfigProduction(contractid,groupid,propertyid,emailnotify)
                                if result.status_code != 201:
                                    print("There seems to be an error in activating the config on production, please check the Akamai luna portal for error resolution. Error code from API backend below\n \n")
                                    print(result.json());
                                    continue;
                                else:
                                    print("Successfully activated the config on production network. Please give it 90 mins for both the activation to complete.\n \n")
                                    # Once config is activated to production, wait for 20 mins and then trigger the appsec API to add domains into WAF.
                                    time.sleep(1200)
                                    result=appsecaddhostnames(pol_id,pol_version_number,hostname)
                                    if result.status_code != 200:
                                        print("Something went wrong with WAF hostname addition. Please contact Akamai representative to find out what went wrong. Error code shared below\n \n")
                                        print(result.json())
                                        continue;
                                    else:
                                        print("Addition of the hostname to the security policy succesful. Lets move to the next hostnames\n \n")
