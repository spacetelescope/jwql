# The James Webb Quicklook Application 

One Paragraph of project description goes here.

## Getting Started

### Prerequisites

git
flake8

(Once we have more things we deem as prereqs for using and contributing to our project then we can add them here.) 

### Installing

You first need to install the current version of jwql. The simplest way to do this is to go to the directory you want your version to be in and clone the repoistory there. Once you are in the directory you can do the following: 

```
git clone https://github.com/spacetelescope/jwql.git
```

## Contributing

Be sure to talk about the [style guide](https://github.com/spacetelescope/jwql/blob/style-guide/style_guide/style_guide.md) and what's in there regarding this. The following is a bare bones example of a best work flow for contributing to the project. 


### Make an issue on github

This is most easily done on the website [here](https://github.com/spacetelescope/jwql/issues).

It's important to do this as  

### Make a branch (forking):
You can do this either through your terminal or through the webpage. Here is an explaination of how to do each: 

#### Webpage: 

#### Terminal: 


### Best Practices Workflow:

As you go be sure to follow the steps:

    ```
    git status 

    git add 'file.py'

    git commit -m " This is the first commit of the first code for this project. "

    git push
    
    *** The first time that you push your branch you will get a warning and first need to run this: 

    git push --set-upstream origin your-branch-name
    ```

Repeat! Feel free to repeat everytime you make a big change to your project and/or at the end of every work day to ensure you're keeping track of your work in incremental steps that make sense for you. 

### Git Ignore: 
It's a good idea to set up a .gitignore file to allow you to place file types that you don't want to upload to the git branch. 

For example, if you are testing your updates or codes in a jupyter notebook in the directory it's good practice to not upload that notebook. Therefore, you can create a '.gitignore' file in the directory and place ' *ipynb' in a line in that file. Then when you do a 'git status' those file types will not show up as having changed and needing to be commited. Other examples of files you would want to add are: ...   

### Switching Branches: 
When you are working on a project you will have made a branch to change or add files. But what if you now need to go back to the current version of the project to work on something else? You can switch your branch!

To check what branch you are on: 
```
git branch
```

To change to the current version of the project: 
```
git checkout -b master
```

To get up to date with the current version of the project:
```
git pull
```

You can then switch back to your project (or a different project) any time by checking the name of hte branch and then switching: 

```
git checkout -b name_of_branch
```

### Merging your Branch with the Master Branch: 
What do you do once you've finished your addition or changes to the project and want to get it into the most recent version?

This is most easily done on the github website at the project page. 

#### Pull Request: 
On the webpage of our [project](https://github.com/spacetelescope/jwql/) you can change to the branch of your project under the 'Branch:master' button which will have a pull down list of all branches. 

Switch to your branch, and there will be a 'new pull request' button which you will click. From there it's important to do the following: 

##### 1. Fill out the tags to the side of the page including: choose a reviewer who will look over your changes and over suggestions to ensure your contributions follow the style guide, etc and tag yourself as the assignee. You can also add labels, projects or milestones if you would like as they help organize things. 

##### 2. Add a comment and title to your pull request that will inform the reviewer what your updates are supposed to do so they are aware of what they are reviewing. 

##### 3. Create the pull request and iterate with your reviewer on changes. You can follow the same workflow as above where you make changes to your local branch based on their comments on the webpage pull request. Then you will add, commit and push those changes to your branch which the pull request will keep track of. The pull request will also allow both you and the reviewer to track your changes. 

*** It's useful sometimes to create a pull request for a branch that isn't 100% ready to be merged - you can in that case make a 'WIP' (work in progress) request which will allow you to assign a reviewer and allow iteration over the project with that reviewer. 


## Versioning
See our [style guide](https://github.com/spacetelescope/jwql/blob/master/style-guide/style_guide.md) (will place summary in here as well).

## Environment Installation

Instructions in our wiki: https://github.com/spacetelescope/jwql/wiki/Environment-Installation

## Authors

## License

## Acknowledgments