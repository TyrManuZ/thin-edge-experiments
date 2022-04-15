#!/bin/sh
tmp_dir=deviceCertificates

read -p 'CN prefix: ' cn_prefix
read -p 'How many certificates do you need?: ' iterations


for i in `seq 1 $iterations`
do
    serial=`cat serial`
    mkdir $tmp_dir
    openssl genrsa -out $tmp_dir/deviceKeyNoPW.pem 4096 
    openssl req -config caConfig.cnf -new -sha256 -subj "/CN=${cn_prefix}-${serial}" -key $tmp_dir/deviceKeyNoPW.pem -out $tmp_dir/deviceCsr.pem
    openssl ca -batch -config caConfig.cnf -extensions v3_signed -days 365 -notext -md sha256 -in $tmp_dir/deviceCsr.pem -out $tmp_dir/deviceCert.pem
    cat $tmp_dir/deviceCert.pem >> $tmp_dir/deviceCertChain.pem
    cat tedge_CA_cert.pem >> $tmp_dir/deviceCertChain.pem
    rm $tmp_dir/$serial.pem
    mv $tmp_dir "device_${cn_prefix}-${serial}"
done
