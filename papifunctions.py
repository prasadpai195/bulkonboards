#!/usr/bin/env python
import requests
import json
from akamai.edgegrid import EdgeGridAuth
from urllib.parse import urljoin
import re
import sys
import argparse
from datetime import datetime
import calendar
import yaml
import route53


yamlconfighandle=yaml.load(open('credentials.yml'))
baseurl= yamlconfighandle['Credentials'][0]
client_token=yamlconfighandle['Credentials'][1]
client_secret=yamlconfighandle['Credentials'][2]
access_token=yamlconfighandle['Credentials'][3]
s = requests.Session()
s.auth = EdgeGridAuth(
client_token=client_token,
client_secret=client_secret,
access_token=access_token
)
# Connecting to route 53
#conn = route53.connect(
#  aws_access_key_id='XXXXXX',
#  aws_secret_access_key='o5XXXXXXXXXX',
#)

def creatCertEnrollment(contractid,commonname,altnames):
  #Function to create cert enrollment.
  #Extract the short contracid. Example, if contractid is ctr_G-123GHS, the shortcontractid=G-123GHS
  headers = {"content-type": "application/vnd.akamai.cps.enrollment.v7+json","Accept":"application/vnd.akamai.cps.enrollment-status.v1+json"}
  hostname="test.prasadtest.akamaidevops.com"
  data={'ra': 'lets-encrypt', 'validationType': 'dv', 'certificateType': 'san', 'networkConfiguration': {'geography': 'core', 'secureNetwork': 'enhanced-tls', 'mustHaveCiphers': 'ak-akamai-default', 'preferredCiphers': 'ak-akamai-default', 'sniOnly': True, 'quicEnabled': False, 'disallowedTlsVersions': ['TLSv1', 'TLSv1_1'], 'dnsNameSettings': {'cloneDnsNames': False, 'dnsNames': None}}, 'signatureAlgorithm': 'SHA-256', 'changeManagement': False, 'csr': {'cn': commonname, 'c': 'US', 'st': 'MA', 'l': 'Cambridge', 'o': 'Akamai', 'ou': 'IT', 'sans': altnames}, 'org': {'name': 'Akamai Technologies', 'addressLineOne': '150 Broadway', 'addressLineTwo': None, 'city': 'Cambridge', 'region': 'MA', 'postalCode': '02142', 'country': 'US', 'phone': '617-555-0111'}, 'adminContact': {'firstName': 'Test', 'lastName': 'Test', 'phone': '111-111-1111', 'email': 'test@testxac.com', 'addressLineOne': '150 Broadway', 'addressLineTwo': None, 'city': 'Cambridge', 'country': 'US', 'organizationName': 'Akamai', 'postalCode': '02142', 'region': 'MA', 'title': 'Customer'}, 'techContact': {'firstName': 'Akamai', 'lastName': 'Akamai', 'phone': '111-111-1111', 'email': 'test@akamai.com', 'addressLineOne': '150 Broadway', 'addressLineTwo': None, 'city': 'Cambridge', 'country': 'US', 'organizationName': 'Akamai', 'postalCode': '02142', 'region': 'MA', 'title': 'Script'}, 'enableMultiStackedCertificates': False}
  result=s.post(urljoin(baseurl,'/cps/v2/enrollments?contractId='+contractid+''), data=json.dumps(data), headers=headers)
  return result
def checkCertEnrollment(enrollmentID,changeID):
  headers = {"Accept":"application/vnd.akamai.cps.change.v2+json"}
  result=s.get(urljoin(baseurl,'/cps/v2/enrollments/'+enrollmentID+'/changes/'+changeID+''),headers=headers)
  return result
def Convert(string):
  li = '"'+ string + '"'
  li1 = list(li.split(" "))
  return li1
def getDVChallenges(enrollmentID):
  headers = {"Accept":"application/vnd.akamai.cps.dv-history.v1+json"}
  result=s.get(urljoin(baseurl,'/cps/v2/enrollments/'+enrollmentID+'/dv-history'),headers=headers)
  data=result.json();
  #print(data)
  if json.dumps(data)=="{\"results\": []}":
    status="fail";
  else:
    status="success";
    zone = conn.get_hosted_zone_by_id('Z18XT5TVMN5UQR')
    dvtree=data["results"];
    for domain in dvtree:
      for children in domain["domainHistory"]:
        for validationtype in children["challenges"]:
          if validationtype["type"] == "dns-01":
            print("DNS DV challenges: Creating a TXT record pointing "+validationtype["fullPath"]+ " to " +validationtype["responseBody"]+" with a DNS TTL of 60s")
            new_record, change_info = zone.create_txt_record(
            # Notice that this is a full-qualified name.
            name=validationtype["fullPath"],
            # A list of IP address entries, in the case fo an A record.
            values=Convert(validationtype["responseBody"]),
            ttl='60',
            )
            print("DNS record for "+ validationtype["fullPath"]+ " successfully created in AWS")
  return status
