branchname=$1
python_version=$2

printf "UPDATING JWQL ENVIRONMENT\n\n"

# Check operating system to obtain proper substring for environment
if [[ "$OSTYPE" == "darwin"* ]]; then
    os_str="macOS_ARM64"
    printf "INFORMATION: \n \t MAC OS DETECTED, USING MAC ENVIRONMENT FILE\n"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    os_str="Linux_X64"
    printf "INFORMATION: \n \t LINUX OS DETECTED, USING LINUX ENVIRONMENT FILE\n"
else
    printf "EXCEPTION: \n \t $OSTYPE NOT SUPPORTED, EXITING"
    return
fi

# Check if branch name starts with "v" for our major releases
# Our branch names contain v prior to version number, but version names on git
# do not contain v prior to the number.
if [[ $branchname == v* ]]; then
    jwql_version=${branchname:1:${#branchname}}
    environment_url=https://github.com/spacetelescope/jwql/releases/download/$jwql_version/
    environment_name=jwql_${jwql_version}_conda_${os_str}_py${python_version}
    environment_filename="${environment_name}.yml"
else
    printf "EXCEPTION: \n \t RELEASE DOESNT FOLLOW RELEASE VERSIONING NAMING CONVENTION, EXITING"
    return
fi

# Download asset from release and install it.
if curl --head --silent --fail "${environment_url}${environment_filename}" 2> /dev/null;
    then
        # Reset back to base first before generating environment (incase one is currently activated)
        eval "$(conda shell.bash deactivate)"
        eval "$(conda shell.bash activate base)"
        printf "\n SUCESSFULLY LOCATED ENVIRONMENT FILE ${environment_url}${environment_filename} \n"
        curl -L "${environment_url}/${environment_filename}" > jwql-current.yml
        $CONDA_EXE env create --name $environment_name --file jwql-current.yml
    else
        printf "EXCEPTION:\n"
        printf "\t ${environment_url}${environment_filename} DOES NOT EXIST, EXITING\n"
        printf "\t \nENSURE THAT: \n"
        printf "\t https://github.com/spacetelescope/jwql/releases/tag/$branchname \n"
        printf "EXISTS AND VERIFY ASSET FOR ${jwql_version}, ${python_version} FOR OS ${os_str}"
        return
fi

# Update symlink
cd ${CONDA_PREFIX}/envs/

env_symlink="jwql-current"

if [[ -L $env_symlink || -e $env_symlink ]]; then
   printf "INFORMATION:\n"
   printf "\tjwql-current SYMLINK EXISTS, UNLINKING\n"
   unlink jwql-current
fi

printf "INFORMATION:\n\tLINKING NEW ENVIRONMENT\n"
ln -s $environment_name jwql-current

printf "\tjwql-current HAS BEEN SET TO: ${environment_name}\n"
printf "\tTO SEE CHANGES, EXIT/RESTART SHELL\n"

# return to original directory
cd -

# Conda commands change shell prompt, this just returns it to the default
export PS1="\n(base)\h:\W \u\$ "
