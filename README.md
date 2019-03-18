# bulkonboards
Bulk onboard secure domains to Akamai

The script takes a yaml file as the input and creates the configurations in bulk. The hostnames should be passed in the YAML file, along with the rules.

Input format in the input.yml file:
Hostname : Origin name/IP address.
Email to notify.
Certificate details – CN, Altnames – this will create 1 DV SAN cert with Lets Encrypt.
Security Policy details/name.