def createSecureEdgeHostname(hostname,contractid,groupid,enrollmentid):
  headers={"content-type": "application/x-www-form-urlencoded"}
  #data={"productId": productid,"domainPrefix": hostname,"domainSuffix": "edgekey.net","secure":"true","ipVersionBehavior": "IPV4","slotNumber": 19,"certEnrollmentId":enrollmentid}
  data="cnameHostname="+hostname+"&enrollmentId="+enrollmentid+""
  print(contractid)
  print(groupid)
  result=s.post(urljoin(baseurl,'/config-secure-provisioning-service/v1/secure-edge-hosts?contractId='+contractid+'&groupId='+groupid+''), data=data, headers=headers)
  print(result.json())
def createCPCodes(productid,contractid,groupid,hostname):
  headers={"content-type": "application/json"}
  data={"cpcodeName": hostname ,"productId": productid}
  result=s.post(urljoin(baseurl,'/papi/v1/cpcodes?contractId='+contractid+'&groupId='+groupid+''), data=json.dumps(data), headers=headers)
  return result
def getCPCodes(cpcode,contractid,groupid):
   result=s.get(urljoin(baseurl,'/papi/v0/cpcodes/cpc_'+cpcode+'?contractId='+contractid+'&groupId='+groupid+''))
   return result
def createNewConfig(productid,hostname,contractid,groupid):
  data={"productId": productid,"propertyName": hostname}
  headers = {"content-type": "application/json"}
  result=s.post(urljoin(baseurl,'/papi/v1/properties/?contractId='+contractid+'&groupId='+groupid+''), data=json.dumps(data), headers=headers)
  return result
def addHostNames(productid,hostname,contractid,groupid,propertyid):
  headers={"content-type": "application/json"}
  #Hardcoding for now.
  data=[{"cnameTo":""+hostname+".edgekey.net" ,"cnameFrom": hostname,"cnameType": "EDGE_HOSTNAME","secure":"true"}]
  result=s.put(urljoin(baseurl, '/papi/v1/properties/'+propertyid+'/versions/1/hostnames/?contractId='+ contractid+'&groupId='+groupid+'&validateHostnames=true'),data=json.dumps(data),headers=headers)
  return result
