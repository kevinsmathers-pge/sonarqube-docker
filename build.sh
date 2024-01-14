stages=${*:-1 2 3 4 5}
# build.sh is to build docker image from within MacBook
#. setting.sh
. ~/bin/arad-de
AWS_ACCOUNT=925741509387
TAG=sonarqube-scan

if grep -q 3 <<< "$stages" ; then
    echo "Stage 3: Build docker image"
    
    docker build . -t $TAG --build-arg AWS_ACCOUNT=$AWS_ACCOUNT
fi


