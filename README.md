# bulkonboards
Bulk onboard secure domains to Akamai

The script takes a yaml file as the input and creates the configurations in bulk. The hostnames should be passed in the YAML file, along with the rules.

Input format in the input.yml file:
Hostname : Origin name/IP address.
Email to notify.
Certificate details – CN, Altnames – this will create 1 DV SAN cert with Lets Encrypt.
Security Policy details/name.

# Akamai Bulk Onboarding Script + AWS Route53 integration

A python script that accepts a YAML file as the input and creates all the neccesary pieces required to onboard all the domains you have in your YAML file in bulk. 

Maintained by 
Prasad Pai @ Akamai Technologies
Akhil Jayaprakash @ Akamai Technologies [Twitter](https://twitter.com/akhiljp_dev)

## Installation Guide

### Step 1: Install the neccesary python libraries
Depending on what version of python you have you will need to import the appropriate python libraries
````
pip3 install requests
pip3 install edgegrid-python
pip3 install openpyxl
pip3 install pyyaml
pip3 install route53

````
### Step 2: Configure your YAML file
Enter the appropriate settings you wish to configure on Akamai within input.yml
````
OnboardConfig:
 Account:
  - ctr_G-2HFSI15  <-- enter the contract ID 
  - grp_126485 <-- enter the group ID
 ProductId:
  - prd_Fresca <-- enter the product ID
 Host-Origin:
  - onboard10.akamai.tools:onboard10-origin.akamai.tools  <-- each host:origin combination is going to be created as a separate configuration
  - onboard11.akamai.tools:onboard11-origin.akamai.tools
 notify:
  - jpakhil@gmail.com
OnboardCertconfig:
  Action: TRUE
  CN: onboard10.akamai.tools
  Altnames: ["onboard11.akamai.tools"]
OnboardSecurityConfig: <-- does not work at the moment, we are working on it. Stay tuned
  Policy: pol_name1
````



## Usage Instructions

### Step 1: 
Enter multiple hostname:staging-hostname combination into the  separated by a comma
For example:

1. For single hostname & staging hostname combination enter : www.foo.com:www.foo.com.edgekey-staging.net

2. For multiple hostnames & staging hostnames combination enter : www.foo.com:www.foo.com.edgekey-staging.net,static.foo.com:static.foo.edgekey-staging.net

![alt-text](https://github.com/akhiljay/Akamai-staging-proxy/blob/master/proxy-usage-1.png)


### Step 3: Click "save proxy settings" to start routing chrome browser traffic to Akamai Staging 

![alt-text](https://github.com/akhiljay/Akamai-staging-proxy/blob/master/proxy-usage-2.png)
Now all your browser traffic is being proxies via the Akamai-staging-proxy server that you have running locally

> Note: You can configure proxy settings for incognito windows as well. In order to do that you will need to first allow the extension to access incognito window

## You are all Set! 
Tweet at me [here](https://twitter.com/akhiljp_dev)  if you like the extension 

Additional Notes:

> * You can always revert back your Chrome browser's proxy settings by selecting "Use the system's proxy settings" within the google proxy extension

> * You can keep the node server running if you wish, but if you may wish to stop it anytime by clicking on CRTL-C

## Credits
1. Chrome Extension code from Mike West @ google
2. Node HTTP server based on [Node Proxy Server](https://github.com/nodejitsu/node-http-proxy) Charlie Robbins, Jarrett Cruger & the Contributors.





