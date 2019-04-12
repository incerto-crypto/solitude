#!/bin/bash
if [ "$TRAVIS_BRANCH" == "feature/ci-cd" ]; then
    #TO-DO: change feature/ci-cd -> master
    git config --global user.email "travis@travis-ci.org"
    git config --global user.name "Travis CI"
    pip install -r ci/requirements-ci.txt
    git fetch --all
    git branch -a
    cd docs
    make html
    git add build *.html -f
    git commit -m "Travis build: $TRAVIS_COMMIT"
    git branch temp-branch
    git branch -a
    git checkout gh-pages
    git merge temp-branch
    remote=https://$GITHUB_TOKEN@github.com/$TRAVIS_REPO_SLUG
    git push --quiet --follow-tags "$remote" "gh-pages" >/dev/null 2>&1
fi

