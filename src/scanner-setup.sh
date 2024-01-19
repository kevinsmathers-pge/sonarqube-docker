python3 /tmp/fill-template.py /tmp/sonar_scanner_cnf.patch.template
patch -d/opt/sonar-scanner/conf -p0 </tmp/sonar_scanner_cnf.patch