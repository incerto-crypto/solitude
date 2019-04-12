#!/bin/bash
if [ "$TRAVIS_BRANCH" == "feature/ci-cd" ]; then
    #TO-DO: change feature/ci-cd -> master 
    pip install -r ci/requirement-ci.txt
    cd docs
    git checkout gh-pages
    make html
    git add build
    git commit -m $TRAVIS_COMMIT
    git push
fi


