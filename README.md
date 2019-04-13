# Akamai Bulk Onboarding Script + AWS Route53 integration

A python script that accepts a YAML file as the input and creates all the neccesary pieces required to onboard all the domains you have in your YAML file in bulk. 

Maintained by 
Prasad Pai @ Akamai Technologies
| Akhil Jayaprakash @ Akamai Technologies [Twitter](https://twitter.com/akhiljp_dev)

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
### Step 3: Configure your Akamai Credentials
Enter the appropriate API secrets within credentials.yml
````
Credentials:
  - https://akab-xxxxx   <-- Base URL
  - akab-xxxxxx          <-- Client Token
  - jcHFxxxxxxxxxx       <-- Client Secret
  - akab-vxxxx           <-- Access Token
````
### Step 4: Configure your AWS Route53 Credentials
Enter the appropriate AWS route53 IAM API key ID and secret into papifunctions.py. These credentials will be used to create DNS records automatically when Akamai provides the script with the domain validation DNS instructions
````
Connecting to route 53 
conn = route53.connect(
    aws_access_key_id='XXXXXX',
    aws_secret_access_key='o5XXXXXXXXXX',
)
````
### Step 5: Enter the Route53 hosted zone ID within the script
Enter the right Route53 hostedzone ID within papifunctions.py so the script knows which DNS zone it should create the resource record. 
````
    zone = conn.get_hosted_zone_by_id('Z1XXXXXX')
````


## Usage Instructions

### Step 1: 
Execute the python script 

````
python3 hulkcreator.py -f input.yml
````

The script will commence execution with the required data. The script starts with creating a CPS enrollment, then fetching the DV challenges. The DNS challenges are fed into AWS route53 APIs and upon a successful response it proceeds to deploying the cert. 
Once the certificate is deployed, the script starts performing the following operations
1. Secure Edgehostname
2. Creating a blank Property manager file for individual domains
3. Create a new CP codes for each of the domains
4. Update the initial blank property manager file with the secure edgehostname, CP code and the appropriate forward SSL settings
5. Pushes the config to staging
6. Pushes the config to production and exits the script

### Step 2: Email confirmation once activation is complete
Once the activation is complete on both staging and production, an email will be sent as a notification. 







