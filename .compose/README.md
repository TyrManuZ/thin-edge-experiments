# Instructions

## Generating certificates
1. Run ```sh init_setup.sh```. This will generate your CA and root certificate and the setup for generating and signing device certificates.
2. Run ```sh sign_device_certs.sh```. This will prompt you with entering a prefix for the CN and the amount of certificates you want to generate. The CN will always have the following structure ```{your_prefix}_{serial}```. The serial numbers will start at 1000 and are incremented (in hex) with every new certificate you generate. You can edit the file called ```serial``` if you want to start at a different number.
3. You will see a folder being created for every certificate you generate (the folder name is the CN prefixed with ```deivce_```). Inside the folder you will find the certificate, key and chain that you need for the client.

## Running docker-compose

# Dev notes
## Create CA
openssl genrsa -des3 -out temp_key.key 2048

## Remove password from key file

openssl rsa -in temp_key.key -out tedge_CA_key.pem

## Create root certificate
openssl req -x509 -new -nodes -key tedge_CA_key.pem -sha256 -days 1825 -out tedge_CA_cert.pem

Important: Set a Common Name (all other fields are optional)