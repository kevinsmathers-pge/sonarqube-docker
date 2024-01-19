stages=${*:-1 2 3 4 5}
# build.sh is to build docker image from within MacBook
#. setting.sh
if [ -x ~/bin/arad-de ] ; then
    . ~/bin/arad-de
fi
AWS_ACCOUNT=925741509387
ARTIFACTORY=arad-micro-svcs-docker-virtual.jfrog.io.pge.com
TAG=sonarqube-scan
if grep -q 1 <<< "$stages" ; then
    echo "Rebuild distribution"
    rm $HOME/dist/*
    (cd $HOME/git/dca-foundry-jupyter && pip wheel -w $HOME/dist .)
    (cd $HOME/git/dca-aws-jupyter && pip wheel -w $HOME/dist .)
    rm $HOME/dist/*macos*
    rm -rf dist
    mkdir -p dist
    cp $HOME/dist/* dist
fi
if grep -q 3 <<< "$stages" ; then
    echo "Stage 3: Build docker image"

    docker build . -t $TAG --build-arg ARTIFACTORY=$ARTIFACTORY/
fi


