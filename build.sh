stages=${*:-1 2 3 4 5}
# build.sh is to build docker image from within MacBook
. setting.sh
if [ -x ~/bin/arad-de ] ; then
    . ~/bin/arad-de
fi
AWS_ACCOUNT=
ARTIFACTORY=

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
    docker build . -t $PROJECT:$VERSION --build-arg ARTIFACTORY=$ARTIFACTORY
fi
if grep -q 4 <<< "$stages" ; then
    echo "Stage 4: Tag and push docker image"
    ECR=$AWS_ACCOUNT.dkr.ecr.us-west-2.amazonaws.com
    TAG=$ECR/$PROJECT:$VERSION
    aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $ECR >/dev/null
    docker tag $PROJECT:$VERSION $TAG
    docker push $TAG
fi
if grep -q 5 <<< "$stages" ; then
    echo "Stage 5: Deply kubernetes cronjob"
    python src/fill-template.py cron.yaml.template
    kubectl apply cron.yaml
fi