def updateConfigRules(contractid,groupid,propertyid,origin_dns_ip,cpcode,cpcode_time,hostname):
  headers = {"content-type": "application/vnd.akamai.papirules.latest+json"}
  data={"rules":{"name":"default","children":[{"name":"Content Compression","children":[],"behaviors":[{"name":"gzipResponse","options":{"behavior":"ALWAYS"}}],"criteria":[{"name":"contentType","options":{"matchCaseSensitive":False,"matchOperator":"IS_ONE_OF","matchWildcard":True,"values":["text/*","application/javascript","application/x-javascript","application/x-javascript*","application/json","application/x-json","application/*+json","application/*+xml","application/text","application/vnd.microsoft.icon","application/vnd-ms-fontobject","application/x-font-ttf","application/x-font-opentype","application/x-font-truetype","application/xmlfont/eot","application/xml","font/opentype","font/otf","font/eot","image/svg+xml","image/vnd.microsoft.icon"]}}],"criteriaMustSatisfy":"all"},{"name":"Static Content","children":[],"behaviors":[{"name":"caching","options":{"behavior":"MAX_AGE","mustRevalidate":False,"ttl":"1d"}},{"name":"prefetch","options":{"enabled":False}},{"name":"prefetchable","options":{"enabled":True}}],"criteria":[{"name":"fileExtension","options":{"matchCaseSensitive":False,"matchOperator":"IS_ONE_OF","values":["aif","aiff","au","avi","bin","bmp","cab","carb","cct","cdf","class","css","doc","dcr","dtd","exe","flv","gcf","gff","gif","grv","hdml","hqx","ico","ini","jpeg","jpg","js","mov","mp3","nc","pct","pdf","png","ppc","pws","swa","swf","txt","vbs","w32","wav","wbmp","wml","wmlc","wmls","wmlsc","xsd","zip","pict","tif","tiff","mid","midi","ttf","eot","woff","woff2","otf","svg","svgz","webp","jxr","jar","jp2"]}}],"criteriaMustSatisfy":"all"},{"name":"Dynamic Content","children":[],"behaviors":[{"name":"downstreamCache","options":{"behavior":"TUNNEL_ORIGIN"}}],"criteria":[{"name":"cacheability","options":{"matchOperator":"IS_NOT","value":"CACHEABLE"}}],"criteriaMustSatisfy":"all"},{"name":"Performance","children":[],"behaviors":[{"name":"http2","options":{"enabled":""}},{"name":"allowTransferEncoding","options":{"enabled":True}},{"name":"removeVary","options":{"enabled":True}}],"criteria":[],"criteriaMustSatisfy":"all","comments":"Improves the performance of delivering objects to end users. Behaviors in this rule are applied to all requests as appropriate."}],"behaviors":[{"name": "origin","options": {"cacheKeyHostname": "ORIGIN_HOSTNAME","compress": True,"enableTrueClientIp": True,"trueClientIpHeader":"True-Client-IP","trueClientIpClientSetting":False,"forwardHostHeader":"REQUEST_HOST_HEADER","hostname": origin_dns_ip,"httpPort": 80,"httpsPort": 443,"originSni": True,"originType": "CUSTOMER","verificationMode": "CUSTOM","originCertificate": "","ports": "","customValidCnValues": ["{{Origin Hostname}}","{{Forward Host Header}}"],"originCertsToHonor": "STANDARD_CERTIFICATE_AUTHORITIES","standardCertificateAuthorities": ["akamai-permissive"]}},{"name":"cpCode","options":{"value":{"id":cpcode,"name":hostname}}},{"name":"caching","options":{"behavior":"NO_STORE"}},{"name":"sureRoute","options":{"enabled":True,"forceSslForward":False,"raceStatTtl":"30m","toHostStatus":"INCOMING_HH","type":"PERFORMANCE","testObjectUrl":"/akamai/test/object.html","enableCustomKey":False}},{"name":"tieredDistribution","options":{"enabled":True,"tieredDistributionMap":"CH2"}},{"name":"prefetch","options":{"enabled":True}},{"name":"allowPost","options":{"allowWithoutContentLength":False,"enabled":True}},{"name":"report","options":{"logAcceptLanguage":False,"logCookies":"OFF","logCustomLogField":False,"logHost":False,"logReferer":False,"logUserAgent":True}},{"name":"realUserMonitoring","options":{"enabled":True}}],"options":{"is_secure":True},"variables":[]},"ruleFormat": "v2018-09-12"}
  #print(json.dumps(data))
  result=s.put(urljoin(baseurl, '/papi/v1/properties/'+propertyid+'/versions/1/rules/?contractId='+contractid+'&groupId='+groupid+'&validateRules=true'),data=json.dumps(data),headers=headers)
  #print (result.json())
  return result
def activateConfigStaging(contractID,groupID,propertyid,emailnotify):
  data = {"propertyVersion": 1 ,"network": "STAGING","note": "Initial Activation","notifyEmails": [emailnotify],"acknowledgeAllWarnings":1}
  headers = {"content-type": "application/json"}
  result=s.post(urljoin(baseurl,'/papi/v1/properties/'+propertyid+'/activations/?contractId='+contractID+'&groupId='+groupID+''), data=json.dumps(data), headers=headers)
  return result
def activateConfigProduction(contractID,groupID,propertyid,emailnotify):
  data = {"propertyVersion": 1 ,"network": "PRODUCTION","note": "Initial Activation","notifyEmails": [emailnotify],"acknowledgeAllWarnings":1}
  headers = {"content-type": "application/json"}
  result=s.post(urljoin(baseurl,'/papi/v1/properties/'+propertyid+'/activations/?contractId='+contractID+'&groupId='+groupID+''), data=json.dumps(data), headers=headers)
  return result
def activationStatus(contractID,groupID,propertyid,emailnotify):
  data = {"propertyVersion": 1 ,"network": "PRODUCTION","note": "Initial Activation","notifyEmails": [emailnotify],"acknowledgeAllWarnings":1}
  headers = {"content-type": "application/json"}
  result=s.post(urljoin(baseurl,'/papi/v1/properties/'+propertyid+'/activations/?contractId='+contractID+'&groupId='+groupID+''), data=json.dumps(data), headers=headers)
  return result
def appsecaddhostnames(pol_id,pol_version_number,hostname):
  #Get the existing hostname list
  result=s.get(urljoin(baseurl,'/appsec/v1/configs/'+pol_id+'/versions/'+pol_version_number+'/selected-hostnames'))
  data=json.loads(json.dumps(result.json()))
  newhost={'hostname': hostname}
  data['hostnameList'].append(newhost)
  # Add the hostname to selected hosts(appends to the existing hosts list)
  headers = {"content-type": "application/json"}
  result=s.put(urljoin(baseurl, '/appsec/v1/configs/'+pol_id+'/versions/'+pol_version_number+'/selected-hostnames'),data=json.dumps(data),headers=headers)
  return result
