#!/bin/bash
if [ "$TRAVIS_BRANCH" == "feature/ci-cd" ]; then
    #TO-DO: change feature/ci-cd -> master 
    pip install -r ci/requirements-ci.txt
    git fetch --all
    git branch -a
    cd docs
    make html
    git add build -f
    git commit -m $TRAVIS_COMMIT
    git branch temp-branch
    git branch -a
    git checkout gh-pages
    git merge temp-branch
    git push origin gh-pages
fi

