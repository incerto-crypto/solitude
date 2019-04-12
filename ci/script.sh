#!/bin/bash
if [ "$TRAVIS_BRANCH" == "feature/ci-cd" ]; then
    #TO-DO: change feature/ci-cd -> master 
    pip install -r ci/requirements-ci.txt

    cd docs
    make html
    git add build -f
    git commit -m $TRAVIS_COMMIT
    git branch temp-branch
    git checkout gh-pages
    git merge gh-pages
    git push origin gh-pages
fi

