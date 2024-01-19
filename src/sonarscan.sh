set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 setup|<foundry-code-repository-path>"
    exit 1
fi

setup() {
    python3 /tmp/fill-template.py /tmp/sonar_scanner_cnf.patch.template
    patch -d/opt/sonar-scanner/conf -p0 </tmp/sonar_scanner_cnf.patch
}

scan() {
    CODEREPO=$1
    PROJECT_NAME=`basename "$CODEREPO"`
    fsm clone "$CODEREPO"
    cd /opt/sonarqube/git-helper/$PROJECT_NAME
    /opt/sonar-scanner/bin/sonar-scanner -D sonar.projectKey=$PROJECT_NAME
}

while [ $# -gt 0 ]; do
   echo $1
   if [ $1 = "setup" ] ; then setup
   else scan $1
   fi
   shift
done

