touch database.txt
touch serial
echo "1000" >> serial

# Create CA
openssl genrsa -out tedge_CA_key.pem 4096

# Create root certificate
openssl req -x509 -new -nodes -key tedge_CA_key.pem -sha256 -days 1825 -out tedge_CA_cert.pem