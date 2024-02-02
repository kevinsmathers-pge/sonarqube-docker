stages=${*:-1 2 3}


# start sonarqube server and wait for it to come up
if grep -q 1 <<<"$stages" ; then
    python3 /tmp/fill-template.py /tmp/sonarqube_cnf.patch.template
    patch -d/ -p0 </tmp/sonarqube_cnf.patch
    bash /opt/sonarqube/bin/linux-x86-64/sonar.sh start
    sleep 5
    while ! grep -q "SonarQube is operational" /opt/sonarqube/logs/sonar.log ; do
        sleep 5
    done
fi

# setup scanner
if grep -q 2 <<<"$stages" ; then
    bash /opt/sonarscan.sh setup
fi

# setup scanner and run scans
if grep -q 3 <<<"$stages" ; then
    bash /opt/sonarscan.sh repository_list       
fi
