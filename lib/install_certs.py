# Copyright Notice
# [2020] - [Current] Peter Gossler 
# All Rights Reserved.
# NOTICE:  All information contained herein is, and remains the property of Peter Gossler
# and his suppliers, if any.  The intellectual and technical concepts contained herein 
# are proprietary to Peter Gossler and his suppliers and may be covered by Singaporean 
# and Foreign Patents, patents in process, and are protected by trade secret or copyright law. 
# Dissemination of this information or reproduction of this material is strictly forbidden 
# unless prior written permission is obtained from Peter Gossler, kpg141260@live.de.

import os, sys, ssl
import os.path
from OpenSSL import SSL, crypto
import socket
import stat, time
import subprocess, socket
from cryptography                   import x509
from cryptography.hazmat.backends   import default_backend

STAT_0o775 = ( stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH )

def get_certificate(cafile, host='srsupply.fortiddns.com', port=8743, cert_file_pathname='sr_supply'):
    s = socket.socket()
    context = SSL.Context(SSL.TLSv1_2_METHOD)
    print('Connecting to {0} to get certificate...'.format(host))
    conn = SSL.Connection(context, s)
    certs = []

    try:
        conn.connect((host, port))
        conn.do_handshake()
        certs = conn.get_peer_cert_chain()

    except SSL.Error as e:
        print('Error: {0}'.format(str(e)))
        exit(1)

    try:
        for index, cert in enumerate(certs):
            cert_components = dict(cert.get_subject().get_components())
            if(sys.version_info[0] >= 3):
                cn = (cert_components.get(b'CN')).decode('utf-8')
            else:
                cn = cert_components.get('CN')
            print('Certificate {0} - CN: {1}'.format(index, cn))

            try:
                temp_certname = '{0}_{1}.crt'.format(cert_file_pathname, index)
                print (temp_certname)
                with open(temp_certname, 'w+') as output_file:
                    if(sys.version_info[0] >= 3):
                        output_file.write((crypto.dump_certificate
                                         (crypto.FILETYPE_PEM, cert).decode('utf-8')))
                        print ('File saved')
                    else:
                        output_file.write((crypto.dump_certificate(crypto.FILETYPE_PEM, cert)))
                        print ('File saved')

                    print('Adding custom certs to Certifi store...')
                    with open(temp_certname, 'rb') as infile:
                        customca = infile.read()
                    with open(cafile, 'ab') as outfile:
                        outfile.write(customca)
                    print('That might have worked.')

            except IOError:
                print('Exception:  {0}'.format(IOError.strerror))

    except SSL.Error as e:
        print('Error: {0}'.format(str(e)))
        exit(1)

def main():
    openssl_dir, openssl_cafile = os.path.split(ssl.get_default_verify_paths().openssl_cafile)

    print(" -- pip install --upgrade certifi")
    subprocess.check_call([sys.executable, "-E", "-s", "-m", "pip", "install", "--upgrade", "certifi"])

    import certifi

    # change working directory to the default SSL directory
    os.chdir(openssl_dir)
    relpath_to_certifi_cafile = os.path.relpath(certifi.where())
    print(" -- removing any existing file or link")
    try:
        os.remove(openssl_cafile)
    except FileNotFoundError:
        pass
    print(" -- creating symlink to certifi certificate bundle")
    os.symlink(relpath_to_certifi_cafile, openssl_cafile)
    print(" -- setting permissions")
    os.chmod(openssl_cafile, STAT_0o775)
    print(" -- update complete")

    get_certificate (certifi.where())

if __name__ == '__main__':
    main()

